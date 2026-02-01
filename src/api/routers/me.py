from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps_db import get_db
from api.models.users import MeResponse
from services.db.repository import UserRepository
from services.guards import require_active_user

router = APIRouter(
    prefix="/api/me",
    tags=["me"],
)


@router.get("", response_model=MeResponse)
def get_me(
    user_id: UUID = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    repo = UserRepository(db)

    user = repo.get_by_id(user_id)
    if not user:
        # teoretycznie nie powinno się zdarzyć, ale defensywnie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return MeResponse(
        id=user.id,
        username=user.username,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
    )
