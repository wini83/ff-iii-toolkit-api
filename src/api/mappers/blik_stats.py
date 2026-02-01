from api.models.blik_stats import (
    BlikMetricsResultResponse,
    BlikMetricsStatusResponse,
)
from services.domain.metrics import BlikStatisticsMetrics
from services.tx_stats.models import MetricsState


def map_blik_metrics_state_to_response(
    state: MetricsState[BlikStatisticsMetrics],
) -> BlikMetricsStatusResponse:
    result = None
    if state.result is not None:
        result = BlikMetricsResultResponse(
            single_part_transactions=state.result.single_part_transactions,
            uncategorized_transactions=state.result.uncategorized_transactions,
            filtered_by_description_exact=state.result.filtered_by_description_exact,
            filtered_by_description_partial=state.result.filtered_by_description_partial,
            not_processed_transactions=state.result.not_processed_transactions,
            not_processed_by_month=state.result.not_processed_by_month,
            inclomplete_procesed_by_month=state.result.inclomplete_procesed_by_month,
            time_stamp=state.result.time_stamp,
            fetch_seconds=state.result.fetching_duration_ms / 1000.0,
        )

    return BlikMetricsStatusResponse(
        status=state.status.value,
        progress=state.progress,
        result=result,
        error=state.error,
    )
