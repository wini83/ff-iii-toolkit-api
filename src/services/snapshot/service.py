import asyncio
import logging
from datetime import UTC, datetime

from services.firefly_base_service import FireflyBaseService
from services.snapshot.models import TransactionSnapshot
from services.snapshot.store import SnapshotStore

logger = logging.getLogger(__name__)
SNAPSHOT_FETCH_TIMEOUT_SECONDS = 180


class TransactionSnapshotService:
    def __init__(
        self,
        store: SnapshotStore,
        firefly_service: FireflyBaseService,
        max_age_seconds: int = 300,
    ) -> None:
        self.store = store
        self.firefly_service = firefly_service
        self.max_age_seconds = max_age_seconds
        self._refresh_lock = asyncio.Lock()
        self._refresh_task: asyncio.Task[TransactionSnapshot] | None = None

    async def get_snapshot(self) -> TransactionSnapshot:
        snapshot = await self.store.get_snapshot()
        if snapshot is not None and not await self.store.is_stale(self.max_age_seconds):
            return snapshot
        return await self._ensure_snapshot(force_refresh=False)

    async def refresh_snapshot(self) -> TransactionSnapshot:
        return await self._ensure_snapshot(force_refresh=True)

    async def get_cached_snapshot(self) -> TransactionSnapshot | None:
        return await self.store.get_snapshot()

    async def get_cached_snapshot_timestamp(self) -> datetime | None:
        snapshot = await self.store.get_snapshot()
        if snapshot is None:
            return None
        if await self.store.is_stale(self.max_age_seconds):
            return None
        return snapshot.fetched_at

    async def _ensure_snapshot(self, *, force_refresh: bool) -> TransactionSnapshot:
        async with self._refresh_lock:
            if not force_refresh:
                snapshot = await self.store.get_snapshot()
                if snapshot is not None and not await self.store.is_stale(
                    self.max_age_seconds
                ):
                    return snapshot

            task = self._refresh_task
            if task is None or task.done():
                task = asyncio.create_task(
                    self._fetch_and_store_snapshot(),
                    name="transaction-snapshot-refresh",
                )
                task.add_done_callback(self._log_refresh_task_failure)
                self._refresh_task = task

        try:
            return await task
        finally:
            if task.done() and self._refresh_task is task:
                self._refresh_task = None

    async def _fetch_and_store_snapshot(self) -> TransactionSnapshot:
        transactions, metrics = await asyncio.wait_for(
            self.firefly_service.fetch_transactions_with_metrics(),
            timeout=SNAPSHOT_FETCH_TIMEOUT_SECONDS,
        )
        snapshot = TransactionSnapshot(
            transactions=transactions,
            metrics=metrics,
            fetched_at=datetime.now(UTC),
        )
        await self.store.set_snapshot(snapshot)
        return snapshot

    def _log_refresh_task_failure(
        self, task: asyncio.Task[TransactionSnapshot]
    ) -> None:
        try:
            task.result()
        except asyncio.CancelledError:
            logger.warning("Transaction snapshot refresh task was cancelled")
        except Exception:
            logger.exception("Transaction snapshot refresh task failed")
