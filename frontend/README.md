# Student job portal: local setup and integrated filters

For the complete website/data handoff and Docker integration checklist, see
[the integration runbook](../docs/integration/README.md). It includes Windows
and macOS/Linux startup commands, publication checks and the fixes required
in the checked Docker PR; it does not claim unexecuted container validation.

## What this website does

The React portal reads **active, AV-relevant jobs from the published MySQL release**
through Leon's Flask API. It does not run collection, classification, or imports.
The `/clusters` and `/trends` pages also provide a read-only analysis view for
teachers and other stakeholders. Tableau remains available as a separate workflow.

The styling uses Bootstrap 5.3.8 for forms, grids, buttons and cards, with the
UWA navy/gold brand theme in `src/theme.css`. Existing page illustrations/layouts
remain in `src/styles.css`. Interactive controls use React state, not Bootstrap's
imperative JavaScript. Lucide supplies icons only. Company logos are optional:
without a Logo.dev publishable key, a company website icon is loaded through
Google's favicon service. If loading fails, the company initial is shown.
These are website icons, not necessarily full wordmark logos. Known company
aliases and name casing are normalised. No account/key is required for the fallback.
Both services are external: the browser sends the public company domain to them;
no job records are sent. `referrerPolicy="no-referrer"` prevents sending the page URL.
Only `pk_` publishable keys are accepted; never put a secret key into a Vite variable.
Initials remain visible while images load; there is no empty icon box on slow networks.
Images load lazily. A company change resets a previous image failure. Icons below
32 pixels are rejected to avoid generic/blurred tiny icons; initials remain the fallback.

## 1. Prepare the database and start the backend

Follow [the database team guide](../database/TEAM_GUIDE.md) to import and publish a
release, and [the backend guide](../backend/README.md) to configure `backend/.env`.
Use a read-only backend database account. Do not point the app at an unverified database.
This change adds API parameters and presentation fields, **not database columns**;
there is no new schema migration or reimport for this frontend/backend fix.
Existing releases without structured locations continue to show source text, but
country/city filters require the location-enriched release described in
[Location integration](../database/LOCATION_INTEGRATION.md).

Windows PowerShell (from `backend/`):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe wsgi.py
```

macOS/Linux (from `backend/`):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python wsgi.py
```

Keep this terminal running. The default backend URL is `http://127.0.0.1:5000`.

## 2. Start this frontend

Copy [frontend/.env.example](.env.example) to local `frontend/.env` and edit it
(do not commit your configured file). Run from the repository root:

```powershell
# Windows: preserve an existing configuration.
if (-not (Test-Path frontend/.env)) { Copy-Item frontend/.env.example frontend/.env }
```

```bash
# macOS/Linux: preserve an existing configuration.
if [ ! -e frontend/.env ]; then cp frontend/.env.example frontend/.env; fi
```

| Variable | Required / optional | Value and purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Required for a non-default backend/deployment; optional for the default local setup | Backend origin, e.g. `http://127.0.0.1:5000`. No `/api` suffix or trailing slash; routes already append `/api/...`. |
| `VITE_LOGO_DEV_TOKEN` | **Optional** | Logo.dev CDN **publishable** `pk_...` key. Leave blank for website icons/initials; never use a secret `sk_...` key. |

Local example:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:5000
VITE_LOGO_DEV_TOKEN=
```

**Docker responsibility:** these variables are frontend **build-time** settings,
not Flask settings. An intended empty API base for same-origin nginx proxying
requires the changes in [integration guide section 5.1](../docs/integration/README.md#51-route-frontend-requests-through-nginx).
Current `main` still has a `||` fallback, so an empty value alone does not enable
same-origin requests. Sunjol must wire the build arguments/environment and
rebuild the image. Copying this template or changing only the running container's
environment does not make those changes. Do not set the base to `/api` or the
Docker-internal service hostname. Every `VITE_*` value is browser-visible.

In `backend/.env`, allow the exact frontend origin, for example:

```dotenv
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

From `frontend/`, on Windows or macOS/Linux:

```bash
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open `http://127.0.0.1:5173/jobs`. Restart Vite after changing `.env`.
If using different ports, update both the API base URL and backend CORS origins.
Do not deploy these development servers as public production services.

The Docker build intentionally leaves `VITE_API_BASE_URL` empty so browser requests
use the same-origin `/api` proxy provided by nginx. The `127.0.0.1:5000` setting
above is only for running the frontend and backend as separate development servers.

## 3. Search and filtering

All filters are combined with **AND**, except that the general search checks
title/company/location/skill with **OR**. Results are paginated by the backend,
not filtered only within the current page.

