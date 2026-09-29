-- Dashboard-facing views. Run after a fresh schema install or completed table migrations.

USE av_job_profiles;

CREATE OR REPLACE VIEW v_candidate_dashboard_jobs AS
SELECT
  dr.dashboard_release_id,
  dr.release_key,
  j.job_id,
  j.source_key,
  c.company_id,
  JSON_UNQUOTE(JSON_EXTRACT(jo.raw_payload_json, '$.metadata.company')) AS company_name,
  JSON_UNQUOTE(JSON_EXTRACT(jo.raw_payload_json, '$.metadata.platform')) AS platform,
  JSON_UNQUOTE(JSON_EXTRACT(jo.raw_payload_json, '$.metadata.region')) AS source_region,
  jo.advertised_job_title,
  ja.generic_job_title,
  COALESCE(NULLIF(TRIM(ja.generic_job_title), ''), jo.advertised_job_title) AS display_title,
  jo.job_url,
  jo.location_raw,
  jo.city,
  jo.state_region,
  jo.country_code,
  jo.remote_type,
  jo.salary_raw,
  jo.salary_min,
  jo.salary_max,
  jo.salary_currency,
  jo.salary_period,
  jo.date_posted,
  jo.first_seen_date,
  jo.last_seen_date,
  jo.is_active_at_run AS is_active,
  jo.is_new_at_run AS is_new_in_latest_run,
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
JOIN job_observations AS jo
  ON jo.job_id = j.job_id AND jo.collection_run_id = dr.collection_run_id
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
WHERE dr.status IN ('draft', 'published')
  AND dr.collection_run_id IS NOT NULL
  AND ja.analysis_status = 'success'
  AND ja.av_relevant = TRUE
  AND NOT EXISTS (
    SELECT 1
    FROM job_deduplication_links AS jdl
    WHERE jdl.analysis_run_id = dr.analysis_run_id
      AND jdl.duplicate_job_id = j.job_id
  );

CREATE OR REPLACE VIEW v_candidate_dashboard_job_skills AS
SELECT
  dr.dashboard_release_id,
  dr.release_key,
  j.job_id,
  j.source_key,
  c.company_id,
  JSON_UNQUOTE(JSON_EXTRACT(jo.raw_payload_json, '$.metadata.company')) AS company_name,
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
JOIN job_observations AS jo
  ON jo.job_id = j.job_id AND jo.collection_run_id = dr.collection_run_id
JOIN job_sources AS src
  ON src.source_id = j.source_id
JOIN companies AS c
  ON c.company_id = src.company_id
JOIN job_skills AS js
  ON js.job_analysis_id = ja.job_analysis_id
JOIN skills AS s
  ON s.skill_id = js.skill_id
WHERE dr.status IN ('draft', 'published')
  AND dr.collection_run_id IS NOT NULL
  AND ja.analysis_status = 'success'
  AND ja.av_relevant = TRUE
  AND NOT EXISTS (
    SELECT 1
    FROM job_deduplication_links AS jdl
    WHERE jdl.analysis_run_id = dr.analysis_run_id
      AND jdl.duplicate_job_id = j.job_id
  );

CREATE OR REPLACE VIEW v_candidate_dashboard_clusters AS
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
WHERE dr.status IN ('draft', 'published')
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

-- Public views read only rows copied at publication. Candidate views above are
-- internal build inputs and must not be granted to the public backend account.
CREATE OR REPLACE VIEW v_dashboard_jobs AS
SELECT dr.dashboard_release_id, dr.release_key, snap.*
FROM dashboard_releases dr
JOIN dashboard_release_snapshot_rows r
  ON r.dashboard_release_id=dr.dashboard_release_id AND r.row_kind='job'
