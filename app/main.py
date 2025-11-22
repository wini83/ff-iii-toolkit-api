from fastapi import FastAPI

from app.api.file import router as file_router
from app.api.upload import router as upload_router
from app.utils.logger import setup_logging
from fastapi.staticfiles import StaticFiles
import tomllib

setup_logging()

def get_version() -> str:
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]

APP_VERSION = get_version()

app = FastAPI(title="Firefly III Alior BLIK Tool", version=APP_VERSION)

app.include_router(upload_router)
app.include_router(file_router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")

app.get("/health")
async def health_check():
    return {"status": "ok"}