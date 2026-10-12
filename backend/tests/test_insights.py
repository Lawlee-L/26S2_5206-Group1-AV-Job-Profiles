from app import create_app
from app.repositories.insights import build_insights, cluster_label, InsightsRepository


def dataset():
    jobs = [dict(job_id=i, source_key=f"source-{i}", advertised_job_title=f"Role {i}",
                 company_name="AV Co", is_active=i != 4, av_relevant=i != 5,
                 cluster_number=-1 if i == 3 else 25, is_noise=i == 3, release_key="release-new") for i in range(1, 6)]
    skills = [dict(job_id=i, skill_name="Python", skill_type="tool") for i in range(1, 6)]
    skills.append(dict(job_id=1, skill_name="python", skill_type="domain"))
    clusters = [dict(cluster_number=25, cluster_name=None, is_noise=False, top_terms_json='["planning","control"]'),
                dict(cluster_number=-1, cluster_name=None, is_noise=True, top_terms_json='["software"]')]
    versions = [dict(week_date="2026-09-06", classification_status="ready"),
                dict(week_date="2026-09-13", classification_status="pending"),
                dict(week_date="2026-09-25", classification_status="ready")]
    collections = [dict(week_date=row["week_date"], active_jobs=20, total_jobs=30, company_count=2, source_count=3) for row in versions]
    weekly_jobs = [dict(week_date="2026-09-06", job_id=1, is_active=True, cluster_number=10, is_noise=False),
                   dict(week_date="2026-09-25", job_id=1, is_active=True, cluster_number=25, is_noise=False),
                   dict(week_date="2026-09-25", job_id=3, is_active=True, cluster_number=-1, is_noise=True),
                   dict(week_date="2026-09-25", job_id=4, is_active=False, cluster_number=9, is_noise=False)]
    weekly_skills = [dict(week_date="2026-09-25", job_id=1, skill_name="Python", skill_type="tool"),
                     dict(week_date="2026-09-25", job_id=1, skill_name="python", skill_type="domain"),
                     dict(week_date="2026-09-25", job_id=4, skill_name="Inactive skill", skill_type="tool")]
    return jobs, skills, clusters, versions, collections, weekly_jobs, weekly_skills


def test_counts_only_active_av_distinct_jobs_and_excludes_inactive_skills():
    payload = build_insights(*dataset())
    current = payload["current"]
    assert current["jobCount"] == 3
    assert current["clusterCount"] == 1
    assert current["unclusteredJobs"] == 1
    assert current["skills"][0]["jobCount"] == 3
    assert current["skills"][0]["share"] == 100
    assert current["clusters"][0]["topSkills"][0]["jobCount"] == 2
    assert current["clusters"][0]["nameStatus"] == "provisional"
    assert current["clusters"][1]["name"] == "Unclustered AV roles"


def test_history_unknown_is_not_zero_and_cluster_numbers_not_cross_run_identity():
    history = build_insights(*dataset())["history"]
    assert history["classifiedVersionCount"] == 2
    points = history["points"]
    assert [row["clusterCount"] for row in points] == [1, None, 1]
    assert points[1]["avJobs"] is None
    assert points[2]["unclusteredShare"] == 50
    series = history["skillSeries"][0]
    assert series["name"] == "Python"
    assert [row["jobCount"] for row in series["values"]] == [0, None, 1]
    assert [row["share"] for row in series["values"]] == [0, None, 50]
    assert len(history["skillSeries"]) == 1


def test_provided_names_win_and_noise_not_named_as_a_profession():
    assert cluster_label(dict(cluster_number=25, cluster_name="Approved", label_status="approved")) == ("Approved", "approved")
    assert cluster_label(dict(cluster_number=-1, cluster_name="Engineer")) == ("Unclustered AV roles", "unclustered")
    assert cluster_label(dict(cluster_number=3, top_terms_json="invalid")) == ("Specialist skill group", "provisional")
    assert cluster_label(dict(cluster_number=3, top_terms_json='["perception", "vision"]'))[0] == "Perception & computer vision"
    assert cluster_label(dict(cluster_number=3, top_terms_json='["planning", "behavior", "learning"]'))[0] == "Behaviour planning"
    assert cluster_label(dict(cluster_number=3, top_terms_json='["simulation", "vehicle dynamics", "control"]'))[0] == "Vehicle dynamics simulation"


def test_empty_database_and_missing_skills_are_supported():
    assert build_insights([], [], [], [], [], [], [])["current"]["jobCount"] == 0
    args = list(dataset())
    args[1] = []
    assert build_insights(*args)["current"]["jobsWithoutSkills"] == 3


def test_missing_cluster_metadata_does_not_silently_drop_active_jobs():
    args = list(dataset())
    args[2] = []
    result = build_insights(*args)["current"]
    assert sum(row["jobCount"] for row in result["clusters"]) == result["jobCount"]


def test_qualifications_are_not_technical_skill_trend_choices():
    args = list(dataset())
    args[6].append(dict(week_date="2026-09-25", job_id=1, skill_name="Bachelor's degree", skill_type="qualification"))
    series = build_insights(*args)["history"]["skillSeries"]
    assert [row["name"] for row in series] == ["Python"]


def test_insights_route_supports_dependency_injection():
    class FakeRepository:
        def get_insights(self):
            return build_insights(*dataset())
    response = create_app({"TESTING": True}, insights_repository=FakeRepository()).test_client().get("/api/insights")
    assert response.status_code == 200
    assert response.json["data"]["current"]["jobCount"] == 3


def test_repository_uses_one_read_only_snapshot_and_always_closes(monkeypatch):
    from contextlib import contextmanager
    class Cursor:
        def __init__(self):
            self.index = -1
            self.closed = False
        def execute(self, sql):
            assert sql.startswith("SELECT")
            self.index += 1
        def fetchall(self):
            return dataset()[self.index]
        def close(self):
            self.closed = True
    class Connection:
        def __init__(self):
            self.reader = Cursor()
            self.rolled_back = False
        def start_transaction(self, **kwargs):
            assert kwargs == dict(isolation_level="REPEATABLE READ", consistent_snapshot=True, readonly=True)
        def cursor(self, **kwargs):
            assert kwargs == {"dictionary": True}
            return self.reader
        def rollback(self):
            self.rolled_back = True
    connection = Connection()
    @contextmanager
    def connect():
        yield connection
    monkeypatch.setattr("app.repositories.insights.database_connection", connect)
    assert InsightsRepository().get_insights()["current"]["jobCount"] == 3
    assert connection.reader.closed and connection.rolled_back