JOIN JSON_TABLE(r.payload_json, '$' COLUMNS (
  job_id BIGINT PATH '$.job_id', source_key VARCHAR(191) PATH '$.source_key',
  company_id BIGINT PATH '$.company_id', company_name VARCHAR(191) PATH '$.company_name',
  platform VARCHAR(40) PATH '$.platform', source_region VARCHAR(80) PATH '$.source_region',
  advertised_job_title VARCHAR(512) PATH '$.advertised_job_title',
  generic_job_title VARCHAR(255) PATH '$.generic_job_title',
  display_title VARCHAR(512) PATH '$.display_title',
  job_url VARCHAR(2048) PATH '$.job_url', location_raw VARCHAR(1024) PATH '$.location_raw',
  city VARCHAR(191) PATH '$.city', state_region VARCHAR(191) PATH '$.state_region',
  country_code CHAR(2) PATH '$.country_code', remote_type VARCHAR(24) PATH '$.remote_type',
  salary_raw VARCHAR(1024) PATH '$.salary_raw', salary_min DECIMAL(18,2) PATH '$.salary_min',
  salary_max DECIMAL(18,2) PATH '$.salary_max', salary_currency CHAR(3) PATH '$.salary_currency',
  salary_period VARCHAR(24) PATH '$.salary_period', date_posted VARCHAR(40) PATH '$.date_posted',
  first_seen_date DATE PATH '$.first_seen_date', last_seen_date DATE PATH '$.last_seen_date',
  is_active TINYINT PATH '$.is_active', is_new_in_latest_run TINYINT PATH '$.is_new_in_latest_run',
  av_relevant TINYINT PATH '$.av_relevant',
  analysis_result_origin VARCHAR(24) PATH '$.analysis_result_origin',
  relevance_confidence DECIMAL(5,4) PATH '$.relevance_confidence',
  relevance_confidence_label VARCHAR(24) PATH '$.relevance_confidence_label',
  seniority_code VARCHAR(32) PATH '$.seniority_code',
  experience_min_years DECIMAL(5,1) PATH '$.experience_min_years',
  experience_max_years DECIMAL(5,1) PATH '$.experience_max_years',
  cluster_number INT PATH '$.cluster_number',
  current_label_revision_id BIGINT PATH '$.current_label_revision_id',
  cluster_name VARCHAR(255) PATH '$.cluster_name',
  job_family VARCHAR(128) PATH '$.job_family',
  specialisation VARCHAR(128) PATH '$.specialisation',
  label_source VARCHAR(32) PATH '$.label_source',
  label_status VARCHAR(24) PATH '$.label_status',
  label_revision_number INT PATH '$.label_revision_number',
  cluster_lean VARCHAR(32) PATH '$.cluster_lean',
  is_noise TINYINT PATH '$.is_noise'
)) AS snap
WHERE dr.status='published' AND dr.snapshot_frozen_at IS NOT NULL;

CREATE OR REPLACE VIEW v_dashboard_job_skills AS
SELECT dr.dashboard_release_id, dr.release_key, snap.*
FROM dashboard_releases dr
JOIN dashboard_release_snapshot_rows r
  ON r.dashboard_release_id=dr.dashboard_release_id AND r.row_kind='job_skill'
JOIN JSON_TABLE(r.payload_json, '$' COLUMNS (
  job_id BIGINT PATH '$.job_id', source_key VARCHAR(191) PATH '$.source_key',
  company_id BIGINT PATH '$.company_id', company_name VARCHAR(191) PATH '$.company_name',
  skill_id BIGINT PATH '$.skill_id', skill_name VARCHAR(191) PATH '$.skill_name',
  skill_type VARCHAR(32) PATH '$.skill_type',
  confidence DECIMAL(5,4) PATH '$.confidence', skill_rank INT PATH '$.skill_rank'
)) AS snap
WHERE dr.status='published' AND dr.snapshot_frozen_at IS NOT NULL;

CREATE OR REPLACE VIEW v_dashboard_skill_demand AS
SELECT dashboard_release_id, release_key, skill_id, skill_name, skill_type,
  COUNT(DISTINCT job_id) AS job_count, COUNT(DISTINCT company_id) AS company_count
