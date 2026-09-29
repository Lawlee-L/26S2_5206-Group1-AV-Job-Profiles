# MVP database: team operating guide

This is the practical guide for running the Group 1 database on **your own
computer**. The team does not currently share a deployed MySQL server. A local
database is a development copy, not the team's official publication or an
instruction to upload database credentials or backups to GitHub.

**MVP boundary:** the importer and MySQL views can store weekly collections,
attach a matching classification later, freeze an AV-only Dashboard release,
and give the backend versioned read access. They do not implement the backend
API, frontend, automatic scheduling, cluster-label approval UI, or a verified
labour-market trend. The 25 September example has 2,902 displayable AV jobs;
most cluster names still await human approval.

## 1. Who supplies, changes, and reads what?

These are **workflow permissions**. A person who installs MySQL locally may
technically have administrator access; that does not make them the owner of
another role's data. On a shared server, use separate accounts and grant only
the required SQL privileges.

| Role (current contact) | Supplies or approves | Database write route | Reads / access boundary |
| --- | --- | --- | --- |
| Collection (Li) | One reviewed, cumulative `jobs_history_translated.json` per official week; collection/source quality | Delivers files; **does not edit core MySQL tables directly** | Collection reports and weekly collection status |
| Classification (Sunjol) | One complete output folder made from the exact Li file; model/code provenance, AV relevance, skills and clusters | Delivers files; **does not edit core MySQL tables directly** | Matching Li input and classification QA |
| Label reviewer (team/client-designated) | Reviews proposed cluster names and records explicit approval | Reviewed label workflow only; no CLI approval command exists yet | Cluster evidence, examples and proposed names |
| Database/integration (Nyx or delegated operator) | Validates file pairing and counts, runs imports/backups/QA; publishes only after team approval | Importer service/CLI and reviewed schema migrations | Core tables for QA; backend-facing views |
| Backend (Leon) | API, historical comparisons and optional backend-owned application tables | **No writes to core analytical tables**; write only separately approved application tables | `v_dashboard_*` and approved `v_weekly_*` views, using a read-only account |
| Frontend / Power BI | UI and charts | None in the core database | Frontend calls backend API; an approved local Power BI prototype may query read-only views |
| Team lead / client | Confirms the display scope and release/label decisions | None | QA report, demo and release/version catalogue |

Only the importer writes collection, analysis, skill, cluster and release data.
Do not “fix” a row with an ad-hoc SQL update: correct the owning input, review
the replacement, and preserve provenance. A frozen release is never edited in
place. `v_weekly_jobs` contains **all** collected jobs, including non-AV ones;
the backend must not expose it as the public AV job list.

For a shared server, an administrator should give the backend account `SELECT`
only on these views: `v_dashboard_jobs`, `v_dashboard_job_skills`,
`v_dashboard_skill_demand`, `v_dashboard_clusters`, `v_weekly_versions`,
`v_weekly_jobs`, `v_weekly_av_jobs`, and `v_weekly_av_job_skills`. Grant neither
base-table access nor `v_candidate_dashboard_*` access to that account. Keep
schema creation, restore and importer write/backup credentials with the
database operator. The frontend must never contain a MySQL password.

## 2. Get the code and the two kinds of data

Clone [the team repository](https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles)
and open a terminal at its root. Once this guide's PR is merged, use `main`;
until then, use the PR branch. The following reviewed files are tracked in Git:

| Official week | Li collection file | Classification in Git | Expected collection rows in this example |
| --- | --- | --- | ---: |
| 2026-09-06 | `data-collection/deliverables/2026-09-06/jobs_history_translated.json` | Not supplied | 4,163 |
| 2026-09-13 | `data-collection/deliverables/2026-09-13/jobs_history_translated.json` | Not supplied | 4,475 |
| 2026-09-19 | `data-collection/deliverables/2026-09-19/jobs_history_translated.json` | Not supplied | 4,842 |
| 2026-09-25 | `data-collection/deliverables/2026-09-25/jobs_history_translated.json` | `classification pipeline/output_full/` | 5,139 |

