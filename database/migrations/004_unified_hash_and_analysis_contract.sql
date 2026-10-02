-- Bring an existing MySQL database to the importer/classifier field contract.
-- Safe for either the previous importer schema (SHA-256 in content_hash) or
-- the Classification-pipeline PR schema (SHA-1 in content_hash). Apply once.
USE av_job_profiles;

DROP PROCEDURE IF EXISTS m004_av_migrate_hash_columns;
DROP PROCEDURE IF EXISTS m004_av_ensure_column;
DELIMITER //
CREATE PROCEDURE m004_av_migrate_hash_columns(IN p_table VARCHAR(64))
BEGIN
  DECLARE v_hash_length INT DEFAULT NULL;
  DECLARE v_record_count INT DEFAULT 0;
  DECLARE v_record_length INT DEFAULT NULL;
  DECLARE v_sql TEXT;

  SELECT MAX(CHARACTER_MAXIMUM_LENGTH)
    INTO v_hash_length
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = p_table
     AND COLUMN_NAME = 'content_hash';

  SELECT COUNT(*), MAX(CHARACTER_MAXIMUM_LENGTH)
    INTO v_record_count, v_record_length
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = p_table
     AND COLUMN_NAME = 'record_hash_sha256';

  IF v_hash_length = 64 AND v_record_count = 0 THEN
    SET v_sql = CONCAT(
      'ALTER TABLE `', p_table,
      '` CHANGE COLUMN `content_hash` `record_hash_sha256` CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,',
      ' ADD COLUMN `content_hash` CHAR(40) CHARACTER SET ascii COLLATE ascii_bin NULL'
    );
  ELSEIF v_hash_length = 40 AND v_record_count = 0 THEN
    SET v_sql = CONCAT(
      'ALTER TABLE `', p_table,
      '` ADD COLUMN `record_hash_sha256` CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL'
    );
  ELSEIF v_hash_length = 40 AND v_record_count = 1 AND v_record_length = 64 THEN
    SET v_sql = NULL;
  ELSE
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Unexpected content_hash/record_hash_sha256 schema; inspect before migrating';
  END IF;

  IF v_sql IS NOT NULL THEN
    SET @av_migration_sql = v_sql;
    PREPARE av_stmt FROM @av_migration_sql;
    EXECUTE av_stmt;
    DEALLOCATE PREPARE av_stmt;
  END IF;
END//

CREATE PROCEDURE m004_av_ensure_column(
  IN p_table VARCHAR(64),
  IN p_column VARCHAR(64),
  IN p_definition VARCHAR(255)
)
BEGIN
  DECLARE v_count INT DEFAULT 0;
  DECLARE v_sql TEXT;

  SELECT COUNT(*) INTO v_count
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = p_table
     AND COLUMN_NAME = p_column;

  IF v_count = 0 THEN
    SET v_sql = CONCAT('ALTER TABLE `', p_table, '` ADD COLUMN `', p_column, '` ', p_definition);
    SET @av_migration_sql = v_sql;
    PREPARE av_stmt FROM @av_migration_sql;
    EXECUTE av_stmt;
    DEALLOCATE PREPARE av_stmt;
  END IF;
END//
DELIMITER ;

CALL m004_av_migrate_hash_columns('jobs');
CALL m004_av_migrate_hash_columns('job_observations');

CALL m004_av_ensure_column('analysis_runs', 'prompt_tokens', 'BIGINT UNSIGNED NULL');
CALL m004_av_ensure_column('analysis_runs', 'output_tokens', 'BIGINT UNSIGNED NULL');
CALL m004_av_ensure_column('analysis_runs', 'cost_usd', 'DECIMAL(12,6) NULL');

CALL m004_av_ensure_column('job_analyses', 'role_summary', 'TEXT NULL');
CALL m004_av_ensure_column('job_analyses', 'responsibilities_json', 'JSON NULL');
CALL m004_av_ensure_column('job_analyses', 'requirements_json', 'JSON NULL');
CALL m004_av_ensure_column('job_analyses', 'language_of_posting', 'VARCHAR(64) NULL');
CALL m004_av_ensure_column('job_analyses', 'input_content_hash',
  'CHAR(40) CHARACTER SET ascii COLLATE ascii_bin NULL');
CALL m004_av_ensure_column('job_analyses', 'served_by', 'VARCHAR(64) NULL');
CALL m004_av_ensure_column('job_analyses', 'prompt_tokens', 'INT UNSIGNED NULL');
CALL m004_av_ensure_column('job_analyses', 'output_tokens', 'INT UNSIGNED NULL');
CALL m004_av_ensure_column('job_analyses', 'cost_usd', 'DECIMAL(10,6) NULL');

-- Binary collations preserve the exact case-sensitive identifiers used by the
-- pipeline. Existing case-insensitive uniqueness becomes stricter, not broader.
ALTER TABLE jobs
  MODIFY source_job_id VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL;
ALTER TABLE analysis_runs
  MODIFY run_key VARCHAR(96) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL;
ALTER TABLE job_analyses
  MODIFY seniority_conflict BOOLEAN NULL;

DROP PROCEDURE m004_av_ensure_column;
DROP PROCEDURE m004_av_migrate_hash_columns;
