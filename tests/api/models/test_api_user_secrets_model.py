import hashlib
from datetime import UTC, datetime
from uuid import UUID

from api.models.user_secrets import UserSecretResponse
from services.domain.user_secrets import SecretType


def test_user_secret_response_short_id_is_sha1_prefix():
    secret = UserSecretResponse(
        id=UUID("12345678-1234-5678-1234-567812345678"),
        type=SecretType.ALLEGRO,
        usage_count=0,
        last_used_at=None,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
    )

    expected = hashlib.sha1(str(secret.id).encode()).hexdigest()[:8]

    assert secret.short_id == expected
