import ibis
import marivo.datasource as md
import marivo.semantic as ms
from ibis import _

PUBLISHED_RECORD_GUARDRAILS = [
    "Published records include corrections and incomplete values; pair conclusions with quality and coverage metrics.",
]
MONEY_GUARDRAILS = [
    "Negative correction-like amounts are retained; assess record quality before interpreting totals.",
]
LOCAL_TIME_GUARDRAILS = [
    "Interpret values in America/New_York and distinguish pickup time from source-file month.",
]
QUALITY_GUARDRAILS = [
    "These are transparent demo checks, not TLC validity determinations.",
]

@ms.entity(
    datasource=ms.ref.datasource("cloudfront"),
    source=md.parquet(
        "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2025-12.parquet"
    ),
    ai_context=ms.ai_context(
        business_definition="One row per published record in the configured Yellow Taxi Parquet.",
        guardrails=[
            "Count published records. The source projection has no stable record identity.",
            *PUBLISHED_RECORD_GUARDRAILS,
        ],
    ),
)
def yellow_trips(raw):
    return (
        raw.select(
            source_month=ibis.literal("2025-12"),  # Reconciled to the URL by analysis-smoke.
            picked_up_at=raw.tpep_pickup_datetime,
            dropped_off_at=raw.tpep_dropoff_datetime,
            duration_seconds=raw.tpep_dropoff_datetime.delta(
                raw.tpep_pickup_datetime, unit="second"
            ),
            pickup_hour=raw.tpep_pickup_datetime.hour().cast("int64"),
            pickup_weekday_number=(raw.tpep_pickup_datetime.day_of_week.index() + 1).cast("int64"),
            pickup_weekday=raw.tpep_pickup_datetime.strftime("%A"),
            vendor_id=raw.VendorID.cast("int64"),
            vendor=raw.VendorID.cases(
                (1, "Creative Mobile Technologies"),
                (2, "Curb Mobility"),
                (6, "Myle Technologies"),
                (7, "Helix"),
                else_="Unmapped or not reported",
            ),
            passenger_count=raw.passenger_count.cast("float64"),
            trip_distance_miles=raw.trip_distance.cast("float64"),
            rate_code_id=raw.RatecodeID.cast("int64"),
            rate_code=raw.RatecodeID.isnull().ifelse(
                "Not reported",
                raw.RatecodeID.cases(
                    (1, "Standard rate"),
                    (2, "JFK"),
                    (3, "Newark"),
                    (4, "Nassau or Westchester"),
                    (5, "Negotiated fare"),
                    (6, "Group ride"),
                    (99, "Null or unknown"),
                    else_="Unmapped",
                ),
            ),
            store_and_forward=raw.store_and_fwd_flag.cases(
                ("Y", "Stored then forwarded"), ("N", "Sent immediately"), else_="Not reported"
            ),
            pickup_location_id=raw.PULocationID.cast("int64"),
            dropoff_location_id=raw.DOLocationID.cast("int64"),
            payment_type_id=raw.payment_type.cast("int64"),
            payment_type=raw.payment_type.cases(
                (0, "Flex Fare trip"),
                (1, "Credit card"),
                (2, "Cash"),
                (3, "No charge"),
                (4, "Dispute"),
                (5, "Unknown (code 5)"),
                (6, "Voided trip"),
                else_="Unmapped or not reported",
            ),
            fare_amount_usd=raw.fare_amount.cast("float64"),
            extra_amount_usd=raw.extra.cast("float64"),
            mta_tax_usd=raw.mta_tax.cast("float64"),
            tip_amount_usd=raw.tip_amount.cast("float64"),
            tolls_amount_usd=raw.tolls_amount.cast("float64"),
            improvement_surcharge_usd=raw.improvement_surcharge.cast("float64"),
            total_amount_usd=raw.total_amount.cast("float64"),
            congestion_surcharge_usd=raw.congestion_surcharge.cast("float64"),
            airport_fee_usd=raw.Airport_fee.cast("float64"),
            cbd_congestion_fee_usd=raw.cbd_congestion_fee.cast("float64"),
        )
        .mutate(
            trip_duration_minutes=_.duration_seconds / 60.0,
            trip_duration_hours=_.duration_seconds / 3600.0,
            pickup_is_weekend=_.pickup_weekday_number.isin([6, 7]),
            pickup_time_matches_source_month=(
                _.picked_up_at.strftime("%Y-%m") == _.source_month
            ).fill_null(False),
            has_positive_duration=(_.dropped_off_at > _.picked_up_at).fill_null(False),
            has_nonnegative_distance=(_.trip_distance_miles >= 0).fill_null(False),
            has_positive_distance=(_.trip_distance_miles > 0).fill_null(False),
            has_reasonable_distance=_.trip_distance_miles.between(0, 200).fill_null(False),
            has_reasonable_duration=_.duration_seconds.between(1, 86400).fill_null(False),
            has_nonnegative_fare=(_.fare_amount_usd >= 0).fill_null(False),
            has_nonnegative_total=(_.total_amount_usd >= 0).fill_null(False),
            has_known_passenger_count=_.passenger_count.notnull(),
            has_valid_pickup_zone=_.pickup_location_id.between(1, 265).fill_null(False),
            has_valid_dropoff_zone=_.dropoff_location_id.between(1, 265).fill_null(False),
        )
        .mutate(
            has_reasonable_speed=(
                (_.trip_distance_miles == 0)
                | (
                    (_.duration_seconds > 0)
                    & (_.trip_distance_miles / _.trip_duration_hours <= 100)
                )
            ).fill_null(False),
        )
        .mutate(
            is_plausible_record=(
                _.pickup_time_matches_source_month
                & _.has_positive_duration
                & (_.duration_seconds <= 86400).fill_null(False)
                & _.has_reasonable_distance
                & _.has_reasonable_speed
                & _.has_nonnegative_fare
                & _.has_nonnegative_total
                & _.has_valid_pickup_zone
                & _.has_valid_dropoff_zone
            ),
        )
        .drop("duration_seconds")
    )


