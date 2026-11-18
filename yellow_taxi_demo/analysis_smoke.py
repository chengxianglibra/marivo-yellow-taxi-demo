"""End-to-end Marivo observations proving the main demo analysis families.

The first seven days of the configured month cover every weekday with a bounded
remote read. The smoke checks joins, time patterns, and representative metrics.
"""

from __future__ import annotations

from datetime import timedelta

import marivo.analysis as mv
import marivo.semantic as ms
import pandas as pd

from yellow_taxi_demo.data import MONTH_START, SOURCE_MONTH

SESSION_NAME = "setup-smoke"
SESSION_QUESTION = "Can the Yellow Taxi semantic layer execute its main analysis families?"
REPORT_TIMEZONE = "America/New_York"


def _session() -> mv.Session:
    return mv.session.get_or_create(
        SESSION_NAME,
        question=SESSION_QUESTION,
        timezone=REPORT_TIMEZONE,
    )


def _value(rows: pd.DataFrame, name: str) -> pd.Series:
    return pd.to_numeric(rows[name], errors="coerce")


def main() -> None:
    catalog = ms.load()
    session = _session()
    week_end = MONTH_START + timedelta(days=7)
    time_scope = session.time_scope(start=MONTH_START.isoformat(), end=week_end.isoformat())
    routes = session.observe(
        {"trip_count": catalog.get("metric:mobility.trip_count")},
        by=(
            catalog.get("dimension:mobility.pickup_zones.borough"),
            catalog.get("dimension:mobility.dropoff_zones.zone"),
        ),
        where=time_scope,
    ).compute().to_pandas()
    if routes.empty:
        raise RuntimeError("time-scoped route observation returned no rows")
    route_trips = int(_value(routes, "trip_count").sum())
    pickup_boroughs = routes["borough"].nunique()
    if route_trips <= 0 or pickup_boroughs < 5 or routes["zone"].nunique() < 2:
        raise RuntimeError("route observation did not cover multiple zones and positive trips")

    payment_and_time = session.observe(
        {
            "trip_count": catalog.get("metric:mobility.trip_count"),
            "average_speed_mph": catalog.get("metric:mobility.average_speed_mph"),
            "implausible_record_rate": catalog.get("metric:mobility.implausible_record_rate"),
        },
        by=(
            catalog.get("dimension:mobility.yellow_trips.source_month"),
            catalog.get("dimension:mobility.yellow_trips.payment_type"),
            catalog.get("dimension:mobility.yellow_trips.pickup_weekday"),
            catalog.get("dimension:mobility.yellow_trips.pickup_hour"),
        ),
        where=time_scope,
    ).compute().to_pandas()
    if payment_and_time.empty:
        raise RuntimeError("payment and time-pattern observation returned no rows")
    if set(payment_and_time["source_month"]) != {SOURCE_MONTH}:
        raise RuntimeError("the projected source month does not match the configured Parquet file")
    payment_and_time_trips = int(_value(payment_and_time, "trip_count").sum())
    tolerance = max(1, payment_and_time_trips // 1000)
    if abs(payment_and_time_trips - route_trips) > tolerance:
        raise RuntimeError(
            "payment and time-pattern trips do not reconcile to the route observation: "
            f"{payment_and_time_trips} != {route_trips} (tolerance {tolerance})"
        )
    if int(payment_and_time["pickup_hour"].nunique()) != 24:
        raise RuntimeError("time-pattern observation did not cover all 24 pickup hours")
    if int(payment_and_time["pickup_weekday"].nunique()) != 7:
        raise RuntimeError("time-pattern observation did not cover all 7 pickup weekdays")
    if not 0 < _value(payment_and_time, "average_speed_mph").max() <= 100:
        raise RuntimeError("plausible aggregate speed is outside the demo's expected range")
    if not (_value(payment_and_time, "implausible_record_rate") > 0).any():
        raise RuntimeError("quality observation failed to detect implausible records")
    print(
        "analysis smoke verified: time-scoped pickup relationship, OD, payment, and "
        f"weekday/hour analysis over the first seven days of {SOURCE_MONTH} "
        f"({route_trips:,} trips, {pickup_boroughs} pickup borough labels, session={session.id})"
    )


if __name__ == "__main__":
    main()
