# Location and work-mode integration

This feature turns Li's existing `data.location` into structured fields for
student search and the market-analysis report. It uses rules, not a model or
external geocoding service. Source files and classification results are unchanged.

**Database-side code is implemented.** Backend/UI tasks below are hand-off
instructions, not features implemented by this change. Start with
[TEAM_GUIDE](TEAM_GUIDE.md) for local setup and normal imports.

## 1. Field contract

| SQL field | Existing backend JSON field | Purpose |
| --- | --- | --- |
| `location_raw` | `location` | Original collected text, preserved unchanged |
| `country_code` | `countryCode` | Two-letter country code, e.g. `US`, `DE`, `GB` |
| `state_region` | `stateRegion` | State/province/prefecture/region where identifiable |
| `city` | `city` | Identifiable city |
| `remote_type` | `remoteType` | Explicit `remote`, `hybrid`, `onsite`; otherwise NULL |
| `location_parser_version` | Optional additional field | Saved rule version; exposed in frozen AV job views |

Country → region → city is a **country-qualified hierarchy**. A city name can
exist in several countries; keep its country in filter requests. A country may
be known while city/region is not. Remote jobs do not require a city.

| Raw location | Country | Region | City | Work arrangement |
| --- | --- | --- | --- | --- |
| `San Francisco, California, United States (Hybrid)` | `US` | `CA` | `San Francisco` | `hybrid` |
| `Berlin, DE` | `DE` | NULL | `Berlin` | NULL |
| `Germany` | `DE` | NULL | NULL | NULL |
| `Remote - US` | `US` | NULL | NULL | `remote` |
| `Remote - US, Ann Arbor, MI` | `US` | `MI` | `Ann Arbor` | `remote` |
| `Austin, TX \| Berlin, Germany` | NULL | NULL | NULL | NULL |

Rules are conservative, **not a verified worldwide geocoder**:

- Country/region collisions need context: `Berlin, DE` is Germany, whereas
  `Dover, DE` can mean Delaware, US. Unknown city + `DE` stays unresolved.
- A multi-location list never becomes one invented city. Mixed/partially
  unresolved countries stay unknown; recognised same-country lists retain
  only their shared country.
- Do not infer the job country from company headquarters or ATS source region.
- Missing, ambiguous or conflicting evidence stays NULL. City alone does not
  imply onsite; missing city does not imply remote. Long policy text is not a
  work-arrangement declaration. Dictionaries have finite coverage.
- Region/city spellings are not a universal geographic catalogue. US state
  names become abbreviations where recognised; other source formats may retain
  their region names/codes. Use the actual stored values for filter options.
- **Work arrangement is not employment type.** Full-time/part-time/contract
  require separate source facts. This feature reads location text; a work mode
  available only in another source field needs a separately agreed mapping.

## 2. Writes, versions and QA

1. Collection loading validates the raw text, then calls the pure parser.
2. Normal imports fill the four fields in latest `jobs` and that run's
   `job_observations`. Historical imports fill observations without rewinding
   latest jobs.
3. A **new** release freeze also derives fields from that release's raw
   location. This supports old collections without rerunning classification.
4. Already-frozen releases retain their original fields and hashes, including
   NULL values. Reading/reactivating one never silently runs new rules.

Job identity (`source_key`, `job_id`), raw JSON, raw location, source-file
SHA-256, description SHA-1 and canonical source-record SHA-256 are unchanged.
Derived fields are outside the classifier input hash contract. A new public
snapshot has its own row/root hashes; old snapshot hashes remain unchanged.

`plan-collection` / `import-collection` report `location_quality`: populated
field counts, missing raw text, unresolved nonempty text, country/mode counts
and up to 30 unresolved examples. Completed collection metadata saves this
report and parser version. `qa-release` separates **all AV jobs** from **active
AV jobs**: draft coverage previews current rules, frozen coverage reads saved
fields. Coverage is not guaranteed accuracy. Legacy payloads are marked
`legacy/unrecorded` in the report's parser-version counts.

