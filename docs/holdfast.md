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

Nine towers: Archer (cheap, hits flyers), Cannon (splash, ground only), Frost (slows), Ballista
(long reach, ignores armour), Tesla (chains), Beacon (helps the towers beside it), Brazier (sets
things burning; burning ignores armour), Mortar (shells anywhere on the board, ground only) and
Mint (pays its builder every wave, or raises the bounty on kills near it).

**Upgrades are Bloons-style** (the owner asked for different upgrades per tower and a final
evolution "like Bloons Tower Defense"). Every tower has two upgrade paths of four tiers; the first
upgrade picks a path for good, and the other closes. Tier four is the path's **final evolution**:
it costs 2,000-3,400 gold, renames the tower (Eagle Eye, Doomsday Gun, Storm Spire, Royal Mint…),
draws it gold-rimmed with a crown, and only one of each final evolution may stand on the map at a
time (selling it frees the place). Anyone may pay to upgrade any tower; only its builder may sell it
(for 70% of everything spent on it). Every tower counts its kills and damage, shown on its panel.

Every weapon has its own synthesized hit sound (and evolved towers sound bigger); the 🔊 button
mutes them, remembered per browser. Seven
enemies: Grunt, Runner, Swarmling, Brute, Shieldbearer (armour), Flyer (ignores the road) and
Warlord (every tenth wave).

## How it works

- `app/holdfast/data.py` holds every number: towers, enemies, the wave recipe (`wave`), how
  health and bounties grow (`health`, `bounty`) and the maps. A tower is its `base` numbers and
  two `paths` of tiers, each tier a `set` of numbers that replace the ones before; `stats(kind,
  path, tiers)` adds them up (the browser's `statsOf` does the same sum). The comment above
  `TOWERS` lists every number a tower can have. The browser is sent `TOWERS`, `ENEMIES` and the
  map, so its panels show the same numbers the server uses.
- A tower's `mode` decides how it fires (`Room.fire`): `shoot` (the `shots` enemies nearest the
  keep), `splash` (a blast on each of them, plus `cluster` small ones), `aura` (everything in
  reach), `chain`, or nothing (`support`, `income`). `Room.hurt` applies everything a hit carries:
  beacon `power`, the `boss` multiplier, `brittle`, armour (unless `pierce`), `shred`, `stun`,
  `burn` and `slow`. `Room.damage` takes the health off and credits the tower, its builder and,
  for a kill, everyone's bounty (raised by a Mint's `bounty` if the enemy died in its reach).
- `app/holdfast/game.py`: `Room.advance(dt)` is one step of the fight (spawn, walk, shoot, clear
  the dead, end the wave), fifteen steps a second, `speed` of them per tick. It has no I/O, so
  `tools/holdfast-sim.py` calls it directly. Shots land the instant they're fired; what the browser
  draws flying is decoration.
- Messages to the browser: `welcome` (the rules), `map`, `state` (players, towers, wave, lives:
  sent when something structural changes; towers as `{id, k, p (path), n (tier), x, y, o (owner),
  s (spent), kills, dmg}`) and `s`, the snapshot, ten times a second (enemies as `[id, kind index, x,
  y, health %, flags]` with flags 1 slowed, 2 burning, 4 stunned; the shots since the last one, at
  most 80; `k`, the kill counts of towers that killed something; every purse; and the seconds to the
  next wave).
- From the browser: `set`, `start`, `speed`, `again` (host); `build`, `up` (with `path`, 0 or 1),
  `sell`, `give`, `ready`.
- The browser (`js/main.js`) draws the board on one canvas in tile units and eases enemies between
  snapshots. The menu and lobby are the shared `games/shared/lobby.js` and `lobby.css`.

## Design directives

- **Separate purses, shared income.** This is the point of the game. Don't pool the gold.
- **More players doesn't mean tougher enemies.** Income is shared, so four players are no richer
  than one (bar 60 starting gold each). Scaling health by player count made four-player games
  much harder than solo ones.
- **Each tier should be worth about what it costs.** Damage per gold stays near the base tower's
  through tiers 1-2, a little better at tier 3 and about 1.4× at the final evolution, or upgrading
  is a trap. Paths trade: one leans on a single target (good against Warlords), the other on
  crowds or utility.
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
- **The best beacon in reach counts, not the sum**, for each of `boost`, `reach` and `power`
  separately; a beacon doesn't help beacons.
- **Burning ignores armour, and a stronger burn replaces a weaker one** (they don't stack). Stuns on
  Warlords last a third as long.
- **Kill counts live on the tower**: sold, they're gone. A burn's damage and kills go to the tower
  that lit it, even after it's sold.
- **Sounds are throttled to one per weapon every 70 ms**, or a Storm of Arrows (forty shots a
  second) would roar.
- **Tiles are whole numbers**: `Room.free` refuses anything that isn't an `int` in range.
- The games live in the web process's memory: a deploy ends every game in progress.

## Balance

`python3 tools/holdfast-sim.py` (about a minute for 3 games of every map, difficulty and 1, 2 and
4 players) plays whole games with simple builders that keep a fixed mix of towers, put each where
it covers the most road, upgrade along a path picked at random (final evolutions only from wave
15), and never sell, give gold or send a wave early. A decent human should do better: in
particular, the builders don't steer paths towards single-target damage before the Warlord waves.

Latest run (November 2026, after the upgrade paths, final evolutions and three new towers; 3 games
each, `won` and, if any were lost, the wave reached):

| | Easy | Normal | Hard |
|---|---|---|---|
| Meadow, 1 player | won 3/3 | won 1/3, wave 29-30 | won 0/3, wave 10-14 |
| Meadow, 2 players | won 3/3 | won 3/3 | won 0/3, wave 14-15 |
| Meadow, 4 players | won 3/3 | won 2/3, wave 30-30 | won 0/3, wave 9-14 |
| Crossing, 1 player | won 3/3 | won 1/3, wave 24-30 | won 0/3, wave 14-24 |
| Crossing, 2 players | won 3/3 | won 2/3, wave 29-30 | won 0/3, wave 9-10 |
| Crossing, 4 players | won 2/3, wave 30-30 | won 0/3, wave 20-30 | won 0/3, wave 9-9 |
| Coil, 1 player | won 3/3 | won 1/3, wave 20-30 | won 0/3, wave 14-24 |
| Coil, 2 players | won 2/3, wave 29-30 | won 0/3, wave 19-29 | won 0/3, wave 14-20 |
| Coil, 4 players | won 3/3 | won 0/3, wave 20-29 | won 0/3, wave 14-24 |

Compared with before: easy and two-player normal are about the same; solo normal is a little
harder (Meadow 1/3, was 3/3) and hard is much harder for the builders, which spend early gold on
Mints and Mortars that pay off late. Coil on normal with 2 or 4 players fell at waves 19-29 in all
six games (it was 1/3 won with 2 before). The builders rarely reach a final evolution (under one a game).

Before the upgrade paths (six towers, three levels each), with the numbers then (and before enemy
health stopped scaling with players):

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
