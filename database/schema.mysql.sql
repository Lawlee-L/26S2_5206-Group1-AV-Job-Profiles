-- AV Job Profiles relational database foundation
-- Target: MySQL 8.0.16+
-- All timestamps are UTC. Application connections should also use UTC.

CREATE DATABASE IF NOT EXISTS av_job_profiles
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE av_job_profiles;

SET time_zone = '+00:00';

-- ---------------------------------------------------------------------------
-- Import audit layer
-- ---------------------------------------------------------------------------

CREATE TABLE import_batches (
  import_batch_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  batch_type VARCHAR(40) NOT NULL,
  source_filename VARCHAR(512) NOT NULL,
  file_sha256 CHAR(64) NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'pending',
  total_rows INT UNSIGNED NOT NULL DEFAULT 0,
  accepted_rows INT UNSIGNED NOT NULL DEFAULT 0,
  rejected_rows INT UNSIGNED NOT NULL DEFAULT 0,
  metadata_json JSON NULL,
  started_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  completed_at DATETIME(6) NULL,
  PRIMARY KEY (import_batch_id),
  UNIQUE KEY uq_import_batch_file (batch_type, file_sha256),
  CONSTRAINT chk_import_batch_status
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'partial')),
  CONSTRAINT chk_import_batch_counts
    CHECK (accepted_rows + rejected_rows <= total_rows)
) ENGINE=InnoDB;

