from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta

from services.snapshot.models import TransactionSnapshot


class SnapshotStore(ABC):
    @abstractmethod
    async def get_snapshot(self) -> TransactionSnapshot | None:
        raise NotImplementedError

    @abstractmethod
    async def set_snapshot(self, snapshot: TransactionSnapshot) -> None:
        raise NotImplementedError

    @abstractmethod
    async def invalidate(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def is_stale(self, max_age_seconds: int) -> bool:
        raise NotImplementedError


class InMemorySnapshotStore(SnapshotStore):
    def __init__(self) -> None:
        self._snapshot: TransactionSnapshot | None = None

    async def get_snapshot(self) -> TransactionSnapshot | None:
        return self._snapshot

    async def set_snapshot(self, snapshot: TransactionSnapshot) -> None:
        self._snapshot = snapshot

    async def invalidate(self) -> None:
        self._snapshot = None

    async def is_stale(self, max_age_seconds: int) -> bool:
        snapshot = self._snapshot
        if snapshot is None:
            return True

        if snapshot.fetched_at.tzinfo is None:
            raise ValueError("TransactionSnapshot.fetched_at must be timezone-aware")

        return datetime.now(UTC) - snapshot.fetched_at > timedelta(
            seconds=max_age_seconds
        )
