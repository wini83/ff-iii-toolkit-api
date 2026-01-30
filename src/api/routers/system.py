from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.deps_db import get_db
from api.models.system import (
    BootstrapPayload,
    BootstrapResponse,
    HealthResponse,
    VersionResponse,
)
from services.db.passwords import hash_password
from services.db.repository import UserRepository
from services.system.bootstrap import BootstrapAlreadyDone, BootstrapService

router = APIRouter(prefix="/api/system", tags=["system"])


def get_bootstrap_service(
    db: Session = Depends(get_db),
) -> BootstrapService:
    return BootstrapService(
        user_repo=UserRepository(db),
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    db_status = "ok"
    overall_status = "ok"
    # --- DB check ---
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
        overall_status = "error"
    if overall_status == "error":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(status=overall_status, database=db_status)


@router.get("/version", response_model=VersionResponse)
async def version_check(request: Request):
    version = getattr(request.app.state, "version", "unknown")
    return VersionResponse(version=version)


@router.get("/bootstrap/status", response_model=BootstrapResponse)
def bootstrap_status(
    service: BootstrapService = Depends(get_bootstrap_service),
):
    return BootstrapResponse(bootstrapped=service.is_bootstrapped())


@router.post("/bootstrap", status_code=201)
def bootstrap_system(
    payload: BootstrapPayload,
    service: BootstrapService = Depends(get_bootstrap_service),
):
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
