import pytest
from app.facets import FacetIndex
from app.repositories.jobs import JobRepository


@pytest.fixture()
def index():
    rows = [
        dict(dashboard_release_id=7, job_id=1, company_name="Alpha", country_code="US",
             state_region="CA", city="San Jose", remote_type="hybrid", seniority_code="senior",
             advertised_job_title="C++ Engineer", date_posted="2026-09-25", salary_min=100,
             salary_max=200, salary_currency="USD", salary_period="year"),
        dict(dashboard_release_id=7, job_id=2, company_name="Beta", country_code="DE",
             state_region="Berlin", city="Berlin", remote_type="onsite", seniority_code="mid",
             advertised_job_title="Café Engineer", date_posted="2026-09-19"),
        dict(dashboard_release_id=7, job_id=3, company_name="Beta", country_code="US",
             state_region="TX", city="Austin", remote_type="remote", seniority_code="mid",
             advertised_job_title="Data Scientist", salary_min=100, salary_max=200,
             salary_currency="JPY", salary_period="month"),
    ]
    skills = [dict(dashboard_release_id=7, job_id=1, skill_name="C++"),
              dict(dashboard_release_id=7, job_id=1, skill_name="Python"),
              dict(dashboard_release_id=7, job_id=2, skill_name="Python"),
              dict(dashboard_release_id=8, job_id=1, skill_name="Wrong release")]
    return FacetIndex(rows, skills)


def values(result, field):
    return {item["value"]: item["count"] for item in result[field]}


def test_company_narrows_other_facets_but_keeps_own_alternatives(index):
    result = index.options({"company": "Alpha"})
    assert result["total"] == 1
    assert values(result, "country") == {"US": 1}
    assert values(result, "company") == {"Alpha": 1, "Beta": 2}
    assert values(result, "skill") == {"C++": 1, "Python": 1}


def test_location_hierarchy_allows_parent_changes(index):
    result = index.options(dict(company="Beta", country="US", state_region="TX", city="Austin"))
    assert result["total"] == 1
    assert values(result, "country") == {"DE": 1, "US": 1}
    assert values(result, "state_region") == {"TX": 1}
    assert values(result, "company") == {"Beta": 1}
    assert not result["skill"]


@pytest.mark.parametrize("filters,total", [
    ({"search": "Cafe"}, 1), ({"search": "Python"}, 2), ({"search": "Alpha US"}, 0),
    ({"remote_type": "remote"}, 1), ({"seniority": "mid"}, 2),
    ({"has_salary": False}, 1), ({"posted_after": "2026-09-20"}, 1),
    ({"salary_currency": "USD", "salary_period": "year", "salary_min": 150}, 1),
    ({"salary_currency": "USD", "salary_period": "year", "salary_min": 201}, 0),
    ({"skill": "Python", "country": "DE"}, 1),
])
def test_intersections(index, filters, total):
    assert index.options(filters)["total"] == total


def test_skills_exclude_own_filter_and_are_release_scoped(index):
    assert values(index.options({"skill": "Python"}), "skill") == {"Python": 2, "C++": 1}


def test_salary_unit_and_date_can_be_widened(index):
    result = index.options(dict(salary_currency="USD", salary_period="year", salary_min=150))
    assert values(result, "salary_units") == {"JPY/month": 1, "USD/year": 1}
    assert index.options({"posted_after": "2026-09-20"})["posted_range"]["minimum"] == "2026-09-19"


def test_facets_share_filter_validation(client):
    assert client.get("/api/job-facets?country=Germany").status_code == 400
    assert client.get("/api/job-facets?salary_min=10").status_code == 400
    result = client.get("/api/job-facets?country=US").get_json()["data"]
    assert result["country"] == [{"value": "US", "count": 1}]


def test_search_wildcards_are_literal():
    _, sql, params = JobRepository()._build_filters(search="C_ 10% =", company=None, country=None,
        state_region=None, city=None, remote_type=None, seniority=None)
    assert params == ["%C=_ 10=% ==%"] * 5
    assert "ESCAPE '='" in sql


def test_cache_reuses_index_and_invalidates_on_release_change(monkeypatch, client):
    from app.repositories import jobs
    head = [7]
    loads = []
    def fetch(sql, params=()):
        if "SELECT DISTINCT dashboard_release_id" in sql:
            return [{"dashboard_release_id": head[0], "release_key": str(head[0])}]
        loads.append(sql)
        if "skill_name" in sql:
            return []
        return [dict(dashboard_release_id=head[0], job_id=1, company_name="Alpha")]
    monkeypatch.setattr(jobs, "fetch_all", fetch)
    repository = JobRepository()
    with client.application.app_context():
        assert repository.list_facets()["total"] == 1
        repository.list_facets(company="Alpha")
        assert len(loads) == 2
        head[0] = 8
        assert repository.list_facets()["releaseIds"] == [8]
        assert len(loads) == 4


def test_index_load_rejects_mixed_releases(monkeypatch, client):
    from app.repositories import jobs
    checks = []
    def fetch(sql, params=()):
        if "SELECT DISTINCT dashboard_release_id" in sql:
            checks.append(1)
            return [{"dashboard_release_id": len(checks), "release_key": str(len(checks))}]
        return []
    monkeypatch.setattr(jobs, "fetch_all", fetch)
    repository = JobRepository()
    with client.application.app_context(), pytest.raises(RuntimeError, match="release changed"):
        repository.list_facets()
    assert repository._facet_cache is None


def test_case_variants_count_distinct_jobs_not_skill_rows():
    rows = [dict(dashboard_release_id=1, job_id=i, company_name="Example") for i in (1, 2)]
    skills = [dict(dashboard_release_id=1, job_id=i, skill_name=name)
              for i, name in ((1, "Python"), (1, "PYTHON"), (2, "python"))]
    index = FacetIndex(rows, skills)
    result = index.options({"skill": "python"})
    assert result["total"] == 2
    assert result["skill"] == [{"value": "Python", "count": 2}]
