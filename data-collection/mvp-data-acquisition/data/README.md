# Committed Data Snapshot

This directory contains the processed output of one complete, quality-gated run.

| Property | Value |
|---|---|
| Run ID | `20260822T050023Z` |
| Collected | 22 August 2026 at 05:00 UTC |
| Sources | 16/16 successful |
| Active jobs | 1,429 |
| Duplicate active source keys | 0 |
| Missing required title/URL fields | 0 |

Committed artifacts:

- `processed/run_id=20260822T050023Z/jobs.parquet`: the documented job dataset;
- `processed/run_id=20260822T050023Z/source_status.parquet`: collection evidence;
- `published/latest.json`: repository-relative pointer to the accepted snapshot;
- `../output/run_id=20260822T050023Z/av_jobs.duckdb`: query-ready database;
- the same output directory's analysis, quality, issue and run summaries.

Raw responses and intermediate validated JSONL are not committed. They duplicate
source job text, increase the public repository size, and can be reproduced by
running the documented pipeline. Their omission does not remove fields from the
processed Parquet or DuckDB dataset.

This is a point-in-time engineering dataset from the public ATS boards listed in
`../docs/SOURCES.md`. It is not a representative census of all AV employment and
does not imply that every company is client-approved final scope.
