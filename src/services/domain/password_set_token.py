from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class PasswordSetToken:
    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime
    created_by: UUID | None
    meta: dict | None
