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

**1. Collect and translate** (writes `data-collection/deliverables/<date>/`)
```bash
docker compose run --rm collector check-config
docker compose run --rm collector weekly-update --run-date 2026-10-17 --region australiaeast
```
If `AZURE_TRANSLATOR_KEY` is empty in `.env`, you are asked for the key.
Retry one source: `docker compose run --rm collector collect --source-id SOURCE_ID --run-date 2026-10-17`.

**2. Classify and cluster** (writes `classification pipeline/output/<date>/`)
```bash
# Cost estimate first, no paid calls
docker compose run --rm classifier --input input/2026-10-17/jobs_history_translated.json --dry-run
# Full run
docker compose run --rm classifier \
  --input input/2026-10-17/jobs_history_translated.json \
  --output-dir output/2026-10-17
```
Inside the container, `input/` is `data-collection/deliverables/` and
`output/` is `classification pipeline/output/`. Model replies are cached in a
Docker volume, so re-running the same postings costs nothing.

**3. Import into MySQL** (paths are the normal repo paths)
```bash
docker compose run --rm importer plan-collection \
  --input data-collection/deliverables/2026-10-17/jobs_history_translated.json
docker compose run --rm importer import-collection \
  --input data-collection/deliverables/2026-10-17/jobs_history_translated.json
```
Then `plan-analysis`, `import-analysis`, `qa-release` and `publish-release` as
described in `database/TEAM_GUIDE.md`, pointing at
`classification pipeline/output/2026-10-17/...`. For `--git-commit`, use
`--git-commit $(git rev-parse HEAD)` (your shell fills it in).
Backups go to `database/backups/`, logs to `database/operation_logs/`.

**4. Website** shows the new release automatically once it is published.

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
