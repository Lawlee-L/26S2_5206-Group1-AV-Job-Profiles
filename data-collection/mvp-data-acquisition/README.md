# AV Job Data Acquisition MVP

This module implements the collection-to-storage slice of the CITS5206 AV Job
Profiles project. It collects public job advertisements from 16 company career
boards, validates and cleans them, preserves auditable snapshots, and produces
versioned Parquet files plus a DuckDB database.

The boundary is intentional: this MVP proves that repeatable, quality-gated data
can reach storage. Title normalisation, skill extraction, AV classification, an
LLM, scheduling, the dashboard and the job-search website are later consumers of
the processed data contract—not hidden inside the spiders.

## What is implemented

```text
16 company spiders (one per company)
        |
        +-- Ashby adapter
        +-- Greenhouse adapter
        +-- Lever adapter
        v
immutable response + metadata snapshots
        v
Pydantic validation -> pandas cleaning and history merge
        v
jobs.parquet + source_status.parquet
        v
DuckDB tables/views and analysis summary
        v
atomic latest.json update only after all quality gates pass
```

The 16 current sources are 42dot, Aurora, Applied Intuition, Avride, Bot Auto,
Gatik, May Mobility, Kodiak, Latitude, Motional, Vay, XPeng US, Mobileye,
WeRide US, Woven by Toyota and Zoox. They use public structured ATS endpoints
that were verified on 20 August 2026. See the [source register](docs/SOURCES.md)
for exact coverage and its evidence boundary.

## Quick start

Python 3.11 or later is required. In Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python run_pipeline.py --list-spiders
.\.venv\Scripts\python run_pipeline.py --max-jobs 2
```

The last command is a safe sample run: it collects at most two jobs per company,
builds and verifies Parquet/DuckDB, but cannot replace the published `latest.json`
pointer. A full quality-gated run is:

```powershell
.\.venv\Scripts\python run_pipeline.py
```

No Playwright browser, API key, login or paid AI service is required for this
structured-source MVP. See the [operations guide](docs/OPERATIONS.md) for
selective runs, outputs, failure recovery and troubleshooting.

Generate the four-column CSV requested by the team from the accepted DuckDB:

```powershell
.\.venv\Scripts\python export_jobs_csv.py
```

The result is written to `exports/av_jobs_<RUN_ID>.csv` with the columns
`company`, `name`, `description` and `date_posted`. It contains active jobs only.

## Repository layout

```text
run_pipeline.py             thin command-line entry point
export_jobs_csv.py          DuckDB-to-team-CSV command-line entry point
src/av_jobs/
  orchestration.py          application workflow and publication boundary
  models.py                 strict shared Pydantic contracts
  pipelines.py              item validation and validated JSONL export
  cleaning.py               deterministic pandas cleaning and history merge
  quality.py                publication quality rules
  snapshots.py              unmodified response and metadata storage
  storage.py                Parquet, DuckDB and atomic manifest adapters
  exports.py                stable downstream CSV contract
  registry.py               explicit MVP source inventory
  extensions/               per-source completion evidence
  spiders/
    base.py                 behaviour common to structured ATS sources
    ats/<platform>/base.py   one mapper per ATS platform
    ats/<platform>/*.py      one small spider per company
tests/                       offline unit and parser-contract tests
docs/                        architecture, data, operations and governance
```

The separation keeps each part responsible for one job. A source-specific change
normally touches one company spider; a Greenhouse-format change touches the
Greenhouse adapter; storage and dashboard code do not need to know how a company
career page works.

## Output boundary

Each run uses a UTC ID such as `20260820T103642Z` and writes to its own folders:

```text
data/raw/run_id=<RUN_ID>/...                 original responses and metadata
data/validated/run_id=<RUN_ID>/...           Pydantic-valid JSONL records
data/status/run_id=<RUN_ID>/...              one status file per source
data/processed/run_id=<RUN_ID>/jobs.parquet  analytical and historical contract
data/processed/run_id=<RUN_ID>/source_status.parquet
data/published/latest.json                   pointer to last accepted full run
output/run_id=<RUN_ID>/av_jobs.duckdb        reproducible analytical database
output/run_id=<RUN_ID>/*.json                quality, issues and run summaries
```

Raw responses and validated JSONL are deliberately excluded from Git. The branch
contains one reviewed processed snapshot for team use; later generated runs stay
ignored unless the team deliberately selects another snapshot for publication.
Raw recruitment responses can be large and may contain text whose redistribution
needs separate approval.

## Safe publication behaviour

`latest.json` changes only if every selected source finishes successfully,
returns valid records, required fields are populated, active job keys are unique,
both Parquet files are written, and DuckDB can be reopened with the expected row
count. A failed or empty source leaves the previous accepted pointer unchanged.

Sample runs and `--no-publish` runs always leave it unchanged. Partial full runs
preserve unselected companies, and only a successfully refreshed source may mark
one of its previously seen jobs inactive.

## Verification

All tests are offline; they use local ATS-shaped fixtures and do not contact
company websites:

```powershell
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\scrapy check
```

At the committed full verification on 22 August 2026, all 16 sources passed and
1,429 unique active jobs reached Parquet and DuckDB. See the
[snapshot record](data/README.md). This is point-in-time test evidence, not a
promise that external career endpoints will never change.

## Documentation

- [Architecture and design decisions](docs/ARCHITECTURE.md)
- [Data dictionary](docs/DATA_DICTIONARY.md)
- [Operations and troubleshooting](docs/OPERATIONS.md)
- [Adding or changing a source](docs/DEVELOPMENT.md)
- [Source register and investigation evidence](docs/SOURCES.md)
- [Ethics, security and limitations](docs/ETHICS_AND_LIMITATIONS.md)
- [Contribution checklist](CONTRIBUTING.md)

The implemented company set is an engineering MVP proposal based on team Issues;
it is not evidence that the client approved all sixteen companies as final scope.
