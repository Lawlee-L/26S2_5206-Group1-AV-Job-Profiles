# AV Job Data Collection

This project collects public job advertisements from autonomous vehicle (AV)
companies, converts them to one JSON structure, maintains a cumulative weekly
history, and translates non-English job content into English with Azure
Translator.

The output is prepared for later cleaning, AV relevance classification, skill
extraction, and MySQL database loading. Collection and translation do not
remove jobs that appear unrelated to AV; that decision belongs to the later
analysis workflow.

## Project structure

```text
data-collection/
├── config/                       Company source list
├── data/
│   ├── raw/                      Original source responses
│   ├── standardized/             Dated standard job snapshots
│   ├── history/                  Local cumulative job history
│   ├── run_reports/              Source success and failure reports
│   └── translation/              Local translation work and checkpoints
├── deliverables/                 Reviewed dated English datasets for GitHub
├── src/av_jobs/
│   ├── collectors/               Platform-specific collectors
│   ├── translation/              Language checking and Azure translation
│   ├── cli.py                    Command-line interface
│   ├── config.py                 Source configuration reader
│   ├── models.py                 Standard job structure
│   ├── pipeline.py               Collection pipeline
│   ├── storage.py                Snapshot and history storage
│   └── weekly.py                 Complete weekly workflow
├── tests/                        Automated tests
└── pyproject.toml                Python project settings
```

## Setup

Python 3.11 or newer is required. Open a terminal in `data-collection` and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The environment only needs to be created once. For later runs, return to the
same folder and activate it again:

```bash
source .venv/bin/activate
```

## Source configuration

Company sources are stored in:

```text
config/AV_company_sources_cleaned.xlsx
```

The workbook has three sheets:

- `In Scope`: sources that are ready to run.
- `TBD`: sources that still need research or a working collector.
- `Out of Scope`: sources excluded from the current project.

Only `In Scope` sources are collected. Check the configuration before a weekly
run:

```bash
av-jobs check-config
```

The current configuration should report `Ready sources: 36`.

## Complete weekly workflow

The recommended weekly command is:

```bash
av-jobs weekly-update --run-date 2026-09-26 --region australiaeast
```

Replace the example date with the collection date and use the region shown on
the Azure Translator resource. The command:

1. collects and standardizes all current `In Scope` sources;
2. updates the cumulative job history;
3. finds non-English titles, descriptions, and locations;
4. requests an Azure key through a hidden prompt when translation is needed;
5. translates and validates the detected content; and
6. writes the final English history to:

```text
deliverables/<run-date>/jobs_history_translated.json
```

Collection and translation can take several minutes. Keep the terminal open.
Progress messages show the current stage and completed translation groups.

### Azure Translator setup

Each person or organisation running the translation must provide a key for an
Azure resource they are authorised to use. The repository does not contain a
shared key.

Before the first translation run:

1. Sign in to the Azure portal and create a Translator resource under the
   Azure subscription that will pay for the requests. Use the free `F0` tier
   when it is available and suitable for testing, or another approved tier.
2. After deployment, open the resource and select `Keys and Endpoint` under
   `Resource Management`.
3. Copy `KEY 1` or `KEY 2` and note the resource `Location/Region`.
4. Pass that location to `--region`. For example, use `australiaeast` when
   the resource location is Australia East.
5. Paste the key only when the hidden terminal prompt appears.

Never add an Azure key to the code, README, command history, or GitHub.

The default Text Translation endpoint is:

```text
https://api.cognitive.microsofttranslator.com
```

Most users do not need to specify it. Use `--endpoint` only when the Azure
resource requires a different custom endpoint.

### Failure handling

A failed source does not normally stop the weekly workflow. The program shows
a warning, continues with the other sources, and keeps that source's previous
history records unchanged. This prevents a temporary website problem from
being treated as a job removal.

Connection, TLS handshake, timeout, or server errors may be temporary. Retry a
failed source later:

```bash
av-jobs collect --source-id SOURCE_ID --run-date YYYY-MM-DD
```

If it fails repeatedly, the external careers website may be unavailable,
responding slowly, blocking automated requests, or may have changed its
endpoint. A single-source command is only a diagnostic check; it does not add
the result to the combined snapshot. After the source succeeds, rerun the full
`weekly-update` command to regenerate the official weekly deliverable.

If collection already finished but translation still has review records, repair
only the saved translation and update the same deliverable without collecting
the websites again:

```bash
av-jobs repair-translation --run-date 2026-09-25 --region australiaeast
```

This command reuses the saved source batch and checkpoint, retranslates only
the remaining non-English content, validates it, and merges successful repairs
into the dated deliverable by `source_key`.

The complete workflow stops when no source succeeds, the input history is
invalid, the Azure key is missing or rejected, or Azure cannot be reached after
its request retries.

### Translation validation and review

Azure translation uses the stable `source_key` to return translated fields to
the correct job. It deduplicates repeated text, splits long descriptions into
safe request sizes, retries temporary API errors, and saves a checkpoint after
each completed group.

If translated text still appears non-English, the program retries only the
affected fields up to three times. For long mixed-language fields, only the
lines that still appear non-English are sent again, then the field is rebuilt
and validated before it can be merged. Repair requests also provide Azure with
the detected source language so bilingual lines are not mistaken for English.
After those attempts:

- valid translations are merged into the history;
- the original value is retained for any field that still needs review;
- the affected `source_key` and field names are printed as warnings; and
- successful work is not discarded.

Translation working files are stored locally in:

```text
data/translation/<run-date>/
```

Possible files include:

```text
translation_source.json          Fields selected for translation
translation_result.json          Complete Azure output
translation_result.partial.json  Resumable checkpoint
translation_result.passed.json   Records that passed validation
translation_result.review.json   Records and fields that need review
```

