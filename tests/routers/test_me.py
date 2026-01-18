from uuid import uuid4

from api.routers.auth import create_access_token
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


def test_get_me_rejects_invalid_uuid(client):
    response = client.get("/api/me", headers=_auth_header("not-a-uuid"))

    assert response.status_code == 401


def test_get_me_rejects_missing_user(client):
    response = client.get("/api/me", headers=_auth_header(str(uuid4())))

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
