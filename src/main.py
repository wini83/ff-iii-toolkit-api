import logging
import tomllib
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routers.allegro import router as allegro_router
from api.routers.auth import router as auth_router
from api.routers.blik_files import router as blik_router
from api.routers.me import router as me_router
from api.routers.system import router as system_router
from api.routers.tx import router as tx_router
from api.routers.user_secrets import router as user_secrets_router
from api.routers.users import router as users_router
from middleware import register_middlewares
from services.db.engine import (
    create_engine_from_url,
    create_session_factory,
)
from services.db.init import DatabaseBootstrap
from settings import settings
from utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


def get_version() -> str:
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


# ==================================================
# Application factory – ZERO side effects
# ==================================================


def create_app(*, bootstrap: DatabaseBootstrap | None = None) -> FastAPI:
    app = FastAPI(title="Firefly III Toolkit")
    app.state.version = get_version()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if bootstrap:
            bootstrap.run()
        yield

    app.router.lifespan_context = lifespan

    register_middlewares(app, settings)

    app.include_router(auth_router)
    app.include_router(me_router)
    app.include_router(blik_router)
    app.include_router(tx_router)
    app.include_router(allegro_router)
    app.include_router(users_router)
    app.include_router(user_secrets_router)
    app.include_router(system_router)

    return app


# ==================================================
# Production composition root – ONLY HERE engine/db
# ==================================================


def create_production_app() -> FastAPI:
    engine = create_engine_from_url(settings.database_url)
    session_factory = create_session_factory(engine)

    app = create_app(bootstrap=DatabaseBootstrap(engine))
    app.state.session_factory = session_factory

    return app
