from collections.abc import Iterable

from api.mappers.tx import map_tx_to_api
from api.models.allegro import (
    AllegroMetricsResultResponse,
    AllegroMetricsStatusResponse,
    AllegroPayment,
)
from api.models.allegro import MatchResult as ApiMatchResult
from services.domain.allegro import AllegroOrderPayment as AllegroOrderPaymentDomain
from services.domain.allegro import AllegroOrderPayments as AllegroOrderPaymentsDomain
from services.domain.match_result import MatchResult as DomainMatchResult
from services.domain.metrics import AllegroMetrics
from services.domain.transaction import Transaction
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


def map_allegro_payments_to_response(
    payload: AllegroOrderPaymentsDomain,
) -> list[AllegroPayment]:
    responses = []
    for payment in payload.payments:
        response = map_allegro_payment_to_response(payment)
        responses.append(response)
    return responses


def map_allegro_payment_to_response(
    payment: AllegroOrderPaymentDomain,
) -> AllegroPayment:
    return AllegroPayment(
        amount=float(payment.amount),
        date=payment.date,
        details=payment.details,
        is_balanced=payment.is_balanced,
        allegro_login=payment.allegro_login,
    )


def map_match_result_to_api(
    result: DomainMatchResult,
) -> ApiMatchResult:
    """
    Domain MatchResult -> API MatchResult

    Adapter legacy-safe.
    Zero UI changes.
    """
    if not isinstance(result.tx, Transaction):
        raise TypeError(f"Expected Transaction as tx, got {type(result.tx).__name__}")

    simplified_tx = map_tx_to_api(result.tx)

    matches_api: list[AllegroPayment] = []
    for m in result.matches:
        if not isinstance(m, AllegroOrderPaymentDomain):
            raise TypeError(
                f"Expected AllegroOrderPaymentDomain in matches, got {type(m).__name__}"
            )
        matches_api.append(map_allegro_payment_to_response(m))

    return ApiMatchResult(
        tx=simplified_tx,
        matches=matches_api,
    )


def map_match_results_to_api(
    results: Iterable[DomainMatchResult],
) -> list[ApiMatchResult]:
    """
    Bulk mapper: Domain MatchResult -> API MatchResult

    UI-safe
    legacy-preserving
    zero magic
    """
    return [map_match_result_to_api(result) for result in results]