Every command keeps the existing local JSON report/JSONL log. New frozen job
payloads record the rule version; release preparation records that version
and a hash of the relevant contract files. Keep logs, backups and credentials
local, not in GitHub.

See [real-data validation and known QA timing](LOCATION_VALIDATION.md).
Full administrative QA may take minutes; await the command's
result instead of assuming silence means failure or starting another writer.

## 3. Install or refresh views on an explicit target

**No new table-column migration is required for the current MVP schema.** The
columns already exist. Refreshing `views.mysql.sql` exposes the location fields
in the weekly reading interfaces and the parser version in frozen AV job views.
Existing view columns remain available. **Refreshing views does not run the
Python parser or fill the NULL fields in an old frozen release.** Complete
section 4 to create and select a location-enriched release.

For an empty DB, follow TEAM_GUIDE section 3 with the new code. For an existing
DB: verify its name → stop other import/schema writers → `backup` → refresh
views in that same DB → create/QA/activate a new release. Do not reinstall the
fresh schema over populated tables. No test-copy restore is required.

With connection variables/tool paths from TEAM_GUIDE, run in PowerShell 7 from
the repository root. `--database` alone does not override the SQL file's `USE
av_job_profiles;`; this substitutes only that target statement:

Define this helper once in the same PowerShell session. It refreshes views only
in the explicit target; it does not install tables, import files or switch a
release. Section 4 shows when to call it.

```powershell
function Update-LocationViews {
    param([Parameter(Mandatory)][string] $DatabaseName)
    if ($DatabaseName -notmatch '^[A-Za-z0-9_]{1,64}$') { throw 'Invalid database name' }
    $env:MYSQL_PWD = $env:AVDB_PASSWORD
    $connection = @('--host', $env:AVDB_HOST, '--port', $env:AVDB_PORT,
                    '--user', $env:AVDB_USER, '--default-character-set=utf8mb4',
                    '--database', $DatabaseName)
    & $env:AVDB_MYSQL @connection -e 'SELECT DATABASE(); SHOW FULL TABLES;'
    if ($LASTEXITCODE -ne 0) { throw 'Target connection failed' }
    $views = Get-Content -Raw -Encoding utf8 database/views.mysql.sql
    if ([regex]::Matches($views, 'USE av_job_profiles;').Count -ne 1) { throw 'Unexpected SQL target header' }
    $views = $views.Replace('USE av_job_profiles;', ('USE `' + $DatabaseName + '`;'))
    $views | & $env:AVDB_MYSQL @connection
    if ($LASTEXITCODE -ne 0) { throw 'View installation failed; inspect before continuing' }
    & $env:AVDB_MYSQL @connection -e 'SHOW COLUMNS FROM v_weekly_jobs; SHOW COLUMNS FROM v_weekly_av_jobs; SHOW CREATE VIEW v_dashboard_jobs;'
    if ($LASTEXITCODE -ne 0) { throw 'View inspection failed' }
}
```

View DDL is not a rollback-able data transaction; preserve the backup and the
previous code revision. Switching releases back does not undo view definitions.
If view installation fails, stop and inspect the error before activating data;
restore the previous reviewed view definitions if needed. Do not delete the DB.

For a schema predating weekly versions/revisions, use the existing
[006/007 decision table](RELEASE_REVISIONS.md#2-install-before-using-the-new-commands)
for that schema. This feature is not a generic old-schema upgrade;
never rerun an already-applied migration.

## 4. Enhance an old published week without rerunning AI

**Use this route when the old database already has a selected, frozen AV
release.** No Li collection reimport or Sunjol classification rerun is needed.
It upgrades the public representation, not the original input or old snapshot:

```text
Back up the existing database
  → update importer code and refresh views
  → create-release: new draft, same collection and classification
  → qa-release: inspect proposed location/work-mode coverage
  → activate-release: freeze and select the enhanced snapshot
  → verify public/weekly reads; old release remains available to switch back
