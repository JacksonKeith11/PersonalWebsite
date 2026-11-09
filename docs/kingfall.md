# Kingfall (planned: /games/kingfall)

**Status: plan only. Nothing is built yet.** "Kingfall" is a working title. This doc is the design
plan from the owner's answers (Nov 2026). When building starts, it becomes the area doc: keep "The
owner's design answers" as they are, and replace the plan sections with how the game actually works.

## What it is

A 2D top-down co-op **boss rush roguelite** for 1-4 players in the browser. Its influences are souls
games (readable but punishing bosses, stamina, poise, delayed swings, a healing flask), Hades
(top-down action, builds that grow across a run, upgrades that change how attacks behave) and Ember
Knights (co-op chaos, weapon variety). It is its own game: own setting, names, bosses and art. Don't
borrow any game's bosses, names, art or layouts.

**Setting: dark fantasy.** A fallen kingdom: knights who broke their oaths, cursed beasts, dead saints.
Each boss has its own ruined arena. A run climbs through them to the throne.

A run fights 7 bosses, with a level-up and upgrade screen (the **Bonfire**) after each one, and takes
40-60 minutes. Losing ends the run.

## The owner's design answers

Keep to these. They came from the owner directly.

- **Online plus couch.** Rooms by four-letter code, like Board Brawl and Saltbound, with each friend on
  their own computer. Extra controllers plugged into one browser join that same room as extra local
  players. 1-4 players in total. It must play well solo and with 2 or 3.
- **Top-down three-quarter view**, as in Hades and Ember Knights.
- **Art is drawn by code, at a much higher level than the other games.** It extends the Python
  pixel-art pipeline (`docs/game-art.md`) with bigger sprites, real multi-frame animation, lighting
  and effects. No bought or downloaded art.
- **Roguelite rush.** Each run draws its bosses from a larger pool, in tiers of rising difficulty,
  with upgrade picks between bosses.
- **Souls-hard.** Small health pools, heavy boss damage, few heals (a flask with limited charges).
  Reviving a downed teammate costs the reviver health.
- **Weapons:** pick one of six at the start. Each has a light attack, a heavy attack, a special and a
  defensive move. Upgrades change how they behave. Weapons can be swapped at certain Bonfires.
- **Upgrades are individual, XP is shared.** The party levels together. Each player picks from their
  own draw at the same time, so nobody waits on anyone. Coins are shared, for a shop.
- **Everything is unlocked from the first run.** Nothing carries over between runs. No bots in real
  games (bots are for automated testing only). No endless mode for now.
- **Stamina bar.** Dodging, heavy attacks, blocking and sprinting use stamina, which refills quickly
  when you stop.
- **Full launch:** build all 6 weapons, 12 bosses and about 80 upgrades before it's shown.
- **Controller and keyboard plus mouse**, both first-class, including every menu.

## Open questions (with the defaults the plan assumes)

These are smaller. The plan uses the default unless the owner says otherwise.

| Question | Default |
|---|---|
| The name | Kingfall (working title) |
| Friendly fire | Off |
| How attacks are telegraphed | Melee is read from the boss's animation (souls style). Big area attacks also mark the ground briefly (Hades style), so four players can read them through the clutter. |
| Lock-on | Optional: toggled with R3 or middle mouse. Aim snaps toward the locked target. |
| Difficulty presets | Normal (the souls-hard design), Hard (faster, meaner bosses), and a gentler Squire for casual nights. They change only numbers. |
| Solo safety net | One self-revive ("Second Wind") per run when solo, since nobody can revive you. Off on Hard. |
| Saving | A checkpoint at every Bonfire (SQLite), so a deploy or crash only loses the current fight. |

## Architecture

Saltbound's split applies: the server owns the run, and the browser sends what you're doing and draws.
Action combat changes how fights are timed, though, so fights borrow from Frag Arena's netcode.

- **Client:** Phaser 3.80.1 from cdnjs (as Saltbound), WebGL. No build step. The game is drawn at a
  low internal resolution (640x360, pixel-perfect) and scaled to the window. The UI (menus, Bonfire,
  HUD frames) is DOM over the canvas, as in Saltbound.
- **Server:** `app/kingfall/` plugs into `app/rooms.py` (`serve`, `Codes`, `push`). It runs a 30 Hz tick
  only during fights. It owns boss AI, boss and player HP, poise, XP, coins, upgrade draws, Bonfire
  checkpoints and run state. One uvicorn worker, as for the other games.

### Netcode: dodging has to feel exact over the tunnel

The tunnel adds tens of milliseconds, and a souls-style dodge lives or dies on a few frames. The plan:

