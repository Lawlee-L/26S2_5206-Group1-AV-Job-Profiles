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
candidate releases are not exposed through the public API.

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
- `GET /api/locations` - returns country-qualified location options and
  available work arrangements from the current active published AV release.

## Jobs endpoint

`GET /api/jobs` supports:

- `page` - default `1`
- `page_size` - default `20`, maximum `100`
- `q` - searches title, company, location, generic title, or skill
- `company`
- `country`
- `state_region`
- `city`
- `remote_type`
- `seniority`

Skill search is implemented using a distinct set of matching
`(dashboard_release_id, job_id)` pairs before joining to the job list.

This avoids repeatedly scanning the job-skill view for every job and prevents
a job from being duplicated when multiple skills match the same search term.

Whitespace-only `q` values are treated as an empty search.

## Location filtering

Structured location filtering uses the published database fields:

- `countryCode`
- `stateRegion`
- `city`
- `remoteType`

Country codes are represented as two-letter codes such as:

```text
US
AU
DE
GB
```

Region and city filters are country-qualified. A `country` parameter is
required whenever `state_region` or `city` is supplied.

Examples:

```text
/api/jobs?country=US
/api/jobs?country=US&state_region=CA
/api/jobs?country=US&state_region=CA&city=San%20Francisco
/api/jobs?remote_type=hybrid
```

A request such as:

```text
/api/jobs?city=San%20Francisco
```

is rejected with HTTP `400` because the city is not qualified by a country.

Supported `remote_type` values are:

```text
remote
hybrid
onsite
```

`remoteType` represents work arrangement, not employment type.

Unknown or ambiguous location information remains unknown. The backend does
not infer a country, region, city, or work arrangement when the published
database does not provide one.

## Location options endpoint

`GET /api/locations` provides the frontend with location and work-arrangement
options derived from the current active AV release.

Example response structure:

```json
{
  "data": {
    "releaseId": 7,
    "releaseKey": "example-release",
    "locations": [
      {
        "countryCode": "US",
        "stateRegion": "CA",
        "city": "San Francisco",
        "jobCount": 12
      }
    ],
    "workArrangements": [
      {
        "value": "hybrid",
        "jobCount": 15
      }
    ]
  }
}
```

The backend does not maintain a hard-coded list of countries, regions, cities,
or work arrangements.

The location and work-arrangement queries are pinned to the same
`dashboard_release_id` so that options from different releases cannot be mixed.

If the current published release contains no structured location information,
the endpoint may correctly return empty `locations` and `workArrangements`
arrays while still identifying the current release.

## Job-detail response

`GET /api/jobs/<source_key>` includes the normal job fields plus:

- `description`
- `roleSummary`
- `responsibilities`
- `requirements`
- `detailSnapshotAvailable`

These fields are read from `v_dashboard_job_details` using both
`dashboard_release_id` and `job_id`.

This ensures the returned job details belong to the same frozen published
release as the main job record.

A missing detail field is not invented. For example, `description` may be
`null` even when `detailSnapshotAvailable` is `true`.

## Published-release safety

The backend reads only approved published dashboard views.

Candidate-mode access is intentionally not supported because combining jobs,
skills, or other information from different releases could produce inconsistent
API responses.

Related database reads are release-scoped wherever necessary.

## Setup on Windows

From the repository root:

```cmd
cd backend
```

Activate the repository virtual environment in Command Prompt:

```cmd
..\.venv\Scripts\activate.bat
```

If a virtual environment has not yet been created, create and install the
backend dependencies first.

For example:

```cmd
py -3.11 -m venv ..\.venv
..\.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

Copy the example configuration if needed:

```cmd
copy .env.example .env
```

Edit `.env` with the read-only MySQL credentials supplied by the database
owner.

Do not commit `.env`.

## Running the API

From the `backend` directory:

```cmd
python wsgi.py
```

The local development server normally runs at:

```text
http://127.0.0.1:5000
```

Useful endpoints include:

```text
http://127.0.0.1:5000/api/health
http://127.0.0.1:5000/api/health/db
http://127.0.0.1:5000/api/jobs
http://127.0.0.1:5000/api/companies
http://127.0.0.1:5000/api/skills
http://127.0.0.1:5000/api/clusters
http://127.0.0.1:5000/api/locations
```

An individual job request uses a URL-encoded `source_key`:

```text
GET /api/jobs/<source_key>
```

## Tests

Run the backend test suite from the `backend` directory:

```cmd
python -m pytest -q
```

The automated tests cover areas including:

- health and database-health routes;
- jobs listing and pagination;
- invalid pagination parameters;
- individual job lookup;
- company, skill, and cluster endpoints;
- frozen job-detail handling;
- missing job-detail rows;
- JSON detail-array validation;
- optimized skill search;
- whitespace-only search behavior;
- country, region, and city filtering;
- country-qualified city and region validation;
- work-arrangement validation;
- parameterized location predicates;
- the `/api/locations` endpoint;
- release-pinned location-option queries;
- protection against mixed-release location data.

Most route tests use a fake repository and therefore do not require a live
MySQL database.

Real database integration tests should also be performed against an approved
published release before deployment.

## Database access

The backend database account should have read-only `SELECT` access to the
published dashboard views required by the API.

The backend must not directly update:

- collection tables;
- analysis tables;
- skill tables;
- cluster tables;
- release snapshots;
- label history.

Changes to the database contract should be made through reviewed database
migrations or view changes.

## Structured-location data availability

The API supports structured location fields, but their availability depends on
the currently published frozen release.

An older frozen release may contain:

```text
countryCode = null
stateRegion = null
city = null
remoteType = null
```

even when the original raw `location` field contains location text.

The backend must not reconstruct or guess those values itself. A
location-enriched release must be created and published through the database
release process before the structured fields appear in the public API.

The original raw `location` value remains available as a display fallback.

## Current database-contract limitation

Employment type is not currently part of the published dashboard view contract.

`remoteType` describes work arrangement only:

```text
remote
hybrid
onsite
```

It must not be presented as an employment-type value such as full-time,
part-time, or contract.

The backend does not invent an employment type when the database does not
provide one.

Any additional analytical field required by the frontend should first be added
through a reviewed database-view contract change.