```

**Two separate operations:** views expose fields; new snapshot creation fills
the fields. Doing only the first operation leaves the old frozen data unchanged.
Run this sequence directly on your existing local database after backing it up.
Sections 4.1–4.7 use **Windows PowerShell 7**; section 4.8 provides the complete
**macOS zsh / Bash** equivalent. Run commands from the repository root. Neither
route requires a separate test database.

### 4.1 Get the new code and configure the original target

Finish or preserve your own uncommitted work first; do not force-reset it.
After this PR is merged:

```powershell
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
python -m pip install -r database/requirements-import.txt
```

Before merge, use the reviewed `nyx/location-importer-integration` PR branch
instead of `main`; old main does not include this upgrade. Set connection
variables and MySQL tool paths as in TEAM_GUIDE section 3. Set the actual
original database name explicitly, not the example name blindly:

```powershell
$originalDb = 'REPLACE_WITH_YOUR_EXISTING_DATABASE'
$weekDate = '2026-09-25'               # target the week actually classified
$env:AVDB_NAME = $originalDb
$env:MYSQL_PWD = $env:AVDB_PASSWORD
& $env:AVDB_MYSQL --host $env:AVDB_HOST --port $env:AVDB_PORT --user $env:AVDB_USER --database $env:AVDB_NAME -e 'SELECT DATABASE(); SELECT week_date,classification_status,release_key FROM v_weekly_versions ORDER BY week_date;'
if ($LASTEXITCODE -ne 0) { throw 'Check target and schema before continuing' }
```

Only the database operator runs the following write steps. Stop other importer
or schema writers. `REPLACE_WITH_YOUR_EXISTING_DATABASE` is a placeholder, not
a DB to create. A much older schema must follow the migration decision table
in section 3 first.

### 4.2 Back up the existing database, then refresh its views directly

The CLI prints JSON; these commands capture the returned backup path without
guessing a filename. Save this path for recovery. Define
`Update-LocationViews` from section 3 before calling it here.

```powershell
$backupResult = python database/weekly_import.py backup | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Backup failed; do not continue' }
$backupFile = $backupResult.result.backup
if (-not $backupFile) { throw 'Missing backup path' }
Update-LocationViews -DatabaseName $env:AVDB_NAME
```

Confirm `SHOW CREATE VIEW` refers to `$originalDb`. Continue 4.3–4.6 in this
same database. The views are now updated, but the old frozen release data and
official selection remain unchanged until activation.

### 4.3 Identify the selected week release and create a new draft

List **all** releases so the current dashboard is found even if it belongs to
a different week. The two selected keys are deliberate activation safeguards.

```powershell
$catalog = python database/weekly_import.py list-releases | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Release inspection failed' }
$weekSelection = @($catalog.result.releases | Where-Object { $_.week_date -eq $weekDate -and $_.selected_for_week })
$currentSelection = @($catalog.result.releases | Where-Object { $_.current_dashboard })
if ($weekSelection.Count -ne 1 -or $currentSelection.Count -ne 1) { throw 'Expected one selected week release and one current dashboard' }
if (-not $weekSelection[0].snapshot_frozen_at) { throw 'Selected release is not frozen; follow the legacy-release guide first' }
$oldWeek = $weekSelection[0].release_key
$current = $currentSelection[0].release_key
$historicalArgs = @()
if ([datetime]$weekDate -lt [datetime]$currentSelection[0].week_date) { $historicalArgs = @('--historical') }
$draftResult = python database/weekly_import.py create-release --from-release-key $oldWeek --reason 'Populate structured location and work mode' | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Draft creation failed' }
$new = $draftResult.result.release_key
if (-not $new) { throw 'Missing new release key' }
```

The new draft reuses the same collection, analysis and cluster run. It does
not copy or overwrite old frozen rows, make paid calls, or become public yet.
For an older week, `$historicalArgs` preserves the newer current dashboard;
for the current week it is empty. Do not add `--historical` to the current
dashboard's own week.

### 4.4 Check QA and proposed location coverage

```powershell
$qa = python database/weekly_import.py qa-release --release-key $new | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $qa.result.status -ne 'passed') { throw 'QA failed; do not activate' }
$qa.result.location_quality | ConvertTo-Json -Depth 10
$qa.result.warnings
```

Inspect country/city/region/mode counts for **all AV** and **active AV** jobs,
unresolved examples, and unchanged AV population. NULL is valid when evidence
is insufficient; QA passing does not certify perfect geocoding or remove the
existing skill/cluster warnings. Obtain the team's release approval before
updating its intended DB. Full QA may take minutes; wait for its exit status.

### 4.5 Freeze and activate the reviewed snapshot

```powershell
python database/weekly_import.py activate-release --release-key $new --expected-week-release $oldWeek --expected-current-release $current @historicalArgs --reason 'Reviewed location-enriched release'
if ($LASTEXITCODE -ne 0) { throw 'Activation did not complete normally; inspect its report and selections before retrying' }
```

Activation parses the release's preserved location text, freezes the enriched
fields with their parser version/hashes, then atomically switches the official
selection. If another operator changed a selected key, the command stops
rather than silently replacing their release. A prepared frozen draft may
remain after a failed switch; it is not automatically official/public.

### 4.6 Verify the public and weekly interfaces

```powershell
python database/weekly_import.py qa-release --release-key $new
if ($LASTEXITCODE -ne 0) { throw 'Final QA needs investigation' }
python database/weekly_import.py list-releases --week-date $weekDate
$env:MYSQL_PWD = $env:AVDB_PASSWORD
& $env:AVDB_MYSQL --host $env:AVDB_HOST --port $env:AVDB_PORT --user $env:AVDB_USER --database $env:AVDB_NAME -e 'SELECT release_key,COUNT(*) AS active_av_jobs,COUNT(country_code) AS country_known,COUNT(city) AS city_known,COUNT(state_region) AS region_known,COUNT(remote_type) AS work_mode_known FROM v_dashboard_jobs WHERE is_active=TRUE GROUP BY release_key;'
if ($LASTEXITCODE -ne 0) { throw 'Published-view verification failed' }
& $env:AVDB_MYSQL --host $env:AVDB_HOST --port $env:AVDB_PORT --user $env:AVDB_USER --database $env:AVDB_NAME -e 'SELECT week_date,release_key,COUNT(*) AS av_jobs,COUNT(country_code) AS country_known FROM v_weekly_av_jobs GROUP BY week_date,release_key ORDER BY week_date;'
if ($LASTEXITCODE -ne 0) { throw 'Weekly-view verification failed' }
```

After activation:

- `v_dashboard_jobs` reads the enriched fields **when this is the current
  dashboard week**. An older-week historical activation leaves today's
  dashboard unchanged.
- `v_weekly_av_jobs` reads the enriched selected snapshot for the target week.
- The previous frozen release is intact, with unchanged rows/hashes, and can
  be selected again. No classification rerun is necessary.

This does **not** rewrite old `jobs` / `job_observations`. Their historical
`v_weekly_jobs` values can remain NULL; see section 5 if all raw historical
collection fields must be rebuilt. Refreshing a view alone cannot fill them.

### 4.7 Switch back if needed; keep both versions

Reinspect `list-releases`. The following assumes no intervening switch: `$new`
is still the target week's selection. For a current-week upgrade the expected
current key is `$new`; for an older-week upgrade it remains `$current`.

```powershell
python database/weekly_import.py list-releases
$expectedCurrentAfter = if ($historicalArgs.Count -gt 0) { $current } else { $new }
python database/weekly_import.py activate-release --release-key $oldWeek --expected-week-release $new --expected-current-release $expectedCurrentAfter @historicalArgs --reason 'Revert location enhancement after review'
if ($LASTEXITCODE -ne 0) { throw 'Reversion stopped; recheck actual selections' }
```

Switching back reuses the exact old frozen data; it does not rebuild it, delete
the new release or undo the view definitions. If selections changed, stop and
follow the [reversion guide](RELEASE_REVISIONS.md#7-switch-back-retain-both-versions)
with reviewed current keys. Do not directly UPDATE snapshots or observations.

### 4.8 macOS: update the existing database (zsh / Bash)

Use Python 3 and an installed MySQL server with `mysql` and `mysqldump` on
your PATH. The commands detect their paths rather than assuming an Apple
Silicon or Intel Homebrew directory. If either `command -v` fails, fix your
MySQL installation/PATH before continuing. MySQL server must already be
running. Do not paste Windows `$env:` assignments into a macOS terminal.

**Setup:** preserve your own work before switching branches. Use `main` only
after this PR is merged; before merge use the reviewed
`nyx/location-importer-integration` branch instead.

```bash
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r database/requirements-import.txt

