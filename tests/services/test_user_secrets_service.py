from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.domain.user_secrets import (
    SecretType,
    UserSecretModel,
    UserSecretReadModel,
)
from services.exceptions import SecretDecryptionFailed, SecretNotAccessible
from services.user_secrets_service import UserSecretsService


@pytest.fixture
def secret_obj():
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        type=SecretType.ALLEGRO,
        alias="prod",
        external_username="login",
        usage_count=3,
        last_used_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        secret="shhh",
        ciphertext=b"ciphertext",
        secret_nonce=b"secret-nonce",
        wrapped_dek=b"wrapped-dek",
        wrapped_dek_nonce=b"wrapped-dek-nonce",
        crypto_version=1,
    )


def test_create_secret_happy_path(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    vault_service = MagicMock()
    crypto_service = MagicMock()
    secret_repo.create.return_value = secret_obj
    vault_service.require_user_key.return_value = b"user-key"
    crypto_service.encrypt_secret.return_value = SimpleNamespace(
        ciphertext=b"ciphertext",
        secret_nonce=b"secret-nonce",
        wrapped_dek=b"wrapped-dek",
        wrapped_dek_nonce=b"wrapped-dek-nonce",
        crypto_version=1,
    )

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=vault_service,
        crypto_service=crypto_service,
    )

    actor_id = uuid4()
    user_id = secret_obj.user_id
    result = svc.create_secret(
        actor_id=actor_id,
        user_id=user_id,
        vault_session_id="session-123",
        type=SecretType.ALLEGRO,
        alias="shop",
        external_username="shop-user",
        secret="token",
    )

    vault_service.require_user_key.assert_called_once_with(user_id, "session-123")
    crypto_service.encrypt_secret.assert_called_once_with("token", b"user-key")
    secret_repo.create.assert_called_once_with(
        user_id=user_id,
        type=SecretType.ALLEGRO,
        alias="shop",
        external_username="shop-user",
        ciphertext=b"ciphertext",
        secret_nonce=b"secret-nonce",
        wrapped_dek=b"wrapped-dek",
        wrapped_dek_nonce=b"wrapped-dek-nonce",
        crypto_version=1,
    )
    audit_repo.log.assert_called_once_with(
        actor_id=actor_id,
        action="user_secret.create",
        target_id=secret_obj.id,
        metadata={
            "type": SecretType.ALLEGRO.value,
            "alias": "shop",
            "external_username": "shop-user",
        },
    )
    assert isinstance(result, UserSecretReadModel)
    assert result.id == secret_obj.id
    assert result.type == secret_obj.type
    assert result.alias == secret_obj.alias
    assert not hasattr(result, "secret")


def test_update_alias_not_found():
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_by_id.return_value = None

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=MagicMock(),
        crypto_service=MagicMock(),
    )

    with pytest.raises(SecretNotAccessible):
        svc.update_alias(
            actor_id=uuid4(),
            user_id=uuid4(),
            secret_id=uuid4(),
            alias="new",
        )


def test_update_alias_wrong_owner(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_by_id.return_value = secret_obj

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=MagicMock(),
        crypto_service=MagicMock(),
    )

    with pytest.raises(SecretNotAccessible):
        svc.update_alias(
            actor_id=uuid4(),
            user_id=uuid4(),
            secret_id=secret_obj.id,
            alias="new",
        )

    secret_repo.update_metadata.assert_not_called()
    audit_repo.log.assert_not_called()


def test_update_alias_happy_path(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_by_id.return_value = secret_obj

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=MagicMock(),
        crypto_service=MagicMock(),
    )

    result = svc.update_alias(
        actor_id=secret_obj.user_id,
        user_id=secret_obj.user_id,
        secret_id=secret_obj.id,
        alias="new-name",
    )

    secret_repo.update_metadata.assert_called_once_with(
        secret=secret_obj,
        alias="new-name",
        external_username=...,
    )
    audit_repo.log.assert_called_once_with(
        actor_id=secret_obj.user_id,
        action="user_secret.update",
        target_id=secret_obj.id,
        metadata={
            "alias": "new-name",
            "external_username": None,
            "secret_rotated": False,
        },
    )
    assert result.id == secret_obj.id


def test_delete_secret_not_found():
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_by_id.return_value = None

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=MagicMock(),
        crypto_service=MagicMock(),
    )

    with pytest.raises(SecretNotAccessible):
        svc.delete_secret(
            actor_id=uuid4(),
            user_id=uuid4(),
            secret_id=uuid4(),
        )


def test_delete_secret_wrong_owner(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_by_id.return_value = secret_obj

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=MagicMock(),
        crypto_service=MagicMock(),
    )

    with pytest.raises(SecretNotAccessible):
        svc.delete_secret(
            actor_id=uuid4(),
            user_id=uuid4(),
            secret_id=secret_obj.id,
        )

    secret_repo.delete.assert_not_called()
    audit_repo.log.assert_not_called()


