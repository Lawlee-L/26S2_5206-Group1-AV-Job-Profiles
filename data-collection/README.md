# AV Job Data Collection

This project collects job advertisements from autonomous vehicle (AV)
companies. It reads a list of company career sources, collects jobs from
different recruitment platforms, and converts the results into one standard
JSON format.

The standardized data will later be cleaned and stored in a MySQL database.

## Project structure

```text
AV Job Data Collection/
├── config/                 Company source list
├── data/
│   ├── raw/                Original responses from each source
│   ├── standardized/       Jobs converted to the standard format
│   ├── history/            Jobs kept across all weekly collections
│   └── run_reports/        Results of each collection run
├── deliverables/           Dated English datasets selected for GitHub
├── src/av_jobs/
│   ├── collectors/         One collector for each platform
│   ├── cli.py              Commands used to run the project
│   ├── config.py           Reads and checks the Excel source list
│   ├── models.py           Standard job data structure
│   ├── pipeline.py         Runs collectors and combines results
│   └── storage.py          Saves snapshots and maintains job history
├── tests/                  Tests for the collectors and data model
└── pyproject.toml          Python project settings
```

## Company source list

The source list is stored in:

```text
config/AV_company_sources_cleaned.xlsx
```

The workbook contains three sheets:

- `In Scope`: sources that are ready for collection.
- `TBD`: sources that still need more research or a working collector.
- `Out of Scope`: sources that are not included in the current project.

The program only reads the `In Scope` sheet. A source can be moved from `TBD`
to `In Scope` after its endpoint has been checked and its collector passes a
test.

## Collection scope and data cleaning

This pipeline is responsible for collecting and standardizing job data. Each
collector reads public jobs from its configured source and maps the platform's
field names to the standard format used by this project.

The collectors do not decide whether each job is related to autonomous
vehicles. They also do not delete, correct, or classify jobs. These tasks are
part of the later data-cleaning stage.

This is important for large companies such as Bosch. The SmartRecruiters
collector collects all configured jobs from Germany and the US, including all
pages and full descriptions. AV-related filtering is completed later. Raw
responses are kept so that the cleaned results can be checked against the
original source data.

## Setup

Python 3.11 or a newer version is required.

Open a terminal in the `data-collection` folder and create a local Python
environment:

```bash
python3 -m venv .venv
```

Activate the environment on macOS:

```bash
source .venv/bin/activate
```

Install the project and its packages:

```bash
python -m pip install -e .
```

These setup commands are only needed for the first run. After that, open a
terminal in the project folder and activate the environment again.

## Check the source list

Run this command before collecting jobs:

```bash
av-jobs check-config
```

This checks the required columns, source IDs, request methods, and endpoints in
the `In Scope` sheet.

## Collect jobs

Collect one source:

```bash
av-jobs collect --source-id avride_russia_greenhouse
```

Collect all sources from one platform:

```bash
av-jobs collect --platform greenhouse
```

The platform can currently be `greenhouse`, `lever`, `ashby`, `workable`,
`comeet`, `moka`, `smartrecruiters`, `jobylon`, `hotjob`, `herp`, `aimotive`,
`gm`, or `tensor`.

Run all available collectors:

```bash
av-jobs collect
```

During testing, each platform can produce a separate standardized file, such as
`greenhouse.json`, `lever.json`, or `ashby.json`. A full run automatically
combines all successful results into `jobs.json`, so no manual merge is needed.

A full run also updates `data/history/jobs_history.json`. This is the cumulative
history file. It keeps jobs from earlier weeks, including jobs that are no
longer shown on a company careers page. The stable `source_key` prevents the
same job from being added more than once.

When an earlier dated `jobs_history_translated.json` exists in `deliverables/`,
the weekly full run uses that English file as the starting point for the new
history. Existing jobs keep their translated English title, description, and
location. Their latest metadata, URL, salary, and posting date are still
updated from the current collection. Jobs first found in the new weekly run are
added in their collected language. This means the newly generated
`jobs_history.json` is the previous English history plus the current week's new
jobs, so the next translation step only needs to process content that is not
already English.

## Run a complete In Scope collection

Before a full run, check the Excel source list:

```bash
av-jobs check-config
```

The current configuration should show `Ready sources: 36`. The program only
runs sources from `In Scope`; it does not run sources from `TBD` or
`Out of Scope`.

Run every current `In Scope` source:

```bash
av-jobs collect
```

A full run may take several minutes because some collectors need to open every
job detail page. Keep the terminal open and make sure the internet connection
stays active.

The terminal prints one result for each source. A successful result looks like:

```text
source_id: success, 100 jobs
```

Check that every source reports `success`. If a source reports `failed`, the
error is saved in the run report. The number of jobs may change between runs.

The full run creates three types of local output under the current date:

```text
data/raw/<run-date>/
data/standardized/<run-date>/jobs.json
data/run_reports/<run-date>/jobs_report.json
```

- `raw` contains the original response from each source.
- `jobs.json` is the weekly snapshot. It contains all jobs collected
  successfully in that run, using the standard format.
