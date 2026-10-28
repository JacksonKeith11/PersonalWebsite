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

- `app/main.py`: routes, serials login (`/login`), mounts `/static`; `app/auth.py`: the serials password gate
- `app/static/`: public pages (`/`, `/resume`, `/projects`, `/recipes`, `/games`) and assets
- `app/serials/`: unlisted serial-updates page (Gmail IMAP for Royal Road, AO3, fiction.live;
  XenForo "What's New" threadmarks for SpaceBattles, Sufficient Velocity, Questionable Questing)
- `app/books/` and `app/static/books/`: EPUB library, reader, story importer and Kokoro narration
  at `/books`, behind a username
- `app/static/games/threefold/`: Roguelike Tactics (formerly Threefold Path, hence the folder names), a Phaser tactics
  roguelike at `/games/roguelike-tactics`
- `tools/`: dev scripts (the game's headless autoplay test, and `threefold-art/`, the Python that draws its sprites)
- `data/`: runtime data (SQLite, books, audio); gitignored

## Area docs

Each area has a doc covering what it does, its design directives, and its gotchas. Don't read them
up front. Read the matching one before you change something in that area:

| Changing... | Read |
|---|---|
| `app/main.py`, `app/auth.py`, public pages, `style.css`, the nav bar, Dockerfiles, compose, deploy | `docs/site.md` |
| `app/serials/` | `docs/serials.md` |
| `app/books/`, `app/static/books/` | `docs/books.md` |
| `app/static/games/`, `tools/threefold-autoplay.js`, `tools/threefold-art/` | `docs/game.md` |
| Game sprites (`tools/threefold-art/`, `js/sprites.js`) | `docs/game-art.md` too |

When a change alters how an area works or turns up a new gotcha, update its doc in the same commit.

## Rules

- Never commit secrets, `.env`, or anything under `data/`.
- Keep requests to Royal Road, AO3, fiction.live and the forums to a minimum: use notification
  emails for serial updates where a site sends them, fetch only what a reader asked for, and space
  requests out (the books importer waits a second between them).
- Private pages stay noindex and `no-store`; serials stay behind `auth`, books behind a username.
- Cloudflare caches static files: when changing CSS/JS, bump its `?v=` (`style.css` links,
  `ASSET_VERSION` in `app/books/pages.py`, or the game's module URLs; see the area docs).
- Test the reader against public-domain EPUBs (e.g. Project Gutenberg), not the owner's books.
