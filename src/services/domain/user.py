from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class User:
    id: UUID
    username: str
    password_hash: str
    is_superuser: bool
    is_active: bool
