# Nightjetter

A search through all the available prices for a single ÖBB Nightjet route from A to B.

Can be used to continuously monitor prices and notify the user on changes,
or for a single search for all available prices.

Comes with a nice Python CLI, or could be imported as a Python library for programmatic use.

## The CLI

It comes with a `typer`-supported CLI which you can use to craft your search.
Most options should be pretty self-explanatory, but a few notes:

- `monitor-mode` switches between a single search or the app running continuously until you turn it off.
- Any files created by the application are put under the `base-output-directory`, so make sure it has write permissions there.
- I am not sure how important the `birthdate` is, but included it since Nightjet may give discounts for young people or seniors?
- You can use the price snapshots, if you decide to create them with `dump-price-snapshot`, to create pretty time series graphs
- Currently, we _only_ support `ntfy`, as well as the official `ntfy` server as the notification channel

```help
 Usage: nightjet [OPTIONS] TRAVEL_DATE

╭─ Arguments ─────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    travel_date      TEXT  Travel day to search from. (YYYY-MM-DD) [default: None] [required]                      │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --start-station                                         INTEGER  Departure station number. (default: Berlin Hbf)    │
│                                                                  [default: 8096003]                                 │
│ --end-station                                           INTEGER  Destination station number. (default: Paris Est)   │
│                                                                  [default: 8796001]                                 │
│ --birthdate                                             TEXT     Traveller birthdate, may be important for          │
│                                                                  discounts. (YYYY-MM-DD)                            │
│                                                                  [default: 1990-01-01]                              │
│ --notification-channel                                  TEXT     ntfy channel to inform user on.                    │
│                                                                  [default: nightjet-price-notifier]                 │
│ --monitor-mode              --no-monitor-mode                    Run queries repeatedly over time. If False only    │
│                                                                  runs a single query (oneshot mode).                │
│                                                                  [default: monitor-mode]                            │
│ --monitor-frequency                                     INTEGER  How often to run price queries if in monitoring    │
│                                                                  mode, in seconds.                                  │
│                                                                  [default: 3600]                                    │
│ --base-output-directory                                 PATH     Directory in which to output all result files.     │
│                                                                  [default: out]                                     │
│ --lowest-prices-filename                                TEXT     Filename for collecting lowest found prices.       │
│                                                                  [default: lowest.csv]                              │
│ --price-snapshot-pattern                                TEXT     Filename pattern for saving all prices of each     │
│                                                                  query. Takes %%DATE%% as pattern to replace with   │
│                                                                  current unix timestamp.                            │
│                                                                  [default: all_prices_%%DATE%%.csv]                 │
│ --dump-price-snapshot       --no-dump-price-snapshot             Dump _all_ queried prices into a timestamped csv   │
│                                                                  file.                                              │
│                                                                  [default: dump-price-snapshot]                     │
│ --install-completion                                             Install completion for the current shell.          │
│ --show-completion                                                Show completion for the current shell, to copy it  │
│                                                                  or customize the installation.                     │
│ --help                                                           Show this message and exit.                        │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## Future

This tool does (mostly did) what I needed it to do.
That means I don't have a big drive to work on, change and add to the current codebase.
Nevertheless, feel welcome to file an issue if you noticed something, or have a feature request.
PRs are of course also always welcome.

Here are a bunch of things I think should definitely be considered for further work:

1. The code is not very organized, and everything is one big file.
  Perhaps this could be extracted into the individual areas of operation a bit better.

2. Additional patterns for the price snapshots. We currently only consider `%%DATE%%` as a valid substitution.
  It is substituted into a unix timestamp. More flexibility here could be nice.
  Perhaps also allow the substitution in other paths passed to the cli.

3. The stations are only considered as internal numbers (`int` types). This would be a first QoL change,
  to automatically look up the correct station number for whatever is passed in.

4. We don't map the trains, stations and journeys as internal objects.
  Instead they are all passed around as dicts and JSON objects.
  This could definitely be improved for better maintainability.

5. Support more notification channels. This should be self-explanatory, and could probably be pretty
  easily be improved with a library like [apprise](https://github.com/caronc/apprise?tab=readme-ov-file#developer-api-usage).
