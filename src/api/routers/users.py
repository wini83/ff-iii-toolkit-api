from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from api.deps_db import get_db
from api.models.users import UserCreateRequest, UserResponse
from services.db.passwords import hash_password
from services.db.repository import UserRepository
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
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)

    user = repo.create(
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_superuser=payload.is_superuser,
    )

    return user


@router.post(
    "/{user_id}/disable",
    status_code=status.HTTP_204_NO_CONTENT,
)
def disable_user(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)

    repo.disable(user_id)


@router.post(
    "/{user_id}/promote",
    status_code=status.HTTP_204_NO_CONTENT,
)
def promote_user(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)
    repo.promote_to_superuser(user_id)
