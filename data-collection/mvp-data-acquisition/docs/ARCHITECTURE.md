# Architecture and Design Decisions

## Scope decision

GitHub Issue #1 describes a larger system from collection through classification
and dashboard delivery. This module proves the smallest dependable handoff:

```text
Scrapy -> raw snapshots -> Pydantic -> pandas -> Parquet -> DuckDB
```

Scrapy, one spider per company, shared validation, immutable snapshots, quality
gates, Parquet and DuckDB are implemented. Playwright, Prefect, title/skill
classification, LLM processing and presentation applications are deferred.

## Responsibility boundaries

| Component | Owns | Does not own |
|---|---|---|
| Company spider | Company name, board token and exceptional source settings | Generic ATS parsing or storage |
| ATS adapter | Mapping one platform response into the shared raw schema | Company selection or analytics |
| Validation pipeline | Pydantic validation and validated JSONL evidence | Cleaning or publication decisions |
| Source-status extension | Crawl counts, errors and finish status | Item transformation |
| Cleaning | Text normalisation, deduplication and history state | Network requests or classification |
| Quality module | Acceptance checks and a machine-readable report | Writing the accepted pointer |
| Storage | JSON, Parquet, DuckDB and atomic file operations | Crawl policy |
| Orchestration | Stage order, failure boundary and publication decision | Platform-specific field parsing |
| CLI | User arguments and final exit code | Business logic |

This is high cohesion in practical terms: each file has one reason to change.
It is low coupling because modules exchange typed job/status records or data
frames instead of reaching into one another's internal state.

## Spider structure

```text
spiders/base.py
  AtsApiSpider                    snapshot and common item helpers
      |
      +-- ats/ashby/base.py       Ashby response mapping
      |     +-- aurora.py         token + company only
      +-- ats/greenhouse/base.py  Greenhouse response mapping
      |     +-- kodiak.py
      +-- ats/lever/base.py       Lever response mapping
            +-- zoox.py
```

There is still one concrete spider class per company, so it can be enabled,
tested, reviewed or repaired independently. Shared platform code prevents the
same mapping logic being copied across many files.

## Run and snapshot semantics

Every execution receives a UTC `run_id`.

1. The unmodified response body and a checksum/URL/status metadata sidecar are
   saved under `data/raw`.
2. Every yielded job must pass the strict `RawJob` Pydantic model. Valid records
   are stored per company; validation problems are retained separately.
3. pandas removes duplicate `(company, source_job_id)` keys, normalises text,
   converts time values to UTC and merges the previous accepted history.
4. New jobs are active with matching `first_seen_utc` and `last_seen_utc`.
5. A job missing from a successfully refreshed source becomes inactive, but is
   retained for later trend analysis.
6. A company not selected in a partial refresh is carried forward unchanged.
7. Parquet is the stable downstream contract; DuckDB is rebuilt per run for
   convenient analysis.

The distinction between “not observed after a successful refresh” and “source
failed” is essential. A broken endpoint must not make all its vacancies appear
closed.

## Publication transaction

The workflow prepares all run-specific evidence before changing the accepted
pointer. Publication requires:

- every selected spider to finish, return at least one valid record and report
  no response/schema errors;
- nonblank company, source ID, advertised title, description and source URL;
- unique active `(company, source_job_id)` keys;
- successful Parquet writes;
- a DuckDB database that reopens with the expected row count.

Only then is `data/published/latest.json` written to a temporary file and
atomically replaced. Sampled runs and explicit `--no-publish` runs cannot publish.

This is not a distributed database transaction. It is a small local-file
publication protocol designed so readers either see the previous accepted run or
the new accepted run, not a half-built output.

## Downstream contract

Parquet, rather than scraped HTML or DuckDB, is the intended input to future
classification and dashboard stages. Future enrichments should add versioned
columns such as `generic_job_title`, `required_skills`, taxonomy/model version and
classification confidence without overwriting the original source fields.

DuckDB is a run-specific analytical build output. A dashboard can open the
accepted database read-only without sharing a mutable file with an active crawl.

## Known architectural limits

- Current adapters cover three public structured ATS families, not every career
  platform.
- A source can change format without notice; parser-contract tests reduce but do
  not eliminate that operational risk.
- Zero valid jobs is treated as failure because an empty real board cannot be
  distinguished safely from an upstream break in this MVP.
- The module records job availability observations, not application outcomes or
  the whole labour market.
