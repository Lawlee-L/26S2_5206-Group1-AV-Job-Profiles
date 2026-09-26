-- SQLite copy of the tables in ../schema.mysql.sql that run_pipeline_v2.py fills.
-- Table and column names match MySQL exactly, so a value in the right column here
-- is in the right column there. Types are SQLite's: ids are INTEGER PRIMARY KEY,
-- JSON and timestamps are TEXT (ISO 8601, UTC), decimals are REAL. MySQL tables
-- the pipeline does not fill (imports, collection runs, observations, label
-- revisions, skill aliases, cluster skills, dashboard releases) are left out.

CREATE TABLE IF NOT EXISTS companies (
  company_id INTEGER PRIMARY KEY,
  company_name TEXT NOT NULL UNIQUE,
  company_slug TEXT NOT NULL UNIQUE,
  website_url TEXT,
  headquarters_country_code TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_sources (
  source_id TEXT PRIMARY KEY,
  company_id INTEGER NOT NULL REFERENCES companies (company_id),
  platform TEXT NOT NULL,
  region TEXT NOT NULL,
  endpoint_url TEXT,
  is_enabled INTEGER NOT NULL DEFAULT 1,
  config_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS jobs (
  job_id INTEGER PRIMARY KEY,
  source_key TEXT NOT NULL UNIQUE,
  source_id TEXT NOT NULL REFERENCES job_sources (source_id),
  source_job_id TEXT,
  advertised_job_title TEXT,
  job_description TEXT,
  job_url TEXT,
  location_raw TEXT,
  city TEXT,
  state_region TEXT,
  country_code TEXT,
  remote_type TEXT,
  salary_raw TEXT,
  salary_min REAL,
  salary_max REAL,
  salary_currency TEXT,
  salary_period TEXT,
  date_posted TEXT,
  first_seen_date TEXT NOT NULL,
  last_seen_date TEXT NOT NULL,
  latest_collected_at TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1,
  is_new_in_latest_run INTEGER NOT NULL DEFAULT 0,
  content_hash TEXT,
  duplicate_of_job_id INTEGER REFERENCES jobs (job_id) ON DELETE SET NULL,
  duplicate_type TEXT CHECK (duplicate_type IS NULL OR duplicate_type IN ('exact', 'near')),
  duplicate_similarity REAL CHECK (duplicate_similarity IS NULL OR duplicate_similarity BETWEEN 0 AND 1),
  import_batch_id INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (source_id, source_job_id),
  CHECK (last_seen_date >= first_seen_date)
);

CREATE TABLE IF NOT EXISTS analysis_runs (
  analysis_run_id INTEGER PRIMARY KEY,
  run_key TEXT NOT NULL UNIQUE,
  method TEXT NOT NULL CHECK (method IN ('llm', 'dictionary', 'hybrid', 'manual')),
  provider TEXT,
  model_name TEXT,
  model_version TEXT,
  prompt_version TEXT,
  taxonomy_version TEXT,
  code_version TEXT,
  source_dataset_version TEXT,
  parameters_json TEXT,
  prompt_tokens INTEGER,
  output_tokens INTEGER,
  cost_usd REAL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'partial')),
  notes TEXT,
  started_at TEXT NOT NULL,
  completed_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_analyses (
  job_analysis_id INTEGER PRIMARY KEY,
  job_id INTEGER NOT NULL REFERENCES jobs (job_id) ON DELETE CASCADE,
  analysis_run_id INTEGER NOT NULL REFERENCES analysis_runs (analysis_run_id),
  source_row_index INTEGER,
  analysis_status TEXT NOT NULL DEFAULT 'success'
    CHECK (analysis_status IN ('success', 'skipped', 'failed', 'manual_review')),
  result_origin TEXT NOT NULL DEFAULT 'generated'
    CHECK (result_origin IN ('generated', 'reused', 'manual', 'imported')),
  reused_from_job_analysis_id INTEGER,
  av_relevant INTEGER,
  relevance_confidence REAL,
  relevance_confidence_label TEXT
    CHECK (relevance_confidence_label IS NULL OR relevance_confidence_label IN ('High', 'Medium', 'Low')),
  relevance_reason TEXT,
  technical_responsibilities TEXT,
  role_summary TEXT,
  responsibilities_json TEXT,
  requirements_json TEXT,
  language_of_posting TEXT,
  generic_job_title TEXT,
  seniority_code TEXT,
  seniority_raw TEXT,
  seniority_source TEXT,
  seniority_evidence TEXT,
  seniority_conflict INTEGER,
  experience_min_years REAL,
  experience_max_years REAL,
  experience_evidence TEXT,
  key_evidence_json TEXT,
  raw_response_json TEXT,
  input_content_hash TEXT,   -- hash of the text the model read; reuse needs it to match
  served_by TEXT,
  prompt_tokens INTEGER,
  output_tokens INTEGER,
  cost_usd REAL,
  import_batch_id INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (job_id, analysis_run_id),
  CHECK (experience_min_years IS NULL OR experience_max_years IS NULL
         OR experience_max_years >= experience_min_years)
);

CREATE TABLE IF NOT EXISTS skills (
  skill_id INTEGER PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  normalized_name TEXT NOT NULL,
  skill_type TEXT NOT NULL CHECK (skill_type IN (
    'tool', 'domain', 'qualification', 'certification',
    'programming_language', 'soft_skill', 'other')),
  description TEXT,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (normalized_name, skill_type)
);

CREATE TABLE IF NOT EXISTS job_skills (
  job_analysis_id INTEGER NOT NULL REFERENCES job_analyses (job_analysis_id) ON DELETE CASCADE,
  skill_id INTEGER NOT NULL REFERENCES skills (skill_id),
  raw_skill_text TEXT,
  confidence REAL,
  evidence TEXT,
  skill_rank INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (job_analysis_id, skill_id)
);

CREATE TABLE IF NOT EXISTS cluster_runs (
  cluster_run_id INTEGER PRIMARY KEY,
  run_key TEXT NOT NULL UNIQUE,
  analysis_run_id INTEGER NOT NULL REFERENCES analysis_runs (analysis_run_id),
  population TEXT NOT NULL DEFAULT 'all'
    CHECK (population IN ('all', 'av_relevant', 'not_av_relevant')),
  algorithm TEXT NOT NULL,
  algorithm_version TEXT,
  requested_cluster_count INTEGER,
  produced_cluster_count INTEGER,
  includes_noise INTEGER NOT NULL DEFAULT 0,
  parameters_json TEXT,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'partial')),
  notes TEXT,
  started_at TEXT NOT NULL,
  completed_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clusters (
  cluster_pk INTEGER PRIMARY KEY,
  cluster_run_id INTEGER NOT NULL REFERENCES cluster_runs (cluster_run_id) ON DELETE CASCADE,
  cluster_number INTEGER NOT NULL,
  current_label_revision_id INTEGER,
  cluster_name TEXT,
  job_family TEXT,
  specialisation TEXT,
  lean TEXT CHECK (lean IS NULL OR lean IN ('technical', 'corporate', 'mixed', 'noise')),
  is_noise INTEGER NOT NULL DEFAULT 0,
  size_cached INTEGER NOT NULL DEFAULT 0,
  technical_score REAL CHECK (technical_score IS NULL OR technical_score BETWEEN 0 AND 1),
  top_terms_json TEXT,
  example_titles_json TEXT,
  top_companies_json TEXT,
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (cluster_run_id, cluster_number)
);

CREATE TABLE IF NOT EXISTS job_cluster_assignments (
  job_analysis_id INTEGER NOT NULL REFERENCES job_analyses (job_analysis_id) ON DELETE CASCADE,
  analysis_run_id INTEGER NOT NULL REFERENCES analysis_runs (analysis_run_id),
  cluster_run_id INTEGER NOT NULL REFERENCES cluster_runs (cluster_run_id) ON DELETE CASCADE,
  cluster_pk INTEGER NOT NULL REFERENCES clusters (cluster_pk) ON DELETE CASCADE,
  membership_score REAL,
  distance_score REAL,
  assigned_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (job_analysis_id, cluster_run_id)
);
