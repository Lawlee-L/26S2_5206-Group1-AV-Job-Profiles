import json
import math
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from threading import Lock
from time import monotonic
from flask import current_app

from app.db import fetch_all, fetch_one
from app.display import display_text
from app.salary import salary_from_row, matches_salary
from app.facets import FacetIndex
from app.locations import project_location, location_predicate, aggregate_locations, VERSION as LOCATION_ALIAS_VERSION


VIEWS = {
    "jobs": "v_dashboard_jobs",
    "job_skills": "v_dashboard_job_skills",
    "skills": "v_dashboard_skill_demand",
    "clusters": "v_dashboard_clusters",
    "job_details": "v_dashboard_job_details",
}


class JobRepository:
    def __init__(self):
        self.views = VIEWS
        self._facet_lock = Lock()
        self._facet_cache = None



    JOB_COLUMNS = """
        j.dashboard_release_id,
        j.release_key,
        j.job_id,
        j.source_key,
        j.company_name,
        j.platform,
        j.source_region,
        j.advertised_job_title,
        j.generic_job_title,
        j.job_url,
        j.location_raw,
        j.city,
        j.state_region,
        j.country_code,
        j.remote_type,
        j.salary_raw,
        j.salary_min,
        j.salary_max,
        j.salary_currency,
        j.salary_period,
        j.date_posted,
        j.first_seen_date,
        j.last_seen_date,
        j.is_active,
        j.is_new_in_latest_run,
        j.av_relevant,
        j.analysis_result_origin,
        j.relevance_confidence,
        j.relevance_confidence_label,
        j.seniority_code,
        j.experience_min_years,
        j.experience_max_years,
        j.cluster_number,
        j.cluster_name,
        j.job_family,
        j.specialisation,
        j.cluster_lean,
        j.is_noise
    """

    def list_jobs(
        self,
        *,
        page=1,
        page_size=20,
        search=None,
        company=None,
        country=None,
        state_region=None,
        city=None,
        remote_type=None,
        seniority=None,
        skill=None,
        posted_after=None,
        has_salary=None,
        salary_currency=None,
        salary_period=None,
        salary_min=None,
        salary_max=None,
        sort="newest",
    ):

        jobs_view = self.views["jobs"]

        join_sql, where_sql, params = self._build_filters(
            search=search,
            company=company,
            country=country,
            state_region=state_region,
            city=city,
            remote_type=remote_type,
            seniority=seniority,
            skill=skill,
            posted_after=posted_after,
            has_salary=has_salary,
            salary_currency=salary_currency, salary_period=salary_period,
            salary_min=salary_min, salary_max=salary_max,
        )

        # Only fixed, server-owned SQL expressions may be used for ordering.
        order_sql = {
            "newest": "COALESCE(j.date_posted, TIMESTAMP(j.last_seen_date)) DESC, j.job_id DESC",
            "oldest": "COALESCE(j.date_posted, TIMESTAMP(j.last_seen_date)) ASC, j.job_id ASC",
            "title": "j.advertised_job_title ASC, j.job_id ASC",
            "company": "j.company_name ASC, j.advertised_job_title ASC, j.job_id ASC",
        }[sort]

        # The published views unpack frozen JSON. Prevent MySQL from merging
        # the jobs view into a skills-driven plan and unpacking it once per
        # matching skill row. LIMIT is a non-merging boundary, not a row cap.
        jobs_source = (
            f"(SELECT * FROM {jobs_view} LIMIT 18446744073709551615)"
            if join_sql else jobs_view
        )

        count_row = fetch_one(
            f"""
            SELECT COUNT(*) AS total
            FROM {jobs_source} AS j
            {join_sql}
            {where_sql}
            """,
            tuple(params),
        )
        total = int(count_row["total"] if count_row else 0)

        offset = (page - 1) * page_size
        rows = fetch_all(
            f"""
            SELECT {self.JOB_COLUMNS}
            FROM {jobs_source} AS j
            {join_sql}
            {where_sql}
            ORDER BY {order_sql}
            LIMIT %s OFFSET %s
            """,
            tuple(params + [page_size, offset]),
        )

        skills_by_job = self._skills_for_job_ids([row["job_id"] for row in rows])
        items = [
            self._job_to_api(row, skills_by_job.get(row["job_id"], []))
            for row in rows
        ]

        return {
            "items": items,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": math.ceil(total / page_size) if total else 0,
            },
        }

    def list_companies(self):
        jobs_view = self.views["jobs"]

        rows = fetch_all(
            f"""
            SELECT
                j.company_name,
                COUNT(*) AS job_count
            FROM {jobs_view} AS j
            WHERE j.is_active = TRUE
              AND j.av_relevant = TRUE
              AND j.company_name IS NOT NULL
              AND TRIM(j.company_name) <> ''
            GROUP BY j.company_name
            ORDER BY job_count DESC, j.company_name ASC
            """
        )

        return [
            {
                "name": row["company_name"],
                "jobCount": int(row["job_count"]),
            }
            for row in rows
        ]

    def list_skills(self):
        skills_view = self.views["skills"]
        rows = fetch_all(
            f"""
            SELECT
                skill_id,
                skill_name,
                skill_type,
                job_count,
                company_count
            FROM {skills_view}
            ORDER BY job_count DESC, skill_name ASC
            """
        )
        return [
            {
                "id": row["skill_id"],
                "name": row["skill_name"],
                "type": row["skill_type"],
                "jobCount": int(row["job_count"]),
                "companyCount": int(row["company_count"]),
            }
            for row in rows
        ]

    def list_clusters(self):
        clusters_view = self.views["clusters"]

        rows = fetch_all(
            f"""
            SELECT
                cluster_pk,
                cluster_number,
                cluster_name,
                job_family,
                specialisation,
                label_source,
                label_status,
                label_revision_number,
                label_rationale,
                lean,
                is_noise,
                size_cached,
                technical_score,
                top_terms_json,
                example_titles_json,
                top_companies_json,
                notes
            FROM {clusters_view}
            ORDER BY
                is_noise ASC,
                size_cached DESC,
                cluster_number ASC
            """
        )

        return [
            {
                "id": row["cluster_pk"],
                "number": row["cluster_number"],
                "name": row["cluster_name"],
                "jobFamily": row["job_family"],
                "specialisation": row["specialisation"],
                "labelSource": row["label_source"],
                "labelStatus": row["label_status"],
                "labelRevisionNumber": row["label_revision_number"],
                "labelRationale": row["label_rationale"],
                "lean": row["lean"],
                "isNoise": (
                    bool(row["is_noise"])
                    if row["is_noise"] is not None
                    else None
                ),
                "jobCount": (
                    int(row["size_cached"])
                    if row["size_cached"] is not None
                    else 0
                ),
                "technicalScore": _json_value(row["technical_score"]),
                "topTerms": _json_data(row["top_terms_json"]),
                "exampleTitles": _json_data(row["example_titles_json"]),
                "topCompanies": _json_data(row["top_companies_json"]),
                "notes": row["notes"],
            }
            for row in rows
        ]


    def get_job(self, source_key):
        jobs_view = self.views["jobs"]

        row = fetch_one(
            f"""
            SELECT {self.JOB_COLUMNS}
            FROM {jobs_view} AS j
            WHERE j.source_key = %s
              AND j.is_active = TRUE
              AND j.av_relevant = TRUE
            LIMIT 1
            """,
            (source_key,),
        )

        if row is None:
            return None

        skills = self._skills_for_job_ids([row["job_id"]]).get(row["job_id"], [])
        result = self._job_to_api(row, skills)

        details_view = self.views["job_details"]

        if details_view is None:
            result.update(
                {
                    "description": None,
                    "roleSummary": None,
                    "responsibilities": [],
                    "requirements": [],
                    "detailSnapshotAvailable": False,
                }
            )
            return result

        details = fetch_one(

            f"""
            SELECT
                job_description,
                role_summary,
                responsibilities_json,
                requirements_json,
                detail_snapshot_available
            FROM {details_view}
            WHERE dashboard_release_id = %s
                AND job_id = %s
            """,
            (
                row["dashboard_release_id"],
                row["job_id"], 
            ),

        )

        if details is None:
            result.update(
                {
                    "description": None,
                    "roleSummary": None,
                    "responsibilities": [],
                    "requirements": [],
                    "detailSnapshotAvailable": False,
                }
            )
            return result

        result.update(
            {
                "description": details["job_description"],
                "descriptionDisplay": display_text(details["job_description"]),
                "roleSummary": details["role_summary"],
                "responsibilities": _detail_array(
                    details["responsibilities_json"]
                ),
                "requirements": _detail_array(
                    details["requirements_json"]
                ),
                "detailSnapshotAvailable": bool(
                    details["detail_snapshot_available"]
                ),
            }
        )

        return result



    def _build_filters(
        self,
        *,
        search,
        company,
        country,
        state_region,
        city,
        remote_type,
        seniority,
        skill=None,
        posted_after=None,
        has_salary=None,
        salary_currency=None,
        salary_period=None,
        salary_min=None,
        salary_max=None,
    ):
        join_sql = ""

        clauses = [
            "j.is_active = TRUE",
            "j.av_relevant = TRUE",
        ]

        params = []

        query = (search or "").strip()

        if query:
            # Search text is literal, including C_ and %; facets use the same rule.
            pattern = "%" + query.replace("=", "==").replace("%", "=%").replace("_", "=_") + "%"

            skills_view = self.views["job_skills"]

            join_sql = f"""
                LEFT JOIN (
                    SELECT DISTINCT
                        dashboard_release_id,
                        job_id
                    FROM {skills_view}
                    WHERE skill_name LIKE %s ESCAPE '='
                ) AS skill_matches
                ON skill_matches.dashboard_release_id =
                        j.dashboard_release_id
                AND skill_matches.job_id = j.job_id
            """

            # JOIN parameter appears first in the SQL.
            params.append(pattern)

            clauses.append(
                """
                (
                    j.advertised_job_title LIKE %s ESCAPE '='
                    OR j.generic_job_title LIKE %s ESCAPE '='
                    OR j.company_name LIKE %s ESCAPE '='
                    OR j.location_raw LIKE %s ESCAPE '='
                    OR skill_matches.job_id IS NOT NULL
                )
                """
            )

            params.extend([pattern] * 4)

        if company:
            clauses.append(
                "j.company_name = %s"
            )
            params.append(company)

        if country:
            clauses.append(
                "j.country_code = %s"
            )
            params.append(country.upper())

        if state_region:
            condition, variants = location_predicate(country, "state_region", state_region)
            clauses.append(condition)
            params.extend(variants)

        if city:
            condition, variants = location_predicate(country, "city", city)
            clauses.append(condition)
            params.extend(variants)

        if remote_type:
            clauses.append(
                "j.remote_type = %s"
            )
            params.append(remote_type.lower())

        if seniority:
            clauses.append(
                "j.seniority_code = %s"
            )
            params.append(seniority)

        if skill:
            # Exact skill selection is separate from the general text search.
            # Materialise matching release/job pairs once, rather than repeatedly
            # evaluating the frozen skills view for every candidate job.
            join_sql += f"""
                INNER JOIN (
                    SELECT DISTINCT dashboard_release_id, job_id
                    FROM {self.views['job_skills']}
                    WHERE skill_name = %s
                ) AS selected_skill
                ON selected_skill.dashboard_release_id = j.dashboard_release_id
                AND selected_skill.job_id = j.job_id
            """
            params.insert(1 if query else 0, skill)

        if posted_after:
            # This filter means advertised date, not collection/import date.
            clauses.append("j.date_posted >= %s")
            params.append(posted_after)

        if has_salary is not None:
            salary_known = "(NULLIF(TRIM(j.salary_raw), '') IS NOT NULL OR j.salary_min IS NOT NULL OR j.salary_max IS NOT NULL)"
            clauses.append(salary_known if has_salary else f"NOT {salary_known}")

        if any(value is not None for value in (salary_currency, salary_period, salary_min, salary_max)):
            pairs = [[row["dashboard_release_id"], row["job_id"]] for row in self._salary_rows()
                     if matches_salary(salary_from_row(row), currency=salary_currency,
                                       period=salary_period, minimum=salary_min, maximum=salary_max)]
            # Parse before pagination, then join bound release/job pairs. Filtering
            # only a page would produce wrong totals and miss matching later jobs.
            join_sql += """
                INNER JOIN JSON_TABLE(%s, '$[*]' COLUMNS(
                    release_id BIGINT PATH '$[0]', job_id BIGINT PATH '$[1]'
                )) AS salary_matches
                ON salary_matches.release_id = j.dashboard_release_id
                AND salary_matches.job_id = j.job_id
            """
            params.insert(int(bool(query)) + int(bool(skill)), json.dumps(pairs))

        where_sql = (
            "WHERE "
            + " AND ".join(clauses)
        )

        return (
            join_sql,
            where_sql,
            params,
        )

    def _skills_for_job_ids(self, job_ids):
        if not job_ids:
            return {}

        skills_view = self.views["job_skills"]

        placeholders = ", ".join(["%s"] * len(job_ids))
        rows = fetch_all(
            f"""
            SELECT 
                job_id, 
                skill_name, 
                skill_type, 
                confidence, 
                skill_rank
            FROM {skills_view}
            WHERE job_id IN ({placeholders})
            ORDER BY 
                job_id, 
                skill_rank IS NULL, 
                skill_rank, 
                skill_name
            """,
            tuple(job_ids),
        )

        result = defaultdict(list)

        for row in rows:
            result[row["job_id"]].append(
                {
                    "name": row["skill_name"],
                    "type": row["skill_type"],
                    "confidence": _json_value(row["confidence"]),
                    "rank": row["skill_rank"],
                }
            )
        return result

    @staticmethod
    def _job_to_api(row, skills):
        original = row
        row = project_location(row)
        salary = salary_from_row(row)
        return {
            "id": row["source_key"],
            "jobId": row["job_id"],
            "sourceKey": row["source_key"],
            "company": row["company_name"],
            "platform": row["platform"],
            "title": row["advertised_job_title"],
            "genericTitle": row["generic_job_title"],
            "jobUrl": row["job_url"],
            "location": row["location_raw"],
            "locationDisplay": display_text(row["location_raw"]),
            "city": row["city"],
            "stateRegion": row["state_region"],
            "locationSourceFields": {"city": original["city"], "stateRegion": original["state_region"], "countryCode": original["country_code"]},
            "locationAliasVersion": LOCATION_ALIAS_VERSION,
            "countryCode": row["country_code"],
            "remoteType": row["remote_type"],
            "salary": row["salary_raw"],
            "salaryDisplay": display_text(row["salary_raw"]),
            "salaryMin": salary.minimum,
            "salaryMax": salary.maximum,
            "salaryCurrency": salary.currency,
            "salaryPeriod": salary.period,
            "salaryNormalization": salary.to_api(),
            "postedDate": _json_value(row["date_posted"]),
            "firstSeenDate": _json_value(row["first_seen_date"]),
            "lastSeenDate": _json_value(row["last_seen_date"]),
            "isActive": bool(row["is_active"]),
            "isNew": bool(row["is_new_in_latest_run"]),
            "level": row["seniority_code"],
            "experienceMinYears": _json_value(row["experience_min_years"]),
            "experienceMaxYears": _json_value(row["experience_max_years"]),
            "relevanceConfidence": _json_value(row["relevance_confidence"]),
            "relevanceConfidenceLabel": row["relevance_confidence_label"],
            "cluster": {
                "number": row["cluster_number"],
                "name": row["cluster_name"],
                "jobFamily": row["job_family"],
                "specialisation": row["specialisation"],
                "lean": row["cluster_lean"],
                "isNoise": bool(row["is_noise"]) if row["is_noise"] is not None else None,
            },
            "skills": skills,
        }

    def _salary_rows(self):
        return fetch_all(f"""
            SELECT dashboard_release_id, job_id, salary_raw,
                   salary_min, salary_max, salary_currency, salary_period
            FROM {self.views['jobs']}
            WHERE is_active = TRUE AND av_relevant = TRUE
              AND (salary_raw IS NOT NULL OR salary_min IS NOT NULL OR salary_max IS NOT NULL)
        """)

    def list_salary_options(self):
        counts = defaultdict(int)
        numeric = comparable = 0
        for row in self._salary_rows():
            salary = salary_from_row(row)
            if salary.minimum is not None or salary.maximum is not None:
                numeric += 1
                if salary.currency and salary.period:
                    comparable += 1
                    counts[(salary.currency, salary.period)] += 1
        return {"options": [{"currency": c, "period": p, "jobCount": n}
                            for (c, p), n in sorted(counts.items())],
                "numericJobCount": numeric, "comparableJobCount": comparable}

    def list_facets(self, **filters):
        # Poll the release identity before using a short-lived in-process cache.
        # Never reuse an index across databases, view modes or activated releases.
        def identity():
            rows = fetch_all(f"""SELECT DISTINCT dashboard_release_id, release_key,
                (SELECT w.week_date FROM v_weekly_versions w WHERE w.dashboard_release_id=j.dashboard_release_id LIMIT 1) AS snapshot_date
                FROM (SELECT DISTINCT dashboard_release_id, release_key FROM {self.views['jobs']}) j""")
            return tuple(sorted((row["dashboard_release_id"], row["release_key"], str(row["snapshot_date"]) if row.get("snapshot_date") else None) for row in rows))
        releases = identity()
        key = (current_app.config["DB_HOST"], current_app.config["DB_PORT"], current_app.config["DB_NAME"],
               self.views["jobs"], self.views["job_skills"], releases)
        with self._facet_lock:
            cached = self._facet_cache
            if cached and cached[0] == key and monotonic() - cached[1] < 15:
                index = cached[2]
            else:
                rows = fetch_all(f"SELECT {self.JOB_COLUMNS} FROM {self.views['jobs']} AS j WHERE j.is_active=TRUE AND j.av_relevant=TRUE")
                skills = fetch_all(f"SELECT dashboard_release_id, job_id, skill_name, skill_type FROM {self.views['job_skills']}")
                if identity() != releases:
                    raise RuntimeError("Published release changed while loading filter options; retry the request")
                index = FacetIndex(rows, skills)
                self._facet_cache = (key, monotonic(), index)
        return {**index.options(filters), "releaseIds": [item[0] for item in releases],
                "snapshotDate": releases[0][2] if len(releases) == 1 else None,
                "releaseKey": releases[0][1] if len(releases) == 1 else None}

    def list_locations(self):
        jobs_view = self.views["jobs"]

        release_rows = fetch_all(
            f"""
            SELECT DISTINCT
                dashboard_release_id,
                release_key
            FROM {jobs_view}
            WHERE is_active = TRUE
              AND av_relevant = TRUE
            ORDER BY dashboard_release_id
            LIMIT 2
            """
        )

        if not release_rows:
            return {
                "releaseId": None,
                "releaseKey": None,
                "locations": [],
                "workArrangements": [],
            }

        if len(release_rows) != 1:
            raise RuntimeError(
                "Location options span multiple dashboard releases"
            )

        release_id = release_rows[0]["dashboard_release_id"]
        release_key = release_rows[0]["release_key"]

        location_rows = fetch_all(
            f"""
            SELECT
                country_code,
                state_region,
                city,
                COUNT(*) AS job_count
            FROM {jobs_view}
            WHERE dashboard_release_id = %s
              AND is_active = TRUE
              AND av_relevant = TRUE
              AND country_code IS NOT NULL
            GROUP BY
                country_code,
                state_region,
                city
            ORDER BY
                country_code,
                state_region,
                city
            """,
            (release_id,),
        )

        work_mode_rows = fetch_all(
            f"""
            SELECT
                remote_type,
                COUNT(*) AS job_count
            FROM {jobs_view}
            WHERE dashboard_release_id = %s
              AND is_active = TRUE
              AND av_relevant = TRUE
              AND remote_type IS NOT NULL
            GROUP BY remote_type
            ORDER BY remote_type
            """,
            (release_id,),
        )

        return {
            "releaseId": release_id,
            "releaseKey": release_key,
            "locations": aggregate_locations(location_rows),
            "workArrangements": [
                {
                    "value": row["remote_type"],
                    "jobCount": int(row["job_count"]),
                }
                for row in work_mode_rows
            ],
        }


def _json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value

def _detail_array(value):
    if value is None:
        return []

    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")

    if isinstance(value, str):
        value = json.loads(value)

    if not isinstance(value, list):
        raise ValueError("Invalid job-detail array")

    if any(not isinstance(item, str) for item in value):
        raise ValueError("Invalid job-detail array")

    return value

def _json_data(value):
    if value is None:
        return []

    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []

    return value
