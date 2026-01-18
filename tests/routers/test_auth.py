from uuid import uuid4

from api.routers.auth import create_refresh_token
from services.db.passwords import hash_password
from services.db.repository import UserRepository
from settings import settings


def test_auth_token_happy_path(client, db):
    repo = UserRepository(db)

    repo.create(
        username="user",
        password_hash=hash_password("pass"),
        is_superuser=False,
    )

    response = client.post(
        "/api/auth/token",
        data={"username": "user", "password": "pass"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_auth_refresh_happy_path(client):
    user_id = str(uuid4())

    token = create_refresh_token(user_id)
    client.cookies.set(settings.REFRESH_COOKIE_NAME, token)

    response = client.post("/api/auth/refresh")

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
