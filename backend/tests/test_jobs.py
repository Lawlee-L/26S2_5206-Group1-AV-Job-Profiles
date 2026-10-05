from urllib.parse import quote


def test_list_jobs(client):
    response = client.get("/api/jobs")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["pagination"]["total"] == 1
    assert payload["data"][0]["title"] == "Perception Engineer"


def test_rejects_invalid_page(client):
    response = client.get("/api/jobs?page=zero")

    assert response.status_code == 400
    assert "integer" in response.get_json()["error"]


def test_job_detail(client):
    source_key = quote("greenhouse|example|id:123", safe="")
    response = client.get(f"/api/jobs/{source_key}")

    assert response.status_code == 200
    assert response.get_json()["data"]["company"] == "Example AV"


def test_missing_job_returns_404(client):
    response = client.get("/api/jobs/not-a-real-job")

    assert response.status_code == 404
