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
