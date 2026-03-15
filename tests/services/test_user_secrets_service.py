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
from services.exceptions import SecretNotAccessible
from services.user_secrets_service import UserSecretsService


@pytest.fixture
def secret_obj():
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        type=SecretType.ALLEGRO,
        alias="prod",
        usage_count=3,
        last_used_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        secret="shhh",
    )


def test_create_secret_happy_path(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.create.return_value = secret_obj

    svc = UserSecretsService(secret_repo=secret_repo, audit_repo=audit_repo)

    actor_id = uuid4()
    user_id = secret_obj.user_id
    result = svc.create(
        actor_id=actor_id,
        user_id=user_id,
        type=SecretType.ALLEGRO,
        alias="shop",
        secret="token",
    )

    secret_repo.create.assert_called_once_with(
        user_id=user_id,
        type=SecretType.ALLEGRO,
        alias="shop",
        secret="token",
    )
    audit_repo.log.assert_called_once_with(
        actor_id=actor_id,
        action="user_secret.create",
        target_id=secret_obj.id,
        metadata={"type": SecretType.ALLEGRO.value, "alias": "shop"},
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

    svc = UserSecretsService(secret_repo=secret_repo, audit_repo=audit_repo)

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

    svc = UserSecretsService(secret_repo=secret_repo, audit_repo=audit_repo)

    with pytest.raises(SecretNotAccessible):
        svc.update_alias(
            actor_id=uuid4(),
            user_id=uuid4(),
            secret_id=secret_obj.id,
            alias="new",
        )

    secret_repo.update_alias.assert_not_called()
    audit_repo.log.assert_not_called()


def test_update_alias_happy_path(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    updated_secret = SimpleNamespace(**{**secret_obj.__dict__, "alias": "new-name"})
    secret_repo.get_by_id.return_value = secret_obj
    secret_repo.update_alias.return_value = updated_secret

    svc = UserSecretsService(secret_repo=secret_repo, audit_repo=audit_repo)

    result = svc.update_alias(
        actor_id=secret_obj.user_id,
        user_id=secret_obj.user_id,
        secret_id=secret_obj.id,
        alias="new-name",
    )

    secret_repo.update_alias.assert_called_once_with(
        secret=secret_obj, alias="new-name"
    )
    audit_repo.log.assert_called_once_with(
        actor_id=secret_obj.user_id,
        action="user_secret.update_alias",
        target_id=secret_obj.id,
        metadata={"alias": "new-name"},
    )
    assert result.alias == "new-name"


def test_delete_secret_not_found():
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_by_id.return_value = None

    svc = UserSecretsService(secret_repo=secret_repo, audit_repo=audit_repo)

    with pytest.raises(SecretNotAccessible):
        svc.delete(
            actor_id=uuid4(),
            user_id=uuid4(),
            secret_id=uuid4(),
        )


def test_delete_secret_wrong_owner(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_by_id.return_value = secret_obj

    svc = UserSecretsService(secret_repo=secret_repo, audit_repo=audit_repo)

    with pytest.raises(SecretNotAccessible):
        svc.delete(
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

    svc = UserSecretsService(secret_repo=secret_repo, audit_repo=audit_repo)

    actor_id = uuid4()
    svc.delete(
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


def test_list_for_user_empty():
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_for_user.return_value = []

    svc = UserSecretsService(secret_repo=secret_repo, audit_repo=audit_repo)

    result = svc.list_for_user(user_id=uuid4())

    assert result == []


def test_list_for_user_maps(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_for_user.return_value = [secret_obj]

    svc = UserSecretsService(secret_repo=secret_repo, audit_repo=audit_repo)

    result = svc.list_for_user(user_id=secret_obj.user_id)

    assert len(result) == 1
    assert result[0].id == secret_obj.id
    assert result[0].type == secret_obj.type
    assert result[0].alias == secret_obj.alias


def test_get_for_internal_use_not_found():
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_by_id.return_value = None

    svc = UserSecretsService(secret_repo=secret_repo, audit_repo=audit_repo)

    with pytest.raises(SecretNotAccessible):
        svc.get_for_internal_use(
            secret_id=uuid4(),
            user_id=uuid4(),
            usage_meta=None,
        )


def test_get_for_internal_use_wrong_owner(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_by_id.return_value = secret_obj

    svc = UserSecretsService(secret_repo=secret_repo, audit_repo=audit_repo)

    with pytest.raises(SecretNotAccessible):
        svc.get_for_internal_use(
            secret_id=secret_obj.id,
            user_id=uuid4(),
            usage_meta=None,
        )

    secret_repo.mark_used.assert_not_called()
    audit_repo.log.assert_not_called()


def test_get_for_internal_use_happy_path(secret_obj):
    secret_repo = MagicMock()
    audit_repo = MagicMock()
    secret_repo.get_by_id.return_value = secret_obj

    svc = UserSecretsService(secret_repo=secret_repo, audit_repo=audit_repo)

    usage_meta = {"source": "unit-test"}
    result = svc.get_for_internal_use(
        secret_id=secret_obj.id,
        user_id=secret_obj.user_id,
        usage_meta=usage_meta,
    )

    secret_repo.mark_used.assert_called_once_with(secret=secret_obj, meta=usage_meta)
    audit_repo.log.assert_called_once_with(
        actor_id=secret_obj.user_id,
        action="user_secret.used",
        target_id=secret_obj.id,
        metadata=usage_meta,
    )
    assert isinstance(result, UserSecretModel)
    assert result.alias == secret_obj.alias
    assert result.secret == secret_obj.secret
