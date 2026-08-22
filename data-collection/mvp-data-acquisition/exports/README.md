# Team CSV Exports

Run `python export_jobs_csv.py` from the module directory to rebuild the CSV from
the DuckDB file referenced by `data/published/latest.json`.

The export is intended for simple sharing and inspection in Excel. Parquet and
DuckDB remain the authoritative datasets because they retain source identifiers,
URLs, locations, collection history and quality fields.
