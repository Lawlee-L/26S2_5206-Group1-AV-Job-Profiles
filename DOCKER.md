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
docker compose run --rm classifier --input input/2026-10-17/jobs_history_translated.json --dry-run
# Full run
docker compose run --rm classifier \
  --input input/2026-10-17/jobs_history_translated.json \
  --output-dir output/2026-10-17
```
Inside the classifier, `input/` is `data-collection/deliverables/` and
`output/` is `classification pipeline/output/`. Model replies are cached in a
Docker volume, so re-running the same postings costs nothing. For a cheap test
on a large file, add `--limit 50`.

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
deliverables, and run `docker compose down -v` before importing the real week
(each week can be imported once).

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
- The frontend still reads static data from `src/data/jobs.js`; once it calls
  the API, use relative URLs like `/api/jobs`.
- Watchtower is the maintained fork `nickfedor/watchtower`; the original
  project was archived in December 2025.
