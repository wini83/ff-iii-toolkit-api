from collections.abc import Iterable

from api.mappers.job_status import map_status
from api.mappers.tx import map_tx_to_api
from api.models.allegro import (
    AllegroMatchResponse,
    AllegroMetricsResultResponse,
    AllegroMetricsStatusResponse,
    AllegroPayment,
    ApplyJobResponse,
    ApplyOutcomeResponse,
    ApplyPayload,
)
from api.models.allegro import MatchResult as ApiMatchResult
from api.models.tx import MatchProcessingStatus as MatchProcessingStatus
from services.domain.allegro import (
    AllegroApplyJob,
    AllegroMatchPreview,
    ApplyOutcome,
    MatchDecision,
)
from services.domain.allegro import AllegroOrderPayment as AllegroOrderPaymentDomain
from services.domain.allegro import AllegroOrderPayments as AllegroOrderPaymentsDomain
from services.domain.match_result import (
    MatchProcessingStatus as DomainMatchProcessingStatus,
)
from services.domain.match_result import MatchResult as DomainMatchResult
from services.domain.metrics import AllegroMetrics
from services.domain.transaction import Transaction
from services.tx_stats.models import MetricsState

DOMAIN_TO_API_STATUS = {
    DomainMatchProcessingStatus.NEW: MatchProcessingStatus.NEW,
    DomainMatchProcessingStatus.ALREADY_PROCESSED: MatchProcessingStatus.ALREADY_PROCESSED,
}


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
        status=map_status(state.status),
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
        external_id=payment.external_id,
        external_short_id=payment.external_short_id,
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
        status=DOMAIN_TO_API_STATUS[result.status],
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


def map_match_preview_to_api(preview: AllegroMatchPreview) -> AllegroMatchResponse:
    return AllegroMatchResponse(
        login=preview.login,
        payments_fetched=preview.payments_fetched,
        transactions_found=preview.transactions_found,
        transactions_not_matched=preview.transactions_not_matched,
        transactions_with_one_match=preview.transactions_with_one_match,
        transactions_with_many_matches=preview.transactions_with_many_matches,
        fetch_seconds=preview.fetch_seconds,
        content=map_match_results_to_api(preview.content),
        unmatched_payments=[
            map_allegro_payment_to_response(payment)
            for payment in preview.unmatched_payments
        ],
    )


def map_job_to_response(job: AllegroApplyJob) -> ApplyJobResponse:
    return ApplyJobResponse(
        id=job.id,
        secret_id=job.secret_id,
        status=map_status(job.status),
        total=job.total,
        applied=job.applied,
        failed=job.failed,
        started_at=job.started_at,
        finished_at=job.finished_at,
        results=[map_apply_outcome_to_response(result) for result in job.results],
    )


def map_apply_outcome_to_response(outcome: ApplyOutcome) -> ApplyOutcomeResponse:
    return ApplyOutcomeResponse(
        transaction_id=outcome.transaction_id,
        status=outcome.status,
        reason=outcome.reason,
    )


def map_payload_to_decisions(
    payload: ApplyPayload,
) -> list[MatchDecision]:
    return [
        MatchDecision(
            payment_id=d.payment_id,
            transaction_id=d.transaction_id,
            strategy=d.strategy,
        )
        for d in payload.decisions
    ]
