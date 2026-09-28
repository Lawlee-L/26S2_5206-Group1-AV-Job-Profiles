from flask import Blueprint, jsonify

from app.db import ping_database


bp = Blueprint("health", __name__)


@bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "av-job-backend"})


@bp.get("/health/db")
def database_health():
    try:
        ping_database()
        return jsonify({"status": "ok", "database": "reachable"})
    except Exception:
        # Do not leak credentials, hostnames, or low-level database errors publicly.
        return jsonify({"status": "error", "database": "unreachable"}), 503
