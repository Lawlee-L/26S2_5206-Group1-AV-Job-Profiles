"""Read-only QA metrics for one dashboard release.

Public dashboard filtering is implemented in ``views.mysql.sql``. This module
reports the underlying release population and checks that the public views
match it before a release is approved.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from .errors import ImportErrorSafe


def _relevance(value: Any) -> bool | None:
    """Normalise BOOLEAN values returned as bool, integer, or text by drivers."""
    if value is True or value == 1 or value == "1":
        return True
    if value is False or value == 0 or value == "0":
        return False
    return None


def summarize_outcomes(
    source_rows: list[dict[str, Any]],
    analysis_rows: list[dict[str, Any]],
    duplicate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate partition counts and check duplicate links for one snapshot."""
    source_by_id = {int(row["job_id"]): row for row in source_rows}
    source_ids = set(source_by_id)
    analyses_by_id: dict[int, dict[str, Any]] = {}
    analysis_ids_outside_snapshot: set[int] = set()
    for row in analysis_rows:
        job_id = int(row["job_id"])
        if job_id in source_ids:
            analyses_by_id[job_id] = row
        else:
            analysis_ids_outside_snapshot.add(job_id)

    duplicate_to_kept: dict[int, int] = {}
    duplicate_companies: dict[int, tuple[Any, Any]] = {}
    duplicate_links_outside_snapshot = 0
    for row in duplicate_rows:
        duplicate_id = int(row["duplicate_job_id"])
        kept_id = int(row["kept_job_id"])
        if duplicate_id not in source_ids:
            duplicate_links_outside_snapshot += 1
            continue
        duplicate_to_kept[duplicate_id] = kept_id
        duplicate_companies[duplicate_id] = (
            row.get("duplicate_company_id"), row.get("kept_company_id"),
        )

    duplicate_ids = set(duplicate_to_kept)
    analysis_ids = set(analyses_by_id)
    overlap_ids = analysis_ids & duplicate_ids
    unaccounted_ids = source_ids - analysis_ids - duplicate_ids

    success_rows = {
        job_id: row for job_id, row in analyses_by_id.items()
        if row.get("analysis_status") == "success" and job_id not in duplicate_ids
    }
    non_success = {
        job_id: row for job_id, row in analyses_by_id.items()
        if row.get("analysis_status") != "success" and job_id not in duplicate_ids
    }
    av_count = sum(_relevance(row.get("av_relevant")) is True for row in success_rows.values())
    non_av_count = sum(_relevance(row.get("av_relevant")) is False for row in success_rows.values())
    unknown_count = sum(_relevance(row.get("av_relevant")) is None for row in success_rows.values())

    source_company_by_id = {job_id: row.get("company_id") for job_id, row in source_by_id.items()}
    company_mismatches = sum(
        duplicate_companies.get(job_id, (None, None))[0]
        != duplicate_companies.get(job_id, (None, None))[1]
        for job_id in duplicate_ids
    )

    cycles: set[int] = set()
    broken_targets: set[int] = set()
    unresolved_terminals: set[int] = set()
    resolved: dict[int, int | None] = {}
    for duplicate_id in duplicate_ids:
        if duplicate_id in resolved:
            continue
        trail: list[int] = []
        visited: set[int] = set()
        current = duplicate_id
        terminal: int | None = None
        while current in duplicate_to_kept:
            if current in visited:
                cycles.update(visited)
                break
            if current in resolved:
                terminal = resolved[current]
                break
            visited.add(current)
            trail.append(current)
            current = duplicate_to_kept[current]
            if current not in source_ids:
                broken_targets.add(duplicate_id)
                break
        else:
            terminal = current

        if terminal is not None:
            if terminal not in analyses_by_id or analyses_by_id[terminal].get("analysis_status") != "success":
                unresolved_terminals.add(duplicate_id)
        for item in trail:
            resolved[item] = terminal

    source_count = len(source_ids)
    analysis_count = len(analysis_ids)
    partition_sum = len(duplicate_ids) + analysis_count + len(unaccounted_ids)
    checks = {
        "source_snapshot_not_empty": source_count > 0,
        "source_partition_balanced": partition_sum == source_count and not overlap_ids,
        "classification_partition_balanced": len(success_rows) == av_count + non_av_count + unknown_count,
        "no_duplicate_analysis_overlap": not overlap_ids,
        "no_unaccounted_source_jobs": not unaccounted_ids,
        "duplicate_targets_in_snapshot": not broken_targets,
        "duplicate_chains_acyclic": not cycles,
        "duplicate_targets_same_company": company_mismatches == 0,
        "duplicate_chains_end_at_successful_analysis": not unresolved_terminals,
        "no_analysis_outside_collection_snapshot": not analysis_ids_outside_snapshot,
        "no_duplicate_link_outside_collection_snapshot": duplicate_links_outside_snapshot == 0,
    }
    metrics = {
        "source_postings": source_count,
        "deduplicated_postings": len(duplicate_ids),
        "analysed_postings": len(success_rows),
        "av_postings": av_count,
        "non_av_postings": non_av_count,
        "unknown_relevance": unknown_count,
        "failed_or_pending": len(non_success),
        "unaccounted": len(unaccounted_ids),
        "analysis_rows_in_snapshot": analysis_count,
        "duplicate_analysis_overlap": len(overlap_ids),
        "analysis_rows_outside_snapshot": len(analysis_ids_outside_snapshot),
        "duplicate_links_outside_snapshot": duplicate_links_outside_snapshot,
        "duplicate_company_mismatches": company_mismatches,
        "duplicate_broken_targets": len(broken_targets),
        "duplicate_cycles": len(cycles),
        "duplicate_unresolved_terminals": len(unresolved_terminals),
        "companies_with_av_postings": len({
            source_company_by_id[job_id]
            for job_id, row in success_rows.items()
            if _relevance(row.get("av_relevant")) is True and source_company_by_id[job_id] is not None
        }),
    }
    return {"metrics": metrics, "checks": checks, "duplicate_map": duplicate_to_kept,
            "analysis_rows": analyses_by_id, "source_company_by_id": source_company_by_id}


