import json
from collections import defaultdict
import pytest

from app.salary import project_salary, matches_salary
from app.repositories.jobs import JobRepository


@pytest.mark.parametrize("raw, lo, hi, code, period", [
    ("想定月収 / Estimated Monthly Salary：483,334円 ~ 1,375,000円\nBase Monthly Salary: 350,000円 ~ 999,999円\nFixed overtime 45 hours 133,334円", 483334, 1375000, "JPY", "month"),
    ("USD 90000-120000 per per-year-salary", 90000, 120000, "USD", "year"),
    ("USD 75k—300k per year", 75000, 300000, "USD", "year"),
    ("The minimum salary is 2738,10 EUR gross per month.", 2738.10, None, "EUR", "month"),
    ("GBP 12.50 to 15.75 per hour", 12.5, 15.75, "GBP", "hour"),
    ("Annual salary is USD 130,000.", 130000, 130000, "USD", "year"),
    ("up to EUR 4,000 per month", None, 4000, "EUR", "month"),
    ("$216.8K – $318K", 216800, 318000, None, None),
    ("USD 0-100 per hour", 0, 100, "USD", "hour"),
    ("Salary EUR 2.738,10 per month", 2738.10, 2738.10, "EUR", "month"),
    ("時給1,500円", 1500, 1500, "JPY", "hour"),
])
def test_primary_salary(raw, lo, hi, code, period):
    result = project_salary(raw)
    assert (result.minimum, result.maximum, result.currency, result.period) == (lo, hi, code, period)


@pytest.mark.parametrize("raw", [None, "Negotiable", "45 hours, 20 days of leave",
    "USD 300-100 annually", "USD 100-200 / year; EUR 200-300 / month",
    "San Jose USD 100-200 annually; Austin USD 80-150 annually",
    "USD 1.234 per month", "USD 20 per hour plus USD 500 bonus",
    "USD 1e6 per year", "USD 12,34,567 per year",
    "USD 100000 annually with 5-10 years of experience",
])
def test_ambiguous_salaries_not_collapsed(raw):
    result = project_salary(raw)
    assert result.minimum is None and result.maximum is None


def test_annual_bonus_does_not_establish_salary_period():
    result = project_salary("USD 165,000 - 185,000 along with an annual corporate bonus")
    assert result.minimum == 165000 and result.period is None


def test_single_location_salary_retains_qualification():
    result = project_salary("San Jose, California, US: $75k—$300k USD")
    assert result.minimum == 75000 and result.maximum == 300000
    assert result.qualifier == "San Jose, California, US" and result.period is None


def test_existing_fields_take_precedence_and_single_bound_is_not_invented():
    result = project_salary("USD 999 annually", 100, None, "EUR", "month")
    assert result.minimum == 100 and result.maximum is None
    assert not matches_salary(result, currency="EUR", period="month", minimum=150)
    assert matches_salary(result, currency="EUR", period="month", maximum=100)


def test_overlap_is_inclusive_and_never_converts_currency_or_period():
    result = project_salary("JPY 100-200 monthly")
    assert matches_salary(result, currency="JPY", period="month", minimum=200)
    assert not matches_salary(result, currency="USD", period="year", minimum=100)
    assert not matches_salary(result, currency="JPY", period="month", minimum=201)


@pytest.mark.parametrize("query", ["salary_min=NaN", "salary_min=Infinity", "salary_min=-1",
    "salary_min=1.001", "salary_max=1e100", "salary_min=100", "salary_currency=XYZ",
    "salary_period=annual", "salary_currency=USD&salary_period=year&salary_min=200&salary_max=100"])
def test_bad_salary_requests(client, query):
    assert client.get("/api/jobs?" + query).status_code == 400


def test_salary_filters_forwarded(client):
    repository = client.application.extensions["job_repository"]
    captured = {}
    def capture(**kwargs):
        captured.update(kwargs)
        return {"items": [], "pagination": {}}
    repository.list_jobs = capture
    assert client.get("/api/jobs?salary_currency=jpy&salary_period=month&salary_min=0&salary_max=500000").status_code == 200
    assert captured["salary_min"] == 0 and captured["salary_max"] == 500000
    assert captured["salary_currency"] == "JPY" and captured["salary_period"] == "month"
    assert client.get("/api/salary-options").json["data"]["options"][0]["currency"] == "JPY"


def test_normalized_api_preserves_source():
    raw = "想定月収 / Estimated Monthly Salary: 483,334円 ~ 1,375,000円"
    row = defaultdict(lambda: None, {"salary_raw": raw})
    api = JobRepository._job_to_api(row, [])
    assert api["salary"] == raw
    assert (api["salaryMin"], api["salaryMax"], api["salaryCurrency"], api["salaryPeriod"]) == (483334, 1375000, "JPY", "month")
    assert api["salaryNormalization"]["version"] == "salary-v1"


def test_filter_pair_join_is_release_scoped_and_parameter_order(monkeypatch):
    repository = JobRepository()
    monkeypatch.setattr(repository, "_salary_rows", lambda: [
        {"dashboard_release_id": 7, "job_id": 101, "salary_raw": "USD 100-200 annually"},
        {"dashboard_release_id": 8, "job_id": 101, "salary_raw": "JPY 100-200 monthly"},
    ])
    join, where, params = repository._build_filters(search="engineer", company="Example", country=None,
        state_region=None, city=None, remote_type=None, seniority=None, skill="Python",
        salary_currency="USD", salary_period="year", salary_min=150)
    assert json.loads(params[2]) == [[7, 101]]
    assert "salary_matches.release_id = j.dashboard_release_id" in join
    assert (join + where).count("%s") == len(params)
    assert params[:2] == ["%engineer%", "Python"]


def test_empty_match_join_and_salary_options(monkeypatch):
    repository = JobRepository()
    monkeypatch.setattr(repository, "_salary_rows", lambda: [
        {"dashboard_release_id": 7, "job_id": 1, "salary_raw": "JPY 100-200 monthly"},
        {"dashboard_release_id": 7, "job_id": 2, "salary_raw": "$100-200"},
    ])
    options = repository.list_salary_options()
    assert options["options"] == [{"currency": "JPY", "period": "month", "jobCount": 1}]
    assert options["numericJobCount"] == 2 and options["comparableJobCount"] == 1
    _, _, params = repository._build_filters(search=None, company=None, country=None,
        state_region=None, city=None, remote_type=None, seniority=None, salary_currency="GBP")
    assert params == ["[]"]
