# Sources and implementation references

Data sources and documentation consulted for the October 8, 2026 build.

- [City of Toronto — Bike Share Toronto Ridership Data](https://open.toronto.ca/dataset/bike-share-toronto-ridership-data/): official catalogue and publisher attribution.
- [Toronto CKAN package metadata](https://ckan0.cf.opendata.inter.prod-toronto.ca/api/3/action/package_show?id=bike-share-toronto-ridership-data): downloadable resources, IDs, sizes and timestamps.
- [Exact 2026 archive URL](https://opendata.toronto.ca/toronto.parking.authority/bike-share-toronto-ridership-data/bikeshare-ridership-2026.zip): real source bytes; retrieval and SHA-256 are in `data/provenance.json`. This URL may change its contents later.
- [Open Government Licence – Toronto](https://www.toronto.ca/city-government/data-research-maps/open-data/open-data-licence/): source-data terms and attribution.
- [DuckDB CSV documentation](https://duckdb.org/docs/stable/data/csv/overview): CSV ingestion and explicit schema handling.
- [dbt-duckdb adapter repository](https://github.com/duckdb/dbt-duckdb): supported local profile, persisted DuckDB database and adapter behaviour. This project uses the installed 1.11.0 adapter with dbt Core 1.12.5.
- [Streamlit App testing](https://docs.streamlit.io/develop/api-reference/app-testing): interactive app tests used to verify filter behaviour and totals.
- [UBC DSCI 310 project milestone](https://ubc-dsci.github.io/dsci-310-student/project/m2.html): an undergraduate reproducibility benchmark for modular code, public data, testing and documentation; not a claim that this is a UBC assignment.

Source files can be revised by the publisher. The bundled ZIP and provenance manifest
are the reference for reproducing the included findings.
