from flask import Blueprint, current_app, jsonify, request
from datetime import date
from decimal import Decimal, InvalidOperation
from app.salary import CURRENCIES, PERIODS


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


def _salary_amount(name):
    raw = request.args.get(name)
    if raw is None: return None
    try:
        value = Decimal(raw)
        if not value.is_finite() or value < 0 or value > Decimal("9999999999999999.99"):
            raise ValueError()
        if value.as_tuple().exponent < -2: raise ValueError()
        return float(value)
    except (InvalidOperation, ValueError):
        raise ValueError(f"{name} must be a nonnegative amount with at most two decimal places") from None


@bp.get("/jobs")
@bp.get("/job-facets")
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
        skill = (request.args.get("skill") or "").strip() or None
        posted_after = (request.args.get("posted_after") or "").strip() or None
        if posted_after:
            if len(posted_after) != 10:
                raise ValueError("posted_after must be a date in YYYY-MM-DD format")
            try:
                posted_after = date.fromisoformat(posted_after).isoformat()
            except ValueError as exc:
                raise ValueError("posted_after must be a date in YYYY-MM-DD format") from exc

        raw_salary = request.args.get("has_salary")
        has_salary = None
        if raw_salary is not None:
            if raw_salary not in {"true", "false"}:
                raise ValueError("has_salary must be true or false")
            has_salary = raw_salary == "true"
        sort = request.args.get("sort", "newest")
        if sort not in {"newest", "oldest", "title", "company"}:
            raise ValueError("sort must be one of: newest, oldest, title, company")
        salary_currency = (request.args.get("salary_currency") or "").strip().upper() or None
        salary_period = (request.args.get("salary_period") or "").strip().lower() or None
        salary_min, salary_max = _salary_amount("salary_min"), _salary_amount("salary_max")
        if salary_currency and salary_currency not in CURRENCIES:
            raise ValueError("salary_currency must be a supported three-letter currency code")
        if salary_period and salary_period not in PERIODS:
            raise ValueError("salary_period must be hour, day, week, month or year")
        if salary_min is not None or salary_max is not None:
            if not salary_currency or not salary_period:
                raise ValueError("salary_currency and salary_period are required for numeric salary bounds")
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            raise ValueError("salary_min must not exceed salary_max")

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

    filters = dict(
        search=request.args.get("q"),
        company=request.args.get("company"),
        country=country,
        state_region=state_region,
        city=city,
        remote_type=remote_type,
        seniority=request.args.get("seniority"),
        skill=skill,
        posted_after=posted_after,
        has_salary=has_salary,
        salary_currency=salary_currency, salary_period=salary_period,
        salary_min=salary_min, salary_max=salary_max,
    )
    if request.path.endswith("/job-facets"):
        return jsonify({"data": repository.list_facets(**filters)})
    result = repository.list_jobs(page=page, page_size=page_size, sort=sort, **filters)


    return jsonify(
        {
            "data": result["items"],
            "pagination": result["pagination"],
        }
    )


@bp.get("/salary-options")
def salary_options():
    repository = current_app.extensions["job_repository"]
    return jsonify({"data": repository.list_salary_options()})


@bp.get("/jobs/<path:source_key>")
def job_detail(source_key):
    repository = current_app.extensions["job_repository"]
    job = repository.get_job(source_key)

    if job is None:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({"data": job})
