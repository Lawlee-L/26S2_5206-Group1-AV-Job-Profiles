# Same-week classification revisions and safe re-publication

## 1. Plain-language summary

Think of three things: **the collected jobs**, **the analysis of those jobs**,
and **the saved version that the Dashboard reads**. The collection date stays
the same when we correct an analysis. A week can have several saved versions,
but the Dashboard reads only the one we select for that week.

Prepare and check the new version first. Then switch to it. The old version
keeps working while we prepare the new one. If the new version is wrong,
switch back; do not delete the old data. Adding job descriptions to a saved
version can reuse the existing analysis: **no new AI run is needed**.

| Identifier | What changes? |
| --- | --- |
| `week_date` | Human-facing date of the official Li collection file; unchanged for a same-week revision |
| `analysis_run_id` | A different classification output creates a new analysis; the exact Li file and job keys must still match |
| `release_key` | A new frozen dashboard representation; several releases may reuse one analysis |

One **current dashboard** is separate from each week's **selected historical
release**. Updating an earlier week does not rewind the current dashboard.

## 2. Install before using the new commands

Use the environment and MySQL setup in [TEAM_GUIDE.md](TEAM_GUIDE.md).
Choose the installation route before running SQL:

| Your local database | What to apply |
| --- | --- |
| New, empty database | Current `schema.mysql.sql`, then `views.mysql.sql`; do not also run migrations 006/007 |
| Verified Stage 3 database without `weekly_versions` | Backup/test a restored copy, then migration 006, migration 007 and current views |
| Weekly database already using 006, without `selected_release_id` | Backup/test a restored copy, then migration 007 and current views |
| Already upgraded to 007 | Do not rerun 007; update views when the read contract changes |
| Older or unknown schema | Inspect it first; do not guess which numbered migrations apply |

For an existing database already using migration 006:

1. Confirm `AVDB_NAME` names the intended development database.
2. Run `python database/weekly_import.py backup` and keep the verified backup.
3. Restore/test on a **new database name** first if this copy matters.
4. In MySQL Workbench, select that target schema and execute
   `database/migrations/007_release_revisions.sql` **once**. For the
   command-line alternative, using the configured MySQL tool and credentials:

   ```powershell
   $env:MYSQL_PWD = $env:AVDB_PASSWORD
   Get-Content -Raw database/migrations/007_release_revisions.sql | & $env:AVDB_MYSQL -h $env:AVDB_HOST -P $env:AVDB_PORT -u $env:AVDB_USER -D $env:AVDB_NAME
   if ($LASTEXITCODE -ne 0) { throw 'Migration 007 failed. Stop and inspect the database before retrying.' }
   ```

   Check that the command completed successfully before proceeding.
5. Apply `views.mysql.sql`; check its `USE av_job_profiles` line and change
   it to the intended test database name when using a different local name.
6. Keep the public-view grants in the team guide. Do not grant the new audit
   table or mutable core tables to the backend.

Migration 007 adds `weekly_versions.selected_release_id`, release-parent
provenance and the `release_operations` audit table. It does not replace Li's
data, classification results or frozen payloads. MySQL table-structure changes
are not transactional: do not blindly rerun this one-time migration after an
error. Inspect the target or restore into another new test database.
If a previous attempt failed, some table changes may already exist; do not
treat that database as an untouched 006 schema.

The migration selects an existing matching frozen current release, or a sole
matching frozen historical release. If several historical releases match and
none is current, it leaves the selection empty for explicit operator review.
An empty release selection is passed as `none` below.

After installing the views, run `list-releases` and check the selected/current
keys before any write. Migration 007 keeps the existing frozen snapshots;
it does **not** add descriptions to an old snapshot. If details are needed,
use section 5 to create a new release from the same analysis, then review and
activate it. There is no need to reimport Li's files or rerun Sunjol's model
just to upgrade this schema.

## 3. Inspect the actual selections first

```powershell
python database/weekly_import.py list-releases
python database/weekly_import.py list-releases --week-date 2026-09-25
```

Read `selected_for_week=1` for the target week's formal version and
`current_dashboard=1` for the overall current dashboard. The unfiltered command
is needed when the current release belongs to a different week. A candidate
has neither flag. `status='draft'` with a non-empty `snapshot_frozen_at` means
preparation completed but activation has not completed; it is still invisible.

