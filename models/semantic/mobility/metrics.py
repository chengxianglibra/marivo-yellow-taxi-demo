"""Derived metrics for the mobility domain.

Physical constructors capture typed Deferred symbols; this module references the
governed physical fields by exact path and composes Metrics directly. The loader
binds the forward references before publishing the closed catalog.
"""

import marivo.semantic as ms

PUBLISHED_RECORD_GUARDRAILS = [
    "Published records include corrections and incomplete values; pair conclusions with quality and coverage metrics.",
]
MONEY_GUARDRAILS = [
    "Negative correction-like amounts are retained; assess record quality before interpreting totals.",
]
QUALITY_GUARDRAILS = [
    "These are transparent demo checks, not TLC validity determinations.",
]

trips = ms.ref.entity("mobility.yellow_trips")
picked_up_at_value = ms.ref.time_dimension("mobility.yellow_trips.picked_up_at")
fare_amount_value = ms.ref.measure("mobility.yellow_trips.fare_amount")
extra_amount_value = ms.ref.measure("mobility.yellow_trips.extra_amount")
mta_tax_amount_value = ms.ref.measure("mobility.yellow_trips.mta_tax_amount")
tip_amount_value = ms.ref.measure("mobility.yellow_trips.tip_amount")
tolls_amount_value = ms.ref.measure("mobility.yellow_trips.tolls_amount")
improvement_surcharge_amount_value = ms.ref.measure("mobility.yellow_trips.improvement_surcharge_amount")
total_amount_value = ms.ref.measure("mobility.yellow_trips.total_amount")
congestion_surcharge_amount_value = ms.ref.measure("mobility.yellow_trips.congestion_surcharge_amount")
airport_fee_amount_value = ms.ref.measure("mobility.yellow_trips.airport_fee_amount")
cbd_congestion_fee_value = ms.ref.measure("mobility.yellow_trips.cbd_congestion_fee")
trip_distance_value = ms.ref.measure("mobility.yellow_trips.trip_distance")
trip_duration_value = ms.ref.measure("mobility.yellow_trips.trip_duration")
trip_duration_hours_value = ms.ref.measure("mobility.yellow_trips.trip_duration_hours")
passenger_count_value = ms.ref.measure("mobility.yellow_trips.passenger_count")
payment_type_value = ms.ref.dimension("mobility.yellow_trips.payment_type")
pickup_time_matches_source_month_value = ms.ref.dimension("mobility.yellow_trips.pickup_time_matches_source_month")
has_positive_duration_value = ms.ref.dimension("mobility.yellow_trips.has_positive_duration")
has_positive_distance_value = ms.ref.dimension("mobility.yellow_trips.has_positive_distance")
has_nonnegative_fare_value = ms.ref.dimension("mobility.yellow_trips.has_nonnegative_fare")
has_nonnegative_total_value = ms.ref.dimension("mobility.yellow_trips.has_nonnegative_total")
has_known_passenger_count_value = ms.ref.dimension("mobility.yellow_trips.has_known_passenger_count")
has_valid_pickup_zone_value = ms.ref.dimension("mobility.yellow_trips.has_valid_pickup_zone")
has_valid_dropoff_zone_value = ms.ref.dimension("mobility.yellow_trips.has_valid_dropoff_zone")
is_plausible_record_value = ms.ref.dimension("mobility.yellow_trips.is_plausible_record")

CREDIT_CARD = payment_type_value == "Credit card"
PLAUSIBLE = is_plausible_record_value == True  # noqa: E712 - typed predicate comparison
KNOWN_PASSENGERS = has_known_passenger_count_value == True  # noqa: E712
PLAUSIBLE_KNOWN_PASSENGERS = PLAUSIBLE & KNOWN_PASSENGERS


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Count of published Yellow Taxi trip records.",
        guardrails=PUBLISHED_RECORD_GUARDRAILS,
    ),
)
def trip_count():
    return trips.count(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of metered fare amount in USD.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
def fare_revenue():
    return fare_amount_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of miscellaneous TLC extras and surcharges in USD.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
def extra_charges():
    return extra_amount_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of MTA tax amounts in USD.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
def mta_taxes():
    return mta_tax_amount_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of automatically recorded tips in USD.",
        guardrails=["Cash tips are generally not included."],
    ),
)
def tips():
    return tip_amount_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of passenger-paid tolls in USD.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
def tolls():
    return tolls_amount_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of TLC improvement surcharges in USD.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