Do **not** download an arbitrary earlier `jobs_history_translated.json` and
pair it with the latest `output_full/`. The folder date is the official
`week_date` (weekly version label), **not** necessarily the last job's crawl
date. Each Li file is a full cumulative state, not just that week's changes.
One official collection file is selected per date; re-importing or silently
replacing it is rejected. A future Sunjol output must name the matching week
and be generated from the *exact* Li file selected for it. `source_key` links
individual jobs; file SHA-256, per-job fingerprints and the database's
collection-run/analysis-run relationship verify the whole pairing.

The input files are downloaded with `git clone`/`git pull` after their PRs are
merged. If a later week's files are still on an unmerged PR branch, obtain
that exact reviewed branch/commit from its owner; do not mix folders from
different runs. The classification code may require a paid model call to
produce **new** output, but importing the tracked 25 September output does
not call an AI service.

## 3. Install a local database (Windows PowerShell example)

Requirements: Python 3.11+, MySQL Server **8.0.16+**, the `mysql` and
`mysqldump` command-line tools, and enough disk space for full backups. Run
these commands from the repository root in **PowerShell 7**. On macOS/Linux,
use the equivalent environment-variable and SQL-input syntax.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r database/requirements-import.txt

$env:AVDB_HOST = '127.0.0.1'
$env:AVDB_PORT = '3306'
$env:AVDB_USER = 'root'              # local development only
$env:AVDB_PASSWORD = Read-Host 'Local MySQL password' -MaskInput
$env:AVDB_NAME = 'av_job_profiles'
```

Put the MySQL tools on `PATH`, **or** set their exact paths. Example:

```powershell
$env:AVDB_MYSQL = 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe'
$env:AVDB_MYSQLDUMP = 'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe'
```

For a **new, empty** `av_job_profiles` database only, install the current
tables and views. Check that this database name does not already contain work
you need to keep. The schema file creates the database; do not run it over a
populated database.

```powershell
$env:MYSQL_PWD = $env:AVDB_PASSWORD
Get-Content -Raw database/schema.mysql.sql | & $env:AVDB_MYSQL -h 127.0.0.1 -u root
Get-Content -Raw database/views.mysql.sql  | & $env:AVDB_MYSQL -h 127.0.0.1 -u root
& $env:AVDB_MYSQL -h 127.0.0.1 -u root -D av_job_profiles -e 'SHOW FULL TABLES'
```

If `mysql` and `mysqldump` are already on `PATH`, set
`$env:AVDB_MYSQL = 'mysql'` and `$env:AVDB_MYSQLDUMP = 'mysqldump'` first.
`MYSQL_PWD` is only for this local client session; do not put a password in a
committed script, screenshot, GitHub issue or Teams post. Use a dedicated
least-privilege account instead of `root` when a shared server is deployed.

**Already have a populated Stage 3 development database?** Take and verify a
full backup first. Apply only `database/migrations/006_weekly_versions.sql`
to a **verified Stage 3 schema**, then replace its views using
`database/views.mysql.sql`. Migration 001–005 are history, not a recipe to
upgrade an arbitrary database. Test a restored copy first; never apply the
fresh schema over populated tables. See [version details](WEEKLY_VERSIONS.md).

## 4. Import the four available collection versions

The tested backfill route starts with the **newest** file to establish the
latest canonical `jobs` state. Older cumulative files then add historical
observations without rewinding that state. Run each command separately and
check its printed result before continuing:

```powershell
python database/weekly_import.py plan-collection --input data-collection/deliverables/2026-09-25/jobs_history_translated.json --previous data-collection/deliverables/2026-09-19/jobs_history_translated.json
python database/weekly_import.py import-collection --week-date 2026-09-25 --input data-collection/deliverables/2026-09-25/jobs_history_translated.json

