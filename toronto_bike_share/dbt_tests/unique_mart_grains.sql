select 'daily' as model from {{ ref('mart_daily_ridership') }}
group by trip_date, rider_type, bike_model having count(*) > 1
union all
select 'station_hour' from {{ ref('mart_station_hour') }}
group by station_id, event_hour, rider_type, bike_model having count(*) > 1
