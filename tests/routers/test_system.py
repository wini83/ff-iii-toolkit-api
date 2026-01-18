def test_system_ping(client):
    r = client.get("/api/system/health")
    assert r.status_code == 200


def test_system_version(client):
    r = client.get("/api/system/version")
    assert r.status_code == 200


def test_bootstrap_happy_path(client):
    r = client.post(
        "/api/system/bootstrap",
        json={"username": "admin", "password": "secret"},
    )
    assert r.status_code == 201


def test_bootstrap_only_once(client):
    client.post(
        "/api/system/bootstrap",
        json={"username": "admin", "password": "secret"},
    )
    r = client.post(
        "/api/system/bootstrap",
        json={"username": "admin2", "password": "secret"},
    )
    assert r.status_code == 409
