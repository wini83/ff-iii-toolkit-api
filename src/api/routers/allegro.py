import logging

from fastapi import APIRouter, Depends

from api.deps_runtime import get_allegro_application_runtime
from api.mappers.allegro import map_allegro_metrics_state_to_response
from api.models.allegro import AllegroMetricsStatusResponse
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
