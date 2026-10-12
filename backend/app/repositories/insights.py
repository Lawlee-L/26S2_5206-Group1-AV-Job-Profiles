"""Read-only, version-aware analytics. Never writes provisional labels to MySQL."""
import json
import re
from collections import Counter, defaultdict

from app.db import database_connection


LABEL_RULES = [
    ("Android & in-vehicle software", ["android", "androidautomotive"]),
    ("Commercial vehicle operations", ["box", "trucks", "boxtrucks", "truck"]),
    ("Networking & communications", ["network", "networking", "congestion", "congestioncontrol"]),
    ("Customer solutions & vehicle software", ["customer", "vehicleos", "engagements"]),
    ("Autonomy tools & platforms", ["autonomydevelopment", "featurestools", "productsfeatures"]),
    ("Autonomy testing & field support", ["manualautonomous", "feedbackengineers", "troubleshootoperations"]),
    ("Chip design & verification", ["rtl", "uvm", "systemverilog", "soc", "asic", "chip"]),
    ("Machine learning inference & performance", ["quantization", "inference", "tensorrt", "cuda", "compiler"]),
    ("Motion planning & control", ["planning", "trajectory", "control", "dynamics", "motion"]),
    ("Perception & computer vision", ["perception", "detection", "vision", "segmentation", "fusion"]),
    ("Functional safety & assurance", ["safety", "iso", "hazard", "asil", "safetycase"]),
    ("Vehicle & platform security", ["cybersecurity", "security", "cryptography", "secureboot", "vulnerability"]),
    ("Sensors & signal processing", ["lidar", "radar", "sensor", "sensors", "signalprocessing", "sensing"]),
    ("Electronics & hardware design", ["pcb", "circuit", "analog", "schematic", "signalintegrity", "electronics"]),
    ("Manufacturing & industrial automation", ["manufacturing", "cnc", "machining", "hydraulic", "plc", "assembly"]),
    ("Fleet & vehicle operations", ["fleet", "operations", "driver", "driving", "dispatch", "shift"]),
    ("Machine learning training & infrastructure", ["training", "distributed", "ml", "machinelearning", "gpu", "deep"]),
    ("Simulation & validation", ["simulation", "simulator", "validation", "verification", "testing", "test"]),
    ("Mapping & localisation", ["mapping", "localization", "localisation", "slam", "geospatial"]),
    ("Embedded systems & robotics", ["embedded", "firmware", "rtos", "robotics", "ros", "can"]),
    ("Data engineering & analytics", ["data", "etl", "sql", "analytics", "warehouse", "database"]),
    ("Cloud & developer infrastructure", ["cloud", "kubernetes", "infrastructure", "devops", "deployment", "ci"]),
    ("Application & platform development", ["frontend", "backend", "web", "api", "application", "javascript"]),
    ("Product & programme management", ["product", "program", "programme", "management", "roadmap"]),
]


