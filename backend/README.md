# AV Job Profiles Backend API

This folder contains Leon's read-only backend API. It sits between the published
MySQL dashboard views and the React frontend.

## Backend boundary

The backend reads the published database contract defined by:

- `v_dashboard_jobs`
- `v_dashboard_job_skills`
- `v_dashboard_skill_demand`
- `v_dashboard_clusters`
- `v_dashboard_job_details`

The backend intentionally reads only the published dashboard release. Draft or
candidate releases are not exposed through the API.

Public API handlers must not update the core analytical tables.

## Implemented routes

- `GET /api/health` - confirms the Flask service is running.
- `GET /api/health/db` - checks whether MySQL is reachable without exposing
  database details.
- `GET /api/jobs` - returns active, AV-relevant jobs from the published
  dashboard release.
- `GET /api/jobs/<source_key>` - returns one published AV job, its extracted
  skills, and its frozen job-detail fields.
- `GET /api/companies` - returns companies and their published AV job counts.
- `GET /api/skills` - returns published skill-demand information.
- `GET /api/clusters` - returns published cluster information.

`GET /api/jobs` supports:

- `page` (default `1`)
- `page_size` (default `20`, maximum `100`)
- `q` (title, company, location, generic title, or skill)
- `company`
- `country`
- `remote_type`
- `seniority`

Skill search is implemented using a distinct set of matching
`(dashboard_release_id, job_id)` pairs before joining to the job list. This
avoids repeatedly scanning the job-skill view for every job and prevents a job
from being duplicated when multiple skills match the same search term.

Whitespace-only `q` values are treated as an empty search.

## Job-detail response

`GET /api/jobs/<source_key>` includes the normal job fields plus:

- `description`
- `roleSummary`
- `responsibilities`
- `requirements`
- `detailSnapshotAvailable`

These fields are read from `v_dashboard_job_details` using both
`dashboard_release_id` and `job_id`, so the returned details remain tied to the
same frozen published release as the job.

A missing detail field is not invented. For example, `description` may be
`null` even when `detailSnapshotAvailable` is `true`.

## Setup (Windows PowerShell)

From the repository root:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env