from datetime import UTC, datetime
from uuid import uuid4

from services import vault_session_store as vault_session_store_module
from services.vault_session_store import VaultSessionStore


def test_create_get_and_invalidate_session():
    store = VaultSessionStore()
    user_id = uuid4()
    other_user_id = uuid4()

    session_id = store.create(user_id, b"user-key", ttl_seconds=60)

    assert store.get_user_key(user_id, session_id) == b"user-key"
    assert store.get_user_key(other_user_id, session_id) is None

    store.invalidate(user_id, session_id)

    assert store.get_user_key(user_id, session_id) is None


def test_invalidate_all_for_user_removes_only_that_users_sessions():
    store = VaultSessionStore()
    user_id = uuid4()
    other_user_id = uuid4()
    user_session = store.create(user_id, b"user-key", ttl_seconds=60)
    other_session = store.create(other_user_id, b"other-key", ttl_seconds=60)

    store.invalidate_all_for_user(user_id)

    assert store.get_user_key(user_id, user_session) is None
    assert store.get_user_key(other_user_id, other_session) == b"other-key"


def test_get_user_key_expires_session_on_read(monkeypatch):
    base_now = datetime(2026, 1, 1, tzinfo=UTC)

    class FakeDateTime:
        current = base_now

        @classmethod
        def now(cls, tz):
            assert tz is UTC
            return cls.current

    monkeypatch.setattr(vault_session_store_module, "datetime", FakeDateTime)

    store = VaultSessionStore()
    user_id = uuid4()
    session_id = store.create(user_id, b"user-key", ttl_seconds=10)

    assert store.get_user_key(user_id, session_id) == b"user-key"

    FakeDateTime.current = datetime(2026, 1, 1, 0, 0, 11, tzinfo=UTC)

    assert store.get_user_key(user_id, session_id) is None
    assert user_id not in store._sessions
