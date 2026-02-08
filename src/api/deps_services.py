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
from services.firefly_allegro_service import FireflyAllegroService
from services.firefly_blik_service import FireflyBlikService
from services.firefly_tx_service import FireflyTxService
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
def get_firefly_blik_service() -> FireflyBlikService:
    client = get_firefly_client()
    return FireflyBlikService(
        client,
        settings.BLIK_DESCRIPTION_FILTER,
    )


@lru_cache(maxsize=1)
def get_firefly_tx_service() -> FireflyTxService:
    client = get_firefly_client()
    return FireflyTxService(
        client,
        settings.BLIK_DESCRIPTION_FILTER,
        getattr(settings, "ALLEGRO_DESCRIPTION_FILTER", "allegro"),
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


def get_firefly_allegro_service() -> FireflyAllegroService:
    client = get_firefly_client()
    return FireflyAllegroService(
        client,
        getattr(settings, "ALLEGRO_DESCRIPTION_FILTER", "allegro"),
    )


def get_allegro_service() -> AllegroService:
    return AllegroService(client_factory=allegro_client_factory)
