from api.routers.auth import create_access_token
from services.db.repository import UserRepository
from services.domain.user_secrets import SecretType


def _auth_header(user_id: str) -> dict[str, str]:
    token = create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def _create_user(db, username: str):
    repo = UserRepository(db)
    return repo.create(
        username=username,
        password_hash="hashed",
        is_superuser=False,
    )


def _setup_and_unlock_vault(client, user_id: str) -> None:
    headers = _auth_header(user_id)
    setup_response = client.post(
        "/api/user-secrets/vault/setup",
        headers=headers,
        json={"passphrase": "vault-pass"},
    )
    assert setup_response.status_code == 200

    unlock_response = client.post(
        "/api/user-secrets/vault/unlock",
        headers=headers,
        json={"passphrase": "vault-pass"},
    )
    assert unlock_response.status_code == 200


def test_vault_status_setup_unlock_and_lock_flow(client, db):
    user = _create_user(db, username="vault-owner")
    headers = _auth_header(str(user.id))

    initial_status = client.get("/api/user-secrets/vault/status", headers=headers)
    assert initial_status.status_code == 200
    assert initial_status.json() == {
        "configured": False,
        "unlocked": False,
        "expires_at": None,
    }

    setup_response = client.post(
        "/api/user-secrets/vault/setup",
        headers=headers,
        json={"passphrase": "vault-pass"},
    )
    assert setup_response.status_code == 200
    assert setup_response.json() == {
        "configured": True,
        "unlocked": False,
        "expires_at": None,
    }

    unlock_response = client.post(
        "/api/user-secrets/vault/unlock",
        headers=headers,
        json={"passphrase": "vault-pass"},
    )
    assert unlock_response.status_code == 200
    unlock_body = unlock_response.json()
    assert unlock_body["configured"] is True
    assert unlock_body["unlocked"] is True
    assert unlock_body["expires_at"] is not None
    assert "vault_session_id" in client.cookies

    unlocked_status = client.get("/api/user-secrets/vault/status", headers=headers)
    assert unlocked_status.status_code == 200
    unlocked_body = unlocked_status.json()
    assert unlocked_body["configured"] is True
    assert unlocked_body["unlocked"] is True
    assert unlocked_body["expires_at"] is not None

    lock_response = client.post("/api/user-secrets/vault/lock", headers=headers)
    assert lock_response.status_code == 200
    assert lock_response.json() == {
        "configured": True,
        "unlocked": False,
        "expires_at": None,
    }
    assert "vault_session_id" not in client.cookies


