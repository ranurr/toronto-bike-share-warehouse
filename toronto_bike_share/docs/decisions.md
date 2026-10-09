# Build notes

## Scope

The official 2026 archive retrieved on October 8, 2026 contains January through March.
It is about 16.5 MB compressed, so retaining the entire release was simpler and more
reproducible than sampling it. The report covers the actual file contents, even though
the archive's publication timestamp is much later than the last trip start date.

## Why these tools

Python handles the ZIP, checksums and load. DuckDB keeps setup local. dbt makes the SQL
model order and data tests explicit. Streamlit supplies a small filtering interface.

## Issues encountered and fixes

- End station IDs arrive as strings such as `7037.0`. Integer-like decimal strings are
  accepted, but genuinely fractional IDs are rejected rather than rounded.
- Raw records include missing end stations and timestamps. Those records are kept in
  staging and counted as exclusions instead of disappearing in an inner join.
- The first rerun comparison found tiny changes in floating-point duration aggregates.
  Storing seconds and per-trip minutes as decimals fixed repeated-build stability.
  The final evidence compares row counts, XOR of row hashes and sum of row hashes for
  all six tables. These are practical regression checks, not cryptographic proofs.
- Some March timestamp-duration disagreements are consistent with timezone ambiguity;
  the project does not infer UTC offsets absent from the source. Those records are
  excluded under the stated one-second consistency rule and remain available to inspect.
- An arrival at 00:05 after a 23:55 departure belongs to the next date/hour. The hourly
  mart records that actual event time. End-of-quarter arrivals remain in the cohort.

## Refresh behaviour

The raw snapshot is replaced in a database transaction. A failed header check rolls
back without replacing the previous raw table. dbt then rebuilds downstream tables.
A build failure stops the runner and leaves its log available; the whole multi-model
run is not a single transaction. The dashboard should be stopped before rebuilding.

Normal runs use the bundled ZIP. `python scripts/fetch_snapshot.py` can restore that
exact file while the publisher still serves it; it checks the saved SHA-256 before
replacing the cache. Loading a different quarter requires inspecting its columns and
coverage, updating the provenance entry, and changing the date bounds in staging and
the report script.

## Next small improvements

1. Add a second quarter with an explicit multi-file manifest and period parameters.
2. Inspect the source documentation for timezone conventions before adjusting DST rows.
3. Collect station availability snapshots and join them by time before attempting
   any empty-station analysis.
4. Add weather only if the question needs it; compare similar weekdays and seasons.
