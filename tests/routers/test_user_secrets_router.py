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


def test_create_secret_accepts_alias_and_lists_it(client, db):
    user = _create_user(db, username="secret-owner")

    create_response = client.post(
        "/api/user-secrets",
        headers=_auth_header(str(user.id)),
        json={
            "type": SecretType.ALLEGRO.value,
            "alias": "main account",
            "secret": "s1",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["type"] == SecretType.ALLEGRO.value
    assert created["alias"] == "main account"
    assert created["usage_count"] == 0
    assert created["short_id"]

    list_response = client.get(
        "/api/user-secrets",
        headers=_auth_header(str(user.id)),
    )

    assert list_response.status_code == 200
    listed = list_response.json()
    assert len(listed) == 1
    assert listed[0]["id"] == created["id"]
    assert listed[0]["alias"] == "main account"


def test_patch_secret_updates_alias(client, db):
    user = _create_user(db, username="secret-owner-2")

    create_response = client.post(
        "/api/user-secrets",
        headers=_auth_header(str(user.id)),
        json={"type": SecretType.ALLEGRO.value, "secret": "s1"},
    )
    secret_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/user-secrets/{secret_id}",
        headers=_auth_header(str(user.id)),
        json={"alias": "renamed"},
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["alias"] == "renamed"


def test_patch_secret_returns_404_for_missing_secret(client, db):
    user = _create_user(db, username="secret-owner-3")

    patch_response = client.patch(
        "/api/user-secrets/12345678-1234-5678-1234-567812345678",
        headers=_auth_header(str(user.id)),
        json={"alias": "renamed"},
    )

    assert patch_response.status_code == 404
    assert patch_response.json() == {"detail": "Secret not found"}


def test_patch_secret_returns_404_for_other_users_secret(client, db):
    owner = _create_user(db, username="secret-owner-4")
    other_user = _create_user(db, username="secret-owner-5")

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
    user = _create_user(db, username="secret-owner-6")

    create_response = client.post(
        "/api/user-secrets",
        headers=_auth_header(str(user.id)),
        json={"type": SecretType.ALLEGRO.value, "alias": "to-clear", "secret": "s1"},
    )
    secret_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/user-secrets/{secret_id}",
        headers=_auth_header(str(user.id)),
        json={"alias": None},
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["alias"] is None


def test_patch_secret_maps_blank_alias_to_none(client, db):
    user = _create_user(db, username="secret-owner-7")

    create_response = client.post(
        "/api/user-secrets",
        headers=_auth_header(str(user.id)),
        json={"type": SecretType.ALLEGRO.value, "alias": "kept", "secret": "s1"},
    )
    secret_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/api/user-secrets/{secret_id}",
        headers=_auth_header(str(user.id)),
        json={"alias": "   "},
    )

    assert patch_response.status_code == 200
    assert patch_response.json()["alias"] is None


def test_create_secret_rejects_alias_longer_than_limit(client, db):
    user = _create_user(db, username="secret-owner-8")

    create_response = client.post(
        "/api/user-secrets",
        headers=_auth_header(str(user.id)),
        json={
            "type": SecretType.ALLEGRO.value,
            "alias": "x" * 17,
            "secret": "s1",
        },
    )

    assert create_response.status_code == 422
