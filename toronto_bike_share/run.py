"""Build the local database and optionally compare two runs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

import duckdb
from scripts.ingest import ingest
from scripts.report import write_report

ROOT = Path(__file__).resolve().parent
DB = Path(os.environ.get('BIKE_DB_PATH', ROOT / 'warehouse/bike_share.duckdb'))
TABLES = ['raw.trips','stg_trips','dim_station','fct_trip','mart_daily_ridership','mart_station_hour']


def fingerprints(database=DB):
    with duckdb.connect(str(database), read_only=True) as con:
        return {table: list(con.execute(f'''select count(*), bit_xor(hash(t))::varchar,
            sum(hash(t)::hugeint)::varchar from {table} t''').fetchone()) for table in TABLES}


def build(database=DB, log_name='dbt_build.log'):
    ingest(database)
    env = dict(os.environ, BIKE_DB_PATH=str(database), DBT_SEND_ANONYMOUS_USAGE_STATS='false')
    result = subprocess.run([sys.executable, '-c', 'from dbt.cli.main import cli; cli()',
        'build', '--project-dir', str(ROOT), '--profiles-dir', str(ROOT),
        '--no-use-colors'], cwd=ROOT, env=env, text=True, capture_output=True)
    output = result.stdout + result.stderr
    (ROOT / 'reports' / log_name).write_text(output)
    if result.returncode:
        raise RuntimeError(f'dbt failed; see reports/{log_name}\n{output[-5000:]}')
    print(output[-1100:])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-rerun', action='store_true')
    args = parser.parse_args()
    (ROOT/'reports').mkdir(exist_ok=True)
    build()
    first = fingerprints()
    evidence = {'run_at_utc':datetime.now(timezone.utc).isoformat(),
                'python_version':sys.version.split()[0], 'fingerprints':first,
                'rerun_checked':False, 'rerun_identical':None}
    if args.check_rerun:
        build(log_name='dbt_rerun.log')
        second = fingerprints()
        evidence.update(rerun_checked=True, rerun_identical=first==second,
                        rerun_fingerprints=second)
        if first != second:
            raise AssertionError('Rerun changed table counts or row-content checksums')
        print('Rerun produced identical counts and row-content checksums for all six tables.')
    quality = write_report(DB)
    evidence['quality'] = quality
    (ROOT/'reports/run_evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print('Done. Open reports/findings.md or run: python -m streamlit run app.py')


if __name__ == '__main__':
    main()
