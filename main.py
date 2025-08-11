import json
from pprint import pprint
from typing import Any

import requests

BASE_URL = "https://www.nightjet.com"


def dprint(txt) -> None:
    print(txt)


def request_init_token(endpoint: str = "/nj-booking-ocp/init/start") -> str:
    DEBUG_TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjE3NTU1NDMyMjMsInB1YmxpY0lkIjoiYmU2N2ZlNDNjY2Y3NDI3Yjk0MjY3NmI0MjJmZmIzOWYifQ.Hvo7Ljm9iFof_w7RrQkVVACOX8wgY2qAzTKAYDm5QC4"
    token = DEBUG_TOKEN

    # headers = {
    #     "Referer": "https://www.nightjet.com",
    #     "Content-Type": "application/json"
    # }
    # body = {
    #     "lang": "en"
    # }
    # resp_json = requests.post(f"{BASE_URL}{endpoint}", data=json.dumps(body), headers=headers).json()
    # token = resp_json["token"]

    dprint(f"Received init token: {token}")
    return token


START_STATION = "8096003"  # BerlinHBF
END_STATION = "8796001"  # Paris Est
TRAVEL_DATE = "2025-10-14"


def request_connections(
    token: str, endpoint: str = "/nj-booking-ocp/connection"
) -> list[Any]:
    DEBUG_CONNECTIONS = json.loads(
        '{ "connections": [ { "from": { "name": "Berlin Hbf", "number": "8011160" }, "to": { "name": "Paris Est", "number": "8700011" }, "trains": [ { "train": "NJ 40424", "departure": { "utc": 1760461680000, "local": "2025-10-14T19:08:00" }, "arrival": { "utc": 1760513880000, "local": "2025-10-15T09:38:00" }, "trainType": "regular", "seatAsIC": false } ] }, { "from": { "name": "Berlin Hbf", "number": "8011160" }, "to": { "name": "Paris Est", "number": "8700011" }, "trains": [ { "train": "NJ 40424", "departure": { "utc": 1760634480000, "local": "2025-10-16T19:08:00" }, "arrival": { "utc": 1760686680000, "local": "2025-10-17T09:38:00" }, "trainType": "regular", "seatAsIC": false } ] }, { "from": { "name": "Berlin Hbf", "number": "8011160" }, "to": { "name": "Paris Est", "number": "8700011" }, "trains": [ { "train": "NJ 40424", "departure": { "utc": 1760893680000, "local": "2025-10-19T19:08:00" }, "arrival": { "utc": 1760945880000, "local": "2025-10-20T09:38:00" }, "trainType": "regular", "seatAsIC": false } ] } ] }'
    )
    resp_json = DEBUG_CONNECTIONS

    #     uri = f"{BASE_URL}{endpoint}/{START_STATION}/{END_STATION}/{TRAVEL_DATE}"
    #     headers = {
    #         "Accept": "application/json",
    #         "Accept-Language": "en-US,en;q=0.5",
    #         "Referer": "https://www.nightjet.com/en/ticket-buchen/",
    #         "x-token": token,
    #         "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0",
    #     }
    #
    #     resp_json = requests.get(
    #         uri,
    #         headers=headers,
    #     ).json()
    return resp_json["connections"]


TRAVELLER_BIRTHDATE = "2000-07-15"  # TODO: randomize a little


def connection_data_to_booking_requests(connections) -> list[dict[str, Any]]:
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
                {"type": "person", "birthDate": TRAVELLER_BIRTHDATE, "cards": []}
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
    with open("bookings.json") as f:
        DEBUG_BOOKINGS = json.load(f)
    resp_json = DEBUG_BOOKINGS

    # headers = {
    #     "Accept": "application/json",
    #     "Accept-Language": "en-US,en;q=0.5",
    #     "Content-Type": "application/json",
    #     "Referer": "https://www.nightjet.com/en/ticket-buchen/",
    #     "Origin": "https://www.nightjet.com",
    #     "x-token": token,
    #     "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0",
    # }
    # resp_json = requests.post(
    #     f"{BASE_URL}{endpoint}", headers=headers, data=json.dumps(booking_req)
    # ).json()
    # dprint(f"Requested prices ({booking_req["njFrom"]} -> {booking_req["njTo"]} at {booking_req["njDep"]}).")
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


def extract_prices(bookings_dict: list[dict[Any, Any]]) -> dict[Any, Any]:
    # .result[].connections[].offers[].reservation.reservationSegments[].compartments[].objects
    for booking in bookings_dict:
        for r in booking["result"]:
            for c in r["connections"]:
                for o in c["offers"]:
                    print(o["name"])


def main():
    token = request_init_token()
    connections = request_connections(token)
    booking_requests = connection_data_to_booking_requests(connections)
    bookings = [request_bookings(token, req) for req in booking_requests]
    dprint(extract_prices(bookings))


if __name__ == "__main__":
    main()
