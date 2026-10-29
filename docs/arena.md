# Frag Arena (the game at /games/frag-arena)

Read this before changing anything in `app/arena/`, `app/static/games/arena/`, or the `tools/arena-*`
scripts.

## What it is

A Quake 3-style deathmatch in the browser. Everyone who opens the page joins one shared arena (up
to 12 players, bots included). Watchers who haven't pressed Play sit in the roster as "watching" and
see an orbiting camera. First to 20 frags wins the round. Then there's an 8-second intermission with
the scores up, everyone respawns, and scores reset. Bots can be added and removed from the menu by
anyone. They're for testing and solo play, and the owner and friends are the intended players.

- **Weapons** (all carried from spawn, with ammo): machine gun (hitscan, 7), shotgun (11 pellets of
  8), rocket launcher (100 direct, 100 splash over 3.75 m, knockback, rocket jumps), railgun (100,
  passes through players). One shared cooldown, as in Q3. The table is `WEAPONS` in `game.py` and
  is sent to the client.
- **Pickups**: health +25 (to 100), mega health +100 (to 200, on the middle platform), armor +50
  (absorbs two thirds of damage), ammo boxes. Health and armor above 100 tick down 1 a second.
- **Movement**: Q3's (`PHYS` in `world.py`): ground friction and acceleration, weak air control,
  so strafe-jumping and bunny-hopping (hold Space) build speed. Steps up to 0.5 m are walked, jump
  pads throw you onto the side ledges, and splash knockback is 0.15 m/s per point of damage, so a
  rocket at your feet as you jump lifts you about 9-10 m.
- **The map** is built in code (`build_map()` in `world.py`) from axis-aligned boxes: a 60 × 60
  floor, a central platform with stairs north and south, two side ledges with stairs and pads, four
  pillars, crates. The client draws whatever boxes the server sends.

## Code map

| File | Holds |
|---|---|
| `app/arena/world.py` | The map, box/ray geometry, the movement physics (`move`), and the bots' waypoint graph (`build_graph`, `path`). |
| `app/arena/game.py` | `Game`: joining, the 30 Hz tick, messages from clients, hitscan with lag compensation, rockets, splash, damage, frags, pickups, respawns, intermission, and the bots' brains. `GAME` is the one room. |
| `app/arena/routes.py` | `GET /games/frag-arena` (the page) and the WebSocket at `/games/frag-arena/ws`. |
| `app/static/games/arena/index.html` | The page: HUD, the menu (name, Play, bots, settings, controls), and the import map for three.js. |
| `js/main.js` | The client: input, your own movement, firing, server events, the camera, HUD and menu. |
| `js/physics.js` | **A copy of `world.py`'s physics** (and ray tests) for your own player. |
| `js/net.js` | The socket, the clock shared with the server, and the snapshot buffer other players are interpolated from. |
| `js/render.js` | three.js: map meshes with canvas-drawn textures, player and pickup models, the held weapon, effects. |
| `js/audio.js` | Every sound, synthesized with Web Audio when it plays, panned by position. |
| `game.css` | HUD and menu. The menu is the site's paper card. |

three.js 0.170.0 comes from cdnjs through an import map. There's no build step.

## How the netcode works

- **Your own movement is predicted, not checked.** The browser runs `physics.js` at 125 Hz and
  sends its position, velocity and view 30 times a second (`st`). The server takes it if it's in
  bounds and not inside a wall. That makes movement feel instant over the tunnel. It's fine for
  friends, but it's trivially cheatable; don't make the game public-competitive without moving
  this to the server.
- **Everything that hurts is the server's.** A `fire` message carries the eye position, the
  direction(s) and `at`, the server time the shooter was looking at. Hitscan rewinds every target
  to `at` (from `Player.history`, capped at `REWIND_MAX` = 0.35 s) and tests rays against the map
  and player boxes. So what you hit on your screen is what you hit. The server enforces cooldown
  (with `FIRE_SLACK` for jitter) and ammo.
