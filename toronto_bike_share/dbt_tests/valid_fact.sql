select * from {{ ref('fct_trip') }}
where started_at is null or ended_at is null or duration_seconds <= 0
   or not isfinite(duration_seconds) or ended_at < started_at
   or abs(date_diff('second', started_at, ended_at) - duration_seconds) > 1
   or trip_date < date '2026-01-01' or trip_date >= date '2026-04-01'
