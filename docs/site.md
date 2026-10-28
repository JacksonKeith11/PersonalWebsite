# Site core, public pages and deploy

Read this before changing `app/main.py`, `app/auth.py`, the public pages in `app/static/`
(`index.html`, `resume.html`, `projects.html`, `recipes.html`, `games.html`, `style.css`), the
Dockerfiles, `docker-compose.yml`, or anything about how the site is served.

## What's here

- `app/main.py` is the FastAPI app. Each public page is a plain `FileResponse` of a static HTML
  file. `/static` is mounted from `app/static/`. `/healthz` returns `{"status": "ok"}`.
- The lifespan hook starts two background threads: the serials scheduler (only when `SERIALS_PATH`
  is set) and `books.epub.refresh_all`, which rebuilds books stored in an older format.
- `app/auth.py` is the shared-password gate for the serials page: `SERIALS_PASSWORD`, an HMAC cookie
  `serials_auth`, and `PRIVATE_HEADERS` (`noindex`, `no-store`) for every private response.
  `POST /login` belongs to the serials page. The books library has its own `/books/login`
  (a username, no password; see `docs/books.md`).
- `data/` holds runtime state (`serials.db`, `books/`). It's mounted into both containers and is
  gitignored.

## Deploy

- Pushing to `main` deploys it. A job on the Mac polls GitHub every 2 minutes, fast-forwards, runs
  `docker compose up -d --build web tts`, and rolls back if `http://localhost:8080/healthz` fails.
  Anything that breaks app startup (an import error, a bad route) gets rolled back. Anything that
  starts but is broken goes live.
- Services in `docker-compose.yml`:
  - `web`: uvicorn on port 8000, published as 8080.
  - `tts`: the Kokoro narrator, built from `Dockerfile.tts`. It only gets `app/__init__.py` and
    `app/books`, so the worker may import only from there and the stdlib, numpy, lameenc and
    kokoro_onnx.
  - `tunnel`: cloudflared, under the `tunnel` profile. The deploy job doesn't rebuild it.
- Secrets live only in `.env` on the Mac. A new setting means: add it, empty, to `.env.example`, and
  tell the user it needs setting at the Mac.

## Design directives

- Public pages share a look: `style.css` gives the paper card on a tan background, with Source
  Serif 4 and Source Sans 3. New public pages copy an existing one (`recipes.html` is the
  simplest) and add a route in `main.py`.
- Private pages stay `noindex` and `no-store` (`auth.PRIVATE_HEADERS`). Serials stay behind the
  password; books stay behind a username.
- Keep the site light: no build step, no JS frameworks on the public pages.

## Gotchas

- **The nav bar exists in six places:** `index.html`, `resume.html`, `projects.html`,
  `recipes.html`, `games.html`, and the `NAV` string in `app/books/pages.py`. Each copy marks its
  own page with `aria-current="page"`. Add or rename links in all of them.
- **Cloudflare caches `/static`.** After changing `style.css`, bump `?v=` on every link to it: the
  five public pages, Song Guesser's `index.html`, and `STYLE` in `app/books/pages.py`. The books service worker caches `STYLE`
  too, so changing that also needs a bump of `ASSET_VERSION` there.
- **The serials route is registered at import time.** It's only registered if `SERIALS_PATH` was
  set when the app started. Changing `.env` needs a restart.
- uvicorn runs with `--proxy-headers` because requests arrive through the tunnel. Cookies are set
  `secure=True`, so logging in over plain `http://localhost:8080` won't stick in a browser.
- `README.md` is the human-facing overview; keep its table of paths current when adding a page.
