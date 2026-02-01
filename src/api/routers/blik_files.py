import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from ff_iii_luciferin.api import FireflyClient

from api.mappers.blik_stats import map_blik_metrics_state_to_response
from api.models.blik_files import (
    ApplyPayload,
    FileApplyResponse,
    FileMatchResponse,
    FilePreviewResponse,
    StatisticsResponse,
    UploadResponse,
)
from api.models.blik_stats import BlikMetricsStatusResponse
from services.blik_application_service import BlikApplicationService
from services.blik_stats.manager import BlikMetricsManager
from services.exceptions import (
    ExternalServiceFailed,
    FileNotFound,
    InvalidFileId,
    InvalidMatchSelection,
    MatchesNotComputed,
    TransactionNotFound,
)
from services.firefly_blik_service import FireflyBlikService
from services.guards import require_active_user
from settings import settings

router = APIRouter(
    prefix="/api/blik_files",
    tags=["blik-files"],
    dependencies=[Depends(require_active_user)],
)
logger = logging.getLogger(__name__)


# --------------------------------------------------
# Dependency
# --------------------------------------------------


@lru_cache(maxsize=1)
def blik_service_singleton() -> BlikApplicationService:
    if not settings.FIREFLY_URL or not settings.FIREFLY_TOKEN:
        raise RuntimeError("Config error")

    client = FireflyClient(
        base_url=settings.FIREFLY_URL,
        token=settings.FIREFLY_TOKEN,
    )

    blik_service = FireflyBlikService(
        client,
        settings.BLIK_DESCRIPTION_FILTER,
    )

    return BlikApplicationService(blik_service=blik_service)


def blik_service_dep() -> BlikApplicationService:
    return blik_service_singleton()


@lru_cache(maxsize=1)
def blik_metrics_manager_singleton() -> BlikMetricsManager:
    if not settings.FIREFLY_URL or not settings.FIREFLY_TOKEN:
        raise RuntimeError("Config error")

    client = FireflyClient(
        base_url=settings.FIREFLY_URL,
        token=settings.FIREFLY_TOKEN,
    )

    blik_service = FireflyBlikService(
        client,
        settings.BLIK_DESCRIPTION_FILTER,
    )

    return BlikMetricsManager(blik_service=blik_service)


def blik_metrics_manager_dep() -> BlikMetricsManager:
    return blik_metrics_manager_singleton()


# --------------------------------------------------
# Endpoints
# --------------------------------------------------


@router.get(
    "/statistics",
    response_model=StatisticsResponse,
    deprecated=True,
)
async def get_statistics(
    svc: BlikApplicationService = Depends(blik_service_dep),
):
    try:
        return await svc.get_statistics()
    except ExternalServiceFailed as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post(
    "/statistics/refresh",
    response_model=StatisticsResponse,
    deprecated=True,
)
async def refresh_statistics(
    svc: BlikApplicationService = Depends(blik_service_dep),
):
    try:
        return await svc.get_statistics(refresh=True)
    except ExternalServiceFailed as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get(
    "/statistics_v2",
    response_model=BlikMetricsStatusResponse,
)
async def get_statistics_current(
    manager: BlikMetricsManager = Depends(blik_metrics_manager_dep),
):
    state = manager.get_state()
    return map_blik_metrics_state_to_response(state)


@router.post(
    "/statistics_v2/refresh",
    response_model=BlikMetricsStatusResponse,
)
async def refresh_statistics_current(
    manager: BlikMetricsManager = Depends(blik_metrics_manager_dep),
):
    state = await manager.refresh()
    return map_blik_metrics_state_to_response(state)


@router.post(
    "",
    response_model=UploadResponse,
)
async def upload_csv(
    file: UploadFile = File(...),
    svc: BlikApplicationService = Depends(blik_service_dep),
):
    content = await file.read()
    return await svc.upload_csv(file_bytes=content)


@router.get(
    "/{encoded_id}",
    response_model=FilePreviewResponse,
)
async def preview_csv(
    encoded_id: str,
    svc: BlikApplicationService = Depends(blik_service_dep),
):
    try:
        return await svc.preview_csv(encoded_id=encoded_id)
    except InvalidFileId as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFound:
        raise HTTPException(status_code=404, detail="File not found") from None


@router.get(
    "/{encoded_id}/matches",
    response_model=FileMatchResponse,
)
async def preview_matches(
    encoded_id: str,
    svc: BlikApplicationService = Depends(blik_service_dep),
):
    try:
        return await svc.preview_matches(encoded_id=encoded_id)
    except InvalidFileId as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFound as e:
        raise HTTPException(status_code=404, detail="File not found") from e
    except ExternalServiceFailed as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post(
    "/{encoded_id}/matches",
    response_model=FileApplyResponse,
)
async def apply_matches(
    encoded_id: str,
    payload: ApplyPayload,
    svc: BlikApplicationService = Depends(blik_service_dep),
):
    try:
        return await svc.apply_matches(encoded_id=encoded_id, payload=payload)
    except InvalidFileId as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MatchesNotComputed as e:
        raise HTTPException(status_code=400, detail="No match data found") from e
    except TransactionNotFound as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except InvalidMatchSelection as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ExternalServiceFailed as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
