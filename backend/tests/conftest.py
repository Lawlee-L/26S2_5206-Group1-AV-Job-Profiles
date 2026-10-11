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

    def list_companies(self):
        return [
            {
                "name": "Example AV",
                "jobCount": 3,
            },
            {
                "name": "Another AV Company",
                "jobCount": 1,
            },
        ]

    def list_skills(self):
        return [
            {
                "id": 1,
                "name": "Python",
                "type": "tool",
                "jobCount": 15,
                "companyCount": 6,
            },
            {
                "id": 2,
                "name": "C++",
                "type": "tool",
                "jobCount": 12,
                "companyCount": 5,
            },
        ]

    def list_clusters(self):
        return [
            {
                "id": 10,
                "number": 3,
                "name": "Perception and Computer Vision",
                "jobFamily": "Autonomous Systems",
                "specialisation": "Perception",
                "labelSource": "manual",
                "labelStatus": "approved",
                "labelRevisionNumber": 2,
                "labelRationale": "Jobs focus on perception systems.",
                "lean": "technical",
                "isNoise": False,
                "jobCount": 18,
                "technicalScore": 0.92,
                "topTerms": ["perception", "camera", "lidar"],
                "exampleTitles": [
                    "Perception Engineer",
                    "Computer Vision Engineer",
                ],
                "topCompanies": ["Example AV", "Another AV Company"],
                "notes": None,
            }
        ]

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

    def list_locations(self):
        return {
            "releaseId": 7,
            "releaseKey": "test-release",
            "locations": [
                {
                    "countryCode": "AU",
                    "stateRegion": "WA",
                    "city": "Perth",
                    "jobCount": 3,
                },
                {
                    "countryCode": "US",
                    "stateRegion": "CA",
                    "city": "San Francisco",
                    "jobCount": 2,
                },
            ],
            "workArrangements": [
                {
                    "value": "hybrid",
                    "jobCount": 2,
                },
                {
                    "value": "remote",
                    "jobCount": 1,
                },
            ],
        }


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
