import logging
from secrets import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from api.deps_db import get_db
from services.auth import get_current_user
from services.db.repository import UserRepository
from settings import settings

logger = logging.getLogger(__name__)


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


def require_internal_api_key(
    internal_api_key: Annotated[
        str | None,
        Header(alias="X-Internal-Api-Key"),
    ] = None,
) -> None:
    expected_key = settings.INTERNAL_API_KEY
    if not expected_key:
        logger.error(
            "Internal transaction snapshot refresh attempted without INTERNAL_API_KEY configured"
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)

    provided_key = internal_api_key or ""
    if not compare_digest(provided_key, expected_key):
        logger.warning("Invalid internal API key for transaction snapshot refresh")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
