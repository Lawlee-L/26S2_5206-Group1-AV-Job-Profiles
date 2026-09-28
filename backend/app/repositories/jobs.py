import json
import math
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal

from app.db import fetch_all, fetch_one


class JobRepository:
    """Read-only access to the published dashboard database contract."""

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
        remote_type=None,
        seniority=None,
    ):
        where_sql, params = self._build_filters(
            search=search,
            company=company,
            country=country,
            remote_type=remote_type,
            seniority=seniority,
        )

        count_row = fetch_one(
            f"""
            SELECT COUNT(*) AS total
            FROM v_dashboard_jobs AS j
            {where_sql}
            """,
            tuple(params),
        )
        total = int(count_row["total"] if count_row else 0)

        offset = (page - 1) * page_size
        rows = fetch_all(
            f"""
            SELECT {self.JOB_COLUMNS}
            FROM v_dashboard_jobs AS j
            {where_sql}
            ORDER BY
              COALESCE(j.date_posted, TIMESTAMP(j.last_seen_date)) DESC,
              j.job_id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [page_size, offset]),
        )

        skills_by_job = self._skills_for_job_ids([row["job_id"] for row in rows])
        items = [self._job_to_api(row, skills_by_job.get(row["job_id"], [])) for row in rows]

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
        rows = fetch_all(
            """
            SELECT
                j.company_name,
                COUNT(*) AS job_count
            FROM v_dashboard_jobs AS j
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
        rows = fetch_all(
            """
            SELECT
                skill_id,
                skill_name,
                skill_type,
                job_count,
                company_count
            FROM v_dashboard_skill_demand
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
        rows = fetch_all(
            """
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
            FROM v_dashboard_clusters
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
        row = fetch_one(
            f"""
            SELECT {self.JOB_COLUMNS}
            FROM v_dashboard_jobs AS j
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
        return self._job_to_api(row, skills)

    @staticmethod
    def _build_filters(*, search, company, country, remote_type, seniority):
        clauses = ["j.is_active = TRUE", "j.av_relevant = TRUE"]
        params = []

        if search:
            pattern = f"%{search.strip()}%"
            clauses.append(
                """
                (
                    j.advertised_job_title LIKE %s
                    OR j.generic_job_title LIKE %s
                    OR j.company_name LIKE %s
                    OR j.location_raw LIKE %s
                    OR EXISTS (
                        SELECT 1
                        FROM v_dashboard_job_skills AS s
                        WHERE s.job_id = j.job_id
                          AND s.skill_name LIKE %s
                    )
                )
                """
            )
            params.extend([pattern] * 5)

        if company:
            clauses.append("j.company_name = %s")
            params.append(company)

        if country:
            clauses.append("j.country_code = %s")
            params.append(country.upper())

        if remote_type:
            clauses.append("j.remote_type = %s")
            params.append(remote_type.lower())

        if seniority:
            clauses.append("j.seniority_code = %s")
            params.append(seniority)

        return "WHERE " + " AND ".join(clauses), params

    @staticmethod
    def _skills_for_job_ids(job_ids):
        if not job_ids:
            return {}

        placeholders = ", ".join(["%s"] * len(job_ids))
        rows = fetch_all(
            f"""
            SELECT job_id, skill_name, skill_type, confidence, skill_rank
            FROM v_dashboard_job_skills
            WHERE job_id IN ({placeholders})
            ORDER BY job_id, skill_rank IS NULL, skill_rank, skill_name
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


def _json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
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
