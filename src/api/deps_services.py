from functools import lru_cache

from fastapi import Depends
from ff_iii_luciferin.api import FireflyClient
from sqlalchemy.orm import Session

from api.deps_db import get_db
from services.allegro_service import AllegroService, allegro_client_factory
from services.db.repository import (
    AuditLogRepository,
    UserRepository,
    UserSecretRepository,
)
from services.firefly_base_service import FireflyBaseService
from services.firefly_enrichment_service import FireflyEnrichmentService
from services.firefly_tx_service import FireflyTxService
from services.snapshot import (
    InMemorySnapshotStore,
    SnapshotAllegroMetricsService,
    SnapshotBlikMetricsService,
    SnapshotStore,
    SnapshotTxMetricsService,
    TransactionSnapshotService,
)
from services.system.bootstrap import BootstrapService
from services.user_secrets_service import UserSecretsService
from settings import settings


@lru_cache(maxsize=1)
def get_firefly_client() -> FireflyClient:
    if not settings.FIREFLY_URL or not settings.FIREFLY_TOKEN:
        raise RuntimeError("Config error")

    return FireflyClient(
        base_url=settings.FIREFLY_URL,
        token=settings.FIREFLY_TOKEN,
    )


@lru_cache(maxsize=1)
def get_firefly_base_service() -> FireflyBaseService:
    client = get_firefly_client()
    return FireflyBaseService(client)


@lru_cache(maxsize=1)
def get_firefly_enrichment_service() -> FireflyEnrichmentService:
    client = get_firefly_client()
    return FireflyEnrichmentService(client)


@lru_cache(maxsize=1)
def get_firefly_tx_service() -> FireflyTxService:
    client = get_firefly_client()
    return FireflyTxService(
        client,
        settings.BLIK_DESCRIPTION_FILTER,
        getattr(settings, "ALLEGRO_DESCRIPTION_FILTER", "allegro"),
    )


@lru_cache(maxsize=1)
def get_snapshot_store() -> SnapshotStore:
    return InMemorySnapshotStore()


@lru_cache(maxsize=1)
def get_transaction_snapshot_service() -> TransactionSnapshotService:
    return TransactionSnapshotService(
        store=get_snapshot_store(),
        firefly_service=get_firefly_base_service(),
        max_age_seconds=settings.TRANSACTION_SNAPSHOT_TTL_SECONDS,
    )


@lru_cache(maxsize=1)
def get_snapshot_blik_metrics_service() -> SnapshotBlikMetricsService:
    return SnapshotBlikMetricsService(
        snapshot_service=get_transaction_snapshot_service(),
        filter_desc_blik=settings.BLIK_DESCRIPTION_FILTER,
    )


@lru_cache(maxsize=1)
def get_snapshot_allegro_metrics_service() -> SnapshotAllegroMetricsService:
    return SnapshotAllegroMetricsService(
        snapshot_service=get_transaction_snapshot_service(),
        filter_desc_allegro=getattr(settings, "ALLEGRO_DESCRIPTION_FILTER", "allegro"),
    )


@lru_cache(maxsize=1)
def get_snapshot_tx_metrics_service() -> SnapshotTxMetricsService:
    return SnapshotTxMetricsService(
        snapshot_service=get_transaction_snapshot_service(),
        filter_desc_blik=settings.BLIK_DESCRIPTION_FILTER,
        filter_desc_allegro=getattr(settings, "ALLEGRO_DESCRIPTION_FILTER", "allegro"),
    )


def get_user_secrets_service(
    db: Session = Depends(get_db),
) -> UserSecretsService:
    return UserSecretsService(
        secret_repo=UserSecretRepository(db),
        audit_repo=AuditLogRepository(db),
    )


def get_bootstrap_service(
    db: Session = Depends(get_db),
) -> BootstrapService:
    return BootstrapService(
        user_repo=UserRepository(db),
    )


def get_allegro_service() -> AllegroService:
    return AllegroService(client_factory=allegro_client_factory)