Before any switch, copy the keys you just inspected:

```powershell
$oldWeek = 'PASTE_CURRENTLY_SELECTED_KEY_FOR_TARGET_WEEK'
$current = 'PASTE_OVERALL_CURRENT_DASHBOARD_KEY'
```

Use the literal string `'none'` if the corresponding selection is absent.
The `--expected-*` arguments mean: **"Only switch if the database still has
the old versions I reviewed."** If another operation changed them, the command
stops. Reinspect and review; do not bypass the check.

## 4. New Sunjol output for the same Li file

Set the exact dated Li input and the folder containing one complete new run.
All seven paths must be from the same input/output pairing. New model results
are supplied by Sunjol; the importer makes no model calls.

```powershell
$li = 'data-collection/deliverables/2026-09-25/jobs_history_translated.json'
$out = 'PATH_TO_THE_COMPLETE_NEW_OUTPUT_FOLDER'
$files = @(
  '--source-input', $li,
  '--postings', "$out/postings_all.json",
  '--metadata', "$out/run_metadata.json",
  '--av-summary', "$out/av_relevant/cluster_summary.csv",
  '--other-summary', "$out/not_av_relevant/cluster_summary.csv",
  '--duplicates', "$out/duplicates_removed.csv",
  '--failures', "$out/llm_failures.csv"
)
python database/weekly_import.py plan-analysis @files
python database/weekly_import.py import-analysis @files --candidate --week-date 2026-09-25 --git-commit REAL_CLASSIFICATION_COMMIT_SHA
```

`--candidate` stores the new analysis, skills, clusters and draft without
changing the selected classification or current dashboard. Without this flag,
a second same-week classification is rejected. An identical output remains
duplicate-protected; it is not a way to refresh a frozen snapshot.

Copy the returned `result.release_key`, then run QA:

```powershell
$new = 'PASTE_RETURNED_RELEASE_KEY'
python database/weekly_import.py qa-release --release-key $new
```

Review the counts **and warnings**. Incomplete results or broken input matches
cannot be activated. Missing skills or approved cluster names may be warnings,
not permission to invent them. A new clustering run's numeric IDs are not a
mapping to old approved names: review any new labels separately.

## 5. Same analysis, new dashboard snapshot: no AI rerun

Use this when adding full job descriptions to a release whose old snapshot
does not contain them, or publishing an explicitly reviewed label update.
It reuses the collection, analysis and cluster run, not the old frozen rows.

```powershell
python database/weekly_import.py create-release --from-release-key $oldWeek --reason "Include full job descriptions in the dashboard snapshot" --actor Nyx
$new = 'PASTE_RETURNED_RELEASE_KEY'
python database/weekly_import.py qa-release --release-key $new
```

This creates a new draft and records its parent release; no classification is
reimported, selected, paid for or overwritten. A valid old frozen release is
required. The new snapshot is built during activation using the installed
read contract. Old frozen text and labels remain unchanged.

Do **not** use this command to pretend that new classification output was
imported: use section 4 for actual classification changes.

## 6. Activate the reviewed candidate

For the target current/newest week:

```powershell
python database/weekly_import.py activate-release --release-key $new --expected-week-release $oldWeek --expected-current-release $current --reason "Team reviewed the new release and QA counts" --actor Nyx
```

The command backs up first, prepares and verifies the frozen snapshot without
exposing it, then switches in one transaction:

- the week's selected analysis;
- the week's exact selected release;
- the current dashboard release (unless `--historical`);
- the database operation record describing that switch.

Rows, source pairing, AV-only boundaries, row hashes, the aggregate snapshot
hash and job/cluster/skill coverage are checked. A database advisory lock
serialises importer writers; row locks and expected-key checks protect the
final switch. The costly file/model work is not part of that switch.

For an **earlier** week while another week remains current:

```powershell
python database/weekly_import.py activate-release --release-key $new --expected-week-release $oldWeek --expected-current-release $current --historical --reason "Reviewed revised historical classification" --actor Nyx
```

`--historical` preserves the current dashboard. Do not use it for the current
dashboard's own week: that would make the weekly and current selections disagree.
Without it, an earlier date is rejected rather than silently rewinding today.

