from flask import Blueprint, current_app, jsonify

bp = Blueprint("insights", __name__)


@bp.get("/insights")
def insights():
    return jsonify({"data": current_app.extensions["insights_repository"].get_insights()})
