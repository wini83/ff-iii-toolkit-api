from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.domain.user_secret_vault import DerivedUserKey, VaultCheckBlob
from services.exceptions import (
    InvalidVaultPassphrase,
    VaultAlreadyConfigured,
    VaultLocked,
    VaultNotConfigured,
    VaultSessionExpired,
)
from services.vault_service import VaultService


def test_setup_vault_creates_metadata_and_commits():
    user_id = uuid4()
    vault_repo = MagicMock()
    vault_repo.get_for_user.return_value = None
    session_store = MagicMock()
    crypto_service = MagicMock()
    audit_repo = MagicMock()
    crypto_service.derive_user_key.return_value = DerivedUserKey(
        key=b"user-key",
        salt=b"salt",
        params={"time_cost": 3, "memory_cost": 65536, "parallelism": 2, "hash_len": 32},
    )
    crypto_service.create_vault_check.return_value = VaultCheckBlob(
        ciphertext=b"ciphertext",
        nonce=b"nonce",
    )
    service = VaultService(
        vault_repo=vault_repo,
        session_store=session_store,
        crypto_service=crypto_service,
        audit_repo=audit_repo,
    )

    service.setup_vault(user_id, "passphrase")

    vault_repo.create.assert_called_once_with(
        user_id=user_id,
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
    audit_repo.log.assert_called_once_with(
        actor_id=user_id,
        action="vault.setup",
        target_id=None,
        metadata=None,
        commit=False,
    )
    audit_repo.db.commit.assert_called_once_with()


def test_setup_vault_raises_when_already_configured():
    vault_repo = MagicMock()
    vault_repo.get_for_user.return_value = object()
    service = VaultService(
        vault_repo=vault_repo,
        session_store=MagicMock(),
        crypto_service=MagicMock(),
        audit_repo=MagicMock(),
    )

    with pytest.raises(VaultAlreadyConfigured):
        service.setup_vault(uuid4(), "passphrase")


def test_unlock_vault_raises_when_not_configured():
    vault_repo = MagicMock()
    vault_repo.get_for_user.return_value = None
    service = VaultService(
        vault_repo=vault_repo,
        session_store=MagicMock(),
        crypto_service=MagicMock(),
        audit_repo=MagicMock(),
    )

    with pytest.raises(VaultNotConfigured):
        service.unlock_vault(uuid4(), "passphrase")


def test_unlock_vault_raises_for_invalid_passphrase():
    vault = SimpleNamespace(
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
    vault_repo = MagicMock()
    vault_repo.get_for_user.return_value = vault
    crypto_service = MagicMock()
    crypto_service.derive_user_key.return_value = DerivedUserKey(
        key=b"user-key",
        salt=b"salt",
        params={"time_cost": 3, "memory_cost": 65536, "parallelism": 2, "hash_len": 32},
    )
    crypto_service.verify_vault_check.return_value = False
    service = VaultService(
        vault_repo=vault_repo,
        session_store=MagicMock(),
        crypto_service=crypto_service,
        audit_repo=MagicMock(),
    )

    with pytest.raises(InvalidVaultPassphrase):
        service.unlock_vault(uuid4(), "wrong-passphrase")


def test_unlock_vault_creates_session_and_commits():
    user_id = uuid4()
    vault = SimpleNamespace(
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
    vault_repo = MagicMock()
    vault_repo.get_for_user.return_value = vault
    session_store = MagicMock()
    session_store.create.return_value = "session-123"
    crypto_service = MagicMock()
    crypto_service.derive_user_key.return_value = DerivedUserKey(
        key=b"user-key",
        salt=b"salt",
        params={"time_cost": 3, "memory_cost": 65536, "parallelism": 2, "hash_len": 32},
    )
    crypto_service.verify_vault_check.return_value = True
    audit_repo = MagicMock()
    service = VaultService(
        vault_repo=vault_repo,
        session_store=session_store,
        crypto_service=crypto_service,
        audit_repo=audit_repo,
        vault_session_ttl_seconds=321,
    )

    session_id = service.unlock_vault(user_id, "passphrase")

    assert session_id == "session-123"
    session_store.create.assert_called_once_with(
        user_id,
        b"user-key",
        ttl_seconds=321,
    )
    audit_repo.db.commit.assert_called_once_with()


def test_lock_vault_invalidates_session_and_commits():
    user_id = uuid4()
    session_store = MagicMock()
    audit_repo = MagicMock()
    service = VaultService(
        vault_repo=MagicMock(),
        session_store=session_store,
        crypto_service=MagicMock(),
        audit_repo=audit_repo,
    )

    service.lock_vault(user_id, "session-123")

    session_store.invalidate.assert_called_once_with(user_id, "session-123")
    audit_repo.db.commit.assert_called_once_with()


def test_is_unlocked_returns_false_without_session_id():
    service = VaultService(
        vault_repo=MagicMock(),
        session_store=MagicMock(),
        crypto_service=MagicMock(),
        audit_repo=MagicMock(),
    )

    assert service.is_unlocked(uuid4(), None) is False


def test_is_unlocked_reflects_session_store():
    user_id = uuid4()
    session_store = MagicMock()
    session_store.get_user_key.return_value = b"user-key"
    service = VaultService(
        vault_repo=MagicMock(),
        session_store=session_store,
        crypto_service=MagicMock(),
        audit_repo=MagicMock(),
    )

    assert service.is_unlocked(user_id, "session-123") is True


def test_require_user_key_raises_when_vault_not_configured():
    vault_repo = MagicMock()
    vault_repo.get_for_user.return_value = None
    service = VaultService(
        vault_repo=vault_repo,
        session_store=MagicMock(),
        crypto_service=MagicMock(),
        audit_repo=MagicMock(),
    )

    with pytest.raises(VaultNotConfigured):
        service.require_user_key(uuid4(), "session-123")


def test_require_user_key_raises_when_session_missing():
    vault_repo = MagicMock()
    vault_repo.get_for_user.return_value = SimpleNamespace()
    service = VaultService(
        vault_repo=vault_repo,
        session_store=MagicMock(),
        crypto_service=MagicMock(),
        audit_repo=MagicMock(),
    )

    with pytest.raises(VaultLocked):
        service.require_user_key(uuid4(), None)


def test_require_user_key_raises_when_session_expired():
    vault_repo = MagicMock()
    vault_repo.get_for_user.return_value = SimpleNamespace()
    session_store = MagicMock()
    session_store.get_user_key.return_value = None
    service = VaultService(
        vault_repo=vault_repo,
        session_store=session_store,
        crypto_service=MagicMock(),
        audit_repo=MagicMock(),
    )

    with pytest.raises(VaultSessionExpired):
        service.require_user_key(uuid4(), "session-123")


def test_require_user_key_returns_active_key():
    user_id = uuid4()
    vault_repo = MagicMock()
    vault_repo.get_for_user.return_value = SimpleNamespace()
    session_store = MagicMock()
    session_store.get_user_key.return_value = b"user-key"
    service = VaultService(
        vault_repo=vault_repo,
        session_store=session_store,
        crypto_service=MagicMock(),
        audit_repo=MagicMock(),
    )

    result = service.require_user_key(user_id, "session-123")

    assert result == b"user-key"
    session_store.get_user_key.assert_called_once_with(user_id, "session-123")


def test_change_passphrase_is_explicitly_not_supported_yet():
    service = VaultService(
        vault_repo=MagicMock(),
        session_store=MagicMock(),
        crypto_service=MagicMock(),
        audit_repo=MagicMock(),
    )

    with pytest.raises(NotImplementedError, match="secret rewrap is implemented"):
        service.change_passphrase(uuid4(), "old", "new")


def test_setup_vault_commits_without_audit_repo():
    user_id = uuid4()
    vault_repo = MagicMock()
    vault_repo.get_for_user.return_value = None
    crypto_service = MagicMock()
    crypto_service.derive_user_key.return_value = DerivedUserKey(
        key=b"user-key",
        salt=b"salt",
        params={"time_cost": 3, "memory_cost": 65536, "parallelism": 2, "hash_len": 32},
    )
    crypto_service.create_vault_check.return_value = VaultCheckBlob(
        ciphertext=b"ciphertext",
        nonce=b"nonce",
    )
    service = VaultService(
        vault_repo=vault_repo,
        session_store=MagicMock(),
        crypto_service=crypto_service,
        audit_repo=None,
    )

    service.setup_vault(user_id, "passphrase")

    vault_repo.db.commit.assert_called_once_with()
