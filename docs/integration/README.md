# Integration handoff: website, published data and Docker

For Sunjol and other members finishing the project integration. Run commands from the **repository root**, except where a component directory is specified. This guide supplements, rather than replaces, the component operating guides.

## 1. Start here: verified GitHub position

Checked on **13 October 2026**:

- **#73** is merged: the complete React/Flask integration, faceted search, numeric salary controls, skills/clusters pages, icons and tests are on `main`.
- **#54** is closed: do not restore its older parallel frontend implementation over `main`.
- **#57**, **#72** and **#74** are merged: classification changes, Tableau and the final weekly plan are available.
- **#76** (`docker-setup`, checked head `cf2c798`) and **#75** (root README) are still open. Docker instructions below describe integration work against that checked PR, **not a container release already validated by Nyx**. Recheck their latest heads before acting.

The website startup guide already exists at [frontend/README.md](../../frontend/README.md); the API guide is [backend/README.md](../../backend/README.md). Do not wait for another frontend README to start the native website.

```bash
git fetch origin
git switch main
git pull --ff-only origin main
```

Commit or otherwise preserve your own local work before switching branches. Keep Docker work on your branch and integrate reviewed `main` normally; do not reset another member's work.

## 2. What connects to what

```text
Li's dated English file + Sunjol's matching analysis files
                  -> Python importer -> selected MySQL published release
                  -> Flask API -> React portal
                  -> Tableau (MySQL views or a packaged extract)
```

| Component | Configuration / contract | Must not do |
| --- | --- | --- |
| Importer | `AVDB_HOST`, `AVDB_PORT`, `AVDB_NAME`, `AVDB_USER`, `AVDB_PASSWORD` | Publish arbitrary mismatched files or bypass release selection |
| Flask | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`; published/weekly views | Write directly to importer-owned tables |
| React | Build/development `VITE_API_BASE_URL`; JSON API responses | Connect directly to MySQL or silently substitute sample jobs |
| Tableau | Published MySQL views or an explicitly dated extract | Present a one-snapshot posting-date distribution as measured weekly market change |

The application uses **one MySQL schema, `av_job_profiles`** in the standard setup. Importer and backend must point to the same server, port and schema. The classifier's optional SQLite file is an analysis/cache/evaluation artifact, **not the website database**. `--db` is optional for classification; it does not replace MySQL. Do not copy the classifier's separate `schema.mysql.sql` over the database/importer schema. The authoritative application schema and views are `database/schema.mysql.sql` and `database/views.mysql.sql`.

## 3. Run the current website without Docker

Prerequisites: Node.js/npm, Python, and a populated MySQL database with a selected published release. A schema with empty views is not sufficient. For a new database, follow [TEAM_GUIDE sections 3–6](../../database/TEAM_GUIDE.md); for a populated database follow the documented upgrade path instead of reinstalling the fresh schema.

### 3.1 Backend configuration

Create **`backend/.env`**, keeping real credentials private:

```dotenv
API_HOST=127.0.0.1
API_PORT=5000
FLASK_DEBUG=false
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=av_job_profiles
DB_USER=av_backend
DB_PASSWORD=YOUR_LOCAL_READ_ONLY_PASSWORD
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

Use the actual server/port/schema if yours differs. Configure the read-only account's dashboard and weekly-view grants as described in [TEAM_GUIDE](../../database/TEAM_GUIDE.md); root is not the recommended backend identity.

**Windows PowerShell — Terminal A:**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe wsgi.py
```

**macOS/Linux — Terminal A:**

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python wsgi.py
```

Keep that terminal running. In a browser, check `http://127.0.0.1:5000/api/health`, `/api/health/db`, `/api/jobs?page_size=1` and `/api/locations`. Service health alone does not establish that job data is published.

### 3.2 Frontend configuration and startup

Create **`frontend/.env`**:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:5000
# Optional public logo key, never an sk_ secret:
# VITE_LOGO_DEV_TOKEN=pk_...
```

**Windows, macOS or Linux — Terminal B, initially at repository root:**

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open **`http://127.0.0.1:5173/jobs`**. Also check `/clusters`, `/trends` and a job's detail page. Restart Vite after `.env` changes. If ports are occupied, choose unused ports and update the frontend API base and backend CORS origins together; do not kill unrelated services.

Logos are optional. Without a Logo.dev key, the site tries a company website icon and then falls back to initials. Lack of external icons must not block jobs or filters.

## 4. Establish real published data

### 4.1 Use the bundled, matching sample without paid AI

The repository already contains:

- Li: `data-collection/deliverables/2026-09-25/jobs_history_translated.json`.
- Sunjol: `classification pipeline/output_full/`.

