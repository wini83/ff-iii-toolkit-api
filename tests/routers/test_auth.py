from api.routers import auth as auth_router
from settings import settings


def test_auth_token_happy_path(client, monkeypatch):
    monkeypatch.setattr(auth_router, "USERS", {"user": "pass"})
    response = client.post(
        "/api/auth/token",
        data={"username": "user", "password": "pass"},
    )
    assert response.status_code == 200


def test_auth_refresh_happy_path(client):
    token = auth_router.create_refresh_token("user")
    client.cookies.set(settings.REFRESH_COOKIE_NAME, token)
    response = client.post("/api/auth/refresh")
    assert response.status_code == 200
