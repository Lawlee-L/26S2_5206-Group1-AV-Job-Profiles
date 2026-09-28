from flask import Blueprint, current_app, jsonify


bp = Blueprint("skills", __name__)


@bp.get("/skills")
def list_skills():
    repository = current_app.extensions["job_repository"]
    skills = repository.list_skills()

    return jsonify({"data": skills})