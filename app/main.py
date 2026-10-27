import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import auth
from .books import routes as books_routes
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


@app.post("/login", include_in_schema=False)
async def login(request: Request):
    form = parse_qs((await request.body()).decode())
    password = form.get("password", [""])[0]
    next_path = form.get("next", ["/"])[0]
    if not next_path.startswith("/") or next_path.startswith("//"):
        next_path = "/"
    if not auth.password_ok(password):
        await asyncio.sleep(1)  # slow down guessing
        return HTMLResponse(
            serials_page.render_login(failed=True, next_path=next_path), status_code=401, headers=auth.PRIVATE_HEADERS
        )
    response = RedirectResponse(next_path, status_code=303)
    response.set_cookie(
        auth.COOKIE, auth.token(), max_age=auth.MAX_AGE, path="/", secure=True, httponly=True, samesite="lax"
    )
    return response


if SERIALS_PATH:

    @app.get(f"/{SERIALS_PATH}", include_in_schema=False)
    def serials(request: Request, page: int = 1):
        if not auth.authorized(request):
            return HTMLResponse(
                serials_page.render_login(next_path=f"/{SERIALS_PATH}"), status_code=401, headers=auth.PRIVATE_HEADERS
            )
        return HTMLResponse(serials_page.render(page), headers=auth.PRIVATE_HEADERS)


# Books hold copyrighted text, so they're only served behind the password.
if auth.PASSWORD:
    app.include_router(books_routes.router)
