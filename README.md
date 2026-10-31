# jacksonfkeith.com

A personal site served from a MacBook: Python/FastAPI in Docker (OrbStack), exposed through a
Cloudflare Tunnel.

## What's on it

| Path | What | Access |
|---|---|---|
| `/`, `/resume`, `/projects`, `/recipes` | Static pages (`app/static/`) | Public |
| `/games` | Games list; `/games/roguelike-tactics` is Roguelike Tactics, a Phaser tactics roguelike (the old `/games/threefold-path` redirects); `/games/song-guesser` is Song Guesser, a name-that-tune game played on synthesized arrangements; `/games/frag-arena` is Frag Arena, a multiplayer Quake-style shooter (WebSocket at `/games/frag-arena/ws`); `/games/board-brawl` is Board Brawl, a Mario Party-style board game for 2-4 friends with rooms by code (WebSocket at `/games/board-brawl/ws`); `/games/saltbound` is Saltbound, a co-op strategy RPG for 1-3 players (WebSocket at `/games/saltbound/ws`) | Public |
| `/<SERIALS_PATH>` | New chapters of followed web serials, from notification emails (Royal Road, AO3, fiction.live) and forum threadmarks (SpaceBattles, Sufficient Velocity, Questionable Questing) | Unlisted, password |
| `/books` | EPUB library and reader with a story importer and Kokoro audiobook narration | Per-username |
| `/healthz` | Health check for the deploy job | Public |

## Layout

- `app/main.py`: routes; `app/auth.py`: the serials password gate
- `app/arena/`: Frag Arena's server: the map, physics, match and bots
- `app/brawl/`: Board Brawl's server: the board, rooms and turns, minigames and bots
- `app/saltbound/`: Saltbound's server: the run's rules, combat, rooms, saves (`data/saltbound.db`) and testing bots
- `app/static/`: public pages, styles and assets, including the games (`games/threefold/`, `games/song-guesser/`, `games/arena/`, `games/brawl/`, `games/saltbound/`)
- `app/serials/`: the serial updates page and its sync sources
- `app/books/`, `app/static/books/`: the library, reader, importer and narration worker
- `tools/`: dev scripts (Roguelike Tactics' headless autoplay test, Song Guesser's arrangement check,
  Frag Arena's bot match, physics parity and browser smoke tests)
- `docs/`: one doc per area covering how it works, its design rules and its gotchas
- `data/`: runtime data (SQLite, books, audio); gitignored

## Run locally

```sh
cp .env.example .env        # fill in what you need; everything is optional
docker compose up -d --build web tts
open http://localhost:8080
```

`web` is the site, and `tts` narrates books in the background. Login cookies are secure-only, so
the serials and books logins only stick over HTTPS (the tunnel), not plain `http://localhost`.

To try the game without Docker, serve `app/` with `python3 -m http.server` and open
`/static/games/threefold/index.html`. `node tools/threefold-autoplay.js` plays it headlessly
(see `docs/game.md`). Song Guesser works the same way at `/static/games/song-guesser/index.html`;
`node tools/song-guesser-check.js` checks its arrangements (see `docs/song-guesser.md`).
Frag Arena needs the server, so run the site (Docker, or `uvicorn app.main:app`) and open
`/games/frag-arena`; open it in two windows to play yourself. `python3 tools/arena-check.py` plays
a bots-only match headlessly (see `docs/arena.md`).
Board Brawl also needs the server: open `/games/board-brawl`, make a room, and join it from a second
window (or add bots). `python3 tools/brawl-check.py` plays bots-only games headlessly and
`node tools/brawl-smoke.js` plays one in two headless browsers (see `docs/brawl.md`).

## Deploy

Pushing to `main` deploys. A job on the Mac polls GitHub every 2 minutes, fast-forwards, rebuilds
`web` and `tts`, and rolls back if `/healthz` fails.

To expose the site on a domain:

1. Cloudflare dashboard → Zero Trust → Networks → Tunnels → create a tunnel (Docker connector).
2. Put its token in `.env` as `CLOUDFLARE_TUNNEL_TOKEN`.
3. Add a public hostname for the domain pointing to `http://web:8000`.
4. `docker compose --profile tunnel up -d`

## Settings

Secrets live only in `.env` on the Mac; `.env.example` lists every key. The serials page needs
`SERIALS_PATH` and `SERIALS_PASSWORD`, plus Gmail (an app password) and forum logins for its
sources. The rest of the site runs with none of them.
