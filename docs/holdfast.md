# Holdfast (the game at /games/holdfast)

Read this before changing anything in `app/holdfast/`, `app/static/games/holdfast/`, or the
`tools/holdfast-*` scripts.

## What it is

Co-op tower defence for 1-4 players, each on their own phone or computer (a fifth and later
joiners watch). Everyone builds on one map, but each player has their own purse. Every kill pays
everyone who's connected equally, and a player can hand another 25 gold at a time, so the game is
arguing about who pays for what. Thirty waves; twenty lives between everyone (a Warlord costs
five). Three maps and three difficulties, picked by the host. Between waves there are 12 seconds
to build (25 before the first), or the wave comes at once when everyone presses Ready. The host
can run the game at ×1, ×2 or ×3.

Six towers, each with three levels: Archer (cheap, hits flyers), Cannon (splash, ground only),
Frost (slows), Ballista (long reach, ignores armour), Tesla (chains) and Beacon (towers beside it
fire faster). Anyone may pay to upgrade any tower; only its builder may sell it (for 70%). Seven
enemies: Grunt, Runner, Swarmling, Brute, Shieldbearer (armour), Flyer (ignores the road) and
Warlord (every tenth wave).

## How it works

- `app/holdfast/data.py` holds every number: towers, enemies, the wave recipe (`wave`), how
  health and bounties grow (`health`, `bounty`) and the maps. The browser is sent `TOWERS`,
  `ENEMIES` and the map, so its panels show the same numbers the server uses.
- `app/holdfast/game.py`: `Room.advance(dt)` is one step of the fight (spawn, walk, shoot, clear
  the dead, end the wave), fifteen steps a second, `speed` of them per tick. It has no I/O, so
  `tools/holdfast-sim.py` calls it directly. Shots land the instant they're fired; what the browser
  draws flying is decoration.
- Messages to the browser: `welcome` (the rules), `map`, `state` (players, towers, wave, lives:
  sent when something structural changes) and `s`, the snapshot, ten times a second (enemies as
  `[id, kind index, x, y, health %, slowed]`, the shots since the last one, every purse, and the
  seconds to the next wave).
- From the browser: `set`, `start`, `speed`, `again` (host); `build`, `up`, `sell`, `give`, `ready`.
- The browser (`js/main.js`) draws the board on one canvas in tile units and eases enemies between
  snapshots. The menu and lobby are the shared `games/shared/lobby.js` and `lobby.css`.

## Design directives

- **Separate purses, shared income.** This is the point of the game. Don't pool the gold.
- **More players doesn't mean tougher enemies.** Income is shared, so four players are no richer
  than one (bar 60 starting gold each). Scaling health by player count made four-player games
  much harder than solo ones.
- **Pressure all the way through, not only at the bosses.** Health grows as a polynomial
  (`1 + 0.45w + 0.06w²`), not an exponential: an exponential that's fair at wave 30 is a walkover
  until then.
- **The panels never lie**: every number shown comes from the data the server sent.
- **Works on a phone**: tap to build, the board on top and the panels under it.

## Gotchas

- **Kills and damage in `state` are only as fresh as the last `state`**, which is sent on
  structural changes (a build, a wave starting, a life lost), not on every kill. Gold is in every
  snapshot. The end screen is accurate because the end of the game sends a `state`.
- **Bounties go to whoever is connected.** A seated player who drops keeps their seat, their
  towers and their purse, but earns nothing until they're back; their gold is stuck until then.
- **Flyers take the straight line from where a road starts to the keep** (`Room.flights`), not the
  road, so towers along the road may never see them.
- **Armour is taken off each hit** (down to 15% of the hit at least) and grows with the wave, so
  fast, weak towers fade against Shieldbearers; Ballistas ignore it.
- **The best beacon in reach counts, not the sum**, and a beacon doesn't speed up beacons.
- **Tiles are whole numbers**: `Room.free` refuses anything that isn't an `int` in range.
- The games live in the web process's memory: a deploy ends every game in progress.

## Balance

`python3 tools/holdfast-sim.py` (about a minute for 3 games of every map, difficulty and 1, 2 and
4 players) plays whole games with simple builders that keep a fixed mix of towers, put each where
it covers the most road, and never sell, give gold or send a wave early. A decent human should do
better. With the current numbers (before enemy health stopped scaling with players, which made
the 2- and 4-player rows harder than they'd be now):

| | Easy | Normal | Hard |
|---|---|---|---|
| Meadow, 1 player | won 3/3 | won 3/3, 6-20 lives left | won 0/3, reached wave 19-30 |
| Crossing, 1 player | won 3/3 | won 1/3 | won 0/3, reached wave 9-10 |
| Coil, 1 player | won 3/3 | won 3/3 | won 1/3 |

After that change, a spot check on normal: Meadow won 3/3 with 1 or 2 players and 1/3 with 4;
Crossing won 1/3 solo and fell around wave 14-20 with 2 or 4 (the builders split their gold
badly across its two roads). Crossing is meant to be the hard map.

## Checking a change

- `python3 tools/holdfast-check.py` (a second): the room's rules. In `check-all.sh`.
- `python3 tools/holdfast-sim.py --fast` (2 s): one game of each map, to see the fight runs. In
  `check-all.sh`. The full run is for changes to the numbers; run it once, at the end.
- `node tools/holdfast-smoke.js --serve` (about 50 s): two browsers, one phone-sized, build, fight
  a wave, lose and reopen the room. In `check-all.sh`; skipped where Playwright isn't installed.
  `--shots <folder>` saves screenshots.
- After changing its CSS or JS: `python3 tools/bump-version.py app/static/games/holdfast`.
