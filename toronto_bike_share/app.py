"""A small local dashboard. Run the pipeline before starting this app."""
import json
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'warehouse/bike_share.duckdb'
st.set_page_config(page_title='Toronto Bike Share | Q1 2026', page_icon='🚲', layout='wide')
st.title('Toronto Bike Share')
st.caption('Trip patterns and station activity · January–March 2026 · Toronto Open Data')
if not DB.exists():
    st.info('Build the local warehouse first: python run.py')
    st.stop()


@st.cache_data(show_spinner=False)
def query(sql, params, revision):
    # revision is the database modification time; rebuilding invalidates cached results.
    with duckdb.connect(str(DB), read_only=True) as con:
        return con.execute(sql, params).df()


revision = DB.stat().st_mtime_ns
page = st.sidebar.radio('Page', ['Ridership trends', 'Station activity', 'Data quality'])
if page == 'Data quality':
    quality = query('''select count(*) as source_rows,
        count(*) filter(where rejection_reason is null) as accepted,
        count(*) filter(where rejection_reason is not null) as excluded from stg_trips''', [], revision).iloc[0]
    a,b,c = st.columns(3)
    a.metric('Source records', f'{int(quality.source_rows):,}')
    b.metric('Accepted trips', f'{int(quality.accepted):,}')
    c.metric('Excluded records', f'{int(quality.excluded):,}')
    st.subheader('Exclusions in the complete snapshot')
    st.dataframe(query('''select rejection_reason as reason, count(*) as records from stg_trips
        where rejection_reason is not null group by 1 order by records desc''', [], revision), hide_index=True)
    st.write('Every source row remains in staging. Each excluded row is assigned the first failing rule. '
             'Trip IDs are deduplicated; conflicting duplicate IDs are excluded in full. '
             'Trips over four hours remain included and are flagged.')
    st.write('Duration must agree with elapsed source timestamps within one second. Source timestamps '
             'have no UTC offsets, so daylight-saving ambiguity is a limitation of this check.')
    st.subheader('Source and scope')
    provenance = json.loads((ROOT/'data/provenance.json').read_text())
    st.json(provenance, expanded=False)
    st.caption('Build results and test logs are saved in the reports folder.')
    st.stop()

bounds = query('select min(trip_date) as first_day, max(trip_date) as last_day from fct_trip', [], revision).iloc[0]
start, end = pd.Timestamp(bounds.first_day).date(), pd.Timestamp(bounds.last_day).date()
dates = st.sidebar.date_input('Trip start dates', value=(start,end), min_value=start, max_value=end)
if len(dates) != 2:
    st.info('Choose a start and end date.')
    st.stop()
riders = query('select distinct rider_type from fct_trip order by 1', [], revision).rider_type.tolist()
bikes = query('select distinct bike_model from fct_trip order by 1', [], revision).bike_model.tolist()
rider = st.sidebar.selectbox('Rider category', ['All'] + riders)
bike = st.sidebar.selectbox('Bike model', ['All'] + bikes)
where = 'trip_date between ? and ?'
params = [dates[0], dates[1]]
if rider != 'All':
    where += ' and rider_type = ?'
    params.append(rider)
if bike != 'All':
    where += ' and bike_model = ?'
    params.append(bike)
summary = query(f'''select count(*) as trips, median(duration_minutes) as median_minutes,
    count(*) filter(where is_long_trip) as long_trips from fct_trip where {where}''', params, revision).iloc[0]
if summary.trips == 0:
    st.info('No accepted trips match these filters. Try a wider date range or another category.')
    st.stop()
a,b,c = st.columns(3)
a.metric('Accepted trips', f'{int(summary.trips):,}')
b.metric('Median trip', f'{summary.median_minutes:.1f} min')
c.metric('Trips over 4 hours', f'{int(summary.long_trips):,}')

if page == 'Ridership trends':
    daily = query(f'''select trip_date, count(*) as trips from fct_trip where {where}
        group by 1 order by 1''', params, revision)
    calendar = pd.DataFrame({'trip_date':pd.date_range(dates[0],dates[1])})
    daily = calendar.merge(daily,on='trip_date',how='left').fillna({'trips':0})
    daily['trips'] = daily.trips.astype(int)
    st.subheader('Trips by start date')
    st.line_chart(daily.set_index('trip_date').trips, color='#287477')
    left,right = st.columns(2)
    with left:
        st.subheader('Rider categories')
        data = query(f'''select rider_type, count(*) as trips from fct_trip where {where}
            group by 1 order by trips desc''', params, revision)
        st.bar_chart(data.set_index('rider_type').trips,color='#287477')
    with right:
        st.subheader('Bike models')
        data = query(f'''select bike_model, count(*) as trips from fct_trip where {where}
            group by 1 order by trips desc''', params, revision)
        st.bar_chart(data.set_index('bike_model').trips,color='#bb8042')
    st.download_button('Download filtered daily counts',daily.to_csv(index=False),'daily_trips.csv','text/csv')
    st.caption('Daily counts reconcile to the accepted-trip total above. Source model labels are '
               'retained as published. This winter quarter should not be treated as a whole-year pattern.')
else:
    st.subheader('Station activity for the selected trips')
    hours = st.slider('Event hours (inclusive)',0,23,(0,23))
    station_params = params + [hours[0],hours[1]]
    data = query(f'''with selected as (select * from fct_trip where {where}), events as (
        select start_station_id as station_id, started_at as event_at, 1 as departures, 0 as arrivals from selected
        union all
        select end_station_id, ended_at, 0, 1 from selected
    ) select s.station_id, s.station_name,
        sum(e.departures)::bigint as departures, sum(e.arrivals)::bigint as arrivals,
        (sum(e.departures)-sum(e.arrivals))::bigint as net_departures
        from events e join dim_station s using(station_id)
        where extract(hour from event_at) between ? and ?
        group by 1,2 order by departures desc, station_id''',station_params,revision)
    if data.empty:
        st.info('No station events match the selected hours.')
        st.stop()
    top_n = st.slider('Stations to show',5,30,10)
    st.bar_chart(data.head(top_n).set_index('station_name')[['departures','arrivals']],horizontal=True)
    st.dataframe(data,hide_index=True,width='stretch')
    st.download_button('Download station activity',data.to_csv(index=False),'station_activity.csv','text/csv')
    st.caption('Net departures = departures minus arrivals. Positive means more departures were observed. '
               'It does not measure stockouts or unmet demand. Date filters select trips by start date; '
               'their arrivals can fall after the selected end date. Hour filters use each event’s own hour. '
               'Station names are the latest nonempty names observed in this snapshot.')

st.markdown('[Source: Toronto Open Data](https://open.toronto.ca/dataset/bike-share-toronto-ridership-data/)')
st.caption('Contains information licensed under the Open Government Licence – Toronto.')
