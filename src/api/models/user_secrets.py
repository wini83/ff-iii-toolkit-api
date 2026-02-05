from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

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
