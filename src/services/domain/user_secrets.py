from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class SecretType(str, Enum):
    ALLEGRO = "allegro"
    AMAZON = "amazon"
    SESSION = "session"
    API_TOKEN = "api_token"


@dataclass(slots=True, frozen=True)
class UserSecretReadModel:
    id: UUID
    type: SecretType
    usage_count: int
    last_used_at: datetime | None
    created_at: datetime


@dataclass(slots=True, frozen=True)
class UserSecretModel(UserSecretReadModel):
    secret: str
