import asyncio
import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import auth
from .arena import routes as arena_routes
from .books import epub
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
    threading.Thread(target=epub.refresh_all, name="books-refresh", daemon=True).start()
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


@app.get("/recipes", include_in_schema=False)
def recipes():
    return FileResponse(STATIC_DIR / "recipes.html")


@app.get("/games", include_in_schema=False)
def games():
    return FileResponse(STATIC_DIR / "games.html")


@app.get("/games/roguelike-tactics", include_in_schema=False)
def roguelike_tactics():
    return FileResponse(STATIC_DIR / "games" / "threefold" / "index.html")


@app.get("/games/song-guesser", include_in_schema=False)
def song_guesser():
    return FileResponse(STATIC_DIR / "games" / "song-guesser" / "index.html")


@app.get("/games/threefold-path", include_in_schema=False)
def threefold_path():
    # the game's old name; keep old links working
    return RedirectResponse("/games/roguelike-tactics", status_code=301)


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


app.include_router(arena_routes.router)

# Books are behind a username rather than the password; see app/books/routes.py.
app.include_router(books_routes.router)