- **Others are drawn 100 ms in the past** (`INTERP`), interpolated between snapshots. World events
  in snapshots (shots, rockets, explosions, frags) are queued and played when render time reaches
  their tick, so they line up with the players you see. Private events (`pv`: knockback, damage
  taken, hits, pickups, spawn) apply at once.
- **Your own rockets are simulated in the browser too** (`stepRockets`), so a rocket jump pushes
  you the moment it lands. The server skips sending you knockback for your own rockets
  (`predicted=True` in `damage`). If the server's rocket hits someone yours missed, its `boom`
  (matched by `lid`) explodes yours there.
- **Snapshots** go to every client every tick: all players' positions and views, which pickups are
  up, world events, and `me` (your health, armor, ammo, alive, life). `life` counts spawns, so
  reports from a past life are ignored. The roster (names, colors, scores, pings) goes out on change
  and every 2 s.
- The clock: `net.js` pings at 4 Hz for the first seconds, then every 2 s, and takes the offset
  from the quickest round trips.

## Bots

Bots live in `game.py` and move with the same `world.move` as players. Every ~0.12 s a bot looks
for the nearest enemy it can see (a ~145° view, unless that enemy is already its target or just
hit it). Seeing one, it turns toward it at a limited rate with some aim wobble (more with the
railgun), waits a reaction delay, fires when its aim is close enough, strafes, and keeps a range
that suits its weapon (picked by distance and ammo). Otherwise it walks the waypoint graph (A*) to
a goal: health when hurt, armor or ammo sometimes, where it last saw someone, or anywhere. It
jumps when stuck and replans after 2.5 s without progress.

The graph is built the first time a bot is added: nodes on a 3 m grid over every walkable box top,
plus the pickups, the stairs' ends and the pads, linked when a player could walk straight between
them on one level. Stairs and pads add hand-made links (`LINKS`); a pad only leads to its landing,
and walking links never cross a pad.

## Design directives

- **Friends first.** The owner plays this with friends. Responsiveness beats cheat-proofing, and
  bots are an option for testing and solo play, never forced on. Anyone in the arena can add or
  remove them, and they're removed when the last person leaves.
- **Quake, not a modern shooter**: fast movement, no reloading, no aim-down-sights, no loadouts,
  pickups on the map, rocket jumping.
- **No build step, no assets.** Textures are drawn on canvases, models are boxes, sounds are
  synthesized. Keep it that way.

## Gotchas

- **`world.py` and `physics.js` must agree.** They're the same algorithm in two languages. After
  changing either (or `PHYS`), run `node tools/arena-parity.mjs`, which drives both through the
  same inputs and fails if their paths differ.
- **The match lives in one process's memory.** uvicorn must stay at one worker (the Dockerfile's
  default). Every deploy restarts the container, which drops everyone and resets scores; the
  client reconnects on its own (1, 2, 4… s) and respawns if it was playing.
- **The tick only runs while someone is connected.** `Game.run` starts on the first join and
  stops, clearing bots and rockets, when the last person leaves.
- **Every module URL carries `?v=N`, and they must all match** (Cloudflare caches `/static`, and a
  module loaded under two URLs runs twice). When changing any of the game's JS or CSS, bump them
  together: `grep -rn "?v=" app/static/games/arena`.
- **Don't add or remove three.js lights at runtime**: it recompiles every shader. Flashes borrow
  from the fixed pool in `View.lights`.
- Map changes: boxes must not overlap spawns, pickups or waypoint paths in ways that trap players.
  Run `python3 tools/arena-check.py` afterwards: it checks every waypoint can reach every other,
  then plays 6 bots for 3 simulated minutes and fails if nobody scores, a bot stays stuck, or a tick
  gets slow.
- `?debug` on the page URL exposes `window.arena` (`S`, `net`, `view`, `keys`) for
  `tools/arena-smoke.js`, which plays two headless browsers against a running server (see its
  header). Headless rendering is software, a few frames a second, so test in a real browser for
  feel.
- `websockets` is pinned in `requirements.txt`; uvicorn's WebSocket support comes from it.
