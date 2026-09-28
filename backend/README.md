# AV Job Profiles Backend API

This folder contains Leon's read-only backend API. It sits between the published
MySQL dashboard views and the React frontend.

## Backend boundary

The backend reads the database contract defined by:

- `v_dashboard_jobs`
- `v_dashboard_job_skills`
- later: `v_dashboard_skill_demand`
- later: `v_dashboard_clusters`

Public API handlers must not update the core analytical tables.

## Current first milestone

Implemented routes:

- `GET /api/health` - confirms the Flask service is running.
- `GET /api/health/db` - checks whether MySQL is reachable without exposing database details.
- `GET /api/jobs` - returns active, AV-relevant jobs from the published dashboard release.
- `GET /api/jobs/<source_key>` - returns one current AV job plus its extracted skills.

`GET /api/jobs` supports:

- `page` (default `1`)
- `page_size` (default `20`, maximum `100`)
- `q` (title, company, location, generic title, or skill)
- `company`
- `country`
- `remote_type`
- `seniority`

## Setup (Windows PowerShell)

From the repository root:

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with the read-only MySQL credentials supplied by the database owner.
Do not commit `.env`.

Run the API:

```powershell
python wsgi.py
```

Then open:

```text
http://127.0.0.1:5000/api/health
```

When the database is available, also check:

```text
http://127.0.0.1:5000/api/health/db
http://127.0.0.1:5000/api/jobs
```

## Tests

```powershell
pytest -q
```

The route tests use a fake repository, so they do not require a live MySQL database.

## Known database-contract gap

The current `v_dashboard_jobs` view does not expose `job_description`. The React
job-details design contains a description section, so backend development should
not bypass the view and query core tables directly. If the MVP needs the original
job description, request a reviewed view extension from the database/integration
owner.

The current frontend also shows an employment type, but that field is not part of
the current dashboard view contract. Do not invent a value in the API.
