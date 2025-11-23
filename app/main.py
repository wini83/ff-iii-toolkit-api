import tomllib

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.file import router as file_router
from app.api.upload import router as upload_router
from app.utils.logger import setup_logging
from app.api.auth import router as auth_router
setup_logging()


def get_version() -> str:
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]


APP_VERSION = get_version()

app = FastAPI(title="Firefly III Alior BLIK Tool", version=APP_VERSION)

app.include_router(upload_router)
app.include_router(file_router)

#app.mount("/", StaticFiles(directory="static", html=True), name="static")


app.include_router(auth_router)


app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/file/{file_id}")
def file_view(file_id: str):
    """
    Serves the frontend file viewer page.
    The HTML uses HTMX to fetch /api/file/{id}.
    """
    try:
        with open("static/file.html", "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        return HTMLResponse("<h1>file.html not found</h1>", status_code=500)
    return HTMLResponse(html)


app.get("/health")


async def health_check():
    return {"status": "ok"}