export AVDB_HOST='127.0.0.1'
export AVDB_PORT='3306'
export AVDB_USER='REPLACE_WITH_YOUR_DATABASE_USER'
export AVDB_NAME='REPLACE_WITH_YOUR_EXISTING_DATABASE'
export AVDB_MYSQL="$(command -v mysql)"
export AVDB_MYSQLDUMP="$(command -v mysqldump)"
# Hidden password entry: works in both zsh and Bash.
printf 'MySQL password: '
read -r -s AVDB_PASSWORD
printf '\n'
export AVDB_PASSWORD
export MYSQL_PWD="$AVDB_PASSWORD"
week_date='2026-09-25'  # replace with the week actually classified

mysql_target() {
  "$AVDB_MYSQL" --host "$AVDB_HOST" --port "$AVDB_PORT" \
    --user "$AVDB_USER" --default-character-set=utf8mb4 \
    --database "$AVDB_NAME" "$@"
}
mysql_target -e 'SELECT DATABASE(); SELECT week_date,classification_status,release_key FROM v_weekly_versions ORDER BY week_date;'
```

Check the displayed database and week before writing. **Stop after any failed
command**; these blocks are step-by-step commands, not an unattended script.
Do not proceed with unset tool paths or unedited placeholders. No credentials
or virtual environment should be committed.

**Back up, then refresh views in the same database.** Keep the backup path
printed in the JSON result. Stop other import/schema writers first. This uses
a temporary SQL file, validates the target name, and replaces only the one
`USE` header; `--database` alone would not override that header.

```bash
python database/weekly_import.py backup
# Continue only after backup succeeds and its path is saved.
refresh_location_views() {
  local views_file
  views_file="$(mktemp)" || return 1
  python - "$AVDB_NAME" "$views_file" <<'PY'
import re
import sys
from pathlib import Path
name, output = sys.argv[1:]
if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", name):
    raise SystemExit("Invalid database name")
sql = Path("database/views.mysql.sql").read_text(encoding="utf-8")
if sql.count("USE av_job_profiles;") != 1:
    raise SystemExit("Unexpected SQL target header")
Path(output).write_text(sql.replace("USE av_job_profiles;", f"USE `{name}`;"), encoding="utf-8")
PY
  if [ "$?" -ne 0 ]; then rm -f -- "$views_file"; return 1; fi
  mysql_target < "$views_file"
  local view_status=$?
  rm -f -- "$views_file"
  return "$view_status"
}
refresh_location_views
# Continue only if the refresh succeeds.
mysql_target -e 'SHOW COLUMNS FROM v_weekly_jobs; SHOW COLUMNS FROM v_weekly_av_jobs; SHOW CREATE VIEW v_dashboard_jobs;'
```

**Inspect and create:** from `list-releases`, copy the target week's
`selected_for_week` frozen release key and the global `current_dashboard`
release key. They may belong to different weeks. Do not use guessed keys.

```bash
python database/weekly_import.py list-releases
old_week='PASTE_TARGET_WEEK_SELECTED_RELEASE_KEY'
current='PASTE_CURRENT_DASHBOARD_RELEASE_KEY'
historical_args=()
# ONLY if week_date is older than the current dashboard's week:
# historical_args=(--historical)
python database/weekly_import.py create-release --from-release-key "$old_week" \
  --reason 'Populate structured location and work mode'
