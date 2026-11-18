"""Static semantic-layer verification used by setup."""

from __future__ import annotations

import marivo.semantic as ms

REQUIRED_METRICS = (
    "mobility.trip_count",
    "mobility.fare_revenue",
    "mobility.total_surcharges",
    "mobility.tip_rate",
    "mobility.credit_card_tip_rate",
    "mobility.average_passengers",
    "mobility.passenger_count_coverage",
    "mobility.plausible_passenger_count_coverage",
    "mobility.average_speed_mph",
    "mobility.implausible_record_rate",
    "mobility.negative_fare_record_rate",
)
REQUIRED_DIMENSIONS = (
    "mobility.pickup_zones.borough",
    "mobility.dropoff_zones.borough",
    "mobility.yellow_trips.pickup_location_id",
    "mobility.yellow_trips.dropoff_location_id",
    "mobility.yellow_trips.pickup_hour",
    "mobility.yellow_trips.pickup_weekday",
)


def main() -> None:
    catalog = ms.load()
    required = [catalog.get(f"metric:{path}") for path in REQUIRED_METRICS]
    required += [catalog.get(f"dimension:{path}") for path in REQUIRED_DIMENSIONS]
    report = catalog.readiness(refs=required)
    if report.status != "ready":
        report.show()
        raise RuntimeError("required Yellow Taxi semantic definitions are not ready")
    print(
        f"semantic catalog verified: {len(REQUIRED_METRICS)} metrics + "
        f"{len(REQUIRED_DIMENSIONS)} dimensions, "
        f"physical dependency closures checked, readiness={report.status}"
    )


if __name__ == "__main__":
    main()
