def test_system_ping(client):
    r = client.get("/api/system/health")
    assert r.status_code == 200
