# Scramble (the game at /games/scramble)

Read this before changing anything in `app/scramble/`, `app/static/games/scramble/`, or the
`tools/scramble-*` scripts.

## What it is

A side-on obstacle-course race for 1-8 players, each on their own phone or computer; the host can
add bots. Every round is a new course: a start, seven to eleven obstacle segments picked at random
from sixteen kinds (more in later rounds) and a finish. Each course gets harder along its length,
from difficulty 0.35 at the first obstacle to 1 at the last (`D_FIRST`), and every kind of segment
scales with it (wider gaps, thinner pillars, faster saws, extra hazards). Touch a spike or a saw, or
fall in a pit, and after 1.2 s you start that segment again from its flag. Racers run through each
other. Once the first racer finishes, the rest get 25 seconds or 70% of the winner's time, whichever
is longer. Points by place each round (10, 7, 5, 4, 3, 2, 1, 1; whoever doesn't finish is placed by
how far they got); most points after 3, 5 or 7 rounds wins.

**Items** (the owner asked for a way to stop each other reaching the end). An item box (a "?")
sits at the start of every other obstacle. Running through one gives an item if your hands are
empty, once per box per racer; E, Shift or F (or Use on a phone) uses it. The further back you are,
the nastier the roll (`item_weights`):

| Item | Does |
|---|---|
| Bolt | Knocks out the racer just ahead (back to their flag) |
| Freeze | Everyone ahead runs at half speed for 2.5 s |
| Spike trap | Spikes where you stand (or where you land) for 12 s; they don't hurt whoever dropped them |
| Swap | Trade places with the racer just ahead; back half of the field only |
| Shield | Blocks the next bolt, freeze or swap used on you (not traps) |
| Boost | Run 1.5× as fast for 2 s |

The leader never rolls a bolt, freeze or swap; a racer with nobody behind never rolls a trap; a racer
alone on the course only rolls boosts.

## How it works

- **Each browser runs its own player's physics** (`js/physics.js`) and tells the server where it
  is, fifteen times a second (`{t: "p", v: [x, y, face, in the air, knocked out]}`). The server
  (`app/scramble/game.py`) passes everyone's position on twenty times a second (`pos`), runs the
  bots, and decides who finished when. Players never touch each other, so the only thing browsers
  must agree on is the clock: movers and saws are a function of the race time.
- **The course is data made on the server** (`app/scramble/course.py`) and sent whole (`course`)
  when a round starts and to anyone who joins mid-race. Each segment is a function that builds
  itself with some randomness and a difficulty from 0 to 1 (how far down the course it is).
  Everything is in pixels, y down, the ground's surface at y = 0; every segment starts and ends on
  it, so any can follow any.
