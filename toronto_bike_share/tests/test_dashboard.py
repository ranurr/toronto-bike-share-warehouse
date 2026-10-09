from datetime import date
from pathlib import Path

import duckdb
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_filters_and_station_reconciliation():
    app = AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    assert not app.exception
    assert app.title[0].value == 'Toronto Bike Share'
    chosen_rider = app.sidebar.selectbox[0].options[1]
    app.sidebar.selectbox[0].set_value(chosen_rider)
    app.sidebar.date_input[0].set_value((date(2026,1,1),date(2026,1,31)))
    app.run()
    assert not app.exception
    with duckdb.connect(str(ROOT/'warehouse/bike_share.duckdb'),read_only=True) as con:
        expected = con.execute('''select count(*) from fct_trip where trip_date between
            date '2026-01-01' and date '2026-01-31' and rider_type=?''',[chosen_rider]).fetchone()[0]
    assert app.metric[0].value == f'{expected:,}'
    app.sidebar.radio[0].set_value('Station activity').run()
    assert not app.exception
    activity = app.dataframe[0].value
    assert activity.departures.sum() == expected
    assert activity.arrivals.sum() == expected
    assert activity.net_departures.sum() == 0
    app.slider[0].set_value((7,9)).run()
    assert not app.exception
    assert app.dataframe[0].value.departures.sum() <= expected
    app.sidebar.radio[0].set_value('Data quality').run()
    assert not app.exception
    assert app.metric[0].value == '552,073'