`publish-release` still supports a first complete, normally imported analysis.
It refuses a same-week replacement. A first analysis imported as a candidate
can instead use `activate-release` with `--expected-week-release none`.

## 7. Switch back: retain both versions

Example: A was replaced by B, and B is still selected/current. To go back:

```powershell
$a = 'OLD_FROZEN_RELEASE_KEY'
$b = 'CURRENT_BAD_RELEASE_KEY'
python database/weekly_import.py activate-release --release-key $a --expected-week-release $b --expected-current-release $b --reason "Revert B because the reviewed classification is incorrect" --actor Nyx
```

The same command verifies and reactivates the intact frozen A. It does not
rebuild A from mutable source tables, rerun AI, delete B or restore a whole DB.
If a newer week has become current, reinspect the keys and use `--historical`
with that newer current key to change only the older week's selection.

**`rollback` is different:** it removes an eligible, never-used latest import
batch. It is not release reversion. Published/frozen or revision-linked analysis
must be preserved; use `activate-release` for switching visible versions.

## 8. Failure, evidence and retry

- A failed import transaction does not change official selections.
- If snapshot preparation fails, its uncommitted rows are rolled back.
- If final activation fails, selections/status changes and its operation record
  roll back together. The previous dashboard remains visible.
- A successfully prepared **frozen draft may remain** after an activation
  failure. It is not formal or publicly visible. After fixing the issue and
  rechecking selections, the same command reuses that verified draft.
- A frozen snapshot with a failed integrity check is blocked, not silently
  regenerated. Preserve evidence and investigate or use a verified DB backup.

Every parsed command uses the existing local JSON report and append-only JSONL
log under `database/operation_logs/`, including failures. Successful creates,
preparations and switches also write `release_operations` inside their own
database transaction: actor label, reason, before/after release IDs, UTC time,
backup path/checksum and operation details. Actor is an operator-supplied label,
not an authentication mechanism. Full backups remain local and Git-ignored.

Exit code `3` means the operation succeeded but the local audit file could not
be written; inspect database evidence before retrying. Do not assume it rolled
back simply because local log storage failed.

The database operator can inspect records with:

```sql
SELECT operation_id,action,week_date,reason,actor,created_at,details_json
FROM release_operations ORDER BY created_at,operation_id;
```

## 9. Backend responsibilities and boundaries

Leon keeps reading the same public views; no administrative HTTP endpoint is
required for this feature. `v_weekly_*` now exposes **only the exact selected
release**, not every frozen revision of the same analysis. `v_dashboard_*`
still exposes only the current published release. Previously supplied view
columns remain available.

Use Leon's `DATA_VIEW_MODE=published` for normal integration and display.
His optional `candidate` mode reads internal draft views, not the selected
release. These views can contain several same-week revisions. A candidate
preview must explicitly filter **all** its job, skill and cluster queries to
one `dashboard_release_id`; changing the view name alone is not sufficient.
Keep the normal read-only backend account restricted to public views.

The backend must keep related reads on the same release ID/transaction and
invalidate or version any cached results. Release switching, audit and write
permissions belong to the database operator, not the frontend/backend account.

This workflow does not replace a week's official Li collection file, add a
label-approval UI, schedule classifications or assert reliable market trends.
Historical classification is still optional and must match its own Li file.

## 10. Tests

```powershell
python -m unittest discover -s database/tests -v
```

For real isolated MySQL testing, install `requirements-import.txt`, set normal
`AVDB_*` credentials, and ensure MySQL client tools are installed:

```powershell
$env:AVDB_RUN_MYSQL_TESTS = '1'
python -m unittest database.tests.test_release_revisions_mysql -v
Remove-Item Env:AVDB_RUN_MYSQL_TESTS
```

The tests create unique `av_revision_test_*` and `av_revision_migration_*`
databases, use synthetic input and real backups, test import/upgrade/reversion/
history, migration selection and an injected final transaction failure, and
leave those small databases for inspection. They never
clear an existing database or make paid model calls. Temporary fixture files
and test backups are cleaned up when the test ends.

See [the recorded validation results](tests/RELEASE_REVISION_VALIDATION.md)
for the full suite and restored real-data checks.
