# AV job profiles: job-posting analysis pipeline (v2)

Turns raw job postings from autonomous-vehicle (AV) companies into structured
records (role summary, skills with evidence, seniority, experience, AV relevance),
then groups similar roles into clusters for people to label. Built for a
labour-market study of the AV industry.

One LLM call per posting does the reading, in any language. Everything after that
(embeddings, clustering, summaries, storage) runs locally.

```
postings JSON
  → [1] load + deduplicate           exact copies and ≥95%-similar reposts within a company
  → [2] one LLM call per posting     strict JSON record, validated; 10 calls in flight
  → [3] embed the record             MiniLM on role summary + responsibilities + skills
  → [4] cluster each group apart     AV-relevant and other postings: UMAP → HDBSCAN
  → [5] write outputs                CSV / JSON / Markdown, optionally a SQLite database
```

## Design choices

- **The model never sees the employer.** It gets the job title and description only,
  and relevance is judged from the posting text alone.
- **No posting is dropped.** Each lands in the AV-relevant group or the other group.
  When the model is unsure (confidence `Low`) a posting counts as AV-relevant; the
  model's own verdict is kept alongside (`av_relevant_model`).
- **Every skill carries evidence**: the shortest verbatim quote from the posting.
  Skills are open-ended; nothing restricts them to a fixed list.
- **Clusters are named by people, not by the code.** The pipeline writes a
  labelling worksheet with top terms and example titles for each cluster.
- **Nothing is paid for twice.** Answers are cached per posting, and with `--db`
  they are reused from the database when the model, the exact prompt and the
  posting text are unchanged.

## Setup

Python 3.12 (tested on macOS, Apple Silicon).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then paste your OpenRouter key into .env
```

Model calls go through [OpenRouter](https://openrouter.ai); the key is read from
`.env` and never printed. The embedding model (`all-MiniLM-L6-v2`) downloads once on
first use.

## Input data

The dataset is **not** in this repository. The pipeline reads a JSON list of
postings, each shaped like:

```json
{
  "metadata": {"source_key": "hotjob|horizon|id:6aaa…", "source_id": "horizon_china_hotjob",
               "source_job_id": "6aaa…", "company": "Horizon", "platform": "hotjob",
               "region": "China", "collected_at": "…", "first_seen_date": "…",
               "last_seen_date": "…", "is_active": true, "is_new_in_latest_run": false},
  "data":     {"advertised_job_title": "…", "job_description": "…", "job_url": "…",
               "location": "…", "salary": null, "date_posted": "…"}
}
```

`metadata.source_key` is the join key everywhere: outputs and database rows carry
it unchanged.

## Usage

Always pass `--input` (the default in `avjobs/config.py` points at an older export).

```bash
# Cost estimate only: counts tokens, no model calls
python run_pipeline_v2.py --input postings.json --dry-run

# Small paid sample (random, after dedupe)
python run_pipeline_v2.py --input postings.json --limit 50 --output-dir output_sample --db

# Full run, written to files and to SQLite
python run_pipeline_v2.py --input postings.json --db

# Try cluster settings on cached records (free), then re-run with the chosen size
python run_pipeline_v2.py --input postings.json --sweep
python run_pipeline_v2.py --input postings.json --min-cluster-size 12 --db
```

| Option | What it does |
|---|---|
| `--input` | postings JSON |
| `--output-dir` | where results go (default `output_v3/`) |
| `--model` | any OpenRouter model id (default `openai/gpt-6-luna`) |
| `--limit N` | random sample of N postings |
| `--min-cluster-size`, `--min-samples` | HDBSCAN settings |
| `--sweep` | print a grid of cluster settings per group, then stop |
| `--db` | also write `<output-dir>/av_job_profiles.sqlite`, reusing stored answers |
| `--no-cache` | ignore cached answers and call the model again (paid) |
| `--dry-run` | print the cost estimate and stop |
| `--reference-only` | score the model on 14 hand-checked reference postings (needs `test_set_postings.json` and `sonnet5_reference_answers.json`, not included) |

A run that stops part-way (Ctrl-C, no credit, rate limit) can be restarted with the
same command: finished postings are skipped.

## Outputs

```
<output-dir>/
  postings_all.json          every analysed posting with its full record (import this)
  duplicates_removed.csv     each duplicate and the source_key it copies
  relevance_review.csv       postings with Low relevance confidence, to check by hand
  llm_failures.csv           postings the model could not answer (retried on re-run)
  validation_report.md       spot-check against the reference postings, if available
  run_metadata.json          model, prompt version, tokens, cost, per-group counts
  av_relevant/  and  not_av_relevant/
    postings_enriched.csv/.json    postings that joined a cluster
    needs_review.csv               postings that fit no cluster (noise)
    cluster_summary.csv            size, top terms, example titles, companies
    cluster_labelling_worksheet.md for naming clusters
  av_job_profiles.sqlite     with --db
