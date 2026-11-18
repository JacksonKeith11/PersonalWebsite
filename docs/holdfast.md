# Holdfast (the game at /games/holdfast)

Read this before changing anything in `app/holdfast/`, `app/static/games/holdfast/`, or the
`tools/holdfast-*` scripts.

## What it is

Co-op tower defence for 1-4 players, each on their own phone or computer (a fifth and later
joiners watch). Everyone builds on one map, but each player has their own purse. Every kill pays
everyone who's connected equally, and a player can hand another 25 gold at a time, so the game is
arguing about who pays for what. Thirty waves; twenty lives between everyone (a Warlord costs
five). Five maps (Meadow, Crossing, Coil, Knot, where the road crosses itself, and Quarry, which
can only be built on in a few cleared patches) and three difficulties, picked by the host. Between waves there are 12 seconds
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
mutes them, remembered per browser; the 123 button floats damage numbers off enemies.

Eleven enemies: Grunt, Runner, Swarmling, Brute, Shieldbearer (armour), Flyer (ignores the road),
Warlord (every tenth wave; calls up Grunts as it walks), and four that make the paths matter: Ghost
(camouflaged: only towers that `detect`, auras, or towers beside a Spyglass beacon can target it;
from wave 7), Splitter (bursts into Swarmlings; from 9), Mender (heals the enemies around it; from
12) and Gargoyle (an armoured flyer; from 18).

The owner asked for these in November 2026, all built together:
- **Targeting**: each tower aims at the first enemy (nearest the keep), the last, the strongest or
  the closest; anyone may change it.
- **Abilities**: every final evolution has one (`ABILITIES` in data.py: a strike, a field-wide
  stun, slow or burn, overdrive, rally, mark, gold, bounty), on a cooldown that only runs while a
  wave is being fought. Anyone seated may set one off: from the tower's panel, the bar of abilities
  under the board, or Q.
- **End-of-game summary**: the tower of the game, each player's best tower (sold ones count), the
  waves where lives were lost, and whether it's a record.
- **Endless**: after wave 30 the host can keep going; the wave recipe carries on with every enemy
  mixed in. **Records**: how far each game got, by map, difficulty and party size (`save.py`),
  listed in the lobby.
- **Saves**: the game is saved at the start of every build phase (`data/holdfast.db`) and listed in
  the lobby of everyone who played in it; the host resumes it. Players who aren't back yet keep their
  seat, purse and towers until they rejoin. A game that ends deletes its save.
- **Polish**: the reach an upgrade would give shows while pointing at it; keys (1-9 tower, Z/X buy
  on a path, Q ability, T targeting, U undo, Space ready, Esc); a build or upgrade can be undone for
  a full refund for 5 seconds (`UNDO`), by whoever paid; damage numbers.

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
- Messages to the browser: `welcome` (the rules), `map` (with `build`, the only buildable tiles,
  on Quarry), `saves` (this browser's saved games), `note`, `state` (players, towers, wave, lives:
  sent when something structural changes; towers as `{id, k, p (path), n (tier), x, y, o (owner),
  s (spent), kills, dmg, tg (targeting), un ([payer, seconds of undo left] or null)}`; `summary`,
  `record_new` and `records` once a game ends, `records` in the lobby too) and `s`, the snapshot,
  ten times a second (enemies as `[id, kind index, x, y, health %, flags, damage since the last
  snapshot]` with flags 1 slowed, 2 burning, 4 stunned, 8 camouflaged; the shots since the last
  one, at most 80; `k`, the kill counts of towers that killed something; `a`, evolved towers'
  ability cooldowns; `x`, abilities used; `gl`, seconds left of Rally, Mark and Bounty Hunt; every
  purse; and the seconds to the next wave).
- From the browser: `set`, `start`, `resume`, `speed`, `again`, `endless` (host); `forget`;
  `build`, `up` (with `path`, 0 or 1), `sell`, `undo`, `target`, `ability`, `give`, `ready`.
- `app/holdfast/save.py`: saved games and records in SQLite, at `HOLDFAST_DB` (default
  `data/holdfast.db`; the checks and smoke test point it at a temporary file). Like Kingfall's saves,
  each carries a `VERSION`; one from another version is deleted when listed (no migrations yet).
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
- **Ability cooldowns, overdrive, Rally, Mark and Bounty Hunt run on fight time** (`Room.fight_t`,
  which only moves while a wave is on), so build phases don't burn them.
- **Splitters' Swarmlings and Warlords' Grunts are born mid-step** into `Room.born` and join the
  enemies at the end of the step, so a loop over enemies never grows under itself.
- **Menders don't add up**: an enemy near several is healed by the best one only. Stacked, four
  Menders in a crowd healed 20% a second and nothing could kill them.
