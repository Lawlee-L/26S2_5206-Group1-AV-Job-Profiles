#!/bin/bash
# Runs once, on the very first start of the MySQL container (empty data volume),
# after 01-schema.sql and 02-views.sql. Creates the read-only user the Flask
# backend connects as. The importer/admin user (MYSQL_USER) is created by the
# official mysql image itself.
set -euo pipefail

mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<SQL
CREATE USER IF NOT EXISTS '${BACKEND_DB_USER}'@'%' IDENTIFIED BY '${BACKEND_DB_PASSWORD}';
GRANT SELECT ON av_job_profiles.* TO '${BACKEND_DB_USER}'@'%';
FLUSH PRIVILEGES;
SQL
