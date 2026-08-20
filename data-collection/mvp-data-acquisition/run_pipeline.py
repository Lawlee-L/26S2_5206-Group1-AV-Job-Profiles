"""Command-line interface for the AV job data-acquisition MVP."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from av_jobs.orchestration import RunConfig, execute_run
from av_jobs.registry import MVP_SOURCES, MVP_SPIDERS

PROJECT_ROOT = Path(__file__).resolve().parent


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run selected company spiders, validate and clean their jobs, then "
            "build immutable Parquet and DuckDB snapshots."
        )
    )
    parser.add_argument(
        "--spiders",
        default="mvp",
        help="Comma-separated spider names, or 'mvp' for all verified sources.",
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=0,
        help=(
            "Maximum jobs per source; 0 collects all. Sampled runs never update "
            "the latest manifest."
        ),
    )
    parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Build and verify outputs without updating the latest manifest.",
    )
    parser.add_argument("--run-id", help="Optional explicit run ID for testing.")
    parser.add_argument("--data-root", type=Path, default=PROJECT_ROOT / "data")
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "output")
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default="INFO",
    )
    parser.add_argument(
        "--list-spiders", action="store_true", help="List the implementation MVP."
    )
    return parser.parse_args()


def _select_spiders(value: str) -> tuple[str, ...]:
    """Resolve the friendly ``mvp`` alias and reject unknown spider names."""

    if value.strip().lower() == "mvp":
        return MVP_SPIDERS
    names = tuple(
        dict.fromkeys(name.strip() for name in value.split(",") if name.strip())
    )
    if not names:
        raise ValueError("Select at least one spider")
    unknown = sorted(set(names) - set(MVP_SPIDERS))
    if unknown:
        raise ValueError(
            f"Unknown or non-MVP spider(s): {', '.join(unknown)}. "
            f"Available: {', '.join(MVP_SPIDERS)}"
        )
    return names


def main() -> int:
    """Parse CLI options, execute the workflow and print its JSON summary."""

    args = _parse_args()
    if args.list_spiders:
        for source in MVP_SOURCES:
            print(
                f"{source.spider:20} {source.platform:10} {source.company} "
                f"(Issue #{source.investigation_issue}, {source.region})"
            )
        return 0
    if args.max_jobs < 0:
        raise SystemExit("--max-jobs must be zero or a positive integer")

    try:
        spider_names = _select_spiders(args.spiders)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    run_id = args.run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    outcome = execute_run(
        RunConfig(
            project_root=PROJECT_ROOT,
            data_root=args.data_root.resolve(),
            output_root=args.output_root.resolve(),
            run_id=run_id,
            spider_names=spider_names,
            max_jobs=args.max_jobs,
            no_publish=args.no_publish,
            log_level=args.log_level,
        )
    )
    print(json.dumps(outcome.summary, indent=2, ensure_ascii=False, default=str))
    return outcome.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