Use this exact pair for the initial end-to-end setup. A later Li file cannot be paired with that older classification merely because both contain `source_key` fields. The importer checks the exact source file, fingerprints and outcome coverage. A week date is an explicit version label, not the last posting date. See [TEAM_GUIDE](../../database/TEAM_GUIDE.md) for optional older collection-only versions.

Install `database/requirements-import.txt` in a Python environment and configure the `AVDB_*` variables and MySQL client tools as instructed there. `backend/.env` is not a substitute for importer configuration.

```bash
python database/weekly_import.py plan-collection --input data-collection/deliverables/2026-09-25/jobs_history_translated.json
python database/weekly_import.py import-collection --week-date 2026-09-25 --input data-collection/deliverables/2026-09-25/jobs_history_translated.json
```

`import-collection` is for a week not already selected. If the week is already imported, inspect its version/release rather than blindly repeating or replacing it.

**Windows PowerShell — one complete classification run:**

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

**macOS/Linux bash/zsh:**

```bash
li='data-collection/deliverables/2026-09-25/jobs_history_translated.json'
out='classification pipeline/output_full'
files=(--source-input "$li" --postings "$out/postings_all.json"
       --metadata "$out/run_metadata.json"
       --av-summary "$out/av_relevant/cluster_summary.csv"
       --other-summary "$out/not_av_relevant/cluster_summary.csv"
       --duplicates "$out/duplicates_removed.csv" --failures "$out/llm_failures.csv")
python3 database/weekly_import.py plan-analysis "${files[@]}"
python3 database/weekly_import.py import-analysis "${files[@]}" --week-date 2026-09-25 --git-commit e4f1b77cc56f048c06196e7a27865d98084c2e2a
```

That commit is the documented provenance for the bundled output, **not** the commit to claim for a new run. For newly generated output, record its actual producing commit, matching file/date and parameters. Do not use today's `HEAD` as historical provenance for older output.

### 4.2 Drafts do not appear on the website until publication

Using the actual release key printed by `import-analysis`:

```bash
python database/weekly_import.py qa-release --release-key ACTUAL_DRAFT_KEY
python database/weekly_import.py publish-release --release-key ACTUAL_DRAFT_KEY
python database/weekly_import.py list-releases --week-date 2026-09-25
```

Use `python3` on macOS/Linux if appropriate. Run these individually: stop on failure and inspect QA warnings before publication. This is the initial-publication route. For an existing frozen release, use [RELEASE_REVISIONS](../../database/RELEASE_REVISIONS.md), not another initial import/publication.

If published locations are null, follow [LOCATION_INTEGRATION](../../database/LOCATION_INTEGRATION.md): back up, update the applicable code/views, create a new draft reusing the existing analysis, QA it and activate it using the **actual current/weekly expected release keys**. Use `none` only when no selection exists. Refreshing view definitions alone cannot fill an old frozen snapshot.

Read-only checks in MySQL:

```sql
SELECT week_date, classification_status, release_status
FROM v_weekly_versions ORDER BY week_date;
SELECT release_key, COUNT(*) AS av_records,
       SUM(is_active = TRUE) AS active_av_records,
       SUM(country_code IS NOT NULL) AS known_countries
FROM v_dashboard_jobs GROUP BY release_key;
```

The previously validated 25 September example has **2,902 AV records / 2,412 active AV records**; the portal lists active jobs. These are example counts, not hard-coded acceptance values for every future run or filter. Backups and operation logs stay local; do not upload them or passwords.

## 5. What Sunjol needs to finish in Docker PR #76

These findings refer to checked head `cf2c798`; verify any newer corrections first. This guide intentionally documents required changes rather than silently modifying another member's Docker branch.

### 5.1 Route frontend requests through nginx

Both `frontend/src/api/jobs.js` and `frontend/src/api/insights.js` currently default to `http://127.0.0.1:5000`. The Docker backend is not exposed at that host port. The browser must request the **same-origin** `/api/...` served by nginx, not Docker's internal `http://backend:5000` hostname.

Recommended configuration contract in **both** API modules:

```javascript
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:5000"
).replace(/\/+$/, "");
```

Use `??` rather than `||` so an explicitly empty Docker build value stays empty. Existing calls already append `/api/jobs` or `/api/insights`: **do not set the base to `/api`**, which would duplicate that prefix.

In the frontend Dockerfile's **build stage**, before `npm run build`:

```dockerfile
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
```

Vite configuration is baked into the compiled JS. Changing a runtime container environment variable without rebuilding the frontend is insufficient. For local development, keep the full API origin in `frontend/.env`.

### 5.2 Re-resolve the backend service after recreation

