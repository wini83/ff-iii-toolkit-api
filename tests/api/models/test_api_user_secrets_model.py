import hashlib
from datetime import UTC, datetime
from uuid import UUID

import pytest

from api.models.user_secrets import (
    MAX_SECRET_ALIAS_LENGTH,
    CreateSecretPayload,
    UpdateSecretPayload,
    UserSecretResponse,
    VaultStatusResponse,
)
from services.domain.user_secrets import SecretType


def test_user_secret_response_short_id_is_sha1_prefix():
    secret = UserSecretResponse(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        type=SecretType.ALLEGRO,
        alias="primary",
        external_username="user-1",
        usage_count=0,
        last_used_at=None,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )

    expected = hashlib.sha1(str(secret.id).encode()).hexdigest()[:8]

    assert secret.short_id == expected
    assert secret.alias == "primary"
    assert secret.external_username == "user-1"


def test_create_secret_payload_normalizes_alias():
    payload = CreateSecretPayload(
        type=SecretType.ALLEGRO,
        alias="  main  ",
        secret="s1",
    )

    assert payload.alias == "main"


def test_create_secret_payload_normalizes_external_username():
    payload = CreateSecretPayload(
        type=SecretType.ALLEGRO,
        external_username="  login  ",
        secret="s1",
    )

    assert payload.external_username == "login"


def test_update_secret_payload_maps_blank_alias_to_none():
    payload = UpdateSecretPayload(alias="   ")

    assert payload.alias is None


def test_create_secret_payload_rejects_alias_longer_than_limit():
    with pytest.raises(ValueError):
        CreateSecretPayload(
            type=SecretType.ALLEGRO,
            alias="x" * (MAX_SECRET_ALIAS_LENGTH + 1),
            secret="s1",
        )


def test_vault_status_response_accepts_optional_expires_at():
    status = VaultStatusResponse(
        configured=True,
        unlocked=True,
        expires_at=datetime(2025, 1, 1, tzinfo=UTC),
    )

    assert status.expires_at == datetime(2025, 1, 1, tzinfo=UTC)
