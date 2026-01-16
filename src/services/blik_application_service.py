import asyncio
import logging
import os
import re
import tempfile
from typing import cast

from api.mappers.blik import (
    map_bank_records_to_simplified,
    map_blik_metrics_to_api,
    map_match_results_to_api,
)
from api.models.blik_files import (
    ApplyPayload,
    FileApplyResponse,
    FileMatchResponse,
    FilePreviewResponse,
    StatisticsResponse,
    UploadResponse,
)
from services.csv_reader import BankCSVReader
from services.domain.bank_record import BankRecord
from services.domain.match_result import MatchResult
from services.domain.transaction import Transaction
from services.exceptions import (
    ExternalServiceFailed,
    FileNotFound,
    InvalidFileId,
    InvalidMatchSelection,
    MatchesNotComputed,
    TransactionNotFound,
)
from services.firefly_base_service import FireflyServiceError
from services.firefly_blik_service import FireflyBlikService
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
        blik_service: FireflyBlikService,
    ) -> None:
        self.blik_service = blik_service

        self._matches_cache: dict[str, list[MatchResult]] = {}
        self._stats_cache: StatisticsResponse | None = None
        self._stats_lock = asyncio.Lock()

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
            matches = await self.blik_service.match(
                candidates=csv_records,
                filter_text=settings.BLIK_DESCRIPTION_FILTER,
                tag_done=settings.TAG_BLIK_DONE,
            )
        except FireflyServiceError as e:
            raise ExternalServiceFailed(str(e)) from e
        self._matches_cache[encoded_id] = matches

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

    async def apply_matches(
        self,
        *,
        encoded_id: str,
        payload: ApplyPayload,
    ) -> FileApplyResponse:
        if encoded_id not in self._matches_cache:
            raise MatchesNotComputed("No match data found")

        matches = self._matches_cache[encoded_id]
        index = {int(cast(Transaction, m.tx).id): m for m in matches}

        to_update: list[MatchResult] = []

        for tx_id in payload.tx_indexes:
            match = index.get(tx_id)
            if not match:
                raise TransactionNotFound(f"Transaction id {tx_id} not found")
            if len(match.matches) != 1:
                raise InvalidMatchSelection(
                    f"Transaction id {tx_id} does not have exactly one match"
                )
            to_update.append(match)

        updated = 0
        errors: list[str] = []

        for match in to_update:
            tx = cast(Transaction, match.tx)
            try:
                evidence = cast(BankRecord, match.matches[0])
                await self.blik_service.apply_match(tx=tx, evidence=evidence)
                updated += 1
            except FireflyServiceError as e:
                errors.append(f"Error updating transaction id {tx.id}: {str(e)}")

        return FileApplyResponse(
            file_id=encoded_id,
            updated=updated,
            errors=errors,
        )

    # --------------------------------------------------
    # STATISTICS
    # --------------------------------------------------

    async def get_statistics(self, *, refresh: bool = False) -> StatisticsResponse:
        async with self._stats_lock:
            if self._stats_cache is None or refresh:
                try:
                    domain_metrics = await self.blik_service.fetch_blik_metrics()
                except FireflyServiceError as e:
                    raise ExternalServiceFailed(str(e)) from e
                self._stats_cache = map_blik_metrics_to_api(domain_metrics)
        return self._stats_cache

    # --------------------------------------------------
    # INTERNAL HELPERS
    # --------------------------------------------------

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
