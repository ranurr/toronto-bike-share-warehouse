"""Restore the exact cached source if Toronto still serves the same release."""
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    meta = json.loads((ROOT/'data/provenance.json').read_text())
    with urllib.request.urlopen(meta['archive_url'], timeout=90) as response:
        payload = response.read(50_000_001)
    if len(payload) > 50_000_000:
        raise ValueError('Download exceeded the project limit; inspect the new source release separately.')
    if hashlib.sha256(payload).hexdigest() != meta['archive_sha256']:
        raise ValueError('Toronto now serves different bytes. Kept the bundled snapshot untouched. '
                         'To add a new period, first review its schema and update provenance and period tests.')
    target = ROOT / meta['cached_file']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    print(f'Restored exact source snapshot: {target.name}')


if __name__ == '__main__':
    main()
