# Scramble (the game at /games/scramble)

Read this before changing anything in `app/scramble/`, `app/static/games/scramble/`, or the
`tools/scramble-*` scripts.

## What it is

A side-on obstacle-course race for 1-8 players, each on their own phone or computer; the host can
add bots. Every round is a new course: a start, seven to eleven obstacle segments picked at random
from twenty-one kinds (more in later rounds) and a finish, in one of five themes (Meadow, Dunes,
Snowfield, Dusk, Caverns; dealt out so a game doesn't repeat one until all five are used). Three of
them play differently: **Snowfield** is ice (on the ground you speed up and slow down at 700 px/s²
instead of 3000, `ICE_ACC`), the **Dunes'** sand slows running on the ground to 0.8× (`SAND`; in the air you
get your speed back, so hopping beats running), and the **Caverns** are dark (only the drawing:
`darkness()` in `main.js` lights a pool round the racer the camera follows, dimmer ones round the
others, and glows round saws, boxes, flags, lava and the finish). The countdown and the first seconds
of the race say so. Each course gets harder along its length,
from difficulty 0.35 at the first obstacle to 1 at the last (`D_FIRST`), and every kind of segment
scales with it (wider gaps, thinner pillars, faster saws, extra hazards). Touch a spike or a saw, or
fall in a pit, and after 1.2 s you start that segment again from its flag. Racers run through each
other. Besides running and jumping there's an **air dash** (X, S, K or down; Dash on a phone): a burst
level and fast for 0.16 s, once per jump, given back on landing or a spring. Once the first racer finishes, the rest get 25 seconds or 70% of the winner's time, whichever
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
| Shield | Blocks the next bolt, freeze, swap or curse used on you (not traps) |
| Boost | Run 1.5× as fast for 2 s |
| Curse | Flips the controls of the racer just ahead for 3 s (bots run at 0.6× instead) |
| Grapple | Puts you where the racer just ahead last stood; they aren't moved. Back 60% of the field only |

Bolts and freezes **take 0.7 s to arrive** (`INCOMING`): the server sends `warn` to everyone, the
target's screen flashes red and says so, and a shield used before it lands blocks it. Bots holding a
shield use it in time 60% of the time. The leader never rolls a bolt, freeze, swap, curse or grapple; a racer with nobody behind never rolls a trap; a racer
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
- **Course pieces beyond solid blocks** (all in `physics.js`, all a function of the race time so
  every browser agrees): conveyor `belts` move whoever stands on them; `blinks` are solid for the first
  half of each period, set a quarter period apart so they come and go in a wave; `winds` push whoever
  is in them while they gust (over gaps only, so standing still is always safe); `lavas` rise from
  when a racer passes their trigger, per racer like crumbles (`p.lava`), and reset on a respawn. The
  `fork` segment has two ways over a trench: stones to hop or the floor and a lift (bots take either).
- **Crumbling blocks crumble for each racer separately**: `p.stood` in `physics.js` records when this
  player first stood on each, and a respawn resets it. Other racers' crumbles aren't drawn.
