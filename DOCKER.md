# Running AV Job Profiles with Docker

Every part of the project runs in a container:

| Service | Folder | What it does | Runs |
| --- | --- | --- | --- |
| `collector` | `data-collection/` | Collects jobs from careers sites, translates them (Azure) | on demand |
| `classifier` | `classification pipeline/` | LLM classification, embeddings, clustering (OpenRouter) | on demand |
| `importer` | `database/` | Loads results into MySQL, backups, QA, publishing | on demand |
| `db` | `database/` | MySQL 8.4 with the project schema and views | always |
| `backend` | `backend/` | Flask API | always |
| `frontend` | `frontend/` | React site on nginx, proxies `/api` to the backend | always (port 8080) |
| `watchtower` | — | Restarts backend/frontend when new images are published | always (optional) |

## How updates from GitHub reach the containers

```
push to main ──► GitHub Actions builds all 5 images ──► ghcr.io (:latest)
                                                            │
     website (backend, frontend): Watchtower pulls within 5 min, restarts
     jobs (collector, classifier, importer): newest image pulled on every run
```

The workflow is `.github/workflows/docker-publish.yml`. Each image also gets a
`sha-<commit>` tag so you can roll back.

## One-time setup

**GitHub (repo owner):**
1. Merge these files into `main`.
2. Settings → Actions → General → Workflow permissions → *Read and write permissions*.
3. After the first workflow run, make each of the 5 packages public
   (owner's profile → Packages → package → Package settings → Change visibility).

**Your machine / server:**
```bash
git clone https://github.com/Lawlee-L/26S2_5206-Group1-AV-Job-Profiles.git
cd 26S2_5206-Group1-AV-Job-Profiles
cp .env.docker.example .env        # set passwords and API keys
docker compose pull
docker compose --profile autoupdate up -d
```
Site: http://localhost:8080 · API check: http://localhost:8080/api/health

## Weekly pipeline

Run each step from the repo folder. Results are written into the normal repo
folders on your machine, so you can review and commit them as before.
Use the same date everywhere below (`2026-10-17` is an example).

### How the steps connect

Every stage works from the **same weekly file**,
`data-collection/deliverables/<date>/jobs_history_translated.json`,
produced by `weekly-update`:

```
weekly-update ──► deliverables/<date>/jobs_history_translated.json
                         │                         │
                         ▼                         ▼
              import-collection           classifier (--input this file)
              (jobs go into MySQL)                 │
                         │                         ▼
                         │            output/<date>/postings_all.json, ...
                         ▼                         │
              import-analysis ◄────────────────────┘
              (--source-input = the same weekly file)
                         │
                         ▼
              qa-release ──► publish-release ──► API / website
```

- `import-analysis` attaches the classification to jobs already in MySQL, so
  `import-collection` must run first for that week.
- `import-analysis` checks that the classifier ran on exactly the weekly file
  given as `--source-input`, and that `--week-date` matches the collection.
- Each week can be imported once. To replace a published week, use the
  revision steps in `database/RELEASE_REVISIONS.md` (`--candidate` and
  `activate-release`).

### One-time reuse of the tracked 25 September classification

Before classifying a new cumulative file on a fresh database, load the old
collection and its matching classification. These commands make no AI calls.
The importer mounts both `output/` and `output_full/` read-only.

```bash
li="data-collection/deliverables/2026-09-25/jobs_history_translated.json"
out="classification pipeline/output_full"
files=(--source-input "$li" --postings "$out/postings_all.json"
  --metadata "$out/run_metadata.json"
  --av-summary "$out/av_relevant/cluster_summary.csv"
  --other-summary "$out/not_av_relevant/cluster_summary.csv"
  --duplicates "$out/duplicates_removed.csv" --failures "$out/llm_failures.csv")
docker compose run --rm importer plan-collection --input "$li"
docker compose run --rm importer plan-analysis "${files[@]}"
docker compose run --rm importer import-collection --input "$li" --week-date 2026-09-25
docker compose run --rm importer import-analysis "${files[@]}" \
  --week-date 2026-09-25 --git-commit e4f1b77cc56f048c06196e7a27865d98084c2e2a
# No publication is needed for classification reuse.
docker compose run --rm classifier \
  --input input/2026-10-13/jobs_history_translated.json --db --dry-run
```

The array example uses bash/zsh; PowerShell equivalents are in
`database/TEAM_GUIDE.md`. Import the 25 September pair only if it is not already
selected in this database. For an existing newer collection, use the guide's
historical backfill route. Keep `output_full/` paired with 25 September, never
with the new week's input. A draft analysis is sufficient for reuse.

Local verification on 13 October 2026 (`avjobs-live` Compose project):
6,044 inputs → 849 duplicates removed → 5,195 postings; 4,517 MySQL answers
reused and 678 remaining, estimated US$0.4242 with `openai/gpt-6-luna`.
The estimate excludes hidden reasoning tokens and actual output can vary.
Use `docker compose -p avjobs-live ...` to access this local database/cache;
a different project name selects different volumes. No paid run was started.

### 1. Collect and translate

Writes `data-collection/deliverables/<date>/jobs_history_translated.json`.
```bash
docker compose run --rm collector check-config
docker compose run --rm collector weekly-update --run-date 2026-10-17 --region australiaeast
```
If `AZURE_TRANSLATOR_KEY` is empty in `.env`, you are asked for the key.

> **`collect` is for checking a source only.**
> `docker compose run --rm collector collect --source-id SOURCE_ID --run-date 2026-10-17`
> writes `data-collection/data/standardized/<date>/<source>.json`. That file has
> no job history (active / first seen / last seen), so the importer rejects it
> and its classification cannot be imported either. Use `weekly-update` (or the
> one-company test below) for anything that should reach the database.

### 2. Classify and cluster

Writes `classification pipeline/output/<date>/`.
```bash
# Cost estimate first, no paid calls
docker compose run --rm classifier --input input/2026-10-17/jobs_history_translated.json --db --dry-run
# Full run
docker compose run --rm classifier \
  --input input/2026-10-17/jobs_history_translated.json \
  --output-dir output/2026-10-17 --db
```
Inside the classifier, `input/` is `data-collection/deliverables/` and
`output/` is `classification pipeline/output/`. Model replies are cached in a
Docker volume. `--db` also reuses successful imported answers whose source key,
content, model and exact prompt match. An empty cache/database cannot reuse old
work; always inspect `--db --dry-run` before authorizing a paid run. If MySQL
cannot be reached, `--db` stops rather than silently reclassifying everything.
For a small sample, add `--limit 50`.

### 3. Import the collected jobs

Paths below are normal repo paths.
```bash
# Validate only (no database changes)
docker compose run --rm importer plan-collection \
  --input data-collection/deliverables/2026-10-17/jobs_history_translated.json
# Import (takes a backup first)
docker compose run --rm importer import-collection \
  --input data-collection/deliverables/2026-10-17/jobs_history_translated.json \
  --week-date 2026-10-17
```

### 4. Import the classification

Validate first (no database changes):
```bash
docker compose run --rm importer plan-analysis \
  --source-input "data-collection/deliverables/2026-10-17/jobs_history_translated.json" \
  --postings "classification pipeline/output/2026-10-17/postings_all.json" \
  --metadata "classification pipeline/output/2026-10-17/run_metadata.json" \
  --av-summary "classification pipeline/output/2026-10-17/av_relevant/cluster_summary.csv" \
  --other-summary "classification pipeline/output/2026-10-17/not_av_relevant/cluster_summary.csv" \
  --duplicates "classification pipeline/output/2026-10-17/duplicates_removed.csv" \
  --failures "classification pipeline/output/2026-10-17/llm_failures.csv"
```
Then import (takes a backup first and creates a draft release):
```bash
docker compose run --rm importer import-analysis \
  --source-input "data-collection/deliverables/2026-10-17/jobs_history_translated.json" \
  --postings "classification pipeline/output/2026-10-17/postings_all.json" \
  --metadata "classification pipeline/output/2026-10-17/run_metadata.json" \
  --av-summary "classification pipeline/output/2026-10-17/av_relevant/cluster_summary.csv" \
  --other-summary "classification pipeline/output/2026-10-17/not_av_relevant/cluster_summary.csv" \
  --duplicates "classification pipeline/output/2026-10-17/duplicates_removed.csv" \
  --failures "classification pipeline/output/2026-10-17/llm_failures.csv" \
  --week-date 2026-10-17 \
  --git-commit $(git rev-parse HEAD)
```
It prints a `release_key` starting with `draft-`.

### 5. Check and publish the release

```bash
docker compose run --rm importer qa-release --release-key <release_key>
docker compose run --rm importer publish-release --release-key <release_key>
```
The published AV jobs and clusters are then served at
http://localhost:8080/api/jobs and http://localhost:8080/api/clusters.
Backups go to `database/backups/`, logs to `database/operation_logs/`.

Notes:
- Paths containing `classification pipeline` must be quoted.
- On Windows PowerShell, end continued lines with `` ` `` instead of `\`.

### Testing end-to-end with one company

`weekly-update` has no company option. This runs it for one source only
(no code changes) and produces a normal weekly file, so steps 2–5 work
unchanged with the same date:
```bash
docker compose run --rm --entrypoint python collector -c 'import sys, av_jobs.pipeline as p; o = p.load_sources; p.load_sources = lambda *a, **k: [s for s in o(*a, **k) if s.source_id == "vay_germany_greenhouse"]; sys.argv = ["av-jobs", "weekly-update", "--run-date", "2026-10-17", "--region", "australiaeast"]; exec(open("/app/docker-entry.py").read())'
```
Replace `vay_germany_greenhouse` with any `source_id` from the **In Scope**
sheet of `data-collection/config/AV_company_sources_cleaned.xlsx`. With
`--min-cluster-size 2 --min-samples 1` the classifier can cluster such a small
sample. In a fresh clone the weekly file then holds only that company; where
earlier collections exist, it also contains their history. Do not commit test
deliverables. Use a separate Compose project and output date for testing;
`docker compose down -v` deletes that project’s database and classifier cache.
Never run it on a project containing data you need to keep.

## Verify a data update and hand over

Run imports against the MySQL database used by this website. Files pushed to
GitHub are not automatically imported. Use the same Compose project name for
startup, pipeline jobs and maintenance; if started with `-p avjobs-live`, add
`-p avjobs-live` to subsequent Compose commands too.

Before `publish-release`, confirm `qa-release` reports `passed`, inspect warnings,
and obtain the release decision from the responsible operator/team. Keep the
printed release key and matching week in the handover record.

After publication, check these URLs (replace the host/port for your deployment):

- `http://localhost:8080/api/health`: the API is running.
- `http://localhost:8080/api/health/db`: the API can reach MySQL.
- `http://localhost:8080/api/jobs`: returns jobs from the published release.
- `http://localhost:8080/jobs`: jobs load, filters and job details work.
- `http://localhost:8080/clusters` and `/trends`: charts load and the expected
  classified week appears in the historical coverage table.

A successful health check alone does not prove a dataset was published. Confirm
the selected week/release in `v_weekly_versions` using the database guide, and
check a known active AV job from the new release in the API and website. Counts
can differ from the collection total because the website shows active AV jobs.

If something fails, inspect `docker compose ps`, backend logs and importer
reports under `database/operation_logs/`. Keep input files, outputs and backups;
do not reset a populated database to troubleshoot. Use
[the database guide](database/TEAM_GUIDE.md) for backup/restore and
[release revisions](database/RELEASE_REVISIONS.md) to switch back to a previous
published release. `docker compose down` retains volumes; `down -v` deletes
the project's database and classifier cache.

The separate Tableau workbook is a saved snapshot. Updating MySQL does not
refresh that packaged file; follow [the Dashboard guide](dashboard/README.md)
to reconnect/refresh, validate and save a new workbook.

At handover, record the website URL, host, Compose project name, published
week/release key, backup location and maintenance contact. Transfer credentials
securely, and assign responsibility for running updates and approving API costs
and publication. Watchtower updates application images only; it does not run
collection, classification, import or publication, or apply schema migrations.

## Everyday commands

| Task | Command |
| --- | --- |
| Status | `docker compose ps` |
| Logs | `docker compose logs -f backend` |
| Watch auto-updates | `docker compose logs -f watchtower` |
| Stop (keep data) | `docker compose down` |
| Wipe DB and reload schema | `docker compose down -v` |
| Use local code for jobs | set `JOB_PULL_POLICY=build` in `.env`, add `--build` to `run` |
| Roll back | set `IMAGE_TAG=sha-<shortsha>` in `.env` |

## Notes

- The schema is loaded only when the MySQL volume is empty. Later changes need
  the importer/migrations, or `docker compose down -v` (deletes data).
- The website uses a read-only DB user; the importer uses root for writes and
  `mysqldump` backups.
- The classifier runs on CPU. A full run mostly waits on the OpenRouter API.
- The frontend reads published MySQL data through the backend API. nginx
  proxies relative `/api/...` requests to the backend container.
- Watchtower is the maintained fork `nickfedor/watchtower`; the original
  project was archived in December 2025.
