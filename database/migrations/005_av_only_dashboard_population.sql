-- Separate AV and non-AV cluster identities and support AV-only public views.
-- Apply once to an existing database after taking a full backup.
USE av_job_profiles;

DROP PROCEDURE IF EXISTS m005_migrate_cluster_population;
DELIMITER //
CREATE PROCEDURE m005_migrate_cluster_population()
BEGIN
  DECLARE v_column_count INT DEFAULT 0;
  DECLARE v_bad_cluster_count INT DEFAULT 0;
  DECLARE v_old_index_count INT DEFAULT 0;
  DECLARE v_new_index_count INT DEFAULT 0;
  DECLARE v_check_count INT DEFAULT 0;
  DECLARE v_sql TEXT;

  SELECT COUNT(*) INTO v_column_count
    FROM INFORMATION_SCHEMA.COLUMNS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'clusters'
     AND COLUMN_NAME = 'population';

  IF v_column_count = 0 THEN
    ALTER TABLE clusters ADD COLUMN population VARCHAR(24) NULL AFTER cluster_run_id;
  END IF;

  UPDATE clusters AS c
  JOIN (
    SELECT jca.cluster_pk, MIN(ja.av_relevant) AS av_relevant
      FROM job_cluster_assignments AS jca
      JOIN job_analyses AS ja
        ON ja.job_analysis_id = jca.job_analysis_id
       AND ja.analysis_run_id = jca.analysis_run_id
     GROUP BY jca.cluster_pk
    HAVING COUNT(*) = COUNT(CASE
             WHEN ja.analysis_status = 'success' AND ja.av_relevant IS NOT NULL THEN 1
           END)
       AND COUNT(DISTINCT ja.av_relevant) = 1
  ) AS population_map
    ON population_map.cluster_pk = c.cluster_pk
     SET c.population = CASE
       WHEN population_map.av_relevant = 1 THEN 'av_relevant'
       ELSE 'not_av_relevant'
     END;

  SELECT COUNT(*) INTO v_bad_cluster_count
    FROM clusters AS c
    LEFT JOIN (
      SELECT jca.cluster_pk,
             COUNT(*) AS member_count,
             COUNT(CASE
               WHEN ja.analysis_status = 'success' AND ja.av_relevant IS NOT NULL THEN 1
             END) AS classified_member_count,
             COUNT(DISTINCT ja.av_relevant) AS relevance_count,
             MIN(ja.av_relevant) AS min_relevance
        FROM job_cluster_assignments AS jca
        JOIN job_analyses AS ja
          ON ja.job_analysis_id = jca.job_analysis_id
         AND ja.analysis_run_id = jca.analysis_run_id
       GROUP BY jca.cluster_pk
    ) AS members
      ON members.cluster_pk = c.cluster_pk
   WHERE c.population IS NULL
      OR members.cluster_pk IS NULL
      OR members.member_count <> members.classified_member_count
      OR members.relevance_count <> 1
      OR c.population <> CASE
           WHEN members.min_relevance = 1 THEN 'av_relevant'
           ELSE 'not_av_relevant'
         END;

  IF v_bad_cluster_count > 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Cannot assign cluster populations: clusters have missing, failed, unknown, or mixed members';
  END IF;

  SELECT COUNT(*) INTO v_old_index_count
    FROM INFORMATION_SCHEMA.STATISTICS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'clusters'
     AND INDEX_NAME = 'uq_clusters_run_number';
  SELECT COUNT(*) INTO v_new_index_count
    FROM INFORMATION_SCHEMA.STATISTICS
   WHERE TABLE_SCHEMA = DATABASE()
     AND TABLE_NAME = 'clusters'
     AND INDEX_NAME = 'uq_clusters_run_population_number';
  SELECT COUNT(*) INTO v_check_count
    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
   WHERE CONSTRAINT_SCHEMA = DATABASE()
     AND TABLE_NAME = 'clusters'
     AND CONSTRAINT_NAME = 'chk_cluster_population';

  SET v_sql = 'ALTER TABLE clusters MODIFY population VARCHAR(24) NOT NULL';
  IF v_old_index_count > 0 THEN
    SET v_sql = CONCAT(v_sql, ', DROP INDEX uq_clusters_run_number');
  END IF;
  IF v_new_index_count = 0 THEN
    SET v_sql = CONCAT(v_sql,
      ', ADD UNIQUE KEY uq_clusters_run_population_number (cluster_run_id, population, cluster_number)');
  END IF;
  IF v_check_count = 0 THEN
    SET v_sql = CONCAT(v_sql,
      ', ADD CONSTRAINT chk_cluster_population CHECK (population IN (''av_relevant'', ''not_av_relevant''))');
  END IF;

  SET @m005_sql = v_sql;
  PREPARE m005_stmt FROM @m005_sql;
  EXECUTE m005_stmt;
  DEALLOCATE PREPARE m005_stmt;
END//
DELIMITER ;

CALL m005_migrate_cluster_population();
DROP PROCEDURE m005_migrate_cluster_population;
