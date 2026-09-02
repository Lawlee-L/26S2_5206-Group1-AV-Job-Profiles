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

From the project folder, install the project and its packages:

```bash
python -m pip install -e .
```

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
`comeet`, `moka`, `smartrecruiters`, or `jobylon`.

Run all available collectors:

```bash
av-jobs collect
```

During testing, each platform has a separate standardized file, such as
`greenhouse.json`, `lever.json`, or `ashby.json`. A full run combines all
available results into `jobs.json`. No manual merge is needed.

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
- Some platforms require one detail request for every job. A complete run can
  therefore take several minutes, especially for the large Bosch sources.
- Job numbers can change between runs because companies add or remove jobs.
- Generated raw data, standardized data, and run reports are local outputs.
  They are excluded from GitHub by `.gitignore`.

## Latest update

The current update completed the collection and standardization work for all
27 `In Scope` sources. It added the SmartRecruiters and Jobylon collectors,
registered them in the main pipeline, and added tests for their field mapping.

The latest complete run successfully collected and automatically combined
3,118 jobs from eight platforms. All 26 automated tests passed. No manual file
merge is required.

## Current progress

Completed:

- Excel configuration reader and validation
- Standard job data model
- Raw and standardized JSON storage
- Greenhouse collector: 12 sources tested
- Lever collector: 6 sources tested
- Ashby collector: 3 sources tested
- Workable collector: 1 source tested
- Comeet collector: 1 source tested
- Moka collector: 1 source tested
- SmartRecruiters collector: 2 sources tested
- Jobylon collector: 1 source tested
- 27 sources tested successfully
- 3,118 job postings collected in the latest test

The collection and standardization work for the current `In Scope` sources is
complete. MySQL database loading belongs to the later backend export workstream.

## GitHub note

The generated files inside `data/raw`, `data/standardized`, and
`data/run_reports` should not be uploaded to GitHub. They can be large and can
be created again by running the pipeline. A `.gitignore` file should be used to
exclude them before the first commit.
