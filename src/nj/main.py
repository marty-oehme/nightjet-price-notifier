import csv
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Annotated, Any

import requests
import typer

BASE_URL = "https://www.nightjet.com"
BASE_DIR = "out"
CSV_LOWEST_FILE = "lowest.csv"
CSV_ALL_PRICES_PATTERN = "all_prices_%%DATE%%.csv"
NOTIFICATION_CHANNEL = "nightjet-price-notifier"

START_STATION = "8096003"  # BerlinHBF
END_STATION = "8796001"  # Paris Est
TRAVELLER_BIRTHDATE = datetime(1990, 1, 1)  # TODO: could randomize a little

MONITOR_FREQUENCY = 3600


def dprint(txt) -> None:
    print(f"{datetime.now()}: {txt}")


def request_start(endpoint: str = "/nj-booking-ocp/init/start") -> dict:
    headers = {
        "Referer": "https://www.nightjet.com",
        "Content-Type": "application/json",
    }
    body = {"lang": "en"}
    resp_json = requests.post(
        f"{BASE_URL}{endpoint}", data=json.dumps(body), headers=headers
    ).json()
    return resp_json


def get_init_token(endpoint: str = "/nj-booking-ocp/init/start") -> str:
    token = request_start(endpoint)["token"]
    dprint(f"Received init token: {token}")
    return token


def request_connections(
    token: str,
    start_station: int,
    end_station: int,
    travel_date: datetime,
    endpoint: str = "/nj-booking-ocp/connection",
) -> list[Any]:
    uri = f"{BASE_URL}{endpoint}/{start_station}/{end_station}/{travel_date.strftime('%Y-%m-%d')}"
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.nightjet.com/en/ticket-buchen/",
        "x-token": token,
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0",
    }

    resp_json = requests.get(
        uri,
        headers=headers,
    ).json()
    return resp_json["connections"]


def connection_data_to_booking_requests(
    connections, traveller_birthdate: datetime = TRAVELLER_BIRTHDATE
) -> list[dict[str, Any]]:
    b_requests = []
    for c in connections:
        train = c["trains"][0]
        dep = train["departure"]["utc"]
        req = {
            "njFrom": c["from"]["number"],  # from station,
            "njTo": c["to"]["number"],  # to station
            "njDep": dep,  # departure time,
            "maxChanges": 0,
            "connections": 1,
            "filter": {
                "njTrain": train["train"],  # train number
                "njDeparture": dep,  # departure time again
            },
            "objects": [  # traveller
                {
                    "type": "person",
                    "birthDate": traveller_birthdate.strftime("%Y-%m-%d"),
                    "cards": [],
                }
            ],
            "relations": [],
            "lang": "en",
        }
        b_requests.append(req)
        dprint(
            f"Crafted booking request {c['from']['name']} -> {c['to']['name']}: {train['departure']['local']}-{train['arrival']['local']}."
        )
    return b_requests


def request_bookings(
    token: str, booking_req: dict[str, Any], endpoint: str = "/nj-booking-ocp/offer/get"
) -> dict[Any, Any]:
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.5",
        "Content-Type": "application/json",
        "Referer": "https://www.nightjet.com/en/ticket-buchen/",
        "Origin": "https://www.nightjet.com",
        "x-token": token,
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0",
    }
    resp_json = requests.post(
        f"{BASE_URL}{endpoint}", headers=headers, data=json.dumps(booking_req)
    ).json()
    dprint(
        f"Requested prices ({booking_req['njFrom']} -> {booking_req['njTo']} at {booking_req['njDep']})."
    )
    return resp_json