python database/weekly_import.py import-collection --historical --week-date 2026-09-06 --input data-collection/deliverables/2026-09-06/jobs_history_translated.json
python database/weekly_import.py import-collection --historical --week-date 2026-09-13 --input data-collection/deliverables/2026-09-13/jobs_history_translated.json
python database/weekly_import.py import-collection --historical --week-date 2026-09-19 --input data-collection/deliverables/2026-09-19/jobs_history_translated.json
```

There is **no requirement** to invent classifications for the three older
weeks. `v_weekly_versions` will show them as `pending`. To add a new, later
week, import its reviewed Li file normally (without `--historical`) using its
folder date. If an older file contains a `source_key` absent from the current
canonical jobs, historical backfill stops; rebuild a separate empty database
chronologically rather than silently inventing a current job.

## 5. Import the matching 25 September classification

All seven analysis paths below must come from **one complete output run**.
`plan-analysis` is a file-only validation and makes no model calls or DB
changes. Keep the quoted path because `classification pipeline` has a space.

```powershell
$li = 'data-collection/deliverables/2026-09-25/jobs_history_translated.json'
$out = 'classification pipeline/output_full'
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
python database/weekly_import.py import-analysis @files --week-date 2026-09-25 --git-commit e4f1b77cc56f048c06196e7a27865d98084c2e2a
```

The importer checks the selected Li file's SHA-256, the complete `source_key`
set, each job's content fingerprints, duplicate decisions and cluster counts.
For this example, 5,139 inputs reconcile to 4,518 analysed postings and 621
duplicate links; 2,902 analysed, non-duplicate jobs are AV-related. The
command returns a `release_key` starting with `draft-`. **Draft does not mean
published.** A different week's classification requires its own output folder,
the matching dated Li file, that date in `--week-date`, and the Git commit
that actually produced that output. Do not reuse the example commit blindly.

## 6. QA, approval and publication

Set `$releaseKey` to the `release_key` printed by `import-analysis`:

```powershell
$releaseKey = 'draft-REPLACE_WITH_THE_PRINTED_KEY'
python database/weekly_import.py qa-release --release-key $releaseKey
python database/weekly_import.py publish-release --release-key $releaseKey
```

Check that QA reports `passed` **and** read any warnings before publishing.
In the 25 September example, one displayed AV job has no extractable skills
and many clusters lack approved names. The database preserves those gaps; it
does not guess missing skills or treat keywords as approved labels. Obtain
the team's release decision before changing the public Dashboard version.

`publish-release` freezes the candidate rows and makes that release current.
If an older week's classification is added later, QA it and use
`publish-release --release-key <older-draft-key> --historical`: it freezes an
older version for `v_weekly_av_*` but **does not** replace the current
Dashboard. A frozen release cannot be edited or rolled back as a normal draft.

## 7. Read the data

For local inspection, connect with the MySQL client, MySQL Workbench or a
read-only application account. These queries show the version contract:

```sql
SELECT week_date, collection_sha256, classification_status, release_status
FROM av_job_profiles.v_weekly_versions ORDER BY week_date;

SELECT week_date, COUNT(*) AS collected_jobs
FROM av_job_profiles.v_weekly_jobs GROUP BY week_date ORDER BY week_date;

SELECT COUNT(*) AS current_av_jobs FROM av_job_profiles.v_dashboard_jobs;
SELECT source_key, company_name, display_title, is_active
FROM av_job_profiles.v_dashboard_jobs LIMIT 10;

SELECT week_date, COUNT(*) AS classified_av_jobs
FROM av_job_profiles.v_weekly_av_jobs GROUP BY week_date ORDER BY week_date;
```

For example, run `& $env:AVDB_MYSQL -h 127.0.0.1 -u root -D av_job_profiles -e 'SELECT * FROM v_weekly_versions ORDER BY week_date'`
or paste the queries into Workbench. The **backend** should use a read-only SQL account
and query `v_dashboard_jobs`, `v_dashboard_job_skills`,
`v_dashboard_skill_demand`, `v_dashboard_clusters`, plus the approved
`v_weekly_*` views for version-aware endpoints. The backend chooses dates and
computes differences; the database does not claim that two cumulative files
are two equally complete crawls. A `pending` classification week can still
show collected job states, but not historical AV-skill results. The **frontend**
calls the backend API, not MySQL. For Power BI, connect locally to the same
read-only views; a static chart is a prototype, not the versioned API.

For a local backend account, a MySQL administrator can execute the following
**after replacing the example secret**. Use `127.0.0.1` for the backend's
MySQL host, and give Power BI its own account if it needs one. This account
cannot write tables or read the internal candidate views:

```sql
CREATE USER 'av_backend'@'127.0.0.1'
  IDENTIFIED BY 'REPLACE_WITH_A_UNIQUE_LOCAL_SECRET';
