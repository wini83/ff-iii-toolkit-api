import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps_runtime import get_allegro_application_runtime
from api.mappers.allegro import (
    map_allegro_metrics_state_to_response,
    map_allegro_payments_to_response,
    map_job_to_response,
    map_payload_to_decisions,
)
from api.models.allegro import (
    AllegroMatchResponse,
    AllegroMetricsStatusResponse,
    AllegroPayment,
    ApplyJobResponse,
    ApplyPayload,
)
from api.models.user_secrets import UserSecretResponse
from services.allegro_application_service import AllegroApplicationService
from services.domain.allegro import AllegroPageRequest
from services.exceptions import (
    ExternalServiceFailed,
    InvalidFileId,
    InvalidMatchSelection,
    InvalidSecretId,
    MatchesNotComputed,
    TransactionNotFound,
)
from services.guards import require_active_user

router = APIRouter(
    prefix="/api/allegro",
    tags=["allegro"],
    dependencies=[Depends(require_active_user)],
)
logger = logging.getLogger(__name__)


# --------------------------------------------------
# Endpoints
# --------------------------------------------------


@router.get("/secrets", response_model=list[UserSecretResponse])
def list_secrets(
    user_id: UUID = Depends(require_active_user),
    svc: AllegroApplicationService = Depends(get_allegro_application_runtime),
):
    return svc.get_allegro_secrets(user_id=user_id)


@router.get("/{secret_id}/payments", response_model=list[AllegroPayment])
def fetch_for_id(
    secret_id: str,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: UUID = Depends(require_active_user),
    svc: AllegroApplicationService = Depends(get_allegro_application_runtime),
):
    page = AllegroPageRequest(limit=limit, offset=offset)
    try:
        payments = svc.fetch_allegro_data(
            user_id=user_id,
            secret_id=UUID(secret_id),
            page=page,
        )
        return map_allegro_payments_to_response(payments)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid secret_id") from e
    except InvalidSecretId as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ExternalServiceFailed as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.get("/{secret_id}/matches", response_model=AllegroMatchResponse)
async def preview_matches(
    secret_id: str,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: UUID = Depends(require_active_user),
    svc: AllegroApplicationService = Depends(get_allegro_application_runtime),
):
    page = AllegroPageRequest(limit=limit, offset=offset)
    try:
        data = await svc.preview_matches(
            user_id=user_id,
            secret_id=UUID(secret_id),
            page=page,
        )
        return data
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid secret_id") from e
    except InvalidSecretId as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MatchesNotComputed as e:
        raise HTTPException(status_code=400, detail="No match data found") from e
    except TransactionNotFound as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except InvalidMatchSelection as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ExternalServiceFailed as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


@router.post("/{secret_id}/apply", response_model=ApplyJobResponse)
async def apply_matches(
    secret_id: str,
    payload: ApplyPayload,
    svc: AllegroApplicationService = Depends(get_allegro_application_runtime),
):
    try:
        job = await svc.start_apply_job(
            secret_id=UUID(secret_id), decisions=map_payload_to_decisions(payload)
        )
        return map_job_to_response(job)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid secret_id") from e
    except InvalidSecretId as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
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


@router.post("/{secret_id}/apply/auto", response_model=ApplyJobResponse)
async def auto_apply_single_matches(
    secret_id: str,
    limit: int | None = Query(default=None, ge=1, le=500),
    # dry_run: bool = Query(default=False),
    # user_id: UUID = Depends(require_active_user),
    svc: AllegroApplicationService = Depends(get_allegro_application_runtime),
):
    """
    Automatically apply matches that have exactly one candidate match.
    Requires that /{secret_id}/matches was called before (preview snapshot exists).
    """
    try:
        result = await svc.start_auto_apply_single_matches(
            secret_id=UUID(secret_id), limit=limit
        )

        # result is expected to contain:
        # - job: AllegroApplyJob | None
        # - auto_selected: int
        # - skipped: int
        # - dry_run: bool
        return map_job_to_response(result)

    except MatchesNotComputed as e:
        raise HTTPException(
            status_code=400, detail="No match data found; run preview first"
        ) from e
    except ExternalServiceFailed as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except ValueError as e:
        # UUID(secret_id) parsing error
        raise HTTPException(status_code=400, detail="Invalid secret_id") from e


@router.delete("/{secret_id}/cache")
def clear_cache_for_secret(
    secret_id: str,
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int | None = Query(default=None, ge=0),
    svc: AllegroApplicationService = Depends(get_allegro_application_runtime),
):
    if (limit is None) != (offset is None):
        raise HTTPException(
            status_code=400,
            detail="Provide both limit and offset to clear a single page cache",
        )

    try:
        secret_uuid = UUID(secret_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid secret_id") from e

    if limit is None and offset is None:
        cleared = svc.clear_cached_secret(secret_id=secret_uuid)
        return {"scope": "secret", "cleared": cleared}

    assert limit is not None and offset is not None
    page = AllegroPageRequest(limit=limit, offset=offset)
    cleared = svc.clear_cached_page(secret_id=secret_uuid, page=page)
    return {
        "scope": "page",
        "cleared": cleared,
        "limit": page.limit,
        "offset": page.offset,
    }


@router.get("/apply-jobs/{job_id}", response_model=ApplyJobResponse)
def get_apply_job(
    job_id: str,
    svc: AllegroApplicationService = Depends(get_allegro_application_runtime),
):
    job = svc.state_store.job_manager.get(UUID(job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return map_job_to_response(job)


# --------------------------------------------------
# Metrics
# --------------------------------------------------
@router.get(
    "/statistics",
    response_model=AllegroMetricsStatusResponse,
)
async def get_statistics_current(
    svc: AllegroApplicationService = Depends(get_allegro_application_runtime),
):
    state = svc.get_metrics_state()
    return map_allegro_metrics_state_to_response(state)


@router.post(
    "/statistics/refresh",
    response_model=AllegroMetricsStatusResponse,
)
async def refresh_statistics_current(
    svc: AllegroApplicationService = Depends(get_allegro_application_runtime),
):
    state = await svc.refresh_metrics_state()
    return map_allegro_metrics_state_to_response(state)
