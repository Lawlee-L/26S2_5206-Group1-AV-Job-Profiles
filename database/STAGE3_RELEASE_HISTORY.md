# Stage 3: release snapshots and honest history

## Frozen release

`jobs` holds the latest editable/cumulative state. `publish-release` copies
three display populations into `dashboard_release_snapshot_rows`: AV-relevant
non-duplicate jobs (active **and** inactive), their job-skill rows, and AV
clusters with their then-current label state. `v_dashboard_*` reads only the
frozen rows of the one published release. Retired snapshots remain queryable
by release ID internally. Later job, skill, company or cluster-label changes
cannot rewrite an old release. Freezing an unapproved label does not approve it.

`v_candidate_dashboard_*` reads mutable tables solely to build/review a
release. Do **not** grant it to the backend's public read-only account.
Publication backs up the database, freezes rows and switches release status
in one transaction; a failed QA check rolls the transaction back. A frozen
release cannot be materialized again.

```powershell
python database/weekly_import.py qa-release --release-key <draft-key>
python database/weekly_import.py publish-release --release-key <draft-key>
python database/weekly_import.py qa-release --release-key <draft-key>
```

`freeze-release --release-key <key>` can freeze an already-published legacy
release, but only from its **currently available** rows. It cannot reconstruct
a display that changed before freezing. Use it before importing newer data.
During development, a fresh database and reimport from saved inputs is safer;
the team has no deployed shared database requiring migration yet.

## Four distinct times

| Field | Meaning for a cumulative export |
| --- | --- |
| `collection_runs.snapshot_as_of_date` | Explicit week label for the selected cumulative file (normally its dated deliverable folder), not the newest source observation or exact crawl time. |
| `collection_runs.snapshot_generated_at` | Actual UTC export completion time, only when supplied. Never inferred. |
| `collection_runs.started_at/completed_at` | Local importer operation time, not crawl time. |
| `job_observations.collected_at` | NULL: the cumulative file does not prove this job was crawled in this run. |
| `job_observations.source_last_collected_at` | Last supplied source collection time for this job; inactive jobs may have older values. |
| `job_observations.state_as_of_date` | State of this job in the cumulative export. |
| `dashboard_releases.published_at` | Dashboard publication time, not collection time. |

Current Li history imports explicitly use `run_kind='cumulative_state_export'`,
`time_quality='date_only'`, and `source_report_available=FALSE`; no
`source_run_results` are invented. A future verified crawl must provide exact
times and per-source results. Failed or unexpected zero-result sources need
investigation before a run is called complete.

Two different files on one date have distinct file digests, but per-job
timestamps do not order whole exports. Only one file may be selected as the
official weekly version. The importer rejects a second file for that date;
an actual UTC export time does not override this rule. Do not invent a time
or date to force an import. The analysis
run points to the exact `collection_run_id` and source file SHA-256 digest.
Classifier hashes are compared with that run's `job_observations`, not the
newest mutable `jobs` row. Thus later imports do not invalidate an earlier
correctly linked analysis.

## Trend gate

```powershell
python database/weekly_import.py trend-readiness
```

This read-only check needs at least two frozen releases with the same source
set, each backed by a completed `verified_crawl`, exact UTC time, successful
non-empty source results and linked completed analysis. It currently reports
`ready=false`: four cumulative files are not four verified complete crawls,
and only one full classification run is available. Do not plot these as job,
skill or cluster demand trends. Show “insufficient comparable data” instead.

The 2026-09-25 sample release contains 2,902 AV-relevant jobs, including
2,412 active and 490 inactive. “AV-relevant” does not mean “currently open”.

## Development validation

Use a separately named empty MySQL database. Apply `schema.mysql.sql`, then
`views.mysql.sql`, adjusting only their database names for the test instance.
Do not apply a fresh schema over populated data. Import matching collection
and classification files, run QA, publish, then edit `jobs`, `skills` and
`clusters` inside a transaction to verify public views do not change; roll
that transaction back. Automated tests are in `database/tests`. Local reports
are under `database/operation_logs`, and backups under `database/backups`.
