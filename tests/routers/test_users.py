from datetime import UTC, datetime
from uuid import uuid4

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


def _create_audit_log(
    db,
    *,
    actor_id,
    action: str,
    target_id=None,
    meta=None,
    created_at=None,
):
    row = AuditLogORM(
        actor_id=actor_id,
        action=action,
        target_id=target_id,
        meta=meta,
        created_at=created_at or datetime.now(UTC),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


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


def test_enable_user_happy_path(client, db):
    repo = UserRepository(db)
    superuser = _create_superuser(db)
    target = repo.create(
        username="target",
        password_hash="hashed",
        is_superuser=False,
    )
    repo.disable(target.id)

    response = client.post(
        f"/api/users/{target.id}/enable",
        headers=_auth_header(str(superuser.id)),
    )

    assert response.status_code == 204
    user = repo.get_by_id(target.id)
    assert user is not None
    assert user.is_active is True

    log = _find_audit_log(
        db,
        action="user.enable",
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


def test_demote_user_happy_path(client, db):
    repo = UserRepository(db)
    superuser = _create_superuser(db)
    target = repo.create(
        username="target",
        password_hash="hashed",
        is_superuser=True,
    )

    response = client.post(
        f"/api/users/{target.id}/demote",
        headers=_auth_header(str(superuser.id)),
    )

    assert response.status_code == 204
    user = repo.get_by_id(target.id)
    assert user is not None
    assert user.is_superuser is False

    log = _find_audit_log(
        db,
        action="user.demote",
        actor_id=superuser.id,
        target_id=target.id,
    )
    assert log is not None


def test_delete_user_happy_path(client, db):
    repo = UserRepository(db)
    superuser = _create_superuser(db)
    target = repo.create(
        username="target",
        password_hash="hashed",
        is_superuser=False,
    )

    response = client.delete(
        f"/api/users/{target.id}",
        headers=_auth_header(str(superuser.id)),
    )

    assert response.status_code == 204
    user = repo.get_by_id(target.id)
    assert user is None

    log = _find_audit_log(
        db,
        action="user.delete",
        actor_id=superuser.id,
        target_id=target.id,
    )
    assert log is not None


def test_list_audit_log_rejects_non_superuser(client, db):
    repo = UserRepository(db)
    user = repo.create(
        username="regular",
        password_hash="hashed",
        is_superuser=False,
    )

    response = client.get(
        "/api/users/audit-log",
        headers=_auth_header(str(user.id)),
    )

    assert response.status_code == 403


def test_list_audit_log_pagination_and_sorting(client, db):
    superuser = _create_superuser(db)
    target_id = uuid4()

    t1 = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2024, 1, 2, 10, 0, 0, tzinfo=UTC)
    t3 = datetime(2024, 1, 3, 10, 0, 0, tzinfo=UTC)

    log1 = _create_audit_log(
        db,
        actor_id=superuser.id,
        action="user.create",
        target_id=target_id,
        meta={"note": "first"},
        created_at=t1,
    )
    log2 = _create_audit_log(
        db,
        actor_id=superuser.id,
        action="user.disable",
        target_id=target_id,
        meta={"note": "second"},
        created_at=t2,
    )
    _create_audit_log(
        db,
        actor_id=superuser.id,
        action="user.enable",
        target_id=target_id,
        meta={"note": "third"},
        created_at=t3,
    )

    response = client.get(
        "/api/users/audit-log?limit=2&offset=1",
        headers=_auth_header(str(superuser.id)),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert len(body["items"]) == 2
    assert body["items"][0]["id"] == str(log2.id)
    assert body["items"][1]["id"] == str(log1.id)


def test_list_audit_log_filters(client, db):
    superuser = _create_superuser(db)
    target_id = uuid4()

    t1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    t2 = datetime(2024, 1, 2, 12, 0, 0, tzinfo=UTC)
    t3 = datetime(2024, 1, 3, 12, 0, 0, tzinfo=UTC)

    _create_audit_log(
        db,
        actor_id=superuser.id,
        action="user.create",
        target_id=target_id,
        meta={"note": "alpha"},
        created_at=t1,
    )
    matching = _create_audit_log(
        db,
        actor_id=superuser.id,
        action="user.disable",
        target_id=target_id,
        meta={"note": "needle"},
        created_at=t2,
    )
    _create_audit_log(
        db,
        actor_id=uuid4(),
        action="user.disable",
        target_id=uuid4(),
        meta={"note": "needle"},
        created_at=t3,
    )

    response = client.get(
        "/api/users/audit-log",
        params={
            "actor_id": str(superuser.id),
            "target_id": str(target_id),
            "action": "user.disable",
            "created_from": t2.isoformat(),
            "created_to": t2.isoformat(),
            "meta_contains": "needle",
        },
        headers=_auth_header(str(superuser.id)),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(matching.id)
