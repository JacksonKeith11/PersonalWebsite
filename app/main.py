from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Personal site")
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


@app.get("/api/serials")
def serials():
    # Placeholder for the web serial update feed.
    return {"updates": []}
