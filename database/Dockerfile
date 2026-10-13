# Database importer: validate, import, back up, QA and publish (weekly_import.py)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# mysql + mysqldump clients, used for the importer's automatic backups/restores
RUN apt-get update \
 && apt-get install -y --no-install-recommends default-mysql-client \
 && rm -rf /var/lib/apt/lists/*

# The importer resolves paths from the repository root, so mirror that layout:
#   /repo/database/...   (this folder)
WORKDIR /repo
COPY requirements-import.txt database/
RUN pip install --no-cache-dir -r database/requirements-import.txt

COPY . database/

ENTRYPOINT ["python", "database/weekly_import.py"]
CMD ["--help"]