def _terms(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return []
    if not isinstance(value, list):
        return []
    return [str(item.get("term", item.get("name", "")) if isinstance(item, dict) else item)
            for item in value if item]


def cluster_label(row):
    """Approved names win; rule-based names are explicitly only display suggestions."""
    if row.get("is_noise") or row.get("cluster_number") == -1:
        return "Unclustered AV roles", "unclustered"
    if row.get("cluster_name"):
        return row["cluster_name"], row.get("label_status") or "provided"
    terms = _terms(row.get("top_terms_json"))
    tokens = [re.sub(r"[^a-z0-9]", "", term.lower()) for term in terms]
    # Distinctive combinations beat generic words such as 'control' or 'planning'.
    specific = [
        ({"reinforcementlearning", "planning"}, "Learning-based planning & decision making"),
        ({"prediction", "models"}, "Trajectory prediction & learned models"),
        ({"behavior", "planning"}, "Behaviour planning"),
        ({"simulation", "vehicledynamics"}, "Vehicle dynamics simulation"),
        ({"electricdrives", "control"}, "Electric drive control"),
    ]
    for required, name in specific:
        if required.issubset(set(tokens)):
            return name, "provisional"
    scored = [(sum((len(tokens) - i) for i, term in enumerate(tokens) if term in keys), -index, name)
              for index, (name, keys) in enumerate(LABEL_RULES)]
    score, _, name = max(scored)
    if not score:
        useful = [term for term in terms if term.lower() not in {"software", "experience", "work", "skills"}]
        name = " / ".join(term[:1].upper() + term[1:] for term in useful[:2]) or "Specialist skill group"
    return name, "provisional"


def _rank_skills(job_skills, job_ids):
    """Count each skill at most once per job, even across aliases/types."""
    by_name = {}
    for row in job_skills:
        if row["job_id"] not in job_ids or not row.get("skill_name"):
            continue
        name = row["skill_name"].strip()
        key = name.casefold()
        item = by_name.setdefault(key, {"name": name, "types": set(), "jobs": set()})
        item["jobs"].add(row["job_id"])
        item["types"].add(row.get("skill_type") or "unknown")
    result = [{"name": item["name"], "types": sorted(item["types"]), "jobCount": len(item["jobs"]),
               "share": round(100 * len(item["jobs"]) / len(job_ids), 2) if job_ids else 0}
              for item in by_name.values()]
    return sorted(result, key=lambda item: (-item["jobCount"], item["name"].casefold()))


def build_insights(jobs, skills, clusters, versions, collections, weekly_jobs, weekly_skills):
    """Pure aggregation, independent of Flask/MySQL for tests and future adapters."""
    active = {row["job_id"]: row for row in jobs if row.get("is_active") and row.get("av_relevant")}
    grouped = defaultdict(set)
    for job_id, row in active.items():
        grouped[row.get("cluster_number")].add(job_id)
    current_clusters = []
    metadata = {row["cluster_number"]: row for row in clusters}
    for number in grouped:
        if number not in metadata:
            metadata[number] = dict(cluster_number=number, is_noise=number in (None, -1), top_terms_json=[])
    for row in metadata.values():
        members = grouped.get(row["cluster_number"], set())
        if not members:
            continue
        name, status = cluster_label(row)
        sample = sorted((active[key] for key in members), key=lambda job: (job.get("advertised_job_title") or "", str(job["job_id"])))[:3]
        current_clusters.append({
            "number": row["cluster_number"], "name": name, "nameStatus": status,
            "isNoise": bool(row.get("is_noise") or row["cluster_number"] == -1),
            "jobCount": len(members), "share": round(100 * len(members) / len(active), 2),
            "topTerms": _terms(row.get("top_terms_json"))[:8],
            "topSkills": _rank_skills(skills, members)[:8],
            "companies": [{"name": company, "jobCount": count} for company, count in
                          Counter(active[key]["company_name"] for key in members).most_common(3)],
            "examples": [{"title": job["advertised_job_title"], "sourceKey": job["source_key"],
                          "company": job["company_name"]} for job in sample],
        })
    current_clusters.sort(key=lambda item: (item["isNoise"], -item["jobCount"], item["number"] if item["number"] is not None else -2))
    skill_ranking = _rank_skills(skills, set(active))
    covered = {row["job_id"] for row in skills if row.get("skill_name") and row["job_id"] in active}
    collection_by_week = {str(row["week_date"]): row for row in collections}
    av_by_week, skills_by_week = defaultdict(list), defaultdict(list)
    for row in weekly_jobs:
        if row.get("is_active"):
            av_by_week[str(row["week_date"])].append(row)
    for row in weekly_skills:
        skills_by_week[str(row["week_date"])].append(row)
    points, rankings, skill_candidates = [], {}, {}
    for version in sorted(versions, key=lambda row: str(row["week_date"])):
        week = str(version["week_date"])
        raw = collection_by_week.get(week, {})
        ready = version.get("classification_status") == "ready"
        av_jobs = {row["job_id"]: row for row in av_by_week[week]} if ready else {}
        ranked = _rank_skills(skills_by_week[week], set(av_jobs)) if ready else []
        rankings[week] = {item["name"].casefold(): item for item in ranked}
        for item in ranked:
            if not set(item["types"]).issubset({"qualification"}):
                key = item["name"].casefold()
                old = skill_candidates.get(key)
                if old is None or item["jobCount"] > old["jobCount"]:
                    skill_candidates[key] = item
        noise_count = sum(bool(row.get("is_noise") or row.get("cluster_number") in (None, -1)) for row in av_jobs.values())
        points.append({
            "date": week, "classificationStatus": version.get("classification_status"),
            "collectionRunKey": version.get("collection_run_key"), "analysisRunKey": version.get("analysis_run_key"),
            "releaseKey": version.get("release_key"), "collectionStatus": version.get("collection_run_status"),
            "runKind": version.get("run_kind"), "timeQuality": version.get("time_quality"),
            "sourceReportAvailable": bool(version.get("source_report_available")),
            "totalJobs": int(raw.get("total_jobs", 0)), "activeJobs": int(raw.get("active_jobs", 0)),
            "companyCount": int(raw.get("company_count", 0)), "sourceCount": int(raw.get("source_count", 0)),
            "avJobs": len(av_jobs) if ready else None,
            "clusterCount": len({row["cluster_number"] for row in av_jobs.values()
                                 if not row.get("is_noise") and row.get("cluster_number") not in (None, -1)}) if ready else None,
            "unclusteredJobs": noise_count if ready else None,
            "unclusteredShare": round(100 * noise_count / len(av_jobs), 2) if av_jobs else (0 if ready else None),
        })
    selected = sorted(skill_candidates.values(), key=lambda row: (-row["jobCount"], row["name"].casefold()))[:20]
    series = [{"name": item["name"], "values": [
        {"date": point["date"], "jobCount": rankings[point["date"]].get(item["name"].casefold(), {}).get("jobCount", 0)
         if point["avJobs"] is not None else None,
         "share": rankings[point["date"]].get(item["name"].casefold(), {}).get("share", 0)
         if point["avJobs"] is not None else None} for point in points]} for item in selected]
    published = jobs[0] if jobs else {}
    return {"current": {
        "releaseKey": published.get("release_key"),
        "snapshotDate": next((point["date"] for point in points if point["releaseKey"] == published.get("release_key")), None),
        "jobCount": len(active),
        "companyCount": len({row["company_name"] for row in active.values()}),
        "clusterCount": sum(not row["isNoise"] for row in current_clusters),
        "unclusteredJobs": len(grouped.get(-1, set()) | grouped.get(None, set())),
        "jobsWithoutSkills": len(active) - len(covered),
        "clusters": current_clusters, "skills": skill_ranking[:100],
    }, "history": {"points": points, "skillSeries": series,
                   "classifiedVersionCount": sum(point["avJobs"] is not None for point in points),
                   "comparisonKind": "dated_snapshot_comparison"},
        "method": {"population": "Active AV-related jobs; one count per job, not one count per skill mention.",
                   "namingVersion": "display-rules-v2", "labels": "Suggested display names only; not approved labels or standard job titles.",
                   "history": "Dated snapshots, not verified market growth. Missing classification is unknown, not zero. Cluster numbers are local to each analysis run."}}


class InsightsRepository:
    def get_insights(self):
        # One consistent read transaction prevents mixing releases during activation.
        queries = [
            "SELECT dashboard_release_id, release_key, job_id, source_key, advertised_job_title, company_name, is_active, av_relevant, cluster_number, is_noise FROM v_dashboard_jobs",
            "SELECT job_id, skill_name, skill_type FROM v_dashboard_job_skills",
            "SELECT cluster_number, cluster_name, label_status, is_noise, top_terms_json FROM v_dashboard_clusters WHERE population='av_relevant'",
            "SELECT * FROM v_weekly_versions ORDER BY week_date",
            "SELECT week_date, COUNT(DISTINCT job_id) total_jobs, COUNT(DISTINCT CASE WHEN is_active THEN job_id END) active_jobs, COUNT(DISTINCT company_name) company_count, COUNT(DISTINCT source_id) source_count FROM v_weekly_jobs GROUP BY week_date",
            "SELECT week_date, job_id, is_active, cluster_number, is_noise FROM v_weekly_av_jobs",
            "SELECT week_date, job_id, skill_name, skill_type FROM v_weekly_av_job_skills",
        ]
        with database_connection() as connection:
            connection.start_transaction(isolation_level="REPEATABLE READ", consistent_snapshot=True, readonly=True)
            cursor = connection.cursor(dictionary=True)
            try:
                datasets = []
                for sql in queries:
                    cursor.execute(sql)
                    datasets.append(cursor.fetchall())
                return build_insights(*datasets)
            finally:
                cursor.close()
                connection.rollback()