source_month = ms.dimension_column(
    name="source_month",
    entity=yellow_trips,
    column="source_month",
    ai_context=ms.ai_context(
        business_definition="Month encoded in the official source Parquet filename.",
        guardrails=[
            "This is a file-partition label; use picked_up_at for actual trip calendar analysis."
        ],
    ),
)
vendor_id = ms.dimension_column(
    name="vendor_id",
    entity=yellow_trips,
    column="vendor_id",
    ai_context=ms.ai_context(
        business_definition="Raw TLC code for the TPEP provider.",
        guardrails=["Use vendor for presentation and vendor_id for source-code auditing."],
    ),
)
vendor = ms.dimension_column(
    name="vendor",
    entity=yellow_trips,
    column="vendor",
    ai_context=ms.ai_context(
        business_definition="TPEP provider that supplied the trip record.",
        guardrails=PUBLISHED_RECORD_GUARDRAILS,
    ),
)
payment_type_id = ms.dimension_column(
    name="payment_type_id",
    entity=yellow_trips,
    column="payment_type_id",
    ai_context=ms.ai_context(
        business_definition="Raw TLC payment-type code.",
        guardrails=["Use payment_type for presentation and payment_type_id for source-code auditing."],
    ),
)
payment_type = ms.dimension_column(
    name="payment_type",
    entity=yellow_trips,
    column="payment_type",
    ai_context=ms.ai_context(
        business_definition="Published TLC payment category. Code 0 identifies Flex Fare.",
        guardrails=[
            "Cash tips are generally unrecorded. Isolate credit-card trips for rider tip analysis.",
            "Compare fee_breakdown_coverage across payment categories before comparing charges.",
        ],
    ),
)
rate_code_id = ms.dimension_column(
    name="rate_code_id",
    entity=yellow_trips,
    column="rate_code_id",
    ai_context=ms.ai_context(
        business_definition="Raw final TLC rate code.",
        guardrails=["Use rate_code for presentation and rate_code_id for source-code auditing."],
    ),
)
rate_code = ms.dimension_column(
    name="rate_code",
    entity=yellow_trips,
    column="rate_code",
    ai_context=ms.ai_context(
        business_definition="Final TLC rate code in effect for the trip.",
        guardrails=["Not reported is distinct from TLC code 99 and unmapped codes."],
    ),
)
store_and_forward = ms.dimension_column(
    name="store_and_forward",
    entity=yellow_trips,
    column="store_and_forward",
    ai_context=ms.ai_context(
        business_definition="Whether the vehicle held the record before sending it.",
        guardrails=["Not reported is retained as a separate category."],
    ),
)