def json_extract(obj, key):
    """Recursively fetch values from nested JSON."""
    arr = []

    def extract(obj, arr, key):
        """Recursively search for values of key in JSON tree."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    values = extract(obj, arr, key)
    return values


@dataclass
class Price:
    id: str
    name: str
    price: float
    dt_from: datetime
    dt_to: datetime


def extract_prices(bookings_dict: list[dict[Any, Any]]) -> list[Price]:
    prices = []
    # .result[].connections[].offers[].reservation.reservationSegments[].compartments[].objects
    for booking in bookings_dict:
        for reservation in booking["result"]:
            for connection in reservation["connections"]:
                for offer in connection["offers"]:
                    for reservation in offer["reservation"]["reservationSegments"]:
                        for compartment in reservation["compartments"]:
                            id = compartment["externalIdentifier"]
                            name = compartment["name"]["en"]
                            # filter undesired compartments
                            if id in ["sideCorridorCoach_2"]:
                                continue
                            # print all compartment identifiers w/ full name
                            # dprint(f"{id}: {name}")

                            # only keep those with a price (i.e. bookable?)
                            if "objects" not in compartment:
                                continue
                            price = compartment["objects"][0]["price"]
                            prices.append(
                                Price(
                                    id,
                                    name,
                                    price,
                                    dt_from=datetime.strptime(
                                        offer["validityPeriodFrom"],
                                        "%Y-%m-%dT%H:%M:%S.%f%z",
                                    ),
                                    dt_to=datetime.strptime(
                                        offer["validityPeriodTo"],
                                        "%Y-%m-%dT%H:%M:%S.%f%z",
                                    ),
                                )
                            )
    return prices


def_time = datetime.fromtimestamp(0.0)


def get_lowest_price(prices: list[Price]) -> Price:
    lowest = Price("", "", 10000000.0, def_time, def_time)
    for p in prices:
        if p.price < lowest.price:
            lowest = p
    return lowest


def dump_all_prices_to_csv(prices: list[Price], fpath: Path) -> None:
    fstr = str(fpath)
    fpath_replaced = Path(
        fstr.replace("%%DATE%%", str(int(datetime.now().timestamp())))
    )
    with open(fpath_replaced, "w") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "price", "ts_from", "ts_to", "name"])
        writer.writerows(
            [
                [
                    price.id,
                    price.price,
                    price.dt_from.timestamp(),
                    price.dt_to.timestamp(),
                    price.name,
                ]
                for price in prices
            ]
        )
    dprint(f"Dumped current query snapshot into: {fpath_replaced}.")


def add_to_csv(price: Price, file: Path) -> None:
    if not file.is_file():
        with open(file, "w") as f:
            csv.writer(f).writerow(["id", "price", "ts_from", "ts_to", "name"])

    with open(file, "a") as f:
        csv.writer(f).writerow(
            [
                price.id,
                price.price,
                price.dt_from.timestamp(),
                price.dt_to.timestamp(),
                price.name,
            ]
        )


def get_last_price_from_csv(file: Path) -> Price | None:
    if not file.is_file():
        return

    with open(file) as f:
        last = next(reversed(list(csv.reader(f))))
        return Price(
            id=last[0],
            price=float(last[1]),
            dt_from=datetime.fromtimestamp(float(last[2])),
            dt_to=datetime.fromtimestamp(float(last[3])),
            name=last[4],
        )


def notify_user(previous: Price, new: Price, channel: str) -> None:
    requests.post(
        f"https://ntfy.sh/{channel}",
        data=f"from {previous.price} -> {new.price} ({new.name}: {new.dt_from.strftime('%Y-%m-%d %H:%M')} - {new.dt_to.strftime('%Y-%m-%d %H:%M')})",
        headers={
            "Title": f"Nightjet train price went {'down' if new.price < previous.price else 'up'}",
            "Priority": "urgent" if new.price < previous.price else "default",
            "Tags": "green_circle" if new.price < previous.price else "orange_circle",
        },
    )


def query(
    start_station: int,
    end_station: int,
    travel_date: datetime,
    traveller_birthdate: datetime,
) -> list[Price]:
    token = get_init_token()
    connections = request_connections(token, start_station, end_station, travel_date)
    booking_requests = connection_data_to_booking_requests(connections, traveller_birthdate=traveller_birthdate)
    bookings = [request_bookings(token, req) for req in booking_requests]
    prices = extract_prices(bookings)

    return prices


## CLI
app = typer.Typer()


@app.command()
def main(
    travel_date: Annotated[
        str, typer.Argument(help="Travel day to search from. (YYYY-MM-DD)")
    ],
    start_station: int = typer.Option(
        START_STATION, help="Departure station number. (default: Berlin Hbf)"
    ),
    end_station: int = typer.Option(
        END_STATION, help="Destination station number. (default: Paris Est)"
    ),
    birthdate: str = typer.Option(TRAVELLER_BIRTHDATE.strftime("%Y-%m-%d"), help="Traveller birthdate, may be important for discounts. (YYYY-MM-DD)"),
    notification_channel: str = typer.Option(
        NOTIFICATION_CHANNEL, help="ntfy channel to inform user on."
    ),
    monitor_mode: bool = typer.Option(
        True,
        help="Run queries repeatedly over time. If False only runs a single query (oneshot mode).",
    ),
    monitor_frequency: int = typer.Option(
        MONITOR_FREQUENCY,
        help="How often to run price queries if in monitoring mode, in seconds.",
    ),
    base_output_directory: Path = typer.Option(
        Path(BASE_DIR), help="Directory in which to output all result files."
    ),
    lowest_prices_filename: str = typer.Option(
        CSV_LOWEST_FILE, help="Filename for collecting lowest found prices."
    ),
    price_snapshot_pattern: str = typer.Option(
        CSV_ALL_PRICES_PATTERN,
        help="Filename pattern for saving all prices of each query. Takes %%DATE%% as pattern to replace with current unix timestamp.",
    ),
    dump_price_snapshot: bool = typer.Option(
        True, help="Dump _all_ queried prices into a timestamped csv file."
    ),
):
    base_output_directory.mkdir(exist_ok=True, parents=True)
    lowest_prices_path = base_output_directory.joinpath(lowest_prices_filename)
    price_snapshot_path = base_output_directory.joinpath(price_snapshot_pattern)

    try:
        travel_date_obj = datetime.strptime(travel_date, "%Y-%m-%d")
        birth_date_obj = datetime.strptime(birthdate, "%Y-%m-%d")
    except ValueError:
        typer.echo("Invalid date format. Use YYYY-MM-DD", err=True)
        raise typer.Exit(1)

    while True:
        prices = query(
            start_station=start_station, end_station=end_station, travel_date=travel_date_obj, traveller_birthdate=birth_date_obj,
        )

        # create a snapshot of all current prices
        if dump_price_snapshot:
            dump_all_prices_to_csv(prices, price_snapshot_path)

        # extract the lowest and the last lowest price
        new = get_lowest_price(prices)
        previous = get_last_price_from_csv(lowest_prices_path)

        # if the price changed, add it to lowest prices
        if not previous or new.price != previous.price:
            dprint(f"PRICE CHANGE. {previous} -> {new}")
            add_to_csv(new, lowest_prices_path)
            notify_user(
                previous
                or Price(
                    "",
                    "No previous price",
                    0.0,
                    datetime.fromtimestamp(0),
                    datetime.fromtimestamp(0),
                ),
                new,
                notification_channel,
            )

        # oneshot exit
        if not monitor_mode:
            break
        dprint(
            f"Query complete. Monitoring mode active, sleeping for {monitor_frequency} seconds..."
        )
        sleep(monitor_frequency)


if __name__ == "__main__":
    app()
