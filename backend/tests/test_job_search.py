import app.repositories.jobs as jobs_module
from app.repositories.jobs import JobRepository


def test_skill_search_uses_distinct_release_job_join(monkeypatch):
    repository = JobRepository()

    calls = []

    def fake_fetch_one(query, params):
        calls.append(("one", query, params))
        return {"total": 0}

    def fake_fetch_all(query, params=None):
        calls.append(("all", query, params))
        return []

    monkeypatch.setattr(jobs_module, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(jobs_module, "fetch_all", fake_fetch_all)

    repository.list_jobs(
        search="Python",
        page=1,
        page_size=20,
    )

    count_query = calls[0][1]
    page_query = calls[1][1]

    for query in (count_query, page_query):
        assert "SELECT DISTINCT" in query
        assert "dashboard_release_id" in query
        assert "job_id" in query
        assert "skill_matches" in query
        assert "v_dashboard_job_skills" in query

    assert calls[0][2][0] == "%Python%"
    assert calls[1][2][0] == "%Python%"


def test_whitespace_search_does_not_join_skill_view(monkeypatch):
    repository = JobRepository()

    calls = []

    def fake_fetch_one(query, params):
        calls.append(("one", query, params))
        return {"total": 0}

    def fake_fetch_all(query, params=None):
        calls.append(("all", query, params))
        return []

    monkeypatch.setattr(jobs_module, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(jobs_module, "fetch_all", fake_fetch_all)

    repository.list_jobs(
        search="     ",
        page=1,
        page_size=20,
    )

    count_query = calls[0][1]
    page_query = calls[1][1]

    assert "skill_matches" not in count_query
    assert "skill_matches" not in page_query
    assert "v_dashboard_job_skills" not in count_query
    assert "v_dashboard_job_skills" not in page_query


def test_skill_search_uses_same_join_for_count_and_page(monkeypatch):
    repository = JobRepository()

    queries = []

    def fake_fetch_one(query, params):
        queries.append(query)
        return {"total": 0}

    def fake_fetch_all(query, params=None):
        queries.append(query)
        return []

    monkeypatch.setattr(jobs_module, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(jobs_module, "fetch_all", fake_fetch_all)

    repository.list_jobs(
        search="ROS",
        page=2,
        page_size=10,
    )

    count_query, page_query = queries

    assert "ON skill_matches.dashboard_release_id" in count_query
    assert "ON skill_matches.dashboard_release_id" in page_query

    assert "skill_matches.job_id = j.job_id" in count_query
    assert "skill_matches.job_id = j.job_id" in page_query