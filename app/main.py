import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .serials import page as serials_page
from .serials import scheduler

STATIC_DIR = Path(__file__).parent / "static"
# Unlisted path for the serial updates page; it is only served when this is set.
SERIALS_PATH = os.environ.get("SERIALS_PATH", "").strip("/")

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if SERIALS_PATH:
        scheduler.start()
    yield


app = FastAPI(title="Personal site", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/resume", include_in_schema=False)
def resume():
    return FileResponse(STATIC_DIR / "resume.html")


@app.get("/projects", include_in_schema=False)
def projects():
    return FileResponse(STATIC_DIR / "projects.html")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


if SERIALS_PATH:

    @app.get(f"/{SERIALS_PATH}", include_in_schema=False)
    def serials():
        return HTMLResponse(serials_page.render(), headers={"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"})
