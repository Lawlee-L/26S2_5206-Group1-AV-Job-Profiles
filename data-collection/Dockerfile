# Weekly job collection + Azure translation (the `av-jobs` CLI)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# Install dependencies first so code-only changes rebuild quickly
COPY pyproject.toml .
RUN pip install --no-cache-dir "langdetect>=1.0.9" "openpyxl>=3.1" "pandas>=2.2" "requests>=2.32"

# Code and the source workbook. data/ and deliverables/ are mounted at run time.
COPY src/ src/
COPY config/ config/
COPY docker-entry.py .

# The code finds config/, data/ and deliverables/ relative to /app/src/av_jobs,
# so it is run from source (PYTHONPATH) rather than pip-installed.
ENTRYPOINT ["python", "/app/docker-entry.py"]
CMD ["check-config"]
