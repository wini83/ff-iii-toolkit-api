from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from threading import RLock
from uuid import UUID


@dataclass(slots=True)
class _VaultSession:
    user_key: bytes
    expires_at: datetime


class VaultSessionStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: dict[UUID, dict[str, _VaultSession]] = {}

    def create(self, user_id: UUID, user_key: bytes, ttl_seconds: int) -> str:
        session_id = token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        with self._lock:
            sessions = self._sessions.setdefault(user_id, {})
            sessions[session_id] = _VaultSession(
                user_key=user_key,
                expires_at=expires_at,
            )
        return session_id

    def get_user_key(self, user_id: UUID, session_id: str) -> bytes | None:
        with self._lock:
            session = self._get_active_session(user_id=user_id, session_id=session_id)
            if session is None:
                return None
            return session.user_key

    def invalidate(self, user_id: UUID, session_id: str) -> None:
        with self._lock:
            sessions = self._sessions.get(user_id)
            if sessions is None:
                return
            sessions.pop(session_id, None)
            if not sessions:
                self._sessions.pop(user_id, None)

    def invalidate_all_for_user(self, user_id: UUID) -> None:
        with self._lock:
            self._sessions.pop(user_id, None)

    def _get_active_session(
        self, user_id: UUID, session_id: str
    ) -> _VaultSession | None:
        sessions = self._sessions.get(user_id)
        if sessions is None:
            return None

        session = sessions.get(session_id)
        if session is None:
            return None

        if session.expires_at <= datetime.now(UTC):
            sessions.pop(session_id, None)
            if not sessions:
                self._sessions.pop(user_id, None)
            return None

        return session
