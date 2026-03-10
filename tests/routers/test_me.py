from uuid import uuid4

from api.routers.auth import create_access_token, create_refresh_token
from services.db.repository import UserRepository


def _auth_header(user_id: str) -> dict[str, str]:
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def test_get_me_happy_path(client, db):
    repo = UserRepository(db)
    user = repo.create(
        username="alice",
        password_hash="hashed",
        is_superuser=False,
    )

    response = client.get("/api/me", headers=_auth_header(str(user.id)))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["username"] == "alice"
    assert body["is_active"] is True
    assert body["is_superuser"] is False


def test_get_me_accepts_access_token_cookie(client, db):
    repo = UserRepository(db)
    user = repo.create(
        username="cookie-user",
        password_hash="hashed",
        is_superuser=False,
    )
    client.cookies.set("access_token", create_access_token(str(user.id)))

    response = client.get("/api/me")

    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)


def test_get_me_prefers_header_over_cookie(client, db):
    repo = UserRepository(db)
    header_user = repo.create(
        username="header-user",
        password_hash="hashed",
        is_superuser=False,
    )
    cookie_user = repo.create(
        username="cookie-user-2",
        password_hash="hashed",
        is_superuser=False,
    )
    client.cookies.set("access_token", create_access_token(str(cookie_user.id)))

    response = client.get("/api/me", headers=_auth_header(str(header_user.id)))

    assert response.status_code == 200
    assert response.json()["id"] == str(header_user.id)


def test_get_me_rejects_invalid_uuid(client):
    response = client.get("/api/me", headers=_auth_header("not-a-uuid"))

    assert response.status_code == 401


def test_get_me_rejects_missing_user(client):
    response = client.get("/api/me", headers=_auth_header(str(uuid4())))

    assert response.status_code == 401


def test_get_me_rejects_refresh_token_cookie(client):
    client.cookies.set("access_token", create_refresh_token(str(uuid4())))

    response = client.get("/api/me")

    assert response.status_code == 401


def test_get_me_rejects_inactive_user(client, db):
    repo = UserRepository(db)
    user = repo.create(
        username="bob",
        password_hash="hashed",
        is_superuser=False,
    )
    repo.disable(user.id)

    response = client.get("/api/me", headers=_auth_header(str(user.id)))

    assert response.status_code == 403
