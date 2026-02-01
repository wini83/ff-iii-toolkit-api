from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel


class SecretTypeAPI(str, Enum):
    ALLEGRO = "allegro"
    AMAZON = "amazon"


class CreateSecretPayload(BaseModel):
    type: SecretTypeAPI
    secret: str


class UserSecretResponse(BaseModel):
    id: UUID
    type: str
    usage_count: int
    last_used_at: datetime | None
    created_at: datetime