FROM v_dashboard_job_skills
GROUP BY dashboard_release_id, release_key, skill_id, skill_name, skill_type;

CREATE OR REPLACE VIEW v_dashboard_clusters AS
SELECT dr.dashboard_release_id, dr.release_key, snap.*,
  JSON_UNQUOTE(JSON_EXTRACT(r.payload_json, '$.top_terms_json')) AS top_terms_json,
  JSON_UNQUOTE(JSON_EXTRACT(r.payload_json, '$.example_titles_json')) AS example_titles_json,
  JSON_UNQUOTE(JSON_EXTRACT(r.payload_json, '$.top_companies_json')) AS top_companies_json
FROM dashboard_releases dr
JOIN dashboard_release_snapshot_rows r
  ON r.dashboard_release_id=dr.dashboard_release_id AND r.row_kind='cluster'
JOIN JSON_TABLE(r.payload_json, '$' COLUMNS (
  cluster_pk BIGINT PATH '$.cluster_pk', cluster_number INT PATH '$.cluster_number',
  cluster_name VARCHAR(255) PATH '$.cluster_name',
  job_family VARCHAR(128) PATH '$.job_family',
  specialisation VARCHAR(128) PATH '$.specialisation',
  label_source VARCHAR(32) PATH '$.label_source',
  label_status VARCHAR(24) PATH '$.label_status',
  label_revision_number INT PATH '$.label_revision_number',
  label_rationale VARCHAR(1024) PATH '$.label_rationale',
  labelled_by VARCHAR(191) PATH '$.labelled_by',
  reviewed_by VARCHAR(191) PATH '$.reviewed_by',
  reviewed_at VARCHAR(40) PATH '$.reviewed_at',
  population VARCHAR(24) PATH '$.population', lean VARCHAR(24) PATH '$.lean',
  is_noise TINYINT PATH '$.is_noise', size_cached INT PATH '$.size_cached',
  technical_score DECIMAL(5,4) PATH '$.technical_score',
  notes VARCHAR(1024) PATH '$.notes'
)) AS snap
WHERE dr.status='published' AND dr.snapshot_frozen_at IS NOT NULL;

-- A weekly collection can be official before classification exists. These
-- read-only views are the backend's version catalogue and historical inputs;
-- draft analysis and non-AV classifier rows are never exposed here.
CREATE OR REPLACE VIEW v_weekly_versions AS
SELECT
  wv.week_date,
  wv.collection_run_id,
  cr.run_key AS collection_run_key,
  JSON_UNQUOTE(JSON_EXTRACT(cr.source_scope_json, '$.input_sha256')) AS collection_sha256,
  cr.status AS collection_run_status,
  cr.run_kind,
  cr.time_quality,
  cr.source_report_available,
  wv.selected_analysis_run_id AS analysis_run_id,
  ar.run_key AS analysis_run_key,
  ar.status AS analysis_run_status,
  dr.dashboard_release_id,
  dr.release_key,
  dr.status AS release_status,
  CASE
    WHEN wv.selected_analysis_run_id IS NULL THEN 'pending'
    WHEN dr.snapshot_frozen_at IS NOT NULL AND dr.status IN ('published','retired') THEN 'ready'
    ELSE 'imported_pending_release'
  END AS classification_status
FROM weekly_versions AS wv
JOIN collection_runs AS cr ON cr.collection_run_id=wv.collection_run_id
LEFT JOIN analysis_runs AS ar ON ar.analysis_run_id=wv.selected_analysis_run_id
LEFT JOIN dashboard_releases AS dr
  ON dr.analysis_run_id=wv.selected_analysis_run_id
 AND dr.collection_run_id=wv.collection_run_id;