1. **Your own movement is predicted** in the browser and reported at 30 Hz (Frag Arena's model). Other
   players are drawn 100 ms in the past, interpolated.
2. **Boss attacks are scheduled, deterministic timelines.** When the boss AI picks a move, the server
   sends `attack {move, start_at, origin, target ids and positions, seed}`, starting about 120 ms in
   the future. That's enough for every browser to get the message before the move begins. Every move
   is data: wind-up, active frames, hitboxes (circle, arc, rectangle, line, ring) attached to the
   timeline, the boss's scripted motion (lunges, leaps), and seeded projectile patterns. So each
   browser computes exactly where every hitbox is at any server time.
3. **The boss is drawn on the server clock, not delayed.** During a move its position comes from the
   timeline. Between moves (slow walking toward a target) it's extrapolated and gently corrected.
4. **Hits on you are decided by your browser** ("favour the dodger"). If your roll's invincibility
   covered the hitbox on your screen, you dodged. The browser reports `hurt {move, hit}`, and the
   server applies the damage after a loose check that the move was live then.
5. **Your hits on the boss are decided by your browser** against its view of the boss (on the server
   clock, so practically the same view everywhere). The server applies the damage and poise.

Like Frag Arena, this trusts the browsers, which is fine for friends. The move timelines are data in
`app/kingfall/content/`, served to the browser as JSON. The hitbox geometry exists in both languages
(the server needs it for bots and the balance sim), so a parity script like `tools/arena-parity.mjs`
keeps them in agreement.

### Couch co-op and input

- **One input layer, separate from what each input does.** Every player produces the same actions:
  move (vector), aim (vector), light, heavy, special, dodge, block/parry, heal, interact, lock-on.
- **Keyboard and mouse:** WASD to move, mouse to aim, left click light, right click heavy, Space
  dodge, Shift block, Q special, R heal (flask), E interact, Tab for the map and build. Rebindable.
- **Controller** (Gamepad API, standard mapping, Xbox and PlayStation glyphs): left stick to move,
  right stick to aim (when it's idle, aim follows movement with a soft aim assist toward the boss), RB
  light, RT heavy, B/Circle dodge, LB block, Y special, X heal, A interact, R3 lock-on. Rumble where
  the browser supports it.
- **Local players.** The keyboard and mouse are one player; each extra controller that presses Start
  joins as another local player. One socket carries all of a browser's local players. Each one is a
  separate player to the server.
- **The camera** frames that browser's local players and the boss, zooming out a little to fit them.
  Arenas are about 1.5 screens across, so the camera never has to choose between two people.
- **Every menu works with a controller:** a focus system with D-pad navigation, A to confirm, B to go
  back. During the Bonfire, each local player gets their own panel, side by side, couch style.
- None of the site's games read controllers yet. `games/shared/` would be the natural home for the
  gamepad layer, so other games can use it later.

## Combat core (souls-hard)

- **Health** is small: early bosses kill in 4-6 hits. A **flask** heals 40% over a slow,
  interruptible drink. It has 3 charges, refilled at each Bonfire, and upgrades can add more.
- **Stamina:** 100. A dodge costs 25, a heavy 30, and a blocked hit costs stamina in proportion to
  the damage. It refills after 0.6 s of not spending. At 0 you can't dodge, and a blocked hit breaks
  your guard.
- **Dodge roll:** 0.45 s, with invincibility from 0.05 to 0.35 s. Rolling through an attack is the
  core skill.
- **Poise.** Bosses have a poise bar that hits wear down. When it breaks, the boss **staggers**: a
  2-second window in which a heavy attack lands a big **critical**. The bar is shared, so co-op teams
  that focus together stagger more. Players have light poise: weapon heavies and some upgrades give
  hyper-armour.
- **Parry** (sword and shield, and some upgrades): a well-timed block deflects a parryable move and
  deals heavy poise damage.
- **Status buildup**, souls style: bleed, frost, burn and rot fill a meter on the target, then go off.
  Bosses resist each type more after every proc.
- **Downed:** at 0 HP you're down for 15 s. A teammate holds interact for 2 s next to you to revive
  you. That costs them 25% of their max HP, and you rise at 30%. The run ends when everyone is down.
- **Feel:** hitstop (40-80 ms by weight), screen shake, flashes, slash trails, knockback on
  lighter enemies, and a clear sound for every telegraph.

### Scaling for 1-4 players

- **Boss HP:** x1, x1.6, x2.15, x2.7 for 1 to 4 players. Poise scales at half that.
- **Aggro:** the boss targets by a mix of distance, recent damage and time since it last attacked each
  player, so it doesn't ignore anyone and doesn't chase the archer forever.
- **Co-op moves:** some moves target several players at once (a strike at each), tether two players,
  or punish a party that bunches up or spreads out. Their numbers scale with the party. Solo drops
  them or gives a simpler version.
- **Readability with four players:** each player has a coloured outline and ground ring, effects
  scale down when there are more players, and boss telegraphs always draw above player effects.

## Weapons (6)

Each has a light combo, a heavy (chargeable), a special (costs Focus, a meter that fills when you
deal damage) and its own defensive move. Each also has 4 **Arts**: weapon-specific upgrades that
reshape its moveset (like Hades' aspects, but found during the run).

| Weapon | Play | Light / Heavy / Special / Defensive |
|---|---|---|
| Sword & Shield | All-rounder, the teacher | 3-hit combo / rising slash / shield bash (high poise) / block, with a parry on timing and a riposte |
| Greatsword | Slow, heavy, poise-breaking | 2 wide swings / charged overhead with hyper-armour / leaping slam / the roll can chain into a heavy |
| Twin Daggers | Fast, bleed, mobile | 5-hit flurry / backstep cut / a blink that leaves a delayed cut / a short dash with 2 charges instead of a roll (cheaper stamina) |
| Halberd | Reach, crowd control, counters | thrust chain / 270° sweep / pole-vault over an attack / counter stance (absorb a hit, strike back) |
| Longbow | Ranged, positioning | quick shot / charged piercing shot / arrow rain on an area / roll-shot (fire as you roll) |
| Catalyst | Spells, Focus-hungry | bolt / channelled beam / a ward that blocks projectiles for allies / blink |

Balance target: no weapon is much better in a party of four than solo, and each one can solo every boss.

## The Bonfire (between bosses)

After each boss the party gets XP (shared), coins (shared) and an **Ember** (a pick token, each
player's own). The Bonfire screen has four panels that each player works through independently,
then they ready up:

1. **Level up.** Each level gives 1 attribute point: Vigor (HP), Endurance (stamina), Might (heavy and
   poise damage), Finesse (light and attack speed), Arcane (Focus and status buildup). Soft caps make
   spreading points sensible.
2. **Choose an upgrade.** 3 cards from your own draw (one free reroll per run, more from the shop).
3. **Shop** (shared coins, anyone can buy): flask charges, rerolls, a heal, removing an upgrade,
   rarity upgrades.
4. **Weapon shrine** (every second Bonfire): swap your weapon. You keep your general upgrades and lose
   your weapon Arts.

### Upgrades (~80)

Hades' structure suits builds: most upgrades attach to **one slot** (light, heavy, special, dodge,
defensive), so each slot holds one, and picking means choosing. They come from six **Vows**, each
with its own theme, colour and status:

| Vow | Theme | Example |
|---|---|---|
| Ember | burn, explosions | Light attacks build burn; a burning enemy you stagger explodes |
| Rime | frost, slowing | Your dodge leaves an ice trail that freezes boss feet |
| Blood | bleed, lifesteal, risk | Heavy attacks heal you on hit while you're below 50% HP |
| Storm | chains, speed | Every third light hit chains lightning to the boss's adds |
| Rot | poison, curses | The special leaves a rot pool; poisoned bosses lose poise faster |
| Iron | poise, guard, armour | A perfect dodge restores 30 stamina and grants hyper-armour |

- **Passives** (no slot): stat boosts and odd ones such as "Your flask also heals allies within 3 m".
- **Pacts**: co-op upgrades, which only appear with 2+ players. "Revives cost you no HP and give the
  revived ally a shield", "When an ally parries, your next hit crits", "Bound souls: you and the ally
  nearest you share damage taken".
- **Duos**: one appears in the draw once you hold upgrades from two Vows that combine (Ember and Storm
  make "Wildfire": lightning sets things alight).
- **Rarity:** common, rare, epic. Higher rarity is the same effect with bigger numbers.

## Bosses (12)

A run draws 2 from tier 1, 2 from tier 2, 2 from tier 3, then one of the two finals.

**Rules every boss follows:**
- 6-10 moves and 2 phases (finals have 3). The second phase changes the moveset, not just the speed.
- Every move has a tell you can read: an animation wind-up of at least 0.4 s on Normal, its own sound,
  and a ground mark for area attacks.
- Every move has an answer (roll through it, outrange it, block it, get behind it) and an opening to
  punish afterwards.
- At least one **delayed or feinting** attack per boss (the souls rhythm-breaker), and at least one move
  that cares about how the party is placed.
- Each boss teaches something; later tiers combine those lessons.

| Tier | Boss | Arena | The idea, and its key moves |
|---|---|---|---|
| 1 | **Ser Corvin, the Oathless** | A collapsed chapel | A fallen knight with a sword and tower shield. 3-hit combo, shield charge, delayed overhead, lunge. His shield blocks hits from the front, so flank him (teaches positioning). Phase 2: the blade ignites and every swing leaves a fire trail. |
| 1 | **The Mire Mother** | A drowned bog | A giant toad. Tongue lash (a line), belly-flop leap (its shadow marks the landing), spits poison pools that shrink the safe ground, spawns tadpoles. Phase 2: she submerges and erupts under a player. |
| 1 | **The Bellwarden** | A cathedral belfry | A hunched ghoul carrying a great bell. Each toll sends out rings of sound with gaps to roll through, a bell slam, a sweep. Phase 2: a toll silences specials for 5 s and summons a ghost choir. |
| 2 | **The Twin Headsmen** | The execution yard | A duo: a fast one with a hooked chain who pulls players in, and a slow giant with an axe. When one falls, the other absorbs their power and gains their key move. In co-op, the party has to split. |
| 2 | **The Briar Wolf** | A thorn forest | Fast pounces, circling and feints, bleed. A howl raises briar walls that divide the arena (and the party). Phase 2: the arena goes dark, and only its eyes and a glint before each strike show. |
| 2 | **The Ashen Alchemist** | A ruined laboratory | A mage on stilts throwing flasks with landing circles, in three colours (fire pools, freezing mist, poison). Mixing them makes combinations. Glass clones; in phase 2 the floor tiles change. |
| 2 | **The Gravewyrm** | A boneyard | A burrowing serpent of bone. Its burrow lines show under the ground; it bursts out, sweeps its tail, and coils to trap players. The glowing segments are its weak points. |
| 3 | **The Mirror Knight** | A hall of glass | Copies the party: it summons a reflection of each player, using that player's own weapon moveset, and then fights with their moves itself. Every party meets a different fight. |
| 3 | **The Bastion** | A siege wall | A giant siege golem. Rocket fist, a sweeping beam from its eye (hide behind pillars, which crumble), stomp quakes. Break the cores on its limbs to topple it for a big critical. |
| 3 | **The Moth Saint** | A candlelit sanctum | Bullet-hell patterns of glowing dust, pillars of light, wings that blind (darkening the screen around you). Snuffing the candles weakens her, but darkens the room. |
| Final | **The Hollow King** | The throne room | Three phases: an elegant duellist king; then a corrupted giant tearing the room apart; then the roof gone, the sky falling and every lesson at once. |
| Final | **The Eclipse Drake** | The broken sky-bridge | Flies over the arena (its shadow marks breath sweeps and dives), lands to fight with its head, claws and tail, and sets the arena on fire, shrinking it in phase 3. |

Each boss gets its own section in this doc (or its own doc, as Saltbound's classes have), covering its
moves with frame timings, its phase changes, how it scales and its art notes.

## Art plan

The biggest piece of work in the project. It extends `docs/game-art.md`: the same matte, cel-shaded,
muted palette with dark outlines and glowing accents. The owner picks looks from options, as was done
for Roguelike Tactics' heroes.

- **Sizes:** heroes in 48x48 frames (about 34 px tall), ordinary adds 32-48 px, bosses 96-256 px.
  Drawn at 640x360 and scaled 3x on a 1080p screen.
- **Hero rig:** a body drawn in layered parts (head, torso, arms, legs, cape) with pivots, plus a
  **separate weapon layer**, so all six weapons share one body and every look works with every weapon.
  Three facings (down, up, side, with left mirrored from right; diagonals use the nearest).
- **Animation:** Python poses the parts frame by frame from keyframes (rotations done on an upscaled grid
  and cleaned back to pixels, so arms don't break up). Per hero: idle 4, run 8, roll 6, hurt 2, downed,
  revive, drink, plus each weapon's light combo, heavy, special and defence (4-8 frames each). Bosses:
  idle, move and 6-10 attack animations each, with a clear wind-up frame held for the tell.
- **Output:** PNG atlases plus JSON frame data, not JS arrays: the size would be far beyond
  Saltbound's 190 KB `sprites.js`. They're generated by `tools/kingfall-art/build.py` and committed;
  never hand-edited.
- **Four hero looks** in each player's colour (cloth and plume take the player colour), chosen by the
  owner from options: a knight, a hooded pilgrim, a witch hunter and a sellsword.
- **Arenas:** one per boss, made of tiles with props and hazards, in layers so things can stand in front
  and behind. Each one comes in a dark-fantasy palette with its own accent (chapel gold, bog green,
  belfry violet).
- **Light and effects:** Phaser's Light2D pipeline with normal maps (Python can make these from the
  layer depths) for torchlit arenas, and additive glow sprites for magic. Effects are particles plus
  drawn slash arcs. Telegraph marks have a single shared look.
- **Audio:** synthesized with Web Audio like the other games: hits, rolls and a distinct sound per
  telegraph. Music is a theme per boss (as Saltbound did per region), with a second phase that builds on it.

## Code layout (planned)

| Path | Holds |
|---|---|
| `app/kingfall/routes.py` | The page and the WebSocket, through `app/rooms.py` |
| `app/kingfall/room.py` | Lobby, local players, ready-ups, run flow, Bonfire checkpoints (SQLite, versioned like Saltbound's saves) |
| `app/kingfall/fight.py` | The 30 Hz fight tick: boss AI, scheduling moves, damage, poise, downed and revive |
| `app/kingfall/geom.py` | Hitbox shapes and move timelines (twin of `js/moves.js`) |
| `app/kingfall/content/` | Bosses' moves (data), weapons, upgrades, Vows, tuning |
| `app/kingfall/bot.py` | Test bots that read the move data to dodge, for the balance sim only |
| `app/static/games/kingfall/js/` | `input.js` (keyboard, mouse, gamepads), `net.js`, `moves.js`, `player.js`, `boss.js`, `fight.js` (Phaser scene), `fx.js`, `bonfire.js`, `ui.js`, `audio.js` |
| `app/static/games/shared/gamepad.js` | The controller layer, shared so other games can use it later |
| `tools/kingfall-art/` | The Python art pipeline (rigs, poses, atlases, normal maps) |
| `tools/kingfall-check.py`, `kingfall-parity.mjs`, `kingfall-sim.py`, `kingfall-smoke.js` | The fast checks, geometry parity, the bot balance sim, a two-browser smoke test |

## Testing

- **Fast checks** (added to `tools/check-all.sh`): every move's data is valid (tells at least 0.4 s,
  hitboxes in the arena, an end to every phase), geometry parity between Python and JS, every upgrade
  resolves, and a short bot fight per boss finishes without error.
- **Balance sim:** bots of varying skill (reaction time, dodge accuracy) run whole runs per weapon and
  party size, and report win rate, deaths per boss and fight length. Targets: Normal at about 30-40% for
  skilled bots, no boss with more than twice the average deaths, and fights of 2-4 minutes. Run it
  sparingly, per CLAUDE.md.
- **Browser smoke test:** two headless browsers in one room, with controller input faked by
  stubbing `navigator.getGamepads`.
- **Feel needs a human.** Dodge windows, hitstop and controller aim get checked by the owner in a real
  browser at each stage below.

## Build order

The owner chose a full launch: the game isn't listed on `/games` until all of this is done. It's still
built in stages, each ending with something the owner can play at an unlisted URL:

1. **Feel prototype:** one hero with placeholder art and the sword, one boss (Ser Corvin), offline,
   keyboard and controller. *Owner check: does dodging and fighting feel right?*
2. **Netcode and rooms:** online play, couch local players, downed and revive, scaling for 1-4.
   *Owner check: play it with friends over the tunnel.*
3. **Art pipeline:** the hero rig, animation and atlases, the four hero looks (owner picks from
   options), the first arena, Light2D.
4. **All six weapons** with their Arts.
5. **The Bonfire:** levels, attributes, Vows, upgrades, the shop, the weapon shrine, checkpoints.
6. **Bosses in batches:** tier 1 (3), tier 2 (4), tier 3 (3), the finals (2). Owner review after each
   batch.
7. **Balance, audio and music, polish,** a page on `/games`, and listing it on the projects page.

## Risks

- **The amount of art** is the biggest risk: 12 animated bosses at 96-256 px. The part rigs are what
  keep it possible. The prototype should prove the pipeline on one boss before the rest are designed in
  detail.
- **Dodge feel over the tunnel.** The scheduled-move model should make it exact, but this is the first
  thing to test with real latency (stage 2).
- **Clutter with four players.** Coloured outlines, effects that scale down with more players, and
  telegraphs drawn on top of everything.
- **Phaser performance** with four players, a large boss, lights and particles on modest laptops: keep
  a particle budget and test early.
- **Controller-friendly DOM menus** are new to the site. Build the focus system once, in the shared
  gamepad layer.
