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

Fifteen towers: Archer (cheap, hits flyers), Cannon (splash, ground only), Frost (slows), Ballista
(long reach, ignores armour, bolts through three), Tesla (chains), Beacon (helps the towers beside it),
Brazier (sets things burning; burning ignores armour), Mortar (lobs shells anywhere on the board,
ground only), Mint (pays its builder every wave, or raises the bounty on kills near it), and, from
November 2026, Bladewheel (blades all round itself, or a ring of fire), Trapper (lays spikes or mines
on the road), Workshop (builds sentries beside the road), Arcanist (arcane bolts, or fireballs),
Skyhook (anti-air; one path learns to hit the ground) and Alchemist (acid that hurts anything and
eats armour, or potions that make the towers near it stronger and let them hurt every type).

**Upgrades are Bloons-style** (the owner asked for different upgrades per tower and a final
evolution "like Bloons Tower Defense", then for crosspathing). Every tower has two upgrade paths of
four tiers. Both can be bought, but only one past tier 2, so a tower is at most 4-2. The path with
more tiers is the tower's main path (on a tie, the one bought first): its tiers count in full. Each
of the other path's tiers gives only its `cross` bonus, a smaller one written for it (`cross` in
data.py: multiply damage or rate, add pierce, see Ghosts...). The panel says "On the side: ..." for
those. Tier four is the main path's **final evolution**: it costs 1,400-2,400 gold, renames the tower
(Eagle Eye, Doomsday Gun, Storm Spire, Royal Mint…), draws it gold-rimmed with a crown, and only one
of each final evolution may stand on the map at a time (selling it frees the place). Anyone may pay
to upgrade any tower; only its builder may sell it (for 70% of everything spent on it). Every tower
counts its kills and damage, shown on its panel.

The owner asked for these in November 2026, all built together, after a comparison with Bloons TD 6:
- **Real projectiles and pierce.** Arrows, bolts, shells, blades, harpoons, flasks and sentry bolts
  are `Shot`s: they fly at the tower's `speed`, aimed where the target will be (`Room.lead`), and can
  miss when it stops, turns a corner or dies first. Each goes through `pierce` enemies and hits any
  enemy it meets, Ghosts included (only aiming needs `detect`). Shells (`splash`) burst on the first
  enemy they meet or where they were aimed; mortar shells are lobbed (`lob`) and land where they were
  aimed after `LOB_TIME`, so moving targets can dodge them. Auras and lightning are still instant.
  (The old `pierce`, ignoring armour, is now `ap`.)
- **Damage types and immunities.** Every attack has a `dtype`: sharp, blast, cold, energy (lightning),
  fire, arcane or normal. Ironclad is immune to sharp, Cinder to blast, Frostborn to cold, Warded to
  energy, fire and arcane; the Stormhulk to energy and the Ironmaw to sharp. Immune means no damage
  and no slow, stun or burn from that hit. Normal hurts everything: some tier-3 upgrades turn a tower
  normal (Bodkin Points, Shatter Shells, Steel Bolts, Overcharge, Siege Shells, Iron Spikes, Unravel),
  as do most final evolutions; a tower beside an Alchemist's Solvent Draught (`unlock`) hurts every
  type, and the Arcanist's Unmake strips every enemy's immunities and armour for 8 s. The wave
  preview warns when nothing built can hurt something coming.
- **Layered enemies.** An enemy's `children` burst out when it dies (they keep its camouflage):
  Brute → 2 Grunts, Splitter → 3 Swarmlings, Ironclad → 2 Grunts, Cinder → 2 Swarmlings, Frostborn
  and Warded → 2 Runners, and two blimps: Juggernaut (from wave 22; → 4 Brutes, costs 4 lives) and
  Colossus (wave 29 and endless; → 2 Juggernauts, costs 10). Towers' `boss` bonus counts against
  blimps, and stuns last a third as long on them.
- **Things towers put on the board.** Trappers lay piles (`Trap`) on road points in reach, up to
  `max` at once, each lasting `life` seconds of fighting: spikes hurt `hits` enemies (each once),
  mines burst on the first. Workshops build `Sentry`s on free squares beside the road, preferring one
  in reach of the nearest enemy; they fight with their own numbers (`sentry` in data.py), last `life`
  seconds, credit their workshop, and pack up when the wave ends (piles stay).