| Control | Backend parameter | Meaning |
|---|---|---|
| Search | `q` | Partial title, generic title, company, source location, or skill |
| Country | `country` | Country name shown to the user; two-letter code sent to API |
| State / region | `state_region` | Structured region, including approved country-scoped aliases |
| City | `city` | Structured city, including approved country-scoped aliases |
| Experience level | `seniority` | Classified level, not employment contract type |
| Work arrangement | `remote_type` | `remote`, `hybrid`, `onsite`; not full-time/part-time |
| Company | `company` | Exact company name |
| Skill | `skill` | Exact extracted skill; type and select in one searchable control |
| Posted since | `posted_after` | Inclusive advertised date (`YYYY-MM-DD`); missing dates excluded |
| Salary information | `has_salary` | `true` / `false`: source salary text or numeric bound is present / absent |
| Salary unit | `salary_currency`, `salary_period` | Explicit currency and hour/day/week/month/year combination |
| Minimum / maximum amount | `salary_min`, `salary_max` | Inclusive overlap with the advertised range; click Apply salary range |
| Sort | `sort` | `newest`, `oldest`, `title`, `company` |

Changing country clears region/city; changing region clears city. Changing an
actual filter resets pagination. Clear resets all filters and sorting.
All filter choices come from `/api/job-facets`, not a hardcoded country list.
Selecting a company, country, skill or another condition narrows the other menus
to compatible options. Counts beside each option show the number of matching jobs.
A menu ignores its own selected value when calculating alternatives, so users can
change it without first clearing it. Country/region menus ignore child location
values because changing a parent clears those children. Salary units ignore the
current amounts because changing units clears the amounts.

The basic panel shows company, country, skill, work arrangement and experience. **More
filters** opens city/region, posting date and salary controls. Collapsing
this panel keeps active filters; removable chips show what is still applied.
Options are disabled while a newer request is loading, preventing selection from
stale choices. If loading fails, retry or remove/clear conditions; the page does
not silently fall back to all-company options. Typed search/date/salary bounds can
still intentionally produce no results. Previously bookmarked unavailable options
remain visible with count zero; remove the chip to widen the search.

Filters, sort order, page number and panel state are saved in the URL. Opening a
job carries that context to its detail page. **Back to Jobs**, browser Back and
refresh restore the same search. URLs can be copied/bookmarked; do not put private
information in search terms. Changing a real filter resets the page to one.

Unknown and multi-location records remain visible without a structured location
filter; no country is guessed. The searchable skill picker shows up to 60 matches,
grouped into tools/technical skills, domain knowledge and qualifications.
Use Arrow keys and Enter to choose, Escape to cancel, or the clear button to remove
the selected skill. Typing alone does not apply an arbitrary value.

Salary provided means source information exists, not that it is comparable.
Choose a salary unit before entering numbers. For `USD / year`, a minimum of
100,000 finds advertised bands whose known upper bound is at least 100,000;
a maximum of 200,000 requires a known lower bound no greater than 200,000.
This is **range overlap**, not a guaranteed offer or a minimum guaranteed salary.
Changing units clears old bounds; Clear removes all salary filters. Unknown
currency/period or a missing required bound is excluded from numeric filtering.
No exchange-rate conversion, annualisation or salary-period guessing is used.

The backend adds a versioned, read-only numeric projection for existing published
data. Existing valid numeric fields take precedence. Explicit source ranges are
parsed (including K notation, decimal commas and Japanese yen). A Tier IV
Estimated Monthly Salary line is kept separate from base salary and fixed
overtime; those components are not added together. Bare `$` does not establish
USD, and missing periods are never treated as annual pay. Multiple pay bands or
conflicting currencies/periods retain source text instead of an invented range.
**No database migration, reimport or release activation is required for this UI/API
feature.** Frozen data remains unchanged; numeric fields returned by the API may
now be populated even where the snapshot stores nulls. The direct SQL views used
by Tableau are unchanged and do not gain these derived salary numbers.

## 4. Display contract and long source fields

Backend raw `location`, `salary`, and `description` fields remain available.
Additive `locationDisplay`, `salaryDisplay`, and `descriptionDisplay` fields strip
HTML and decode entities into plain text; source database rows are not modified.
The frontend never inserts this text as executable HTML.

Cards prefer the known city/region/country hierarchy. Salary appears on its own
labelled row, not inside the location row. Long fields wrap without overlapping.
The detail page has a numeric salary preview when reliable amounts are available,
otherwise a short text preview, and separate expandable full location
and salary information. A long description is also expandable, with the role
summary and extracted responsibilities/requirements still available.

An original salary line such as `San Jose: $75k–$300k USD` is geographically
qualified pay, not a wrongly mapped location field. Keep the location qualification
in salary information so users do not assume that amount applies everywhere.

## 5. Verify before merging

From `frontend/`:

```bash
npm test
npm run build
npm audit
```

