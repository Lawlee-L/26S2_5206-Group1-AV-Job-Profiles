# Database importer: validate, import, back up, QA and publish (weekly_import.py)
#
# Built on the official MySQL 8.4 image so mysqldump/mysql exactly match the
# database server. (Debian's mysql client is MariaDB's, which rejects the
# MySQL-only --set-gtid-purged option the importer uses for backups.)
FROM mysql:8.4

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN microdnf install -y python3.12 python3.12-pip \
 && microdnf clean all

# The importer resolves paths from the repository root, so mirror that layout:
#   /repo/database/...   (this folder)
WORKDIR /repo
COPY requirements-import.txt database/
RUN python3.12 -m pip install --no-cache-dir --root-user-action=ignore -r database/requirements-import.txt

COPY . database/

# Replace the MySQL server entrypoint: this image only runs the importer
ENTRYPOINT ["python3.12", "database/weekly_import.py"]
CMD ["--help"]
