from __future__ import annotations

import argparse
from collections import Counter

from av_jobs.config import DEFAULT_CONFIG_PATH, load_sources
from av_jobs.pipeline import run_pipeline
from av_jobs.storage import rebuild_job_history
from av_jobs.weekly import run_weekly_workflow


def check_config() -> int:
    sources = load_sources()
    platform_counts = Counter(source.platform for source in sources)

    print(f"Configuration: {DEFAULT_CONFIG_PATH}")
    print(f"Ready sources: {len(sources)}")
    print("Platforms:")
    for platform, count in sorted(platform_counts.items()):
        print(f"  {platform}: {count}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="av-jobs")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("check-config", help="Validate the In Scope sheet")
    subparsers.add_parser("build-history", help="Combine all dated jobs.json snapshots")
    collect_parser = subparsers.add_parser("collect", help="Collect and standardize jobs")
    collect_parser.add_argument("--platform")
    collect_parser.add_argument("--source-id")
    collect_parser.add_argument("--run-date")
    weekly_parser = subparsers.add_parser(
        "weekly-update",
        help="Collect, translate, validate, and create the weekly deliverable",
    )
    weekly_parser.add_argument("--region", required=True)
    weekly_parser.add_argument("--run-date")
    weekly_parser.add_argument("--endpoint")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "check-config":
        return check_config()
    if args.command == "build-history":
        history_path = rebuild_job_history()
        print(f"History: {history_path}")
        return 0
    if args.command == "collect":
        jobs, results, output_path = run_pipeline(
            platform=args.platform,
            source_id=args.source_id,
            run_date=args.run_date,
        )
        for result in results:
            suffix = f" ({result.error})" if result.error else ""
            print(f"{result.source_id}: {result.status}, {result.job_count} jobs{suffix}")
        print(f"Standardized jobs: {len(jobs)}")
        print(f"Output: {output_path}")
        return 0 if all(result.status != "failed" for result in results) else 1
    if args.command == "weekly-update":
        options = {
            "region": args.region,
            "run_date": args.run_date,
        }
        if args.endpoint:
            options["endpoint"] = args.endpoint
        run_weekly_workflow(**options)
        return 0
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
