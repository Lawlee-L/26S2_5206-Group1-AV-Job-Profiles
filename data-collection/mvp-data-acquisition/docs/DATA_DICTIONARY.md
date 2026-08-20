# Data Dictionary

## Raw validated job contract

Every company spider produces the same strict Pydantic record before cleaning.
Unknown fields are rejected rather than silently stored.

| Field | Type | Meaning |
|---|---|---|
| `source_job_id` | string, required | Stable job identifier supplied by the ATS |
| `company` | string, required | Project display name for the company/source scope |
| `original_title` | string, required | Advertised title as supplied, except surrounding whitespace |
| `location_raw` | string or null | Source location text; not yet geographically normalised |
| `description_raw` | string, required | Source HTML or text description before cleaning |
| `source_url` | URL, required | Canonical public job advertisement/application URL |
| `posted_at` | datetime or null | Posting date where exposed by the source |
| `updated_at` | datetime or null | Update date where exposed by the source |
| `employment_type` | string or null | Source employment/commitment label |
| `department` | string or null | Source department label |
| `team` | string or null | Source team label |
| `workplace_type` | string or null | Remote/hybrid/on-site label where exposed |
| `salary_raw` | string or null | Unnormalised compensation payload where exposed |
| `source_type` | `ats_api` | Acquisition method used by this MVP |
| `source_name` | enum | `ashby`, `greenhouse` or `lever` |
| `scraped_at` | UTC datetime | Time the record was collected |
| `run_id` | string | UTC identifier of the collection run |
| `content_hash` | SHA-256 | Hash of identity/content fields, added after validation |

Null means the source did not expose a dependable value. It does not mean the
real-world value does not exist.

## Processed `jobs.parquet` contract

The processed dataset removes source HTML from the description, normalises
Unicode/whitespace, standardises times to UTC and adds observation history.

| Field | Meaning |
|---|---|
| `snapshot_run_id` | Run whose complete processed snapshot contains this row |
| `collected_run_id` | Run that last collected this job record |
| `source_job_id`, `company`, `original_title` | Cleaned identity/source values |
| `location_raw` | Cleaned but deliberately unclassified source location |
| `description_text` | Plain-text job description |
| `employment_type`, `department`, `team`, `workplace_type`, `salary_raw` | Cleaned optional source values |
| `posted_at_utc`, `updated_at_utc`, `scraped_at_utc` | Source/collection times converted to UTC |
| `source_url`, `source_type`, `source_name` | Source provenance |
| `first_seen_utc` | First successful observation retained in project history |
| `last_seen_utc` | Most recent successful observation of the job |
| `status` | `active` or `inactive` observation state |
| `is_active` | Boolean equivalent used for filtering |
| `description_word_count`, `description_character_count` | Basic quality/analysis measures |
| `content_hash` | Validated source-content checksum |

The primary identity key is `(company, source_job_id)`. The same ATS ID from two
companies is not assumed to describe the same job.

## `source_status.parquet` contract

One row records the outcome of each selected company spider:

- `run_id`, `spider`, `company`, `source_name`;
- `finish_reason` and final `status` (`success` or `failed`);
- `source_items_seen` and `validated_items`;
- `validation_errors`, `response_count` and `response_errors`;
- `snapshot_files`.

This table is operational evidence. It prevents a failed or unexpectedly empty
source from being confused with a company that has closed all jobs.

## DuckDB objects

| Object | Type | Purpose |
|---|---|---|
| `jobs` | table | Complete current plus retained historical snapshot |
| `source_status` | table | Source outcome evidence for the run |
| `active_jobs` | view | Only records whose `is_active` value is true |
| `jobs_with_quality_flags` | view | Missing title/URL and short-description indicators |

## Not yet produced

`generic_job_title`, normalised country/city, `required_skills`, AV job category,
classification confidence and model/taxonomy version are downstream enrichment
fields. They must not be fabricated during scraping or confused with original
source data.