- `jobs_report.json` shows which sources succeeded or failed.

The cumulative job history is stored separately:

```text
data/history/jobs_history.json
```

Each history record includes four extra metadata fields:

- `first_seen_date`: the date when the job was first collected.
- `last_seen_date`: the most recent date when the job was collected.
- `is_new_in_latest_run`: `true` when the job first appeared in the latest run.
- `is_active`: `true` when the job was still listed during the latest
  successful check of its source.

Use `is_new_in_latest_run` and `is_active` together:

| `is_new_in_latest_run` | `is_active` | Meaning |
| --- | --- | --- |
| `true` | `true` | A new job first found in the latest run |
| `false` | `true` | An older job that is still online |
| `false` | `false` | An older job that is no longer listed |

These four fields are only added to `metadata` in `jobs_history.json`. They do
not change the agreed job fields in each weekly `jobs.json` snapshot.

If a source is retried or the history is merged again on the same date, a job
is still marked as new when its `first_seen_date` matches that run date. This
keeps `is_new_in_latest_run` correct during same-day retries.

If a source fails during a run, its older jobs are not marked as inactive. This
prevents a temporary source error from being treated as a job removal. In
summary, `jobs.json` shows one weekly snapshot, while `jobs_history.json` keeps
both current and older job opportunities for later analysis.

To build the history file from all weekly snapshots already saved locally, run:

```bash
av-jobs build-history
```

If one source fails, it can be tested separately:

```bash
av-jobs collect --source-id SOURCE_ID
```

This command creates a file for that source only. It does not add the result to
an older `jobs.json`. After fixing or retrying a failed source, run
`av-jobs collect` again to create a new complete snapshot.

The folders under `data/` are excluded from GitHub by `.gitignore`. The required
final dataset can instead be placed in `deliverables/`, as explained below.

## English history deliverables

English history datasets are stored in dated folders under `deliverables/`.
After a translated history is reviewed, save it as:

```text
deliverables/<run-date>/jobs_history_translated.json
```

The next complete weekly collection automatically finds the latest translated
history from an earlier date and uses it as the base for
`data/history/jobs_history.json`. The translation itself is not performed by
the collection command. Earlier dated deliverables remain unchanged and can be
used again during the next weekly update.

The translation helpers under `src/av_jobs/translation/` find content that
appears non-English, call Azure Translator, verify the returned batch, and
merge it back without changing other job fields.

Check a complete history file:

```bash
python -m av_jobs.translation.language_check \
  data/history/jobs_history.json \
  --output /tmp/non_english_jobs.json
```

To prepare only jobs first found in one weekly collection:

```bash
python -m av_jobs.translation.workflow prepare \
  data/history/jobs_history.json \
  /tmp/translation_source.json \
  --first-seen-date 2026-09-19
```

After Azure returns the same JSON structure with English values, validate it
before merging:

```bash
python -m av_jobs.translation.workflow validate \
  /tmp/translation_source.json \
  /tmp/translation_result.json
```

Azure Translator can produce the result file directly. The key is requested
through a hidden terminal prompt and is never written to the repository:

```bash
python -m av_jobs.translation.azure \
  /tmp/translation_source.json \
  /tmp/translation_result.json \
  --region australiaeast
```

The Azure helper deduplicates repeated text, splits long descriptions into
safe request sizes, retries temporary errors, and saves a `.partial.json`
checkpoint after each completed group. Running the same command again resumes
from that checkpoint.

If a record still contains non-English text after three focused repair passes,
the command prints a warning with its `source_key` and affected fields, saves
the completed output, and continues without stopping the other records. Input
errors, invalid API credentials, and missing records remain fatal errors.

Only after validation succeeds, merge it into a new output file:

```bash
python -m av_jobs.translation.workflow merge \
  data/history/jobs_history.json \
  /tmp/translation_source.json \
  /tmp/translation_result.json \
  deliverables/2026-09-19/jobs_history_translated.json
```

Validation checks that every `source_key` and requested field is returned,
that translated values are not empty, and that no non-English text is still
detected. It cannot judge whether a translation is semantically perfect, so a
small human review is still recommended.

The original `data/history/jobs_history.json` remains local and is not included
in GitHub. Personal translation API keys are also not stored in this
repository.

The translated dataset may still include jobs that are not related to
autonomous vehicles. Translation is separate from the later filtering,
cleaning, information extraction, deduplication, quality checking, and database
export tasks.

## Standard job format

Each job record has two parts:

- `metadata`: tracking information about the source. It includes the company,
  region, platform, source ID, original job ID, `source_key`, and collection
  time. It helps the team trace each record, recognise the same job in later
  runs, check data quality, and prepare the data for deduplication or database
  storage.
- `data`: the job advertisement fields required by the current task. It
  contains `advertised_job_title`, `job_description`, `job_url`, `location`,
  `salary`, and `date_posted`. Later workstreams can clean, filter, translate,
  analyse, or extend these fields.