def release_qa_report(connection: Any, release_key: str) -> dict[str, Any]:
    """Read one release and return AV-only metrics plus internal QA counts."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT dr.dashboard_release_id,dr.release_key,dr.status,dr.collection_run_id,"
            "dr.analysis_run_id,dr.cluster_run_id,dr.data_cutoff_date,cr.run_key AS collection_run_key,"
            "cr.status AS collection_run_status,"
            "ar.run_key AS analysis_run_key,ar.status AS analysis_run_status,"
            "clr.run_key AS cluster_run_key,clr.status AS cluster_run_status "
            "FROM dashboard_releases dr "
            "LEFT JOIN collection_runs cr ON cr.collection_run_id=dr.collection_run_id "
            "JOIN analysis_runs ar ON ar.analysis_run_id=dr.analysis_run_id "
            "JOIN cluster_runs clr ON clr.cluster_run_id=dr.cluster_run_id "
            "WHERE dr.release_key=%s",
            (release_key,),
        )
        release = cursor.fetchone()
        if release is None:
            raise ImportErrorSafe(f"Dashboard release not found: {release_key}")
        if not release.get("collection_run_id"):
            raise ImportErrorSafe("Release has no collection snapshot; release metrics cannot be reconciled")

        cursor.execute(
            "SELECT jo.job_id,co.company_id FROM job_observations jo "
            "JOIN jobs j ON j.job_id=jo.job_id "
            "JOIN job_sources src ON src.source_id=j.source_id "
            "JOIN companies co ON co.company_id=src.company_id "
            "WHERE jo.collection_run_id=%s",
            (release["collection_run_id"],),
        )
        source_rows = list(cursor.fetchall())

        cursor.execute(
            "SELECT job_id,job_analysis_id,analysis_status,av_relevant "
            "FROM job_analyses WHERE analysis_run_id=%s",
            (release["analysis_run_id"],),
        )
        analysis_rows = list(cursor.fetchall())

        cursor.execute(
            "SELECT jdl.duplicate_job_id,jdl.kept_job_id,dup_src.company_id AS duplicate_company_id,"
            "keep_src.company_id AS kept_company_id "
            "FROM job_deduplication_links jdl "
            "JOIN jobs dup_job ON dup_job.job_id=jdl.duplicate_job_id "
            "JOIN job_sources dup_src ON dup_src.source_id=dup_job.source_id "
            "JOIN jobs keep_job ON keep_job.job_id=jdl.kept_job_id "
            "JOIN job_sources keep_src ON keep_src.source_id=keep_job.source_id "
            "WHERE jdl.analysis_run_id=%s",
            (release["analysis_run_id"],),
        )
        duplicate_rows = list(cursor.fetchall())

        cursor.execute(
            "SELECT jca.job_analysis_id,ja.job_id,ja.analysis_status,ja.av_relevant,"
            "c.cluster_pk,c.population,c.size_cached "
            "FROM job_cluster_assignments jca "
            "JOIN job_analyses ja ON ja.job_analysis_id=jca.job_analysis_id "
            "JOIN clusters c ON c.cluster_pk=jca.cluster_pk "
            "WHERE jca.analysis_run_id=%s AND jca.cluster_run_id=%s",
            (release["analysis_run_id"], release["cluster_run_id"]),
        )
        assignment_rows = list(cursor.fetchall())

        cursor.execute(
            "SELECT c.cluster_pk,c.population,c.size_cached,c.is_noise,c.cluster_name,clr.label_status,"
            "COUNT(jca.job_analysis_id) AS member_count "
            "FROM clusters c LEFT JOIN job_cluster_assignments jca "
            "ON jca.cluster_pk=c.cluster_pk AND jca.cluster_run_id=c.cluster_run_id "
            "LEFT JOIN cluster_label_revisions clr ON clr.cluster_label_revision_id=c.current_label_revision_id "
            "WHERE c.cluster_run_id=%s GROUP BY c.cluster_pk,c.population,c.size_cached,c.is_noise,c.cluster_name,clr.label_status",
            (release["cluster_run_id"],),
        )
        cluster_rows = list(cursor.fetchall())

        cursor.execute(
            "SELECT COUNT(*) AS skillless_av_jobs FROM ("
            "SELECT ja.job_analysis_id "
            "FROM job_analyses ja "
            "JOIN job_observations jo ON jo.job_id=ja.job_id AND jo.collection_run_id=%s "
            "LEFT JOIN job_deduplication_links jdl ON jdl.duplicate_job_id=ja.job_id "
            "AND jdl.analysis_run_id=ja.analysis_run_id "
            "LEFT JOIN job_skills js ON js.job_analysis_id=ja.job_analysis_id "
            "WHERE ja.analysis_run_id=%s AND ja.analysis_status='success' "
            "AND ja.av_relevant=TRUE AND jdl.duplicate_job_id IS NULL "
            "GROUP BY ja.job_analysis_id HAVING COUNT(js.skill_id)=0) AS skillless",
            (release["collection_run_id"], release["analysis_run_id"]),
        )
        skillless_row = cursor.fetchone()

        cursor.execute(
            "SELECT COUNT(*) AS visible_job_rows,COUNT(DISTINCT job_id) AS visible_job_count,"
            "COUNT(DISTINCT company_id) AS visible_company_count "
            "FROM v_dashboard_jobs WHERE dashboard_release_id=%s",
            (release["dashboard_release_id"],),
        )
        public_jobs = cursor.fetchone()
        cursor.execute(
            "SELECT COUNT(DISTINCT job_id) AS visible_skilled_job_count "
            "FROM v_dashboard_job_skills WHERE dashboard_release_id=%s",
            (release["dashboard_release_id"],),
        )
        public_skills = cursor.fetchone()
        cursor.execute(
            "SELECT COUNT(*) AS violations FROM v_dashboard_jobs v "
            "JOIN job_analyses ja ON ja.job_id=v.job_id AND ja.analysis_run_id=%s "
            "LEFT JOIN job_deduplication_links jdl ON jdl.analysis_run_id=%s AND jdl.duplicate_job_id=v.job_id "
            "WHERE v.dashboard_release_id=%s AND (ja.analysis_status<>'success' OR ja.av_relevant IS NULL "
            "OR ja.av_relevant<>TRUE OR jdl.duplicate_job_id IS NOT NULL "
            "OR NOT EXISTS (SELECT 1 FROM job_observations jo WHERE jo.job_id=v.job_id "
            "AND jo.collection_run_id=%s))",
            (release["analysis_run_id"], release["analysis_run_id"], release["dashboard_release_id"],
             release["collection_run_id"]),
        )
        public_job_violations = cursor.fetchone()
        cursor.execute(
            "SELECT COUNT(*) AS violations FROM v_dashboard_job_skills v "
            "JOIN job_analyses ja ON ja.job_id=v.job_id AND ja.analysis_run_id=%s "
            "LEFT JOIN job_deduplication_links jdl ON jdl.analysis_run_id=%s AND jdl.duplicate_job_id=v.job_id "
            "WHERE v.dashboard_release_id=%s AND (ja.analysis_status<>'success' OR ja.av_relevant IS NULL "
            "OR ja.av_relevant<>TRUE OR jdl.duplicate_job_id IS NOT NULL "
            "OR NOT EXISTS (SELECT 1 FROM job_observations jo WHERE jo.job_id=v.job_id "
            "AND jo.collection_run_id=%s))",
            (release["analysis_run_id"], release["analysis_run_id"], release["dashboard_release_id"],
             release["collection_run_id"]),
        )
        public_skill_violations = cursor.fetchone()
        cursor.execute(
            "SELECT COUNT(*) AS visible_cluster_count,"
            "COUNT(CASE WHEN population<>'av_relevant' THEN 1 END) AS visible_non_av_cluster_count "
            "FROM v_dashboard_clusters WHERE dashboard_release_id=%s",
            (release["dashboard_release_id"],),
        )
        public_cluster_leaks = cursor.fetchone()

    outcomes = summarize_outcomes(source_rows, analysis_rows, duplicate_rows)
    metrics = outcomes["metrics"]
    assignment_count_by_analysis: Counter[int] = Counter()
    assignment_population_mismatches = 0
    duplicate_cluster_assignments = 0
    for row in assignment_rows:
        job_analysis_id = int(row["job_analysis_id"])
        assignment_count_by_analysis[job_analysis_id] += 1
        relevance = _relevance(row.get("av_relevant"))
        expected_population = "av_relevant" if relevance is True else (
            "not_av_relevant" if relevance is False else None
        )
        if row.get("analysis_status") != "success" or expected_population != row.get("population"):
            assignment_population_mismatches += 1
        if int(row["job_id"]) in outcomes["duplicate_map"]:
            duplicate_cluster_assignments += 1

    success_analysis_ids = {
        int(row["job_analysis_id"])
        for row in analysis_rows
        if int(row["job_id"]) in outcomes["analysis_rows"]
        and row.get("analysis_status") == "success"
        and _relevance(outcomes["analysis_rows"][int(row["job_id"])].get("av_relevant")) is True
    }
    unclustered_av = sum(assignment_count_by_analysis.get(analysis_id, 0) == 0
                         for analysis_id in success_analysis_ids)
    cluster_size_mismatches = sum(
        int(row["size_cached"]) != int(row["member_count"])
        for row in cluster_rows
    )
    visible_job_count = int((public_jobs or {}).get("visible_job_count") or 0)
    visible_company_count = int((public_jobs or {}).get("visible_company_count") or 0)
    visible_skillless = int((skillless_row or {}).get("skillless_av_jobs") or 0)
    visible_cluster_count = int((public_cluster_leaks or {}).get("visible_cluster_count") or 0)
    visible_non_av_cluster_count = int((public_cluster_leaks or {}).get("visible_non_av_cluster_count") or 0)
    expected_public_jobs = metrics["av_postings"] if release["status"] == "published" else 0
    expected_public_companies = metrics["companies_with_av_postings"] if release["status"] == "published" else 0
    expected_public_skilled = metrics["av_postings"] - visible_skillless if release["status"] == "published" else 0
    visible_skilled = int((public_skills or {}).get("visible_skilled_job_count") or 0)
    unnamed_av_clusters = sum(
        row.get("population") == "av_relevant" and int(row["member_count"]) > 0
        and not bool(row.get("is_noise"))
        and (not row.get("cluster_name") or row.get("label_status") != "approved")
        for row in cluster_rows
    )
    av_noise_clusters = sum(
        row.get("population") == "av_relevant" and int(row["member_count"]) > 0
        and bool(row.get("is_noise"))
        for row in cluster_rows
    )
    av_noise_postings = sum(
        int(row["member_count"])
        for row in cluster_rows
        if row.get("population") == "av_relevant" and bool(row.get("is_noise"))
    )
    expected_av_cluster_count = sum(
        row.get("population") == "av_relevant" and int(row["member_count"]) > 0
        for row in cluster_rows
    )
    expected_public_clusters = expected_av_cluster_count if release["status"] == "published" else 0
    public_job_violation_count = int((public_job_violations or {}).get("violations") or 0)
    public_skill_violation_count = int((public_skill_violations or {}).get("violations") or 0)
    checks = dict(outcomes["checks"])
    checks.update({
        "cluster_assignments_match_population": assignment_population_mismatches == 0,
        "no_duplicate_has_cluster_assignment": duplicate_cluster_assignments == 0,
        "cluster_cached_sizes_match_memberships": cluster_size_mismatches == 0,
        "all_av_postings_are_clustered": unclustered_av == 0,
        "analysis_run_completed": release["analysis_run_status"] == "completed",
        "cluster_run_completed": release["cluster_run_status"] == "completed",
        "published_view_job_count_matches_av_count": visible_job_count == expected_public_jobs,
        "public_job_rows_are_unique": int(public_jobs["visible_job_rows"]) == visible_job_count,
        "published_company_count_matches_av_companies": visible_company_count == expected_public_companies,
        "published_skilled_job_count_matches_av_skills": visible_skilled == expected_public_skilled,
        "public_job_view_is_av_only_and_release_scoped": public_job_violation_count == 0,
        "public_skill_view_is_av_only_and_release_scoped": public_skill_violation_count == 0,
        "published_cluster_view_matches_av_population": visible_cluster_count == expected_public_clusters,
        "public_cluster_view_has_no_non_av_population": visible_non_av_cluster_count == 0,
    })
    metrics.update({
        "unclustered_av_postings": unclustered_av,
        "cluster_population_mismatches": assignment_population_mismatches,
        "duplicate_cluster_assignments": duplicate_cluster_assignments,
        "cluster_size_mismatches": cluster_size_mismatches,
        "av_postings_without_skills": visible_skillless,
        "av_clusters_without_approved_names": unnamed_av_clusters,
        "av_noise_clusters": av_noise_clusters,
        "av_noise_postings": av_noise_postings,
        "public_visible_av_postings": visible_job_count,
        "public_visible_companies": visible_company_count,
        "public_visible_skilled_postings": int((public_skills or {}).get("visible_skilled_job_count") or 0),
        "public_job_view_violations": public_job_violation_count,
        "public_skill_view_violations": public_skill_violation_count,
        "public_visible_non_av_clusters": visible_non_av_cluster_count,
    })
    errors = [name for name, passed in checks.items() if not passed]
    warnings = []
    if visible_skillless:
        warnings.append(f"{visible_skillless} AV-relevant posting(s) have no extracted skills")
    if unnamed_av_clusters:
        warnings.append(
            f"{unnamed_av_clusters} regular AV cluster(s) have no approved name; "
            "display an unlabelled state, not an invented occupation name"
        )
    return {
        "status": "passed" if not errors else "failed",
        "release": {
            "dashboard_release_id": int(release["dashboard_release_id"]),
            "release_key": release["release_key"],
            "status": release["status"],
            "data_cutoff_date": str(release["data_cutoff_date"]),
            "collection_run_id": int(release["collection_run_id"]),
            "collection_run_key": release["collection_run_key"],
            "collection_run_status": release["collection_run_status"],
            "analysis_run_id": int(release["analysis_run_id"]),
            "analysis_run_key": release["analysis_run_key"],
            "analysis_run_status": release["analysis_run_status"],
            "cluster_run_id": int(release["cluster_run_id"]),
            "cluster_run_key": release["cluster_run_key"],
            "cluster_run_status": release["cluster_run_status"],
        },
        "metrics": metrics,
        "public_dashboard": {
            "population": "successful av_relevant=true, non-duplicate jobs in the published release snapshot",
            "expected_visible_av_postings": expected_public_jobs,
            "visible_av_postings": visible_job_count,
            "visible_companies": visible_company_count,
            "visible_skilled_postings": int((public_skills or {}).get("visible_skilled_job_count") or 0),
            "visible_clusters": visible_cluster_count,
        },
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "notes": [
            "Counts describe the linked release snapshot; they do not assert that a posting is currently open.",
            "AV relevance is the imported classifier result and has not been manually verified by this report.",
        ],
    }
