# Frag Arena (the game at /games/frag-arena)

Read this before changing anything in `app/arena/`, `app/static/games/arena/`, or the `tools/arena-*`
scripts.

## What it is

A Quake 3-style deathmatch in the browser, with Counter-Strike's bunny-hopping. Everyone who opens
the page joins one shared arena (up to 12 players, bots included). Watchers who haven't pressed Play sit in the roster as "watching" and
see an orbiting camera. First to 20 frags wins the round. Then there's an 8-second intermission with
the scores up, everyone respawns, and scores reset. Anyone can switch the round to a party mode
(Gun Game, Infection, Juggernaut) and mix in mutators from the menu; see "Modes and mutators". Bots
can be added and removed from the menu by anyone. They're for testing and solo play, and the owner
and friends are the intended players.

- **Weapons everyone carries** (keys 1-3): machine gun (hitscan, 11 a bullet, 11 a second; the
  owner asked for it stronger than Q3's), shotgun (11 pellets of 8), rocket launcher (100 direct,
  100 splash over 3.75 m, knockback, rocket jumps). One shared cooldown, as in Q3. The table is
  `WEAPONS` in `game.py` and is sent to the client. A knife (index 8) exists only in some modes.
- **Power weapons** (key 4): rare, one at a time. See below.
- **Pickups**: health +25 (to 100), mega health +100 (to 200, on the middle platform), armor +50
  (absorbs two thirds of damage), ammo boxes. Health and armor above 100 tick down 1 a second.
- **Movement** copies Counter-Strike's (`PHYS` in `world.py`; the owner asked for CS's
  bunny-hopping): CS:GO's ground acceleration and friction, at a quicker 10 m/s run. In the air the
  speed you can add toward where you're steering is capped (`air_cap`, CS's 30 of 250) but added
  fast (`air_accel` 12). So W does nothing mid-air, and strafing with A or D while turning the mouse
  the same way bends your path and builds speed: holding W and Space keeps 10 m/s, and good air
  strafing reaches about 18 m/s in a few jumps. There's no friction on the tick you land if Space is
  held, so hops keep their speed. Steps up to 0.5 m are walked, jump pads throw you onto the side
  ledges, and splash knockback is 0.15 m/s per point of damage, so a rocket at your feet as you
  jump lifts you about 9-10 m.
- **Maps** are built in code (`MAPS` in `world.py`) from axis-aligned boxes; the client draws
  whatever boxes the server sends. See "Maps".

## Power weapons

One power weapon appears 15 s into a match, at a random spot in `world.POWER_SPOTS` (a corner, a
ledge, or the top of a pillar that only a rocket jump reaches), and is announced. Whoever touches
it gets its charges, and it goes into slot 4, replacing any other power weapon. It's lost on death
or when its charges run out (you drop back to the machine gun). The next one appears 30-50 s after
it's taken; one nobody takes vanishes after 45 s and turns up elsewhere 5-10 s later. The owner
asked for the railgun to be one of these, and for others with weird effects:

| Weapon | Charges | What it does |
|---|---|---|
| Railgun | 6 | Hitscan, 100, through every player in a line. |
| Vortex | 3 | A shell that opens a black hole where it lands for 2.6 s: everyone within 9 m with line of sight is pulled in (the owner at half strength), hurt near the core, then thrown out by a 90 burst. |
| Ion orb | 2 | A slow orb that zaps everyone within 9 m (not its owner) for 12 four times a second, then explodes for 110. |
| Swapper | 5 | Hitscan, 15: you and whoever you hit trade places. |
| Yeet cannon | 6 | A fat hitscan blast, 20: flings whoever it hits (26 m/s along the shot plus 9 up), and kicks you back 9 m/s, so it doubles as a jump. |

Their projectiles fly on the server (`step_shots`); only rockets are also predicted in the browser.
Pulls and flings reach a person as `knock` events and are applied by their browser. Swaps move
both players on the server, and tell a person's browser with a `tp` event carrying `warp`, a count
of teleports. Like `life`, it makes the server ignore position reports from before the move.

## Maps

| Map | Builder | What it is |
|---|---|---|
| Arena | `build_arena` | The first one, 60 × 60: a central platform with the mega health, two side ledges with stairs and pads, four pillars (a power spot on one), crates. |
| Warehouse | `build_warehouse` | 64 × 48, two levels: grated catwalks 4 m up along both ends and a bridge down the middle (mega on it; pads from the floor), shipping containers below, two stacked ones a rocket jump reaches. Steel-blue light. |
| Spire | `build_spire` | 60 × 60: a stepped tower in the middle (tiers at 3, 6 and 9 m; stairs to the first two, pads from the second to the top, where a power weapon can appear), corner balconies with stairs, pillars and low walls. Violet dusk. |
| Twin Bases | `build_bases` | 80 × 40, Halo-style: two raised bases facing each other, each with stairs, a pad up, a parapet and a tower behind (rocket jump; power spot), a low platform with the mega in the middle. Overcast teal. Built with team modes in mind. |

