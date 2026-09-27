# Release Metrics and Public AV Dashboard Contract

## Product rule

The public Dashboard displays only successfully classified, AV-relevant,
non-duplicate jobs from the collection snapshot linked to the currently
published release. It exposes those jobs, their extracted skills, AV clusters,
and company aggregates. It does not expose non-AV, unknown, failed, duplicate,
or out-of-snapshot records. Those records remain in the database for internal
quality checks.

AV relevance is the classifier's result. It has not been independently
verified by this database report. Counts describe the linked dataset; they do
not mean that a job is still open today. Historical active status and trend
meaning are handled separately from this contract.

## Metrics

Each metric is computed for the exact `dashboard_release_id` and its linked
`collection_run_id`, `analysis_run_id`, and `cluster_run_id`.

| Metric | Definition | Public? |
| --- | --- | --- |
| `source_postings` | Distinct jobs with an observation in the release's collection run. | No; internal QA only. |
| `deduplicated_postings` | Distinct `duplicate_job_id` values in `job_deduplication_links` for the release's analysis run and collection snapshot. The source jobs remain stored. | No; internal QA only. |
| `analysed_postings` | Distinct in-snapshot jobs with `analysis_status = 'success'`, excluding duplicate source rows. | No; QA context. |
| `av_postings` | Successful, in-snapshot, non-duplicate analyses with `av_relevant = TRUE`. | Yes; the Dashboard's job count. |
| `non_av_postings` | Successful analyses with `av_relevant = FALSE`. | No. |
| `unknown_relevance` | Successful analyses whose `av_relevant` is `NULL`. | No. |
| `failed_or_pending` | In-snapshot analysis rows whose status is not `success`. | No. |
| `unaccounted` | In-snapshot jobs with neither an analysis outcome nor a duplicate decision. | No; QA error. |

For a complete outcome partition:

```text
source_postings
= deduplicated_postings + analysed_postings + failed_or_pending + unaccounted

analysed_postings
= av_postings + non_av_postings + unknown_relevance
```

If an analysis row and duplicate link refer to the same source job, the run
fails QA rather than counting that job twice. Broken or cross-company duplicate
links, cycles, outcomes outside the collection snapshot, and mismatched cluster
populations also fail QA.

The verified 25 September 2026 sample reconciles as follows:

```text
5,139 source postings = 621 duplicate decisions + 4,518 successful analyses
4,518 successful analyses = 2,902 AV + 1,616 non-AV
failed_or_pending = 0; unknown_relevance = 0; unaccounted = 0
```

These are sample QA values. Queries calculate each future release's values;
they must never use `2,902` as a hard-coded total.

## Public database views

The public views in `views.mysql.sql` apply the same release and population
filter:

- `v_dashboard_jobs`: AV-relevant, successful, non-duplicate job rows in the
  release's collection snapshot.
- `v_dashboard_job_skills`: skills linked to those same AV jobs.
- `v_dashboard_skill_demand`: skill and company counts derived only from the
  AV-only skill view. Job counts use distinct `job_id`; company counts use
  distinct `company_id`.
- `v_dashboard_clusters`: AV-population clusters with members in the same
  release. `clusters.population` distinguishes AV clusters from non-AV clusters
  even when their source cluster numbers overlap.

The public views return no rows for a draft or retired release. Non-AV data is
retained in base tables and may appear in the local QA report only; the public
API must not offer a non-AV or all-jobs toggle.

## Read-only QA command

Run the QA report for a release without changing database rows:

```text
python database/weekly_import.py qa-release --release-key <release-key>
```

The JSON report identifies the release and three linked runs, reports the
internal partition counts, checks duplicate chains and cluster membership,
counts AV jobs without skills, and compares the public view to the AV count.
A non-passing QA result exits with a non-zero status and is written to the
existing per-operation local report and append-only log.

The report shows `public_visible_av_postings = 0` for an unpublished draft.
For a published release, that count must equal `av_postings`. Publication
remains a separate reviewed operation; running QA does not publish a release.