- **Bots don't run the physics.** Each segment lists the surfaces a bot crosses (`Seg.route`), which
  `legs_of` turns into runs and jumps; `Room.move_bot` walks a bot along them at its own pace
  (`skill`, 0.62-0.92 of flat out) and now and then has it fluff a jump and restart the segment,
  more often on segments with a higher `risk` (scaled up with the segment's difficulty, and by
  `ICE_RISK` on snow). On the dunes they run at 0.9× (half the sand's slowing: people can hop it).
  - **Dashes**: on a jump over 150 px a bot dashes with a chance of its skill less 0.2, getting
    across 1.3× quicker (`DASH_PACE`) and reporting `air` 2 so browsers draw its afterimages (a
    browser reports 2 while its own player dashes, too).
  - **Other ways through**: a segment can have a second route (`Seg.alt`; only the fork's trench so
    far), built into legs as `alts` (`course.build` returns it, by segment index). At the start of
    a round `Room.route_for` gives each bot its own legs (`Player.legs`), swapping the slow way in
    with a chance of 0.15 + 0.9 × (0.92 − skill), so clumsy bots take it more; a bot on the slow
    way never fluffs that segment (`Player.calm`). A `ride` leg waits for the lift to reach the
    bottom, then rides it up on the race clock (`Room.ride`), not the bot's pace.
  - **Items**: they run through boxes and look at using their item after a second or three, then
    every half second until it would do some good (`bot_items`): a swap or grapple once the racer
    ahead is 400 px ahead, a curse when that racer is in a risky segment, a freeze with two ahead or
    one within 900 px, a trap on the ground with someone within 450 px behind. After 8 s held
    (`BOT_PATIENCE`) they settle for less (150 px for a swap or grapple). Shields go up straight
    away (a shield stays up until something hits it, so holding one back gains nothing). Bots are
    caught once by each trap and run slower or faster while frozen or boosted.
  - A swap puts a bot on the nearest ground at or before where it lands (`Room.place_bot`).
- **Results**: the server counts each racer's falls, items used, items landed and hits taken
  (`stats` in `state`), gives up to four awards a round (`awards()`: Never fell, Sharpshooter, Most
  bolted, Item hoarder, Bounced back; at most one each, no ties), and keeps the room's best time
  through each kind of segment (`Room.records`, timed in `Room.timed` from crossing one flag to the
  next; a swap or grapple, a jump past several flags, or anything under a second doesn't count). The
  round's results list new records; the final screen lists them all.
- **Emotes and hats**: 1-6 (or the emote buttons) send `emote`; the server passes it on, at most one
  per racer per 1.2 s, and the browsers show a bubble over the racer and a line in the feed. Bots
  emote now and then when they hit someone or finish. A hat is picked in the lobby (`hat`, 0-8, kept in
  the browser's storage and sent again on joining); bots get a random one.
- **Watching**: once you've finished (or are sitting a round out), the camera follows whoever is
  running in front; the arrows (or the run buttons) move along the field.
- **Drawing**: a progress strip along the top shows the flags and every racer; a "?" by a name means
  they hold an item. Particles (dust, bursts on knock-outs, confetti at the line, sparks behind
  incoming items), a screen shake when you're knocked out, a squash on landing, legs that run by
  distance, and dash afterimages are all the browser's own, from what it already knows.
- **The clock**: the race time is `time.monotonic() - t0`, negative during the countdown. Every
  `pos` carries it, and the browser keeps the offset from the message that arrived quickest.
- The menu and lobby are the shared `games/shared/lobby.js` and `lobby.css` (Holdfast uses them too).

## Design directives

- **A segment must be finishable, and provably so.** `tools/scramble-check.mjs` searches the real
  physics for a way through several random builds of every segment, easy and hard, without the dash
  (so the dash is only ever a way to be quicker). A new segment
  goes in `SEGMENTS` and must pass it.
- **Catch-up through items, not rubber-banding.** The back of the field gets the bolts, freezes,
  swaps, curses, grapples and boosts; the leader gets shields and traps. Don't speed anyone up or slow anyone down
  except through an item.
- **Trust the browsers.** It's a game between friends: the server takes each browser's word for
  where its player is, and only refuses a finish quicker than 80% of a flat-out run with nothing
  in the way.
- **Phones work**: on a touch screen there are run and jump buttons, and on a narrow screen the
  view zooms out so at least 560 px of course fits across.
- **Nobody waits long**: 25 seconds after the first finisher, two seconds once only bots are still
  running, 150 seconds at most.

## Gotchas

- **`RUN` is in two places**: `course.py` (the bots' pace, and the finish check) and `physics.js`; `SAND` too.
  So are `KNOCKOUT` and the freeze, boost and curse numbers: `game.py` (bots, and what's drawn on
  others) and `main.js` (this player). The counts of hats and emotes are in both too.
- **Anything per-racer on the player object must be replaced, not changed** (`stood`, `lava`): the
  checker's search copies players shallowly. Its state key includes the lava start times.
- **A theme that changes the physics must be searched**: `physics.js` reads `c.theme` (the server
  sets it on the course after building it), and `tools/scramble-check.mjs` builds a hard variant of
  every segment for each such theme. Add a new one to its list. The checks there are why snow is
  700, not slipperier, and why sand slows running rather than jumping.
- **Blinking platforms must move slower than a runner**: the wave advances a platform a quarter
  period at a time; at 2.6 s or more that's under 300 px/s. Quicker and nobody can keep up with it.
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

- `node tools/scramble-check.mjs` (about 1 m 45 s): every segment can be finished, at difficulty 0.35
  and at 1, and at 1 on snow and on the dunes. In `check-all.sh`. A new segment goes in `SEGMENTS`
  and must pass it. On ice the search tells states apart by speed in steps of 100 px/s; finer and the
  600 states it keeps fill up with near-copies and it loses the way up the lava (a wider search,
  3000, finds it either way).
- `python3 tools/scramble-check.py` (about 5 s): bots race whole games on a fake clock (one human
  standing still, seven bots using items on each other); scoring, finishing, watching, leaving, every
  item (bolts and freezes arriving late, and blocked by a late shield), emotes, hats, records and
  awards; the fork's slow way and the lift, bot dashes, and bots waiting for a good moment to use an
  item. Latest runs (November 2026, after theme mechanics and smarter bots): bots finish in 36-123 s
  (average about 76), and 6-20 of about 105 run out of time (the runs before these changes: 11-15),
  mostly the slow bots that get hit most. Before the difficulty and item changes it was 26-70 s and
  about 5%. In `check-all.sh`.
- `node tools/scramble-smoke.js --serve` (about 45 s): two browsers, one phone-sized, and a bot race
  a round, including grabbing and using an item. In `check-all.sh`; skipped where Playwright isn't
  installed. `--shots <folder>` saves screenshots.
- After changing its CSS or JS: `python3 tools/bump-version.py app/static/games/scramble`.
