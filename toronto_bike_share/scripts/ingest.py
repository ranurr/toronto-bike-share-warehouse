"""Load a verified source snapshot. Reruns replace raw tables instead of appending."""
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
COLUMNS = ['Trip_Id', 'Trip_Duration', 'Start_Station_Id', 'Start_Time',
           'Start_Station_Name', 'End_Station_Id', 'End_Time', 'End_Station_Name',
           'Bike_Id', 'User_Type', 'Bike_Model']


def load_csv(csv_path, database):
    """Also used by explicitly synthetic test fixtures; column drift fails loudly."""
    con = duckdb.connect(str(database))
    try:
        con.execute('BEGIN')
        con.execute('CREATE SCHEMA IF NOT EXISTS raw')
        con.read_csv(str(csv_path), all_varchar=True, header=True, parallel=False).create_view('input_csv')
        found = [row[0] for row in con.execute('DESCRIBE input_csv').fetchall()]
        if found != COLUMNS:
            raise ValueError(f'Source columns changed: {found}')
        con.execute('''CREATE OR REPLACE TABLE raw.trips AS
            SELECT row_number() OVER () AS source_row_number,
                   md5(to_json(input_csv)) AS source_row_hash, * FROM input_csv''')
        count = con.execute('SELECT count(*) FROM raw.trips').fetchone()[0]
        con.execute('COMMIT')
        return count
    except Exception:
        con.execute('ROLLBACK')
        raise
    finally:
        con.close()


def ingest(database=None):
    database = Path(database or ROOT / 'warehouse/bike_share.duckdb')
    database.parent.mkdir(parents=True, exist_ok=True)
    meta = json.loads((ROOT / 'data/provenance.json').read_text())
    archive = ROOT / meta['cached_file']
    if hashlib.sha256(archive.read_bytes()).hexdigest() != meta['archive_sha256']:
        raise ValueError('Cached ZIP checksum does not match provenance.json')
    with zipfile.ZipFile(archive) as z, tempfile.TemporaryDirectory() as temp:
        payload = z.read(meta['archive_member'])
        if hashlib.sha256(payload).hexdigest() != meta['csv_sha256']:
            raise ValueError('CSV checksum does not match provenance.json')
        csv_path = Path(temp) / 'trips.csv'
        csv_path.write_bytes(payload)
        count = load_csv(csv_path, database)
    print(f'Loaded {count:,} raw rows from the verified real-data snapshot.')
    return count


if __name__ == '__main__':
    ingest()
