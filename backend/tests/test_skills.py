def test_list_skills(client):
    response = client.get("/api/skills")

    assert response.status_code == 200

    payload = response.get_json()

    assert len(payload["data"]) == 2

    first_skill = payload["data"][0]

    assert first_skill["id"] == 1
    assert first_skill["name"] == "Python"
    assert first_skill["type"] == "tool"
    assert first_skill["jobCount"] == 15
    assert first_skill["companyCount"] == 6