# Copy result.release_key from this successful command:
new_release='PASTE_NEW_DRAFT_RELEASE_KEY'
python database/weekly_import.py qa-release --release-key "$new_release"
```

Review `status: passed`, warnings and `location_quality` for all/active AV
jobs. Passing QA is not perfect-geocoding certification. Obtain approval for
the release before activation. If QA fails, stop; do not run the next block.

**Activate and verify:** for an older target week set the historical array
above; for the current week leave it empty. The empty-array syntax below
works in zsh and Bash.

```bash
python database/weekly_import.py activate-release --release-key "$new_release" \
  --expected-week-release "$old_week" --expected-current-release "$current" \
  "${historical_args[@]}" --reason 'Reviewed location-enriched release'
# Continue only after successful activation.
python database/weekly_import.py qa-release --release-key "$new_release"
python database/weekly_import.py list-releases --week-date "$week_date"
mysql_target -e 'SELECT release_key,COUNT(*) AS active_av_jobs,COUNT(country_code) AS country_known,COUNT(city) AS city_known,COUNT(state_region) AS region_known,COUNT(remote_type) AS work_mode_known FROM v_dashboard_jobs WHERE is_active=TRUE GROUP BY release_key;'
mysql_target -e 'SELECT week_date,release_key,COUNT(*) AS av_jobs,COUNT(country_code) AS country_known FROM v_weekly_av_jobs GROUP BY week_date,release_key ORDER BY week_date;'
```

**Optional switchback:** first inspect selections again. The following only
applies if no intervening switch occurred. It restores old frozen data, not
old view definitions; keep the backup for structural recovery.

```bash
python database/weekly_import.py list-releases
expected_current_after="$new_release"
if [ "${#historical_args[@]}" -gt 0 ]; then expected_current_after="$current"; fi
python database/weekly_import.py activate-release --release-key "$old_week" \
  --expected-week-release "$new_release" \
  --expected-current-release "$expected_current_after" \
  "${historical_args[@]}" --reason 'Revert location enhancement after review'
