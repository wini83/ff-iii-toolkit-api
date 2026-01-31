from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.deps_db import get_db
from api.models.users import UserCreateRequest, UserResponse
from services.db.passwords import hash_password
from services.db.repository import AuditLogRepository, UserRepository
from services.guards import require_superuser

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    dependencies=[Depends(require_superuser)],
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
    admin_id: Annotated[UUID, Depends(require_superuser)],
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
    admin_id: Annotated[UUID, Depends(require_superuser)],
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
    admin_id: Annotated[UUID, Depends(require_superuser)],
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
    admin_id: Annotated[UUID, Depends(require_superuser)],
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
    admin_id: Annotated[UUID, Depends(require_superuser)],
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
    admin_id: Annotated[UUID, Depends(require_superuser)],
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    repo.delete(user_id)
    audit = AuditLogRepository(db)
    audit.log(actor_id=admin_id, action="user.delete", target_id=user_id)