CREATE TABLE import_rejections (
  import_rejection_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  import_batch_id BIGINT UNSIGNED NOT NULL,
  source_row_number INT UNSIGNED NULL,
  source_key VARCHAR(191) NULL,
  error_code VARCHAR(64) NOT NULL,
  error_message TEXT NOT NULL,
  raw_record JSON NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (import_rejection_id),
  KEY idx_import_rejections_batch (import_batch_id),
  KEY idx_import_rejections_source_key (source_key),
  CONSTRAINT fk_import_rejections_batch
    FOREIGN KEY (import_batch_id) REFERENCES import_batches (import_batch_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- Collection and current job layer
-- ---------------------------------------------------------------------------

CREATE TABLE companies (
  company_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  company_name VARCHAR(191) NOT NULL,
  company_slug VARCHAR(191) NOT NULL,
  website_url VARCHAR(2048) NULL,
  headquarters_country_code CHAR(2) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (company_id),
  UNIQUE KEY uq_companies_name (company_name),
  UNIQUE KEY uq_companies_slug (company_slug)
) ENGINE=InnoDB;

CREATE TABLE job_sources (
  source_id VARCHAR(64) NOT NULL,
  company_id BIGINT UNSIGNED NOT NULL,
  platform VARCHAR(40) NOT NULL,
  region VARCHAR(80) NOT NULL,
  endpoint_url VARCHAR(2048) NULL,
  is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
  config_json JSON NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (source_id),
  KEY idx_job_sources_company (company_id),
  KEY idx_job_sources_platform (platform),
  CONSTRAINT fk_job_sources_company
    FOREIGN KEY (company_id) REFERENCES companies (company_id)
    ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE collection_runs (
  collection_run_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_key VARCHAR(96) NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'pending',
  pipeline_version VARCHAR(64) NULL,
  git_commit_sha CHAR(40) NULL,
  source_scope_json JSON NULL,
  notes TEXT NULL,
  started_at DATETIME(6) NOT NULL,
  completed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (collection_run_id),
  UNIQUE KEY uq_collection_runs_key (run_key),
  KEY idx_collection_runs_completed (completed_at),
  CONSTRAINT chk_collection_run_status
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'partial'))
) ENGINE=InnoDB;

CREATE TABLE source_run_results (
  collection_run_id BIGINT UNSIGNED NOT NULL,
  source_id VARCHAR(64) NOT NULL,
  status VARCHAR(24) NOT NULL,
  job_count INT UNSIGNED NOT NULL DEFAULT 0,
  error_message TEXT NULL,
  raw_snapshot_path VARCHAR(1024) NULL,
  completed_at DATETIME(6) NULL,
  PRIMARY KEY (collection_run_id, source_id),
  KEY idx_source_run_results_status (status),
  CONSTRAINT fk_source_run_results_run
    FOREIGN KEY (collection_run_id) REFERENCES collection_runs (collection_run_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_source_run_results_source
    FOREIGN KEY (source_id) REFERENCES job_sources (source_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_source_run_status
    CHECK (status IN ('pending', 'success', 'failed', 'skipped'))
) ENGINE=InnoDB;

CREATE TABLE jobs (
  job_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_key VARCHAR(191) NOT NULL,
  source_id VARCHAR(64) NOT NULL,
  source_job_id VARCHAR(255) NULL,
  advertised_job_title VARCHAR(512) NULL,
  job_description LONGTEXT NULL,
  job_url VARCHAR(2048) NULL,
  location_raw VARCHAR(1024) NULL,
  city VARCHAR(191) NULL,
  state_region VARCHAR(191) NULL,
  country_code CHAR(2) NULL,
  remote_type VARCHAR(24) NULL,
  salary_raw VARCHAR(1024) NULL,
  salary_min DECIMAL(18,2) NULL,
  salary_max DECIMAL(18,2) NULL,
  salary_currency CHAR(3) NULL,
  salary_period VARCHAR(24) NULL,
  date_posted DATETIME(6) NULL,
  first_seen_date DATE NOT NULL,
  last_seen_date DATE NOT NULL,
  latest_collected_at DATETIME(6) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  is_new_in_latest_run BOOLEAN NOT NULL DEFAULT FALSE,
  content_hash CHAR(64) NULL,
  import_batch_id BIGINT UNSIGNED NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (job_id),
  UNIQUE KEY uq_jobs_source_key (source_key),
  UNIQUE KEY uq_jobs_source_job_id (source_id, source_job_id),
  KEY idx_jobs_active_date (is_active, date_posted),
  KEY idx_jobs_first_seen (first_seen_date),
  KEY idx_jobs_last_seen (last_seen_date),
  KEY idx_jobs_country (country_code),
  KEY idx_jobs_import_batch (import_batch_id),
  CONSTRAINT fk_jobs_source
    FOREIGN KEY (source_id) REFERENCES job_sources (source_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_jobs_import_batch
    FOREIGN KEY (import_batch_id) REFERENCES import_batches (import_batch_id)
    ON DELETE SET NULL,
  CONSTRAINT chk_jobs_seen_dates
    CHECK (last_seen_date >= first_seen_date),
  CONSTRAINT chk_jobs_salary_range
    CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_max >= salary_min),
  CONSTRAINT chk_jobs_remote_type
    CHECK (remote_type IS NULL OR remote_type IN ('onsite', 'hybrid', 'remote', 'unknown'))
) ENGINE=InnoDB;

-- Immutable snapshots preserve what was seen in each collection. The jobs table
-- intentionally duplicates the latest values for fast dashboard queries.
CREATE TABLE job_observations (
  job_observation_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  job_id BIGINT UNSIGNED NOT NULL,
  collection_run_id BIGINT UNSIGNED NOT NULL,
  advertised_job_title VARCHAR(512) NULL,
  job_description LONGTEXT NULL,
  job_url VARCHAR(2048) NULL,
  location_raw VARCHAR(1024) NULL,
  salary_raw VARCHAR(1024) NULL,
  date_posted DATETIME(6) NULL,
  collected_at DATETIME(6) NOT NULL,
  is_active_at_run BOOLEAN NOT NULL DEFAULT TRUE,
  content_hash CHAR(64) NULL,
  raw_payload_json JSON NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (job_observation_id),
  UNIQUE KEY uq_job_observations_job_run (job_id, collection_run_id),
  KEY idx_job_observations_run (collection_run_id),
  KEY idx_job_observations_collected (collected_at),
  CONSTRAINT fk_job_observations_job
    FOREIGN KEY (job_id) REFERENCES jobs (job_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_job_observations_run
    FOREIGN KEY (collection_run_id) REFERENCES collection_runs (collection_run_id)
    ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- Classification and skill layer
-- ---------------------------------------------------------------------------

CREATE TABLE analysis_runs (
  analysis_run_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_key VARCHAR(96) NOT NULL,
  method VARCHAR(32) NOT NULL,
  provider VARCHAR(64) NULL,
  model_name VARCHAR(128) NULL,
  model_version VARCHAR(128) NULL,
  prompt_version VARCHAR(64) NULL,
  taxonomy_version VARCHAR(64) NULL,
  code_version VARCHAR(64) NULL,
  source_dataset_version VARCHAR(128) NULL,
  parameters_json JSON NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'pending',
  notes TEXT NULL,
  started_at DATETIME(6) NOT NULL,
  completed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (analysis_run_id),
  UNIQUE KEY uq_analysis_runs_key (run_key),
  KEY idx_analysis_runs_completed (completed_at),
  CONSTRAINT chk_analysis_method
    CHECK (method IN ('llm', 'dictionary', 'hybrid', 'manual')),
  CONSTRAINT chk_analysis_run_status
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'partial'))
) ENGINE=InnoDB;

CREATE TABLE job_analyses (
  job_analysis_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  job_id BIGINT UNSIGNED NOT NULL,
  analysis_run_id BIGINT UNSIGNED NOT NULL,
  source_row_index INT NULL,
  analysis_status VARCHAR(24) NOT NULL DEFAULT 'success',
  result_origin VARCHAR(24) NOT NULL DEFAULT 'generated',
  reused_from_job_analysis_id BIGINT UNSIGNED NULL,
  av_relevant BOOLEAN NULL,
  relevance_confidence DECIMAL(5,4) NULL,
  relevance_confidence_label VARCHAR(24) NULL,
  relevance_reason TEXT NULL,
  technical_responsibilities TEXT NULL,
  generic_job_title VARCHAR(255) NULL,
  seniority_code VARCHAR(32) NULL,
  seniority_raw VARCHAR(128) NULL,
  seniority_source VARCHAR(32) NULL,
  seniority_evidence TEXT NULL,
  seniority_conflict BOOLEAN NOT NULL DEFAULT FALSE,
  experience_min_years DECIMAL(5,1) NULL,
  experience_max_years DECIMAL(5,1) NULL,
  experience_evidence VARCHAR(1024) NULL,
  key_evidence_json JSON NULL,
  raw_response_json JSON NULL,
  import_batch_id BIGINT UNSIGNED NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (job_analysis_id),
  UNIQUE KEY uq_job_analyses_job_run (job_id, analysis_run_id),
  UNIQUE KEY uq_job_analyses_pk_run (job_analysis_id, analysis_run_id),
  KEY idx_job_analyses_run_relevance (analysis_run_id, av_relevant),
  KEY idx_job_analyses_seniority (seniority_code),
  KEY idx_job_analyses_reused_from (reused_from_job_analysis_id),
  KEY idx_job_analyses_import_batch (import_batch_id),
  CONSTRAINT fk_job_analyses_job
    FOREIGN KEY (job_id) REFERENCES jobs (job_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_job_analyses_run
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs (analysis_run_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_job_analyses_reused_from
    FOREIGN KEY (reused_from_job_analysis_id)
    REFERENCES job_analyses (job_analysis_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_job_analyses_import_batch
    FOREIGN KEY (import_batch_id) REFERENCES import_batches (import_batch_id)
    ON DELETE SET NULL,
  CONSTRAINT chk_job_analysis_status
    CHECK (analysis_status IN ('success', 'skipped', 'failed', 'manual_review')),
  CONSTRAINT chk_job_analysis_origin
    CHECK (result_origin IN ('generated', 'reused', 'manual', 'imported')),
  CONSTRAINT chk_job_analysis_reuse_source
    CHECK (
      (result_origin = 'reused' AND reused_from_job_analysis_id IS NOT NULL)
      OR (result_origin <> 'reused' AND reused_from_job_analysis_id IS NULL)
    ),
  CONSTRAINT chk_relevance_confidence
    CHECK (relevance_confidence IS NULL OR relevance_confidence BETWEEN 0 AND 1),
  CONSTRAINT chk_experience_range
    CHECK (
      experience_min_years IS NULL
      OR experience_max_years IS NULL
      OR experience_max_years >= experience_min_years
    )
) ENGINE=InnoDB;

CREATE TABLE skills (
  skill_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  canonical_name VARCHAR(191) NOT NULL,
  normalized_name VARCHAR(191) NOT NULL,
  skill_type VARCHAR(32) NOT NULL,
  description TEXT NULL,
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (skill_id),
  UNIQUE KEY uq_skills_normalized_type (normalized_name, skill_type),
  KEY idx_skills_type_name (skill_type, canonical_name),
  CONSTRAINT chk_skill_type
    CHECK (skill_type IN (
      'tool', 'domain', 'qualification', 'certification',
      'programming_language', 'soft_skill', 'other'
    ))
) ENGINE=InnoDB;

CREATE TABLE skill_aliases (
  skill_alias_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  skill_id BIGINT UNSIGNED NOT NULL,
  alias_text VARCHAR(255) NOT NULL,
  normalized_alias VARCHAR(191) NOT NULL,
  alias_source VARCHAR(64) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (skill_alias_id),
  UNIQUE KEY uq_skill_alias (skill_id, normalized_alias),
  KEY idx_skill_alias_lookup (normalized_alias),
  CONSTRAINT fk_skill_aliases_skill
    FOREIGN KEY (skill_id) REFERENCES skills (skill_id)
    ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE job_skills (
  job_analysis_id BIGINT UNSIGNED NOT NULL,
  skill_id BIGINT UNSIGNED NOT NULL,
  raw_skill_text VARCHAR(512) NULL,
  confidence DECIMAL(5,4) NULL,
  evidence TEXT NULL,
  skill_rank SMALLINT UNSIGNED NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (job_analysis_id, skill_id),
  KEY idx_job_skills_skill (skill_id, job_analysis_id),
  CONSTRAINT fk_job_skills_analysis
    FOREIGN KEY (job_analysis_id) REFERENCES job_analyses (job_analysis_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_job_skills_skill
    FOREIGN KEY (skill_id) REFERENCES skills (skill_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_job_skill_confidence
    CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- Clustering layer
-- ---------------------------------------------------------------------------

CREATE TABLE cluster_runs (
  cluster_run_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  run_key VARCHAR(96) NOT NULL,
  analysis_run_id BIGINT UNSIGNED NOT NULL,
  algorithm VARCHAR(64) NOT NULL,
  algorithm_version VARCHAR(64) NULL,
  requested_cluster_count INT NULL,
  produced_cluster_count INT NULL,
  includes_noise BOOLEAN NOT NULL DEFAULT FALSE,
  parameters_json JSON NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'pending',
  notes TEXT NULL,
  started_at DATETIME(6) NOT NULL,
  completed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (cluster_run_id),
  UNIQUE KEY uq_cluster_runs_key (run_key),
  UNIQUE KEY uq_cluster_runs_pk_analysis (cluster_run_id, analysis_run_id),
  KEY idx_cluster_runs_analysis (analysis_run_id),
  CONSTRAINT fk_cluster_runs_analysis
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs (analysis_run_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_cluster_run_status
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'partial'))
) ENGINE=InnoDB;

CREATE TABLE clusters (
  cluster_pk BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  cluster_run_id BIGINT UNSIGNED NOT NULL,
  cluster_number INT NOT NULL,
  current_label_revision_id BIGINT UNSIGNED NULL,
  cluster_name VARCHAR(255) NULL,
  job_family VARCHAR(191) NULL,
  specialisation VARCHAR(191) NULL,
  lean VARCHAR(24) NULL,
  is_noise BOOLEAN NOT NULL DEFAULT FALSE,
  size_cached INT UNSIGNED NOT NULL DEFAULT 0,
  technical_score DECIMAL(5,4) NULL,
  top_terms_json JSON NULL,
  example_titles_json JSON NULL,
  top_companies_json JSON NULL,
  notes TEXT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (cluster_pk),
  UNIQUE KEY uq_clusters_run_number (cluster_run_id, cluster_number),
  UNIQUE KEY uq_clusters_pk_run (cluster_pk, cluster_run_id),
  KEY idx_clusters_family (job_family, specialisation),
  CONSTRAINT fk_clusters_run
    FOREIGN KEY (cluster_run_id) REFERENCES cluster_runs (cluster_run_id)
    ON DELETE CASCADE,
  CONSTRAINT chk_cluster_lean
    CHECK (lean IS NULL OR lean IN ('technical', 'corporate', 'mixed', 'noise')),
  CONSTRAINT chk_cluster_technical_score
    CHECK (technical_score IS NULL OR technical_score BETWEEN 0 AND 1)
) ENGINE=InnoDB;

-- Every automatic or manual label is immutable. clusters.* label fields are
-- the approved dashboard cache and point back to one revision.
CREATE TABLE cluster_label_revisions (
  cluster_label_revision_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  cluster_pk BIGINT UNSIGNED NOT NULL,
  revision_number INT UNSIGNED NOT NULL,
  label_source VARCHAR(24) NOT NULL,
  label_status VARCHAR(24) NOT NULL DEFAULT 'proposed',
  proposed_cluster_name VARCHAR(255) NOT NULL,
  proposed_job_family VARCHAR(191) NULL,
  proposed_specialisation VARCHAR(191) NULL,
  rationale TEXT NULL,
  model_name VARCHAR(128) NULL,
  prompt_version VARCHAR(64) NULL,
  labelled_by VARCHAR(191) NULL,
  reviewed_by VARCHAR(191) NULL,
  review_notes TEXT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  reviewed_at DATETIME(6) NULL,
  PRIMARY KEY (cluster_label_revision_id),
  UNIQUE KEY uq_cluster_label_revision (cluster_pk, revision_number),
  UNIQUE KEY uq_cluster_label_revision_cluster
    (cluster_label_revision_id, cluster_pk),
  KEY idx_cluster_label_status (cluster_pk, label_status),
  CONSTRAINT fk_cluster_label_revision_cluster
    FOREIGN KEY (cluster_pk) REFERENCES clusters (cluster_pk)
    ON DELETE CASCADE,
  CONSTRAINT chk_cluster_label_source
    CHECK (label_source IN ('llm', 'manual', 'hybrid', 'imported')),
  CONSTRAINT chk_cluster_label_status
    CHECK (label_status IN ('proposed', 'reviewed', 'approved', 'rejected', 'superseded')),
  CONSTRAINT chk_cluster_label_provenance
    CHECK (
      (label_source <> 'manual' OR labelled_by IS NOT NULL)
      AND (label_source <> 'llm' OR model_name IS NOT NULL)
    ),
  CONSTRAINT chk_cluster_label_reviewer
    CHECK (
      label_status NOT IN ('reviewed', 'approved', 'rejected')
      OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
    )
) ENGINE=InnoDB;

ALTER TABLE clusters
  ADD CONSTRAINT fk_clusters_current_label
  FOREIGN KEY (current_label_revision_id, cluster_pk)
  REFERENCES cluster_label_revisions (cluster_label_revision_id, cluster_pk)
  ON DELETE RESTRICT;

CREATE TABLE job_cluster_assignments (
  job_analysis_id BIGINT UNSIGNED NOT NULL,
  analysis_run_id BIGINT UNSIGNED NOT NULL,
  cluster_run_id BIGINT UNSIGNED NOT NULL,
  cluster_pk BIGINT UNSIGNED NOT NULL,
  membership_score DECIMAL(7,6) NULL,
  distance_score DECIMAL(12,8) NULL,
  assigned_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (job_analysis_id, cluster_run_id),
  KEY idx_job_cluster_assignments_cluster (cluster_pk),
  CONSTRAINT fk_job_cluster_assignments_analysis
    FOREIGN KEY (job_analysis_id, analysis_run_id)
    REFERENCES job_analyses (job_analysis_id, analysis_run_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_job_cluster_assignments_cluster_run
    FOREIGN KEY (cluster_run_id, analysis_run_id)
    REFERENCES cluster_runs (cluster_run_id, analysis_run_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_job_cluster_assignments_cluster
    FOREIGN KEY (cluster_pk, cluster_run_id)
    REFERENCES clusters (cluster_pk, cluster_run_id)
    ON DELETE CASCADE,
  CONSTRAINT chk_cluster_membership_score
    CHECK (membership_score IS NULL OR membership_score BETWEEN 0 AND 1)
) ENGINE=InnoDB;

CREATE TABLE cluster_skills (
  cluster_pk BIGINT UNSIGNED NOT NULL,
  skill_id BIGINT UNSIGNED NOT NULL,
  skill_rank SMALLINT UNSIGNED NULL,
  score DECIMAL(12,8) NULL,
  job_frequency INT UNSIGNED NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (cluster_pk, skill_id),
  KEY idx_cluster_skills_skill (skill_id, cluster_pk),
  CONSTRAINT fk_cluster_skills_cluster
    FOREIGN KEY (cluster_pk) REFERENCES clusters (cluster_pk)
    ON DELETE CASCADE,
  CONSTRAINT fk_cluster_skills_skill
    FOREIGN KEY (skill_id) REFERENCES skills (skill_id)
    ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------------
-- Dashboard publication layer
-- ---------------------------------------------------------------------------

CREATE TABLE dashboard_releases (
  dashboard_release_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  release_key VARCHAR(96) NOT NULL,
  collection_run_id BIGINT UNSIGNED NULL,
  analysis_run_id BIGINT UNSIGNED NOT NULL,
  cluster_run_id BIGINT UNSIGNED NOT NULL,
  data_cutoff_date DATE NOT NULL,
  status VARCHAR(24) NOT NULL DEFAULT 'draft',
  published_at DATETIME(6) NULL,
  notes TEXT NULL,
  published_guard TINYINT
    GENERATED ALWAYS AS (CASE WHEN status = 'published' THEN 1 ELSE NULL END) STORED,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (dashboard_release_id),
  UNIQUE KEY uq_dashboard_release_key (release_key),
  UNIQUE KEY uq_single_published_release (published_guard),
  KEY idx_dashboard_release_runs (analysis_run_id, cluster_run_id),
  CONSTRAINT fk_dashboard_release_collection
    FOREIGN KEY (collection_run_id) REFERENCES collection_runs (collection_run_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_dashboard_release_analysis
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs (analysis_run_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_dashboard_release_cluster
    FOREIGN KEY (cluster_run_id, analysis_run_id)
    REFERENCES cluster_runs (cluster_run_id, analysis_run_id)
    ON DELETE RESTRICT,
  CONSTRAINT chk_dashboard_release_status
    CHECK (status IN ('draft', 'published', 'retired')),
  CONSTRAINT chk_dashboard_release_published_at
    CHECK (status <> 'published' OR published_at IS NOT NULL)
) ENGINE=InnoDB;
