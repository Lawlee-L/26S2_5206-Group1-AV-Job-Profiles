from av_jobs.models import JobData, JobMetadata, StandardJob, build_source_key


def test_standard_job_has_two_layers() -> None:
    source_key = build_source_key(
        platform="greenhouse",
        company="Avride",
        source_job_id="12345",
        job_url="https://example.com/jobs/12345",
        title="Software Engineer",
        location="Austin",
    )
    job = StandardJob(
        metadata=JobMetadata(
            source_id="avride_russia_greenhouse",
            platform="greenhouse",
            company="Avride",
            region="Russia",
            source_job_id="12345",
            source_key=source_key,
            collected_at="2026-09-02T00:00:00+00:00",
        ),
        data=JobData(
            advertised_job_title="Software Engineer",
            job_description="Build autonomous driving software.",
            job_url="https://example.com/jobs/12345",
            location="Austin",
            salary=None,
            date_posted="2026-09-01",
        ),
    )

    result = job.to_dict()
    assert set(result) == {"metadata", "data"}
    assert result["metadata"]["source_key"] == "greenhouse|avride|id:12345"
    assert set(result["data"]) == {
        "advertised_job_title",
        "job_description",
        "job_url",
        "location",
        "salary",
        "date_posted",
    }