def test_delete_secret_happy_path(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_by_id.return_value = secret_obj

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=MagicMock(),
        crypto_service=MagicMock(),
    )

    actor_id = uuid4()
    svc.delete_secret(
        actor_id=actor_id,
        user_id=secret_obj.user_id,
        secret_id=secret_obj.id,
    )

    secret_repo.delete.assert_called_once_with(secret=secret_obj)
    audit_repo.log.assert_called_once_with(
        actor_id=actor_id,
        action="user_secret.delete",
        target_id=secret_obj.id,
    )


def test_list_secrets_empty():
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_for_user.return_value = []

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=MagicMock(),
        crypto_service=MagicMock(),
    )

    result = svc.list_secrets(user_id=uuid4())

    assert result == []


def test_list_secrets_maps(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_for_user.return_value = [secret_obj]

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=MagicMock(),
        crypto_service=MagicMock(),
    )

    result = svc.list_secrets(user_id=secret_obj.user_id)

    assert len(result) == 1
    assert result[0].id == secret_obj.id
    assert result[0].type == secret_obj.type
    assert result[0].alias == secret_obj.alias


def test_get_for_internal_use_not_found():
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_by_id.return_value = None

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=MagicMock(),
        crypto_service=MagicMock(),
    )

    with pytest.raises(SecretNotAccessible):
        svc.get_secret_for_internal_use(
            secret_id=uuid4(),
            user_id=uuid4(),
            vault_session_id="session-123",
            usage_meta=None,
        )


def test_get_for_internal_use_wrong_owner(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_by_id.return_value = secret_obj

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=MagicMock(),
        crypto_service=MagicMock(),
    )

    with pytest.raises(SecretNotAccessible):
        svc.get_secret_for_internal_use(
            secret_id=secret_obj.id,
            user_id=uuid4(),
            vault_session_id="session-123",
            usage_meta=None,
        )

    secret_repo.mark_used.assert_not_called()
    audit_repo.log.assert_not_called()


def test_get_for_internal_use_happy_path(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    vault_service = MagicMock()
    crypto_service = MagicMock()
    secret_repo.get_by_id.return_value = secret_obj
    vault_service.require_user_key.return_value = b"user-key"
    crypto_service.decrypt_secret.return_value = "decrypted-secret"

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=vault_service,
        crypto_service=crypto_service,
    )

    usage_meta = {"source": "unit-test"}
    result = svc.get_secret_for_internal_use(
        secret_id=secret_obj.id,
        user_id=secret_obj.user_id,
        vault_session_id="session-123",
        usage_meta=usage_meta,
    )

    vault_service.require_user_key.assert_called_once_with(
        secret_obj.user_id,
        "session-123",
    )
    crypto_service.decrypt_secret.assert_called_once()
    secret_repo.mark_used.assert_called_once_with(secret=secret_obj, meta=usage_meta)
    audit_repo.log.assert_called_once_with(
        actor_id=secret_obj.user_id,
        action="user_secret.used",
        target_id=secret_obj.id,
        metadata=usage_meta,
    )
    assert isinstance(result, UserSecretModel)
    assert result.alias == secret_obj.alias
    assert result.secret == "decrypted-secret"


def test_get_secret_for_internal_use_raises_for_legacy_plaintext_secret(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    vault_service = MagicMock()
    crypto_service = MagicMock()
    secret_repo.get_by_id.return_value = SimpleNamespace(
        **{
            **secret_obj.__dict__,
            "ciphertext": None,
            "secret_nonce": None,
            "wrapped_dek": None,
            "wrapped_dek_nonce": None,
            "crypto_version": None,
        }
    )
    vault_service.require_user_key.return_value = b"user-key"

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=vault_service,
        crypto_service=crypto_service,
    )

    with pytest.raises(SecretDecryptionFailed):
        svc.get_secret_for_internal_use(
            secret_id=secret_obj.id,
            user_id=secret_obj.user_id,
            vault_session_id="session-123",
        )


def test_update_secret_value_uses_vault_and_encryption(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    vault_service = MagicMock()
    crypto_service = MagicMock()
    secret_repo.get_by_id.return_value = secret_obj
    vault_service.require_user_key.return_value = b"user-key"
    crypto_service.encrypt_secret.return_value = SimpleNamespace(
        ciphertext=b"new-ciphertext",
        secret_nonce=b"new-secret-nonce",
        wrapped_dek=b"new-wrapped-dek",
        wrapped_dek_nonce=b"new-wrapped-dek-nonce",
        crypto_version=1,
    )

    svc = UserSecretsService(
        secret_repo=secret_repo,
        audit_repo=audit_repo,
        vault_service=vault_service,
        crypto_service=crypto_service,
    )

    svc.update_secret(
        actor_id=secret_obj.user_id,
        user_id=secret_obj.user_id,
        secret_id=secret_obj.id,
        vault_session_id="session-123",
        secret="rotated",
    )

    vault_service.require_user_key.assert_called_once_with(
        secret_obj.user_id,
        "session-123",
    )
    crypto_service.encrypt_secret.assert_called_once_with("rotated", b"user-key")
    secret_repo.update_encrypted_secret.assert_called_once()
