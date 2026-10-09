"""Write the findings, chart and CSV summaries from the database."""
import json
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]


def write_report(database):
    out = ROOT / 'reports'
    out.mkdir(exist_ok=True)
    con = duckdb.connect(str(database), read_only=True)
    scalar = lambda query: con.execute(query).fetchone()[0]
    raw = scalar('select count(*) from raw.trips')
    accepted = scalar('select count(*) from fct_trip')
    stations = scalar('select count(*) from dim_station')
    excluded = con.execute('''select rejection_reason, count(*) as rows from stg_trips
        where rejection_reason is not null group by 1 order by 2 desc''').df()
    monthly = con.execute('''select strftime(trip_date, '%Y-%m') as month,
        count(*) as trips, round(median(duration_minutes), 2) as median_minutes
        from fct_trip group by 1 order by 1''').df()
    riders = con.execute('''select rider_type, count(*) as trips,
        round(100.0 * count(*) / sum(count(*)) over(), 2) as share_percent
        from fct_trip group by 1 order by trips desc''').df()
    bike_models = con.execute('''select bike_model, count(*) as trips from fct_trip
        group by 1 order by trips desc''').df()
    # Average per calendar day: weekends have fewer days than weekdays.
    hourly = con.execute('''with days as (
        select cast(d as date) as d, extract(isodow from d) in (6, 7) as is_weekend
        from generate_series(date '2026-01-01', date '2026-03-31', interval '1 day') t(d)
    ), day_counts as (select is_weekend, count(*) as days from days group by 1)
    select f.start_hour, case when f.is_weekend then 'Weekend' else 'Weekday' end as day_type,
           count(*)::double / d.days as average_trips_per_day
    from fct_trip f join day_counts d using(is_weekend) group by f.start_hour, f.is_weekend, d.days order by 1, 2''').df()
    busiest = con.execute('''select s.station_name, t.station_id, sum(t.departures) as departures,
        sum(t.arrivals) as arrivals, sum(t.net_departures) as net_departures
        from mart_station_hour t join dim_station s using(station_id)
        group by 1, 2 order by departures desc, station_id limit 10''').df()
    morning = con.execute('''select s.station_name, t.station_id,
        sum(t.departures) as departures, sum(t.arrivals) as arrivals,
        sum(t.net_departures) as net_departures
        from mart_station_hour t join dim_station s using(station_id)
        where extract(isodow from t.event_hour) between 1 and 5
          and extract(hour from t.event_hour) >= 7 and extract(hour from t.event_hour) < 10
          and t.event_hour >= timestamp '2026-01-01' and t.event_hour < timestamp '2026-04-01'
        group by 1, 2 order by net_departures desc, station_id limit 10''').df()
    long_trips = scalar('select count(*) from fct_trip where is_long_trip')
    median = scalar('select median(duration_minutes) from fct_trip')
    max_end = str(scalar('select max(ended_at) from fct_trip'))
    duration_mismatch = scalar('''select count(*) from stg_trips where started_at is not null
        and ended_at is not null and abs(date_diff('second', started_at, ended_at)-duration_seconds)>1''')
    for name, data in [('monthly_ridership', monthly), ('rider_mix', riders), ('bike_models', bike_models),
                       ('hourly_pattern', hourly), ('busiest_stations', busiest),
                       ('morning_net_departures', morning), ('excluded_rows', excluded)]:
        data.to_csv(out / f'{name}.csv', index=False)
    quality = {'source_rows':raw, 'accepted_trips':accepted, 'excluded_rows':raw-accepted,
        'station_ids':stations, 'long_trips_over_4_hours_retained':long_trips,
        'duration_timestamp_mismatch_rows_before_other_filters':duration_mismatch,
        'latest_accepted_arrival':max_end,
        'rejection_reasons':excluded.to_dict(orient='records')}
    (out/'quality.json').write_text(json.dumps(quality,indent=2)+'\n')
    fig, axes = plt.subplots(1,2,figsize=(11,4.2))
    axes[0].bar(monthly['month'], monthly['trips']/1000, color='#2f6f71')
    axes[0].set(ylabel='Accepted trips (thousands)', title='Trips by month')
    for day, group in hourly.groupby('day_type'):
        axes[1].plot(group['start_hour'],group['average_trips_per_day'], label=day, linewidth=2)
    axes[1].set(xlabel='Start hour (source local time)',ylabel='Trips per calendar day',
                title='Average trips by start hour', xticks=[0,6,12,18,23])
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.spines[['top','right']].set_visible(False)
        ax.grid(axis='y',alpha=.18)
    fig.suptitle('Toronto Bike Share | January–March 2026', x=.06, ha='left', fontsize=15)
    fig.tight_layout()
    fig.savefig(out/'ridership.png',dpi=150, bbox_inches='tight')
    plt.close(fig)
    top = busiest.iloc[0]
    am = morning.iloc[0]
    reason_lines = '\n'.join(f'- {r.rejection_reason}: {r.rows:,} rows.' for r in excluded.itertuples()) or '- No excluded rows.'
    month_lines = '\n'.join(f'| {r.month} | {r.trips:,} | {r.median_minutes:.2f} |' for r in monthly.itertuples())
    peak = hourly[hourly.day_type=='Weekday'].sort_values('average_trips_per_day',ascending=False).iloc[0]
    memo = f'''# Toronto Bike Share: January–March 2026

The cleaned dataset contains **{accepted:,} trips** across **{stations:,} station IDs**.
The median trip lasted **{median:.2f} minutes**. These results use the complete
January–March archive retrieved from Toronto Open Data on October 8, 2026.

## Ridership

| Start month | Accepted trips | Median minutes |
|---|---:|---:|
{month_lines}

Weekday trips peaked at **{int(peak.start_hour):02d}:00**, averaging
**{peak.average_trips_per_day:,.1f} starts** in that hour per weekday. Each hourly average
uses the number of weekdays or weekend days in the quarter, including days with no trips.
Holidays are counted by their day of the week.

![Monthly trips and hourly pattern](ridership.png)

## Station activity

**{top.station_name}** (station {int(top.station_id)}) had the most departures:
**{int(top.departures):,}**, with **{int(top.arrivals):,} arrivals** among the accepted trips.

During weekday mornings (07:00–09:59), **{am.station_name}**
(station {int(am.station_id)}) had the largest net departure count: **{int(am.net_departures):,}**
({int(am.departures):,} departures minus {int(am.arrivals):,} arrivals).
Availability data would help check whether this station was short of bikes during those
hours. The trip records alone cannot show empty stations or unmet demand.

## Cleaning the data

Of **{raw:,} source records**, **{raw-accepted:,}** were excluded:

{reason_lines}

There were **{duration_mismatch:,} rows** where the published duration differed from the
elapsed timestamps by more than one second, before other filters. The timestamps have
no UTC offsets, so daylight-saving changes may explain some disagreements. These rows
remain excluded until the source timezone conventions can be confirmed. The one-second
tolerance is a project rule.

Trips over four hours were kept and flagged (**{long_trips:,} accepted trips**). The median
is less affected by unusually long trips than the mean. Excluded rows remain in
`stg_trips`, with the first failing rule recorded in `rejection_reason`.

## Limits

January–March does not cover summer riding. Weather, station capacity and availability
are not included. Station names use their latest nonempty value in this snapshot, so
the display name may differ from the name used earlier in the quarter.

Daily totals use the trip start date. Station activity uses each event's own timestamp;
the latest accepted arrival is **{max_end}**. Trips starting before January 1 are outside
this dataset, even if they ended in January. Station balances near the quarter boundaries
therefore need care.

The next step is to compare morning net departures with station-availability snapshots.
Adding another quarter would also show whether the hourly patterns persist.

CSV summaries in this folder include monthly counts, rider categories, bike models,
hourly patterns and the top stations. Category labels are kept as published.

Source: [City of Toronto, Bike Share Toronto Ridership Data](https://open.toronto.ca/dataset/bike-share-toronto-ridership-data/).
Contains information licensed under the [Open Government Licence – Toronto](https://www.toronto.ca/city-government/data-research-maps/open-data/open-data-licence/).
The source URL, retrieval time and checksums are saved in `data/provenance.json`.
'''
    (out/'findings.md').write_text(memo)
    con.close()
    return quality