def test_vault_setup_rejects_second_configuration(client, db):
    user = _create_user(db, username="vault-owner-2")
    headers = _auth_header(str(user.id))

    _setup_and_unlock_vault(client, str(user.id))

    response = client.post(
        "/api/user-secrets/vault/setup",
        headers=headers,
        json={"passphrase": "vault-pass"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Vault already configured"}


def test_vault_unlock_rejects_invalid_passphrase(client, db):
    user = _create_user(db, username="vault-owner-3")
    headers = _auth_header(str(user.id))

    setup_response = client.post(
        "/api/user-secrets/vault/setup",
        headers=headers,
        json={"passphrase": "vault-pass"},
    )
    assert setup_response.status_code == 200

    response = client.post(
        "/api/user-secrets/vault/unlock",
        headers=headers,
        json={"passphrase": "wrong-pass"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid vault passphrase"}


def test_create_secret_requires_unlocked_vault(client, db):
    user = _create_user(db, username="secret-owner-locked")
    headers = _auth_header(str(user.id))

    setup_response = client.post(
        "/api/user-secrets/vault/setup",
        headers=headers,
        json={"passphrase": "vault-pass"},
    )
    assert setup_response.status_code == 200

    create_response = client.post(
        "/api/user-secrets",
        headers=headers,
        json={"type": SecretType.ALLEGRO.value, "secret": "s1"},
    )

    assert create_response.status_code == 423
    assert create_response.json() == {"detail": "Vault is locked"}


def test_create_secret_accepts_alias_and_lists_metadata_only(client, db):
    user = _create_user(db, username="secret-owner")
    headers = _auth_header(str(user.id))
    _setup_and_unlock_vault(client, str(user.id))

    create_response = client.post(
        "/api/user-secrets",
        headers=headers,
        json={
            "type": SecretType.ALLEGRO.value,
            "alias": "main account",
            "external_username": "market-login",
            "secret": "s1",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["type"] == SecretType.ALLEGRO.value
    assert created["alias"] == "main account"
    assert created["external_username"] == "market-login"
    assert created["usage_count"] == 0
    assert created["short_id"]
    assert "secret" not in created

    list_response = client.get("/api/user-secrets", headers=headers)

    assert list_response.status_code == 200
    listed = list_response.json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]
    assert listed[0]["alias"] == "main account"
    assert listed[0]["external_username"] == "market-login"
    assert "secret" not in listed[0]


def test_patch_secret_updates_alias_without_vault_session(client, db):
    user = _create_user(db, username="secret-owner-2")
    headers = _auth_header(str(user.id))
    _setup_and_unlock_vault(client, str(user.id))

    create_response = client.post(
        "/api/user-secrets",
        headers=headers,
        json={"type": SecretType.ALLEGRO.value, "secret": "s1"},
    )
    secret_id = create_response.json()["id"]

    client.cookies.clear()

    patch_response = client.patch(
        f"/api/user-secrets/{secret_id}",
        headers=headers,
        json={"alias": "renamed", "external_username": "new-login"},
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["alias"] == "renamed"
    assert patch_response.json()["external_username"] == "new-login"


def test_patch_secret_value_requires_unlocked_vault(client, db):
    user = _create_user(db, username="secret-owner-3")
    headers = _auth_header(str(user.id))
    _setup_and_unlock_vault(client, str(user.id))

    create_response = client.post(
        "/api/user-secrets",
        headers=headers,
        json={"type": SecretType.ALLEGRO.value, "secret": "s1"},
    )
    secret_id = create_response.json()["id"]

    client.cookies.clear()

    patch_response = client.patch(
        f"/api/user-secrets/{secret_id}",
        headers=headers,
        json={"secret": "rotated"},
    )

    assert patch_response.status_code == 423
    assert patch_response.json() == {"detail": "Vault is locked"}


def test_patch_secret_returns_404_for_missing_secret(client, db):
    user = _create_user(db, username="secret-owner-4")
    headers = _auth_header(str(user.id))

    patch_response = client.patch(
        "/api/user-secrets/12345678-1234-5678-1234-567812345678",
        headers=headers,
        json={"alias": "renamed"},
    )

    assert patch_response.status_code == 404
    assert patch_response.json() == {"detail": "Secret not found"}


def test_patch_secret_returns_404_for_other_users_secret(client, db):
    owner = _create_user(db, username="secret-owner-5")
    other_user = _create_user(db, username="secret-owner-6")
    _setup_and_unlock_vault(client, str(owner.id))

    create_response = client.post(
        "/api/user-secrets",
        headers=_auth_header(str(owner.id)),
        json={"type": SecretType.ALLEGRO.value, "alias": "mine", "secret": "s1"},
    )
    secret_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/user-secrets/{secret_id}",
        headers=_auth_header(str(other_user.id)),
        json={"alias": "stolen"},
    )

    assert patch_response.status_code == 404
    assert patch_response.json() == {"detail": "Secret not found"}


def test_patch_secret_allows_clearing_alias_with_null(client, db):
    user = _create_user(db, username="secret-owner-7")
    headers = _auth_header(str(user.id))
    _setup_and_unlock_vault(client, str(user.id))

    create_response = client.post(
        "/api/user-secrets",
        headers=headers,
        json={"type": SecretType.ALLEGRO.value, "alias": "to-clear", "secret": "s1"},
    )
    secret_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/user-secrets/{secret_id}",
        headers=headers,
        json={"alias": None},
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["alias"] is None


def test_patch_secret_maps_blank_alias_to_none(client, db):
    user = _create_user(db, username="secret-owner-8")
    headers = _auth_header(str(user.id))
    _setup_and_unlock_vault(client, str(user.id))

    create_response = client.post(
        "/api/user-secrets",
        headers=headers,
        json={"type": SecretType.ALLEGRO.value, "alias": "kept", "secret": "s1"},
    )
    secret_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/user-secrets/{secret_id}",
        headers=headers,
        json={"alias": "   "},
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["alias"] is None


def test_create_secret_rejects_alias_longer_than_limit(client, db):
    user = _create_user(db, username="secret-owner-9")
    headers = _auth_header(str(user.id))
    _setup_and_unlock_vault(client, str(user.id))

    create_response = client.post(
        "/api/user-secrets",
        headers=headers,
        json={
            "type": SecretType.ALLEGRO.value,
            "alias": "x" * 17,
            "secret": "s1",
        },
    )

    assert create_response.status_code == 422
