def test_list_clusters(client):
    response = client.get("/api/clusters")

    assert response.status_code == 200

    payload = response.get_json()

    assert len(payload["data"]) == 1

    cluster = payload["data"][0]

    assert cluster["id"] == 10
    assert cluster["number"] == 3
    assert cluster["name"] == "Perception and Computer Vision"
    assert cluster["jobFamily"] == "Autonomous Systems"
    assert cluster["jobCount"] == 18
    assert cluster["isNoise"] is False
    assert cluster["topTerms"] == ["perception", "camera", "lidar"]