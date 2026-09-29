# Current Source-to-Database Mapping

This mapping covers Li's latest cumulative collection snapshot and the output
contract expected from Sunjol's v2 pipeline. Older classification samples are
not interchangeable with the v2 output and must not replace the canonical job
history.

## 1. Collection history JSON

Current source:

`data-collection/deliverables/2026-09-25/jobs_history_translated.json`

The file contains 5,139 unique `source_key` values. `source_key` is the only
approved cross-stage join key.

| Input field | Destination | Rule |
| --- | --- | --- |
| `metadata.company` | `companies.company_name` | Trim only; keep canonical spelling. |
| `metadata.source_id` | `job_sources.source_id` | Natural source identifier. |
| `metadata.platform` | `job_sources.platform` | Lowercase in importer. |
| `metadata.region` | `job_sources.region` | Do not treat as the job location. |
| `metadata.source_key` | `jobs.source_key` | Required and unique. |
| `metadata.source_job_id` | `jobs.source_job_id` | May be absent in future sources. |
| `metadata.collected_at` | `jobs.latest_collected_at` | Parse as UTC. |
| `metadata.first_seen_date` | `jobs.first_seen_date` | Parse as date. |
| `metadata.last_seen_date` | `jobs.last_seen_date` | Parse as date. |
| `metadata.is_active` | `jobs.is_active` | Do not infer from date. |
| `metadata.is_new_in_latest_run` | `jobs.is_new_in_latest_run` | Latest-run display flag. |
| `data.advertised_job_title` | `jobs.advertised_job_title` | Preserve NULL; flag missing values for dashboard QA. |
| `data.job_description` | `jobs.job_description` | Preserve full text. |
| `data.job_url` | `jobs.job_url` | Preserve NULL; `source_key` remains the stable identifier. |
| `data.location` | `jobs.location_raw` | Normalised location fields remain nullable. |
| `data.salary` | `jobs.salary_raw` | Do not guess currency or interval. |
| `data.date_posted` | `jobs.date_posted` | Parse when valid; otherwise NULL. |

The supplied Li snapshot has no hash fields. The importer calculates two
different fingerprints and stores both in `jobs` and each
`job_observations` snapshot:

| Database field | What is hashed | Algorithm and purpose |
| --- | --- | --- |
| `content_hash` | The job description after the same Unicode, punctuation, bullet, and whitespace normalization used by classification-pipeline `clean.py` v2. | 40-character SHA-1. Matches the pipeline's exact-description deduplication/cache key and proves which description version an analysis read. |
| `record_hash_sha256` | Canonical title, full description, job URL, raw location, raw salary, and posting date. | 64-character SHA-256. Detects any change to those collected fields; it is not a job ID and is not used for classifier deduplication. |

`job_analyses.input_content_hash` stores the 40-character description hash for
the exact description version consumed by that analysis. The same `source_key`
still identifies and joins the job; none of these hashes replaces it. The hash
contract is versioned as `av-job-hash-v1` in importer provenance. Do not
truncate, compare, or reuse one hash as the other.

The current history file is cumulative rather than a complete set of weekly
snapshots. Each file import creates a synthetic collection run; its run key
includes the snapshot date and file digest so distinct files from one day do
not collide. For cumulative exports, `job_observations.collected_at` is NULL:
no exact per-run crawl observation was supplied. `state_as_of_date` records
date-level state and `source_last_collected_at` preserves each job's latest
source timestamp. `collection_runs.snapshot_generated_at` is set only when
the actual export time is supplied. `trend-readiness` rejects cumulative
exports even if a generation timestamp is known.

## 2. Sunjol v2 pipeline output contract

The importer expects all files from one full run, produced from the same Li
snapshot. Do not use `--limit` for an importable run.

### `postings_all.json`

One row per successfully analysed, deduplicated input. Every row must keep the
exact input `source_key` and the full `record` object. The importer matches it
to `jobs` by `source_key`, then validates company, title, URL, location, date,
source file checksum and per-record hashes, and the cluster assignment. It stores relevance,
confidence label, reason, responsibilities, seniority, experience and evidence
in `job_analyses`; skill names/evidence become `skills` and `job_skills`. The
complete model record remains in `raw_response_json`.

