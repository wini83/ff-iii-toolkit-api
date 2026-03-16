import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from api.deps_runtime import get_blik_application_runtime
from api.mappers.blik import map_job_to_response, map_payload_to_decisions
from api.mappers.blik_stats import map_blik_metrics_state_to_response
from api.models.blik_files import (
    ApplyDecisionsPayload,
    ApplyJobResponse,
    ApplyPayload,
    FileApplyResponse,
    FileMatchResponse,
    FilePreviewResponse,
    StatisticsResponse,
    UploadResponse,
)
from api.models.blik_stats import BlikMetricsStatusResponse
from services.blik_application_service import BlikApplicationService
from services.exceptions import (
    ExternalServiceFailed,
    FileNotFound,
    InvalidFileId,
    InvalidMatchSelection,
    MatchesNotComputed,
    TransactionNotFound,
)
from services.guards import require_active_user

router = APIRouter(
    prefix="/api/blik_files",
    tags=["blik-files"],
    dependencies=[Depends(require_active_user)],
)
logger = logging.getLogger(__name__)


# --------------------------------------------------
# Endpoints
# --------------------------------------------------


@router.get(
    "/statistics",
    response_model=StatisticsResponse,
    deprecated=True,
)
async def get_statistics(
    svc: BlikApplicationService = Depends(get_blik_application_runtime),
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
    svc: BlikApplicationService = Depends(get_blik_application_runtime),
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
    svc: BlikApplicationService = Depends(get_blik_application_runtime),
):
    state = svc.get_metrics_state()
    return map_blik_metrics_state_to_response(state)


@router.post(
    "/statistics_v2/refresh",
    response_model=BlikMetricsStatusResponse,
)
async def refresh_statistics_current(
    svc: BlikApplicationService = Depends(get_blik_application_runtime),
):
    state = await svc.refresh_metrics_state()
    return map_blik_metrics_state_to_response(state)


@router.post(
    "",
    response_model=UploadResponse,
)
async def upload_csv(
    file: UploadFile = File(...),
    svc: BlikApplicationService = Depends(get_blik_application_runtime),
):
    content = await file.read()
    return await svc.upload_csv(file_bytes=content)


@router.get(
    "/{encoded_id}",
    response_model=FilePreviewResponse,
)
async def preview_csv(
    encoded_id: str,
    svc: BlikApplicationService = Depends(get_blik_application_runtime),
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
    svc: BlikApplicationService = Depends(get_blik_application_runtime),
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
    deprecated=True,
)
async def apply_matches(
    encoded_id: str,
    payload: ApplyPayload,
    svc: BlikApplicationService = Depends(get_blik_application_runtime),
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


@router.post(
    "/{encoded_id}/apply",
    response_model=ApplyJobResponse,
)
async def start_apply_job(
    encoded_id: str,
    payload: ApplyDecisionsPayload,
    svc: BlikApplicationService = Depends(get_blik_application_runtime),
):
    try:
        job = await svc.start_apply_job(
            encoded_id=encoded_id,
            decisions=map_payload_to_decisions(payload),
        )
        return map_job_to_response(job)
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


@router.post(
    "/{encoded_id}/apply/auto",
    response_model=ApplyJobResponse,
)
async def auto_apply_single_matches(
    encoded_id: str,
    limit: int | None = Query(default=None, ge=1, le=500),
    svc: BlikApplicationService = Depends(get_blik_application_runtime),
):
    try:
        job = await svc.start_auto_apply_single_matches(
            encoded_id=encoded_id,
            limit=limit,
        )
        return map_job_to_response(job)
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


@router.get(
    "/apply-jobs/{job_id}",
    response_model=ApplyJobResponse,
)
async def get_apply_job(
    job_id: str,
    svc: BlikApplicationService = Depends(get_blik_application_runtime),
):
    try:
        parsed_job_id = UUID(job_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid job_id") from e

    job = svc.get_apply_job(job_id=parsed_job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return map_job_to_response(job)
