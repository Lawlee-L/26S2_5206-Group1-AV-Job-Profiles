-- Apply once to an existing database that does not have this table.
USE av_job_profiles;

CREATE TABLE job_deduplication_links (
  analysis_run_id BIGINT UNSIGNED NOT NULL,
  duplicate_job_id BIGINT UNSIGNED NOT NULL,
  kept_job_id BIGINT UNSIGNED NOT NULL,
  duplicate_type VARCHAR(8) NOT NULL,
  similarity DECIMAL(5,4) NOT NULL,
  source_row_index INT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (analysis_run_id, duplicate_job_id),
  KEY idx_job_deduplication_kept (analysis_run_id, kept_job_id),
  CONSTRAINT fk_job_deduplication_run
    FOREIGN KEY (analysis_run_id) REFERENCES analysis_runs (analysis_run_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_job_deduplication_duplicate
    FOREIGN KEY (duplicate_job_id) REFERENCES jobs (job_id)
    ON DELETE CASCADE,
  CONSTRAINT fk_job_deduplication_kept
    FOREIGN KEY (kept_job_id) REFERENCES jobs (job_id)
    ON DELETE CASCADE,
  CONSTRAINT chk_job_deduplication_pair
    CHECK (duplicate_job_id <> kept_job_id),
  CONSTRAINT chk_job_deduplication_type
    CHECK (duplicate_type IN ('exact', 'near')),
  CONSTRAINT chk_job_deduplication_similarity
    CHECK (similarity BETWEEN 0 AND 1)
) ENGINE=InnoDB;
