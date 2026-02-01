from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps_runtime import get_tx_application_runtime
from api.models.tx import ScreeningMonthResponse, TxTag
from api.models.tx_stats import TxMetricsStatusResponse
from services.exceptions import ExternalServiceFailed
from services.guards import require_active_user
from services.tx_application_service import TxApplicationService

router = APIRouter(
    prefix="/api/tx",
    tags=["transactions"],
)


# --------------------------------------------------
# Endpoints
# --------------------------------------------------


@router.get(
    "/screening",
    response_model=ScreeningMonthResponse,
    responses={
        200: {"description": "Uncategorized transactions for given month"},
        204: {"description": "No uncategorized transactions in this month"},
        400: {"description": "Invalid year or month"},
        502: {"description": "Firefly error"},
    },
)
async def get_screening_month(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    user_id: UUID = Depends(require_active_user),
    svc: TxApplicationService = Depends(get_tx_application_runtime),
):
    try:
        response = await svc.get_screening_month(year=year, month=month)
    except ExternalServiceFailed as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    if response is None:
        raise HTTPException(status_code=204)
    return response


@router.post(
    "/{tx_id}/category/{category_id}",
    status_code=204,
)
async def apply_category(
    tx_id: int,
    category_id: int,
    user_id: UUID = Depends(require_active_user),
    svc: TxApplicationService = Depends(get_tx_application_runtime),
):
    try:
        await svc.apply_category(tx_id=tx_id, category_id=category_id)
    except ExternalServiceFailed as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post(
    "/{tx_id}/tag/",
    status_code=204,
)
async def apply_tag(
    tx_id: int,
    tag: TxTag = Query(...),
    user_id: UUID = Depends(require_active_user),
    svc: TxApplicationService = Depends(get_tx_application_runtime),
):
    try:
        await svc.apply_tag(tx_id=tx_id, tag=tag)
    except ExternalServiceFailed as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get(
    "/statistics",
    response_model=TxMetricsStatusResponse,
)
async def get_tx_stats(
    user_id: UUID = Depends(require_active_user),
    svc: TxApplicationService = Depends(get_tx_application_runtime),
):
    return await svc.get_tx_metrics()


@router.post(
    "/statistics/refresh",
    response_model=TxMetricsStatusResponse,
)
async def refresh_tx_stats(
    user_id: UUID = Depends(require_active_user),
    svc: TxApplicationService = Depends(get_tx_application_runtime),
):
    return await svc.refresh_tx_metrics()
