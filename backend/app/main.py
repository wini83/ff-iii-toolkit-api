import tomllib

from fastapi import APIRouter, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.settings import settings
from app.api.auth import router as auth_router
from app.api.file import router as file_router
from app.api.upload import router as upload_router
from app.routers.file import router as file_ui_router
from app.utils.logger import setup_logging
from fastapi.middleware.cors import CORSMiddleware

setup_logging()


def get_version() -> str:
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


APP_VERSION = get_version()

app = FastAPI(title="Firefly III Alior BLIK Tool", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

router = APIRouter()
templates = Jinja2Templates("templates")


app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(file_router)
app.include_router(file_ui_router)



app.mount("/static", StaticFiles(directory="static"), name="static")


app.get("/health")
async def health_check():
    return {"status": "ok"}
