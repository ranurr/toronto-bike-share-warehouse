-- Latest name observed within this snapshot, not a historical location dimension.
with observations as (
    select start_station_id as station_id, start_station_name as station_name,
           started_at as observed_at, source_row_number
    from {{ ref('stg_trips') }} where rejection_reason is null
    union all
    select end_station_id, end_station_name, ended_at, source_row_number
    from {{ ref('stg_trips') }} where rejection_reason is null
), ranked as (
    select *, row_number() over (
        partition by station_id order by (station_name is null), observed_at desc,
        source_row_number desc, station_name
    ) as name_rank,
    count(distinct station_name) over (partition by station_id) as observed_name_count
    from observations
)
select station_id, coalesce(station_name, 'Unnamed station') as station_name,
       observed_at as latest_named_observation, observed_name_count
from ranked where name_rank = 1
