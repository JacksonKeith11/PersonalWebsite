# Kingfall (/games/kingfall)

Read this before changing anything in `app/kingfall/`, `app/static/games/kingfall/`, `tools/kingfall-*`
or `tools/kingfall-art/`.

**Status: built.** All twelve bosses, six weapons, 95 upgrades, the Bonfire, saves, difficulty and music
are in. The first half of this doc is what the owner decided; "How it plays now" is the game as it is.
When a change alters how the game works, update "How it plays now" (not a new section at the end) in
the same commit.

## What it is

A 2D top-down co-op **boss rush roguelite** for 1-4 players in the browser. Its influences are souls
games (readable but punishing bosses, stamina, poise, delayed swings, a healing flask), Hades (top-down
action, builds that grow across a run, upgrades that change how attacks behave) and Ember Knights (co-op
chaos, weapon variety). It is its own game: own setting, names, bosses and art. Don't borrow any game's
bosses, names, art or layouts.

**Setting: dark fantasy.** A fallen kingdom: knights who broke their oaths, cursed beasts, dead saints.
Each boss has its own ruined arena. A run fights 7 bosses with a Bonfire after each, 40-60 minutes;
losing ends it.

## The owner's design answers

Keep to these. They came from the owner directly.

- **Online plus couch.** Rooms by four-letter code, each friend on their own computer; extra controllers
  plugged into one browser join that room as extra local players. 1-4 players in total, and it must play
  well solo and with 2 or 3.
- **Top-down three-quarter view**, as in Hades and Ember Knights.
- **Art drawn by code**, bigger and more detailed than the other games (heroes about 48 px tall, bosses
  about twice that), with real animation, lighting and effects. No bought or downloaded art. The owner
  picks each character's look from options and approves every boss's sprite.
- **Roguelite rush**: bosses drawn from a pool in tiers of rising difficulty, upgrades between them.
- **Souls-hard.** Small health pools, heavy boss damage, a flask with few charges. Reviving a downed
  teammate costs the reviver health.
- **Six weapons**, each with a light combo, a charged heavy, a special and its own defensive move;
  upgrades change how they behave; a weapon shrine at some Bonfires lets you swap.
- **Upgrades are individual, XP is shared.** Everyone picks at once from their own draw; coins are shared.
- **Everything is unlocked from the first run.** No progress between runs; no bots in real games (they're
  for testing); no endless mode for now.
- **Stamina** for rolling, heavy attacks and blocking.
- **Full launch:** everything built before it's listed.
- **Controller and keyboard plus mouse**, both first-class, including every menu.
- Defaults the owner accepted: no friendly fire; melee read from animation while area attacks also mark
  the ground; optional lock-on; difficulty presets that change only numbers; one Second Wind a run when
  solo; a checkpoint at every Bonfire.

## How it plays now

### A run

The host makes a room; friends join by code, couch players press Start on a controller. Each hero picks a
look (knight, pilgrim, witch hunter, sellsword; tinted in their player colour) and a weapon. The host picks
the difficulty (Squire, Knight, Hard) and begins, or resumes a saved run.

A run draws two bosses from each tier, then a final (`POOLS`, `TIERS` in `room.py`):

| Tier | Bosses |
|---|---|
| 1 | Ser Corvin, the Oathless · the Mire Mother · the Bellwarden |
| 2 | the Twin Headsmen · the Briar Wolf · the Ashen Alchemist · the Gravewyrm |
| 3 | the Mirror Knight · the Bastion · the Moth Saint |
| Final | the Hollow King · the Eclipse Drake |

