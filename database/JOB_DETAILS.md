# Job detail read contract

## 1. Ownership and sources

Nyx supplies the read-only database views below. Leon adds their fields to the
job-detail API; frontend developers decide how to display them. The importer
does not generate new descriptions or perform classification.

| Field | Meaning / source | Missing value |
| --- | --- | --- |
| `job_description` | Full collected description from the release's `job_observations` record, supplied by Li | `NULL` |
| `role_summary` | Summary from the release's selected `job_analyses` record, supplied by Sunjol | `NULL` |
| `responsibilities_json` | Responsibilities extracted by classification, not guaranteed to be verbatim source text | JSON array, `[]` when unavailable |
| `requirements_json` | Requirements extracted by classification, not guaranteed to be verbatim source text | JSON array, `[]` when unavailable |
| `detail_snapshot_available` | Whether this frozen snapshot contains the new detail fields | `0` for older snapshots; `1` for the new contract |

`detail_snapshot_available=1` does **not** mean the source supplied a description
or that every extracted section is non-empty. It means those fields were captured
at publication. No missing text is guessed.

## 2. Public views and version boundaries

- `v_dashboard_job_details`: AV jobs in the current published frozen release.
- `v_weekly_av_job_details`: AV details from the selected, frozen classification
  of each official collection week; includes `week_date`.

Both expose `dashboard_release_id`, `release_key`, `job_id`, `source_key`, and
the five detail fields above. Join on **both release ID and job ID**, never
job ID alone. The same job can have different text in different releases.

These views do not impose an active-only policy: use `v_dashboard_jobs.is_active`
with the same filter as the existing detail route when active-only is required.
Unclassified weeks have no AV detail rows. Consult `v_weekly_versions` to
distinguish a pending classification from an empty result.

`v_frozen_av_job_details` is an internal helper, not an application contract.
Do not grant it or the mutable core tables to the backend.

## 3. Leon: extend the detail endpoint, not the job list

Keep the existing list response and pagination unchanged. In `get_job`, after
reading the selected job, fetch its detail fields using the same release:

```sql
SELECT job_description, role_summary, responsibilities_json,
       requirements_json, detail_snapshot_available
FROM v_dashboard_job_details
WHERE dashboard_release_id = %s AND job_id = %s;
```

Bind `(job['dashboard_release_id'], job['job_id'])` as query parameters. Keep
the existing not-found response if the job is not visible. An absent detail
row must not remove an otherwise valid job; return empty detail fields instead.
If the application needs several queries to use exactly the same publication,
perform the whole detail read in one read transaction, or use one joined query.

For example, extend the existing detail SELECT with a `LEFT JOIN`:

```sql
SELECT j.source_key, j.job_id, j.dashboard_release_id, j.display_title,
       d.job_description, d.role_summary, d.responsibilities_json,
       d.requirements_json, COALESCE(d.detail_snapshot_available, 0)
         AS detail_snapshot_available
FROM v_dashboard_jobs AS j
LEFT JOIN v_dashboard_job_details AS d
  ON d.dashboard_release_id = j.dashboard_release_id AND d.job_id = j.job_id
WHERE j.source_key = %s AND j.is_active = 1;
```

Use the route's existing job columns in place of this shortened example.
`source_key` remains the external job identifier; URL-encode it in route URLs.

Suggested additional response fields:

```python
import json

def detail_array(value):
    if value is None:
        return []
    items = json.loads(value) if isinstance(value, (str, bytes, bytearray)) else value
    if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
        raise ValueError("Invalid job-detail array")
    return items

# Add these only to the detail response; keep existing response fields.
details = {
    "description": row.get("job_description"),
    "roleSummary": row.get("role_summary"),
    "responsibilities": detail_array(row.get("responsibilities_json")),
    "requirements": detail_array(row.get("requirements_json")),
    "detailSnapshotAvailable": bool(row.get("detail_snapshot_available")),
}
```

Do not silently turn invalid JSON into a successful empty array: log the data
error and use the API's error handler. Source text is data, not trusted HTML;
render as text or sanitise it before HTML rendering.

Historical detail example:

```sql
SELECT * FROM v_weekly_av_job_details
WHERE week_date = %s AND release_key = %s AND source_key = %s;
```

Select the intended release from `v_weekly_versions`. The weekly detail view
exposes only that exact selected release; superseded revisions stay stored but
are not duplicated in the query result.

## 4. Installing and publishing

For a new local database, follow `TEAM_GUIDE.md` as usual. For an existing
006 development database, install migration 007 first, then apply the updated
`views.mysql.sql` through the database operator's existing SQL runner;
**do not rerun the CREATE TABLE schema**. Follow the sequence documented in
[the revision guide](RELEASE_REVISIONS.md). It adds selection/audit fields,
not new job-description columns or changed classification output requirements.

The next newly frozen release captures detail text and arrays in each existing
`row_kind='job'` snapshot row. Both description and classification sections are
copied from that release's selected collection and analysis, then hashed with
the rest of the snapshot payload. This does not change `jobs.content_hash` or
`job_observations.content_hash`.

Old frozen releases are not rewritten. Applying the views alone makes their
detail rows readable, but they return `NULL` text, empty arrays, and
`detail_snapshot_available=0`. A new reviewed draft and publication are needed
to expose details from existing input data. Use `create-release` to reuse the
existing analysis in a new draft, QA it, then `activate-release` with the
expected old selections. This requires no model rerun or whole-database
rebuild. See [the step-by-step commands](RELEASE_REVISIONS.md). Never fill an
old snapshot by joining the latest mutable `jobs` record.

Grant the backend account only the additional public views:

```sql
GRANT SELECT ON av_job_profiles.v_dashboard_job_details
  TO 'av_backend'@'127.0.0.1';
GRANT SELECT ON av_job_profiles.v_weekly_av_job_details
  TO 'av_backend'@'127.0.0.1';
```

## 5. Acceptance checks

1. Current details contain exactly the same release/job pairs as current AV jobs.
2. Description equals that release's collection observation without truncation.
3. Responsibilities and requirements are arrays, not JSON strings inside arrays.
4. Historical details use the selected week's collection and classification.
5. Changing a mutable source row does not change an already frozen detail.
6. Older frozen snapshots remain readable with the availability flag set to zero.
7. Existing job-list, skill and cluster contracts remain unchanged.

Automated field normalisation tests: `python -m unittest discover -s database/tests -v`.
