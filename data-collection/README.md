# AV Job Data Collection

This project collects job postings from autonomous vehicle companies. It reads
the company source list, collects jobs from different recruitment platforms,
and converts all results into one standard format.

The final goal is to store the standardized job data in one MySQL database.

## Project structure

```text
AV Job Data Collection/
├── config/                 Company source list
├── data/
│   ├── raw/                Original responses from each source
│   ├── standardized/       Jobs converted to the standard format
│   └── run_reports/        Result of each collection run
├── src/av_jobs/
│   ├── collectors/         One collector for each platform
│   ├── cli.py              Commands used to run the project
│   ├── config.py           Reads and checks the Excel source list
│   ├── models.py           Standard job data structure
│   ├── pipeline.py         Runs collectors and combines results
│   └── storage.py          Saves raw and standardized files
├── tests/                  Tests for the collectors and data model
└── pyproject.toml          Python project settings
```

## Source list

The source list is stored in:

```text
config/AV_company_sources_cleaned.xlsx
```

It contains three sheets:

- `In Scope`: sources that are ready to be used by the pipeline.
- `TBD`: sources that still need endpoint or collector research.
- `Out of Scope`: sources that are not included in this project.

The program reads only the `In Scope` sheet. A source can be moved from `TBD`
to `In Scope` after its endpoint is checked and its collector is available.

## Collection scope and data cleaning

This pipeline is responsible for data collection and standardization. Each
collector reads all public jobs from its configured source and maps the source
fields to the standard job format.

The collectors do not decide whether a job is related to autonomous vehicles.
They also do not delete, correct, or classify job records. These tasks belong
to the later data cleaning stage.

This difference is important for broad companies such as Bosch. The
SmartRecruiters collector must collect all configured Germany and US postings
with pagination and full descriptions. AV-related filtering is completed after
collection. Raw responses are kept so the cleaning result can be checked later.

## Setup

Python 3.11 or a newer version is required.

Open a terminal in the `data-collection` folder. Create a local Python
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

These setup commands are only required the first time. For later runs, open a
terminal in the project folder and activate the environment again.

## Check the source list

Run this command before collecting jobs:

```bash
av-jobs check-config
```

It checks required columns, source IDs, request methods, and endpoints in the
`In Scope` sheet.

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

During testing, each platform has a separate standardized file, such as
`greenhouse.json`, `lever.json`, or `ashby.json`. A full run combines all
available results into `jobs.json`. No manual merge is needed.

## Run a complete In Scope collection

Before a full run, check the Excel source list:

```bash
av-jobs check-config
```

The current configuration should show `Ready sources: 36`. The program reads
only the `In Scope` sheet. It does not run sources from `TBD` or `Out of Scope`.

Run every current `In Scope` source:

```bash
av-jobs collect
```

A full run can take several minutes because some collectors must open every job
detail page. Keep the terminal open and keep the internet connection active.

The terminal prints one result for each source. A successful result looks like:

```text
source_id: success, 100 jobs
```

Check that every source reports `success`. If a source reports `failed`, its
error is also saved in the run report. Job numbers may change between runs.

The full run creates three types of local output under the current date:

```text
data/raw/<run-date>/
data/standardized/<run-date>/jobs.json
data/run_reports/<run-date>/jobs_report.json
```

- `raw` contains the original response saved for each source.
- `jobs.json` contains all successfully collected jobs in one standard file.
- `jobs_report.json` shows whether each source succeeded or failed.

If one source fails, it can be tested separately:

```bash
av-jobs collect --source-id SOURCE_ID
```

This separate command creates a file for that source only. It does not add the
result to an older `jobs.json`. After fixing or retrying a failed source, run
`av-jobs collect` again to create a new complete combined file.

These generated files are excluded from GitHub by `.gitignore`. They should be
shared separately with the next workstream when the final collection run is
ready.

## Standard job format

Each collected job has two parts:

- `metadata`: information used to track where the record came from. It includes
  the company, region, platform, source ID, original job ID, tracking key, and
  collection time. This information helps later workstreams trace a record back
  to its source, recognise the same job in future runs, check data quality, and
  prepare records for deduplication or database storage.
- `data`: the job information required by the current collection task. It
  contains `advertised_job_title`, `job_description`, `job_url`, `location`,
  `salary`, and `date_posted`. Later workstreams can clean, filter, translate,
  analyse, or extend these fields.

Keeping these two parts separate prevents tracking information from being mixed
with the job advertisement itself. The structure can be flattened or changed
later when the cleaned data is prepared for the final database schema.

Raw source responses are saved under `data/raw/<run-date>/`. Standardized jobs
are saved under `data/standardized/<run-date>/`. Run reports are saved under
`data/run_reports/<run-date>/`.

## Important notes

- This collected dataset is an input for later work, not the final analysis
  dataset. It may include jobs that are not related to autonomous vehicles.
  Later workstreams must clean and filter the data before analysis or further
  processing.
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
- Generated raw data, standardized data, and run reports are local outputs.
  They are excluded from GitHub by `.gitignore`.

## Latest update

The collectors for the original 27 `In Scope` sources are complete. Pony.AI US,
Horizon China, WeRide China, Stack AV USA, Tier IV Japan, AImotive Hungary, GM
USA, Inceptio China, and Tensor Global have now been verified and moved from `TBD` to
`In Scope`. Pony.AI uses
the existing Workable collector. Horizon uses the HotJob collector. WeRide uses
the existing Moka collector, and Stack AV uses the existing Greenhouse
collector. Tier IV uses the new HERP collector for all job groups on its public
company page. AImotive uses the new AImotive HTML collector. GM uses the new GM
XML collector and selects the official `#GM-AV-1` source marker. Other AV
relevance filtering belongs to the later data cleaning stage.
Inceptio uses the existing Moka field mapping and its current public Moka site.
Tensor uses a new HTML collector. Its source is marked as `Global` because the
public careers page includes jobs in the US, Singapore, Spain, and the UAE.

The previous complete run collected and automatically combined 3,118 jobs from
the original 27 sources. A new complete run will be completed after more `TBD`
sources are added. No manual file merge is required.

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
- 45 automated tests passed
- Previous complete run: 3,118 jobs from 27 sources

The collection and standardization work for the current `In Scope` sources is
complete. MySQL database loading belongs to the later backend export workstream.

## Next phase

The remaining 7 sources in the `TBD` sheet will be investigated one at a time.
A source will remain in `TBD` until its endpoint or collection method is
confirmed and it passes a live test. This work is tracked in GitHub Issue #24.

## GitHub note

The generated files inside `data/raw`, `data/standardized`, and
`data/run_reports` should not be uploaded to GitHub. They can be large and can
be created again by running the pipeline. A `.gitignore` file should be used to
exclude them before the first commit.
