from asyncio import create_task
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from services.allegro_service import AllegroService
from services.allegro_state_store import AllegroStateStore
from services.allegro_stats.manager import AllegroMetricsManager
from services.domain.allegro import (
    AllegroAccount,
    AllegroApplyJob,
    AllegroMatchPreview,
    AllegroOrderPayment,
    AllegroOrderPayments,
    AllegroPageMatchCacheEntry,
    AllegroPageRequest,
    ApplyOutcome,
    MatchDecision,
)
from services.domain.job_base import JobStatus
from services.domain.match_result import MatchResult
from services.domain.metrics import AllegroMetrics
from services.domain.transaction import Transaction, TxTag
from services.domain.user_secrets import SecretType, UserSecretReadModel
from services.exceptions import (
    ExternalServiceFailed,
    InvalidMatchSelection,
    InvalidSecretId,
    MatchesNotComputed,
    TransactionNotFound,
)
from services.firefly_allegro_service import FireflyAllegroService
from services.firefly_base_service import FireflyServiceError
from services.tx_stats.models import MetricsState
from services.user_secrets_service import UserSecretsService


class AllegroApplicationService:
    def __init__(
        self,
        secrets_service: UserSecretsService,
        ff_allegro_service: FireflyAllegroService,
        allegro_service: AllegroService,
        state_store: AllegroStateStore,
    ) -> None:
        self.secrets_service = secrets_service
        self.ff_allegro_service = ff_allegro_service
        self.allegro_service = allegro_service
        self.state_store = state_store
        if self.state_store.metrics_manager is None:
            self.state_store.metrics_manager = AllegroMetricsManager(
                ff_allegro_service=self.ff_allegro_service
            )

    def get_allegro_secrets(self, user_id: UUID) -> list[UserSecretReadModel]:
        secrets = self.secrets_service.list_for_user(user_id=user_id)
        allegro_secrets = [
            secret for secret in secrets if secret.type == SecretType.ALLEGRO
        ]
        return allegro_secrets

    def fetch_allegro_data(
        self,
        *,
        user_id: UUID,
        secret_id: UUID,
        page: AllegroPageRequest,
    ) -> AllegroOrderPayments:
        try:
            secret = self.secrets_service.get_for_internal_use(
                secret_id=secret_id, user_id=user_id
            )
        except Exception as e:
            raise InvalidSecretId(
                f"Secret with id {secret_id} not found for user {user_id}"
            ) from e
        account = AllegroAccount(secret=secret.secret, id=secret.id)
        try:
            data = self.allegro_service.fetch(
                account=account,
                limit=page.limit,
                offset=page.offset,
            )
            return data
        except Exception as e:
            raise ExternalServiceFailed(
                f"Failed to fetch allegro data for secret {secret_id}"
            ) from e

    async def _match_page(
        self, *, payments: list[AllegroOrderPayment]
    ) -> tuple[list[MatchResult], list[AllegroOrderPayment]]:
        try:
            matches, unmatched = await self.ff_allegro_service.match_with_unmatched(
                filter_text=self.ff_allegro_service.filter_desc_allegro,
                tag_done=TxTag.allegro_done,
                candidates=payments,
            )
            unmatched_payments = [cast(AllegroOrderPayment, item) for item in unmatched]
            return matches, unmatched_payments
        except FireflyServiceError as e:
            raise ExternalServiceFailed(str(e)) from e

    def _cache_page(
        self,
        *,
        secret_id: UUID,
        page: AllegroPageRequest,
        payments: list[AllegroOrderPayment],
        matches: list[MatchResult],
    ) -> None:
        login = payments[0].allegro_login if payments else "unknown"
        self.state_store.put_page_matches(
            secret_id=secret_id,
            entry=AllegroPageMatchCacheEntry(
                page=page,
                login=login,
                payments=payments,
                matches=matches,
            ),
        )

    async def preview_matches(
        self,
        *,
        user_id: UUID,
        secret_id: UUID,
        page: AllegroPageRequest | None = None,
    ) -> AllegroMatchPreview:
        page_request = page or AllegroPageRequest()
        payments = self.fetch_allegro_data(
            user_id=user_id,
            secret_id=secret_id,
            page=page_request,
        )

        matches, unmatched_payments = await self._match_page(payments=payments.payments)
        self._cache_page(
            secret_id=secret_id,
            page=page_request,
            payments=payments.payments,
            matches=matches,
        )

        login = payments.payments[0].allegro_login if payments.payments else "unknown"
        not_matched = len([r for r in matches if not r.matches])
        with_one_match = len([r for r in matches if len(r.matches) == 1])
        with_many_matches = len([r for r in matches if len(r.matches) > 1])

        return AllegroMatchPreview(
            login=login,
            payments_fetched=len(payments.payments),
            transactions_found=len(matches),
            transactions_not_matched=not_matched,
            transactions_with_one_match=with_one_match,
            transactions_with_many_matches=with_many_matches,
            fetch_seconds=0.0,  # TODO: measure time taken for matching
            content=matches,
            unmatched_payments=unmatched_payments,
        )

    async def start_apply_job(
        self,
        *,
        secret_id: UUID,
        decisions: list[MatchDecision],
    ) -> AllegroApplyJob:
        matches = self.state_store.get_all_matches(secret_id=secret_id)
        if not matches:
            raise MatchesNotComputed()

        job = self.state_store.job_manager.create(
            secret_id=secret_id,
            total=len(decisions),
        )

        create_task(
            self._run_apply_job(
                job=job,
                decisions=decisions,
                matches=matches,
            )
        )

        return job

    def _index_matches(self, match: MatchResult) -> dict[str, AllegroOrderPayment]:
        index = {
            cast(AllegroOrderPayment, m).external_short_id: cast(AllegroOrderPayment, m)
            for m in match.matches
        }
        return index

    async def _run_apply_job(
        self,
        *,
        job: AllegroApplyJob,
        decisions: list[MatchDecision],
        matches: list[MatchResult],
    ):
        job.status = JobStatus.RUNNING

        index = {int(cast(Transaction, m.tx).id): m for m in matches}

        for decision in decisions:
            tx_id = decision.transaction_id
            try:
                match_result = index.get(tx_id)
                if not match_result:
                    raise TransactionNotFound(f"Transaction id {tx_id} not found")
                result_matches = self._index_matches(match_result)
                payment = result_matches.get(decision.payment_id)
                if not payment:
                    raise InvalidMatchSelection(
                        f"Payment id {decision.payment_id} not found for transaction id {tx_id}"  # shortID
                    )
                tx = cast(Transaction, match_result.tx)
                await self.ff_allegro_service.apply_match(tx=tx, evidence=payment)
                job.applied += 1
                job.results.append(ApplyOutcome(transaction_id=tx_id, status="success"))

            except Exception as e:
                job.failed += 1
                job.results.append(
                    ApplyOutcome(transaction_id=tx_id, status="failed", reason=str(e))
                )

        job.status = JobStatus.DONE
        job.finished_at = datetime.now(UTC)

    async def start_auto_apply_single_matches(
        self,
        *,
        secret_id: UUID,
        limit: int | None = None,
    ) -> AllegroApplyJob:
        matches = self.state_store.get_all_matches(secret_id=secret_id)
        if not matches:
            raise MatchesNotComputed()
        single = [m for m in matches if len(m.matches) == 1]

        if limit:
            single = single[:limit]

        decisions = [
            MatchDecision(
                transaction_id=int(cast(Transaction, m.tx).id),
                payment_id=cast(AllegroOrderPayment, m.matches[0]).external_short_id,
            )
            for m in single
        ]

        return await self.start_apply_job(
            secret_id=secret_id,
            decisions=decisions,
        )

    def clear_cached_page(self, *, secret_id: UUID, page: AllegroPageRequest) -> bool:
        return self.state_store.invalidate_page(secret_id=secret_id, page=page)

    def clear_cached_secret(self, *, secret_id: UUID) -> bool:
        return self.state_store.invalidate_secret(secret_id=secret_id)

    # --------------------------------------------------
    # METRICS V2
    # --------------------------------------------------

    def _ensure_metrics_manager(self) -> AllegroMetricsManager:
        if self.state_store.metrics_manager is None:
            self.state_store.metrics_manager = AllegroMetricsManager(
                ff_allegro_service=self.ff_allegro_service
            )
        return self.state_store.metrics_manager

    def get_metrics_state(self) -> MetricsState[AllegroMetrics]:
        manager = self._ensure_metrics_manager()
        return manager.get_state()

    async def refresh_metrics_state(self) -> MetricsState[AllegroMetrics]:
        manager = self._ensure_metrics_manager()
        return await manager.refresh()
