# Contributing

## Workflow

1. Create a descriptive branch from the latest `main`.
2. Keep each change focused; do not combine generated data or unrelated report
   edits with scraper code.
3. Update tests and documentation with behaviour changes.
4. Run all offline checks before requesting review.
5. Use a pull request; explain scope, evidence, verification and known limits.

## Required checks

```powershell
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\scrapy check
```

A live sampled crawl is useful but is not a substitute for offline tests because
external sources can change or be temporarily unavailable.

## Commit and PR checklist

- [ ] One company spider per source; common platform mapping is not duplicated.
- [ ] Parser/history/publication behaviour has offline test coverage.
- [ ] Data fields and source coverage are documented.
- [ ] No secrets, `.venv`, generated snapshots, Parquet or DuckDB files included.
- [ ] Collection respects the documented ethical and access boundary.
- [ ] Client requirements, team proposals and future work are clearly separated.
