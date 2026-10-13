"""Initialise an empty website database using the tracked, classified snapshots.

Run inside the importer container. No collection or AI requests are made.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys

if __package__:
    from . import weekly_import as engine
else:
    import weekly_import as engine

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = (("2026-09-25", "output_full"), ("2026-10-13", "output/2026-10-13"))


def run(*args: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "database/weekly_import.py"), *args],
                   cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Check database state without importing")
    parser.add_argument("--git-commit", help="Commit of this project checkout")
    args = parser.parse_args()
    conn = engine.db_connect()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT GET_LOCK('avjobs_website_bootstrap', 0) AS acquired")
            if cursor.fetchone()["acquired"] != 1:
                raise RuntimeError("Another website initialisation is running. Try again when it finishes.")
            cursor.execute("SELECT COUNT(*) AS n FROM dashboard_releases WHERE status='published' "
                           "AND snapshot_frozen_at IS NOT NULL")
            if cursor.fetchone()["n"]:
                print("Published data already exists. Skipping initialisation; existing data is unchanged.")
                return 0
            for table in ("collection_runs", "analysis_runs", "dashboard_releases", "jobs"):
                cursor.execute(f"SELECT COUNT(*) AS n FROM {table}")
                if cursor.fetchone()["n"]:
                    raise RuntimeError("This database contains unpublished or incomplete imports. "
                                       "Initialisation stopped without changes. Follow DOCKER.md troubleshooting "
                                       "and database/TEAM_GUIDE.md to complete the existing release.")
        if args.check_only:
            print("Database is empty and ready for initialisation.")
            return 0
        if not args.git_commit or not re.fullmatch(r"[0-9a-fA-F]{7,64}", args.git_commit):
            parser.error("Pass --git-commit with the checkout commit (see DOCKER.md).")
        # Validate BOTH pairs before the first database change.
        prepared = []
        for week, folder in SNAPSHOTS:
            source = f"data-collection/deliverables/{week}/jobs_history_translated.json"
            output = f"classification pipeline/{folder}"
            files = ["--source-input", source, "--postings", f"{output}/postings_all.json",
                     "--metadata", f"{output}/run_metadata.json",
                     "--av-summary", f"{output}/av_relevant/cluster_summary.csv",
                     "--other-summary", f"{output}/not_av_relevant/cluster_summary.csv",
                     "--duplicates", f"{output}/duplicates_removed.csv",
                     "--failures", f"{output}/llm_failures.csv"]
            run("plan-collection", "--input", source)
            run("plan-analysis", *files)
            prepared.append((week, source, files))
        for week, source, files in prepared:
            run("import-collection", "--input", source, "--week-date", week)
            run("import-analysis", *files, "--week-date", week,
                "--git-commit", args.git_commit, "--publish")
        print("Website data is ready: 2026-10-13, with 2026-09-25 available for historical trends.")
        return 0
    finally:
        conn.close()  # Also releases the initialisation lock.


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (engine.ImportErrorSafe, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Initialisation stopped: {exc}", file=sys.stderr)
        raise SystemExit(1)
