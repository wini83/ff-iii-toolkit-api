# api/models/users.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserResponse(BaseModel):
    id: UUID
    username: str
    is_superuser: bool
    is_active: bool
    must_change_password: bool


class UserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str
    is_superuser: bool = False


class UserCreateResponse(UserResponse):
    invite_url: str | None
    token: str
    expires_at: datetime


class InviteResponse(BaseModel):
    invite_url: str | None
    token: str
    expires_at: datetime


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
