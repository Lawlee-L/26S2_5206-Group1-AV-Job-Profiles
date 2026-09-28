-- Dashboard-facing views. Run after a fresh schema install or completed table migrations.

USE av_job_profiles;

CREATE OR REPLACE VIEW v_dashboard_jobs AS
SELECT
  dr.dashboard_release_id,
  dr.release_key,
  j.job_id,
  j.source_key,
  c.company_id,
  c.company_name,
  js.platform,
  js.region AS source_region,
  j.advertised_job_title,
  ja.generic_job_title,
  COALESCE(NULLIF(TRIM(ja.generic_job_title), ''), j.advertised_job_title) AS display_title,
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
  ja.av_relevant,
  ja.result_origin AS analysis_result_origin,
  ja.relevance_confidence,
  ja.relevance_confidence_label,
  ja.seniority_code,
  ja.experience_min_years,
  ja.experience_max_years,
  cl.cluster_number,
  cl.current_label_revision_id,
  cl.cluster_name,
  cl.job_family,
  cl.specialisation,
  clr.label_source,
  clr.label_status,
  clr.revision_number AS label_revision_number,
  cl.lean AS cluster_lean,
  cl.is_noise
FROM dashboard_releases AS dr
JOIN job_analyses AS ja
  ON ja.analysis_run_id = dr.analysis_run_id
JOIN jobs AS j
  ON j.job_id = ja.job_id
JOIN job_sources AS js
  ON js.source_id = j.source_id
JOIN companies AS c
  ON c.company_id = js.company_id
LEFT JOIN job_cluster_assignments AS jca
  ON jca.job_analysis_id = ja.job_analysis_id
 AND jca.cluster_run_id = dr.cluster_run_id
LEFT JOIN clusters AS cl
  ON cl.cluster_pk = jca.cluster_pk
LEFT JOIN cluster_label_revisions AS clr
  ON clr.cluster_label_revision_id = cl.current_label_revision_id
WHERE dr.status = 'published'
  AND dr.collection_run_id IS NOT NULL
  AND ja.analysis_status = 'success'
  AND ja.av_relevant = TRUE
  AND EXISTS (
    SELECT 1
    FROM job_observations AS jo
    WHERE jo.job_id = j.job_id
      AND jo.collection_run_id = dr.collection_run_id
  )
  AND NOT EXISTS (
    SELECT 1
    FROM job_deduplication_links AS jdl
    WHERE jdl.analysis_run_id = dr.analysis_run_id
      AND jdl.duplicate_job_id = j.job_id
  );

CREATE OR REPLACE VIEW v_dashboard_job_skills AS
SELECT
  dr.dashboard_release_id,
  dr.release_key,
  j.job_id,
  j.source_key,
  c.company_id,
  c.company_name,
  s.skill_id,
  s.canonical_name AS skill_name,
  s.skill_type,
  js.confidence,
  js.skill_rank
FROM dashboard_releases AS dr
JOIN job_analyses AS ja
  ON ja.analysis_run_id = dr.analysis_run_id
JOIN jobs AS j
  ON j.job_id = ja.job_id
JOIN job_sources AS src
  ON src.source_id = j.source_id
JOIN companies AS c
  ON c.company_id = src.company_id
JOIN job_skills AS js
  ON js.job_analysis_id = ja.job_analysis_id
JOIN skills AS s
  ON s.skill_id = js.skill_id
WHERE dr.status = 'published'
  AND dr.collection_run_id IS NOT NULL
  AND ja.analysis_status = 'success'
  AND ja.av_relevant = TRUE
  AND EXISTS (
    SELECT 1
    FROM job_observations AS jo
    WHERE jo.job_id = j.job_id
      AND jo.collection_run_id = dr.collection_run_id
  )
  AND NOT EXISTS (
    SELECT 1
    FROM job_deduplication_links AS jdl
    WHERE jdl.analysis_run_id = dr.analysis_run_id
      AND jdl.duplicate_job_id = j.job_id
  );

CREATE OR REPLACE VIEW v_dashboard_skill_demand AS
SELECT
  dashboard_release_id,
  release_key,
  skill_id,
  skill_name,
  skill_type,
  COUNT(DISTINCT job_id) AS job_count,
  COUNT(DISTINCT company_id) AS company_count
FROM v_dashboard_job_skills
GROUP BY dashboard_release_id, release_key, skill_id, skill_name, skill_type;

CREATE OR REPLACE VIEW v_dashboard_clusters AS
SELECT
  dr.dashboard_release_id,
  dr.release_key,
  cl.cluster_pk,
  cl.cluster_number,
  cl.cluster_name,
  cl.job_family,
  cl.specialisation,
  clr.label_source,
  clr.label_status,
  clr.revision_number AS label_revision_number,
  clr.rationale AS label_rationale,
  clr.labelled_by,
  clr.reviewed_by,
  clr.reviewed_at,
  cl.population,
  cl.lean,
  cl.is_noise,
  cl.size_cached,
  cl.technical_score,
  cl.top_terms_json,
  cl.example_titles_json,
  cl.top_companies_json,
  cl.notes
FROM dashboard_releases AS dr
JOIN clusters AS cl
  ON cl.cluster_run_id = dr.cluster_run_id
LEFT JOIN cluster_label_revisions AS clr
  ON clr.cluster_label_revision_id = cl.current_label_revision_id
WHERE dr.status = 'published'
  AND dr.collection_run_id IS NOT NULL
  AND cl.population = 'av_relevant'
  AND EXISTS (
    SELECT 1
    FROM job_cluster_assignments AS jca
    JOIN job_analyses AS ja
      ON ja.job_analysis_id = jca.job_analysis_id
     AND ja.analysis_run_id = dr.analysis_run_id
    JOIN job_observations AS jo
      ON jo.job_id = ja.job_id
     AND jo.collection_run_id = dr.collection_run_id
    WHERE jca.cluster_run_id = dr.cluster_run_id
      AND jca.cluster_pk = cl.cluster_pk
      AND ja.analysis_status = 'success'
      AND ja.av_relevant = TRUE
      AND NOT EXISTS (
        SELECT 1
        FROM job_deduplication_links AS jdl
        WHERE jdl.analysis_run_id = dr.analysis_run_id
          AND jdl.duplicate_job_id = ja.job_id
      )
  );
