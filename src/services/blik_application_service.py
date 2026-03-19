import logging
import os
import re
import tempfile
from asyncio import create_task
from datetime import UTC, datetime
from typing import cast
from uuid import UUID

from api.mappers.blik import (
    build_blik_match_id,
    map_bank_records_to_simplified,
    map_match_results_to_api,
)
from api.models.blik_files import (
    FileMatchResponse,
    FilePreviewResponse,
    UploadResponse,
)
from services.blik_state_store import BlikStateStore
from services.blik_stats.manager import BlikMetricsManager
from services.csv_reader import BankCSVReader
from services.domain.bank_record import BankRecord
from services.domain.blik import ApplyOutcome, BlikApplyJob, MatchDecision
from services.domain.job_base import JobStatus
from services.domain.match_result import MatchResult
from services.domain.metrics import BlikStatisticsMetrics
from services.domain.transaction import Transaction, TxTag
from services.exceptions import (
    ExternalServiceFailed,
    FileNotFound,
    InvalidFileId,
    InvalidMatchSelection,
    MatchesNotComputed,
    TransactionNotFound,
)
from services.firefly_base_service import FireflyServiceError
from services.firefly_enrichment_service import FireflyEnrichmentService
from services.tx_stats.models import MetricsState
from services.tx_stats.runner import MetricsProvider
from settings import settings
from utils.encoding import decode_base64url, encode_base64url

logger = logging.getLogger(__name__)

SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


