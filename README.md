# CITS5206 Group 1 — AV Job Profiles

This repository is the central workspace for the CITS5206 Group 1 project. It is used to organise meeting records, team planning documents, project tasks, and data-collection work.
## Website maintenance and handover

Start with [the Docker guide](DOCKER.md) to run the website and update its data.
The React website reads published MySQL data through the Flask API. Collection,
classification and database import are separate jobs started by an operator;
there is no scheduled end-to-end data update in the current setup.

| Task | Guide |
| --- | --- |
| Start the website, configure credentials, run a weekly update | [Docker guide](DOCKER.md) |
| Validate/import data, publish a release, back up or recover MySQL | [Database operating guide](database/TEAM_GUIDE.md) |
| Revert or correct a published data release | [Release revisions](database/RELEASE_REVISIONS.md) |
| Check the API and database connection | [Backend guide](backend/README.md) |
| Understand the website filters and charts | [Frontend guide](frontend/README.md) |
| Open or refresh the separate Tableau workbook | [Dashboard guide](dashboard/README.md) |

### Updating data

1. Collect and classify a dated dataset, or download an existing reviewed pair:
   `data-collection/deliverables/<date>/jobs_history_translated.json` and its
   complete classification output folder. Existing output can be imported
   without rerunning paid classification.
2. On the machine hosting the website database, use the importer to validate
   and import the collection and its matching classification, following
   [the weekly Docker steps](DOCKER.md#weekly-pipeline). Keep the same date and
   exact source file throughout.
3. Check QA and its warnings, then publish the approved release. Reload the
   website and verify the API and pages as described in the Docker guide.

Uploading files to GitHub shares the dataset; it does **not** import it into
MySQL. Importing into a developer's local database does not update a website
connected to another database. Keep the Compose project name consistent so
commands use the intended database and cache volumes.

With Watchtower enabled, new backend/frontend images can update automatically
when published. This updates application code, not job records, classification,
or database schema. The separate Tableau `.twbx` workbook contains a saved
extract and requires its own refresh and save to show newer data.

### Responsibilities at handover

Record the deployed URL, hosting machine, Compose project name, published data
week/release key and maintenance contact before handing over. Assign an operator
for data updates, publication, API costs, backups and recovery. Transfer access
to the hosting account, registry and API services securely; keep passwords and
API keys out of GitHub. Store database backups outside the container and retain
a separate copy. Ordinary website visitors do not run these maintenance steps.

## Team Members

| Name | Student ID | GitHub Username | Role |
|---|---:|---|---|
| Li Luo | 24250049 | `Lawlee-L` | Team Lead and Facilitator Liaison |
| Nyx Chen | 24290498 | `hot-tofu-curd` | Future Team Lead and Team Member |
| Seonjeong Jeong | 24732339 | `seon-jeongx2` | Current Team Lead and Team Member |
| Sunjol Singh Paul | 24433446 | `sunjol` | Client Liaison and Team Member |
| Thushamini Chathusika Hewa Pathegamage | 24562882 | `Chathushika2000` | Team Member |
| Leon Nel Nel | 24268801 | `DemionNeo1` | Team Member |

The Team Lead role will rotate from **Li Luo** to **Seonjeong Jeong** and then to **Nyx Chen** during the project.
## Repository Structure

```text
.
├── Meeting Minutes/     Team and client meeting records
├── data-collection/     Job collection, translation, validation, and datasets
├── team-guidelines/     Team processes, responsibilities, and project planning
├── .gitignore           Files and local data excluded from GitHub
└── README.md            Project overview and repository guide
```

## Meeting Minutes

This folder contains the records of client, facilitator, and team meetings.

It also contains:

- `CITS5206 Meeting Minutes Rotation.md` — records the assigned minute-taker for each meeting.
- `Template.md` — provides the required format for meeting minutes.

The assigned minute-taker should follow the template and upload the completed minutes to the correct folder.

## Data Collection

This folder contains the project’s weekly job data collection and translation workflow. It includes source configuration, collectors for supported recruitment platforms, data standardisation, cumulative job-history management, non-English content detection, Azure translation, validation, and dated English datasets for downstream analysis.

Generated raw data, weekly snapshots, run reports, and working history files are stored locally. Only reviewed English datasets under `deliverables/` are intended to be uploaded to GitHub.

## Team Guidelines

This folder contains the main team collaboration and project-planning documents.

- `Weekly Project Plan.md` — records weekly goals, tasks, responsibilities, deadlines, risks, and progress.
- `team-code-of-conduct.md` — records the team's agreed roles, communication methods, meeting arrangements, and working expectations.

All members should regularly review these documents and update their assigned tasks when completed.

## Team Responsibilities

Team members are expected to:

- Check Microsoft Teams and GitHub regularly.
- Complete assigned tasks by the agreed deadlines.
- Update task status when work is completed.
- Follow the required meeting-minutes format.
- Communicate delays, blockers, or support needs early.
- Keep project records clear and up to date.

## Current Project Stage

The project has progressed from initial investigation to implementation and integration. The team is developing and testing the data collection, translation, data cleaning, job classification, database, and dashboard components. The current focus is on connecting these components into a reliable end-to-end workflow, validating data quality, refining the MVP, and incorporating feedback from the client and facilitators. For local MySQL setup and the exact data import/publication workflow, use the [database team operating guide](database/TEAM_GUIDE.md).
