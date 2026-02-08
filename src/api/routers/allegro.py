import logging
from uuid import UUID

from fastapi import APIRouter, Depends

from api.deps_runtime import get_allegro_application_runtime
from api.mappers.allegro import (
    map_allegro_metrics_state_to_response,
    map_allegro_payments_to_response,
)
from api.models.allegro import (
    AllegroMatchResponse,
    AllegroMetricsStatusResponse,
    AllegroPayment,
)
from api.models.user_secrets import UserSecretResponse
from services.allegro_application_service import AllegroApplicationService
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
    user_id: UUID = Depends(require_active_user),
    svc: AllegroApplicationService = Depends(get_allegro_application_runtime),
):
    payments = svc.fetch_allegro_data(user_id=user_id, secret_id=UUID(secret_id))
    return map_allegro_payments_to_response(payments)


@router.get("/{secret_id}/matches", response_model=AllegroMatchResponse)
async def preview_matches(
    secret_id: str,
    user_id: UUID = Depends(require_active_user),
    svc: AllegroApplicationService = Depends(get_allegro_application_runtime),
):
    data = await svc.preview_matches(user_id=user_id, secret_id=UUID(secret_id))
    return data


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
