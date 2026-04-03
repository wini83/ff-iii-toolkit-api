import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.deps_db import get_db
from api.deps_services import (
    get_bootstrap_service,
    get_transaction_snapshot_service,
)
from api.models.system import (
    BootstrapPayload,
    BootstrapResponse,
    HealthResponse,
    TransactionSnapshotRefreshResponse,
    TransactionSnapshotStatusResponse,
    VersionResponse,
)
from services.db.passwords import hash_password
from services.guards import require_internal_api_key
from services.snapshot import TransactionSnapshotService
from services.snapshot.models import TransactionSnapshot
from services.system.bootstrap import BootstrapAlreadyDone, BootstrapService

router = APIRouter(prefix="/api/system", tags=["system"])
logger = logging.getLogger(__name__)


def _build_transaction_snapshot_status_response(
    snapshot_service: TransactionSnapshotService,
    snapshot: TransactionSnapshot,
    *,
    is_stale: bool,
) -> TransactionSnapshotStatusResponse:
    return TransactionSnapshotStatusResponse(
        ttl_seconds=snapshot_service.max_age_seconds,
        has_snapshot=True,
        snapshot_fetched_at=snapshot.fetched_at,
        expires_at=snapshot.fetched_at
        + timedelta(seconds=snapshot_service.max_age_seconds),
        is_stale=is_stale,
        transaction_count=snapshot.transaction_count,
        schema_version=snapshot.schema_version,
    )


@router.get("/health", response_model=HealthResponse)
async def health_check(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    db_service: BootstrapService = Depends(get_bootstrap_service),
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

    bootstrapped = db_service.is_bootstrapped()

    return HealthResponse(
        status=overall_status, database=db_status, bootstrapped=bootstrapped
    )


@router.get("/version", response_model=VersionResponse)
async def version_check(request: Request):
    version = getattr(request.app.state, "version", "unknown")
    return VersionResponse(version=version)


@router.get(
    "/transaction-snapshot",
    response_model=TransactionSnapshotStatusResponse,
)
async def transaction_snapshot_status(
    snapshot_service: TransactionSnapshotService = Depends(
        get_transaction_snapshot_service
    ),
):
    snapshot = await snapshot_service.get_cached_snapshot()
    if snapshot is None:
        return TransactionSnapshotStatusResponse(
            ttl_seconds=snapshot_service.max_age_seconds,
            has_snapshot=False,
            snapshot_fetched_at=None,
            expires_at=None,
            is_stale=True,
        )

    is_stale = await snapshot_service.store.is_stale(snapshot_service.max_age_seconds)

    return _build_transaction_snapshot_status_response(
        snapshot_service,
        snapshot,
        is_stale=is_stale,
    )


@router.post(
    "/transaction-snapshot/refresh",
    response_model=TransactionSnapshotRefreshResponse,
    dependencies=[Depends(require_internal_api_key)],
)
async def refresh_transaction_snapshot(
    snapshot_service: TransactionSnapshotService = Depends(
        get_transaction_snapshot_service
    ),
):
    snapshot = await snapshot_service.refresh_snapshot()
    logger.info(
        "Transaction snapshot refreshed via internal endpoint",
        extra={
            "transaction_count": snapshot.transaction_count,
            "schema_version": snapshot.schema_version,
        },
    )
    return TransactionSnapshotRefreshResponse(
        status="ok",
        refreshed=True,
        ttl_seconds=snapshot_service.max_age_seconds,
        snapshot_fetched_at=snapshot.fetched_at,
        expires_at=snapshot.fetched_at
        + timedelta(seconds=snapshot_service.max_age_seconds),
        transaction_count=snapshot.transaction_count,
        schema_version=snapshot.schema_version,
    )


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
