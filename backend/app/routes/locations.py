from flask import Blueprint, current_app, jsonify


bp = Blueprint("locations", __name__)


@bp.get("/locations")
def list_locations():
    repository = current_app.extensions["job_repository"]

    result = repository.list_locations()

    return jsonify({"data": result})