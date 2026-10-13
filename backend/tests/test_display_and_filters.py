import pytest
from collections import defaultdict

from app.display import display_text
from app.repositories.jobs import JobRepository


@pytest.mark.parametrize("value, expected", [
    (None, None), ("   ", None),
    ("<p>Tokyo</p><p>Japan</p>", "Tokyo\nJapan"),
    ("&lt;p&gt;USD 100,000 &amp; benefits&lt;/p&gt;", "USD 100,000 & benefits"),
    ("<script>alert(1)</script><p>Safe salary</p>", "Safe salary"),
    ("10 < 20", "10 < 20"),
])
def test_display_fields_are_plain_text(value, expected):
    assert display_text(value) == expected


def test_api_display_does_not_rewrite_raw_fields():
    row = defaultdict(lambda: None, {
        "location_raw": "<p>Tokyo</p><p>Japan</p>",
        "salary_raw": "<p>JPY 500,000 per month</p>",
    })
    result = JobRepository._job_to_api(row, [])
    assert result["location"] == row["location_raw"]
    assert result["salary"] == row["salary_raw"]
    assert result["locationDisplay"] == "Tokyo\nJapan"
    assert result["salaryDisplay"] == "JPY 500,000 per month"


@pytest.mark.parametrize("query", [
    "posted_after=2026-13-01", "posted_after=20260901", "posted_after=2026-02-30",
    "has_salary=yes", "sort=salary_desc", "sort=title%3BDROP",
])
def test_rejects_invalid_extra_filters(client, query):
    assert client.get(f"/api/jobs?{query}").status_code == 400


def test_extra_filters_forwarded_to_repository(client):
    repository = client.application.extensions["job_repository"]
    captured = {}
    original = repository.list_jobs
    def capture(**kwargs):
        captured.update(kwargs)
        return original(**kwargs)
    repository.list_jobs = capture
    response = client.get("/api/jobs?country=us&city=Perth&skill=C%2B%2B&posted_after=2026-09-01&has_salary=false&sort=title")
    assert response.status_code == 200
    assert captured["country"] == "US"
    assert captured["skill"] == "C++"
    assert captured["posted_after"] == "2026-09-01"
    assert captured["has_salary"] is False
    assert captured["sort"] == "title"


def test_new_filters_are_parameterised_and_release_scoped():
    repository = JobRepository()
    join, sql, params = repository._build_filters(
        search=None, company=None, country=None, state_region=None, city=None,
        remote_type=None, seniority=None, skill="Python' OR 1=1 --",
        posted_after="2026-09-01", has_salary=False,
    )
    assert "Python'" not in sql
    assert "selected_skill.dashboard_release_id = j.dashboard_release_id" in join
    assert "selected_skill.job_id = j.job_id" in join
    assert "SELECT DISTINCT" in join
    assert "j.date_posted >= %s" in sql
    assert "NOT (NULLIF" in sql
    assert params == ["Python' OR 1=1 --", "2026-09-01"]


def test_search_and_exact_skill_join_parameter_order():
    repository = JobRepository()
    join, sql, params = repository._build_filters(
        search="robotics", company="Kodiak", country=None, state_region=None,
        city=None, remote_type=None, seniority=None, skill="C++",
    )
    assert params == ["%robotics%", "C++", *(["%robotics%"] * 4), "Kodiak"]
    assert (join + sql).count("%s") == len(params)
