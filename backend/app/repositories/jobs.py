import json
import math
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from app.db import fetch_all, fetch_one


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
        )

        count_row = fetch_one(
            f"""
            SELECT COUNT(*) AS total
            FROM {jobs_view} AS j
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
            FROM {jobs_view} AS j
            {join_sql}
            {where_sql}
            ORDER BY
              COALESCE(j.date_posted, TIMESTAMP(j.last_seen_date)) DESC,
              j.job_id DESC
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
    ):
        join_sql = ""

        clauses = [
            "j.is_active = TRUE",
            "j.av_relevant = TRUE",
        ]

        params = []

        query = (search or "").strip()

        if query:
            pattern = f"%{query}%"

            skills_view = self.views["job_skills"]

            join_sql = f"""
                LEFT JOIN (
                    SELECT DISTINCT
                        dashboard_release_id,
                        job_id
                    FROM {skills_view}
                    WHERE skill_name LIKE %s
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
                    j.advertised_job_title LIKE %s
                    OR j.generic_job_title LIKE %s
                    OR j.company_name LIKE %s
                    OR j.location_raw LIKE %s
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
            clauses.append(
                "j.state_region = %s"
            )
            params.append(state_region)

        if city:
            clauses.append(
                "j.city = %s"
            )
            params.append(city)

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
            "city": row["city"],
            "stateRegion": row["state_region"],
            "countryCode": row["country_code"],
            "remoteType": row["remote_type"],
            "salary": row["salary_raw"],
            "salaryMin": _json_value(row["salary_min"]),
            "salaryMax": _json_value(row["salary_max"]),
            "salaryCurrency": row["salary_currency"],
            "salaryPeriod": row["salary_period"],
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
            "locations": [
                {
                    "countryCode": row["country_code"],
                    "stateRegion": row["state_region"],
                    "city": row["city"],
                    "jobCount": int(row["job_count"]),
                }
                for row in location_rows
            ],
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
