# Current Source-to-Database Mapping

This mapping covers the current collection history and Sunjol's experimental
classification files. The analysis files are samples and must not replace the
canonical collection dataset.

## 1. Collection history JSON

Current source:

`data-collection/deliverables/2026-09-06/jobs_history_translated.json`

The file contains 4,163 unique `source_key` values. `source_key` is the only
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

The current history file is cumulative rather than a complete set of weekly
snapshots. Its first database load should create a synthetic collection run,
for example `history-2026-09-06`. Future weekly pipeline runs should insert
real `job_observations`.

## 2. `postings_enriched.csv` / `postings_enriched.json`

The current sample has 533 classified jobs. Resolve every record to `jobs` by
`source_key` before inserting analysis data.

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

## 3. `cluster_summary.csv`

The current sample contains 30 regular clusters and one noise cluster (`-1`).
Cluster labels are not yet complete, so nullable naming fields are intentional.

| Input field | Destination | Rule |
| --- | --- | --- |
| `cluster_id` | `clusters.cluster_number` | Scoped by `cluster_run_id`. |
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

## 4. `gpt_oss_answers.json`

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