```

The actor label defaults to the local operating-system user on both platforms.
Keep the same terminal open to retain variables. Neither route changes backend
or frontend `.env` files; consumers keep their existing database connection.

## 5. Structured location for all raw historical collections

For a development copy, create a **separate empty database**, install current
schema/views, reimport the original dated Li snapshots and attach only the
matching classifications that actually exist. Follow TEAM_GUIDE sections 4–6:
newest first, older files with `--historical`, subject to the documented key
coverage check; if it fails, rebuild chronologically.

Unclassified weeks supply geography through `v_weekly_jobs` and remain
`pending` in `v_weekly_versions`. Do not pair September 25 analysis with another
date. Future normal collections fill fields automatically. Never edit a file
to bypass exact-file/same-week protections. Keep the old DB until the new
copy's counts, keys, hashes and application reads are verified. Switching
backend/BI connections is an explicit owner decision.

## 6. Leon: backend tasks

Current code maps all four existing JSON fields and supports `country` and
`remote_type` filters. Keep published-view reads. Parser version is additive
and optional to expose; old DTO fields require no renaming.

For country → region → city filtering:

1. Add optional `state_region` / `city` query parameters in
   `backend/app/routes/jobs.py` and `JobRepository.list_jobs`.
2. Pass them to `_build_filters`; require country for a city/region request
   (HTTP 400 if missing), or explicitly document a different worldwide search.
3. Append **parameterised**, not string-interpolated, predicates:

   ```python
   if state_region:
       clauses.append('j.state_region = %s')
       params.append(state_region)
   if city:
       clauses.append('j.city = %s')
       params.append(city)
   ```

4. Validate country codes and `remote|hybrid|onsite`. NULL evidence is unknown,
   not a guessed country. No filter must continue to include unknown jobs.
5. Add a proposed `GET /api/locations` or equivalent options response based
   on the same **current, active AV** release, with country-qualified region/
   city options and available work arrangements. Avoid fixed country lists.
6. Pin related reads/caches to a release and retain server-side pagination.

Options SQL example:

```sql
SELECT country_code, state_region, city, COUNT(*) AS job_count
FROM v_dashboard_jobs WHERE is_active=TRUE AND country_code IS NOT NULL
GROUP BY country_code, state_region, city
ORDER BY country_code, state_region, city;
```

Existing requests: `/api/jobs?country=US`, `/api/jobs?remote_type=hybrid`.
After implementing the new parameters:
`/api/jobs?country=US&state_region=CA&city=San%20Francisco`.
Test each filter and combinations against SQL counts, pagination totals,
nulls, details and release reversion. Old demo connections remain old until
their owner upgrades/switches them.

## 7. Thushamini / SJ: portal and analysis

### Frontend

- Country option: label `United States`, **value `US`**. Options should come
  from actual published data; a code is an acceptable unknown-label fallback.
- Enable dependent city/region controls only after the backend implements
  their parameters/options. A new dropdown alone does not implement filtering.
- Country changes clear region/city; region changes clear city. Encode URL
  values. No filter includes unknown jobs; a specific country excludes them.
- Display city/region/country where known, retaining raw `location` as fallback.
  Never display `null` as text or default to onsite.
- Label `remoteType` **Work arrangement**, not Employment type. Hide unsupported
  employment-type controls or clearly mark them unavailable.
- Test reset, combinations, empty/error/loading states and no known work modes.
  Logos are unrelated and their existing letter fallback can remain unchanged.

### Market-analysis report / BI

`v_dashboard_jobs` / `v_weekly_av_jobs` contain non-duplicate AV jobs, including
inactive ones; student search adds `is_active=TRUE`. `v_weekly_jobs` contains
**all** source postings, including non-AV/duplicate rows. Label the denominator.

```sql
SELECT COALESCE(country_code,'unknown') AS country, COUNT(*) AS jobs
FROM v_dashboard_jobs WHERE is_active=TRUE
GROUP BY country_code ORDER BY jobs DESC;

