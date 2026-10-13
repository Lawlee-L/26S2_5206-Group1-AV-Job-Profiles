# CITS5206 Group 1 — Autonomous Vehicle Job Profiles

## Project Overview

This project provides an end-to-end system for collecting, translating, analysing, storing, and presenting job advertisements from companies in the autonomous vehicle industry.

The system collects public job postings from company career websites and Applicant Tracking Systems (ATSs), standardises them into a common structure, translates non-English content, identifies AV-relevant roles and skills, stores validated releases in MySQL, and presents the results through a web application and a Tableau dashboard.

## System Workflow

```text
Company career websites and ATS APIs
                    ↓
Data collection and standardisation
                    ↓
Azure translation and validation
                    ↓
AV relevance classification and skill extraction
                    ↓
Versioned MySQL database release
                    ↓
Flask backend API
             ↙              ↘
      React website     Tableau dashboard
```

Each stage retains the original `source_key`, allowing collected jobs, classification results, database records, and displayed results to be traced back to the same source record.

## Main Features

- Weekly collection from supported company career websites and ATS platforms.
- Standardisation of job postings into a shared JSON structure.
- Cumulative job history across weekly collection runs.
- Detection and translation of non-English content using Azure Translator.
- Validation, repair attempts, checkpoints, and recovery from interrupted translation runs.
- AV relevance classification, skill extraction, seniority analysis, and job clustering.
- Versioned MySQL imports with validation, publication, rollback, and recovery support.
- Read-only Flask API for published job, company, skill, cluster, and location data.
- React website with job search, filters, job details, skills, clusters, and market trends.
- Tableau dashboard for AV job-market analysis.

## Repository Structure

```text
.
├── Meeting Minutes/          Client, facilitator, and team meeting records
├── data-collection/          Collection, translation, validation, and weekly datasets
├── classification pipeline/ AV classification, skill extraction, and clustering
├── database/                 MySQL schema, importers, releases, and validation
├── backend/                  Read-only Flask API
├── frontend/                 React and Vite web application
├── dashboard/                Tableau dashboard and documentation
├── team-guidelines/          Team processes, plans, and responsibilities
├── .gitignore
└── README.md
```

Detailed setup, usage, and testing instructions are maintained in each component’s documentation:

- [Data collection and translation](data-collection/README.md)
- [Classification and clustering](classification%20pipeline/README.md)
- [Database and import workflow](database/README.md)
- [Database team operating guide](database/TEAM_GUIDE.md)
- [Docker setup and weekly workflow](DOCKER.md)
- [Backend API](backend/README.md)
- [Frontend website](frontend/README.md)
- [Dashboard](dashboard/README.md)

## Latest Reviewed Dataset

The latest reviewed English job-history dataset is:

```text
data-collection/deliverables/2026-10-13/jobs_history_translated.json
```

It contains **6,044 unique job records**. Validation found:

- no missing `source_key` values;
- no duplicate `source_key` values; and
- no remaining detected non-English job fields.

Earlier dated datasets remain available under `data-collection/deliverables/` for reproducibility and comparison.

## Start Using the Project