After each win: everyone heals and refills flasks, gains a level (one attribute point), one upgrade pick
from three cards, and the party gets shared coins (60 + 40 x tier). The shop sells rerolls (30), an
extra flask (120, +60 each time) and an extra blessing (150). The weapon shrine is lit at the Bonfires
after fights 2 and 4 (changing weapon drops that weapon's Arts). The next fight starts when everyone is
ready. The run is saved at every Bonfire (`save.py`, `data/kingfall.db`) and the save deleted when the
run ends.

### Combat

- **Heroes** (`HERO` in `content/__init__.py`): 100 health, 100 stamina (refills 0.6 s after spending),
  92 px/s. Roll: 0.42 s, 74 px, invulnerable 0.03-0.32 s, 25 stamina. Flask: 3 charges, heals 45% after
  0.75 s of a 1 s drink, spilled if hit. Downed: 15 s to be revived (hold interact 2 s next to them; costs
  the reviver 25% of their health; they rise at 30%). Solo heroes get one Second Wind a run (not on Hard).
- **Poise.** Every hit wears a boss's poise; at zero it staggers for 2.6 s, and a heavy or special during
  a stagger is a **critical** (x3) that ends it. Poise refills after 3 s without poise damage.
- **Statuses** on bosses: Burn and Bleed burst for damage, Frost slows the boss and breaks poise, Rot
  poisons over 5 s. Each meter needs 100 x 1.4^(bursts so far).
- **Boss health** scales x1, x2, x3, x4 with party size; poise x1, x1.4, x1.8, x2.2. Bosses pick their
  target by distance, recent damage and how long since they last went for each hero. Solo, they rest
  longer between moves; two-bodied bosses rest longer still.
- **Difficulty** (`DIFFS` in `room.py`): Squire 0.75 health, 0.7 damage, 0.9 speed; Knight as designed;
  Hard 1.15 health, 1.25 damage, 1.12 speed, no Second Wind.

### Weapons (`content/weapons.py`)

| Weapon | Light | Heavy (hold) | Special (Focus) | Defensive |
|---|---|---|---|---|
| Sword & Shield | 3-hit combo | rising slash | Shield Bash | block, parry in the first 0.18 s |
| Greatsword | 2 wide swings | overhead with hyper-armour | Leaping Slam (airborne) | block that lets 30% through |
| Twin Daggers | 5-hit flurry | backstep cut | Shadowstep (blink and cut) | a dash with 2 charges instead of a roll |
| Halberd | thrusts, a sweep | 270° sweep | Pole Vault (airborne) | counter stance: a hit taken is absorbed and answered |
| Longbow | arrows, a 3-arrow volley | charged piercing shot | Arrow Rain where you aim | roll-shot: the roll looses an arrow |
| Catalyst | bolts, a 3-bolt fan | charged orb that explodes | Nova round you | blink instead of a roll |

Focus fills as you deal damage. Each weapon has four Arts (weapon-only upgrades).

### Upgrades (`content/upgrades.py`, applied in `build.py`)

95 in all: six Vows (Ember, Rime, Blood, Storm, Rot, Iron) of nine each (one per slot: light, heavy,
special, dodge, guard; and four passives), five plain passives, six Pacts (only offered to parties of two
or more), six Duos (offered once you hold both Vows), and 24 Weapon Arts. A slot holds one upgrade; taking
another replaces it. Rarity (common, rare x1.5, epic x2) scales the numbers. Offers lean toward Vows you
already follow. Attributes: Vigor +12 health; Endurance +10 stamina and quicker recovery; Might +7% heavy
and special damage and +8% poise damage; Finesse +6% light damage; Arcane +12% status buildup and +8%
special damage.

### The bosses

Every boss has 5-7 moves and a second phase (the finals have three) whose transition is an invulnerable
roar with a shockwave. Every move has a readable wind-up (and a distinct sound); area attacks mark the
ground first.

| Boss | What it does |
|---|---|
| Ser Corvin | 3-hit combo that re-aims each swing, shield charge, delayed overhead, lunge, guard stance (front hits glance off). Phase 2: a fourth burning slam with a spreading ring; fire waves. |
| Mire Mother | tongue lash that pulls you in, belly-flop leap (lands where its shadow is), poison pools, slap, tadpoles. Phase 2: submerges and erupts under you; double flop. |
| Bellwarden | tolls send rings with gaps at the sides (sound can't be blocked), rakes, bell-slam, lurch, ghost choir. Phase 2: three tolls with different gaps; drags the bell round. |
| Twin Headsmen | two bodies: the Hook (chain pull, flurry, chain whirl, dash) and the Axe (execution, sweep, stomp, charge). When one falls the other roars, heals a quarter and learns the other's signature. |
| Briar Wolf | pounces, a feint that hops back then pounces, bites, tail lash, howl raising a wall of thorns. Phase 2: the clearing goes dark; double pounces. |
| Ashen Alchemist | keeps its distance; lobbed fire flasks, three-colour volleys, stilt stamp, vaults away leaving poison, homunculi. Phase 2: transmutes the floor; the great mixture; burning spray. |
| Gravewyrm | burrows and erupts under you, lunging bite, bone shards, thrash, a ring that closes in. Its vertebrae can be struck too. Phase 2: burrows twice. |
| Mirror Knight | the heroes' own combo, glide, shard fan, a parrying stance, glass reflections. Phase 2: shards rain in marked circles. |
| Bastion | rocket fist, stomp, a sweeping furnace beam, two-fist hammer. Armoured (half damage) until both knee cores and the back core are broken; then it topples for 7 s. Phase 2: two fists, the beam both ways. |
| Moth Saint | hovers at range; dust spirals, pillars of light, wing gust, dust streams, mothlings. Phase 2: snuffs the candles (darkness); double spirals. |
| Hollow King | phase 1 a duellist (lunges, a four-cut flourish, riposte stance, backstep); phase 2 swells into the hollow giant (cleave, leaping crash, sweeps, void bolts, pools of void); phase 3 the sky falls. |
| Eclipse Drake | fire breath that sweeps and leaves the bridge burning, claws, tail, wing gust. Phase 2: dives along the bridge and rains fire from the air. Phase 3: the bridge's edges burn for the rest of the fight. |

### Netcode

- **Your heroes are predicted**: the browser moves them and reports position, aim and animation 20
  times a second. Other heroes are drawn 100 ms in the past, interpolated.
- **Boss moves are announced, then played on the server clock.** The server picks a move and sends `mv`
  (`seq`, body `e`, `id`, start time `at` 0.14 s ahead, origin, aim, resolved step lengths) before it
  starts; at each of the move's `locks` it re-aims and sends `aim`; a stagger or phase change sends
  `cancel`. Every browser computes the boss's position and every hit's shape from the same data at the
  same server time (`js/moves.js`, `app/kingfall/content/moves.py`), so the dodger decides: a hit only
  lands if it touched your hero on your screen while you weren't invulnerable.
- **The browser reports both directions**: `hurt` (with block/parry/counter) and `hit` / `hitadd` (with
  the attack, combo index, charge, swing number, body and weak point). The server dedupes, works out every
  number (weapon base x attack x build x crits x statuses x armour) and broadcasts `fx` events.
- This trusts the browsers, fine for friends. Don't make it competitive without moving checks to the server.

### Art

- Parts, not frames: each character is cutout parts drawn by Python (`tools/kingfall-art/`), posed by
  rotating them around pivots. `rigs.py` holds every rig (parent, rest position) and is copied into
  `atlas.json`; `js/rig.js` poses them the same way. Everything faces right; facing left flips.
- Heroes: `heroes.py` (the owner's four picks, redrawn at 48 px). Weapons: `weapons.py`. Bosses: `bosses.py`
  (Corvin), `tier1.py`, `tier2.py`, `tier3.py`; adds: `adds.py`. All approved by the owner.
- Moves animate from keyframes in the content files (`anim`: `(t, pose)`); a pose names part angles plus
  `lean`, `dy`, `z` (height: leaps, flight), `front` (shield/bell in front) and `run` (legs cycle).
- Arenas are drawn in the browser on a canvas (`js/arena.js` for the chapel, `js/arenas.js` for the rest).
- Music (`js/music.js`) and sounds (`js/audio.js`) are synthesized as they play.

## Code map

| File | Holds |
|---|---|
| `app/kingfall/routes.py` | The page and the WebSocket (through `app/rooms.py`) |
| `app/kingfall/room.py` | Rooms, couch heroes per browser, the lobby, the run, the Bonfire, difficulty, checkpoints, the 30 Hz loop |
| `app/kingfall/fight.py` | One fight: bodies, moves, AI, damage, poise, statuses, adds, cores, downed and revive |
| `app/kingfall/build.py` | A hero's attributes and upgrades folded into numbers (`Build`); `client()` is what the browser needs |
| `app/kingfall/geom.py` | Hit shapes in Python (for the sim; twin of `js/moves.js`) |
| `app/kingfall/save.py` | Saved runs in SQLite |
| `app/kingfall/content/` | `moves.py` (shape builders, motion), one file per boss, `weapons.py`, `upgrades.py`, `__init__.py` (hero numbers, scaling, what the browser gets) |
| `app/static/games/kingfall/js/main.js` | Boot (Phaser at a whole-number zoom), menus, lobby, Bonfire, the connection |
| `js/input.js` | Keyboard/mouse and up to four gamepads as one set of actions |
| `js/fight.js` | The fight scene: arena, lights, darkness, heroes, boss, hit checks, effects, camera |
| `js/hero.js` | Local heroes (every weapon's behaviour), remote heroes, poses |
| `js/boss.js` | Boss bodies, adds, the wyrm's trail, danger drawing, hit checks against heroes |
| `js/moves.js`, `js/rig.js`, `js/ui.js`, `js/net.js`, `js/audio.js`, `js/music.js`, `js/arena.js`, `js/arenas.js` | As named |
| `art/atlas.png`, `art/atlas.json` | Generated by `python3 tools/kingfall-art/build.py`; never edit by hand |

## Testing

- `tools/check-all.sh` runs `node tools/kingfall-parity.mjs` (the JS and Python move maths agree on every
  move of every boss) and `python3 tools/kingfall-sim.py --fast`.
- **The balance sim** (`tools/kingfall-sim.py`): bot parties fight on the real server code in simulated
  time. Bots see hits coming and roll with probability `skill`, step out of pools, fight adds, break
  cores, drink and revive; they get the levels and random blessings a run gives before that boss's tier.
  `python3 tools/kingfall-sim.py "" 10 --skill 0.85` runs every boss at every party size in about a minute.
  Bots never block, parry or use specials, and are poor at rings and slow projectiles, so treat their
  numbers as a rough guide. Latest (Nov 2026, skill 0.85, win % solo / 2 / 3 / 4): Corvin 40/70/100/100,
  Mire 90/100/100/100, Bellwarden 50/0/50/90, Headsmen 40/40/60/70, Wolf 80/90/90/100, Alchemist
  10/30/80/100, Wyrm 100/80/90/100 (after a damage buff), Mirror 20/80/100/100, Bastion 30/10/60/70, Moth
  50/50/80/80, King 10/60/90/90, Drake 100/60/30/90.
- `?debug&boss=mire` on the page: a debug room that starts at that boss; `window.kf.win()` wins the fight.
- `python3 tools/kingfall-art/anim.py <boss|weapon> <move> out.png` draws a move's keyframes as a strip;
  `sheet.py` reviews bosses beside a hero at game size; `preview.py` the heroes.

## Gotchas

- **The two halves of the move maths must agree.** After changing `js/moves.js`, `geom.py` or
  `content/moves.py` (or adding a shape kind), run `node tools/kingfall-parity.mjs`.
- **The server never clamps a move's motion after the fact**: browsers draw it as sent. `Fight.fit`
  shortens steps so a move can't carry the boss through a wall; a move whose steps come after a lock is
  only shortened from that lock on (or the boss would jump on screen).
- **Hit ids**: `seq:i` for a move's hit, `seq:i:n` for a pool's nth tick, `a<id>:<n>` for an add's bite
  (every 2 s, not in its first second). The server keeps the last 12 finished moves for late reports and
  lingering pools; a pool that outlives that won't hurt.
- **Parts**: a rig only gets images for frames that exist in the atlas, so an optional part (a shield) can
  simply be missing. A new boss needs its rig in `tools/kingfall-art/bosses.py` (`RIGS`, `BOSSES`,
  `BOSS_RIG`), then `build.py`, then a content file registered in `content/__init__.py` and `POOLS`.
- **Cache versions**: `python3 tools/bump-version.py app/static/games/kingfall` after changing its JS or
  CSS. The atlas is loaded with the page's version, so a rebuilt atlas also needs a bump.
- The fight lives in one process's memory; a deploy drops it (the run resumes from the last Bonfire).
