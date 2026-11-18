from __future__ import annotations

from datetime import timedelta

import marivo.semantic as ms

from yellow_taxi_demo.data import MONTH_END, MONTH_START, SOURCE_MONTH


def test_analysis_window_covers_the_source_month() -> None:
    assert MONTH_START.isoformat() == f"{SOURCE_MONTH}-01"
    assert MONTH_END.day == 1
    assert (MONTH_END - timedelta(days=1)).strftime("%Y-%m") == SOURCE_MONTH


def test_trip_and_zone_entities_use_independent_cloudfront_files() -> None:
    catalog = ms.load()
    trips = catalog.get("entity:mobility.yellow_trips").definition
    pickup = catalog.get("entity:mobility.pickup_zones").definition
    dropoff = catalog.get("entity:mobility.dropoff_zones").definition

    assert trips.source.path == (
        "https://d37ci6vzurychx.cloudfront.net/trip-data/"
        f"yellow_tripdata_{SOURCE_MONTH}.parquet"
    )
    assert pickup.source == dropoff.source
    assert pickup.source.table == "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"
    assert trips.datasource == pickup.datasource == dropoff.datasource == "datasource:cloudfront"
    assert trips.primary_key == ()
    assert pickup.primary_key == dropoff.primary_key == ("location_id",)
