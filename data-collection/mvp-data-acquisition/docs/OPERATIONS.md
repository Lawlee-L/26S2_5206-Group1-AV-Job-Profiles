# Operations Guide

## Install

Requirements: Python 3.11+, internet access for live collection, and enough disk
space for versioned source responses. From this module directory in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
```

The package is installed in editable mode, so local source changes are used
without reinstalling. No browser, login, API key or LLM subscription is needed.

## Choose a run type

List supported spider names:

```powershell
.\.venv\Scripts\python run_pipeline.py --list-spiders
```

Fast smoke test across every implemented source:

```powershell
.\.venv\Scripts\python run_pipeline.py --max-jobs 2
```

Targeted investigation without changing the accepted pointer:

```powershell
.\.venv\Scripts\python run_pipeline.py --spiders kodiak,latitude,zoox --no-publish
```

Full quality-gated collection and publication:

```powershell
.\.venv\Scripts\python run_pipeline.py
```

Useful options:

| Option | Effect |
|---|---|
| `--spiders a,b,c` | Run only named implemented spiders |
| `--max-jobs N` | Limit each source; automatically prevents publication |
| `--no-publish` | Verify outputs but keep `latest.json` unchanged |
| `--log-level DEBUG` | Show detailed Scrapy diagnostics |
| `--run-id VALUE` | Supply a deterministic ID for controlled testing |
| `--data-root PATH` / `--output-root PATH` | Redirect generated artifacts |

The process exits with code 0 for verified outputs and code 1 when collection or
quality gates fail. The final console output is also valid JSON for automation.

## Read the result

Start with `output/run_id=<RUN_ID>/run_summary.json`:

- `published`: a complete non-sampled run passed and updated `latest.json`;
- `verified_not_published`: outputs passed but publication was intentionally
  disabled;
- `failed` or `failed_quality_gate`: inspect `issues.json`,
  `quality_report.json` and individual files under `data/status`.

`duckdb_analysis.json` gives counts by company/platform, date range and quality
flags. To query the database in Python:

```python
import duckdb

with duckdb.connect("output/run_id=<RUN_ID>/av_jobs.duckdb", read_only=True) as db:
    print(db.sql("SELECT company, count(*) FROM active_jobs GROUP BY company"))
```

## Failure recovery

Do not delete or edit the previous published snapshot when a run fails. The
workflow intentionally leaves `data/published/latest.json` unchanged.

1. Open the failed run's `run_summary.json` and `issues.json`.
2. Check the affected company's status JSON for response, validation or empty
   result evidence.
3. Re-run only that spider with `--no-publish --log-level DEBUG`.
4. If the ATS format changed, update the shared platform adapter and its offline
   contract test; if only one company differs, override that company spider.
5. Run all verification commands, then perform a full run before publication.

Never “fix” an empty result by weakening required-field validation or manually
pointing `latest.json` at an unverified output.

## Common problems

| Symptom | Likely cause / action |
|---|---|
| Unknown spider error | Use the exact name shown by `--list-spiders` |
| HTTP 404 or zero jobs | Board token or career provider changed; recheck official public careers page |
| HTTP 429 | Rate limit; keep auto-throttle enabled and retry later |
| `robots.txt` denial | Do not bypass it; defer the source and review permission |
| Schema validation errors | Inspect the recorded source response; update mapping/tests, not stored evidence |
| Missing latest Parquet | Restore the accepted snapshot or perform a new full verified run |
| DuckDB file locked | Close programs using that run's database; each run writes a new file |

## Scheduled operation later

This MVP has no scheduler. A future scheduler should call the same CLI, retain
the exit code/run summary, alert on failure, and only let this workflow update
the accepted pointer. Scheduling must not duplicate publication logic.
