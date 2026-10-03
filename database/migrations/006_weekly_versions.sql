-- Apply only to an existing Stage 3 database after a verified backup.
-- Duplicate collection dates intentionally fail the primary-key insert: a
-- human must choose the official file, not let migration order choose one.
ALTER TABLE analysis_runs
  ADD UNIQUE KEY uq_analysis_collection_pair (analysis_run_id, collection_run_id);

CREATE TABLE weekly_versions (
  week_date DATE NOT NULL,
  collection_run_id BIGINT UNSIGNED NOT NULL,
  selected_analysis_run_id BIGINT UNSIGNED NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
    ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (week_date),
  UNIQUE KEY uq_weekly_collection (collection_run_id),
  UNIQUE KEY uq_weekly_analysis (selected_analysis_run_id),
  KEY idx_weekly_analysis_pair (selected_analysis_run_id, collection_run_id),
  CONSTRAINT fk_weekly_collection
    FOREIGN KEY (collection_run_id) REFERENCES collection_runs (collection_run_id)
    ON DELETE RESTRICT,
  CONSTRAINT fk_weekly_analysis_pair
    FOREIGN KEY (selected_analysis_run_id, collection_run_id)
    REFERENCES analysis_runs (analysis_run_id, collection_run_id)
    ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Only a currently published, QA-checked analysis is selected automatically.
-- An imported draft is not silently declared the week's official result.
INSERT INTO weekly_versions (week_date, collection_run_id, selected_analysis_run_id)
SELECT cr.snapshot_as_of_date, cr.collection_run_id, dr.analysis_run_id
FROM collection_runs AS cr
LEFT JOIN dashboard_releases AS dr
  ON dr.collection_run_id = cr.collection_run_id AND dr.status = 'published'
WHERE cr.snapshot_as_of_date IS NOT NULL;
