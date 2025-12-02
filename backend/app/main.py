import tomllib

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.api.auth import router as auth_router
from app.api.file import router as file_router
from app.api.upload import router as upload_router
from app.settings import settings
from app.utils.logger import setup_logging

setup_logging()

class HealthCheck(BaseModel):
    status: str = "OK"

def get_version() -> str:
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]



APP_VERSION = get_version()

print(f"Settings loaded DEMO_MODE={settings.DEMO_MODE}")

app = FastAPI(title="Firefly III Toolkit", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()
templates = Jinja2Templates("templates")


app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(file_router)

@app.get("/api/health", response_model=HealthCheck, tags=["health"])
async def health_check() -> HealthCheck:
    return HealthCheck()