Keeping these parts separate prevents source-tracking information from being
mixed with the job advertisement. The structure can be flattened or changed
later when the cleaned data is prepared for the final database.

Raw source responses are saved under `data/raw/<run-date>/`. Standardized jobs
are saved under `data/standardized/<run-date>/`. Run reports are saved under
`data/run_reports/<run-date>/`.

## Important notes

- The collected dataset is an input for later work, not the final analysis
  dataset. It may include jobs that are not related to autonomous vehicles, so
  the data must be cleaned and filtered before analysis.
- A missing source field is saved as `null`. The collector does not invent or
  guess a value.
- Salary is saved only when the public source gives a clear amount and unit.
- Jobylon first reads the job links from the company widget. It then reads the
  `JobPosting` JSON-LD from every detail page to get the full job information.
- HERP first reads the job links from the public company page. It then reads the
  `JobPosting` JSON-LD and public HERP page data from every detail page.
- AImotive uses server-rendered HTML. Its collector reads job links from the
  careers page and the title, description, and location from each detail page.
- Inceptio uses the current public Moka job API. The standard Moka collector
  reads all results from the configured site and removes repeated job IDs.
- GM uses its public XML job feed. The collector selects jobs containing GM's
  official `#GM-AV-1` marker. This marker is used to define the configured GM
  source; the collector does not make its own AV relevance decision.
- Tensor uses its public static careers page and individual job pages. The
  collector keeps all public roles from every listed country. It saves the
  location-specific salary ranges when available. The pages do not provide a
  reliable posting date, so `date_posted` is saved as `null`.
- Some platforms require one detail request for every job. A complete run can
  therefore take several minutes, especially for the large Bosch sources.
- Job numbers can change between runs because companies add or remove jobs.
- Generated raw data, standardized data, job history, and run reports are local
  outputs. They are excluded from GitHub by `.gitignore`.

## Project status

The collectors for the original 27 `In Scope` sources are complete. Nine more
sources have been checked and moved from `TBD` to `In Scope`: Pony.AI US,
Horizon China, WeRide China, Stack AV USA, Tier IV Japan, AImotive Hungary, GM
USA, Inceptio China, and Tensor Global.

- Pony.AI uses the existing Workable collector.
- Horizon uses the HotJob collector.
- WeRide and Inceptio use the Moka collector.
- Stack AV uses the Greenhouse collector.
- Tier IV uses the HERP collector and reads all job groups from its public page.
- AImotive uses its server-rendered HTML collector.
- GM uses its public XML feed and the official `#GM-AV-1` source marker.
- Tensor uses an HTML collector. Its region is `Global` because its public
  careers page contains jobs in the US, Singapore, Spain, and the UAE.

Other AV relevance filtering will be completed during the later data-cleaning
stage.

The complete run on 13 September 2026 collected and combined 3,986 active jobs
from all 36 configured sources. The cumulative history contains 4,475 records.
Job numbers change over time as companies add and remove advertisements. A full
run automatically combines the results, so no manual file merge is normally
required.

## Current progress

Completed:

- Excel configuration reader and validation
- Standard job data model
- Raw and standardized JSON storage
- Greenhouse collector: 13 sources tested
- Lever collector: 6 sources tested
- Ashby collector: 3 sources tested
- Workable collector: 2 sources tested
- Comeet collector: 1 source tested
- Moka collector: 3 sources tested
- SmartRecruiters collector: 2 sources tested
- Jobylon collector: 1 source tested
- HotJob collector: 1 source tested
- HERP collector: 1 source tested
- AImotive collector: 1 source tested
- GM collector: 1 source tested
- Tensor collector: 1 source tested
- 36 sources tested successfully
- Pony.AI US source test: 11 jobs collected
- Horizon China source test: 229 jobs collected
- WeRide China source test: 236 jobs collected
- Stack AV USA source test: 9 jobs collected
- Tier IV Japan source test: 60 jobs collected
- AImotive Hungary source test: 5 jobs collected
- GM USA source test: 49 jobs collected
- Inceptio China source test: 100 jobs collected
- Tensor Global source test: 99 jobs collected
- 49 automated tests passed
- Latest complete run: 3,986 active jobs from 36 sources
- Latest cumulative history: 4,475 jobs, including 312 newly found jobs

The collection and standardization work for the current `In Scope` sources is
complete. MySQL database loading belongs to the later backend export workstream.

## Next steps

The remaining seven sources in the `TBD` sheet can be investigated one at a
time. A source should stay in `TBD` until its endpoint or collection method is
confirmed and it passes a live test. This work is tracked in GitHub Issue #24.

## GitHub note

Do not upload the generated files inside `data/raw`, `data/standardized`,
`data/history`, or `data/run_reports`. These files can be large and can be
created again by running the pipeline. They are already excluded by
`.gitignore`.

The dated files under `deliverables/` are different: they are selected English
datasets for the project, so they are intended to be included in GitHub. The
latest file is `deliverables/2026-09-13/jobs_history_translated.json`.
