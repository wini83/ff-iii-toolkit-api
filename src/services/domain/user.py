from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class User:
    id: UUID
    username: str
    password_hash: str
    is_superuser: bool
    is_active: bool
    must_change_password: bool
    password_changed_at: datetime | None
