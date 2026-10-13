from flask import Blueprint, current_app, jsonify


bp = Blueprint("clusters", __name__)


@bp.get("/clusters")
def list_clusters():
    repository = current_app.extensions["job_repository"]
    clusters = repository.list_clusters()

    return jsonify({"data": clusters})