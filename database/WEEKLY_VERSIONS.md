# Weekly collection and optional classification versions

One `week_date` selects one official Li cumulative file. Its classification is
optional and can be imported later. The date is a human-facing **weekly label**,
not a crawl timestamp or a substitute for the file SHA-256. The dated
deliverable folder, not the newest job's `collected_at`, supplies this label;
the 9/6 file can legitimately contain a latest source collection from 9/5.
Repeated or corrected files for the same date are rejected instead of silently replacing the official
file; replacement needs a separately reviewed workflow.

`weekly_versions` is the selection table. `collection_runs` and
`job_observations` preserve the file's full state. Its nullable
`selected_analysis_run_id` points to Sunjol's classification of that *exact*
collection run; a composite foreign key enforces that pairing in MySQL. The
analysis importer requires `--week-date`, the exact
`--source-input` file, matching file SHA-256, matching `source_key` set, and
matching per-job hashes. An incomplete classification is retained for audit but
is not selected as the week's official analysis.

## Current-week import

```text
python database/weekly_import.py import-collection \
  --week-date 2026-09-25 --input data-collection/deliverables/2026-09-25/jobs_history_translated.json
```

## Earlier-week backfill after a newer week was imported

```text
python database/weekly_import.py import-collection \
  --historical --week-date 2026-09-06 \
  --input data-collection/deliverables/2026-09-06/jobs_history_translated.json
```

Backfill adds the historical `collection_runs` and `job_observations` only;
it never rewinds `jobs`, the latest canonical state. Every historical
`source_key` must already exist in `jobs` with the same `source_id`. If it
does not, the importer stops: rebuild an isolated database chronologically
instead of inventing a current state for an old-only job. Do not run an old
file as a normal `import-collection` command. The backup and local operation
report apply to backfills too.

## Attach a classification later

Use the same file set from one complete Sunjol run and specify the matching
week explicitly:

```text
python database/weekly_import.py import-analysis \
  --week-date 2026-09-06 \
  --source-input data-collection/deliverables/2026-09-06/jobs_history_translated.json \
  --postings PATH/postings_all.json --metadata PATH/run_metadata.json \
  --av-summary PATH/av_relevant/cluster_summary.csv \
  --other-summary PATH/not_av_relevant/cluster_summary.csv \
  --duplicates PATH/duplicates_removed.csv --failures PATH/llm_failures.csv \
  --git-commit CLASSIFICATION_COMMIT_SHA
```

The import produces a draft. Run `qa-release --release-key KEY`, then either
`publish-release --release-key KEY` for the newest current week, or
`publish-release --release-key KEY --historical` to freeze an older week
without replacing the current Dashboard. Only QA-passing, frozen releases
appear in the AV-specific historical views.

## Read-only backend contract

| View | What it exposes |
| --- | --- |
| `v_weekly_versions` | Every official week, even without classification; collection and classification status plus the selected release. |
| `v_weekly_jobs` | The cumulative raw job state for each week, including active/inactive flags; not AV-filtered. |
| `v_weekly_av_jobs` | AV-relevant, non-duplicate jobs from frozen published or historical releases only. |
| `v_weekly_av_job_skills` | Job-to-skill links from those same frozen releases. |
| `v_dashboard_*` | Only the one currently published Dashboard release. |

Grant the backend read-only access to these views, not the candidate views or
core tables. Backend code chooses comparable dates, handles missing
classification, and computes differences. A date label alone does not prove
that every source was successfully crawled that week. The current cumulative
files have no imported per-source run reports, so AV trend claims need that
coverage limitation stated until Li's run reports are linked.

## Existing development database

For an existing Stage 3 database, verify a backup and apply
`migrations/006_weekly_versions.sql`, then replace the views using
`views.mysql.sql` after reviewing the target database name. The migration
selects an existing published classification automatically but refuses to
silently choose between multiple collection files with the same date. A new
empty database needs only `schema.mysql.sql` and `views.mysql.sql`.