- **Boss events.** The host picks the bosses in the lobby (`BOSSES`): Warlords (the classic, one more
  every tenth wave), the Gravewarden, the Stormhulk, the Ironmaw or a random one each time
  (`Room.boss_kind`, seeded by the game, so the preview and the wave agree). A named boss comes alone,
  a tier tougher each time (tier = wave / 10: half again its health a tier), costs 10 lives if it gets
  through, and has two skulls (66% and 33% health) where it does its move: the Gravewarden turns
  untouchable for 2.5 s and raises a ring of Ghosts (and calls up Grunts as it walks); the Stormhulk
  knocks out every tower within 4 squares for 3 s (and every 9 s the best tower within 5); the Ironmaw
  grows a shell (12% of its health, soaked up first) and charges at 2.5x for 3 s. A bar over the board
  shows its health, skulls and shell.
- **One-use items** (`ITEMS`), bought from your own purse: Caltrops (a pile of 30 spikes on the
  road), Tar Pot (a pool that halves speed for 10 s), Powder Keg (a blast anywhere), Hired Bow (a
  sentry for 45 s that sees Ghosts and hurts anything), War Horn (every tower ×1.5 for 8 s) and Frost
  Flask (freezes everything for 2 s). Costs and damage grow with the wave; each player waits the
  item's cooldown (fight time) before using the same one again. Keg, Horn and Flask only while a wave
  is on.

Every weapon has its own synthesized sound (and evolved towers sound bigger); the 🔊 button
mutes them, remembered per browser; the 123 button floats damage numbers off enemies.

Twenty enemies: Grunt, Runner, Swarmling, Brute, Shieldbearer (armour), Flyer (ignores the road),
Warlord (every tenth wave; calls up Grunts as it walks), Ghost (camouflaged: only towers that
`detect`, auras, or towers beside a Spyglass beacon can target it; from wave 7), Ironclad (8),
Splitter (9), Cinder (11), Mender (heals the enemies around it; 12), Frostborn (13), Warded (15),
Gargoyle (an armoured flyer; 18), Juggernaut (22), Colossus (29), and the three event bosses.

Earlier in November 2026, also asked for and built together:
- **Targeting**: each tower aims at the first enemy (nearest the keep), the last, the strongest or
  the closest; anyone may change it.
- **Abilities**: every final evolution has one (`ABILITIES` in data.py: a strike, a field-wide
  stun, slow or burn, overdrive, rally, mark, gold, bounty), on a cooldown that only runs while a
  wave is being fought. Anyone seated may set one off: from the tower's panel, the bar of abilities
  under the board, or Q.
- **End-of-game summary**: the tower of the game, each player's best tower (sold ones count), the
  waves where lives were lost, and whether it's a record.
- **Endless**: after wave 30 the host can keep going; the wave recipe carries on with every enemy
  mixed in. Health also compounds by `ENDLESS_GROWTH` (20%) a wave on top of the polynomial, and
  enemies walk faster (`pace`: 1.5% a wave, at most +50%), while bounties grow only slowly, so every
  defence falls in the end (asked for in November 2026: the test builders sat at wave 71 with all
  thirty evolutions and 24,000 gold unspent). With 20% they fall on waves 39-44 (one game each on
  Coil, Knot and Meadow, solo and two players; one two-player Knot game fell on 24); 12% still let
  them hold past wave 62. **Records**: how far each game got, by map, difficulty and party size (`save.py`),
  listed in the lobby.
- **Saves**: the game is saved at the start of every build phase (`data/holdfast.db`) and listed in
  the lobby of everyone who played in it; the host resumes it. Players who aren't back yet keep their
  seat, purse and towers until they rejoin. A game that ends deletes its save.
- **Next-wave preview** (asked for with the balance pass below): the wave box lists what's coming,
  each kind drawn as on the board, with how many and what's special (camouflaged, flies, armoured,
  heals, splits, costs 5 lives); during a fight it shows the wave after. It warns when nothing built
  can see Ghosts (towers send `cs`, whether they can) or hit flyers (worked out from `statsOf`). It
  only redraws when the wave, the towers' warnings or the list change, not on every snapshot.