Anyone picks the map in the menu's Game section, which starts a new round there for everyone (like
a mode change), and can tick "Next map after each round" to rotate through `MAPS` in order. A deploy
goes back to Arena.

- **`load_map(key)` empties and refills `world`'s lists in place** (`BOXES`, `PICKUPS`, `SPAWNS`,
  `NODES`...), sets `HALF` (the inside of the outer walls, used for the grid of waypoints and for
  checking reported positions) and `THEME` (sky, fog and sun colours). Code that reads
  `world.BOXES` etc. sees the new map; never copy them at import.
- **Each map's waypoint graph is built the first time bots play it** (0.2-0.35 s, which stalls one
  tick) and kept in `_GRAPHS`, so switching back is free.
- **Switching sends a `map` message** with the whole map (`map_payload`), before the new round's
  respawns. The browser rebuilds its meshes (disposing the old ones) and re-themes the sky.
- Builders share helpers: `outer(hx, hz)` (floor and walls, 16 m high so rocket jumps stay in),
  `stairs(...)` (along x or z, from any `base` height, with the bots' link up and down),
  `jump_pad(..., y=)` (from any height; worked out at normal gravity), `pickup`, `power_spot`,
  `spawn`.

## Modes and mutators

The owner asked for party modes from Halo and Counter-Strike. Anyone picks the mode and any mix of
mutators in the menu's Game section; a change starts a new round for everyone at once
(`Game.new_round`, also what ends an intermission), and is announced. The choice lasts until
someone changes it, even through an empty server; a deploy resets it to Deathmatch on Arena.

| Mode | How it plays |
|---|---|
| Deathmatch | As above. |
| Gun Game (CS:GO's Arms Race) | Everyone climbs `GUN_LADDER` (MG, SG, RL, ion orb, vortex, rail, knife), two kills a rung, with endless ammo and the knife always on 2. A kill on the last rung (the knife) wins. Dying by your own hand or a knife costs a kill. Score is kills toward the ladder. No power weapon spawns or ammo pickups. |
| Infection (Halo) | 10 s in, a random player (bot or person) becomes the first zombie: knife only, 1.25× run speed, no pickups. Whoever dies as a human comes back a zombie, and so does anyone who joins late. Humans can't hurt humans, nor zombies zombies. Zombies score for infecting, humans for killing zombies. The last survivor gets 200 health and 100 armor. Zombies win when no humans are left; humans win if any survive 3 minutes. Waits for two players. |
| Juggernaut (Halo) | Free for all until the first kill; the killer becomes the Juggernaut: 300 health and 100 armor (no decay), a random power weapon that gets a charge back every 5 s, drawn 1.3× bigger with a ring. Only the Juggernaut and the people hunting them can hurt each other, so everyone else is a team. The Juggernaut scores a point a kill; killing them scores one and takes the mantle. First to 10. |

| Mutator | Effect |
|---|---|
| Low gravity | Gravity × 0.45, so jumps go twice as high. Pads launch at × √0.45 and splash knockback is × √0.45, so pads land where they always do and rocket jumps reach the same height (but hang longer). |
| Instagib | Railguns only, endless, 300 damage. No pickups, no power weapons. |
| Rockets only | Rocket launchers only, endless. No ammo pickups, no power weapons. |
| Big heads | Heads drawn 2.3× bigger. Only the look; hitboxes stay boxes. |
| Power frenzy | Power weapons appear 3 s in and every 4-8 s after one is taken; untaken ones vanish after 20 s. |

How it's built:

- **The kit.** `Game.kit(p)` says what p may hold, in slot order, and which weapons never run out,
  from the mode, p's role and the mutators. `sync_kit` runs every tick: it keeps p holding an
  allowed weapon, tops up endless ones, and sends the browser a `kit` event when the kit changes.
  The browser's number keys, wheel and HUD slots all follow the kit (`S.allow`, `S.inf`), and the
  server refuses shots and weapon choices outside it.
- **Roles.** `Player.role` is `"zombie"`, `"jugg"` or empty, set through `set_role`, sent in the
  roster (its ninth field) and drawn by `render.js` (green zombies with red eyes; the
  Juggernaut). `Game.friendly(a, b)` decides who can't hurt whom; `damage` checks it first, so
  teammates get no knockback from each other either.
- **The rules message** (`t: "rules"`): map, rotation, mode, mutators, score limit, physics,
  knockback, and the Infection timers (`alpha`, when the first zombie is picked; `ends`). Sent after `welcome` and
  whenever they change. The HUD's mode line under the scores is built from it and the roster.
- **Run speed** is a body's `fast` (zombies' 1.25), part of the physics in both copies.
- Bots skip teammates when picking targets, hunt (zombies know where the living are, and everyone
  knows where the Juggernaut is), charge with the knife, and only fire it in reach.

## Code map

| File | Holds |
|---|---|
| `app/arena/world.py` | The maps and `load_map`, box/ray geometry, the movement physics (`move`), and the bots' waypoint graph (`build_graph`, `path`). |
| `app/arena/game.py` | `Game`: joining and rejoining, the 30 Hz tick, messages from clients, hitscan with lag compensation, projectiles, black holes, splash, damage, frags, pickups, power weapons, respawns, rounds, modes and mutators, and the bots' brains. `GAME` is the one room. |
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
- **Leaving and coming back keeps your place.** The browser keeps a random `token` in
  localStorage and a `tab` id in sessionStorage, and sends both in `hello`. If the token's player is
  still connected from the same tab (a reload, or a reconnect before the server noticed the old
  socket die), the new socket takes the player over and the old one is closed. If they left, their
  `Player` (id, colour, score, deaths) waits in `Game.away` for 20 minutes (`AWAY_KEEP`) and is
  restored. A second tab of the same browser is a separate, unremembered player. `leave(p, queue)`
  ignores a closing socket that no longer owns its player. A deploy still forgets everyone.
- The clock: `net.js` pings at 4 Hz for the first seconds, then every 2 s, and takes the offset
  from the quickest round trips.

## Bots

Bots live in `game.py` and move with the same `world.move` as players. Every ~0.12 s a bot looks
for the nearest enemy it can see (a ~145° view, unless that enemy is already its target or just
hit it). Seeing one, it turns toward it at a limited rate with some aim wobble (more with the
railgun), waits a reaction delay, fires when its aim is close enough, strafes, and keeps a range
that suits its weapon (picked by distance and ammo). Otherwise it walks the waypoint graph (A*) to
a goal: health when hurt, armor or ammo sometimes, a power weapon, where it last saw someone, or
anywhere. Within 25 m of a power weapon it can reach (`POWER_SPOTS[...]["bots"]`), it runs for it
even mid-fight, still shooting (`Brain.rush`). It jumps when stuck and replans after 2.5 s without
progress. Bots don't air-strafe.

The graph is built the first time a bot is added: nodes on a 3 m grid over every walkable box top,
plus the pickups, the stairs' ends and the pads, linked when a player could walk straight between
them on one level. Stairs and pads add hand-made links (`LINKS`); a pad only leads to its landing,
and walking links never cross a pad.

## Design directives

- **Friends first.** The owner plays this with friends. Responsiveness beats cheat-proofing, and
  bots are an option for testing and solo play, never forced on. Anyone in the arena can add or
  remove them, and they're removed when the last person leaves.
- **Quake, not a modern shooter**: fast movement, no reloading, no aim-down-sights, no loadouts,
  pickups on the map, rocket jumping. Movement is the exception: CS's air strafing, on request.
- **Power weapons are rare and strange.** One on the map at a time, few charges, lost on death.
  New ones should do something odd, not just more damage.
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
- Map changes and new maps: boxes must not overlap spawns, pickups or waypoint paths in ways that
  trap players. Run `python3 tools/arena-check.py` afterwards: for every map it checks every
  waypoint can reach every other and that spawns, pickups and bots' power spots are clear and on
  the graph, then plays 6 bots on each map for 3 simulated minutes (failing if nobody scores, a bot
  stays stuck, or a tick gets slow), then plays each party mode and a few mutators. Common
  failures: stairs whose foot ends hard against a wall or another box (the link's lower end can't
  join the floor's waypoints; leave about 3 m clear), and a ledge bots can climb to but not walk
  down from (add a one-way link off it, as the Spire's top has). Also check pads land where they
  should, at both gravities.
- **The low gravity mutator rewrites `world.PHYS` in place** (`new_round` restores it from
  `world.BASE_PHYS` first), since bots' movement reads it. Anything that reads `PHYS` reads the
  round's physics, and the browser gets them in the rules message (`setPhys`). Jump pads are built
  once with normal gravity; `pad_mul` scales their launch.
- **A new mode** needs an entry in `MODES`, its kit in `kit`, its scoring in `kill`, any rules it
  keeps in `step_mode`, a line in `modeLine` and `MODE_BLURB` (`main.js`), and a run in
  `tools/arena-check.py` that checks it does its thing. New weapons go after the knife, or every
  index in both languages moves.
- `?debug` on the page URL exposes `window.arena` (`S`, `net`, `view`, `keys`) for
  `tools/arena-smoke.js`, which plays two headless browsers against a running server (see its
  header). Headless rendering is software, a few frames a second, so test in a real browser for
  feel.
- A new power spot needs `bots: False` if bots can't walk there, or the waypoint check fails (an
  unreachable node). A new power weapon needs a `POWER_COLOR` and a `gunModel` case in `render.js`
  (by index), sounds keyed by its `key` in `audio.js`, and handling in `bot_weapon` and the range
  table in `bot_tick`.
- Testing rejoins in one browser: two tabs are two players, but a reload is the same player.
- `websockets` is pinned in `requirements.txt`; uvicorn's WebSocket support comes from it.
