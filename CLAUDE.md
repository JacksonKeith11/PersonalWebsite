# jacksonfkeith.com

Personal site served from a MacBook: FastAPI in Docker (OrbStack), exposed through a Cloudflare Tunnel.

## Deploying

Pushing to `main` deploys. A job on the Mac polls GitHub every 2 minutes, fast-forwards, runs
`docker compose up -d --build web tts`, and rolls back if `http://localhost:8080/healthz` fails.
So commit and push straight to `main`; no branches or pull requests. Check a change works before
pushing, since every push goes live.

Changes that need someone at the Mac (say so in the commit message and to the user):
- new or changed settings in `.env` (it holds every secret and is not in the repo; add new keys,
  empty, to `.env.example`)
- changes to the tunnel, OrbStack, or anything outside this repo

## Layout

- `app/main.py`: routes, login (`/login`), mounts `/static`
- `app/auth.py`: shared password gate for the serials page (`SERIALS_PASSWORD`, HMAC cookie `serials_auth`)
- `app/static/`: public pages (`/`, `/resume`, `/projects`) and assets
- `app/serials/`: unlisted serial-updates page. Gmail IMAP for Royal Road, AO3, fiction.live;
  XenForo "What's New" threadmarks for SpaceBattles, Sufficient Velocity, Questionable Questing
- `app/books/`: EPUB library and reader at `/books`. No password: readers pick a username (cookie
  `books_user`) and see only books whose `book.json` `owner` matches; others' books 404
  - `epub.py` parses uploads; `store.py` documents the on-disk layout under `data/books/`
  - `worker.py` runs in the `tts` container (`Dockerfile.tts`) and narrates with Kokoro (am_michael),
    only books someone asked for (Make audiobook, or pressing listen: a `narrate` file in the book)
  - `pages.py` renders the shells; `app/static/books/` has the reader/library JS and CSS
  - `importer.py` builds an EPUB from a Royal Road fiction or SpaceBattles/SV/QQ thread link
    (threadmarks via reader mode), one import at a time on a background thread. Royal Road and
    SpaceBattles block the server, so stories also come in through the "Import to Library"
    bookmarklet (`library.js` `grab`): the same parsers run on pages the reader's browser fetched,
    and `importer.gather` asks it (via `/books/receive`) for the ones still missing
- `data/`: runtime data (SQLite, books, audio); gitignored

## Rules

- Never commit secrets, `.env`, or anything under `data/`.
- Keep requests to Royal Road, AO3, fiction.live and the forums to a minimum: use notification
  emails for serial updates where a site sends them, fetch only what a reader asked for, and space
  requests out (the books importer waits a second between them).
- Private pages stay noindex and `no-store`; serials stay behind `auth`, books behind a username.
- Cloudflare caches static files: when changing CSS/JS, bump `?v=` on `style.css` links or
  `ASSET_VERSION` in `app/books/pages.py`.
- Test the reader against public-domain EPUBs (e.g. Project Gutenberg), not the owner's books.
