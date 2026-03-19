from abc import ABC, abstractmethod
from datetime import datetime

from services.domain.metrics import (
    AllegroMetrics,
    BlikStatisticsMetrics,
    TXStatisticsMetrics,
)
from services.domain.transaction import TxTag
from services.firefly_base_service import filter_by_description, filter_out_categorized
from services.snapshot.models import TransactionSnapshot
from services.snapshot.service import TransactionSnapshotService
from services.tx_stats.helpers import group_tx_by_month


class SnapshotMetricsService[T](ABC):
    def __init__(self, snapshot_service: TransactionSnapshotService) -> None:
        self.snapshot_service = snapshot_service

    async def fetch_metrics(self) -> T:
        snapshot = await self.snapshot_service.get_snapshot()
        return await self._build_metrics(snapshot)

    async def refresh_metrics(self) -> T:
        snapshot = await self.snapshot_service.refresh_snapshot()
        return await self._build_metrics(snapshot)

    async def get_cached_snapshot_timestamp(self) -> datetime | None:
        return await self.snapshot_service.get_cached_snapshot_timestamp()

    @abstractmethod
    async def _build_metrics(self, snapshot: TransactionSnapshot) -> T:
        raise NotImplementedError


class SnapshotAllegroMetricsService(SnapshotMetricsService[AllegroMetrics]):
    def __init__(
        self,
        snapshot_service: TransactionSnapshotService,
        filter_desc_allegro: str,
    ) -> None:
        super().__init__(snapshot_service)
        self.filter_desc_allegro = filter_desc_allegro

    async def _build_metrics(self, snapshot: TransactionSnapshot) -> AllegroMetrics:
        filtered_by_desc_partial = filter_by_description(
            snapshot.transactions,
            self.filter_desc_allegro,
            exact_match=False,
        )
        not_processed = [
            tx
            for tx in filtered_by_desc_partial
            if not tx.tags or TxTag.allegro_done not in tx.tags
        ]
        not_processed_by_month = await group_tx_by_month(not_processed)

        return AllegroMetrics(
            total_transactions=snapshot.metrics.total_transactions,
            fetching_duration_ms=snapshot.metrics.fetching_duration_ms,
            allegro_transactions=len(filtered_by_desc_partial),
            not_processed_allegro_transactions=len(not_processed),
            not_processed_by_month=not_processed_by_month,
            time_stamp=snapshot.fetched_at,
        )


class SnapshotBlikMetricsService(SnapshotMetricsService[BlikStatisticsMetrics]):
    def __init__(
        self,
        snapshot_service: TransactionSnapshotService,
        filter_desc_blik: str,
    ) -> None:
        super().__init__(snapshot_service)
        self.filter_desc_blik = filter_desc_blik

    async def _build_metrics(
        self, snapshot: TransactionSnapshot
    ) -> BlikStatisticsMetrics:
        uncategorized = filter_out_categorized(snapshot.transactions)
        filtered_by_desc_exact = filter_by_description(
            uncategorized,
            self.filter_desc_blik,
            exact_match=True,
        )
        filtered_by_desc_partial = filter_by_description(
            uncategorized,
            self.filter_desc_blik,
            exact_match=False,
        )

        not_processed = [
            tx
            for tx in filtered_by_desc_exact
            if not tx.tags or TxTag.blik_done not in tx.tags
        ]
        incomplete_processed = [
            tx
            for tx in filtered_by_desc_partial
            if not tx.tags or TxTag.blik_done not in tx.tags
        ]
        not_processed_by_month = await group_tx_by_month(not_processed)
        incomplete_processed_by_month = await group_tx_by_month(incomplete_processed)

        return BlikStatisticsMetrics(
            total_transactions=snapshot.metrics.total_transactions,
            single_part_transactions=len(snapshot.transactions),
            uncategorized_transactions=len(uncategorized),
            filtered_by_description_exact=len(not_processed),
            filtered_by_description_partial=len(incomplete_processed),
            not_processed_transactions=len(not_processed),
            not_processed_by_month=not_processed_by_month,
            inclomplete_procesed_by_month=incomplete_processed_by_month,
            time_stamp=snapshot.fetched_at,
            fetching_duration_ms=snapshot.metrics.fetching_duration_ms,
        )


class SnapshotTxMetricsService(SnapshotMetricsService[TXStatisticsMetrics]):
    def __init__(
        self,
        snapshot_service: TransactionSnapshotService,
        filter_desc_blik: str,
        filter_desc_allegro: str,
    ) -> None:
        super().__init__(snapshot_service)
        self.filter_desc_blik = filter_desc_blik
        self.filter_desc_allegro = filter_desc_allegro

    async def _build_metrics(
        self, snapshot: TransactionSnapshot
    ) -> TXStatisticsMetrics:
        txs_uncategorized = filter_out_categorized(snapshot.transactions)
        txs_blik_ok = filter_by_description(
            txs_uncategorized,
            self.filter_desc_blik,
            exact_match=True,
            exclude=True,
        )
        txs_action_not_req = [
            tx for tx in txs_blik_ok if TxTag.action_req not in tx.tags
        ]
        txs_allegro_ok = [
            tx
            for tx in txs_action_not_req
            if not (
                self.filter_desc_allegro in tx.description.lower()
                and TxTag.allegro_done not in tx.tags
            )
        ]
        categorizable_by_month = await group_tx_by_month(txs_allegro_ok)

        return TXStatisticsMetrics(
            total_transactions=snapshot.metrics.total_transactions,
            single_part_transactions=len(snapshot.transactions),
            uncategorized_transactions=len(txs_uncategorized),
            blik_not_ok=len(txs_uncategorized) - len(txs_blik_ok),
            action_req=len(txs_blik_ok) - len(txs_action_not_req),
            allegro_not_ok=len(txs_action_not_req) - len(txs_allegro_ok),
            categorizable=len(txs_allegro_ok),
            categorizable_by_month=categorizable_by_month,
            time_stamp=snapshot.fetched_at,
            fetching_duration_ms=snapshot.metrics.fetching_duration_ms,
        )
