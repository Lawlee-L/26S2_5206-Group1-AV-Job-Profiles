-- Apply once to an existing database created before import_job_undo existed.
USE av_job_profiles;

ALTER TABLE import_batches
  DROP CHECK chk_import_batch_status,
  ADD CONSTRAINT chk_import_batch_status
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'partial', 'rolled_back'));

CREATE TABLE import_job_undo (
  import_batch_id BIGINT UNSIGNED NOT NULL,
  source_key VARCHAR(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
  change_kind VARCHAR(8) NOT NULL,
  previous_row_json JSON NULL,
  applied_row_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  PRIMARY KEY (import_batch_id, source_key),
  CONSTRAINT fk_import_job_undo_batch
    FOREIGN KEY (import_batch_id) REFERENCES import_batches (import_batch_id)
    ON DELETE CASCADE,
  CONSTRAINT chk_import_job_undo_kind
    CHECK (change_kind IN ('insert', 'update')),
  CONSTRAINT chk_import_job_undo_before
    CHECK ((change_kind = 'insert' AND previous_row_json IS NULL)
       OR (change_kind = 'update' AND previous_row_json IS NOT NULL))
) ENGINE=InnoDB;
