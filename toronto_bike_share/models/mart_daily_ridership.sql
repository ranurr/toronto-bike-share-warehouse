select trip_date, rider_type, bike_model, is_weekend,
       count(*) as trips,
       sum(duration_minutes) as total_duration_minutes,
       avg(duration_minutes) as average_duration_minutes,
       median(duration_minutes) as median_duration_minutes
from {{ ref('fct_trip') }}
group by all
