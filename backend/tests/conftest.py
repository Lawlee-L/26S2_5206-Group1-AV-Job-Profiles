import pytest

from app import create_app


class FakeJobRepository:
    def list_jobs(self, **_kwargs):
        return {
            "items": [
                {
                    "id": "greenhouse|example|id:123",
                    "jobId": 123,
                    "sourceKey": "greenhouse|example|id:123",
                    "company": "Example AV",
                    "title": "Perception Engineer",
                    "location": "Perth, WA",
                    "skills": [{"name": "Python", "type": "tool", "confidence": 0.9, "rank": 1}],
                }
            ],
            "pagination": {"page": 1, "pageSize": 20, "total": 1, "totalPages": 1},
        }

    def get_job(self, source_key):
        if source_key == "greenhouse|example|id:123":
            return {
                "id": source_key,
                "sourceKey": source_key,
                "company": "Example AV",
                "title": "Perception Engineer",
                "skills": [],
            }
        return None


@pytest.fixture()
def client():
    app = create_app(
        {
            "TESTING": True,
            "CORS_ORIGINS": ["http://localhost:5173"],
        },
        job_repository=FakeJobRepository(),
    )
    return app.test_client()
