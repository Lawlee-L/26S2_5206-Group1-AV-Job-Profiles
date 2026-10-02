from app.repositories.jobs import JobRepository


def test_repository_defaults_to_published_views():
    repository = JobRepository()

    assert repository.view_mode == "published"
    assert repository.views["jobs"] == "v_dashboard_jobs"
    assert repository.views["job_skills"] == "v_dashboard_job_skills"
    assert repository.views["clusters"] == "v_dashboard_clusters"


def test_repository_can_use_candidate_views():
    repository = JobRepository("candidate")

    assert repository.view_mode == "candidate"
    assert repository.views["jobs"] == "v_candidate_dashboard_jobs"
    assert (
        repository.views["job_skills"]
        == "v_candidate_dashboard_job_skills"
    )
    assert (
        repository.views["clusters"]
        == "v_candidate_dashboard_clusters"
    )