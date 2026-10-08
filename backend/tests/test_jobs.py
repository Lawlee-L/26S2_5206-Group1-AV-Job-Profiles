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


def test_accepts_country_region_city_filters(client):
    response = client.get(
        "/api/jobs?country=US&state_region=CA&city=San%20Francisco"
    )

    assert response.status_code == 200


def test_city_requires_country(client):
    response = client.get(
        "/api/jobs?city=San%20Francisco"
    )

    assert response.status_code == 400
    assert "country is required" in response.get_json()["error"]


def test_state_region_requires_country(client):
    response = client.get(
        "/api/jobs?state_region=CA"
    )

    assert response.status_code == 400
    assert "country is required" in response.get_json()["error"]


def test_rejects_invalid_country_code(client):
    response = client.get(
        "/api/jobs?country=USA"
    )

    assert response.status_code == 400
    assert "two-letter country code" in response.get_json()["error"]


def test_accepts_valid_remote_type(client):
    response = client.get(
        "/api/jobs?remote_type=hybrid"
    )

    assert response.status_code == 200


def test_rejects_invalid_remote_type(client):
    response = client.get(
        "/api/jobs?remote_type=full-time"
    )

    assert response.status_code == 400
    assert "remote_type must be one of" in response.get_json()["error"]