def improvement_surcharges():
    return improvement_surcharge_amount_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of total passenger charges excluding unrecorded cash tips.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
def total_charged():
    return total_amount_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of NYS congestion surcharges in USD.",
        guardrails=["Do not conflate this field with total_cbd_congestion_fees."],
    ),
)
def congestion_surcharges():
    return congestion_surcharge_amount_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of published airport fees in USD.",
        guardrails=MONEY_GUARDRAILS,
    ),
)
def airport_fees():
    return airport_fee_amount_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of published Congestion Relief Zone fees in USD.",
        guardrails=["The field applies from January 5, 2025."],
    ),
)
def total_cbd_congestion_fees():
    return cbd_congestion_fee_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition=(
            "Sum of miscellaneous extras, MTA tax, improvement, congestion, airport, "
            "and CBD fee components."
        ),
        guardrails=["Excludes metered fare, tips, and tolls."],
    ),
)
def total_surcharges():
    return (
        extra_charges
        + mta_taxes
        + improvement_surcharges
        + congestion_surcharges
        + airport_fees
        + total_cbd_congestion_fees
    )


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of taximeter-reported trip miles.",
        guardrails=PUBLISHED_RECORD_GUARDRAILS,
    ),
)
def total_trip_distance():
    return trip_distance_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of elapsed trip minutes.",
        guardrails=PUBLISHED_RECORD_GUARDRAILS,
    ),
)
def total_trip_duration():
    return trip_duration_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of elapsed trip hours.",
        guardrails=PUBLISHED_RECORD_GUARDRAILS,
    ),
)
def total_trip_duration_hours():
    return trip_duration_hours_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Sum of available driver-entered passenger counts.",
        guardrails=["Missing passenger counts are excluded from the sum."],
    ),
)
def total_passengers():
    return passenger_count_value.sum(time=picked_up_at_value)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Count of rows passing the demo's technical plausibility predicate.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def plausible_trip_count():
    return trips.count(time=picked_up_at_value).where(PLAUSIBLE)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Metered fare revenue from technically plausible records.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def plausible_fare_revenue():
    return fare_amount_value.sum(time=picked_up_at_value).where(PLAUSIBLE)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Reported miles from technically plausible records.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def plausible_total_trip_distance():
    return trip_distance_value.sum(time=picked_up_at_value).where(PLAUSIBLE)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Elapsed minutes from technically plausible records.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def plausible_total_trip_duration():
    return trip_duration_value.sum(time=picked_up_at_value).where(PLAUSIBLE)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Elapsed hours from technically plausible records.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def plausible_total_trip_duration_hours():
    return trip_duration_hours_value.sum(time=picked_up_at_value).where(PLAUSIBLE)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Reported passengers from technically plausible records.",
        guardrails=["Missing values are excluded, not treated as zero."],
    ),
)
def plausible_total_passengers():
    return passenger_count_value.sum(time=picked_up_at_value).where(PLAUSIBLE_KNOWN_PASSENGERS)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Technically plausible records with a reported passenger count.",
        guardrails=["Use as the denominator for average_passengers."],
    ),
)
def known_plausible_passenger_trip_count():
    return trips.count(time=picked_up_at_value).where(PLAUSIBLE_KNOWN_PASSENGERS)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Count of published records with a reported passenger count.",
        guardrails=["Use as the denominator for average_passengers."],
    ),
)
def known_passenger_trip_count():
    return trips.count(time=picked_up_at_value).where(KNOWN_PASSENGERS)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Count of records whose payment type is credit card.",
        guardrails=PUBLISHED_RECORD_GUARDRAILS,
    ),
)
def credit_card_trip_count():
    return trips.count(time=picked_up_at_value).where(CREDIT_CARD)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Metered fare revenue from plausible credit-card records.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def credit_card_fare_revenue():
    return fare_amount_value.sum(time=picked_up_at_value).where(CREDIT_CARD & PLAUSIBLE)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Automatically recorded tips from plausible credit-card records.",
        guardrails=["Cash tips and technically implausible records are outside this metric by design."],
    ),
)
def credit_card_tips():
    return tip_amount_value.sum(time=picked_up_at_value).where(CREDIT_CARD & PLAUSIBLE)


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Metered fare revenue per technically plausible trip.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def average_fare():
    return plausible_fare_revenue / plausible_trip_count


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Taximeter-reported miles per technically plausible trip.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def average_trip_distance():
    return plausible_total_trip_distance / plausible_trip_count


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Elapsed minutes per technically plausible trip.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def average_trip_duration():
    return plausible_total_trip_duration / plausible_trip_count


