import logging
import tomllib
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routers.auth import router as auth_router
from api.routers.blik_files import router as blik_router
from api.routers.system import init_system_router
from api.routers.system import router as system_router
from api.routers.tx import router as tx_router
from api.routers.users import router as users_router
from middleware import register_middlewares
from services.db.init import init_db
from settings import settings
from utils.logger import setup_logging

setup_logging()

logger = logging.getLogger(__name__)


def get_version() -> str:
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
        init_system_router(data["project"]["version"])
    return data["project"]["version"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP
    init_db()
    yield
    # SHUTDOWN
    # (tu kiedyś: engine.dispose(), close pools, etc.)


APP_VERSION = get_version()


logger.info("Settings loaded ")
logger.info(f"Acces token expire: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")


app = FastAPI(title="Firefly III Toolkit", version=APP_VERSION, lifespan=lifespan)


register_middlewares(app, settings)

logger.info(f"Allowed_origins={settings.allowed_origins}")


app.include_router(auth_router)
app.include_router(blik_router)
app.include_router(system_router)
app.include_router(tx_router)
app.include_router(users_router)
