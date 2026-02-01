from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import String, cast, select
from sqlalchemy.orm import Session

from api.deps_db import get_db
from api.models.users import (
    AuditLogItem,
    AuditLogResponse,
    UserCreateRequest,
    UserResponse,
)
from services.db.models import AuditLogORM
from services.db.passwords import hash_password
from services.db.repository import AuditLogRepository, UserRepository
from services.guards import require_superuser

router = APIRouter(
    prefix="/api/users", tags=["users"], dependencies=[Depends(require_superuser)]
)


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    users = repo.list_all()
    return users


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreateRequest,
    admin_id: UUID = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)

    user = repo.create(
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_superuser=payload.is_superuser,
    )
    audit = AuditLogRepository(db)
    audit.log(actor_id=admin_id, action="user.create", target_id=user.id)
    return user


@router.post(
    "/{user_id}/disable",
    status_code=status.HTTP_204_NO_CONTENT,
)
def disable_user(
    user_id: UUID,
    admin_id: UUID = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)

    repo.disable(user_id)
    audit = AuditLogRepository(db)
    audit.log(actor_id=admin_id, action="user.disable", target_id=user_id)


@router.post(
    "/{user_id}/enable",
    status_code=status.HTTP_204_NO_CONTENT,
)
def enable_user(
    user_id: UUID,
    admin_id: UUID = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)

    repo.enable(user_id)
    audit = AuditLogRepository(db)
    audit.log(actor_id=admin_id, action="user.enable", target_id=user_id)


@router.post(
    "/{user_id}/promote",
    status_code=status.HTTP_204_NO_CONTENT,
)
def promote_user(
    user_id: UUID,
    admin_id: UUID = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    repo.promote_to_superuser(user_id)
    audit = AuditLogRepository(db)
    audit.log(actor_id=admin_id, action="user.promote", target_id=user_id)


@router.post(
    "/{user_id}/demote",
    status_code=status.HTTP_204_NO_CONTENT,
)
def demote_user(
    user_id: UUID,
    admin_id: UUID = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    repo.demote_from_superuser(user_id)
    audit = AuditLogRepository(db)
    audit.log(actor_id=admin_id, action="user.demote", target_id=user_id)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(
    user_id: UUID,
    admin_id: UUID = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    repo.delete(user_id)
    audit = AuditLogRepository(db)
    audit.log(actor_id=admin_id, action="user.delete", target_id=user_id)


@router.get("/audit-log", response_model=AuditLogResponse)
def list_audit_log(
    actor_id: UUID | None = None,
    target_id: UUID | None = None,
    action: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    meta_contains: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    filters = []
    if actor_id is not None:
        filters.append(AuditLogORM.actor_id == actor_id)
    if target_id is not None:
        filters.append(AuditLogORM.target_id == target_id)
    if action is not None:
        filters.append(AuditLogORM.action == action)
    if created_from is not None:
        filters.append(AuditLogORM.created_at >= created_from)
    if created_to is not None:
        filters.append(AuditLogORM.created_at <= created_to)
    if meta_contains:
        filters.append(cast(AuditLogORM.meta, String).ilike(f"%{meta_contains}%"))

    stmt = (
        select(AuditLogORM)
        .where(*filters)
        .order_by(AuditLogORM.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = db.execute(stmt).scalars().all()
    items = [
        AuditLogItem(
            id=row.id,
            actor_id=row.actor_id,
            action=row.action,
            target_id=row.target_id,
            meta=row.meta,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return AuditLogResponse(items=items, limit=limit, offset=offset)
