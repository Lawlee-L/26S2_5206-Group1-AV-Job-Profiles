from flask import Blueprint, current_app, jsonify


bp = Blueprint("companies", __name__)


@bp.get("/companies")
def list_companies():
    repository = current_app.extensions["job_repository"]
    companies = repository.list_companies()

    return jsonify({"data": companies})