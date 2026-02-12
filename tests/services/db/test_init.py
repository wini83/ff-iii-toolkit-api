from unittest.mock import MagicMock

import pytest

from services.db.init import DatabaseBootstrap


def _engine_with_scalar(value):
    conn = MagicMock()
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn
    engine.connect.return_value.__exit__.return_value = None

    first = MagicMock()
    second = MagicMock()
    second.scalar.return_value = value
    conn.execute.side_effect = [first, second]
    return engine, conn


def test_db_bootstrap_success():
    engine, conn = _engine_with_scalar(1)
    bootstrap = DatabaseBootstrap(engine)

    bootstrap.run()

    assert conn.execute.call_count == 2


def test_db_bootstrap_raises_when_not_initialized():
    engine, conn = _engine_with_scalar(None)
    bootstrap = DatabaseBootstrap(engine)

    with pytest.raises(RuntimeError):
        bootstrap.run()

    assert conn.execute.call_count == 2