The checked nginx config uses a fixed startup resolution. Apply Li's suggested Docker DNS configuration and retain the existing proxy headers:

```nginx
resolver 127.0.0.11 valid=10s ipv6=off;
location /api/ {
    set $backend_upstream http://backend:5000;
    proxy_pass $backend_upstream;
    # retain existing proxy_set_header lines
}
```

Validate syntax and actual `/api/jobs` proxying, then recreate the backend and verify that the website recovers. Do not claim Watchtower resilience from a syntax check alone. Leave automatic updating disabled until the base application is verified; pin a tested image/commit for delivery.

### 5.3 Match the latest classifier and importer contracts

- The current classifier uses **`thenlper/gte-base`**. The checked Dockerfile preloads `all-MiniLM-L6-v2`. Preload the configured model instead and verify that inference finds its cache; otherwise the promised offline first run still downloads another model.
- Li's MariaDB/mysqldump incompatibility was addressed by changing the importer base to `mysql:8.4`. Build that image and run a real backup before declaring the fix verified. This guide has not performed that container build.
- Every `import-collection` and `import-analysis` command requires **`--week-date YYYY-MM-DD`**. The checked DOCKER.md collection-import example omits it.
- Include all seven analysis file flags, QA and explicit publication/activation. Container creation alone does not import or publish data.
- Remove DOCKER.md's stale statement that React still reads static sample jobs. The merged #73 frontend uses the real API.
- Cached classifications can avoid paid calls **only on valid cache hits**. New/changed jobs, changed model/prompt or bypassed cache may incur costs. Do not promise that every rerun is free.
- Container image auto-update is not a weekly pipeline scheduler. Collection, translation, analysis, import and publication are still separate explicit operations unless orchestration is implemented and tested.

### 5.4 Existing output needs a visible container mount

The checked Compose mounts `classification pipeline/output/`, not the bundled `output_full/`. For a no-paid-call demo, copy the bundled output into the mounted tree without changing the original:

```powershell
# Windows: destination must not already contain another run.
New-Item -ItemType Directory -Force 'classification pipeline/output' | Out-Null
if (Test-Path 'classification pipeline/output/2026-09-25') { throw 'Destination already exists; inspect it before copying.' }
Copy-Item -LiteralPath 'classification pipeline/output_full' -Destination 'classification pipeline/output/2026-09-25' -Recurse
```

```bash
# macOS/Linux: destination must not already contain another run.
mkdir -p 'classification pipeline/output'
if [ -e 'classification pipeline/output/2026-09-25' ]; then echo 'Destination exists; inspect it before copying.'; exit 1; fi
cp -R 'classification pipeline/output_full' 'classification pipeline/output/2026-09-25'
```

Inside the importer, that run is `/repo/classification pipeline/output/2026-09-25`; inside the classifier, collected files are `/app/input/<date>/...`. Host paths are not interchangeable with container paths. Quote paths containing spaces.

## 6. Container verification sequence — after the fixes above

Start Docker Desktop (Windows/macOS) or the Docker daemon (Linux). The checked local machine has the Docker CLI but its Linux engine is **not currently available**, so this guide does not claim an end-to-end Docker execution.

On the integrated Docker branch, from the repository root:

```powershell
# Windows: do not overwrite an existing configured .env.
if (-not (Test-Path .env)) { Copy-Item .env.docker.example .env }
```

```bash
# macOS/Linux: do not overwrite an existing configured .env.
if [ ! -e .env ]; then cp .env.docker.example .env; fi
```

Edit passwords privately; set `JOB_PULL_POLICY=build` for local integration testing. If local MySQL already uses host 3306, choose an unused `DB_HOST_PORT` such as 3307. Docker services still connect internally to **db:3306**. Then:

```bash
docker compose config --quiet
docker compose build backend frontend importer
docker compose up -d db backend frontend
docker compose ps
docker compose logs --tail=60 backend frontend
docker compose run --rm --build importer backup
docker compose run --rm --build importer plan-collection --input data-collection/deliverables/2026-09-25/jobs_history_translated.json
docker compose run --rm --build importer import-collection --week-date 2026-09-25 --input data-collection/deliverables/2026-09-25/jobs_history_translated.json
```

Validate the staged seven-file pair (this single-line command works in PowerShell and bash):

```bash
docker compose run --rm --build importer plan-analysis --source-input data-collection/deliverables/2026-09-25/jobs_history_translated.json --postings "classification pipeline/output/2026-09-25/postings_all.json" --metadata "classification pipeline/output/2026-09-25/run_metadata.json" --av-summary "classification pipeline/output/2026-09-25/av_relevant/cluster_summary.csv" --other-summary "classification pipeline/output/2026-09-25/not_av_relevant/cluster_summary.csv" --duplicates "classification pipeline/output/2026-09-25/duplicates_removed.csv" --failures "classification pipeline/output/2026-09-25/llm_failures.csv"
```

