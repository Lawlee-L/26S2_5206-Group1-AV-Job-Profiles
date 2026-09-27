-- Apply once to an existing database so source_key comparisons remain exact.
USE av_job_profiles;

ALTER TABLE jobs
  MODIFY source_key VARCHAR(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL;

ALTER TABLE import_rejections
  MODIFY source_key VARCHAR(191) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NULL;