@ms.metric(
    ai_context=ms.ai_context(
        business_definition=(
            "Average driver-entered passenger count among technically plausible records that report it."
        ),
        guardrails=[
            "Pair with plausible_passenger_count_coverage; missing values are excluded, not treated as zero."
        ],
    ),
)
def average_passengers():
    return plausible_total_passengers / known_plausible_passenger_trip_count


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Share of published records with a reported passenger count.",
        guardrails=["Use with average_passengers to assess representativeness."],
    ),
)
def passenger_count_coverage():
    return known_passenger_trip_count / trip_count


@ms.metric(
    ai_context=ms.ai_context(
        business_definition=(
            "Share of technically plausible records with a reported passenger count."
        ),
        guardrails=["Use with average_passengers to assess its exact denominator coverage."],
    ),
)
def plausible_passenger_count_coverage():
    return known_plausible_passenger_trip_count / plausible_trip_count


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Automatically recorded tips divided by metered fare revenue.",
        guardrails=["Use credit_card_tip_rate for rider tipping behavior."],
    ),
)
def tip_rate():
    return tips / fare_revenue


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Recorded credit-card tips divided by credit-card metered fare revenue.",
        guardrails=["Represents recorded tips, not all rider gratuities."],
    ),
)
def credit_card_tip_rate():
    return credit_card_tips / credit_card_fare_revenue


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Share of published records paid by credit card.",
        guardrails=PUBLISHED_RECORD_GUARDRAILS,
    ),
)
def credit_card_trip_share():
    return credit_card_trip_count / trip_count


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Metered fare revenue per reported mile among plausible records.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def fare_per_mile():
    return plausible_fare_revenue / plausible_total_trip_distance


@ms.metric(
    ai_context=ms.ai_context(
        business_definition=(
            "Aggregate reported distance divided by aggregate elapsed hours among plausible records."
        ),
        guardrails=["The plausible subset caps record-level implied speed at 100 mph."],
    ),
)
def average_speed_mph():
    return plausible_total_trip_distance / plausible_total_trip_duration_hours


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Published rows failing at least one technical plausibility condition.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def implausible_trip_count():
    return trip_count - plausible_trip_count


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Share of published rows failing the technical plausibility predicate.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def implausible_record_rate():
    return implausible_trip_count / trip_count


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Count of rows whose pickup month differs from source-file month.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def pickup_time_mismatch_count():
    return trips.count(time=picked_up_at_value).where(pickup_time_matches_source_month_value == False)  # noqa: E712


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Count of rows whose drop-off is not after pickup.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def nonpositive_duration_count():
    return trips.count(time=picked_up_at_value).where(has_positive_duration_value == False)  # noqa: E712


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Count of rows with zero, negative, or missing reported distance.",
        guardrails=["Zero-distance records are review flags, not automatic proof of invalidity."],
    ),
)
def nonpositive_distance_count():
    return trips.count(time=picked_up_at_value).where(has_positive_distance_value == False)  # noqa: E712


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Count of rows with negative or missing metered fare.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def negative_fare_count():
    return trips.count(time=picked_up_at_value).where(has_nonnegative_fare_value == False)  # noqa: E712


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Count of rows with negative or missing total charge.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def negative_total_count():
    return trips.count(time=picked_up_at_value).where(has_nonnegative_total_value == False)  # noqa: E712


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Count of rows with a missing or out-of-range pickup zone ID.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def invalid_pickup_zone_count():
    return trips.count(time=picked_up_at_value).where(has_valid_pickup_zone_value == False)  # noqa: E712


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Count of rows with a missing or out-of-range drop-off zone ID.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def invalid_dropoff_zone_count():
    return trips.count(time=picked_up_at_value).where(has_valid_dropoff_zone_value == False)  # noqa: E712


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Share of rows whose pickup month differs from source-file month.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def pickup_time_mismatch_rate():
    return pickup_time_mismatch_count / trip_count


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Share of rows whose drop-off is not after pickup.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def nonpositive_duration_record_rate():
    return nonpositive_duration_count / trip_count


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Share of rows with nonpositive or missing reported distance.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def nonpositive_distance_record_rate():
    return nonpositive_distance_count / trip_count


@ms.metric(
    ai_context=ms.ai_context(
        business_definition="Share of rows with negative or missing metered fare.",
        guardrails=QUALITY_GUARDRAILS,
    ),
)
def negative_fare_record_rate():
    return negative_fare_count / trip_count
