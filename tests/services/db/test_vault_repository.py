from services.db.repository import UserRepository, UserSecretVaultRepository


def test_create_and_get_vault_for_user(db):
    user = UserRepository(db).create(username="vault-owner", password_hash="hashed")
    repo = UserSecretVaultRepository(db)

    created = repo.create(
        user_id=user.id,
        kdf_salt=b"salt",
        kdf_params_json={
            "time_cost": 3,
            "memory_cost": 65536,
            "parallelism": 2,
            "hash_len": 32,
        },
        vault_check_ciphertext=b"ciphertext",
        vault_check_nonce=b"nonce",
    )

    fetched = repo.get_for_user(user.id)

    assert created.user_id == user.id
    assert fetched is not None
    assert fetched.user_id == user.id
    assert fetched.kdf_salt == b"salt"
    assert fetched.vault_check_ciphertext == b"ciphertext"


def test_update_vault_metadata(db):
    user = UserRepository(db).create(username="vault-owner-2", password_hash="hashed")
    repo = UserSecretVaultRepository(db)
    vault = repo.create(
        user_id=user.id,
        kdf_salt=b"salt",
        kdf_params_json={
            "time_cost": 3,
            "memory_cost": 65536,
            "parallelism": 2,
            "hash_len": 32,
        },
        vault_check_ciphertext=b"ciphertext",
        vault_check_nonce=b"nonce",
    )

    updated = repo.update(
        vault=vault,
        kdf_salt=b"new-salt",
        kdf_params_json={
            "time_cost": 4,
            "memory_cost": 32768,
            "parallelism": 1,
            "hash_len": 32,
        },
        vault_check_ciphertext=b"new-ciphertext",
        vault_check_nonce=b"new-nonce",
    )

    assert updated.kdf_salt == b"new-salt"
    assert updated.kdf_params_json == {
        "time_cost": 4,
        "memory_cost": 32768,
        "parallelism": 1,
        "hash_len": 32,
    }
    assert updated.vault_check_ciphertext == b"new-ciphertext"
    assert updated.vault_check_nonce == b"new-nonce"
