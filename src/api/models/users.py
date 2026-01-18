# api/models/users.py
from uuid import UUID

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: UUID
    username: str
    is_superuser: bool
    is_active: bool


class UserCreateRequest(BaseModel):
    username: str
    password: str
    is_superuser: bool = False