class BlikApplicationService:
    """
    Application-level service for BLIK flows.

    Responsibilities:
    - manage CSV lifecycle
    - run enrichment preview / apply
    - keep in-memory state (matches, statistics)
    - expose data in API DTO shape (router stays thin)
    """

    def __init__(
        self,
        *,
        enrichment_service: FireflyEnrichmentService,
        metrics_provider: MetricsProvider[BlikStatisticsMetrics],
        state_store: BlikStateStore,
    ) -> None:
        self.enrichment_service = enrichment_service
        self.metrics_provider = metrics_provider
        self.state_store = state_store
        self.blik_metrics_manager = BlikMetricsManager(provider=metrics_provider)

    # --------------------------------------------------
    # CSV lifecycle
    # --------------------------------------------------

    async def upload_csv(self, *, file_bytes: bytes) -> UploadResponse:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        records = BankCSVReader(tmp_path).parse()

        filename = os.path.basename(tmp_path)
        file_id = os.path.splitext(filename)[0]
        encoded = encode_base64url(file_id)

        return UploadResponse(
            message="File uploaded successfully", count=len(records), id=encoded
        )

    async def preview_csv(self, *, encoded_id: str) -> FilePreviewResponse:
        decoded = decode_base64url(encoded_id)
        self._validate_file_id(decoded)

        path = self._resolve_csv_path(decoded)
        records_domain = BankCSVReader(path).parse()

        records = map_bank_records_to_simplified(records=records_domain)

        return FilePreviewResponse(
            file_id=encoded_id,
            decoded_name=decoded,
            size=len(records),
            content=records,
        )

    # --------------------------------------------------
    # MATCHING
    # --------------------------------------------------

    async def preview_matches(self, *, encoded_id: str) -> FileMatchResponse:
        decoded = decode_base64url(encoded_id)
        self._validate_file_id(decoded)

        path = self._resolve_csv_path(decoded)
        csv_records = BankCSVReader(path).parse()
        try:
            matches = await self.enrichment_service.match(
                candidates=csv_records,
                filter_text=settings.BLIK_DESCRIPTION_FILTER,
                tag_done=TxTag.blik_done,
            )
        except FireflyServiceError as e:
            raise ExternalServiceFailed(str(e)) from e
        self.state_store.put_matches(file_id=encoded_id, matches=matches)

        not_matched = len([r for r in matches if not r.matches])
        with_one_match = len([r for r in matches if len(r.matches) == 1])
        with_many_matches = len([r for r in matches if len(r.matches) > 1])

        matches_api = map_match_results_to_api(results=matches)

        return FileMatchResponse(
            file_id=encoded_id,
            decoded_name=decoded,
            records_in_file=len(csv_records),
            transactions_found=len(matches),
            transactions_not_matched=not_matched,
            transactions_with_one_match=with_one_match,
            transactions_with_many_matches=with_many_matches,
            content=matches_api,
        )

    # --------------------------------------------------
    # APPLY
    # --------------------------------------------------

    async def start_apply_job(
        self,
        *,
        encoded_id: str,
        decisions: list[MatchDecision],
    ) -> BlikApplyJob:
        matches = self.state_store.get_matches(file_id=encoded_id)
        if not matches:
            raise MatchesNotComputed("No match data found")

        job = self.state_store.job_manager.create(
            file_id=encoded_id, total=len(decisions)
        )

        create_task(
            self._run_apply_job(
                job=job,
                decisions=decisions,
                matches=matches,
            )
        )

        return job

    async def start_auto_apply_single_matches(
        self,
        *,
        encoded_id: str,
        limit: int | None = None,
    ) -> BlikApplyJob:
        matches = self.state_store.get_matches(file_id=encoded_id)
        if not matches:
            raise MatchesNotComputed("No match data found")

        single_matches = [match for match in matches if len(match.matches) == 1]
        if limit is not None:
            single_matches = single_matches[:limit]

        decisions = [
            MatchDecision(
                transaction_id=int(cast(Transaction, match.tx).id),
                selected_match_id=build_blik_match_id(
                    transaction_id=int(cast(Transaction, match.tx).id),
                    record=cast(BankRecord, match.matches[0]),
                ),
            )
            for match in single_matches
        ]

        return await self.start_apply_job(encoded_id=encoded_id, decisions=decisions)

    def get_apply_job(self, *, job_id: UUID) -> BlikApplyJob | None:
        return self.state_store.job_manager.get(job_id)

    # --------------------------------------------------
    # METRICS V2
    # --------------------------------------------------

    async def get_metrics_state(self) -> MetricsState[BlikStatisticsMetrics]:
        return await self.blik_metrics_manager.ensure_current()

    async def refresh_metrics_state(self) -> MetricsState[BlikStatisticsMetrics]:
        return await self.blik_metrics_manager.refresh()

    async def _run_apply_job(
        self,
        *,
        job: BlikApplyJob,
        decisions: list[MatchDecision],
        matches: list[MatchResult],
    ) -> None:
        job.status = JobStatus.RUNNING

        try:
            outcomes = await self._apply_decisions(decisions=decisions, matches=matches)
            for outcome in outcomes:
                if outcome.status == "success":
                    job.applied += 1
                else:
                    job.failed += 1
                job.results.append(outcome)
            job.status = JobStatus.DONE
        except Exception as e:
            job.status = JobStatus.FAILED
            job.results.append(
                ApplyOutcome(
                    transaction_id=-1,
                    selected_match_id=None,
                    status="failed",
                    reason=str(e),
                )
            )
        finally:
            job.finished_at = datetime.now(UTC)

    # --------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------

    def _build_single_match_decisions(
        self,
        *,
        matches: list[MatchResult],
        tx_ids: list[int],
    ) -> list[MatchDecision]:
        index = {int(cast(Transaction, match.tx).id): match for match in matches}
        decisions: list[MatchDecision] = []

        for tx_id in tx_ids:
            match = index.get(tx_id)
            if not match:
                raise TransactionNotFound(f"Transaction id {tx_id} not found")
            if len(match.matches) != 1:
                raise InvalidMatchSelection(
                    f"Transaction id {tx_id} does not have exactly one match"
                )

            decisions.append(
                MatchDecision(
                    transaction_id=tx_id,
                    selected_match_id=build_blik_match_id(
                        transaction_id=tx_id,
                        record=cast(BankRecord, match.matches[0]),
                    ),
                )
            )

        return decisions

    async def _apply_decisions(
        self,
        *,
        decisions: list[MatchDecision],
        matches: list[MatchResult],
    ) -> list[ApplyOutcome]:
        outcomes: list[ApplyOutcome] = []
        index = {int(cast(Transaction, match.tx).id): match for match in matches}

        for decision in decisions:
            tx_id = decision.transaction_id
            try:
                match = index.get(tx_id)
                if not match:
                    raise TransactionNotFound(f"Transaction id {tx_id} not found")

                evidence = self._find_selected_match(
                    transaction_id=tx_id,
                    match=match,
                    selected_match_id=decision.selected_match_id,
                )
                tx = cast(Transaction, match.tx)
                await self.enrichment_service.apply_match(tx=tx, evidence=evidence)
                outcomes.append(
                    ApplyOutcome(
                        transaction_id=tx_id,
                        selected_match_id=decision.selected_match_id,
                        status="success",
                    )
                )
            except (FireflyServiceError, ExternalServiceFailed) as e:
                outcomes.append(
                    ApplyOutcome(
                        transaction_id=tx_id,
                        selected_match_id=decision.selected_match_id,
                        status="failed",
                        reason=str(e),
                    )
                )
            except Exception as e:
                outcomes.append(
                    ApplyOutcome(
                        transaction_id=tx_id,
                        selected_match_id=decision.selected_match_id,
                        status="failed",
                        reason=str(e),
                    )
                )

        return outcomes

    def _find_selected_match(
        self,
        *,
        transaction_id: int,
        match: MatchResult,
        selected_match_id: str,
    ) -> BankRecord:
        candidates = {
            build_blik_match_id(
                transaction_id=transaction_id, record=cast(BankRecord, record)
            ): cast(BankRecord, record)
            for record in match.matches
        }
        evidence = candidates.get(selected_match_id)
        if evidence is None:
            raise InvalidMatchSelection(
                f"Match id {selected_match_id} not found for transaction id {transaction_id}"
            )
        return evidence

    @staticmethod
    def _validate_file_id(decoded: str) -> None:
        if "/" in decoded or ".." in decoded:
            raise InvalidFileId("Invalid file id")

    @staticmethod
    def _resolve_csv_path(decoded: str) -> str:
        if not SAFE_NAME_RE.match(decoded):
            raise FileNotFound("Invalid file identifier")

        base_dir = tempfile.gettempdir()
        filename = f"{decoded}.csv"
        full_path = os.path.normpath(os.path.join(base_dir, filename))

        if not full_path.startswith(os.path.abspath(base_dir)):
            raise FileNotFound("Invalid file path")

        if not os.path.exists(full_path):
            raise FileNotFound("File not found")

        return full_path
