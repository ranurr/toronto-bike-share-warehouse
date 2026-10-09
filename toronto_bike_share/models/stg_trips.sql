-- Preserve one row per source record so every exclusion can be audited.
with parsed as (
    select source_row_number, source_row_hash,
        case when regexp_full_match(trim(Trip_Id), '[0-9]+(\.0+)?')
             then try_cast(Trip_Id as bigint) end as trip_id,
        case when regexp_full_match(trim(Start_Station_Id), '[0-9]+(\.0+)?')
             then try_cast(Start_Station_Id as bigint) end as start_station_id,
        case when regexp_full_match(trim(End_Station_Id), '[0-9]+(\.0+)?')
             then try_cast(End_Station_Id as bigint) end as end_station_id,
        try_strptime(Start_Time, '%Y-%m-%d %H:%M:%S') as started_at,
        try_strptime(End_Time, '%Y-%m-%d %H:%M:%S') as ended_at,
        try_cast(Trip_Duration as decimal(18,3)) as duration_seconds,
        nullif(trim(Start_Station_Name), '') as start_station_name,
        nullif(trim(End_Station_Name), '') as end_station_name,
        nullif(trim(Bike_Id), '') as bike_id,
        coalesce(nullif(trim(User_Type), ''), 'Unknown') as rider_type,
        coalesce(nullif(trim(Bike_Model), ''), 'Unknown') as bike_model
    from {{ source('raw', 'trips') }}
), duplicates as (
    select *,
        row_number() over (partition by trip_id order by source_row_number) as occurrence,
        count(distinct source_row_hash) over (partition by trip_id) as payload_versions
    from parsed
)
select *,
    case
        when trip_id is null then 'missing_or_invalid_trip_id'
        when payload_versions > 1 then 'conflicting_duplicate_id'
        when occurrence > 1 then 'repeated_identical_trip'
        when started_at is null or ended_at is null then 'invalid_timestamp'
        when cast(started_at as date) < date '2026-01-01'
          or cast(started_at as date) >= date '2026-04-01' then 'outside_snapshot_period'
        when start_station_id is null or end_station_id is null then 'missing_or_invalid_station_id'
        when duration_seconds is null or not isfinite(duration_seconds)
          or duration_seconds <= 0 then 'invalid_duration'
        when ended_at < started_at then 'end_before_start'
        when abs(date_diff('second', started_at, ended_at) - duration_seconds) > 1
          then 'duration_timestamp_mismatch'
        else null
    end as rejection_reason,
    duration_seconds > 14400 as is_long_trip
from duplicates