- **Website:** follow [First-time website setup](DOCKER.md#first-time-website-setup).
  It starts the site and loads the included data; no Azure/OpenRouter keys or
  new AI classification are needed. Then open http://localhost:8080 on that computer.
- **Tableau dashboard:** download [AV jobs market analysis_Final.twbx](dashboard/AV%20jobs%20market%20analysis_Final.twbx)
  (open the file link, then choose **Download raw file**) and open it in Tableau
  Desktop, Tableau Public Desktop, or Tableau Reader. It includes its data and
  does not need MySQL. See [dashboard instructions](dashboard/README.md).

The website initially uses the 13 October 2026 snapshot; the separate Tableau
workbook uses 25 September 2026. `localhost` is a local address, not a public
website link. To use a hosted deployment, obtain its URL from the project operator.

## Website Maintenance and Handover

Start with [the Docker guide](DOCKER.md) to run the website and update its data.
The React website reads published MySQL data through the Flask API. Collection,
classification and database import are operator-started jobs; there is no
scheduled end-to-end data update in the current setup.

| Task | Guide |
| --- | --- |
| Start the website, configure credentials, run a weekly update | [Docker guide](DOCKER.md) |
| Validate/import data, publish a release, back up or recover MySQL | [Database operating guide](database/TEAM_GUIDE.md) |
| Revert or correct a published data release | [Release revisions](database/RELEASE_REVISIONS.md) |
| Check the API and database connection | [Backend guide](backend/README.md) |
| Understand the website filters and charts | [Frontend guide](frontend/README.md) |
| Open or refresh the separate Tableau workbook | [Dashboard guide](dashboard/README.md) |

### Updating Data

1. Collect and classify a dated dataset, or download an existing reviewed pair:
   `data-collection/deliverables/<date>/jobs_history_translated.json` and its
   complete classification output folder. Existing output can be imported
   without rerunning paid classification.
2. On the machine hosting the website database, validate and import the
   collection and its matching classification by following
   [the weekly Docker steps](DOCKER.md#weekly-pipeline). Keep the same date and
   exact source file throughout.
3. Use `import-analysis --publish` to run blocking release QA and publish only
   when it passes. Inspect any warnings, then reload the website and verify the
   API and pages as described in the Docker guide.

Uploading files to GitHub shares the dataset; it does **not** import it into
MySQL. Importing into a developer's local database does not update a website
connected to another database. Keep the Compose project name consistent so
commands use the intended database and cache volumes.

With Watchtower enabled, new backend/frontend images can update automatically
when published. This updates application code, not job records, classification,
or database schema. The separate Tableau `.twbx` workbook contains a saved
extract and requires its own refresh and save to show newer data.

### Responsibilities at Handover

Record the deployed URL, hosting machine, Compose project name, published data
week/release key and maintenance contact before handing over. Assign an operator
for data updates, publication, API costs, backups and recovery. Transfer access
to the hosting account, registry and API services securely; keep passwords and
API keys out of GitHub. Store database backups outside the container and retain
a separate copy. Ordinary website visitors do not run these maintenance steps.

## Testing and Validation

The project includes automated and manual checks covering:

- source configuration and collector behaviour;
- data standardisation and cumulative history;
- translation, retry, repair, and validation behaviour;
- classification processing, caching, and storage;
- database imports, release activation, rollback, backup, and restore;
- location parsing and structured-location handling;
- backend routes, pagination, filters, and published-release isolation;
- frontend rendering, loading states, filters, and backend integration; and
- dashboard figures, filters, geographic analysis, and skill analysis.

Most automated tests use local fixtures or simulated services and do not consume Azure or LLM credits. Real database and end-to-end checks are performed separately against approved project data.

## Data and System Limitations

- External career websites may become unavailable, respond slowly, block automated requests, or change their APIs.
- If an individual source fails temporarily, its previous history records are retained rather than treated as removed jobs.
- Some source websites do not provide reliable structured city, state, or country fields. Uncertain values are left empty instead of being guessed.
- Translation and classification outputs may require human review even after automated validation.
- The Tableau workbook is a fixed validated snapshot and is not automatically refreshed when a new database release is published.
- API keys, passwords, local working files, translation checkpoints, and generated raw data are excluded from GitHub.

## Team Members

| Name | Student ID | GitHub Username | Main Responsibilities |
|---|---:|---|---|
| Li Luo | 24250049 | `Lawlee-L` | Project coordination, data collection, and translation |
| Nyx Chen | 24290498 | `hot-tofu-curd` | Database design and system integration |
| Seonjeong Jeong | 24732339 | `seon-jeongx2` | Data analysis and Tableau dashboard |
| Sunjol Singh Paul | 24433446 | `sunjol` | Classification, skill extraction, and clustering |
| Thushamini Chathusika Hewa Pathegamage | 24562882 | `Chathushika2000` | Frontend development |
| Leon Nel Nel | 24268801 | `DemionNeo1` | Backend API development |

The Team Lead role rotated between Li Luo, Seonjeong Jeong, and Nyx Chen during the project.

## Project Records

Meeting minutes are stored under `Meeting Minutes/`. Team plans, responsibilities, working agreements, and progress records are stored under `team-guidelines/`.

These records document the team’s decisions, responsibilities, validation activities, and project development process.
