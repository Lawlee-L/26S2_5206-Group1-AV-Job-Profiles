"""Stable domain errors surfaced to any importer front end."""


class ImportErrorSafe(RuntimeError):
    """An input or state failed a safety check; no partial import is allowed."""
