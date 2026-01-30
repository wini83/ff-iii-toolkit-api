from api.routers.auth import create_access_token
from services.db.models import AuditLogORM
from services.db.repository import UserRepository


def _auth_header(user_id: str) -> dict[str, str]:
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def _create_superuser(db, username: str = "admin"):
    repo = UserRepository(db)
    return repo.create(
        username=username,
        password_hash="hashed",
        is_superuser=True,
    )


def _find_audit_log(db, *, action: str, actor_id, target_id):
    return (
        db.query(AuditLogORM)
        .filter(
            AuditLogORM.action == action,
            AuditLogORM.actor_id == actor_id,
            AuditLogORM.target_id == target_id,
        )
        .one_or_none()
    )


def test_list_users_happy_path(client, db):
    repo = UserRepository(db)
    superuser = _create_superuser(db)
    repo.create(username="user1", password_hash="hashed", is_superuser=False)
    repo.create(username="user2", password_hash="hashed", is_superuser=False)

    response = client.get("/api/users", headers=_auth_header(str(superuser.id)))

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    usernames = {user["username"] for user in body}
    assert {"admin", "user1", "user2"} <= usernames


def test_list_users_rejects_non_superuser(client, db):
    repo = UserRepository(db)
    user = repo.create(
        username="regular",
        password_hash="hashed",
        is_superuser=False,
    )

    response = client.get("/api/users", headers=_auth_header(str(user.id)))

    assert response.status_code == 403


def test_create_user_happy_path(client, db):
    superuser = _create_superuser(db)

    response = client.post(
        "/api/users",
        json={
            "username": "new-user",
            "password": "secret",
            "is_superuser": False,
        },
        headers=_auth_header(str(superuser.id)),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "new-user"
    assert body["is_superuser"] is False
    assert body["is_active"] is True

    repo = UserRepository(db)
    stored = repo.get_by_username("new-user")
    assert stored is not None
    assert stored.password_hash != "secret"

    # 🔍 AUDIT LOG
    log = _find_audit_log(
        db,
        action="user.create",
        actor_id=superuser.id,
        target_id=stored.id,
    )
    assert log is not None


def test_disable_user_happy_path(client, db):
    repo = UserRepository(db)
    superuser = _create_superuser(db)
    target = repo.create(
        username="target",
        password_hash="hashed",
        is_superuser=False,
    )

    response = client.post(
        f"/api/users/{target.id}/disable",
        headers=_auth_header(str(superuser.id)),
    )

    assert response.status_code == 204
    user = repo.get_by_id(target.id)
    assert user is not None
    assert user.is_active is False

    log = _find_audit_log(
        db,
        action="user.disable",
        actor_id=superuser.id,
        target_id=target.id,
    )
    assert log is not None


def test_promote_user_happy_path(client, db):
    repo = UserRepository(db)
    superuser = _create_superuser(db)
    target = repo.create(
        username="target",
        password_hash="hashed",
        is_superuser=False,
    )

    response = client.post(
        f"/api/users/{target.id}/promote",
        headers=_auth_header(str(superuser.id)),
    )

    assert response.status_code == 204
    user = repo.get_by_id(target.id)
    assert user is not None
    assert user.is_superuser is True

    log = _find_audit_log(
        db,
        action="user.promote",
        actor_id=superuser.id,
        target_id=target.id,
    )
    assert log is not None
