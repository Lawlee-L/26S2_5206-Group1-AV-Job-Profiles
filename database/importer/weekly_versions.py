"""Selection rules for one official collection and analysis per week date."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .errors import ImportErrorSafe


def checked_week_date(actual: date, requested: date | None) -> date:
    """The user's date selects a version; source contents must independently agree."""
    if requested is not None and requested != actual:
        raise ImportErrorSafe(
            f"Requested week {requested.isoformat()} does not match source snapshot date "
            f"{actual.isoformat()}"
        )
    return actual


def file_week_date(path: Path, latest_source_date: date, requested: date | None) -> date:
    """Use the dated deliverable folder, never the last source crawl, as week label."""
    folder_date = None
    if len(path.parent.name) == 10:
        try:
            folder_date = date.fromisoformat(path.parent.name)
        except ValueError:
            pass
    selected = checked_week_date(folder_date, requested) if folder_date else (
        requested or latest_source_date
    )
    if latest_source_date > selected:
        raise ImportErrorSafe(
            f"Week {selected.isoformat()} predates source content dated "
            f"{latest_source_date.isoformat()}"
        )
    return selected


def ensure_unselected_week(cursor: Any, week_date: date) -> None:
    cursor.execute(
        "SELECT collection_run_id FROM weekly_versions WHERE week_date=%s FOR UPDATE",
        (week_date,),
    )
    if cursor.fetchone():
        raise ImportErrorSafe(
            f"Week {week_date.isoformat()} already has an official collection file; "
            "do not silently replace it"
        )


def selected_collection(cursor: Any, week_date: date, collection_run_id: int) -> None:
    cursor.execute(
        "SELECT collection_run_id,selected_analysis_run_id FROM weekly_versions "
        "WHERE week_date=%s FOR UPDATE",
        (week_date,),
    )
    selected = cursor.fetchone()
    if selected is None:
        raise ImportErrorSafe(f"No official collection file selected for week {week_date.isoformat()}")
    if int(selected["collection_run_id"]) != int(collection_run_id):
        raise ImportErrorSafe(
            f"Classification input is not the official collection file for week {week_date.isoformat()}"
        )
    if selected["selected_analysis_run_id"] is not None:
        raise ImportErrorSafe(
            f"Week {week_date.isoformat()} already has a selected classification; "
            "a replacement requires an explicit review workflow"
        )
