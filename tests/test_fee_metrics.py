from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from shutil import copyfile

import marivo.analysis as mv
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from yellow_taxi_demo.data import MONTH_START, SOURCE_MONTH

FEE_COLUMNS = (
    "extra",
    "mta_tax",
    "improvement_surcharge",
    "congestion_surcharge",
    "Airport_fee",
    "cbd_congestion_fee",
)
METRICS = (
    "trip_count",
    "flex_fare_trip_count",
    "flex_fare_trip_share",
    "fee_breakdown_complete_trip_count",
    "fee_breakdown_coverage",
    "total_surcharges",
    "tips",
)


def _trip(day: int, payment_code: int, **amounts: float | None) -> dict[str, object]:
    pickup = datetime(MONTH_START.year, MONTH_START.month, day, 12)
    return {
        "tpep_pickup_datetime": pickup,
        "tpep_dropoff_datetime": pickup + timedelta(minutes=10),
        "VendorID": 1,
        "passenger_count": 1,
        "trip_distance": 1.0,
        "RatecodeID": 1,
        "store_and_fwd_flag": "N",
        "PULocationID": 100,
        "DOLocationID": 132,
        "payment_type": payment_code,
        "fare_amount": 10.0,
        "tip_amount": 0.0,
        "tolls_amount": 0.0,
        "total_amount": 10.0,
        **dict.fromkeys(FEE_COLUMNS, 0.0),
        **amounts,
    }


@pytest.fixture
def fee_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> mv.Session:
    root = Path(__file__).resolve().parents[1]
    parquet = tmp_path / "trips.parquet"
    rows = [
        _trip(1, 1),
        _trip(1, 1, fare_amount=-1.0, total_amount=-1.0),
        *(_trip(1, 1, **{column: None}) for column in FEE_COLUMNS if column != "Airport_fee"),
        _trip(1, 1, Airport_fee=None, extra=2.0),
        _trip(1, 0, congestion_surcharge=None, Airport_fee=None, tip_amount=3.5),
        _trip(2, 0),
    ]
    pq.write_table(pa.Table.from_pylist(rows), parquet)
    for name in (
        "models/datasources/cloudfront.py",
        "models/semantic/mobility/_domain.py",
        "models/semantic/mobility/metrics.py",
    ):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        copyfile(root / name, target)

    trip_model = Path("models/semantic/mobility/trips.py")
    source = (root / trip_model).read_text(encoding="utf-8")
    remote = f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{SOURCE_MONTH}.parquet"
    assert source.count(remote) == 1
    (tmp_path / trip_model).write_text(source.replace(remote, parquet.as_posix()), encoding="utf-8")
    (tmp_path / "marivo.toml").write_text(
        '[project]\nname = "fee-metrics-test"\nversion = "0.1.0"\n\n'
        '[telemetry]\nenabled = "off"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MARIVO_PROJECT_ROOT", str(tmp_path))
    return mv.session.get_or_create("fee-metrics-test", timezone="America/New_York")


def _observe(
    session: mv.Session, start: int, end: int, *, by_payment: bool = False
) -> pd.DataFrame:
    catalog = session.catalog
    metrics = {name: catalog.get(f"metric:mobility.{name}") for name in METRICS}
    by = (catalog.get("dimension:mobility.yellow_trips.payment_type"),) if by_payment else ()
    period = session.time_scope(
        start=f"{SOURCE_MONTH}-{start:02d}", end=f"{SOURCE_MONTH}-{end:02d}"
    )
    return session.observe(metrics, by=by, where=period).compute().to_pandas()


def test_fee_coverage_distinguishes_zero_from_missing_by_payment(fee_session: mv.Session) -> None:
    rows = _observe(fee_session, 1, 2, by_payment=True).set_index("payment_type")

    card = rows.loc["Credit card"]
    assert card["trip_count"] == 8
    assert card["fee_breakdown_complete_trip_count"] == 2
    assert card["fee_breakdown_coverage"] == pytest.approx(2 / 8)
    assert card["total_surcharges"] == pytest.approx(2.0)

    flex = rows.loc["Flex Fare trip"]
    assert flex["trip_count"] == flex["flex_fare_trip_count"] == 1
    assert flex["fee_breakdown_complete_trip_count"] == 0
    assert flex["fee_breakdown_coverage"] == 0.0
    assert pd.isna(flex["total_surcharges"])
    assert flex["tips"] == pytest.approx(3.5)


def test_shares_count_published_rows_and_complete_flex_fares(fee_session: mv.Session) -> None:
    row = _observe(fee_session, 1, 3).iloc[0]

    assert row["trip_count"] == 10
    assert row["flex_fare_trip_count"] == 2
    assert row["flex_fare_trip_share"] == pytest.approx(2 / 10)
    assert row["fee_breakdown_complete_trip_count"] == 3
    assert row["fee_breakdown_coverage"] == pytest.approx(3 / 10)

    only_complete_flex = _observe(fee_session, 2, 3).iloc[0]
    assert only_complete_flex["fee_breakdown_coverage"] == 1.0
    assert only_complete_flex["total_surcharges"] == 0.0


def test_shares_are_missing_with_zero_published_trips(fee_session: mv.Session) -> None:
    row = _observe(fee_session, 3, 4).iloc[0]

    assert row["trip_count"] == 0
    assert pd.isna(row["flex_fare_trip_share"])
    assert pd.isna(row["fee_breakdown_coverage"])
