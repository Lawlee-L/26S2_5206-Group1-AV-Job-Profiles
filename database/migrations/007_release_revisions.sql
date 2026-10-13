-- One-time upgrade from migration 006, after a verified full backup.
-- No classification, collection, or frozen snapshot payload is overwritten.
-- MySQL DDL is not transactional; test on a restored copy before applying.

ALTER TABLE dashboard_releases
  ADD COLUMN parent_release_id BIGINT UNSIGNED NULL,
  ADD UNIQUE KEY uq_release_week_pair (dashboard_release_id, collection_run_id, analysis_run_id),
  ADD CONSTRAINT fk_release_parent
    FOREIGN KEY (parent_release_id) REFERENCES dashboard_releases (dashboard_release_id)
    ON DELETE RESTRICT;

ALTER TABLE weekly_versions
  ADD COLUMN selected_release_id BIGINT UNSIGNED NULL,
  ADD KEY idx_weekly_release_pair (selected_release_id, collection_run_id, selected_analysis_run_id),
  ADD CONSTRAINT fk_weekly_release_pair
    FOREIGN KEY (selected_release_id, collection_run_id, selected_analysis_run_id)
    REFERENCES dashboard_releases (dashboard_release_id, collection_run_id, analysis_run_id)
    ON DELETE RESTRICT,
  ADD CONSTRAINT chk_weekly_release_analysis
    CHECK (selected_release_id IS NULL OR selected_analysis_run_id IS NOT NULL);

CREATE TABLE release_operations (
  operation_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  action VARCHAR(24) NOT NULL,
  week_date DATE NOT NULL,
  target_release_id BIGINT UNSIGNED NOT NULL,
  previous_week_release_id BIGINT UNSIGNED NULL,
  previous_current_release_id BIGINT UNSIGNED NULL,
  next_current_release_id BIGINT UNSIGNED NULL,
  reason TEXT NOT NULL,
  actor VARCHAR(128) NOT NULL,
  backup_file VARCHAR(1024) NOT NULL,
  backup_sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  details_json JSON NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (operation_id),
  KEY idx_release_operations_week (week_date, created_at),
  CONSTRAINT fk_operation_target FOREIGN KEY (target_release_id)
    REFERENCES dashboard_releases (dashboard_release_id) ON DELETE RESTRICT,
  CONSTRAINT fk_operation_previous_week FOREIGN KEY (previous_week_release_id)
    REFERENCES dashboard_releases (dashboard_release_id) ON DELETE RESTRICT,
  CONSTRAINT fk_operation_previous_current FOREIGN KEY (previous_current_release_id)
    REFERENCES dashboard_releases (dashboard_release_id) ON DELETE RESTRICT,
  CONSTRAINT fk_operation_next_current FOREIGN KEY (next_current_release_id)
    REFERENCES dashboard_releases (dashboard_release_id) ON DELETE RESTRICT,
  CONSTRAINT chk_release_operation_action
    CHECK (action IN ('create', 'freeze_candidate', 'activate', 'reactivate', 'publish', 'freeze_legacy'))
) ENGINE=InnoDB;

-- Prefer the currently published, frozen release when it matches the selection.
UPDATE weekly_versions wv
JOIN dashboard_releases dr ON dr.collection_run_id=wv.collection_run_id
  AND dr.analysis_run_id=wv.selected_analysis_run_id
SET wv.selected_release_id=dr.dashboard_release_id
WHERE dr.status='published' AND dr.snapshot_frozen_at IS NOT NULL;

-- Otherwise only choose an unambiguous frozen historical release. If several
-- match, leave the pointer empty: an operator must explicitly activate one.
UPDATE weekly_versions wv
JOIN (
  SELECT collection_run_id,analysis_run_id,MIN(dashboard_release_id) AS release_id
  FROM dashboard_releases
  WHERE status IN ('published','retired') AND snapshot_frozen_at IS NOT NULL
  GROUP BY collection_run_id,analysis_run_id HAVING COUNT(*)=1
) sole ON sole.collection_run_id=wv.collection_run_id
  AND sole.analysis_run_id=wv.selected_analysis_run_id
SET wv.selected_release_id=sole.release_id
WHERE wv.selected_release_id IS NULL;