- **The simulator turns saving off** (`room.saving = False`); anything else that makes rooms in a
  script should too, or point `HOLDFAST_DB` somewhere temporary.
- **A resumed game's towers keep their owner by browser token**: a tower whose builder never comes
  back has no owner, so nobody can sell it (anyone can still upgrade it).
- **Undo only takes back the latest build or upgrade on a tower**, within `UNDO` real seconds (not
  game seconds), and only for whoever paid.
- **Sounds are throttled to one per weapon every 70 ms**, or a Storm of Arrows (forty shots a
  second) would roar.
- **Tiles are whole numbers**: `Room.free` refuses anything that isn't an `int` in range.
- The games live in the web process's memory: a deploy ends every game in progress.

## Balance

`python3 tools/holdfast-sim.py` (about a minute and a half for 3 games of every map, difficulty and
1, 2 and 4 players) plays whole games with simple builders. They keep a fixed mix of towers, put each
where it covers the most road, take each tower down its usual path (`PREFER`), make sure something
can see Ghosts before wave 7, aim sniper ballistas at the strongest enemy, save for a final evolution
only from wave 15 with most of the price in hand, and use abilities when a crowd or a Warlord is on
the board. They never sell, give gold or send a wave early, and two builders can both upgrade one
tower (each remembers the tier it was saving for). A decent human should do better.

Latest run (November 2026, after targeting, abilities, the four new enemies, Knot and Quarry, and
the smarter builders; 3 games each, `won` and, if any were lost, the wave reached):

| | Easy | Normal | Hard |
|---|---|---|---|
| Meadow, 1 player | won 3/3 | won 3/3 | won 0/3, wave 14-20 |
| Meadow, 2 players | won 3/3 | won 1/3, wave 24-30 | won 0/3, wave 11-16 |
| Meadow, 4 players | won 3/3 | won 0/3, wave 16-20 | won 0/3, wave 10-11 |
| Crossing, 1 player | won 3/3 | won 3/3 | won 0/3, wave 19-21 |
| Crossing, 2 players | won 3/3 | won 3/3 | won 0/3, wave 9-19 |
| Crossing, 4 players | won 3/3 | won 2/3, wave 21-30 | won 0/3, wave 7-8 |
| Coil, 1 player | won 2/3, wave 29-30 | won 0/3, wave 24-29 | won 0/3, wave 19-20 |
| Coil, 2 players | won 2/3, wave 29-30 | won 0/3, wave 29-29 | won 0/3, wave 24-29 |
| Coil, 4 players | won 2/3, wave 29-30 | won 0/3, wave 24-29 | won 0/3, wave 10-20 |
| Knot, 1 player | won 0/3, wave 24-24 | won 0/3, wave 19-19 | won 0/3, wave 14-14 |
| Knot, 2 players | won 1/3, wave 19-30 | won 0/3, wave 19-29 | won 0/3, wave 14-19 |
| Knot, 4 players | won 1/3, wave 24-30 | won 1/3, wave 14-30 | won 0/3, wave 9-24 |
| Quarry, 1 player | won 3/3 | won 0/3, wave 29-29 | won 0/3, wave 16-29 |
| Quarry, 2 players | won 3/3 | won 0/3, wave 21-29 | won 0/3, wave 11-14 |
| Quarry, 4 players | won 3/3 | won 0/3, wave 16-24 | won 0/3, wave 9-11 |

Meadow and Crossing are about where they were (solo normal better), Quarry is fine on easy,
Coil got harder (it lost its "gentle" label to Meadow) and Knot is the hardest map, lost even on
easy alone, mostly on the flyer waves. Four-player games are harder than one or two (four builders
split the gold four ways and each builds less). Hard is lost everywhere by the builders. They
never reach a final evolution, so abilities barely figure here. If real games feel too hard on
Knot or Coil, the levers are the flyer waves and Gargoyles (`_extras` in data.py).

The run before these (upgrade paths, final evolutions and three new towers; three maps):

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

- `python3 tools/holdfast-check.py` (a few seconds): the room's rules, every tower's and ability's
  effects, the newer enemies, undo, endless, records, and saving and resuming (into a temporary
  database). In `check-all.sh`.
- `python3 tools/holdfast-sim.py --fast` (2 s): one game of each map, to see the fight runs. In
  `check-all.sh`. The full run is for changes to the numbers; run it once, at the end.
- `node tools/holdfast-smoke.js --serve` (about 50 s): two browsers, one phone-sized, build, undo,
  aim, upgrade, fight a wave, lose, read the end summary and see the record in the room. In `check-all.sh`; skipped where Playwright isn't installed.
  `--shots <folder>` saves screenshots.
- After changing its CSS or JS: `python3 tools/bump-version.py app/static/games/holdfast`.
