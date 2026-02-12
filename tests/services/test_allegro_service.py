from unittest.mock import MagicMock
from uuid import uuid4

import pytest

import services.allegro_service as allegro_service_module
from services.allegro.api import AllegroApiError, AllegroAuthError
from services.allegro_service import AllegroService, AllegroServiceError
from services.domain.allegro import AllegroAccount, AllegroOrderPayment


class DummyInfo:
    def __init__(self, login):
        self.login = login


class DummyOrders:
    def __init__(self, payments):
        self.payments = payments


def test_fetch_with_login_none_enriches_and_maps(monkeypatch):
    client = MagicMock()
    client.get_user_info.return_value = DummyInfo("user1")
    client.get_orders.return_value = DummyOrders(payments=["p1", "p2"])

    factory = MagicMock(return_value=client)
    svc = AllegroService(client_factory=factory)

    mapped1 = object()
    mapped2 = object()
    mapper = MagicMock(side_effect=[mapped1, mapped2])
    monkeypatch.setattr(AllegroOrderPayment, "from_allegro_payment", mapper)

    account = AllegroAccount(id=uuid4(), secret="s1", login=None)
    result = svc.fetch(account)

    factory.assert_called_once_with("s1")
    client.get_user_info.assert_called_once()
    assert result.payments == [mapped1, mapped2]
    mapper.assert_any_call("p1", "user1")
    mapper.assert_any_call("p2", "user1")


def test_fetch_with_login_present_skips_user_info(monkeypatch):
    client = MagicMock()
    client.get_orders.return_value = DummyOrders(payments=["p1"])

    factory = MagicMock(return_value=client)
    svc = AllegroService(client_factory=factory)

    mapped = object()
    mapper = MagicMock(return_value=mapped)
    monkeypatch.setattr(AllegroOrderPayment, "from_allegro_payment", mapper)

    account = AllegroAccount(id=uuid4(), secret="s1", login="known")
    result = svc.fetch(account)

    client.get_user_info.assert_not_called()
    mapper.assert_called_once_with("p1", "known")
    assert result.payments == [mapped]


def test_fetch_wraps_auth_error():
    client = MagicMock()
    client.get_orders.side_effect = AllegroAuthError("nope")

    factory = MagicMock(return_value=client)
    svc = AllegroService(client_factory=factory)

    account = AllegroAccount(id=uuid4(), secret="s1", login="l")

    with pytest.raises(AllegroServiceError) as exc:
        svc.fetch(account)

    assert "authentication" in str(exc.value).lower()
    assert exc.value.details == {"error": "nope"}


def test_fetch_wraps_api_error():
    client = MagicMock()
    client.get_orders.side_effect = AllegroApiError("bad")

    factory = MagicMock(return_value=client)
    svc = AllegroService(client_factory=factory)

    account = AllegroAccount(id=uuid4(), secret="s1", login="l")

    with pytest.raises(AllegroServiceError) as exc:
        svc.fetch(account)

    assert "api" in str(exc.value).lower()
    assert exc.value.details == {"error": "bad"}


def test_fetch_reraises_unknown_error():
    client = MagicMock()
    client.get_orders.side_effect = ValueError("boom")

    factory = MagicMock(return_value=client)
    svc = AllegroService(client_factory=factory)

    account = AllegroAccount(id=uuid4(), secret="s1", login="l")

    with pytest.raises(ValueError):
        svc.fetch(account)


def test_batch_fetch_combines_and_enriches(monkeypatch):
    client1 = MagicMock()
    client1.get_user_info.return_value = DummyInfo("u1")
    client1.get_orders.return_value = DummyOrders(payments=["p1"])

    client2 = MagicMock()
    client2.get_orders.return_value = DummyOrders(payments=["p2", "p3"])

    factory = MagicMock(side_effect=[client1, client2])
    svc = AllegroService(client_factory=factory)

    mapped = [object(), object(), object()]
    mapper = MagicMock(side_effect=mapped)
    monkeypatch.setattr(AllegroOrderPayment, "from_allegro_payment", mapper)

    accounts = [
        AllegroAccount(id=uuid4(), secret="s1", login=None),
        AllegroAccount(id=uuid4(), secret="s2", login="u2"),
    ]

    result = svc.batch_fetch(accounts)

    assert result.payments == mapped
    client1.get_user_info.assert_called_once()
    client2.get_user_info.assert_not_called()
    mapper.assert_any_call("p1", "u1")
    mapper.assert_any_call("p2", "u2")
    mapper.assert_any_call("p3", "u2")


def test_batch_fetch_wraps_api_error(monkeypatch):
    client1 = MagicMock()
    client1.get_orders.return_value = DummyOrders(payments=["p1"])

    client2 = MagicMock()
    client2.get_orders.side_effect = AllegroApiError("bad")

    factory = MagicMock(side_effect=[client1, client2])
    svc = AllegroService(client_factory=factory)

    accounts = [
        AllegroAccount(id=uuid4(), secret="s1", login="u1"),
        AllegroAccount(id=uuid4(), secret="s2", login="u2"),
    ]

    monkeypatch.setattr(
        AllegroOrderPayment, "from_allegro_payment", MagicMock(return_value=object())
    )

    with pytest.raises(AllegroServiceError) as exc:
        svc.batch_fetch(accounts)

    assert "api" in str(exc.value).lower()
    assert exc.value.details == {"error": "bad"}


def test_allegro_client_factory_uses_secret_and_session(monkeypatch):
    captured = {}

    class DummyClient:
        def __init__(self, cookie, session):
            captured["cookie"] = cookie
            captured["session"] = session

    session_obj = object()

    monkeypatch.setattr(allegro_service_module, "AllegroApiClient", DummyClient)
    monkeypatch.setattr(allegro_service_module, "Session", lambda: session_obj)

    client = allegro_service_module.allegro_client_factory("secret")

    assert isinstance(client, DummyClient)
    assert captured["cookie"] == "secret"
    assert captured["session"] is session_obj
