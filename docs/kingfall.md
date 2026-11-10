# Kingfall (/games/kingfall)

Read this before changing anything in `app/kingfall/`, `app/static/games/kingfall/`, `tools/kingfall-*`
or `tools/kingfall-art/`.

**Status: built.** All twelve bosses, six weapons, twelve skills, 100 upgrades, the Bonfire, saves, difficulty and music
are in. The first half of this doc is what the owner decided; "How it plays now" is the game as it is.
When a change alters how the game works, update "How it plays now" (not a new section at the end) in
the same commit.

## What it is

A 2D top-down co-op **boss rush roguelite** for 1-4 players in the browser. Its influences are souls
games (readable but punishing bosses, poise, delayed swings, a healing flask), Hades (top-down
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
  upgrades change how they behave. (There was a weapon shrine at some Bonfires; the owner had it
  removed in Nov 2026: a run keeps the weapon it started with.)
- **Upgrades are individual, XP is shared.** Everyone picks at once from their own draw; coins are shared.
- **Everything is unlocked from the first run.** No progress between runs; no bots in real games (they're
  for testing); no endless mode for now.
- **No stamina** (Nov 2026; it was there at first, for rolls, heavies and blocks): instead each hero has a
  number of dashes that come back at a rate, both depending on the weapon.
- **Heroes' areas and bosses' areas must look different** (Nov 2026), and a hero must be able to hover
  over a blessing they hold and read what it does.
- **Full launch:** everything built before it's listed.
- **Controller and keyboard plus mouse**, both first-class, including every menu.
- Defaults the owner accepted: no friendly fire; optional lock-on; difficulty presets that change only
  numbers; one Second Wind a run when solo; a checkpoint at every Bonfire.
- **Clear hits both ways** (Nov 2026, after watching bots play): clear animations and visible hitboxes
  for heroes and bosses; every player attack shows exactly where it hits; bosses switch targets to the
  archers and casters at the back; every boss has ranged attacks and attacks whose areas you must keep
  out of. (This replaced the earlier default of reading melee from animation alone.)

- **Weapons must be seen to swing** (Nov 2026): sword and staff attacks show the weapon really swinging
  outward, never held awkwardly or thrust into the hero's own body.
- **Skills** (Nov 2026): abilities on cooldowns, shared across all weapons, chosen after each fight; a
  hero carries at most two and swaps one out when over the limit.

- **Feel and HUD** (Nov 2026, after the owner played): flasks left and cooldowns shown somewhere obvious,
  at the bottom left, each player seeing only their own unless they share a screen; heroes move faster
  with a smoother roll they can steer; every weapon has a light combo that repeats while the button is
  held, as in Hades; boss attacks have sounds; the loadout can be changed in the lobby after a defeat.

- **Blessings** (Nov 2026): one a hero's weapon can't use is never offered (no block upgrades for the
  daggers); blessings should change how attacks play or add effects, not hand out flat stat bonuses.

## How it plays now

### A run

The host makes a room; friends join by code. Every hero on a browser is driven by its own devices
(`heroOf` in `js/main.js`):
- **Player one** (made with the room, slot 0) is the keyboard and mouse, plus player one's controller
  (`S.p1pad`): the first controller used (any button or the stick) that has no hero of its own, while player
  one has none. In a fight whichever of the two was used last drives it (`pickDevices` in `js/fight.js`;
  the HUD's key hints follow).
- **Couch players**: any further controller presses Start for a hero of its own (slot = controller + 1).
  "Split off" on player one's row gives player one's controller its own hero instead.
- Unplugging player one's controller frees it; the next controller used takes its place.

Each hero picks a
look (knight, pilgrim, witch hunter, sellsword; tinted in their player colour) and a weapon. The host picks
the difficulty (Squire, Knight, Hard) and begins, or resumes a saved run. When a run ends (lost or won) the room
returns to the same lobby screen (`state` "over"), where everyone can change look, weapon and starting skill, join or
leave before the host fights again.

A run draws two bosses from each tier, then a final (`POOLS`, `TIERS` in `room.py`):

| Tier | Bosses |
|---|---|
| 1 | Ser Corvin, the Oathless · the Mire Mother · the Bellwarden |
| 2 | the Twin Headsmen · the Briar Wolf · the Ashen Alchemist · the Gravewyrm |
| 3 | the Mirror Knight · the Bastion · the Moth Saint |
| Final | the Hollow King · the Eclipse Drake |

After each win: everyone heals and refills flasks, gains a level (one attribute point), one upgrade pick
from three cards, the offer of a skill (below), and the party gets shared coins (60 + 40 x tier). The shop sells rerolls (30), a redraw of the skills on offer (30), an
extra flask (120, +60 each time) and an extra blessing (150). Each blessing and skill a hero already holds is a chip in their panel: hovering it (or moving a
controller's focus onto it) shows a tooltip with what it does (`showTip` in `js/ui.js`, any element with `data-tip`). The next fight starts when everyone is
ready. The run is saved at every Bonfire (`save.py`, `data/kingfall.db`) and the save deleted when the
run ends.

### The menu during a run (`runMenu` in `js/main.js`, `openMenu` in `js/ui.js`)

Esc (Start on a controller) over a fight or the Bonfire: sound and music volume, "Quit the run" (the
host only, after a question: message `quit`, `Room.quit_run`; everyone returns to the lobby with
`result` "quit", and the save from the last Bonfire is kept so the run can be resumed) and "Leave the
room". Esc, B or Start closes it. The fight does not pause (the server runs it); while the menu is up
this browser's heroes stand idle. The menu is an overlay (`#menu`) over `#ui`: it takes the controller's
focus, and `show()` can still redraw the Bonfire beneath it.

In the lobby, a "◀ name ▶" picker (look, weapon, starting skill) goes back when clicked on its left half
and on when clicked on its right (`side` in `js/main.js`). The three pickers are equal, fixed-size cells on one
row; a long name is cut short with "…" rather than resizing or wrapping (buttons never wrap their text).

**Menu cursors.** Each couch player steers their own menu cursor, drawn in their player colour
(`setOwners` and `reach` in `js/ui.js`). The `main` cursor (keyboard, mouse, player one's controller and any
controller without a hero) reaches shared elements (no `data-owner`: Begin, difficulty, Leave) and player
one's box; a couch cursor reaches only its own box (the lobby row or Bonfire panel marked
`data-owner="<hero id>"`). Only `main` presses `data-back`, so a couch player's B can't leave the room. While
the Esc menu is up, every device steers the one cursor in it.

A redraw puts every cursor back on the element it was on (`keyOf` in `js/ui.js`), and a mouse click moves the
main cursor. Gotcha: the lobby appends its hero rows after `show()` returns, so `show()` looks again in a
microtask; without that every lobby update put the focus back on Begin.

### Combat

- **Heroes** (`HERO` in `content/__init__.py`): 100 health, 116 px/s. Roll: 0.38 s, 92 px,
  invulnerable 0.02-0.29 s; it starts at 1.5x its average
  speed and eases down to half (about a run), bends toward the stick at 200 degrees a second, and a light,
  heavy or roll pressed during it happens the moment it ends. A roll also cuts short the recovery of a
  heavy or special once it has struck. Flask: 3 charges, heals 45% after
  0.75 s of a 1 s drink, spilled if hit. Downed: 15 s to be revived (hold interact 2 s next to them; costs
  the reviver 25% of their health; they rise at 30%). Solo heroes get one Second Wind a run (not on Hard).
- **Dashes, not stamina** (`dodge` on each weapon; `useDash` in `js/hero.js`). A roll, the daggers' dash
  or the catalyst's blink spends one dash; so does blocking a hit (the guard's `cost`: with none left
  the guard breaks and the hit lands) and taking the halberd's counter stance. A parry spends nothing.
  Attacks, heavies included, are free. Dashes refill one after another; a part-filled one can't be used.
  Sword 3 dashes, one back every 1.0 s; greatsword 2, 1.1 s; daggers 4, 0.9 s; halberd 3, 1.1 s; bow 3,
  0.8 s; catalyst 3, 1.2 s. Endurance (+8% a point) and Patience bring them back faster, Far Blink
  sooner, Fourth Dash adds one, Bulwark / Tower Shield / Living Wall make a block use less of one,
  Perfect Form gives part of one back for dodging through a hit, Second Breath refills them all. The
  HUD shows them as pips, the one coming back filling; they shake when a dodge is refused.
- **Light combos repeat while held** (`update` in `js/hero.js`): holding light runs the combo and starts
  it again after the last hit; each swing re-aims as it starts. No attack costs anything, so a held combo never stalls. A skill, the special, a drink, a
  heavy or a roll pressed mid-combo goes off at the next gap, ahead of the held light.
- **Poise and stagger** (the owner asked for staggers to be rarer and longer). Every hit wears a boss's
  poise (its written poise x `POISE_K` 2.6 x the party scale); at zero it staggers for 5 s, shown by a
  ring counting down over its head. During a stagger each hero's first heavy or special is a
  **critical** (x3); the stagger runs its full length and takes no poise damage; a boss beaten past a phase threshold while
  reeling changes phase when the stagger ends, not before (it used to cut the stagger short). Each stagger makes the
  next need 25% more. Poise refills (12% a second) after 3 s without poise damage. About two to four (see Testing)
  staggers a fight.
- **Parrying** (sword and greatsword; `takeHit` in `js/hero.js`, `HERO["parry"]`): a hit that lands
  from the front within the weapon's window (0.18 s, greatsword 0.12 s) of *pressing* block is parried:
  no damage, no dash spent, a chunk of the boss's poise. The window runs from the press, not from when
  the guard comes up, so holding block through a swing earns nothing. As in Sekiro, tapping doesn't
  work: pressing block again within 0.5 s of the last press halves the window, then quarters it, and
  from the fourth quick press there's none; half a second without a press restores it. A shrunk or
  missed parry is still a block.
- **Statuses** on bosses: Burn and Bleed burst for damage, Frost slows the boss and breaks poise, Rot
  poisons over 5 s. Each meter needs 100 x 1.4^(bursts so far). A meter shows under the boss's bars
  once someone has built some of that status, fills toward its burst, and glows while the status is in
  force (4 s after a burst; Rot while it eats). The snapshot's last two boss fields carry them: percent
  full and in-force flags, in `STATUSES` order.
- **Boss health** scales x1.05, x2.05, x3.1, x4.1 with party size; poise x1, x1.4, x1.8, x2.2. Solo, bosses rest
  longer between moves; two-bodied bosses rest longer still.
- **Targeting** (`pick_target`, `choose`, `target_weight` in `fight.py`): each attack picks a move *and*
  a hero together, from every hero in that move's range, favouring the one it's walking toward, anyone it
  hasn't attacked for a while, and (for moves reaching 60 px or more) anyone who has kept over 120 px
  away (`far`). So a boss brawling with the swords turns its ranged moves on the archer. After every move
  it looks round again and may walk toward someone else.
- **What you see** (`drawWindup`, `drawTell` in `js/boss.js`; `drawSwing` in `js/hero.js`): every boss
  hit is outlined in red on the floor before it lands, from the moment its aim is final (its last lock)
  or 0.6 s before; projectiles show a dashed path, rings a faint circle; area hits (`mark`) fill in.
  A glint flashes on the boss just before its first strike (red if it can't be blocked), and a red
  marker hangs over the hero the move is aimed at. Every hero swing draws its real hitbox as it plays
  (a crescent across the arc, a lance along a thrust, a burst for a slam) in that player's colour; a
  hit lands with a white star, sparks and a short hit-stop. A boss flashes pale red in the instant
  before its strike.
- **Whose area is it** (`allyArea`, `pool` in `js/fx.js`): a boss's areas are solid: filled red
  warnings, and pools in their own colour with a hard red rim. A hero's (a skill's, a blessing's, arrow
  rain, for every player) are never filled and never red: a broken ring of dashes turning round the
  spot with four ticks pointing in, in the skill's colour, and motes rising if it lingers. Keep to this
  when adding either kind.
- **Where a boss can be hit** (`targets` in `js/boss.js`): the circle at its feet and a second of the
  same size on its drawn body (its radius x 1.5 above the feet, plus its height when it hovers or
  leaps). Before the second circle a shot or swing aimed at the boss you see, from the side, passed
  over the one on the floor; the Moth Saint, who hovers, was the worst.
- **One look for every effect** (`js/fx.js`; the owner asked for clean effects like Hades'): swings are
  tapered crescents, thrusts spearheads, slams bursts, shockwaves glowing rings, projectiles orbs with a
  tail and a white core, arrows a shaft with a streak; all filled shapes on additive-blend Graphics, the
  same for heroes (their colour) and bosses (the hit's `col`, orange for fire). A swing's trail lingers
  0.2 s after it stops hurting. Add new effects there, not as ad-hoc lines in the scene.
- **Screen-resolution canvas.** The canvas is the window's size and the fight camera zooms by the
  whole-number zoom, so sprites stay crisp pixel art while effects and rotated parts are smooth. World
  coordinates are unchanged (the view is 640x360 to 800x450 world px); use `cam.worldView` and
  `cam.getWorldPoint`, never `scale.width`, for anything in world space.
- **Animation easing** (`sample` in `js/rig.js`): keys under 0.2 s apart (strikes) snap out and settle;
  longer ones ease both ways, so wind-ups hold and strikes crack.
- **Difficulty** (`DIFFS` in `room.py`): Squire 0.75 health, 0.7 damage, 0.9 speed; Knight as designed;
  Hard 1.15 health, 1.25 damage, 1.12 speed, no Second Wind.

### The HUD (`buildHud`, `updateHud` in `js/ui.js`)

- **Your heroes are at the bottom left**: one panel online, one per couch player side by side. Each has
  health (with numbers; it pulses under 30%), Focus, the dash pips, then tiles with the
  key to press: the flask (a big count of what's left, red at none), each skill (a shade sweeps away as
  it cools down, with the seconds) and the special (shaded until there's Focus for it).
- **On each hero** (`drawBars` in `js/hero.js`; the owner asked, Nov 2026): a health bar over the head,
  framed in the player's colour, for every hero; and under the feet of this browser's heroes, their dashes.
- **Everyone else** is a small card at the top left (name, health, flasks as dots, buffs, downed text).
- **The boss's bars are top centre** (they were at the bottom, where the panels now go). The camera may
  scroll 56 px below the floor so a hero at the bottom wall isn't under a panel.

### Weapons (`content/weapons.py`)

| Weapon | Light | Heavy (hold) | Special (Focus) | Defensive |
|---|---|---|---|---|
| Sword & Shield | 3-hit combo | rising slash | Shield Bash | block, parry in the first 0.18 s |
| Greatsword | 2 wide swings, an overhead chop | overhead with hyper-armour | Leaping Slam (airborne) | block that lets 30% through |
| Twin Daggers | 5-hit flurry, every cut building Bleed | backstep cut | Shadowstep (blink and cut) | a dash instead of a roll: 0.28 s, untouchable throughout; the most dashes of any weapon |
| Halberd | thrusts, a sweep | 270° sweep | Pole Vault (airborne) | counter stance: a hit taken is absorbed and answered |
| Longbow | arrows, a 3-arrow volley | charged piercing shot | Arrow Rain where you aim | roll-shot: the roll looses an arrow as it ends, at what you're aiming at (not the way you rolled) |
| Catalyst | bolts, a 3-bolt fan | charged orb that explodes | Nova round you | blink instead of a roll |

Focus fills as you deal damage. Each weapon has four Arts (weapon-only upgrades).

**Write swings with `sw(arm, blade)`, `off()` and `both()`, never raw `weapon=` angles.** On the hero rig
a weapon at angle 0 lies back along the arm, so a raw angle that looks outward points into the body. The
helpers take the blade's real direction (0 forward, 90 up, 180 back, -90 down). The knight bosses that
hold a hero-style blade (Corvin, the Headsmen, the Mirror Knight, the King) had 180 added to every
`weapon=` of 30 or less for the same reason; the Alchemist's "weapon" is a round flask, so its angles
don't matter.

### Skills (`content/skills.py`)

Abilities on a cooldown that work with any weapon. Each hero picks one in the lobby to start the run
with (Ember Lance unless they change it; the keyboard player's choice is remembered). After every won
fight each hero is offered three they don't know and may learn one or pass; a hero carries two
(`MAX_SKILLS`), so with two already each card offers "Replace <skill>" for either slot. The shop
redraws the offer for 30 coins. Skills are kept in the save. Cooldowns start afresh each fight and show
on the hero's HUD panel.

- **Keys.** Slot 1 is Z or 1 (LT on a controller), slot 2 is X or 2 (A on a controller, or the D-pad).
  A is also revive: beside a fallen ally, holding it only revives. There's no rebinding.
- **Presses are buffered.** A skill pressed mid-swing, mid-roll or while reeling fires as soon as the hero
  is free (within 0.4 s). Pressed while cooling down, its HUD chip shakes red with a sound.
- **What's on a hero shows** (the snapshot's last three hero fields: ward left, seconds of extra damage,
  a charged next hit): a pale shell for a ward, embers circling the feet for extra damage, a violet spark
  for a charged hit, on every screen, and as chips on that hero's HUD card ("Ward 23", "Damage up 4s",
  "Next hit charged"). A hit a ward soaks whole says "Warded" and doesn't spill a drink.

| Skill | Cooldown | What it does |
|---|---|---|
| Ember Lance | 8 s | a piercing lance of fire, x3.2, builds Burn |
| Frost Nova | 12 s | a ring of ice round you (72 px), x2.2, builds Frost, heavy on poise |
| Judgement | 12 s | a pillar of light where you aim (the cursor or the boss you're locked on to, up to 220 px; else 110 px ahead), landing after 0.55 s, x4.5 |
| Reaping Whirl | 9 s | three strikes all round you (58 px), x1.3 each |
| Phase Step | 8 s | blink 120 px the way you're walking (or aiming), untouchable for 0.28 s; your next hit within 5 s deals 60% more |
| Rallying Cry | 22 s | you and allies within 150 px deal 30% more for 6 s |
| Litany of Mending | 30 s | heals you and allies within 120 px for a fifth of your health |
| Stone Ward | 20 s | soaks the next 45 damage you take |
| Fan of Knives | 7 s | five knives in a fan, x0.9 each, each builds Bleed |
| Plague Censer | 16 s | a cloud where you aim (up to 200 px) for 3 s: six ticks of x0.7, building Rot |
| Hammerfall | 11 s | a slam just ahead of you, x1.6, the most poise damage of any skill |
| Second Breath | 24 s | every dash comes back at once, +40 Focus |

A skill's damage is `BASE` (20) x its multiplier whatever weapon is held; it counts as a special for
build bonuses and for the critical on a staggered boss, but builds only its own status (not the
special slot's) and doesn't trigger heal-on-special. The browser plays a skill like an attack (state
`skill`, animation `k_<id>`, hits reported as `atk: 'skill', sk`) and tells the server `{t: 'skill'}`
when it starts: the server keeps the cooldown (0.3 s of slack), applies what acts at once (empower,
rally, heal, ward), broadcasts fx `skill` (everyone sees a ring in the skill's colour and its name) and
only counts that skill's hits for 4 s after. Bonfire message: `{t: 'learn', h, i, at}` (`at` = the
slot to replace when full) or `{t: 'learn', h, skip: 1}`.

### Upgrades (`content/upgrades.py`, applied in `build.py`)

The owner calls these blessings. Only those a hero's weapon can use are offered (`usable`, `req`: block and
parry upgrades need the sword or greatsword, guard upgrades a block or the halberd's counter, the longer
roll an ordinary roll, Long Reach a melee weapon). About twenty that were flat bonuses now add an attack or an effect instead (`proc` effects: the
browser looses them in `LocalHero.proc`, the server prices them as `atk: 'proc', p: <id>` at 20 x `pow`):
a wave of fire or a shockwave on the light combo's last hit, an eruption, lightning or a ground wave on a
fully charged heavy, ice shards or a pool of rot on any heavy, fire left behind a roll or thunder where it
ends, frost bursting from a block or from drinking, an echo striking after a roll through a hit. Others:
Momentum (each combo hit deals more than the last), faster light attacks, Tailwind (speed after a roll),
heals when your Burn or Rot takes hold, Unbowed (once a fight, survive a downing hit), piercing light
arrows, an extra bolt on every catalyst cast. A heavy that is a shot (the bow's arrow, the catalyst's orb)
carries a `heavy` / `heavy_full` area with it: Thunderclap, Pyre Strike and the like go off where the shot first
strikes or comes to rest, not at the hero's feet (they used to land at the cursor 0.4 s after release, or, on a
controller, just in front of the caster, which read as not working). "Fully charged" is 95% or more, and
reaching full charge flashes the hero with a chime. When adding one, prefer these to a flat `dmg` or `stat`.

100 in all: six Vows (Ember, Rime, Blood, Storm, Rot, Iron) of nine each (one per slot: light, heavy,
special, dodge, guard; and four passives), ten plain passives (five of them for skills: quicker cooldowns, more damage, a heal, a ward or Focus on
use), six Pacts (only offered to parties of two
or more), six Duos (offered once you hold both Vows), and 24 Weapon Arts. A slot holds one upgrade; taking
another replaces it. Rarity (common, rare x1.5, epic x2) scales the numbers. Offers lean toward Vows you
already follow. Attributes: Vigor +12 health; Endurance dashes back 8% faster; Might +7% heavy
and special damage and +8% poise damage; Finesse +6% light damage; Arcane +12% status buildup and +8%
special damage.

### The bosses

Every boss has 5-7 moves and a second phase (the finals have three) whose transition is an invulnerable
roar with a shockwave. Every move has a readable wind-up (and a distinct sound); area attacks mark the
ground first. Every boss has ranged attacks and areas to keep out of from its first phase.

| Boss | What it does |
|---|---|
| Ser Corvin | 3-hit combo that re-aims each swing, shield charge, delayed overhead, lunge, guard stance (front hits glance off), a thrown steel crescent, the brand (sword planted: burning brands in a cross round him and under you). Phase 2: a fourth burning slam with a spreading ring; fire waves. |
| Mire Mother | tongue lash that pulls you in, belly-flop leap (lands where its shadow is), poison pools, a fan of bile globs, slap, tadpoles. Phase 2: submerges and erupts under you; double flop. |
| Bellwarden | tolls send rings with gaps at the sides (sound can't be blocked), rakes, bell-slam, lurch, ghost choir, the knell (three ghost bells fall on you, each re-aimed). Phase 2: three tolls with different gaps; drags the bell round. |
| Twin Headsmen | two bodies: the Hook (chain pull, flurry, chain whirl, dash, thrown hooks, a snare of chains that bleed whoever stands in them) and the Axe (execution, sweep, stomp, charge, a thrown axe). When one falls the other roars, heals a quarter and learns the other's signature. |
| Briar Wolf | pounces, a feint that hops back then pounces, bites, tail lash, a spray of thorns, briars (roots burst under you and leave a thicket round the spot), howl raising a wall of thorns. Phase 2: the clearing goes dark; double pounces. |
| Ashen Alchemist | keeps its distance; lobbed fire flasks, three-colour volleys, stilt stamp, vaults away leaving poison, homunculi. Phase 2: transmutes the floor; the great mixture; burning spray. |
| Gravewyrm | burrows and erupts under you, lunging bite, bone shards, thrash, a ring that closes in. Its vertebrae can be struck too. Phase 2: burrows twice. |
| Mirror Knight | the heroes' own combo, glide, shard fan, a parrying stance, glass reflections, shards raining in marked circles. Phase 2: the mirrors shatter. |
| Bastion | rocket fist, stomp, a sweeping furnace beam, two-fist hammer, mortar shells lobbed from its back that leave fire. Armoured (half damage) until both knee cores and the back core are broken; then it topples for 7 s. Phase 2: two fists, the beam both ways. |
| Moth Saint | hovers at range; dust spirals, pillars of light, wing gust, dust streams, mothlings. Phase 2: snuffs the candles (darkness); double spirals. |
| Hollow King | phase 1 a duellist (lunges, a four-cut flourish, riposte stance, backstep, thrown knives, the decree: a crown of sigils round you, then its centre); phase 2 swells into the hollow giant (cleave, leaping crash, sweeps, void bolts, pools of void); phase 3 the sky falls. |
| Eclipse Drake | fire breath that sweeps and leaves the bridge burning, lobbed fireballs, claws, tail, wing gust. Phase 2: dives along the bridge and rains fire from the air. Phase 3: the bridge's edges burn for the rest of the fight. |

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
- **Boss attacks are heard** (`sounds` in `js/boss.js`, `sfx.boss` in `js/audio.js`): a breath drawn in
  through the wind-up, a ping with the glint (a sour low one if the move can't be blocked), then each
  hit's own sound as it starts, by shape: a whoosh for a swing, a sharp one for a thrust, a thump for a
  slam, a rolling boom for a ring, a zip for a projectile, a crash for an area landing on its mark, a
  hiss for a pool, a chirp for adds; lower for bigger hits, with a roar of flame for fire. They play
  from the move's timeline, panned to where the hit is; hits of one kind within 60 ms sound once.

## Code map

| File | Holds |
|---|---|
| `app/kingfall/routes.py` | The page and the WebSocket (through `app/rooms.py`) |
| `app/kingfall/room.py` | Rooms, couch heroes per browser, the lobby, the run, the Bonfire, difficulty, checkpoints, the 30 Hz loop |
| `app/kingfall/fight.py` | One fight: bodies, moves, AI, damage, poise, statuses, adds, cores, downed and revive |
| `app/kingfall/build.py` | A hero's attributes and upgrades folded into numbers (`Build`); `client()` is what the browser needs |
| `app/kingfall/geom.py` | Hit shapes in Python (for the sim; twin of `js/moves.js`) |
| `app/kingfall/save.py` | Saved runs in SQLite |
| `app/kingfall/content/` | `moves.py` (shape builders, motion), one file per boss, `weapons.py`, `skills.py`, `upgrades.py`, `__init__.py` (hero numbers, scaling, what the browser gets) |
| `app/static/games/kingfall/js/main.js` | Boot (Phaser at a whole-number zoom), menus, lobby, Bonfire, the connection |
| `js/input.js` | Keyboard/mouse and up to four gamepads as one set of actions (LT and A are the skills, so only LB blocks) |
| `js/fight.js` | The fight scene: arena, lights, darkness, heroes, boss, hit checks, effects, camera |
| `js/hero.js` | Local heroes (every weapon's behaviour), remote heroes, poses |
| `js/boss.js` | Boss bodies, adds, the wyrm's trail, danger drawing, hit checks against heroes |
| `js/fx.js` | Every drawn effect: crescents, lances, bursts, shockwaves, orbs, arrows, impacts, pools |
| `js/moves.js`, `js/rig.js`, `js/ui.js`, `js/net.js`, `js/audio.js`, `js/music.js`, `js/arena.js`, `js/arenas.js` | As named |
| `art/atlas.png`, `art/atlas.json` | Generated by `python3 tools/kingfall-art/build.py`; never edit by hand |

## Testing

- `tools/check-all.sh` runs `node tools/kingfall-parity.mjs` (the JS and Python move maths agree on every
  move of every boss), `python3 tools/kingfall-sim.py --fast` (two fights a boss and party size, and two for each weapon) and
  the browser smoke test below.
- **The balance sim** (`tools/kingfall-sim.py`): bot parties fight on the real server code in simulated
  time. Bots see hits coming and roll with probability `skill`, step out of pools, fight adds, break
  cores, drink and revive; they get the levels and random blessings a run gives before that boss's tier.
  `python3 tools/kingfall-sim.py "" 10 --skill 0.85` runs every boss at every party size in about a minute.
  Bots carry the skills a run gives by then (a starting one, a second from the first Bonfire) and use
  them when they'd do some good; how many of a skill's hits land is an estimate (`use_skill` in the sim).
- **Bots fight with every weapon** (`--weapon bow`, or `mixed`; the default is the sword). They stand
  inside a melee weapon's reach or well back with a bow or catalyst (backing off when the boss closes),
  run the light combo, use the special when there's Focus and it reaches, and wind up the charged heavy
  on a staggered boss for the critical. The daggers dodge with their dash (two charges), the catalyst
  with its blink (to a spot nothing is about to hit). Lights are checked against their real shapes;
  heavies and specials by reach; arrows and bolts hit what's in range, ignoring flight time. Bots never
  block, parry or counter, spend and regain dashes as the game does, and are
  poor at rings and slow projectiles: treat the numbers as a rough guide.
- **The weapons table** (`python3 tools/kingfall-sim.py "" 8 --weapons --skill 0.85`, about five
  minutes): each weapon alone / in a pair of the same, then mixed parties of 3 / 4. Latest (Nov 2026,
  8 fights a cell, win %):

  | Boss | Sword | Greatsword | Daggers | Halberd | Bow | Catalyst | Mixed 3/4 |
  |---|---|---|---|---|---|---|---|
  | Corvin | 75/88 | 88/88 | 100/88 | 88/100 | 50/100 | 100/100 | 100/100 |
  | Mire | 88/88 | 100/88 | 100/100 | 100/100 | 62/88 | 100/100 | 100/100 |
  | Bellwarden | 62/75 | 100/88 | 88/88 | 100/100 | 75/100 | 100/100 | 100/100 |
  | Headsmen | 75/88 | 88/88 | 75/88 | 88/100 | 88/88 | 100/100 | 100/100 |
  | Wolf | 100/100 | 100/100 | 100/88 | 100/100 | 88/100 | 100/100 | 100/100 |
  | Alchemist | 62/100 | 88/88 | 100/88 | 88/88 | 62/100 | 88/100 | 100/100 |
  | Wyrm | 100/88 | 75/100 | 100/100 | 62/100 | 62/100 | 100/100 | 100/100 |
  | Mirror | 88/88 | 88/100 | 88/88 | 75/100 | 75/100 | 100/100 | 100/100 |
  | Bastion | 50/50 | 88/100 | 88/88 | 75/88 | 25/12 | 100/88 | 100/100 |
  | Moth | 100/75 | 100/100 | 100/75 | 75/75 | 12/75 | 0/62 | 88/100 |
  | King | 88/88 | 75/100 | 75/88 | 88/75 | 38/75 | 0/50 | 100/100 |
  | Drake | 88/38 | 62/62 | 100/100 | 50/25 | 25/12 | 50/100 | 75/100 |
  | All | 81 | 90 | 90 | 85 | 67 | 85 | 98 |

  This is the first table under dashes instead of stamina (bots used to roll for free). Fights average
  1.1 to 1.7 minutes and 1.5 to 2.7 staggers. With 8 fights a cell, one cell swings by 25 points; read
  the columns. The daggers column is from a second run after one adjustment (4 dashes a 0.7 s apiece
  and base 16 won 97%; now 0.9 s and base 15); the bow's recharge went 1.0 s to 0.8 s after its
  column was run and a rerun scored the same (55% alone, 79% in pairs). **The bow is the weakest**,
  worst alone against the Bastion, the Moth and the Drake; the catalyst alone can't beat the Moth or
  the King. Parties of three and four win nearly everything.
- **How the daggers got here** (Nov 2026): 35% at first (base 13, two dashes). The cause was the dash's
  invulnerability, 0.2 s against a roll's 0.29 s, too short for any hit that lingers; untouchable for
  the whole 0.28 s dash they reached 91%. The catalyst's first 49% was the bots blinking into the next
  hit, not the weapon.
- **After the faster heroes and longer roll** (Nov 2026, sword parties, 10 fights each at skill 0.85,
  solo / 2 / 3 / 4): Mirror 80/100/100/100, Bastion 60/80/90/100, Moth 90/90/80/100, King
  90/90/100/100, Drake 80/50/80/90; staggers 1.3 to 4.7 a fight. Much as before: bots then rolled for free
  and dodge by timing, so they gain little from speed. A person will find it easier.
- **Earlier numbers** (Nov 2026, sword parties before bots used heavies; 12 fights each at skill 0.85;
  solo / 2 / 3 / 4): Corvin 67/67/92/100, Headsmen 67/75/92/100, Alchemist 67/100/100/100, the rest
  83-100. Middling bots (skill 0.6) won a third to a half of Corvin, the Headsmen, the Wyrm, the
  Bastion and the finals. Bosses staggered two to four times (five for the Headsmen and the finals with
  a full party): more than the one to three the owner asked for, so poise is the next thing to raise
  if it feels cheap.
- **Why the boss numbers moved** (Nov 2026): until bots used skills and specials they won 16-66% of the
  hard fights; once they did, with the old numbers, they won about 95% of everything. One tuning pass
  brought it back: `POISE_K` 1.8 to 2.6, boss health scale 0.9/1.8/2.7/3.6 to 1.05/2.05/3.1/4.1, and the
  skills' poise damage cut by about a third.
- **The browser smoke test** (`node tools/kingfall-smoke.js --serve`, about 50 s, in `check-all.sh`):
  starts its own server. One player: picks a starting skill, uses it, wins, learns a second at the
  Bonfire, uses that. Then two players in one room (two browser contexts): each must see the other's
  skill announced and animated, a ward on the other's hero and HUD card, a lance in flight, the boss
  hurt and its Burn meter showing; both go through the Bonfire into the second fight. Then couch: two
  pretend controllers (`navigator.getGamepads` replaced) on one browser; the first used must become player
  one's, the second gets a hero with Start, its cursor must stay in its own row, and in the fight each
  stick must move only its own hero. Fails on any page error. Skipped (not failed) where Playwright isn't installed. Without `--serve` it runs against a
  server you started. It doesn't cover going down and being revived, or a reconnect.
  (The game reuses one fight scene object across fights: anything a test hangs on it outlives the fight.)
- In a debug room the start message takes `ups: [upgrade ids]`: every hero begins holding them (how the
  proc upgrades were checked in a browser). Sim bots count finisher and heavy procs roughly; roll, guard,
  flask and perfect-dodge procs aren't played by bots.
- `?debug&boss=mire` on the page: a debug room that starts at that boss; `window.kf.win()` wins the
  fight, `window.kf.safe()` makes this fight's boss walk about without ever attacking (for tests that
  stand and look).
- `python3 tools/kingfall-art/anim.py <boss|weapon> <move> out.png` draws a move's keyframes as a strip;
  `sheet.py` reviews bosses beside a hero at game size; `preview.py` the heroes.

## Gotchas

- **The two halves of the move maths must agree.** After changing `js/moves.js`, `geom.py` or
  `content/moves.py` (or adding a shape kind), run `node tools/kingfall-parity.mjs`.
- **The server never clamps a move's motion after the fact**: browsers draw it as sent. `Fight.fit`
  shortens steps so a move can't carry the boss through a wall; a move whose steps come after a lock is
  only shortened from that lock on (or the boss would jump on screen).
- **A move has one reach** (`tx` hits are placed by the move's last resolved distance, shared by all its
  hits). In a move that re-aims more than once, a lingering `tx` zone or ring would slide when it re-aims,
  so such moves use only short `tx` circles (the Bellwarden's knell); pools at the target belong in
  moves with a single aim.
- **Hit ids**: `seq:i` for a move's hit, `seq:i:n` for a pool's nth tick, `a<id>:<n>` for an add's bite
  (every 2 s, not in its first second). The server keeps the last 12 finished moves for late reports and
  lingering pools; a pool that outlives that won't hurt.
- **Parts**: a rig only gets images for frames that exist in the atlas, so an optional part (a shield) can
  simply be missing. A new boss needs its rig in `tools/kingfall-art/bosses.py` (`RIGS`, `BOSSES`,
  `BOSS_RIG`), then `build.py`, then a content file registered in `content/__init__.py` and `POOLS`.
- **Cache versions**: `python3 tools/bump-version.py app/static/games/kingfall` after changing its JS or
  CSS. The atlas is loaded with the page's version, so a rebuilt atlas also needs a bump.
- **A shot's `hit` window is a moment, not a span.** Projectiles and called-down areas have 10 ms
  windows, narrower than a frame, so `checkHit` looses them on the first frame at or after `hit[0]`.
  (Until Nov 2026 it required a frame inside the window, and about four shots in ten never left the
  hero: every bow and catalyst attack, and the thrown skills. The two-player smoke test found it.)
  Melee shapes still need a frame inside their window; keep those 60 ms or wider.
- **A new skill** needs only an entry in `content/skills.py` if it's built from the existing pieces
  (`shape`, `proj`, `aoe`, `blink`, `empower`, `rally`, `heal`, `ward`, `status`; poses `cast` and
  `raise`; `dashes` and `focus` are applied by the browser). Animation names reach the server cut to 12 characters, so keep ids to 10 or fewer.
- **The last snapshot of a lost fight must go out.** The loop sends a snapshot every other tick; when the
  last hero fell on an off tick, their browser never heard they were down and they could walk about for
  the three seconds before the lobby. The loop now sends one on losing, and the browser downs its own
  hero on the `down` and `wipe` events without waiting.
- The fight lives in one process's memory; a deploy drops it (the run resumes from the last Bonfire).
