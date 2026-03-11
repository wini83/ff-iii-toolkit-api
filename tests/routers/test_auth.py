from datetime import UTC, datetime, timedelta
from uuid import uuid4

from api.routers.auth import create_access_token, create_refresh_token
from services.db.models import AuditLogORM, UserPasswordSetTokenORM
from services.db.passwords import hash_password, verify_password
from services.db.repository import UserRepository
from services.password_set_tokens import hash_password_set_token
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


def test_auth_token_rejects_unknown_user(client):
    response = client.post(
        "/api/auth/token",
        data={"username": "missing", "password": "pass"},
    )

    assert response.status_code == 401


def test_auth_token_rejects_invalid_password(client, db):
    repo = UserRepository(db)
    repo.create(
        username="user",
        password_hash=hash_password("pass"),
        is_superuser=False,
    )

    response = client.post(
        "/api/auth/token",
        data={"username": "user", "password": "bad"},
    )

    assert response.status_code == 401


def test_auth_refresh_rejects_missing_cookie(client):
    response = client.post("/api/auth/refresh")

    assert response.status_code == 401


def test_auth_refresh_rejects_access_token(client):
    token = create_access_token(str(uuid4()))
    client.cookies.set(settings.REFRESH_COOKIE_NAME, token)

    response = client.post("/api/auth/refresh")

    assert response.status_code == 401


def test_set_password_happy_path_consumes_token_and_clears_flag(client, db):
    repo = UserRepository(db)
    user = repo.create(
        username="invite-user",
        password_hash=hash_password("temporary"),
        must_change_password=True,
    )
    raw_token = "invite-token"
    token = UserPasswordSetTokenORM(
        user_id=user.id,
        token_hash=hash_password_set_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db.add(token)
    db.commit()

    response = client.post(
        "/api/auth/set-password",
        json={"token": raw_token, "new_password": "new-secret"},
    )

    assert response.status_code == 204
    updated = repo.get_by_id(user.id)
    assert updated is not None
    assert updated.must_change_password is False
    assert updated.password_changed_at is not None
    assert verify_password("new-secret", updated.password_hash)

    stored_token = db.get(UserPasswordSetTokenORM, token.id)
    assert stored_token is not None
    assert stored_token.used_at is not None

    audit = (
        db.query(AuditLogORM)
        .filter(
            AuditLogORM.action == "user.password.set",
            AuditLogORM.target_id == user.id,
        )
        .one_or_none()
    )
    assert audit is not None
    assert audit.meta == {"by_token": True}


def test_set_password_rejects_expired_token(client, db):
    repo = UserRepository(db)
    user = repo.create(
        username="expired-user",
        password_hash=hash_password("temporary"),
        must_change_password=True,
    )
    db.add(
        UserPasswordSetTokenORM(
            user_id=user.id,
            token_hash=hash_password_set_token("expired-token"),
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
    )
    db.commit()

    response = client.post(
        "/api/auth/set-password",
        json={"token": "expired-token", "new_password": "new-secret"},
    )

    assert response.status_code == 400


def test_set_password_rejects_used_token(client, db):
    repo = UserRepository(db)
    user = repo.create(
        username="used-user",
        password_hash=hash_password("temporary"),
        must_change_password=True,
    )
    db.add(
        UserPasswordSetTokenORM(
            user_id=user.id,
            token_hash=hash_password_set_token("used-token"),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            used_at=datetime.now(UTC),
        )
    )
    db.commit()

    response = client.post(
        "/api/auth/set-password",
        json={"token": "used-token", "new_password": "new-secret"},
    )

    assert response.status_code == 400


def test_set_password_rejects_too_short_password(client, db):
    repo = UserRepository(db)
    user = repo.create(
        username="short-password-user",
        password_hash=hash_password("temporary"),
        must_change_password=True,
    )
    db.add(
        UserPasswordSetTokenORM(
            user_id=user.id,
            token_hash=hash_password_set_token("short-token"),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    db.commit()

    response = client.post(
        "/api/auth/set-password",
        json={"token": "short-token", "new_password": "123"},
    )

    assert response.status_code == 422
