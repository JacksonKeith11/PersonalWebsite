# Scramble (the game at /games/scramble)

Read this before changing anything in `app/scramble/`, `app/static/games/scramble/`, or the
`tools/scramble-*` scripts.

## What it is

A side-on obstacle-course race for 1-8 players, each on their own phone or computer; the host can
add bots. Every round is a new course: a start, five to eight obstacle segments picked at random
(more in later rounds) and a finish. Touch a spike or a saw, or fall in a pit, and you start that
segment again from its flag. Racers run through each other. Once the first racer finishes, the
rest get 25 seconds. Points by place each round (10, 7, 5, 4, 3, 2, 1, 1; whoever doesn't finish
is placed by how far they got); most points after 3, 5 or 7 rounds wins.

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
- **Bots don't run the physics.** Each segment lists the surfaces a bot crosses (`Seg.route`), which
  `legs_of` turns into runs and jumps; `Room.move_bot` walks a bot along them at its own pace
  (`skill`, 0.62-0.92 of flat out) and now and then has it fluff a jump and restart the segment,
  more often on segments with a higher `risk`.
- **The clock**: the race time is `time.monotonic() - t0`, negative during the countdown. Every
  `pos` carries it, and the browser keeps the offset from the message that arrived quickest.
- The menu and lobby are the shared `games/shared/lobby.js` and `lobby.css` (Holdfast uses them too).

## Design directives

- **A segment must be finishable, and provably so.** `tools/scramble-check.mjs` searches the real
  physics for a way through several random builds of every segment, easy and hard. A new segment
  goes in `SEGMENTS` and must pass it.
- **Trust the browsers.** It's a game between friends: the server takes each browser's word for
  where its player is, and only refuses a finish quicker than 80% of a flat-out run with nothing
  in the way.
- **Phones work**: on a touch screen there are run and jump buttons, and on a narrow screen the
  view zooms out so at least 560 px of course fits across.
- **Nobody waits long**: 25 seconds after the first finisher, two seconds once only bots are still
  running, 150 seconds at most.

## Gotchas

- **`RUN` is in two places**: `course.py` (the bots' pace, and the finish check) and `physics.js`.
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

- `node tools/scramble-check.mjs` (about 20 s): every segment can be finished. In `check-all.sh`.
- `python3 tools/scramble-check.py` (2 s): bots race whole games on a fake clock; scoring,
  finishing, watching and leaving. Latest run: bots finish in 26-70 s (average 45), and about 1 in
  20 runs out of time. In `check-all.sh`.
- `node tools/scramble-smoke.js --serve` (about 40 s): two browsers, one phone-sized, and a bot race
  a round. In `check-all.sh`; skipped where Playwright isn't installed. `--shots <folder>` saves
  screenshots.
- After changing its CSS or JS: `python3 tools/bump-version.py app/static/games/scramble`.