From `backend/` (Windows):

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tests/live_smoke.py http://127.0.0.1:5000
```

From `backend/` (macOS/Linux):

```bash
.venv/bin/python -m pytest -q
.venv/bin/python tests/live_smoke.py http://127.0.0.1:5000
```

The smoke test requires a nonempty published release and makes read-only requests.
Also check desktop and narrow screens, country→region→city reset, a rare skill,
combined filters and option counts, pagination, list→detail→Back/refresh state,
a directly opened detail URL, long salary/location
text, missing values, and Clear. Unit tests use fixtures; they do not replace a
real MySQL check. Build output is generated locally and is not part of this fix.

## 6. Skill clusters and historical charts

- **Skill clusters** (`/clusters`): active AV job counts, top-10 cluster and skill
  bar charts, search, clustered/unclustered selection, expandable skills/keywords,
  and links to example active jobs. Skill links intentionally search *all* jobs
  with that skill, not only the displayed cluster.
- **Historical trends** (`/trends`): dated active-job coverage, skill demand
  (job count or percentage), non-noise cluster count, unclustered share, and a
  coverage table showing which collections have published classifications.
  Select up to five of the 20 highest-demand tools/domain skills across the
  available classified snapshots. Qualifications are not used for trend choices.
- Chart.js 4.5.1 renders charts; exact values are also available in expandable
  HTML data tables for accessibility. Hover points/bars to see full labels/values.

Suggested cluster names are generated deterministically from existing keywords.
They are marked **Provisional**, do not update MySQL labels, and are not approved
job titles. Existing supplied names take precedence and keep their label status.
Different clusters can share a broad suggested name; the run-local cluster number
keeps them distinguishable. Noise (`-1`) is shown as **Unclustered AV roles**,
not as non-AV jobs. Each skill counts distinct jobs, not repeated mentions.

The pages fetch `GET /api/insights` from the same configured backend as Jobs.
No static/mock production data is used. The database account needs the weekly-view
SELECT grants in `database/TEAM_GUIDE.md`, section 5. No schema changes, imports,
label approvals, or release activations are performed by these pages.

To populate history, use the existing importer workflow in the database team guide:
import each chosen collection with its date, attach the matching classification,
then publish/freeze its release. Raw-only dates remain pending; missing analysis
is `null`, never zero. New points appear on page reload. A single classified date
shows an honest insufficient-history state, not large single-point trend charts. Existing local raw
files are not automatically imported by the frontend.

These are **snapshot comparisons**, not verified market-growth statistics:
partial collections, changed source coverage, cumulative exports, or changed
classification methods can affect results. The database's stricter verified-crawl
trend gate remains unchanged. Cluster IDs are not stable across runs, so this
page compares the number of populated groups, not the same numbered cluster over
time. Percentages use all active AV jobs in the corresponding snapshot.

Implementation/test note: the analytics repository, charts, pages, and related
tests were developed with AI assistance. Verify results against the frozen data
and review provisional labels before using them in a formal client report.

## 7. Product navigation and information hierarchy

- Global navigation: Home, Jobs, Insights, Saved Jobs. The analysis area alone
  has the Skill clusters / Historical trends sub-navigation. About, Help, Terms
  and GitHub live in the compact footer, without duplicate destination links.
- Home: a shorter introduction, dated active-AV counts, real clickable popular
  skills and featured companies. Static skill-category marketing and the obscure
  total skill count have been removed.
- Saved jobs have their own `/saved` page. Old `/about#favorites` links redirect
  there. Storage remains local; no account, upload or cross-device sync is added.
  Removing a saved copy affects only browser storage, not the source job/database.
- Job details show each known fact once. Missing salary/work arrangement is
  mentioned once, not displayed in repeated empty cards. Skills are grouped,
  case-deduplicated and labelled **Extracted Skills**, not employer-preferred skills.
  The generated summary is identified as automatic. Full original fields, internal
  record ID and recruitment platform are inside the data-source disclosure.
  Only HTTP/HTTPS original-posting links are accepted.
- The header/list shows the official published dataset date from `/api/job-facets`.
  This is not the job's advertised posting date. If unavailable, the UI says so
  instead of guessing a date from the newest record. Active means active in the
  snapshot; users must still verify current availability on the original site.
- Cluster directory: 18 cards initially, Show more groups, search, name/job-count
  sorting, grouping selection and three preview skills visible before expansion.
  Controls are stored in the URL and carried into example-job back links.
- Trends focus on skill demand and group count after two classified dates exist
  in the chosen range. Unclustered share, raw collection coverage and provenance
  are secondary disclosures. Missing classification is never filled with zero.

## 8. Location aliases: consistent read-only matching

`backend/app/locations.py` defines a small explicit, country-scoped alias list.
For example, Canadian ON/Ontario, Chinese Guangzhou/Guangzhou City, and Swedish
Göteborg/Goteborg/Gothenburg share display/filter options. Matching SQL expands to
the same bound aliases, so combining an option never loses the underlying jobs.
The same read projection is used by cards, details, facets and location options.

Raw `location` and `locationSourceFields` remain available. There are **no writes
to frozen snapshots, no schema migration and no reimport**. Tableau/direct SQL
does not automatically get the API's alias display values. This is not a universal
geocoder: unknown places, country ambiguity and districts are not guessed or
silently merged. Add a reviewed country/field-specific mapping and regression
tests when another genuine alias is identified.

Reference sources for reviewed aliases:
[Canada Post province abbreviations](https://www.canadapost-postescanada.ca/cpc/en/support/articles/addressing-guidelines/symbols-and-abbreviations.page)
and [Gothenburg's official visitor guide](https://www.goteborg.com/en/information/about-goteborg-com).
