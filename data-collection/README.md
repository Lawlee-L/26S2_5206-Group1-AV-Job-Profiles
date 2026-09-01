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

The platform can currently be `greenhouse`, `lever`, or `ashby`.

Run all available collectors:

```bash
av-jobs collect
```

During testing, each platform has a separate standardized file, such as
`greenhouse.json`, `lever.json`, or `ashby.json`. A full run combines all
available results into `jobs.json`. No manual merge is needed.

## Standard job format

Each collected job has two parts:

- `metadata`: company, platform, source ID, tracking key, and collection time.
- `data`: title, description, job URL, location, salary, and posted date.

Raw source responses are saved under `data/raw/<run-date>/`. Standardized jobs
are saved under `data/standardized/<run-date>/`. Run reports are saved under
`data/run_reports/<run-date>/`.

## Current progress

Completed:

- Excel configuration reader and validation
- Standard job data model
- Raw and standardized JSON storage
- Greenhouse collector: 12 sources tested
- Lever collector: 6 sources tested
- Ashby collector: 3 sources tested
- 21 sources tested successfully
- 1,898 job postings collected in the latest test

Still to do:

- Workable collector
- Comeet collector
- Moka collector
- SmartRecruiters collector
- Jobylon collector
- MySQL database connection and data loading

## GitHub note

The generated files inside `data/raw`, `data/standardized`, and
`data/run_reports` should not be uploaded to GitHub. They can be large and can
be created again by running the pipeline. A `.gitignore` file should be used to
exclude them before the first commit.
