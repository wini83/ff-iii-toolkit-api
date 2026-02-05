from api.models.allegro import (
    AllegroMetricsResultResponse,
    AllegroMetricsStatusResponse,
)
from services.domain.metrics import AllegroMetrics
from services.tx_stats.models import MetricsState


def map_allegro_metrics_state_to_response(
    state: MetricsState[AllegroMetrics],
) -> AllegroMetricsStatusResponse:
    result = None
    if state.result is not None:
        result = AllegroMetricsResultResponse(
            total_transactions=state.result.total_transactions,
            allegro_transactions=state.result.allegro_transactions,
            not_processed__allegro_transactions=state.result.not_processed_allegro_transactions,
            not_processed_by_month=state.result.not_processed_by_month,
            time_stamp=state.result.time_stamp,
            fetch_seconds=state.result.fetching_duration_ms / 1000.0,
        )

    return AllegroMetricsStatusResponse(
        status=state.status.value,
        progress=state.progress,
        result=result,
        error=state.error,
    )
