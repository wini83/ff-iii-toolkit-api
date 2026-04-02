import hashlib
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator

from services.domain.user_secrets import SecretType

MAX_SECRET_ALIAS_LENGTH = 16


def _normalize_alias(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


class CreateSecretPayload(BaseModel):
    type: SecretType
    alias: str | None = Field(default=None, max_length=MAX_SECRET_ALIAS_LENGTH)
    external_username: str | None = None
    secret: str

    @field_validator("alias", mode="before")
    @classmethod
    def normalize_alias(cls, value: str | None) -> str | None:
        return _normalize_alias(value)

    @field_validator("external_username", mode="before")
    @classmethod
    def normalize_external_username(cls, value: str | None) -> str | None:
        return _normalize_alias(value)


class UserSecretResponse(BaseModel):
    id: UUID
    type: SecretType
    alias: str | None = None
    external_username: str | None = None
    usage_count: int
    last_used_at: datetime | None
    created_at: datetime

    @computed_field
    def short_id(self) -> str:
        return hashlib.sha1(str(self.id).encode()).hexdigest()[:8]


class UpdateSecretPayload(BaseModel):
    alias: str | None = Field(default=None, max_length=MAX_SECRET_ALIAS_LENGTH)
    external_username: str | None = None
    secret: str | None = None

    @field_validator("alias", mode="before")
    @classmethod
    def normalize_alias(cls, value: str | None) -> str | None:
        return _normalize_alias(value)

    @field_validator("external_username", mode="before")
    @classmethod
    def normalize_external_username(cls, value: str | None) -> str | None:
        return _normalize_alias(value)


class VaultPassphrasePayload(BaseModel):
    passphrase: str = Field(min_length=1)


class VaultStatusResponse(BaseModel):
    configured: bool
    unlocked: bool
