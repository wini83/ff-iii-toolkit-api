from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps_db import get_db
from services.auth import get_current_user
from services.db.repository import UserRepository


def require_superuser(
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UUID:
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from None

    repo = UserRepository(db)

    if not repo.is_superuser(user_uuid):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return user_uuid


def require_active_user(
    user_id: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UUID:
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        # sub z tokenu nie jest UUID → token traktujemy jako zły
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED) from None

    repo = UserRepository(db)
    user = repo.get_by_id(user_uuid)

    if not user:
        # token OK, ale user nie istnieje → auth error
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    return user_uuid
