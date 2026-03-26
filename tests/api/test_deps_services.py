from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import api.deps_services as deps_services
from services.allegro_service import AllegroService, allegro_client_factory
from services.firefly_base_service import FireflyBaseService
from services.firefly_enrichment_service import FireflyEnrichmentService
from services.firefly_tx_service import FireflyTxService
from services.snapshot import (
    InMemorySnapshotStore,
    SnapshotAllegroMetricsService,
    SnapshotBlikMetricsService,
    SnapshotTxMetricsService,
    TransactionSnapshotService,
)
from services.system.bootstrap import BootstrapService
from services.user_secrets_service import UserSecretsService


@pytest.fixture(autouse=True)
def clear_dependency_caches():
    for factory in [
        deps_services.get_firefly_client,
        deps_services.get_firefly_base_service,
        deps_services.get_firefly_enrichment_service,
        deps_services.get_firefly_tx_service,
        deps_services.get_snapshot_store,
        deps_services.get_transaction_snapshot_service,
        deps_services.get_snapshot_blik_metrics_service,
        deps_services.get_snapshot_allegro_metrics_service,
        deps_services.get_snapshot_tx_metrics_service,
    ]:
        cache_clear = getattr(factory, "cache_clear", None)
        if cache_clear is not None:
            cache_clear()


def test_get_firefly_client_returns_cached_client(monkeypatch):
    created = []

    class DummyClient:
        def __init__(self, *, base_url: str, token: str) -> None:
            created.append((base_url, token))

    monkeypatch.setattr(
        deps_services,
        "settings",
        SimpleNamespace(
            FIREFLY_URL="https://firefly.test",
            FIREFLY_TOKEN="secret-token",
        ),
    )
    monkeypatch.setattr(deps_services, "FireflyClient", DummyClient)

    first = deps_services.get_firefly_client()
    second = deps_services.get_firefly_client()

    assert isinstance(first, DummyClient)
    assert second is first
    assert created == [("https://firefly.test", "secret-token")]


def test_get_firefly_client_raises_when_config_missing(monkeypatch):
    monkeypatch.setattr(
        deps_services,
        "settings",
        SimpleNamespace(
            FIREFLY_URL="",
            FIREFLY_TOKEN="",
        ),
    )

    with pytest.raises(RuntimeError, match="Config error"):
        deps_services.get_firefly_client()


def test_get_firefly_base_service_uses_firefly_client(monkeypatch):
    client = object()

    monkeypatch.setattr(deps_services, "get_firefly_client", lambda: client)

    service = deps_services.get_firefly_base_service()

    assert isinstance(service, FireflyBaseService)
    assert service.firefly_client is client


def test_get_firefly_enrichment_service_uses_firefly_client(monkeypatch):
    client = object()

    monkeypatch.setattr(deps_services, "get_firefly_client", lambda: client)

    service = deps_services.get_firefly_enrichment_service()

    assert isinstance(service, FireflyEnrichmentService)
    assert service.firefly_client is client


def test_get_firefly_tx_service_uses_filters_from_settings(monkeypatch):
    client = object()

    monkeypatch.setattr(deps_services, "get_firefly_client", lambda: client)
    monkeypatch.setattr(
        deps_services,
        "settings",
        SimpleNamespace(
            BLIK_DESCRIPTION_FILTER="blik-x",
            ALLEGRO_DESCRIPTION_FILTER="allegro-x",
        ),
    )

    service = deps_services.get_firefly_tx_service()

    assert isinstance(service, FireflyTxService)
    assert service.firefly_client is client
    assert service.filter_desc_blik == "blik-x"
    assert service.filter_desc_allegro == "allegro-x"


def test_get_snapshot_store_returns_cached_in_memory_store():
    first = deps_services.get_snapshot_store()
    second = deps_services.get_snapshot_store()

    assert isinstance(first, InMemorySnapshotStore)
    assert second is first


def test_get_transaction_snapshot_service_uses_store_and_firefly_service(monkeypatch):
    store = MagicMock()
    firefly_service = MagicMock()

    monkeypatch.setattr(deps_services, "get_snapshot_store", lambda: store)
    monkeypatch.setattr(
        deps_services, "get_firefly_base_service", lambda: firefly_service
    )
    monkeypatch.setattr(
        deps_services,
        "settings",
        SimpleNamespace(TRANSACTION_SNAPSHOT_TTL_SECONDS=86400),
    )

    service = deps_services.get_transaction_snapshot_service()

    assert isinstance(service, TransactionSnapshotService)
    assert service.store is store
    assert service.firefly_service is firefly_service
    assert service.max_age_seconds == 86400


def test_get_snapshot_blik_metrics_service_uses_snapshot_service(monkeypatch):
    snapshot_service = MagicMock()

    monkeypatch.setattr(
        deps_services, "get_transaction_snapshot_service", lambda: snapshot_service
    )
    monkeypatch.setattr(
        deps_services,
        "settings",
        SimpleNamespace(BLIK_DESCRIPTION_FILTER="blik-only"),
    )

    service = deps_services.get_snapshot_blik_metrics_service()

    assert isinstance(service, SnapshotBlikMetricsService)
    assert service.snapshot_service is snapshot_service
    assert service.filter_desc_blik == "blik-only"


def test_get_snapshot_allegro_metrics_service_uses_snapshot_service(monkeypatch):
    snapshot_service = MagicMock()

    monkeypatch.setattr(
        deps_services, "get_transaction_snapshot_service", lambda: snapshot_service
    )
    monkeypatch.setattr(
        deps_services,
        "settings",
        SimpleNamespace(ALLEGRO_DESCRIPTION_FILTER="allegro-only"),
    )

    service = deps_services.get_snapshot_allegro_metrics_service()

    assert isinstance(service, SnapshotAllegroMetricsService)
    assert service.snapshot_service is snapshot_service
    assert service.filter_desc_allegro == "allegro-only"


def test_get_snapshot_tx_metrics_service_uses_both_filters(monkeypatch):
    snapshot_service = MagicMock()

    monkeypatch.setattr(
        deps_services, "get_transaction_snapshot_service", lambda: snapshot_service
    )
    monkeypatch.setattr(
        deps_services,
        "settings",
        SimpleNamespace(
            BLIK_DESCRIPTION_FILTER="blik-only",
            ALLEGRO_DESCRIPTION_FILTER="allegro-only",
        ),
    )

    service = deps_services.get_snapshot_tx_metrics_service()

    assert isinstance(service, SnapshotTxMetricsService)
    assert service.snapshot_service is snapshot_service
    assert service.filter_desc_blik == "blik-only"
    assert service.filter_desc_allegro == "allegro-only"


def test_get_user_secrets_service_builds_repositories_from_db():
    db = MagicMock()

    service = deps_services.get_user_secrets_service(db=db)

    assert isinstance(service, UserSecretsService)
    assert service.secret_repo.db is db
    assert service.audit_repo.db is db


def test_get_bootstrap_service_builds_user_repository_from_db():
    db = MagicMock()

    service = deps_services.get_bootstrap_service(db=db)

    assert isinstance(service, BootstrapService)
    assert service.user_repo.db is db


def test_get_allegro_service_uses_default_client_factory():
    service = deps_services.get_allegro_service()

    assert isinstance(service, AllegroService)
    assert service._client_factory is allegro_client_factory
