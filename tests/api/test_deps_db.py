from contextlib import suppress
from types import SimpleNamespace

from api.deps_db import get_db


def test_get_db_yields_session_from_request_state():
    session = SimpleNamespace(close=lambda: None)
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(session_factory=lambda: session),
        )
    )

    generator = get_db(request)

    yielded = next(generator)

    assert yielded is session


def test_get_db_closes_session_when_generator_finishes():
    closed = {"value": False}

    class DummySession:
        def close(self) -> None:
            closed["value"] = True

    session = DummySession()
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(session_factory=lambda: session),
        )
    )

    generator = get_db(request)
    next(generator)

    with suppress(StopIteration):
        next(generator)

    assert closed["value"] is True


def test_get_db_closes_session_when_generator_is_closed_after_error():
    closed = {"value": False}

    class DummySession:
        def close(self) -> None:
            closed["value"] = True

    session = DummySession()
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(session_factory=lambda: session),
        )
    )

    generator = get_db(request)
    next(generator)

    generator.close()

    assert closed["value"] is True