SELECT state_region, city, COUNT(*) AS jobs
FROM v_dashboard_jobs WHERE is_active=TRUE AND country_code='US'
GROUP BY state_region, city;

SELECT week_date, COALESCE(country_code,'unknown') AS country, COUNT(*) AS jobs
FROM v_weekly_av_jobs WHERE is_active=TRUE
GROUP BY week_date, country_code ORDER BY week_date, country;

SELECT week_date, classification_status, release_key
FROM v_weekly_versions ORDER BY week_date;
```

Keep unknown countries as a separate bucket. Use `COUNT(DISTINCT job_id)` when
joining many-to-many skills. Raw collection-location history is not historical
**AV/skill** demand without matching analyses. Files are cumulative snapshots;
their folder dates label versions, not guaranteed complete fresh crawls. Apply
the existing time/trend contract and do not claim trends from missing analyses.

### Ownership and access

| Owner | Task |
| --- | --- |
| Li | Preserve source location/work-mode evidence; agree future structured-field mappings |
| SJ | Review examples/unresolved cases; propose tested rule corrections; read views for analysis |
| Nyx / database operator | Parser integration, imports, backups, view upgrade, QA and version switching |
| Leon | API params, qualified options, validation, queries/response mapping and backend tests |
| Thushamini | Labels/values, cascading selection, display fallbacks and frontend/API tests |

No direct repairs of core tables by consumers. Backend/BI use SELECT on approved
views; frontend calls API only and never receives MySQL credentials.
