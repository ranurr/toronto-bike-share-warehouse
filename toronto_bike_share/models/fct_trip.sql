select trip_id, start_station_id, end_station_id, started_at, ended_at,
    cast(started_at as date) as trip_date,
    extract(hour from started_at)::integer as start_hour,
    extract(isodow from started_at)::integer as weekday_number,
    extract(isodow from started_at) in (6, 7) as is_weekend,
    duration_seconds, cast(duration_seconds / 60.0 as decimal(20,6)) as duration_minutes,
    rider_type, bike_model, bike_id, is_long_trip, source_row_number
from {{ ref('stg_trips') }}
where rejection_reason is null
