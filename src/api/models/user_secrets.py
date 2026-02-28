import hashlib
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, computed_field

from services.domain.user_secrets import SecretType


class CreateSecretPayload(BaseModel):
    type: SecretType
    secret: str


class UserSecretResponse(BaseModel):
    id: UUID
    type: SecretType
    usage_count: int
    last_used_at: datetime | None
    created_at: datetime

    @computed_field
    @property
    def short_id(self) -> str:
        return hashlib.sha1(str(self.id).encode()).hexdigest()[:8]
