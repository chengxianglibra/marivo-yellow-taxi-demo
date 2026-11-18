# Marivo NYC Yellow Taxi Demo

[English](README.md) | [简体中文](README.zh-CN.md)

A clone-and-analyze Marivo project over the official NYC TLC Yellow Taxi trip
records for December 2025 and the separately published Taxi Zone lookup.

## Setup

Requirements: macOS, Linux, or WSL; `make`; and network access. Python 3.12+ is
used when available, otherwise Marivo's installer provisions it with `uv`.

```bash
git clone <repository-url>
cd marivo-yellow-taxi-demo
make setup
```

`make setup` installs Marivo and its agent skills, verifies both remote schemas,
checks the semantic layer, and runs observations on the first seven days of the
source month.
DuckDB runs in memory and reads both source files over HTTPS during analysis.
The first remote read may install DuckDB's `httpfs` extension. The installer
resolves Marivo from upstream, so rerunning setup may replace a locally selected
build.

## Ask an agent

After setup, open this repository in a coding agent and ask:

> Compare December 1–7 with December 8–14, 2025. How much did metered fare
> revenue change, and which pickup boroughs, pickup zones, payment methods, and
> rate categories accounted for most of the difference? Check data completeness
> and unusual records, distinguish metered fares from total passenger charges,
> and avoid causal claims.

More prompts live under [`questions/en/`](questions/en/). A Chinese version is
available under [`questions/zh-CN/`](questions/zh-CN/).

## Useful commands

```bash
make verify
make semantic-snapshot
make semantic-check
make analysis-smoke
make data-verify
```

`make semantic-check` previews representative objects and checks both zone
relationships. `make semantic-snapshot` runs a bounded preview of every
published object for deeper diagnostics.

## Data model

The [`cloudfront` datasource](models/datasources/cloudfront.py) reads two
independent remote files through one in-memory DuckDB engine.
[`yellow_trips`](models/semantic/mobility/trips.py) reads the December 2025 Parquet.
The [pickup and drop-off entities](models/semantic/mobility/zones.py) read the Taxi
Zone CSV in their respective roles. Use their borough, zone, and service-zone
dimensions for OD analysis. Give same-named axes distinct aliases when exporting
a flat table with `frame.to_pandas(axis_names=...)`.

```text
yellow_trips
  ├── pickup_location_id  -> pickup_zones
  └── dropoff_location_id -> dropoff_zones
```

The trip Entity has one row per published record and declares no primary key.
Record-level operations that require a stable key are unavailable on that Entity.

Core governed metrics include demand; the complete published fare-component
family; recorded and credit-card-specific tips; distance, duration, plausible
speed, and fare per mile; known-record passenger averages and coverage;
congestion-pricing fees; and transparent record-quality counts and rates.
Pickup hour, ISO weekday, weekend, zone, borough, and service-zone dimensions
support operational and temporal pattern analysis.

`flex_fare_trip_share` counts TLC payment code `0` as a share of published
records in the observation scope. `fee_breakdown_coverage` divides the number
of records with all six fee components present by the same published-record
count. A reported zero counts as present. Both shares are missing when the
observation scope has zero published records.

In the December 1–7, 2025 check (New York local time), the 266,478 Flex Fare
records had 0% fee breakdown coverage. The NYS congestion surcharge and
airport fee were missing throughout the group. `tip_amount` was present on
every record and nonzero on 24,703 records.

Published totals retain correction-like records for auditability. Common
averages and efficiency metrics use a documented plausible-record subset:
source-month alignment, positive duration up to 24 hours, distance from 0 to
200 miles, implied speed no more than 100 mph, nonnegative fare and total, and
pickup and drop-off IDs in the published 1–265 range.

## Source and caveats

- Trip records and data dictionaries:
  <https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page>
- December 2025 trip records:
  <https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-12.parquet>
- Taxi zones:
  <https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv>

The TLC states that the records are supplied by authorized technology providers
and does not guarantee their accuracy or completeness. This project deliberately
retains implausible and correction-like rows so Marivo quality analysis can
surface them. Payment type `5` and `6` labels follow the TLC data dictionary.
