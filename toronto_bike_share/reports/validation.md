# Validation of the included snapshot

Rerun locally on October 8, 2026 after the documentation and chart-label updates, using
Python 3.14.7 and the versions pinned in `requirements.txt`. The source is the cached
official Toronto download; synthetic records are used only in tests.

The refreshed run timestamp is `2026-10-09T00:39:13.259448+00:00` (October 8 in Toronto).
All six table fingerprints still match the previous saved build.

- `python run.py --check-rerun`: two full builds succeeded. Each ran five SQL/dbt models
  and 15 dbt data tests. `reports/dbt_build.log` and `reports/dbt_rerun.log` preserve the output.
- All six tables had identical row counts, XOR row hashes and summed row hashes across
  the two builds. The saved values are in `reports/run_evidence.json`.
- `python -m pytest -q`: **6 passed in 2.79 seconds**. Tests exercise synthetic invalid records, exact
  and conflicting duplicates, schema drift with rollback, station naming, blank categories,
  long trips and real-data reconciliation.
- The Streamlit AppTest loads all three views, selects January and a rider category,
  checks the displayed count against SQL, verifies station departures and arrivals match
  the same trip cohort, and exercises the morning-hour filter without an exception.
- `reports/ridership.png` was inspected after regenerating it; labels and layout are readable.

Actual data reconciliation:

| Measure | Count |
|---|---:|
| Source rows | 552,073 |
| Accepted unique trips | 550,146 |
| Excluded rows | 1,927 |
| Station IDs represented | 1,025 |
| All-time station departures from the accepted cohort | 550,146 |
| All-time station arrivals from the accepted cohort | 550,146 |
| Sum of station net departures | 0 |

The GitHub Actions file is supplied for future runs; no GitHub-hosted run was performed.
Tests validate this snapshot and the stated rules, not the truth of every publisher record.