After that succeeds, repeat that exact command with **`import-analysis`** instead of `plan-analysis` and append **`--week-date 2026-09-25 --git-commit e4f1b77cc56f048c06196e7a27865d98084c2e2a`**. For a new run use its actual date and producing commit, not this example. Use the returned draft key below, run each command separately, and stop on a failed check:

```bash
docker compose run --rm --build importer qa-release --release-key ACTUAL_DRAFT_KEY
docker compose run --rm --build importer publish-release --release-key ACTUAL_DRAFT_KEY
docker compose run --rm --build importer list-releases --week-date 2026-09-25
```

Inspect existing selections instead of repeating initial imports if the volume already contains that week. Use the revision/activation guide for replacements.

Visit `http://localhost:8080/api/health/db`, `/api/jobs?page_size=1`, `/api/locations`, `/api/insights` and `http://localhost:8080/jobs` (or the chosen `WEB_PORT`). The browser Network panel must show same-origin `/api/...` requests, not `127.0.0.1:5000`.

```bash
docker compose exec frontend nginx -t
docker compose up -d --force-recreate backend
docker compose logs --tail=60 frontend backend
```

Confirm real jobs still load after backend recreation. Keep automatic image updates off until this passes. `docker compose down` stops the stack while retaining named-volume data. **Do not use `docker compose down -v` for routine troubleshooting**: it deletes the MySQL data and classifier cache.

## 7. Symptom checklist and help boundaries

| Symptom | Check / action |
| --- | --- |
| Healthy API, zero jobs | Check that backend and importer use the same MySQL target and that a release is selected/published. Do not rerun paid classification to fix release selection. |
| Jobs load, country returns zero | Inspect `/api/locations` and job structured fields; activate an enriched release if null. Send `US`, not a full country name; keep country-qualified region/city filters. |
| Docker site cannot reach API | Check baked API base and nginx proxy; browser `localhost` is the visitor's computer, not the backend container. |
| 502 after container update | Check Docker DNS/re-resolution and backend readiness; use section 5.2 and actual restart tests. |
| Import fails before writing | Check mysql/mysqldump compatibility, backups, exact inputs/date and MySQL target. Read the operation report; do not disable validation. |
| Cannot see bundled classification files | Confirm the `output/` mount or stage the reviewed `output_full/` as in section 5.4. |
| Missing logos | Test optional external icon service/public key; initials are the supported fallback. Never put a secret logo key into Vite. |
| Only one history point | Add a matching dated classification later; do not invent trend data or relabel posting-month counts as weekly changes. |

**Responsibilities:** Sunjol owns Docker/orchestration and classifier execution; Li supplies collector/translator settings and coverage; Leon checks Flask configuration/API access; Thushamini checks website operation; Nyx supports importer/version/publication contracts; Seonjeong checks Tableau data scope. Changes crossing those boundaries need the relevant owner's review, not a separate competing database model.

For a blocker, share the commit/image tag, operating system, command, selected week/release, HTTP status or redacted error, and relevant logs. **Never share passwords, API keys or full `.env` files.**

## 8. Verification record and delivery evidence

- #73's previously recorded validation: 113 backend tests, 46 frontend tests, production build and published-MySQL API smoke passed. This is evidence for that version, not proof that #76 containers pass.
- Commands, configuration names and file flags were checked against `main` at `a38ec92` and the referenced Docker head. `plan-collection` and the seven-file `plan-analysis` example both ran successfully: 5,139 source records reconcile to 4,518 analysed records plus 621 duplicates (2,902 AV / 1,616 other; no failed outcomes). These were file-only checks, not imports or paid analysis. The checked Compose configuration passed `docker compose config --quiet` using example credentials without starting a container.
- Docker image building, client-backup execution, nginx proxying and clean-machine container startup remain Sunjol's integration acceptance checks until completed and recorded.
- Preserve a tested commit/image tag, exact input/output versions, release key, backup/recovery instructions and actual client handover status.

Component references: [frontend](../../frontend/README.md), [backend](../../backend/README.md), [database operations](../../database/TEAM_GUIDE.md), [release revisions](../../database/RELEASE_REVISIONS.md), [location integration](../../database/LOCATION_INTEGRATION.md), [collector](../../data-collection/README.md), [classifier](../../classification%20pipeline/README.md), [Docker PR #76](https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles/pull/76).

AI assisted in drafting this guide; configuration and command claims were checked against the repository. Unexecuted Docker steps are identified explicitly.
