from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from services.domain.user_secrets import SecretType
from services.mappers.user_secrets import (
    map_secret_to_domain_model,
    map_secret_to_domain_read_model,
    map_secrets_to_domain_read_models,
)


def _secret_obj():
    return SimpleNamespace(
        id=uuid4(),
        user_id=uuid4(),
        type=SecretType.AMAZON,
        usage_count=1,
        last_used_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        secret="s3cr3t",
    )


def test_map_secret_to_domain_read_model():
    obj = _secret_obj()
    result = map_secret_to_domain_read_model(obj)
    assert result.id == obj.id
    assert result.type == obj.type
    assert result.usage_count == obj.usage_count
    assert result.last_used_at == obj.last_used_at
    assert result.created_at == obj.created_at
    assert not hasattr(result, "secret")


def test_map_secrets_to_domain_read_models_empty():
    assert map_secrets_to_domain_read_models([]) == []


def test_map_secrets_to_domain_read_models():
    obj = _secret_obj()
    result = map_secrets_to_domain_read_models([obj])
    assert len(result) == 1
    assert result[0].id == obj.id
    assert result[0].type == obj.type


def test_map_secret_to_domain_model_includes_secret():
    obj = _secret_obj()
    result = map_secret_to_domain_model(obj)
    assert result.id == obj.id
    assert result.secret == obj.secret
