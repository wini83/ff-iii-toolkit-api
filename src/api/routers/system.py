from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps_db import get_db
from api.models.system import BootstrapPayload, HealthResponse, VersionResponse
from services.db.passwords import hash_password
from services.db.repository import UserRepository
from services.system.bootstrap import BootstrapAlreadyDone, BootstrapService

router = APIRouter(prefix="/api/system", tags=["system"])

APP_VERSION: str | None = None


def init_system_router(version: str):
    """Call this function from main to inject version."""
    global APP_VERSION
    APP_VERSION = version


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()


@router.get("/version", response_model=VersionResponse)
async def version_check():
    return VersionResponse(version=APP_VERSION or "unknown")


@router.post("/bootstrap", status_code=201)
def bootstrap_system(
    payload: BootstrapPayload,
    db: Session = Depends(get_db),
):
    service = BootstrapService(UserRepository(db))
    try:
        service.bootstrap_superuser(
            username=payload.username,
            password_hash=hash_password(payload.password),
        )
    except BootstrapAlreadyDone as e:
        raise HTTPException(
            status_code=409,
            detail="System already bootstrapped",
        ) from e
