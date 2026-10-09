# Data dictionary

## Source and staging

The raw table is `raw.trips`. All eleven source fields are ingested as text, including
IDs that look numeric. `source_row_number` records CSV order; `source_row_hash` hashes
the complete source row. No source columns are silently removed or renamed during load.

| Raw column | Staging column | Meaning and treatment |
|---|---|---|
| `Trip_Id` | `trip_id` | Integer trip ID; required; duplicate handling described below |
| `Trip_Duration` | `duration_seconds` | Published seconds, cast to DECIMAL(18,3); positive and finite |
| `Start_Station_Id` | `start_station_id` | Integer ID; strings such as `7006.0` accepted; `7006.5` rejected |
| `Start_Time` | `started_at` | Parsed as `%Y-%m-%d %H:%M:%S`; no timezone offset supplied |
| `Start_Station_Name` | `start_station_name` | Whitespace trimmed; blank becomes null |
| `End_Station_Id` | `end_station_id` | Same integer rule as the start station |
| `End_Time` | `ended_at` | Same timestamp format; may be outside the start-date period |
| `End_Station_Name` | `end_station_name` | Whitespace trimmed; blank becomes null |
| `Bike_Id` | `bike_id` | Source identifier retained as text; not a person identifier |
| `User_Type` | `rider_type` | Published label; blank becomes `Unknown` |
| `Bike_Model` | `bike_model` | Published model label; blank becomes `Unknown` |

`stg_trips` has one row per raw record. It adds:

- `occurrence`: order among records with the same parsed trip ID.
- `payload_versions`: number of distinct raw-row payload hashes for that ID.
- `rejection_reason`: first applicable exclusion rule, or null when accepted.
- `is_long_trip`: true for a duration over 14,400 seconds; this is a flag, not a rejection.

Exclusion priority is invalid trip ID; conflicting duplicate ID; repeated identical
record; invalid timestamp; start date outside the snapshot; invalid station ID; invalid
duration; end before start; duration/timestamp mismatch. An exact repeated row keeps
its first occurrence. Conflicting records sharing a trip ID are all excluded. The
counts in `reports/excluded_rows.csv` are mutually exclusive because of that priority.

## Dimensions and fact

| Table | Grain | Key | Useful fields |
|---|---|---|---|
| `dim_station` | One station ID seen in accepted trips | `station_id` | `station_name`, `latest_named_observation`, `observed_name_count` |
| `fct_trip` | One accepted unique trip | `trip_id` | Start/end station IDs, timestamps, duration, categories, `source_row_number` |

Station names use the latest nonempty observation, breaking ties with source row number
and then name. IDs with no nonempty name use `Unnamed station`. This is a display rule,
not a slowly changing dimension or a claim that the station had that name throughout.
`latest_named_observation` is the timestamp of the selected label observation; when all
names are blank it is the latest station event. `observed_name_count` excludes null names.

Fact `trip_date` is the local-looking source start date; `start_hour` is 0–23;
`weekday_number` uses Monday=1 through Sunday=7. `is_weekend` means Saturday/Sunday and
does not classify holidays. `duration_minutes` is seconds/60 rounded to six decimal
places in an exact decimal type. This avoids unstable floating sums on repeated builds.

## Reporting tables

| Table | Grain | Measures |
|---|---|---|
| `mart_daily_ridership` | Start date × rider type × bike model | `trips`, `total_duration_minutes`, `average_duration_minutes`, `median_duration_minutes` |
| `mart_station_hour` | Station ID × event hour × rider type × bike model | `departures`, `arrivals`, `net_departures` |

Each accepted trip contributes one departure and one arrival. `event_hour` is truncated
to the beginning of the source timestamp's hour. `net_departures = departures - arrivals`;
a positive value means more observed departures. Empty station-hour/category combinations
are not materialized. Daily dashboard charts fill absent dates with zero for display.

Totals add across dates/categories. Averages need their trip weights, and medians do not
add: query the trip fact for a combined median. The dashboard follows that rule.

## Test data and validation

Synthetic records are generated in a temporary directory by `tests/test_pipeline.py`.
They cover repeated and conflicting trip IDs, broken dates, fractional station IDs,
missing station IDs, mismatched durations, long trips, renamed stations, blank categories
and schema drift. Their database is temporary and never used in the report.

The real-data dbt tests check unique/non-null keys, both station relationships, valid
facts, unique mart grains, and the identity:

`raw rows = accepted trips + excluded rows = staged rows`

`accepted trips = daily trip sum = station departures = station arrivals`

Across the complete cohort, station net departures must sum to zero.