- **Polish**: the reach an upgrade would give shows while pointing at it; keys (1-9 tower, Z/X buy
  on a path, Q ability, T targeting, U undo, Space ready, Esc); a build or upgrade can be undone for
  a full refund for 5 seconds (`UNDO`), by whoever paid; damage numbers.

## How it works

- `app/holdfast/data.py` holds every number: towers, enemies, bosses, items, the wave recipe
  (`wave`), how health and bounties grow (`health`, `bounty`) and the maps. A tower is its `base`
  numbers and two `paths` of tiers, each tier a `set` of numbers that replace the ones before and a
  `cross` bonus for when it's on the side path; `stats(kind, tiers, first)` adds them up and
  `can_buy(tiers, path)` says whether the next tier may be bought (the browser's `statsOf` and
  `canBuy` do the same). The comment above `TOWERS` lists every number a tower can have and how
  `cross` numbers combine. The browser is sent `TOWERS`, `ENEMIES`, `ITEMS`, `BOSSES` and the map,
  so its panels show the same numbers the server uses.
- A tower's `mode` decides how it fires (`Room.fire`): `shoot` (a projectile at each of the `shots`
  enemies first in line, the rest fanned out), `splash` (a shell, `lob`bed or not, that bursts with
  `cluster` small ones), `radial` (projectiles all round), `aura` (everything in reach), `chain`,
  `trap` (`Room.lay`), `sentry` (`Room.assemble`), or nothing (`support`, `income`). A `Sentry`
  fires through the same `Room.fire`. `Room.fly` moves projectiles in quarter-tile substeps and
  hits what they meet; `Room.spring` sets off piles. `Room.hurt(e, dmg, src, st)` applies everything
  a hit carries (`st` is the tower's or the sentry's numbers): immunity (unless `unlock` or Unmake),
  support `power`, Mark, the `boss` multiplier on bosses and blimps, `brittle`, armour (unless `ap`),
  `shred`, `stun`, `burn` and `slow`. `Room.damage` lets a shell soak it up first, takes the health
  off, sets off a boss's skull (`Room.skull`), and credits the tower, its builder and, for a kill,
  everyone's bounty (raised by any tower's `bounty` if the enemy died in its reach), then bursts the
  enemy into its children (`Room.killed`).
- `app/holdfast/game.py`: `Room.advance(dt)` is one step of the fight (spawn, walk, boss moves,
  piles, projectiles, towers, sentries, clear the dead, end the wave), fifteen steps a second,
  `speed` of them per tick. It has no I/O, so `tools/holdfast-sim.py` calls it directly.
