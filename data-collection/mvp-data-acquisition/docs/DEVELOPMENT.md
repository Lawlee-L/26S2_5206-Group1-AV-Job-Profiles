# Development Guide

## Design rules

- Keep one concrete spider per company.
- Put response-format mapping in the ATS adapter, not in every company file.
- Preserve source values; perform classification in a downstream stage.
- Exchange data through the typed `RawJob` contract or documented data frames.
- Do not let spiders write Parquet/DuckDB or let storage code make network calls.
- Add a test for every parsing or history rule changed.
- Retain raw evidence and fail closed when source correctness is uncertain.

Comments should explain a non-obvious decision or safety rule. Docstrings state
module/class responsibility. Avoid comments that merely repeat the code.

## Add a company on an existing ATS

1. Confirm the official public careers page and structured endpoint, source
   terms/robots behaviour, AV relevance and board scope.
2. Create one small module under the matching platform directory. For example:

```python
"""Example company job spider."""

from .base import GreenhouseSpider


class ExampleCompanySpider(GreenhouseSpider):
    """Collect Example Company's public Greenhouse vacancies."""

    name = "example_company"
    company = "Example Company"
    board_token = "official-public-token"
```

3. Add one `SourceDefinition` to `registry.py`, including the team Issue that
   provides investigation evidence.
4. Add or extend an offline parser fixture if the source exposes a new field or
   differs from the existing ATS mapping.
5. Run a targeted sampled crawl, inspect raw/validated/status evidence, then run
   the complete verification suite.
6. Update `SOURCES.md`. Do not call it client-approved unless meeting evidence
   explicitly supports that statement.

## Add a new acquisition method

Create a method-specific adapter directory rather than inserting many conditions
into `AtsApiSpider`. Define how it obtains data, snapshots responses and maps the
same `RawJob` contract. Add fixture-based tests before adding company spiders.

Playwright sources should live separately from API spiders because browser
lifecycle, rendering failures and collection cost are different responsibilities.
Do not silently fall back to browser automation or access-control workarounds.

## Change the data contract

Classify the change first:

- a source field belongs in `RawJob` only if spiders can collect it reliably;
- a cleaned/derived field belongs in `jobs.parquet` and must be documented;
- an AI/taxonomy result belongs in a later enrichment dataset with provenance,
  version and confidence—not in the raw contract.

For a breaking change, update the Pydantic model, all ATS adapters, cleaning,
data dictionary, fixture tests and downstream compatibility notes together.

## Local quality commands

```powershell
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m ruff format --check .
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\scrapy check
.\.venv\Scripts\python run_pipeline.py --max-jobs 1
```

The first four are deterministic/offline. The last is a live smoke test and may
fail because external sites change; record that separately from code-test results.

## Review checklist

- Source and scope evidence are linked.
- No secrets, credentials, raw generated data or local environment files enter
  the commit.
- Platform logic is not duplicated across company spiders.
- Required fields cannot pass blank.
- A failed/empty source cannot change the accepted pointer or close its history.
- New output fields have clear meaning, type, provenance and null semantics.
- README/source register/data dictionary reflect the implementation.
