import asyncio
import hashlib
import hmac
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .serials import page as serials_page
from .serials import scheduler

STATIC_DIR = Path(__file__).parent / "static"
# Unlisted path for the serial updates page; it is only served when this is set.
SERIALS_PATH = os.environ.get("SERIALS_PATH", "").strip("/")
# Optional password for that page. It's a light gate against casual visitors, not real security.
SERIALS_PASSWORD = os.environ.get("SERIALS_PASSWORD", "")
AUTH_COOKIE = "serials_auth"
AUTH_MAX_AGE = 400 * 24 * 60 * 60  # browsers cap cookie lifetimes at about 400 days

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


PRIVATE_HEADERS = {"X-Robots-Tag": "noindex, nofollow", "Cache-Control": "no-store"}


def _auth_token() -> str:
    # Derived from the password, so changing SERIALS_PASSWORD signs out every browser.
    return hmac.new(SERIALS_PASSWORD.encode(), b"serials-auth", hashlib.sha256).hexdigest()


def _authorized(request: Request) -> bool:
    return not SERIALS_PASSWORD or hmac.compare_digest(request.cookies.get(AUTH_COOKIE, ""), _auth_token())


if SERIALS_PATH:

    @app.get(f"/{SERIALS_PATH}", include_in_schema=False)
    def serials(request: Request, page: int = 1):
        if not _authorized(request):
            return HTMLResponse(serials_page.render_login(), status_code=401, headers=PRIVATE_HEADERS)
        return HTMLResponse(serials_page.render(page), headers=PRIVATE_HEADERS)

    @app.post(f"/{SERIALS_PATH}", include_in_schema=False)
    async def serials_login(request: Request):
        password = parse_qs((await request.body()).decode()).get("password", [""])[0]
        if not SERIALS_PASSWORD or not hmac.compare_digest(password.encode(), SERIALS_PASSWORD.encode()):
            await asyncio.sleep(1)  # slow down guessing
            return HTMLResponse(serials_page.render_login(failed=True), status_code=401, headers=PRIVATE_HEADERS)
        response = RedirectResponse(f"/{SERIALS_PATH}", status_code=303)
        response.set_cookie(
            AUTH_COOKIE,
            _auth_token(),
            max_age=AUTH_MAX_AGE,
            path=f"/{SERIALS_PATH}",
            secure=True,
            httponly=True,
            samesite="lax",
        )
        return response