CREATE OR REPLACE VIEW v_weekly_jobs AS
SELECT
  wv.week_date, wv.collection_run_id, j.job_id, j.source_key, j.source_id,
  c.company_id, c.company_name,
  jo.advertised_job_title, jo.job_url, jo.location_raw, jo.date_posted,
  jo.first_seen_date, jo.last_seen_date, jo.state_as_of_date,
  jo.source_last_collected_at, jo.is_active_at_run AS is_active,
  jo.is_new_at_run AS is_new_in_run
FROM weekly_versions AS wv
JOIN job_observations AS jo ON jo.collection_run_id=wv.collection_run_id
JOIN jobs AS j ON j.job_id=jo.job_id
JOIN job_sources AS src ON src.source_id=j.source_id
JOIN companies AS c ON c.company_id=src.company_id;

CREATE OR REPLACE VIEW v_weekly_av_jobs AS
SELECT
  wv.week_date, dr.dashboard_release_id, dr.release_key,
  snap.job_id, snap.source_key, snap.company_id, snap.company_name,
  snap.advertised_job_title, snap.display_title, snap.job_url,
  snap.location_raw, snap.date_posted, snap.is_active, snap.seniority_code,
  snap.cluster_number, snap.cluster_name, snap.is_noise
FROM weekly_versions AS wv
JOIN dashboard_releases AS dr
  ON dr.collection_run_id=wv.collection_run_id
 AND dr.analysis_run_id=wv.selected_analysis_run_id
JOIN dashboard_release_snapshot_rows AS r
  ON r.dashboard_release_id=dr.dashboard_release_id AND r.row_kind='job'
JOIN JSON_TABLE(r.payload_json, '$' COLUMNS (
  job_id BIGINT PATH '$.job_id', source_key VARCHAR(191) PATH '$.source_key',
  company_id BIGINT PATH '$.company_id', company_name VARCHAR(191) PATH '$.company_name',
  advertised_job_title VARCHAR(512) PATH '$.advertised_job_title',
  display_title VARCHAR(512) PATH '$.display_title',
  job_url VARCHAR(2048) PATH '$.job_url', location_raw VARCHAR(1024) PATH '$.location_raw',
  date_posted VARCHAR(40) PATH '$.date_posted', is_active TINYINT PATH '$.is_active',
  seniority_code VARCHAR(32) PATH '$.seniority_code',
  cluster_number INT PATH '$.cluster_number', cluster_name VARCHAR(255) PATH '$.cluster_name',
  is_noise TINYINT PATH '$.is_noise'
)) AS snap
WHERE dr.status IN ('published','retired') AND dr.snapshot_frozen_at IS NOT NULL;

CREATE OR REPLACE VIEW v_weekly_av_job_skills AS
SELECT
  wv.week_date, dr.dashboard_release_id, dr.release_key,
  snap.job_id, snap.source_key, snap.company_id, snap.company_name,
  snap.skill_id, snap.skill_name, snap.skill_type, snap.confidence
FROM weekly_versions AS wv
JOIN dashboard_releases AS dr
  ON dr.collection_run_id=wv.collection_run_id
 AND dr.analysis_run_id=wv.selected_analysis_run_id
JOIN dashboard_release_snapshot_rows AS r
  ON r.dashboard_release_id=dr.dashboard_release_id AND r.row_kind='job_skill'
JOIN JSON_TABLE(r.payload_json, '$' COLUMNS (
  job_id BIGINT PATH '$.job_id', source_key VARCHAR(191) PATH '$.source_key',
  company_id BIGINT PATH '$.company_id', company_name VARCHAR(191) PATH '$.company_name',
  skill_id BIGINT PATH '$.skill_id', skill_name VARCHAR(191) PATH '$.skill_name',
  skill_type VARCHAR(32) PATH '$.skill_type',
  confidence DECIMAL(5,4) PATH '$.confidence'
)) AS snap
WHERE dr.status IN ('published','retired') AND dr.snapshot_frozen_at IS NOT NULL;