The v2-specific fields are retained separately for backend queries:

| Pipeline field | Database destination | Rule |
| --- | --- | --- |
| `record.role_summary` | `job_analyses.role_summary` | Store the concise role summary. |
| `record.responsibilities` | `job_analyses.responsibilities_json` | Preserve the structured array; also keep the legacy readable text in `technical_responsibilities`. |
| `record.requirements` | `job_analyses.requirements_json` | Preserve the structured array without flattening it. |
| `record.language_of_posting` | `job_analyses.language_of_posting` | Keep the detected/source language. |
| `input_content_hash` or `content_hash`, if exported | Validate against the source description SHA-1 | Optional in the current file contract; the importer calculates and stores `job_analyses.input_content_hash` from the exact source row if omitted. |
| Per-posting `served_by`, `prompt_tokens`, `output_tokens`, `cost_usd`, if exported | Matching `job_analyses` columns | Preserve per-call provenance/usage when present; absent values remain NULL. |

Aggregate `prompt_tokens`, `output_tokens`, and `cost_usd` from
`run_metadata.json` are stored on `analysis_runs`. Imported output is marked as
`result_origin='imported'`; a numeric reuse ID from another local SQLite/MySQL
database is not treated as a valid foreign key in this database.

### `run_metadata.json`

Required to confirm which input and pipeline run produced the output. The
importer reconciles `n_input_rows`, `n_after_dedupe`, `n_duplicates_removed`,
`n_records`, and `n_llm_failures` against the detail files and verifies the
input filename and row total.

### `duplicates_removed.csv`

Required to record each intentional exclusion. `source_key` and
`duplicate_of_source_key` must both exist in Li's snapshot; cross-company
matches and cyclic chains are blocked for review. The importer preserves each
original direct link, including duplicate-to-duplicate chains, instead of
silently flattening them; both endpoints remain available as source jobs.
Links are written to `job_deduplication_links`; no source job is deleted.

### `llm_failures.csv`

Required even when it contains only a header. Each failure must have a known
`source_key` and an error. Failed model rows are retained as
`job_analyses.analysis_status = 'failed'` and are not given skills or clusters.

### Group `cluster_summary.csv` files

Import both `av_relevant/cluster_summary.csv` and
`not_av_relevant/cluster_summary.csv`. The importer recalculates each cluster's
membership count from `postings_all.json`; mismatches block the import. The
source cluster number is retained as-is and scoped by both `cluster_run_id` and
`population`, so AV and non-AV clusters may use the same number. Both noise
clusters retain source number `-1` and are separately identified by population.

The v2 run is importable only when successful rows, duplicate links, and failed
rows account for every input key exactly once. The prior 533-row experiment
files are documented separately below and are not joinable to Li's current
source keys.

## 3. Legacy `postings_enriched.csv` / `postings_enriched.json`

The older sample has 533 classified jobs with `sha1:...` keys. A check against
the 25 September collection file found zero exact key matches. It must not be
imported or matched by title/row number. The field map below describes its
shape only.

| Input field | Destination | Rule |
| --- | --- | --- |
| `source_key` | lookup `jobs.job_id` | Reject row if no exact match. |
| `row_index` | `job_analyses.source_row_index` | Trace/debug only; never a key. |
| `company` | validation only | Must agree with the linked source/company. |
| `name` | validation only | Do not overwrite the canonical advertised title. |
| `date_posted` | validation only | Canonical value remains in `jobs`. |
| `seniority` | `job_analyses.seniority_raw` and mapped `seniority_code` | Preserve raw label. |
| `seniority_source` | `job_analyses.seniority_source` | Direct mapping. |
| `seniority_evidence` | `job_analyses.seniority_evidence` | Direct mapping. |
| `seniority_conflict` | `job_analyses.seniority_conflict` | Boolean. |
| `experience_min` | `job_analyses.experience_min_years` | Decimal years. |
| `experience_max` | `job_analyses.experience_max_years` | Decimal years. |
| `experience_evidence` | `job_analyses.experience_evidence` | Preserve original evidence. |
| `skills_tools` | `skills` + `job_skills` | Split on semicolon; type `tool`. |
| `skills_domain` | `skills` + `job_skills` | Split on semicolon; type `domain`. |
| `skills_qualifications` | `skills` + `job_skills` | Split on semicolon; type `qualification`. |
| `cluster_id` | `job_cluster_assignments` | Resolve inside one cluster run. |
| `cluster_lean` | validation against `clusters.lean` | Cluster-level attribute, not a permanent job field. |