```

## Database

`schema.mysql.sql` is the project's database design (MySQL 8). While the layout is
being checked, `--db` writes the same tables and columns to SQLite
(`avjobs/schema.sql`), so the file opens in any SQLite viewer:

| Table | Holds |
|---|---|
| `companies`, `job_sources`, `jobs` | the postings (temporary loader: the team's job import will replace it); duplicates link to the kept copy |
| `analysis_runs` | one row per run: model, prompt version, tokens, cost |
| `job_analyses` | one row per posting per run: relevance, confidence, reason, summary, seniority, experience, the full record |
| `skills`, `job_skills` | each skill once (by name ignoring case, and type) and every mention with its evidence |
| `cluster_runs`, `clusters`, `job_cluster_assignments` | clusters per group and each posting's cluster |

Each run adds a new `analysis_runs` row, so queries should filter to one run
(usually the latest). A stored answer is reused as `result_origin = 'reused'`,
pointing at the original, only when the model, the exact prompt
(`analysis_runs.prompt_version`, e.g. `p5-72e4e4cb`) and the posting text
(`job_analyses.input_content_hash`) all match.

An optional MySQL container is included: `docker compose up -d` loads
`schema.mysql.sql` (needs `MYSQL_ROOT_PASSWORD` and `MYSQL_PASSWORD` in `.env`).

## Configuration

Settings live in `avjobs/config.py`; the ones most likely to change:

| Setting | Default | Meaning |
|---|---|---|
| `LLM_MODEL` | `openai/gpt-6-luna` | chosen over gpt-4o-mini on the reference postings |
| `LLM_WORKERS` | `10` | model calls in flight at once |
| `MIN_CLUSTER_SIZE`, `MIN_SAMPLES` | `8`, `2` | HDBSCAN |
| `NEAR_DUP_THRESHOLD` | `0.95` | similarity at which two postings of one company are duplicates |
| `SENIORITY_LABELS` | Intern … Executive, Other | the seniority scale |

The prompt and output schema are in `avjobs/llm.py` (`PROMPT`, `SCHEMA`,
`PROMPT_VERSION`). Changing either invalidates cached answers, so the next run
pays again.

## Cost and time

Measured on a 50-posting sample with `openai/gpt-6-luna`: about $0.0005 per posting.
Roughly **$2 and 40 minutes for 4,500 postings** with 10 calls in flight. Run
`--dry-run` for an estimate on your data.

## Tests

Offline: the model is replaced by a fake, so no API calls are made.

```bash
python -m unittest discover -s tests -t . -v
```

- `tests/test_llm_parallel.py`: ordering, 10 calls at once, one failure does not stop
  the run, a fatal error cancels the queue, re-runs use the cache.
- `tests/test_store.py`: the database end to end, including reuse and roll-back
  (skipped unless the dataset file `jobs_history_translated.json` is present).

## Layout

```
run_pipeline_v2.py     entry point
avjobs/
  config.py            settings
  clean.py             loading and deduplication
  llm.py               prompt, schema, model calls, cache, cost estimate
  embed.py             MiniLM embeddings
  cluster.py           UMAP, HDBSCAN, cluster summaries, labelling worksheet
  validate.py          reference-posting checks
  store.py, schema.sql SQLite storage in the tables of schema.mysql.sql
schema.mysql.sql       full database design (MySQL 8)
docker-compose.yml     optional local MySQL
tests/                 offline tests
```
