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
- `app/arena/` and `app/static/games/arena/`: Frag Arena, a multiplayer Quake-style shooter (three.js client,
  FastAPI WebSocket server with bots) at `/games/frag-arena`
- `app/brawl/` and `app/static/games/brawl/`: Board Brawl, a Mario Party-style board game for 2-4 friends (rooms by
  code, a FastAPI WebSocket server with bots, thirty-nine minigames, two of them 3D) at `/games/board-brawl`
- `app/static/games/song-guesser/`: Song Guesser, a name-that-tune game with synthesized arrangements at
  `/games/song-guesser`
- `app/saltbound/` and `app/static/games/saltbound/`: Saltbound, a 1-3 player co-op strategy RPG (hex overworld,
  dice combat, a rising sea as the clock; FastAPI WebSocket server, Phaser map) at `/games/saltbound`
- `app/rooms.py` and `app/static/games/shared/net.js`: what the three multiplayer games share (the WebSocket loop,
  sending, room codes; the browser's identity and reconnecting socket)
- `tools/`: dev scripts (the tactics game's headless autoplay test, `threefold-art/`, the Python that draws its
  sprites, `song-guesser-check.js`, which checks Song Guesser's arrangements, and `song-guesser-midi/`, which
  turns MIDI transcriptions into Song Guesser choruses, `arena-*`, Frag Arena's checks, `brawl-*`, Board Brawl's, and `saltbound-*` plus `saltbound-art/`, Saltbound's; `check-all.sh`, every fast check, and
  `bump-version.py`, the cache versions)
- `data/`: runtime data (SQLite, books, audio); gitignored

## Area docs

Each area has a doc covering what it does, its design directives, and its gotchas. Don't read them
up front. Read the matching one before you change something in that area:

| Changing... | Read |
|---|---|
| `app/main.py`, `app/auth.py`, `app/rooms.py`, `games/shared/`, public pages, `style.css`, the nav bar, Dockerfiles, compose, deploy, `tools/check-all.sh`, `tools/bump-version.py` | `docs/site.md` |
| `app/serials/` | `docs/serials.md` |
| `app/books/`, `app/static/books/` | `docs/books.md` |
| `app/static/games/threefold/`, `tools/threefold-autoplay.js`, `tools/threefold-art/` | `docs/game.md` |
| `app/static/games/song-guesser/`, `tools/song-guesser-check.js`, `tools/song-guesser-midi/` | `docs/song-guesser.md` |
| `app/arena/`, `app/static/games/arena/`, `tools/arena-*` | `docs/arena.md` |
| `app/brawl/`, `app/static/games/brawl/`, `tools/brawl-*` | `docs/brawl.md` |
| `app/saltbound/`, `app/static/games/saltbound/`, `tools/saltbound-*`, `tools/saltbound-art/` | `docs/saltbound.md` |
| Game sprites (`tools/threefold-art/`, `js/sprites.js`) | `docs/game-art.md` too |

When a change alters how an area works or turns up a new gotcha, update its doc in the same commit.

## Rules

- When you finish a task, send the owner a push notification (the automatic one doesn't reach them):
  one line saying what's done or what needs their answer.
- Never commit secrets, `.env`, or anything under `data/`.
- Keep requests to Royal Road, AO3, fiction.live and the forums to a minimum: use notification
  emails for serial updates where a site sends them, fetch only what a reader asked for, and space
  requests out (the books importer waits a second between them).
- Private pages stay noindex and `no-store`; serials stay behind `auth`, books behind a username.
- Cloudflare caches static files: when changing CSS/JS, bump its `?v=` with
  `python3 tools/bump-version.py <folder or file>` (a game's folder, `app/static/books`, or
  `app/static/style.css`); it updates every link together.
- Run `tools/check-all.sh` before pushing: the fast checks for every area, in about a minute.
- Don't run long scripts (the Saltbound simulator, browser audits) when existing numbers answer the
  question. For a question, answer first from what's known (the area doc's latest numbers, earlier
  output, `python3 tools/saltbound-sim.py --last`), say how old it is, and offer a fresh run. When a
  run is needed, use the smallest that settles it (about two minutes), say how long before starting,
  run it in the background, and never queue several big batches at once.
- When building many changes in one batch, run the big balance test once, at the end. While
  iterating, use small spot tests only (`tools/check-all.sh`, `python3 tools/saltbound-sim.py 40
  normal --fast`, about 15 s, whose tally shows what happened, or a scratch script on two or three
  seeds). Full-bot batches are only for changes that directly affect game balance. If the end result needs a tuning pass, change
  everything you mean to change first, then test once; don't run a big batch per adjustment.
- Test the reader against public-domain EPUBs (e.g. Project Gutenberg), not the owner's books.
