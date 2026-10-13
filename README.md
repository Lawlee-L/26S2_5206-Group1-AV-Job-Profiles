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
- [Backend API](backend/README.md)
- [Dashboard](dashboard/README.md)

## Latest Reviewed Dataset

The latest reviewed English job-history dataset is:

```text
data-collection/deliverables/2026-10-10/jobs_history_translated.json
```

It contains **5,916 unique job records**. Validation found:

- no missing `source_key` values;
- no duplicate `source_key` values; and
- no remaining detected non-English job fields.

Earlier dated datasets remain available under `data-collection/deliverables/` for reproducibility and comparison.

## Running the Project

The project components can be run separately. Refer to the component documentation for complete setup instructions.

### Website

The website requires:

1. a running MySQL database with an approved published release;
2. the Flask backend API; and
3. the React frontend.

The backend normally runs at:

```text
http://127.0.0.1:5000
```

The frontend normally runs at:

```text
http://127.0.0.1:5173
```

Database credentials and API keys must be stored in local `.env` files and must not be committed to GitHub.

### Tableau Dashboard

Open the following packaged workbook with Tableau Desktop, Tableau Public Desktop, or Tableau Reader:

```text
dashboard/AV jobs market analysis_Final.twbx
```

The workbook contains a packaged Hyper extract, so a live MySQL connection is not required for viewing it.

The current dashboard is a fixed snapshot based on the **25 September 2026** classified release. Updating MySQL does not automatically refresh the packaged workbook.

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