- **Items are decided on the server.** A browser asks for a box's item (`grab`, with the box's
  index; the server checks it's near, unused by them and their hands are empty) and to use it
  (`use`). The server picks the target from everyone's positions and broadcasts `{t: "fx", k, by,
  to, blocked, warp?}`; each browser named in `to` does it to its own player (a bolt sets `dead`, a
  freeze or boost sets a timer that `main.js` turns into `p.speed`, a swap moves them to the spot in
  `warp`). The server does the same to bots, and keeps freeze and boost timers so everyone can see
  them (`pos` carries a seventh number per racer: 1 shielded, 2 frozen, 4 boosted). Traps are in
  `state` (`traps`), and each browser treats them as spikes.
- **Crumbling blocks crumble for each racer separately**: `p.stood` in `physics.js` records when this
  player first stood on each, and a respawn resets it. Other racers' crumbles aren't drawn.
- **Bots don't run the physics.** Each segment lists the surfaces a bot crosses (`Seg.route`), which
  `legs_of` turns into runs and jumps; `Room.move_bot` walks a bot along them at its own pace
  (`skill`, 0.62-0.92 of flat out) and now and then has it fluff a jump and restart the segment,
  more often on segments with a higher `risk` (scaled up with the segment's difficulty). Bots run
  through boxes, use their item after a second or three (holding a bolt, freeze or swap until
  someone is ahead, and a trap until someone is close behind), are caught once by each trap, and
  run slower or faster while frozen or boosted. A swap puts a bot on the nearest ground at or before
  where it lands (`Room.place_bot`).
- **The clock**: the race time is `time.monotonic() - t0`, negative during the countdown. Every
  `pos` carries it, and the browser keeps the offset from the message that arrived quickest.
- The menu and lobby are the shared `games/shared/lobby.js` and `lobby.css` (Holdfast uses them too).

## Design directives

- **A segment must be finishable, and provably so.** `tools/scramble-check.mjs` searches the real
  physics for a way through several random builds of every segment, easy and hard. A new segment
  goes in `SEGMENTS` and must pass it.
- **Catch-up through items, not rubber-banding.** The back of the field gets the bolts, freezes,
  swaps and boosts; the leader gets shields and traps. Don't speed anyone up or slow anyone down
  except through an item.
- **Trust the browsers.** It's a game between friends: the server takes each browser's word for
  where its player is, and only refuses a finish quicker than 80% of a flat-out run with nothing
  in the way.
- **Phones work**: on a touch screen there are run and jump buttons, and on a narrow screen the
  view zooms out so at least 560 px of course fits across.
- **Nobody waits long**: 25 seconds after the first finisher, two seconds once only bots are still
  running, 150 seconds at most.

## Gotchas

- **`RUN` is in two places**: `course.py` (the bots' pace, and the finish check) and `physics.js`.
  So are `KNOCKOUT` and the freeze and boost numbers: `game.py` (bots, and what's drawn on others)
  and `main.js` (this player).
- **A swap moves you to where the other racer last stood** (`Player.safe`, updated whenever a racer
  reports being on the ground and alive), never into mid-air, and sets your checkpoint from there.
- **Items can only hit racers still running** (`Room.running`); a racer who has finished is safe.
- **A box can only be grabbed with empty hands**, and the browser remembers which boxes it has asked
  about (`S.grabbed`), so running through a box while holding something uses it up for you.
- **A tap of jump is a short hop; holding it is the full jump** (144 px high, about 228 px far).
  Segments are sized for that: gaps up to about 180, steps up to about 90.
- **Feet resting on a platform must not count as running into its side.** `blocks` in `physics.js`
  ignores the bottom 3 px of the player; without it a moving platform's rounding error shoves its
  rider off sideways.
- **A jump key pressed and released between two frames** would be missed by reading held keys, so
  `main.js` latches it (`tapped`) until a physics step has seen it.
- **Bots pass through saws** and hop spikes on rails; their mistakes are dice (`risk`), not
  collisions. A segment's `route` must run left to right and join up with its neighbours
  (`tools/scramble-check.py` checks every leg starts where the last ended).
- The games live in the web process's memory: a deploy ends every race in progress.

## Checking a change

- `node tools/scramble-check.mjs` (about 40 s): every segment can be finished, at difficulty 0.35
  and at 1. In `check-all.sh`. A new segment goes in `SEGMENTS` and must pass it.
- `python3 tools/scramble-check.py` (about 5 s): bots race whole games on a fake clock (one human
  standing still, seven bots using items on each other); scoring, finishing, watching, leaving, and
  every item. Latest runs (November 2026, after the difficulty and item changes): bots finish in
  35-130 s (average 75), and 5-25% run out of time, mostly the slow bots that get hit most. Before
  those changes it was 26-70 s and about 5%. In `check-all.sh`.
- `node tools/scramble-smoke.js --serve` (about 45 s): two browsers, one phone-sized, and a bot race
  a round, including grabbing and using an item. In `check-all.sh`; skipped where Playwright isn't
  installed. `--shots <folder>` saves screenshots.
- After changing its CSS or JS: `python3 tools/bump-version.py app/static/games/scramble`.
