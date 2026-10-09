"""Synthetic edge cases only. None of these rows enters the project report."""
import csv
import os
from pathlib import Path
import subprocess
import sys

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.ingest import COLUMNS, load_csv


def write_fixture(path, rows):
    with path.open('w',newline='') as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture(scope='module')
def sample_db(tmp_path_factory):
    temp = tmp_path_factory.mktemp('synthetic_bike_tests')
    base = dict(zip(COLUMNS, ['1','600','100','2026-01-02 08:00:00','First station',
                             '200.0','2026-01-02 08:10:00','Second station','9','Member','ICONIC']))
    rows = [base, dict(base)]
    rows += [dict(base,Trip_Id='2'), dict(base,Trip_Id='2',Start_Station_Name='Conflicting name')]
    rows += [dict(base,Trip_Id='3',Start_Time='not a timestamp'),
             dict(base,Trip_Id='4',Trip_Duration='-1'),
             dict(base,Trip_Id='5',End_Station_Id=''),
             dict(base,Trip_Id='6',End_Time='2026-01-02 07:00:00'),
             dict(base,Trip_Id='7',Trip_Duration='700'),
             dict(base,Trip_Id='8',Trip_Duration='18000',End_Time='2026-01-02 13:00:00'),
             dict(base,Trip_Id='bad'),
             dict(base,Trip_Id='10',Start_Time='2026-04-02 08:00:00',End_Time='2026-04-02 08:10:00'),
             dict(base,Trip_Id='11',End_Station_Id='200.5'),
             dict(base,Trip_Id='12',User_Type='',Bike_Model='',Start_Time='2026-01-03 08:00:00',
                  End_Time='2026-01-03 08:10:00',Start_Station_Name='First station renamed')]
    csv_path, db = temp/'synthetic.csv', temp/'test_bike.duckdb'
    write_fixture(csv_path,rows)
    assert load_csv(csv_path,db) == 14
    env = dict(os.environ, BIKE_DB_PATH=str(db), DBT_SEND_ANONYMOUS_USAGE_STATS='false')
    result = subprocess.run([sys.executable,'-c','from dbt.cli.main import cli; cli()',
        'build','--project-dir',str(ROOT),'--profiles-dir',str(ROOT),
        '--target-path',str(temp/'target'),'--log-path',str(temp/'logs')],
        env=env,cwd=ROOT,text=True,capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return db, csv_path


def test_bad_rows_are_accounted_for(sample_db):
    db,_ = sample_db
    with duckdb.connect(str(db),read_only=True) as con:
        actual = dict(con.execute('''select rejection_reason,count(*) from stg_trips
            where rejection_reason is not null group by 1''').fetchall())
        assert actual == {'repeated_identical_trip':1,'conflicting_duplicate_id':2,
            'invalid_timestamp':1,'invalid_duration':1,'missing_or_invalid_station_id':2,
            'end_before_start':1,'duration_timestamp_mismatch':1,
            'missing_or_invalid_trip_id':1,'outside_snapshot_period':1}
        assert con.execute('select count(*) from fct_trip').fetchone()[0] == 3
        assert con.execute('select count(*) from stg_trips').fetchone()[0] == 14


def test_long_trips_kept_and_blank_categories_labelled(sample_db):
    db,_ = sample_db
    with duckdb.connect(str(db),read_only=True) as con:
        assert con.execute('select trip_id from fct_trip where is_long_trip').fetchall() == [(8,)]
        assert con.execute('select rider_type,bike_model from fct_trip where trip_id=12').fetchone() == ('Unknown','Unknown')


def test_station_name_and_decimal_identifier_rule(sample_db):
    db,_ = sample_db
    with duckdb.connect(str(db),read_only=True) as con:
        assert con.execute('select station_name from dim_station where station_id=100').fetchone()[0] == 'First station renamed'
        assert con.execute('select count(*) from fct_trip where end_station_id=200').fetchone()[0] == 3
        assert con.execute('''select count(*) from fct_trip f join dim_station s
            on f.start_station_id=s.station_id join dim_station e on f.end_station_id=e.station_id''').fetchone()[0] == 3


def test_fixture_rerun_does_not_append_and_schema_drift_rolls_back(sample_db,tmp_path):
    db,csv_path = sample_db
    assert load_csv(csv_path,db) == 14
    assert load_csv(csv_path,db) == 14
    bad = tmp_path/'wrong_columns.csv'
    bad.write_text('unexpected\nvalue\n')
    with pytest.raises(ValueError,match='Source columns changed'):
        load_csv(bad,db)
    with duckdb.connect(str(db),read_only=True) as con:
        assert con.execute('select count(*) from raw.trips').fetchone()[0] == 14


def test_snapshot_report_reconciles():
    import json
    evidence = json.loads((ROOT/'reports/run_evidence.json').read_text())
    with duckdb.connect(str(ROOT/'warehouse/bike_share.duckdb'),read_only=True) as con:
        count = con.execute('select count(*) from fct_trip').fetchone()[0]
        assert count == evidence['quality']['accepted_trips']
        assert count == con.execute('select sum(trips) from mart_daily_ridership').fetchone()[0]
        assert con.execute('select sum(net_departures) from mart_station_hour').fetchone()[0] == 0
    assert evidence['rerun_identical'] is True