pickup_location_id = ms.dimension_column(
    name="pickup_location_id",
    entity=yellow_trips,
    column="pickup_location_id",
    ai_context=ms.ai_context(
        business_definition="Official TLC pickup Taxi Zone key.",
        guardrails=["Retain missing and unknown codes in quality checks."],
    ),
)
dropoff_location_id = ms.dimension_column(
    name="dropoff_location_id",
    entity=yellow_trips,
    column="dropoff_location_id",
    ai_context=ms.ai_context(
        business_definition="Official TLC drop-off Taxi Zone key.",
        guardrails=["Retain missing and unknown codes in quality checks."],
    ),
)

pickup_hour = ms.dimension_column(
    name="pickup_hour",
    entity=yellow_trips,
    column="pickup_hour",
    ai_context=ms.ai_context(
        business_definition="Pickup hour of day from 0 through 23 in America/New_York.",
        guardrails=LOCAL_TIME_GUARDRAILS,
    ),
)
pickup_weekday_number = ms.dimension_column(
    name="pickup_weekday_number",
    entity=yellow_trips,
    column="pickup_weekday_number",
    ai_context=ms.ai_context(
        business_definition="ISO pickup weekday number, Monday 1 through Sunday 7.",
        guardrails=LOCAL_TIME_GUARDRAILS,
    ),
)
pickup_weekday = ms.dimension_column(
    name="pickup_weekday",
    entity=yellow_trips,
    column="pickup_weekday",
    ai_context=ms.ai_context(
        business_definition="English pickup weekday name in America/New_York.",
        guardrails=["Use pickup_weekday_number when deterministic calendar ordering matters."],
    ),
)
pickup_is_weekend = ms.dimension_column(
    name="pickup_is_weekend",
    entity=yellow_trips,
    column="pickup_is_weekend",
    ai_context=ms.ai_context(
        business_definition="Whether pickup occurred on Saturday or Sunday local time.",
        guardrails=LOCAL_TIME_GUARDRAILS,
    ),
)

