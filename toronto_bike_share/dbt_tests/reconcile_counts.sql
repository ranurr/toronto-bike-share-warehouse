with totals as (
    select (select count(*) from {{ source('raw', 'trips') }}) as raw_rows,
           (select count(*) from {{ ref('stg_trips') }}) as staged_rows,
           (select count(*) from {{ ref('fct_trip') }}) as accepted,
           (select count(*) from {{ ref('stg_trips') }} where rejection_reason is not null) as excluded,
           (select sum(trips) from {{ ref('mart_daily_ridership') }}) as daily_total,
           (select sum(departures) from {{ ref('mart_station_hour') }}) as departures,
           (select sum(arrivals) from {{ ref('mart_station_hour') }}) as arrivals,
           (select sum(net_departures) from {{ ref('mart_station_hour') }}) as net
)
select * from totals where raw_rows != staged_rows or raw_rows != accepted + excluded
    or accepted != daily_total or accepted != departures or accepted != arrivals or net != 0