GRANT SELECT ON av_job_profiles.v_dashboard_jobs TO 'av_backend'@'127.0.0.1';
GRANT SELECT ON av_job_profiles.v_dashboard_job_skills TO 'av_backend'@'127.0.0.1';
GRANT SELECT ON av_job_profiles.v_dashboard_skill_demand TO 'av_backend'@'127.0.0.1';
GRANT SELECT ON av_job_profiles.v_dashboard_clusters TO 'av_backend'@'127.0.0.1';
GRANT SELECT ON av_job_profiles.v_weekly_versions TO 'av_backend'@'127.0.0.1';
GRANT SELECT ON av_job_profiles.v_weekly_jobs TO 'av_backend'@'127.0.0.1';
GRANT SELECT ON av_job_profiles.v_weekly_av_jobs TO 'av_backend'@'127.0.0.1';
GRANT SELECT ON av_job_profiles.v_weekly_av_job_skills TO 'av_backend'@'127.0.0.1';
```

Test by connecting as `av_backend` and selecting from a granted view; a
direct `SELECT` from `jobs` should be denied. The backend must still restrict
which internal history information it returns through public API endpoints.

## 8. Importer command reference

Run `python database/weekly_import.py <command> --help` for exact flags.

| Command | What it does / key arguments | Database effect |
| --- | --- | --- |
| `plan-collection --input FILE [--previous FILE]` | Validate/count a Li file and optionally compare it with an earlier one | None |
| `import-collection --input FILE --week-date YYYY-MM-DD [--historical]` | Select one official Li file for that week; use `--historical` only to backfill an older week | Backup, collection run, observations; normal import also updates latest jobs |
| `plan-analysis --source-input FILE --postings FILE --metadata FILE --av-summary FILE --other-summary FILE --duplicates FILE --failures FILE` | Reconcile one complete Sunjol run against the Li file | None |
| `import-analysis` with the same seven file flags, `--week-date` and `--git-commit` | Check exact weekly pairing and load derived results | Backup, analysis/skills/clusters and draft release |
| `qa-release --release-key KEY` | Check counts, AV-only scope, skill/cluster gaps and release consistency | None; writes only local operation log |
| `publish-release --release-key KEY [--historical]` | Freeze approved draft; without the flag switch current Dashboard, with it preserve current release | Backup and immutable release snapshot |
| `backup [--backup-dir DIR]` | Make a compressed full MySQL dump and checksum | Local `.sql.gz`, no DB data change |
| `restore --file BACKUP --target-db NEW_NAME` | Verify dump and restore **only into a new database name** | New database; never overwrites one |
| `rollback [--batch-id ID]` | Undo only the latest eligible import batch | Backup first; refuses dependent/frozen data |
| `trend-readiness` | Check whether verified, comparable crawls exist | None; current cumulative files do not pass |
| `freeze-release --release-key KEY` | Legacy recovery: freeze an already-published but not-yet-frozen release | Backup and frozen snapshot; not normal MVP flow |

Every parsed operation writes a JSON report and append-only JSONL log under
`database/operation_logs/` by default. Backups go to `database/backups/`.
Both directories are Git-ignored; never upload them as team deliverables.
Use `--audit-dir DIR` or `--backup-dir DIR` where supported to redirect local
files. A failed import is transactional, but do not rely on rollback after
publication: restore a verified backup into a **new** database for recovery.

## 9. Before handing data to the backend

1. Confirm `v_weekly_versions` lists exactly the selected dates/files and
   identifies which dates are still `pending`.
2. Confirm current `v_dashboard_jobs` is AV-only, non-duplicate and linked to
   the intended published release. Do not hard-code the example count.
3. Share the database/view contract and a **read-only account**, not a root
   password or a dump. Agree which weekly endpoints are internal versus public.
4. Record QA warnings, the approved release key and file/Git provenance in
   the team's project records. Client-facing trends need separately verified
   source coverage; date labels alone are not proof of a complete crawl.

For schema relationships and field meanings, see [README.md](README.md).
For weekly-version invariants, see [WEEKLY_VERSIONS.md](WEEKLY_VERSIONS.md).
For release/history semantics, see [STAGE3_RELEASE_HISTORY.md](STAGE3_RELEASE_HISTORY.md).