- Messages to the browser: `welcome` (the rules), `map` (with `build`, the only buildable tiles,
  on Quarry), `saves` (this browser's saved games), `note`, `state` (players, towers, wave, lives,
  the boss event: sent when something structural changes; towers as `{id, k, p (main path), n (its
  tiers), c ([tiers on each path]), f (path bought first), x, y, o (owner), s (spent), kills, dmg,
  tg (targeting), un ([payer, seconds of undo left] or null), cs (can see Ghosts), ul (hurts every
  type)}`; `coming`, the next wave's `[kind, count]` groups with the boss event's boss in place;
  `item_wave`, the wave item prices go by; `summary`, `record_new` and `records` once a game ends,
  `records` in the lobby too) and `s`, the snapshot, ten times a second: `e`, enemies as `[id, kind
  index, x, y, health %, flags, damage since the last snapshot]` with flags 1 slowed, 2 burning,
  4 stunned, 8 camouflaged, 16 untouchable, 32 shelled, 64 charging; `bo`, event bosses as `[id, kind
  index, health %, tier, shell %]`; `f`, instant shots `[tower id, from x, from y, points...]` (no
  points: an aura's pulse), at most 80; `p`, new projectiles `[id, tower id, style, x, y, vx, vy,
  seconds]` (at most 160; the browser flies them itself) and `pe`, the drawn ones that stopped;
  `bx`, blasts `[x, y, radius, look]`; `tr`, piles `[id, 0 spike / 1 mine / 2 tar, x, y]`; `se`,
  sentries `[id, x, y, workshop id]`; `dz`, towers knocked out and for how long; `k`, kill counts of
  towers that killed something; `a`, evolved towers' ability cooldowns; `x`, abilities, items and
  boss moves (`[tower id or 0, what, points...]`); `gl`, seconds left of Rally, Mark, Bounty Hunt and
  Unmake; `g`, every purse; `ic`, each player's item cooldowns; `n`, the seconds to the next wave.
- From the browser: `set` (map, diff, bosses), `start`, `resume`, `speed`, `again`, `endless`
  (host); `forget`; `build`, `up` (with `path`, 0 or 1), `sell`, `undo`, `target`, `ability`,
  `item` (`k`, and `x`, `y` unless it isn't aimed), `give`, `ready`.
- `app/holdfast/save.py`: saved games and records in SQLite, at `HOLDFAST_DB` (default
  `data/holdfast.db`; the checks and smoke test point it at a temporary file). Like Kingfall's saves,
  each carries a `VERSION`; one from another version is deleted when listed (no migrations yet).
  Version 2 (crosspathing and boss events) dropped every earlier save. Piles and sentries aren't
  saved: a resumed game starts its build phase without them.
- The browser (`js/main.js`) draws the board on one canvas in tile units, eases enemies between
  snapshots and flies projectiles along their sent velocity until they stop or run out of time.
  The boss bar is a DOM element over the board. The menu and lobby are the shared
  `games/shared/lobby.js` and `lobby.css`.

## Design directives

- **Separate purses, shared income.** This is the point of the game. Don't pool the gold.
- **More players doesn't mean tougher enemies.** Income is shared, so four players are no richer
  than one (bar 60 starting gold each). Scaling health by player count made four-player games
  much harder than solo ones.
- **Each tier should be worth about what it costs.** Damage per gold stays near the base tower's
  through tiers 1-2, a little better at tier 3 and about twice as good at the final evolution, or
  upgrading is a trap. The evolution is the exception on purpose: at the old prices (about 1.4×)
  nobody, not even the test builders, could save up for one in a 30-wave game, so the abilities
  never came out. Paths trade: one leans on a single target (good against Warlords), the other on
  crowds or utility.
- **A side tier is a modest bonus, written for it.** Letting the side path's tiers apply their full
  `set` made 4-2 towers far too strong (Twin Shot on a Bodkin archer doubled its damage for 150
  gold), so each tier has a `cross` of its own instead. Keep it small: about a tier's worth of what
  it costs.
- **Every immunity has answers.** Each immune enemy must be hurt by several towers' base attacks
  and by the normal-type upgrades, and the preview warns when nothing built can.
- **Boss events are harder than Warlords, but winnable.** A boss that got through first cost every
  life, and with its first numbers the test builders lost every game on wave 10.
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
  road, so towers along the road may never see them. On maps whose road winds back towards its start
  (Coil, Knot) that line is short, which is why the flyer waves (every wave ending in 4 or 9) were
  where those maps were lost; flyer waves are kept small (`n(5)`) for that reason.
- **Armour is taken off each hit** (down to 15% of the hit at least) and grows with the wave, so
  fast, weak towers fade against Shieldbearers; Ballistas ignore it.
- **The best beacon in reach counts, not the sum**, for each of `boost`, `reach` and `power`
  separately; a beacon doesn't help beacons.
- **Burning ignores armour, and a stronger burn replaces a weaker one** (they don't stack). Stuns on
  bosses and blimps last a third as long. A burn is fire only in that it needs the hit that lit it to
  get through: Warded can't be set burning by fire, but an acid or Hot Blades burn (normal, sharp)
  can.
- **Projectiles hit any Ghost they meet**, though only towers that `detect` aim at Ghosts. Arrows
  already loosed keep flying after their tower is sold, and still credit it.
- **A projectile hits an enemy within its `size` plus `HIT_PAD`**: a target that stops dead (a stun,
  a corner) after an arrow is aimed ahead of it is missed only if the lead was more than that. Big
  enemies have bigger `size`s, so they're hard to miss.
- **Support keys mean support on any tower.** `boosts()` treats any tower with `boost`, `reach`,
  `power`, `reveal` or `unlock` as helping its neighbours (the Alchemist's Elixirs path does), so an
  attacking tower must never get one of those keys for itself.
- **Income and bounty work on any tower**, not only Mints (the Philosopher's Stone pays 150 a wave).
- **The main path can change**: a tower at 1-1 whose second path goes to 3 becomes that path's
  tower, and the first path's tiers turn into side bonuses. Undo hands `first` to the other path when
  the first one's last tier is taken back.
- **Towers' stuns can't lock an enemy forever**: once a tower's stun wears off, an enemy shrugs off
  towers' stuns for `STUN_GUARD` (1 s) (`Enemy.stun_guard`). Endless defences full of stunning towers
  (Blizzard, Thunder God, Carpet Bomber, mines, sentries) otherwise held whole waves still. Abilities
  and the Frost Flask ignore the guard.
- **Endless waves are long**: big defences slow everything by 70%, so a wave on Coil can take three
  minutes of game time, and the simulator crawls past wave 50.
- **The sidebar keeps its layout.** The wave box has a fixed height (its list scrolls), Ready keeps
  its space when hidden, and Undo and Sell sit in a fixed row at the top of the tower panel, always
  there (greyed when unusable): the panel used to jump as the coming list, the Ready button and Undo
  came and went, and a click meant for an upgrade could land on Sell.
- **The Stormhulk's knock-outs, Rally, Mark, Bounty Hunt, Unmake, sentries' and piles' lives and
  item cooldowns all run on fight time.**
- **Sentries pack up at the end of a wave; piles stay** until their life or their hits run out.
- **Kill counts live on the tower**: sold, they're gone. A burn's damage and kills go to the tower
  that lit it, even after it's sold.
- **Ability cooldowns, overdrive, Rally, Mark and Bounty Hunt run on fight time** (`Room.fight_t`,
  which only moves while a wave is on), so build phases don't burn them.
- **Children, summoned Grunts and raised Ghosts are born mid-step** into `Room.born` and join the
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
  second) would roar. Weapons sound when they fire, and blasts once a snapshot.
- **Projectiles are the slow part of the simulator**: the full balance run takes several times as
  long as it did with instant hits (`in_reach` checks distance first for that reason).
- **Tiles are whole numbers**: `Room.free` refuses anything that isn't an `int` in range.
- The games live in the web process's memory: a deploy ends every game in progress.

## Balance

`python3 tools/holdfast-sim.py` (about three minutes for 3 games of every map, difficulty and
1, 2 and 4 players) plays whole games with simple builders. They keep a fixed mix of towers, put each
where it covers the most road, take each tower down its usual path (`PREFER`), make sure something
can see Ghosts before wave 7, aim sniper ballistas at the strongest enemy, save for a final evolution
only from wave 15 with most of the price in hand, and use abilities when a crowd or a Warlord is on
the board. They never sell, give gold, use items or send a wave early; now and then they buy a tier or two on a
tower's other path; and two builders can both upgrade one tower (each remembers the tier it was
saving for). `--bosses <name>` plays a boss event instead of Warlords. A decent human should do better.

Latest runs (November 2026, after crosspathing, projectiles, the six new towers, immunities,
layered enemies, boss events and items). First the full run (3 games each, 179 s; it was about 98 s
with instant hits):

| | Easy | Normal | Hard |
|---|---|---|---|
| Meadow, 1 player | won 3/3, 3.0 evo | won 2/3, wave 27-30, 2.7 evo | won 0/3, wave 22-23 |
| Meadow, 2 players | won 2/3, wave 29-30, 1.3 evo | won 1/3, wave 15-30, 0.7 evo | won 0/3, wave 13-27 |
| Meadow, 4 players | won 0/3, wave 27-29 | won 0/3, wave 13-27 | won 0/3, wave 13-20 |
| Crossing, 1 player | won 3/3, 3.7 evo | won 2/3, wave 24-30, 2.7 evo | won 1/3, wave 20-30, 1.3 evo |
| Crossing, 2 players | won 2/3, wave 29-30, 1.3 evo | won 0/3, wave 24-27 | won 0/3, wave 16-27 |
| Crossing, 4 players | won 0/3, wave 27-29 | won 0/3, wave 15-24 | won 0/3, wave 14-15 |
| Coil, 1 player | won 3/3, 3.3 evo | won 2/3, wave 29-30, 2.7 evo | won 2/3, wave 29-30, 2.3 evo |
| Coil, 2 players | won 3/3, 2.0 evo | won 2/3, wave 29-30, 1.0 evo | won 0/3, wave 29-29 |
| Coil, 4 players | won 1/3, wave 29-30, 0.3 evo | won 1/3, wave 29-30 | won 0/3, wave 27-29 |
| Knot, 1 player | won 3/3, 4.0 evo | won 3/3, 4.0 evo | won 2/3, wave 24-30, 2.7 evo |
| Knot, 2 players | won 3/3, 1.7 evo | won 1/3, wave 19-30, 0.7 evo | won 0/3, wave 19-29 |
| Knot, 4 players | won 3/3, 0.7 evo | won 2/3, wave 29-30 | won 1/3, wave 24-30, 0.3 evo |
| Quarry, 1 player | won 3/3, 3.3 evo | won 2/3, wave 27-30, 2.0 evo | won 1/3, wave 14-30, 1.0 evo |
| Quarry, 2 players | won 2/3, wave 29-30, 1.3 evo | won 1/3, wave 27-30, 0.7 evo | won 0/3, wave 22-25 |
| Quarry, 4 players | won 0/3, wave 27-29 | won 0/3, wave 14-27 | won 0/3, wave 10-14 |

Waves 27-29 were the wall almost everywhere but Knot: two Juggernauts on 27, the Colossus on 29.
So Juggernauts went from 900 health, armour 4 and 6 lives to 550, 3 and 4 (one a wave until 33),
and the Colossus from 3,000 health and 15 lives to 1,500 and 10. Then a confirmation run, one game
each (64 s):

| | Easy | Normal | Hard |
|---|---|---|---|
| Meadow, 1 player | won 1/1, 3.0 evo | won 1/1, 3.0 evo | won 0/1, wave 24 |
| Meadow, 2 players | won 1/1, 2.0 evo | won 1/1, 2.0 evo | won 1/1 |
| Meadow, 4 players | won 1/1, 1.0 evo | won 0/1, wave 15 | won 0/1, wave 14 |
| Crossing, 1 player | won 1/1, 4.0 evo | won 1/1, 4.0 evo | won 1/1, 4.0 evo |
| Crossing, 2 players | won 1/1, 2.0 evo | won 0/1, wave 29 | won 1/1, 1.0 evo |
| Crossing, 4 players | won 1/1, 1.0 evo | won 0/1, wave 15 | won 0/1, wave 15 |
| Coil, 1 player | won 1/1, 3.0 evo | won 1/1, 3.0 evo | won 1/1, 3.0 evo |
| Coil, 2 players | won 1/1, 2.0 evo | won 1/1, 2.0 evo | won 1/1, 2.0 evo |
| Coil, 4 players | won 1/1, 1.0 evo | won 1/1 | won 1/1, 1.0 evo |
| Knot, 1 player | won 1/1, 4.0 evo | won 1/1, 4.0 evo | won 1/1, 4.0 evo |
| Knot, 2 players | won 1/1, 2.0 evo | won 0/1, wave 19 | won 0/1, wave 19 |
| Knot, 4 players | won 1/1 | won 1/1 | won 1/1, 1.0 evo |
| Quarry, 1 player | won 1/1, 4.0 evo | won 1/1, 4.0 evo | won 1/1, 4.0 evo |
| Quarry, 2 players | won 1/1, 2.0 evo | won 1/1, 1.0 evo | won 0/1, wave 22 |
| Quarry, 4 players | won 0/1, wave 29 | won 0/1, wave 14 | won 0/1, wave 10 |

The builders now win most games, hard included, so the game is easier than before these changes
for them: the new towers and crosspathing add more than the new enemies take away. Real players also
have items and gold to give. If it feels too easy, the levers are the blimps' health (`ENEMIES`) and
when they come (`_extras`), not tower numbers. Boss events, in a spot check (one game each, solo,
normal, before the last trim): the Gravewarden was won on every map; the Stormhulk and the Ironmaw
each took a game or two at wave 20. They were trimmed after that (Stormhulk 520 → 480 health,
Ironmaw 480 → 420 and a smaller shell).

The run before these (the earlier balance pass: hard's health ×1.3 → ×1.15, flyer waves cut to
`n(5)` flyers and slowed to 1.1 tiles a second, Gargoyles slowed to 0.8, final evolutions 30%
cheaper, and builders that save for one evolution at a time; 3 games each, `won`, the wave reached
if any were lost, and evolutions standing at the end per game; 98 s):

| | Easy | Normal | Hard |
|---|---|---|---|
| Meadow, 1 player | won 3/3, 2.7 evo | won 3/3, 2.7 evo | won 3/3, 2.0 evo |
| Meadow, 2 players | won 3/3, 0.7 evo | won 1/3, wave 24-30, 0.3 evo | won 0/3, wave 12-29 |
| Meadow, 4 players | won 3/3 | won 0/3, wave 12-19 | won 0/3, wave 10-12 |
| Crossing, 1 player | won 3/3, 2.7 evo | won 3/3, 2.0 evo | won 2/3, wave 26-30, 1.0 evo |
| Crossing, 2 players | won 3/3, 1.0 evo | won 1/3, wave 30-30, 0.7 evo | won 0/3, wave 16-30, 0.3 evo |
| Crossing, 4 players | won 3/3 | won 2/3, wave 30-30 | won 0/3, wave 11-16 |
| Coil, 1 player | won 3/3, 2.7 evo | won 2/3, wave 29-30, 1.0 evo | won 1/3, wave 24-30, 1.0 evo |
| Coil, 2 players | won 3/3, 1.3 evo | won 3/3 | won 3/3 |
| Coil, 4 players | won 3/3 | won 1/3, wave 29-30 | won 0/3, wave 21-24 |
| Knot, 1 player | won 3/3, 1.7 evo | won 1/3, wave 24-30 | won 0/3, wave 24-29 |
| Knot, 2 players | won 2/3, wave 29-30, 0.3 evo | won 2/3, wave 24-30 | won 1/3, wave 24-30 |
| Knot, 4 players | won 1/3, wave 29-30 | won 1/3, wave 24-30, 0.3 evo | won 1/3, wave 19-30 |
| Quarry, 1 player | won 3/3, 2.3 evo | won 3/3, 1.7 evo | won 1/3, wave 26-30, 0.7 evo |
| Quarry, 2 players | won 3/3, 1.0 evo | won 0/3, wave 16-26 | won 0/3, wave 15-16 |
| Quarry, 4 players | won 2/3, wave 30-30, 0.3 evo | won 0/3, wave 14-16 | won 0/3, wave 11-11 |

Solo and two-player games are now winnable almost everywhere on easy and normal; hard is won solo
on every map but Knot, and Coil and Knot are no longer the walls they were (Knot is still the
hardest). Games now see final evolutions (two or three per solo game) and their abilities.
What's left is the builders, not the maps: four builders, and two on Meadow and Quarry, still lose
by waves 10-20 with few towers standing. Each builder saves from its own quarter of the income for
its own next tower and nobody hands gold over, so less gets built early. Real players pool gold (the
Give button) and should do much better. If four-player games feel too hard in real play, the lever
is the starting gold per extra player (`START_GOLD` in data.py), not enemy health.

The run before (after targeting, abilities, the four new enemies, Knot and Quarry, and the smarter
builders):

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
  effects, the newer enemies, crosspathing, projectiles and pierce, immunities, layers, traps,
  sentries, boss events and their skulls, items, the new abilities, undo, endless, records, and
  saving and resuming (into a temporary database). In `check-all.sh`.
- `python3 tools/holdfast-sim.py --fast` (about 7 s): one game of each map, to see the fight runs. In
  `check-all.sh`. The full run is for changes to the numbers; run it once, at the end.
- `node tools/holdfast-smoke.js --serve` (about 50 s): two browsers, one phone-sized, build, undo,
  aim, pick a boss event, upgrade (the side path stays open), drop Caltrops, fight a wave, lose, read the end summary and see the record in the room. In `check-all.sh`; skipped where Playwright isn't installed.
  `--shots <folder>` saves screenshots.
- After changing its CSS or JS: `python3 tools/bump-version.py app/static/games/holdfast`.