The `.passed.json` and `.review.json` files are created only when content still
needs review. Translation working files must not be uploaded to GitHub.

The validator checks returned `source_key` values, requested fields, empty
values, and remaining non-English content. It cannot judge whether every
translation is semantically perfect, so a small human review is still useful.

Only these fields are translated:

- `advertised_job_title`
- `job_description`
- `location`

The workflow does not change `metadata`, `job_url`, `salary`, or `date_posted`.
Missing source values remain `null`.

## Collection outputs and history

A complete collection creates:

```text
data/raw/<run-date>/
data/standardized/<run-date>/jobs.json
data/run_reports/<run-date>/jobs_report.json
data/history/jobs_history.json
```

- `raw` contains original responses from each source.
- `jobs.json` is the current weekly snapshot of successfully collected jobs.
- `jobs_report.json` lists source successes and failures.
- `jobs_history.json` is the cumulative history across weekly runs.

Every history record adds four fields under `metadata`:

| Field | Meaning |
| --- | --- |
| `first_seen_date` | Date when the job was first collected |
| `last_seen_date` | Most recent date when the job was collected |
| `is_new_in_latest_run` | `true` when first seen in the latest run |
| `is_active` | `true` when still listed during the latest successful source check |

Use the two status flags together:

| `is_new_in_latest_run` | `is_active` | Meaning |
| --- | --- | --- |
| `true` | `true` | New job first found in the latest run |
| `false` | `true` | Older job that is still listed |
| `false` | `false` | Older job that is no longer listed |

Same-day reruns keep a job marked as new when its `first_seen_date` matches the
run date. If a source fails, its older records are not marked inactive.

When an earlier translated history exists under `deliverables/`, the next full
run uses the latest earlier English file as its base. Existing jobs retain
their English title, description, and location while current metadata, URL,
salary, and posting date are refreshed. Newly discovered jobs are added in
their collected language and are the main input to the next translation step.

The stable `source_key` prevents the same job from being added twice.

## Individual and diagnostic commands

Collect one source:

```bash
av-jobs collect --source-id SOURCE_ID
```

Collect every source on one platform:

```bash
av-jobs collect --platform greenhouse
```

Collect all `In Scope` sources without running translation:

```bash
av-jobs collect
```

Rebuild local history from saved weekly snapshots:

```bash
av-jobs build-history
```

Check a history file for non-English fields:

```bash
python -m av_jobs.translation.language_check \
  data/history/jobs_history.json \
  --output /tmp/non_english_jobs.json
```

### Manual translation workflow

The one-command workflow is recommended. These commands remain available for
diagnosis or for running translation stages separately.

Prepare a translation batch:

```bash
python -m av_jobs.translation.workflow prepare \
  data/history/jobs_history.json \
  /tmp/translation_source.json \
  --first-seen-date 2026-09-19
```

Translate it with Azure:

```bash
python -m av_jobs.translation.azure \
  /tmp/translation_source.json \
  /tmp/translation_result.json \
  --region australiaeast
```

Validate the result:

```bash
python -m av_jobs.translation.workflow validate \
  /tmp/translation_source.json \
  /tmp/translation_result.json
```

Merge a fully validated result:

```bash
python -m av_jobs.translation.workflow merge \
  data/history/jobs_history.json \
  /tmp/translation_source.json \
  /tmp/translation_result.json \
  deliverables/<run-date>/jobs_history_translated.json
```

## Standard job format

Each job record has two sections:

- `metadata`: source tracking information, including company, region,
  platform, source ID, original job ID, `source_key`, and collection time.
- `data`: `advertised_job_title`, `job_description`, `job_url`, `location`,
  `salary`, and `date_posted`.

Keeping these sections separate prevents source-tracking information from being
mixed with job advertisement content. The structure can be flattened or
extended later for database loading.

A missing source value is stored as `null`; collectors do not invent values.
Salary is stored only when a public source provides a clear amount and unit.

## Supported sources and status

The project currently has 36 `In Scope` sources across Greenhouse, Lever,
Ashby, Workable, Comeet, Moka, SmartRecruiters, Jobylon, HotJob, HERP,
AImotive, GM, and Tensor collectors.

The nine sources added after the original 27 are:

| Source | Collector or source method |
| --- | --- |
| Pony.AI US | Workable |
| Horizon China | HotJob |
| WeRide China | Moka |
| Stack AV USA | Greenhouse |
| Tier IV Japan | HERP public pages and `JobPosting` data |
| AImotive Hungary | Server-rendered HTML |
| GM USA | Public XML feed with the official `#GM-AV-1` marker |
| Inceptio China | Moka |
| Tensor Global | Public careers and job detail pages |

Seven remaining sources stay in `TBD` until their endpoint or collection method
is confirmed and passes a live test. This work is tracked in GitHub Issue #24.

## Automated tests

Run the test suite with:

```bash
pytest
```

The current suite contains 67 passing tests covering:

- source configuration and the standard job structure;
- collector mappings, URLs, descriptions, locations, salaries, and pagination;
- history updates, duplicate prevention, same-day reruns, and English reuse;
- non-English detection and common false-positive cases;
- Azure batching, deduplication, validation, network retries, checkpoints, and
  review outputs; and
- weekly orchestration, including successful merges, retained original values,
  skipped translation, and stale temporary file cleanup.

## GitHub data policy

Generated files under these folders are local working data and must not be
uploaded:

```text
data/raw/
data/standardized/
data/history/
data/run_reports/
data/translation/
```

Reviewed English datasets under dated `deliverables/` folders are intended for
GitHub. The latest official file is:

```text
deliverables/2026-09-19/jobs_history_translated.json
```

The latest official translated history contains 4,842 unique jobs, including
367 jobs first found in the latest official collection.
