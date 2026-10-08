from flask import Blueprint, current_app, jsonify, request


bp = Blueprint("jobs", __name__)


def _positive_int(name, default, maximum=None):
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    if maximum is not None:
        value = min(value, maximum)
    return value


@bp.get("/jobs")
def list_jobs():
    try:
        page = _positive_int("page", 1)
        page_size = _positive_int(
            "page_size",
            20,
            maximum=100,
        )

        country = request.args.get("country")
        state_region = request.args.get("state_region")
        city = request.args.get("city")
        remote_type = request.args.get("remote_type")

        country = country.strip().upper() if country else None
        state_region = state_region.strip() if state_region else None
        city = city.strip() if city else None
        remote_type = remote_type.strip().lower() if remote_type else None

        country = country or None
        state_region = state_region or None
        city = city or None
        remote_type = remote_type or None

        if country and (
            len(country) != 2
            or not country.isalpha()
        ):
            raise ValueError(
                "country must be a two-letter country code"
            )

        if (state_region or city) and not country:
            raise ValueError(
                "country is required when filtering by "
                "state_region or city"
            )

        if remote_type and remote_type not in {
            "remote",
            "hybrid",
            "onsite",
        }:
            raise ValueError(
                "remote_type must be one of: "
                "remote, hybrid, onsite"
            )

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    repository = current_app.extensions["job_repository"]

    result = repository.list_jobs(
        page=page,
        page_size=page_size,
        search=request.args.get("q"),
        company=request.args.get("company"),
        country=country,
        state_region=state_region,
        city=city,
        remote_type=remote_type,
        seniority=request.args.get("seniority"),
    )

    return jsonify(
        {
            "data": result["items"],
            "pagination": result["pagination"],
        }
    )


@bp.get("/jobs/<path:source_key>")
def job_detail(source_key):
    repository = current_app.extensions["job_repository"]
    job = repository.get_job(source_key)

    if job is None:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({"data": job})