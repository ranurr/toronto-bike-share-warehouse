# Toronto Bike Share: January–March 2026

The cleaned dataset contains **550,146 trips** across **1,025 station IDs**.
The median trip lasted **9.72 minutes**. These results use the complete
January–March archive retrieved from Toronto Open Data on October 8, 2026.

## Ridership

| Start month | Accepted trips | Median minutes |
|---|---:|---:|
| 2026-01 | 136,925 | 9.52 |
| 2026-02 | 112,281 | 9.75 |
| 2026-03 | 300,940 | 9.78 |

Weekday trips peaked at **17:00**, averaging
**832.2 starts** in that hour per weekday. Each hourly average
uses the number of weekdays or weekend days in the quarter, including days with no trips.
Holidays are counted by their day of the week.

![Monthly trips and hourly pattern](ridership.png)

## Station activity

**Bay St / College St (East Side)** (station 7006) had the most departures:
**3,880**, with **3,740 arrivals** among the accepted trips.

During weekday mornings (07:00–09:59), **Bathurst St / Front St W**
(station 7682) had the largest net departure count: **531**
(620 departures minus 89 arrivals).
Availability data would help check whether this station was short of bikes during those
hours. The trip records alone cannot show empty stations or unmet demand.

## Cleaning the data

Of **552,073 source records**, **1,927** were excluded:

- missing_or_invalid_station_id: 1,177 rows.
- invalid_timestamp: 498 rows.
- invalid_duration: 220 rows.
- duration_timestamp_mismatch: 32 rows.

There were **32 rows** where the published duration differed from the
elapsed timestamps by more than one second, before other filters. The timestamps have
no UTC offsets, so daylight-saving changes may explain some disagreements. These rows
remain excluded until the source timezone conventions can be confirmed. The one-second
tolerance is a project rule.

Trips over four hours were kept and flagged (**215 accepted trips**). The median
is less affected by unusually long trips than the mean. Excluded rows remain in
`stg_trips`, with the first failing rule recorded in `rejection_reason`.

## Limits

January–March does not cover summer riding. Weather, station capacity and availability
are not included. Station names use their latest nonempty value in this snapshot, so
the display name may differ from the name used earlier in the quarter.

Daily totals use the trip start date. Station activity uses each event's own timestamp;
the latest accepted arrival is **2026-04-01 04:37:24**. Trips starting before January 1 are outside
this dataset, even if they ended in January. Station balances near the quarter boundaries
therefore need care.

The next step is to compare morning net departures with station-availability snapshots.
Adding another quarter would also show whether the hourly patterns persist.

CSV summaries in this folder include monthly counts, rider categories, bike models,
hourly patterns and the top stations. Category labels are kept as published.

Source: [City of Toronto, Bike Share Toronto Ridership Data](https://open.toronto.ca/dataset/bike-share-toronto-ridership-data/).
Contains information licensed under the [Open Government Licence – Toronto](https://www.toronto.ca/city-government/data-research-maps/open-data/open-data-licence/).
The source URL, retrieval time and checksums are saved in `data/provenance.json`.
