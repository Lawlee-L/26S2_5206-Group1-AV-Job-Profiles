def test_list_companies(client):
    response = client.get("/api/companies")

    assert response.status_code == 200

    payload = response.get_json()

    assert len(payload["data"]) == 2
    assert payload["data"][0]["name"] == "Example AV"
    assert payload["data"][0]["jobCount"] == 3