pickup_time_matches_source_month = ms.dimension_column(
    name="pickup_time_matches_source_month",
    entity=yellow_trips,
    column="pickup_time_matches_source_month",
    ai_context=ms.ai_context(
        business_definition="Whether pickup calendar month matches the source-file month.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
has_positive_duration = ms.dimension_column(
    name="has_positive_duration",
    entity=yellow_trips,
    column="has_positive_duration",
    ai_context=ms.ai_context(
        business_definition="Whether drop-off occurs strictly after pickup.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
has_nonnegative_distance = ms.dimension_column(
    name="has_nonnegative_distance",
    entity=yellow_trips,
    column="has_nonnegative_distance",
    ai_context=ms.ai_context(
        business_definition="Whether taximeter-reported distance is nonnegative.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
has_positive_distance = ms.dimension_column(
    name="has_positive_distance",
    entity=yellow_trips,
    column="has_positive_distance",
    ai_context=ms.ai_context(
        business_definition="Whether taximeter-reported distance is strictly positive.",
        guardrails=["A zero-distance record is a review flag, not automatic proof of invalidity."],
    ),
)
has_reasonable_distance = ms.dimension_column(
    name="has_reasonable_distance",
    entity=yellow_trips,
    column="has_reasonable_distance",
    ai_context=ms.ai_context(
        business_definition="Whether reported distance is between 0 and 200 miles inclusive.",
        guardrails=["The 200-mile ceiling is a transparent demo plausibility threshold."],
    ),
)
has_reasonable_duration = ms.dimension_column(
    name="has_reasonable_duration",
    entity=yellow_trips,
    column="has_reasonable_duration",
    ai_context=ms.ai_context(
        business_definition="Whether elapsed duration is greater than 0 and no more than 24 hours.",
        guardrails=["The 24-hour ceiling is a transparent demo plausibility threshold."],
    ),
)
has_reasonable_speed = ms.dimension_column(
    name="has_reasonable_speed",
    entity=yellow_trips,
    column="has_reasonable_speed",
    ai_context=ms.ai_context(
        business_definition="Whether implied speed is no more than 100 mph, allowing zero distance.",
        guardrails=["The 100-mph ceiling is a transparent demo plausibility threshold."],
    ),
)
has_nonnegative_fare = ms.dimension_column(
    name="has_nonnegative_fare",
    entity=yellow_trips,
    column="has_nonnegative_fare",
    ai_context=ms.ai_context(
        business_definition="Whether metered fare amount is nonnegative.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
has_nonnegative_total = ms.dimension_column(
    name="has_nonnegative_total",
    entity=yellow_trips,
    column="has_nonnegative_total",
    ai_context=ms.ai_context(
        business_definition="Whether total passenger charge is nonnegative.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
has_known_passenger_count = ms.dimension_column(
    name="has_known_passenger_count",
    entity=yellow_trips,
    column="has_known_passenger_count",
    ai_context=ms.ai_context(
        business_definition="Whether driver-entered passenger count is present.",
        guardrails=["Missing values are unknown, not zero passengers."],
    ),
)
has_valid_pickup_zone = ms.dimension_column(
    name="has_valid_pickup_zone",
    entity=yellow_trips,
    column="has_valid_pickup_zone",
    ai_context=ms.ai_context(
        business_definition="Whether the pickup code is in the published TLC ID range of 1–265.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
has_valid_dropoff_zone = ms.dimension_column(
    name="has_valid_dropoff_zone",
    entity=yellow_trips,
    column="has_valid_dropoff_zone",
    ai_context=ms.ai_context(
        business_definition="Whether the drop-off code is in the published TLC ID range of 1–265.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
is_plausible_record = ms.dimension_column(
    name="is_plausible_record",
    entity=yellow_trips,
    column="is_plausible_record",
    ai_context=ms.ai_context(
        business_definition=(
            "Technical analysis predicate requiring source-month alignment, positive duration, "
            "bounded distance, duration, and implied speed, nonnegative fare and total, "
            "plus valid pickup and drop-off zones."
        ),
        guardrails=QUALITY_GUARDRAILS,
    ),
)

picked_up_at = ms.time_dimension_column(
    name="picked_up_at",
    entity=yellow_trips,
    column="picked_up_at",
    parse=ms.timestamp(timezone="America/New_York"),
    ai_context=ms.ai_context(
        business_definition="Passenger pickup wall-clock time in America/New_York.",
        guardrails=LOCAL_TIME_GUARDRAILS,
    ),
)
dropped_off_at = ms.time_dimension_column(
    name="dropped_off_at",
    entity=yellow_trips,
    column="dropped_off_at",
    parse=ms.timestamp(timezone="America/New_York"),
    ai_context=ms.ai_context(
        business_definition="Passenger drop-off wall-clock time in America/New_York.",
        guardrails=LOCAL_TIME_GUARDRAILS,
    ),
)

fare_amount = ms.measure_column(
    name="fare_amount",
    entity=yellow_trips,
    column="fare_amount_usd",
    additivity=ms.additive_all(),
    unit="USD",
    ai_context=ms.ai_context(
        business_definition="Metered time-and-distance fare in USD.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
extra_amount = ms.measure_column(
    name="extra_amount",
    entity=yellow_trips,
    column="extra_amount_usd",
    additivity=ms.additive_all(),
    unit="USD",
    ai_context=ms.ai_context(
        business_definition="Miscellaneous TLC extras and surcharges in USD.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
mta_tax_amount = ms.measure_column(
    name="mta_tax_amount",
    entity=yellow_trips,
    column="mta_tax_usd",
    additivity=ms.additive_all(),
    unit="USD",
    ai_context=ms.ai_context(
        business_definition="MTA tax amount in USD.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
tip_amount = ms.measure_column(
    name="tip_amount",
    entity=yellow_trips,
    column="tip_amount_usd",
    additivity=ms.additive_all(),
    unit="USD",
    ai_context=ms.ai_context(
        business_definition="Automatically recorded credit-card tip in USD.",
        guardrails=["Cash tips are generally not included."],
    ),
)
tolls_amount = ms.measure_column(
    name="tolls_amount",
    entity=yellow_trips,
    column="tolls_amount_usd",
    additivity=ms.additive_all(),
    unit="USD",
    ai_context=ms.ai_context(
        business_definition="Passenger-paid tolls in USD.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
improvement_surcharge_amount = ms.measure_column(
    name="improvement_surcharge_amount",
    entity=yellow_trips,
    column="improvement_surcharge_usd",
    additivity=ms.additive_all(),
    unit="USD",
    ai_context=ms.ai_context(
        business_definition="TLC improvement surcharge in USD.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
total_amount = ms.measure_column(
    name="total_amount",
    entity=yellow_trips,
    column="total_amount_usd",
    additivity=ms.additive_all(),
    unit="USD",
    ai_context=ms.ai_context(
        business_definition="Total passenger charge excluding cash tips.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
congestion_surcharge_amount = ms.measure_column(
    name="congestion_surcharge_amount",
    entity=yellow_trips,
    column="congestion_surcharge_usd",
    additivity=ms.additive_all(),
    unit="USD",
    ai_context=ms.ai_context(
        business_definition="NYS congestion surcharge in USD.",
        guardrails=["Do not conflate this field with the 2025 CBD congestion fee."],
    ),
)
airport_fee_amount = ms.measure_column(
    name="airport_fee_amount",
    entity=yellow_trips,
    column="airport_fee_usd",
    additivity=ms.additive_all(),
    unit="USD",
    ai_context=ms.ai_context(
        business_definition="Published pickup airport fee in USD.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
cbd_congestion_fee = ms.measure_column(
    name="cbd_congestion_fee",
    entity=yellow_trips,
    column="cbd_congestion_fee_usd",
    additivity=ms.additive_all(),
    unit="USD",
    ai_context=ms.ai_context(
        business_definition="Congestion Relief Zone fee published on 2025 records.",
        guardrails=["The field applies from January 5, 2025; do not treat earlier zeros as noncompliance."],
    ),
)
trip_distance = ms.measure_column(
    name="trip_distance",
    entity=yellow_trips,
    column="trip_distance_miles",
    additivity=ms.additive_all(),
    unit="mile",
    ai_context=ms.ai_context(
        business_definition="Taximeter-reported trip distance in miles.",
        guardrails=PUBLISHED_RECORD_GUARDRAILS,
    ),
)
trip_duration = ms.measure_column(
    name="trip_duration",
    entity=yellow_trips,
    column="trip_duration_minutes",
    additivity=ms.additive_all(),
    unit="minute",
    ai_context=ms.ai_context(
        business_definition="Elapsed minutes from pickup to drop-off.",
        guardrails=PUBLISHED_RECORD_GUARDRAILS,
    ),
)
trip_duration_hours = ms.measure_column(
    name="trip_duration_hours",
    entity=yellow_trips,
    column="trip_duration_hours",
    additivity=ms.additive_all(),
    unit="hour",
    ai_context=ms.ai_context(
        business_definition="Elapsed hours from pickup to drop-off.",
        guardrails=PUBLISHED_RECORD_GUARDRAILS,
    ),
)
passenger_count = ms.measure_column(
    name="passenger_count",
    entity=yellow_trips,
    column="passenger_count",
    additivity=ms.additive_all(),
    unit="passenger",
    ai_context=ms.ai_context(
        business_definition="Driver-entered passenger count when reported.",
        guardrails=["Missing values are unknown and must not be interpreted as zero."],
    ),
)


@ms.dimension(
    name="has_complete_fee_components",
    entity=yellow_trips,
    ai_context=ms.ai_context(
        business_definition=(
            "Whether the record reports all six published TLC fee components: extras, MTA tax, "
            "improvement surcharge, congestion surcharge, airport fee, and CBD congestion fee."
        ),
        guardrails=[
            "A reported zero counts as present. Any missing component makes the breakdown incomplete.",
        ],
    ),
)
def has_complete_fee_components(rows):
    return (
        ms.bind(extra_amount, rows).notnull()
        & ms.bind(mta_tax_amount, rows).notnull()
        & ms.bind(improvement_surcharge_amount, rows).notnull()
        & ms.bind(congestion_surcharge_amount, rows).notnull()
        & ms.bind(airport_fee_amount, rows).notnull()
        & ms.bind(cbd_congestion_fee, rows).notnull()
    )
