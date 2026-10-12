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
- `skill` - exact skill name, combined with other filters
- `posted_after` - inclusive advertised date in `YYYY-MM-DD` format
- `has_salary` - `true` or `false`; any source salary text/numeric bound, not normalised pay
- `sort` - `newest` (default), `oldest`, `title`, or `company`

The frontend integration guide is [frontend/README.md](../frontend/README.md).
Raw fields are retained; additive `locationDisplay`, `salaryDisplay`, and (in job
details) `descriptionDisplay` contain plain text for safe display. This change
does not update source records or require new database columns.

For skill joins, the frozen jobs view is materialised once using a non-merging
derived-table boundary. This prevents MySQL from repeatedly unpacking JSON
snapshots for each matching skill. Both the count and page query use this boundary
and the same parameterised filters. Exact skill matches are distinct release/job
pairs, just like partial skill matches from `q`.

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
## Faceted filter options and URL state

`GET /api/job-facets` accepts the same filter parameters and validation as
`GET /api/jobs` (page/sort are irrelevant). It returns `total`, `releaseIds`,
`company`, `country`, `state_region`, `city`, `remote_type`, `seniority`, `skill`,
`has_salary`, `salary_units` and `posted_range`. Each categorical entry has
`value` and `count`. Counts use **all active AV jobs**, not the current page.
Each facet excludes its own condition when counting compatible alternatives;
parent locations also exclude children. Salary units exclude currency/period/
bounds, because changing units clears the bounds in the UI. No zero-count choices
are offered by the API. Search treats `%` and `_` as literal text, not SQL wildcards.

This MVP-sized read-only index loads frozen jobs/skills into memory and caches it
for at most 15 seconds per repository instance. Every request checks the current
release identity; database/view/release changes invalidate the cache. Loading
rechecks that identity to reject a mixed-release index. It never writes imported
or published data. This avoids repeatedly unpacking snapshot JSON for every menu.
For much larger datasets, replace the index with indexed release projections and
server-side facet aggregation. Each production worker has its own cache.

The React URL stores filters, pagination and sort. The backend remains stateless;
detail and list queries continue to read the selected published views. Updating
these features requires a backend restart and matching frontend code, not a
schema migration or data reimport.

## Numeric salary projection and filtering

`GET /api/salary-options` returns known currency/period pairs and counts from the
active AV jobs in the selected repository views. `GET /api/jobs` also accepts
`salary_currency` (e.g. `JPY`), `salary_period` (`hour`, `day`, `week`, `month`,
`year`), `salary_min` and `salary_max` (nonnegative amounts, at most two decimals).
Both currency and period are mandatory for numeric bounds. Reversed bounds,
NaN/infinity and unsupported units return HTTP 400.

Matching uses inclusive range overlap. A minimum requires a known advertised
upper bound; a maximum requires a known lower bound. Unknown units are not
inferred, and annual/FX conversions are not performed. `salaryMin`, `salaryMax`,
`salaryCurrency`, `salaryPeriod` now use the conservative read-only projection;
raw `salary` remains unchanged. `salaryNormalization` exposes parser version,
status, symbol and reason. Bare dollar/yen symbols and missing periods are not
silently converted to USD/year. Ambiguous multiple ranges retain raw text.

Parsing uses a bounded cache of immutable source-field tuples, not a stale global
release cache. Salary filtering scans all eligible frozen salary rows **before**
pagination and joins parameterised release/job pairs via JSON_TABLE, preserving
counts and release scoping alongside search/skill filters. This is an MVP-scale
read projection; at much larger scale, persist versioned normalisation at release
creation and index it. No direct writes or schema migration are made here.

Restart the backend after updating code. See [frontend guide](../frontend/README.md)
for the matching controls and smoke-test commands. Tableau/SQL readers continue
to see snapshot values, not this API-only projection.

## Read-only skill/cluster analytics

`GET /api/insights` returns `{data: {current, history, method}}` for the React
`/clusters` and `/trends` pages. It uses one consistent, read-only MySQL transaction.
Seven bulk SELECTs read the published/weekly views; no writes, base-table access,
per-cluster database queries, paid LLM calls, or data imports occur.
The backend account needs the existing weekly-view SELECT grants documented in
`database/TEAM_GUIDE.md`; do not solve permissions by granting base-table writes.

`current` includes the published release key/date, distinct active AV job count,
company count, populated non-noise cluster count, unclustered count, missing-skill
count, the cluster directory and top 100 skills. Each cluster includes its
number, suggested/supplied name and status, active job count/share, extracted
skills, keywords, companies and three example active job links. A cluster's
cached historical size is deliberately not treated as its active job count.
Case variants of a skill are deduplicated for each job.

`history.points` contains official dated collection versions, active/total raw
counts, company/source coverage, classification status, release/run keys and
collection-quality metadata. AV job/group/noise counts are available only for
the matching frozen official analysis; otherwise they are `null`.
`history.skillSeries` contains up to 20 leading tool/domain skills, with distinct
job counts and shares for each date. A missing skill in a classified snapshot
is zero extracted occurrences; a missing classification is unknown (`null`).
Raw collection totals may include inactive history; charts use **active** counts.

Names follow `display-rules-v2` in `app/repositories/insights.py`; supplied names
take precedence. Rule-based names are provisional suggestions and never replace
approved names or mutate the database. Noise is not a profession or a non-AV label.
Run-local cluster numbers must not be used to match categories across analyses.
History is explicitly a dated-snapshot comparison, not a verified market trend;
the importer's verified-crawl/comparable-source gate is not relaxed.

Restart the backend and use the matching frontend. No schema migration/reimport
is required to display already imported versions. To add history, follow the
database team's separate collection/classification/import/release workflow.
Unit tests cover inactive/non-AV exclusion, skill deduplication, label precedence,
unknown gaps versus zero, missing metadata, and the consistent read transaction.

## Product read projections and location alias consistency

`GET /api/job-facets` additionally returns `snapshotDate`, `releaseKey` and
`skillTypes`. The date comes from the official weekly version matched to the
published release, not the newest job date. The release/date identity participates
in cache validation. Skills remain exact matches; type metadata lets the frontend
separate qualifications from tools/domain knowledge without changing SQL filtering.

`app/locations.py` (`location-aliases-v1`) is an explicit country-scoped read
projection. It changes API display/grouping for known aliases, not imported data.
Facets, parameterised SQL predicates, details and `/api/locations` all use the
same dictionary. When country is absent, SQL alias alternatives still carry their
country condition; a Canadian abbreviation never reclassifies a US location.
Job responses expose the original `locationSourceFields` and `locationAliasVersion`.
Raw location text remains unchanged. Direct SQL/Tableau readers still see original
frozen values; this update adds no columns, migrations or database writes.

New aliases require evidence and country/field-specific tests. Do not use fuzzy
matching or remove 'City' indiscriminately: Chuo City and named districts must
remain distinct. See the frontend guide for sources, UI behaviour and test commands.
