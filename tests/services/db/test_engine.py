from unittest.mock import MagicMock

import services.db.engine as engine_module


def test_create_engine_from_sqlite_url(monkeypatch):
    sentinel = object()
    captured = {}

    def fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(engine_module, "create_engine", fake_create_engine)

    result = engine_module.create_engine_from_url("sqlite:///db.sqlite")

    assert result is sentinel
    assert captured["kwargs"]["connect_args"] == {"check_same_thread": False}
    assert captured["kwargs"]["pool_pre_ping"] is True


def test_create_engine_from_non_sqlite_url(monkeypatch):
    sentinel = object()
    captured = {}

    def fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(engine_module, "create_engine", fake_create_engine)

    result = engine_module.create_engine_from_url("postgresql://user:pass@host/db")

    assert result is sentinel
    assert captured["kwargs"]["connect_args"] == {}
    assert captured["kwargs"]["pool_pre_ping"] is True


def test_create_session_factory(monkeypatch):
    sentinel = object()
    captured = {}

    def fake_sessionmaker(**kwargs):
        captured["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(engine_module, "sessionmaker", fake_sessionmaker)
    engine = MagicMock()

    result = engine_module.create_session_factory(engine)

    assert result is sentinel
    assert captured["kwargs"]["autocommit"] is False
    assert captured["kwargs"]["autoflush"] is False
    assert captured["kwargs"]["bind"] is engine
