-- An arrival belongs to its end hour, including April 1 for March 31 departures.
with events as (
    select start_station_id as station_id, date_trunc('hour', started_at) as event_hour,
           rider_type, bike_model, 1 as departures, 0 as arrivals
    from {{ ref('fct_trip') }}
    union all
    select end_station_id, date_trunc('hour', ended_at), rider_type, bike_model, 0, 1
    from {{ ref('fct_trip') }}
)
select station_id, event_hour, rider_type, bike_model,
    sum(departures) as departures, sum(arrivals) as arrivals,
    sum(departures) - sum(arrivals) as net_departures
from events group by all