## 4. Legacy `cluster_summary.csv`

The current sample contains 30 regular clusters and one noise cluster (`-1`).
Cluster labels are not yet complete, so nullable naming fields are intentional.

| Input field | Destination | Rule |
| --- | --- | --- |
| `cluster_id` | `clusters.cluster_number` | Scoped by `cluster_run_id` and `population`. |
| summary group | `clusters.population` | `av_relevant` or `not_av_relevant`, taken from the matching source summary file. |
| `size` | `clusters.size_cached` | Validate against assignments. |
| `is_noise` | `clusters.is_noise` | Preserve cluster `-1`. |
| `technical_score` | `clusters.technical_score` | Range 0–1. |
| `lean` | `clusters.lean` | Map `n/a (noise)` to `noise`. |
| `n_companies` | validation only | Recalculate for QA; not authoritative storage. |
| `top_companies` | `clusters.top_companies_json` | Parse into an ordered JSON array. |
| `top_terms` | `clusters.top_terms_json` | Parse into an ordered JSON array. |
| `example_titles` | `clusters.example_titles_json` | Parse into an ordered JSON array. |
| `job_family` | `clusters.job_family` | Nullable until named. |
| `specialisation` | `clusters.specialisation` | Nullable until named. |
| `notes` | `clusters.notes` | Nullable. |

An LLM-generated cluster name must first be inserted into
`cluster_label_revisions` with `label_source = 'llm'` and status `proposed`.
A human-created name uses `label_source = 'manual'`. Neither path overwrites an
older revision. Only an approved revision is copied into the current label
fields in `clusters` and exposed through the dashboard views.

## 5. Legacy `gpt_oss_answers.json`

The current file contains only 14 experimental LLM responses. It lacks
`source_key`, so it must not be bulk-loaded until each result is linked to an
exact canonical job.

| Input field | Destination | Rule |
| --- | --- | --- |
| `av_relevant` | `job_analyses.av_relevant` | Boolean. |
| `relevance_confidence` | `job_analyses.relevance_confidence_label` | Keep labels such as `High`; do not invent a probability. |
| `relevance_reason` | `job_analyses.relevance_reason` | Direct mapping. |
| `technical_responsibilities` | `job_analyses.technical_responsibilities` | Direct mapping. |
| `key_evidence` | `job_analyses.key_evidence_json` | Store as JSON array. |
| `seniority` | seniority fields | Preserve raw label and map through a controlled dictionary. |
| `seniority_evidence` | `job_analyses.seniority_evidence` | Direct mapping. |
| `raw_skills_tools` | `skills` + `job_skills` | One array element per skill, type `tool`. |
| `raw_skills_domain` | `skills` + `job_skills` | One array element per skill, type `domain`. |
| `raw_skills_qualifications` | `skills` + `job_skills` | One array element per skill, type `qualification`. |
| complete response | `job_analyses.raw_response_json` | Preserve for audit and reprocessing. |

## Controlled seniority codes

Keep the model's original label in `seniority_raw`, then map to one of these
backend values in `seniority_code`:

```text
intern
graduate
entry
junior
mid
senior
lead
staff
principal
manager
senior_manager
director
vp
other
unknown
```

Do not collapse `Staff`, `Principal`, and `Lead` unless the team approves a
single reporting taxonomy.

## Validation gates before publication

The importer must block publication when any of these checks fails:

1. duplicate or missing `source_key`;
2. analysis row cannot be joined to exactly one job;
3. cluster assignment references an unknown cluster;
4. cluster size differs from the count of assignments;
5. malformed date, boolean, JSON, or numeric range;
6. `experience_max_years < experience_min_years`;
7. a completed full-source run unexpectedly returns zero jobs;
8. published release refers to incomplete or failed runs.

Label-specific validation must also confirm that the current label revision
belongs to the same cluster and has `label_status = 'approved'` before a
dashboard release can be published.

Rows failing individual validation belong in `import_rejections`; they should
not disappear silently.
