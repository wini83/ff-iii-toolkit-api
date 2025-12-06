import tomllib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.api.routers.auth import router as auth_router
from src.api.routers.blik_files import router as blik_router
from src.api.routers.system import router as system_router
from src.settings import settings
from src.utils.logger import setup_logging

setup_logging()


def get_version() -> str:
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


APP_VERSION = get_version()

print(f"Settings loaded, DEMO_MODE={settings.DEMO_MODE}")

app = FastAPI(title="Firefly III Toolkit", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)
#app.include_router(upload_router)
#app.include_router(file_router)

app.include_router(blik_router)
app.include_router(system_router)

