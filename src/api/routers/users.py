from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import String, cast, select
from sqlalchemy.orm import Session

from api.deps_db import get_db
from api.models.users import (
    AuditLogItem,
    AuditLogResponse,
    InviteResponse,
    UserCreateRequest,
    UserCreateResponse,
    UserResponse,
)
from services.db.models import AuditLogORM
from services.db.repository import (
    AuditLogRepository,
    PasswordSetTokenRepository,
    UserRepository,
)
from services.guards import require_superuser
from services.password_set_tokens import (
    build_invite_url,
    generate_password_set_token,
    generate_placeholder_password_hash,
    get_password_set_expiry,
    hash_password_set_token,
)

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
    response_model=UserCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreateRequest,
    response: Response,
    admin_id: UUID = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    user_repo = UserRepository(db)
    token_repo = PasswordSetTokenRepository(db)
    audit_repo = AuditLogRepository(db)

    plain_token = generate_password_set_token()
    expires_at = get_password_set_expiry()

    user = user_repo.create(
        username=payload.username,
        password_hash=generate_placeholder_password_hash(),
        is_superuser=payload.is_superuser,
        must_change_password=True,
        commit=False,
    )
    token_repo.create_token(
        user_id=user.id,
        token_hash=hash_password_set_token(plain_token),
        expires_at=expires_at,
        created_by=admin_id,
        commit=False,
    )
    audit_repo.log(
        actor_id=admin_id,
        action="user.create",
        target_id=user.id,
        commit=False,
    )
    db.commit()

    response.headers["Cache-Control"] = "no-store"
    return UserCreateResponse(
        id=user.id,
        username=user.username,
        is_superuser=user.is_superuser,
        is_active=user.is_active,
        must_change_password=user.must_change_password,
        invite_url=build_invite_url(plain_token),
        token=plain_token,
        expires_at=expires_at,
    )


@router.post(
    "/{user_id}/invite",
    response_model=InviteResponse,
)
def invite_user(
    user_id: UUID,
    response: Response,
    admin_id: UUID = Depends(require_superuser),
    db: Session = Depends(get_db),
):
    user_repo = UserRepository(db)
    token_repo = PasswordSetTokenRepository(db)
    audit_repo = AuditLogRepository(db)

    user = user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    plain_token = generate_password_set_token()
    expires_at = get_password_set_expiry()
    now = datetime.now(UTC)

    user_repo.mark_password_reset_required(
        user_id=user_id,
        password_hash=generate_placeholder_password_hash(),
        commit=False,
    )
    token_repo.invalidate_previous(
        user_id=user_id,
        invalidated_at=now,
        commit=False,
    )
    token_repo.create_token(
        user_id=user_id,
        token_hash=hash_password_set_token(plain_token),
        expires_at=expires_at,
        created_by=admin_id,
        commit=False,
    )
    audit_repo.log(
        actor_id=admin_id,
        action="user.invite",
        target_id=user_id,
        commit=False,
    )
    db.commit()

    response.headers["Cache-Control"] = "no-store"
    return InviteResponse(
        invite_url=build_invite_url(plain_token),
        token=plain_token,
        expires_at=expires_at,
    )


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
