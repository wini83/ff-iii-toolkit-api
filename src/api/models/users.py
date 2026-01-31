# api/models/users.py
from datetime import datetime
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


class MeResponse(BaseModel):
    id: UUID
    username: str
    is_active: bool
    is_superuser: bool


class AuditLogItem(BaseModel):
    id: UUID
    actor_id: UUID
    action: str
    target_id: UUID | None
    meta: dict | None
    created_at: datetime


class AuditLogResponse(BaseModel):
    items: list[AuditLogItem]
    limit: int
    offset: int
