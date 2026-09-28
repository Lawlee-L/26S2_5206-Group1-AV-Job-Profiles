from flask import Flask, jsonify
from flask_cors import CORS

from app.config import Config
from app.repositories.jobs import JobRepository
from app.routes.health import bp as health_bp
from app.routes.jobs import bp as jobs_bp


def create_app(config_overrides=None, job_repository=None):

    app = Flask(__name__)
    app.config.from_object(Config)

    if config_overrides:
        app.config.update(config_overrides)

    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
    )

    app.extensions["job_repository"] = job_repository or JobRepository()

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(jobs_bp, url_prefix="/api")

    @app.errorhandler(500)
    def internal_error(_error):
        return jsonify({"error": "Internal server error"}), 500

    return app
