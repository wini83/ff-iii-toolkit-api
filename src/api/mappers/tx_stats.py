from api.models.tx_stats import (
    TxMetricsResultResponse,
    TxMetricsStatusResponse,
)
from services.domain.metrics import TXStatisticsMetrics
from services.tx_stats.models import MetricsState


def map_tx_state_to_response(
    state: MetricsState[TXStatisticsMetrics],
) -> TxMetricsStatusResponse:
    result = None
    if state.result is not None:
        result = TxMetricsResultResponse(
            single_part_transactions=state.result.single_part_transactions,
            uncategorized_transactions=state.result.uncategorized_transactions,
            blik_not_ok=state.result.blik_not_ok,
            action_req=state.result.action_req,
            allegro_not_ok=state.result.allegro_not_ok,
            categorizable=state.result.categorizable,
            categorizable_by_month=state.result.categorizable_by_month,
            time_stamp=state.result.time_stamp,
            fetch_seconds=state.result.fetching_duration_ms / 1000.0,
        )

    return TxMetricsStatusResponse(
        status=state.status.value,
        progress=state.progress,
        result=result,
        error=state.error,
    )
