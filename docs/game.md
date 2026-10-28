# Roguelike Tactics (the game at /games/roguelike-tactics)

Read this before changing anything in `app/static/games/threefold/` or `tools/threefold-autoplay.js`.

## What it is

A pixel-art tactical roguelike: a Warrior, Mage and Rogue climb three acts, each drawn per run
from two (Greenwood or Drowned Marsh, Sunken Crypt or Rime Halls, Ember Peaks or Clockwork
Foundry). Each act is a branching map of battles, elites, events and shops ending in a
boss. Battles are grid tactics on a 10×8 board, with speed-based turn order, terrain, flanking,
statuses and line of sight. Runs save to `localStorage`.

## Code map (`app/static/games/threefold/`)

The game was called Threefold Path at first. Its folders, tools, `localStorage` keys and save key
still say `threefold`; leave them, since renaming the keys would wipe players' saves and settings.
`/games/threefold-path` redirects to the new URL.

The game is static files with no build step. `/games/roguelike-tactics` serves `index.html`, which
loads Phaser 3.80.1 from cdnjs, then `js/main.js` as an ES module.

| File | Holds |
|---|---|
| `js/data.js` | All content: terrain, acts and encounters, `ARCHES` (archetypes), classes and skill pools, promotions (`PROMOS`, two tiers), `SKILLS`, `MODS` (skill artifacts), `ITEMS` (hero artifacts), `FOES`. Start here for content or balance changes. |
| `js/rules.js` | Pure rules shared by menus and battle: hero stats, `isClass`, `promoOptions`, `skStats` (a skill after its artifacts, the hero's artifacts and class passives), `thornsOf`, `describe`, `canSocket`, archetype-weighted reward pools, skill offers. |
| `js/battle.js` | `BattleScene` (Phaser drawing, tweens, particles), the turn loop, damage, statuses, movement, line of sight, terrain effects, the AI, and the battle side panel (HTML). |
| `js/main.js` | Run flow and every HTML screen: title, map side panel, rewards, equipping, learning skills, promotion, events, shop, party screen, saving, the Phaser game config. |
| `js/mapscene.js` | `MapScene`: the branching map, drawn and clickable. |
| `js/art.js` | `flat32()`, which gives every sprite its outline and matte shading, the 8×8 map icons, and the canvas and texture caches. |
| `js/sprites.js` | **Generated**: every hero and monster as a 32×32 grid of flat colour regions. Never edit it; change `tools/threefold-art/` and run `build.py`. |
| `js/tiles.js` | Terrain at 32px, painted procedurally per theme (`THEME_ART`), and `drawBoard`, which composes a whole battle board including neighbour-aware touches. |
| `js/audio.js` | Every sound effect and music loop, synthesized at startup with `OfflineAudioContext` and played through Phaser's sound manager. |
| `js/bot.js` | The autopilot's choices outside battle (only with `?auto`): artifact picks and where they go, lessons, classes, team artifacts, map nodes, campfires, shops. |
| `js/ui.js` | DOM helpers `h()`, `sprImg()`, `bar()`, and the status tooltips (`tip`, `tipText`, `initTips`). |
| `game.css` | Styling for the HTML screens and panels. |

Phaser only draws the map and the board. Everything text-heavy (menus, cards, the battle side
panel) is plain HTML in `#screen` and `#side`, so it stays crisp, accessible and phone-friendly.
Keep it that way.

## Design directives (agreed with the owner)

- **Healing is scarce; an act's attrition is the challenge.**
  - There's no healing after a fight. The fallen get up with 10% HP.
  - In-battle healing and lifesteal can restore any HP, old wounds included (the owner dropped the
    old cap). Scarcity comes from few healing skills. The owner took Mend out of the Mage's pool (it stays in
    `SKILLS` so old saves work), and the Blood Vial artifact, which only fit Mend, went with it.
  - Lifesteal was too strong and was cut: drains are 15–45% of damage, Leech Jar 25%, Vampire Fang
    10%, Leech Seed heals half the poison, and `leech()` caps what one skill (echoes included) can
    drink at 20% of max HP.
  - Inns heal 25% for 45g (40% in the shops just before a boss), and event heals are 10–25%.
  - A new act fully heals.
  - Don't add easy healing back.
- **No stalling.** After about 9 rounds (`CALM_TURNS` hero turns) foes gain +10% damage per round.
  This exists to stop "keep one enemy alive and heal in a corner".
- **Every hero promotes after each act boss**, choosing between two classes: a tier-1 class
  (`CLASSES.promos`) after Act 1, then a tier-2 master class (`PROMOS[t1].next`) after Act 2. That's
  6 + 12 classes. `p.line` lists a hero's classes and **all their passives stack**; `p.promo` is
  only the latest (sprite and title). Promoting teaches one skill picked at random from the new
  class's `skill` plus `pool`, rolled when the choice is shown so the card can name it; each class
  has 8–13 skills in all. The class's skill pool then replaces the old one (see below).
- **Skill pools are deliberately maximalist.** The owner plays them and prunes what isn't fun, so
  prefer adding a strange skill over polishing a safe one. Removing a skill means deleting it from
  its pool (and from `SKILLS` if nothing else uses it). A pool naming a missing skill only fails at
  runtime, so grep for the id.
- **Levels grow by class.** Every win levels each hero up (`levelUp` in `rules.js`) using
  `GROWTH` for their current class (latest promotion, else base class): HP and `each` stats every
  level, `every` [n, stats] on multiples of n, and `at` one-offs such as +1 MOV. Classes should feel
  different as they grow; tanks gain DEF and HP, casters MAG and RES, skirmishers SPD, CRIT and MOV.
  New classes need a `GROWTH` entry.
- **Skills come from class pools.** Heroes start with 2: their basic attack (`CLASSES.start[0]`) and
  one random pick from the rest of `start` plus `pool`. They learn only from their
  current class (`skillPool` in rules.js): `start` plus `pool` before the first promotion, then the
  latest class's `skill` plus `pool`, up to `MAX_SKILLS` = 4. Skills already known stay. Learning a fifth means forgetting one.
- **Archetypes give builds a direction.** Nine tags in `ARCHES` (poison, elemental, shield, thorns,
  blood, time, plus hex, carnage and fortune borrowed from other roguelikes) sit on classes (`arch`) and artifacts (`tags`). `artifactPool` weights its order by
  how much of each archetype the party has (`partyArches`), so a build snowballs without being
  forced. Every archetype needs payoff artifacts that reward stacking it (detonate poison, damage vs
  shocked, scale with shield or thorns), not just more of the same status.
  - Hex (Slay the Spire's marks, Darkest Dungeon): `st.hex` stacks to 9, never expires, adds 5%
    damage taken each, and is cashed in by `hexBurst` (4 + 25% of the skill's stat per hex).
  - Carnage (Risk of Rain on-kill items): `onKill()` in battle.js handles per-skill kill rewards
    (overkill spill, cooldown reset, shield, a second move via `u.extraMove`); `ko()` handles worn
    ones (Will-o'-Wisp, Gasoline, Headhunter's Trophy via `u.kills`).
  - Fortune (crits and luck): `critUp`, `alwaysCrit`, Four-Leaf Clover, Loaded Dice (`roll()` and
    the coin flip), crit payouts.
- **Turn order can't be locked.** Time effects used to stunlock foes. Every delay goes through
  `delayUnit` (bosses take half, a second push before the unit's next turn does half again, floor
  of −50 CT) and every haste through `hasteUnit` (capped at "acts next", never a double turn;
  repeats do half). A stun leaves the unit Steady (`st.steady`) so it can't be stunned again until
  its next turn ends. Slow cuts SPD by a third. Don't write `t.ct` directly for a new effect.
- **Foes show a forecast of their next move.** `refreshIntents()` in battle.js plans
  (`planAI(f, true)`, which counts skills one turn off cooldown) for every foe that acts before the
  next hero's next turn, and stores it as `u.intent` (skill, where it will stand, target tile). It's
  recomputed from scratch at the start of each hero turn, after every hero step (move, undo, action)
  and after every turn (with `B.active` cleared first, so the unit that just acted is forecast too;
  otherwise a foe that just attacked showed nothing until the next hero's turn); a foe still plans afresh with `planAI` when its turn comes. So the intent is
  what the foe would do if things stayed as they are, **not a commitment**. The owner first tried
  locked-in attacks (Into the Breach style) and dropped them: heroes could kite forever and never
  be hit. Stun, sleep, confusion, charm and death clear it (the card says "Next: skips its turn").
  The board draws red tiles, a line through where it will stand and the summed damage on each
  target (`intentView`); the foe's card says "Next: Skill → Target −N".
- **Shields last about two rounds.** Each shield gained is its own piece in `u.shieldBits`
  ({ n, t: 2 }); `startTurn` counts them down and drops a piece at the start of the holder's second
  turn after it was gained. Hits eat the oldest piece first (`drainShield`). Don't write `u.shield`
  directly: use `addShield`, `drainShield` or `clearShield` so the pieces stay in step. This was
  added because long fights let shields stack without limit.
- **Run stats.** `tally(u)` in battle.js counts, on each hero's party entry (`p.tally`, so it saves),
  damage dealt (shield soaked plus HP lost, poison and burn credited to whoever applied them via
  `opts.by`), biggest hit, kills, damage taken, HP healed, shield gained, crits and knockouts. The
  defeat and victory screens show them in a table (`heroStatsTable` in main.js).
- **Artifacts that mention a status say how strong it is.** Poison, thorns, brambles and turn
  shifts give their numbers in the note ("each turn dealing 30% of the stat the skill uses", "6 + 50%
  of your DEF", "40% of a turn"); `describeParts` prints delays and hastes as a share of a turn.
- **Removed:** the Swapstone (ATK and MAG trade places) and the Mirror Pool event that did the same,
  since no class wants it. `load()` drops artifact ids that no longer exist from old saves.
- **Team artifacts replace the spoils after act bosses 1 and 2.** `TEAM` in data.js; the party
  picks one of three (`teamReward` in main.js) and it goes in `run.team` and on every hero as
  `p.team` (the same list). `has(u, id)` checks `u.items` and `u.team`, so team effects are written
  like hero artifacts (`heroStats` adds their `stats`; battle.js reads the rest). Several have a
  downside (`down`). Team ids must not collide with `ITEMS` ids, since `has` can't tell them apart
  (the hourglass and blood pact team artifacts are `kingsglass` and `bloodoath` for that reason).
- **Rewards with a downside.** Any artifact may have a `down` string: cards show it in red under
  the upside (`artUp`/`artDown` in rules.js; `artText` joins both for tooltips). The cursed hero
  artifacts (Berserker Mask, Hollow Heart, Reckless Greaves, Gambler's Bone Die, Lodestone Heart)
  and the older Glass Monocle, Tortoise Shell, Featherweight Anklet and Cursed Crown use it.
- **Bonus objectives.** Every normal and elite battle gets one (`makeObjective` in main.js, texts in
  `OBJECTIVES`): win within 5 rounds' worth of hero turns, no hero below half HP (only offered when
  everyone starts at 60%+), nobody knocked out, defeat the toughest foe first, or two kills from one
  action. The reward (gold, or one extra artifact offer and pick) is named up front. battle.js
  tracks it in `B.obj` (`objFail` makes a failure final; `objectiveMet` reads the result on a win),
  shows it under the turn strip and announces it at the start.
- **The ascent ladder.** `ASCENTS` in data.js, cumulative. Every ascent is open from the start (the
  owner asked); the title screen picks one, and `localStorage` `threefold-ascent-pick` remembers the
  last choice. Winning a run moves the pick up one. The
  run keeps `run.asc` and battles get `B.asc`. Where each rule lives: elite/boss and all-foe HP and
  boss CT in `foeUnit`, foe and boss damage in `dmgMult`, start gold in `newRun`, healing in
  `innHeal`/`campHeal`, fallen HP and artifact offers in main.js. `?auto&asc=N` plays at ascent N.
- **Campfires** (map node `rest`, about 12% of nodes from the third row on): one choice of resting (30%
  heal), tempering a skill (`s.tempered`: +25% power, 1 shorter cooldown, a "+" on the name, applied
  in `skStats`; once per skill) or training (learn a class skill).
- **Skill text is laid out, not run on.** `describeParts()` splits a description into `head`
  (reach, power, cooldown), `fx` and `cost`; `skillText()` in ui.js renders them as a line, chips
  (costs in red) and italic flavour. `describe()` still gives the joined string for `title`s.
- **Classes and skills borrow from FFT, Tactics Ogre and Horizon's Gate** (Jump, Draw Out, Rampart,
  Arithmetician math targeting, Steal Heart, songs), reshaped to fit the grid and scarce healing.
- **Skill modifiers are artifacts, and artifacts are the main battle reward.**
  - Skill artifacts (`MODS`) socket into a skill (`MAX_MODS` = 2) and rewrite it: the stat it
    scales with, its targeting, its effect.
  - Hero artifacts (`ITEMS`) are worn (`MAX_RELICS` = 3) and change stats or add passives.
  - Unequipped ones wait in `run.stash`, the pack.
- **Upgrades should be strange.** New artifacts should change how a skill or hero plays, not just
  add numbers.
- **Movement avoids hazards when it can.** `reach()` keeps every route to a tile that isn't beaten
  on both movement cost and hazard (lava, brambles), then gives each tile its safest route, cheapest
  among equals, so a longer route around brambles is taken when it fits in MOV. Each entry's `from`
  points at the route's previous step; `pathTo` follows it.
- **Random-target skills preview one hit per target.** For `shape: 'random'` and `'multi'` the aim
  preview and intents show what a single hit would do to each possible target (`randomPick`), not the
  average share of the volley.
- **Socketed artifacts explain themselves.** On the Party screen, the socketing screen and the
  battle unit card, a skill's artifacts are tooltips (`tipNote` in ui.js) showing the artifact's text.
- **The final boss ends the run at once**: no level-ups or rewards, straight to the victory screen.
- **Show the numbers.** `describe(o, src)` prints the result next to the scaling ("75% MAG = 9"),
  including burn and poison per turn ("Burns 2 turns (30% MAG = 5/turn)"). Pass a source wherever a
  skill is described. Equipping an artifact shows what it changes: `outputOf` before → after for
  each skill, plus stat changes for hero artifacts (`wearPreview` in `main.js`).
- **Pixel art only, no image or audio files.** Sprites are drawn in Python and built into
  `sprites.js`; sounds are synth recipes in `audio.js`.
- **The look aims at modern 16-bit (the owner's reference is a cozy farm tileset).** Everything is
  32px per tile, shown at 2×.
  - Sprites: every hero and monster is hand-drawn at 32×32. **Read `docs/game-art.md`** before
    drawing or changing one: it has the art direction, the palette, and what each chosen hero looks
    like. The drawings live in `tools/threefold-art/` (Python with Pillow). `picks.py` maps each art
    key to its drawing, and `python3 build.py` writes `js/sprites.js`. Then bump the game's `?v=`.
  - Ground follows the owner's grassland reference
    (<https://img.craftpix.net/2023/04/Grassland-Top-Down-Tileset-Pixel-Art.jpg>): calm, warm
    and flat. Greenwood grass is olive `#a1b159` with sparse leafy tufts in clumps, rare small flowers
    and darker grass gathered under trees and rocks, with no speckle noise. Earth is orange-brown
    `#b47c43`. Natural grounds (grass, mud, snow, basalt) also get a board-wide layer of soft lighter
    and darker patches with stepped edges (`patchMask`, theme `patch`); it only recolours bare
    base-colour pixels. Plain ground has eight variants mixed with position so it doesn't visibly
    repeat. Keep new ground calm rather than noisy.
  - Terrain: `tiles.js` paints each tile from the theme's ramps (`blob()` gives lit, rimmed shapes),
    then `drawBoard` adds what depends on neighbours: banks and foam on water, cliff faces under
    high ground, shadows below walls, lava glow. The board is one canvas texture, repainted when
    terrain changes and every animation tick. A new theme is one `THEME_ART` entry.
- **Later acts scale harder** (`foeUnit`: +26% HP and +17% ATK/MAG per act on top of the per-level
  curve) to answer every hero promoting after each boss, plus team artifacts and tempering.
- **Normal fights bring reinforcements** (`battle()` in main.js): extra copies of members of the
  encounter, none in act 1's first two rows, one in the rest of act 1 and early in acts 2 and 3, two
  in their second half. (One everywhere plus +30%/+20% act scaling took the bot to 0 wins in 39.) The owner found normal fights too easy (the bot
  won 98%+ of them); keep encounter lists in data.js at their base size and let this add the rest.
- **Defensive artifacts are kept modest.** The owner had them nerfed after balance runs showed the
  defence and shield builds winning most: Iron Sigil +15% (was +50%), Tower Crest 100% of shield
  (was 150%), Kite Shield Boss half the damage, Bulwark Plate equal to the damage, Bracing Rivet
  +20%, Oak Heart 6%, Butcher's Hook 10%, Capacitor Plate and Aegis Standard 15%, Lodestone Heart
  35%, Aegis Heart +20%, Shrapnel Shell half the shield, Spiked Bulwark +50% thorns, Iron Buckler
  +2 DEF, Tortoise Shell +5 DEF, Ironbark Plate +3 DEF/+6 HP, Phalanx Sigil 15%, Leaden Mantle +3/+3. Foe SPD scales too (`foeSpd`: +2% per level
  plus 1 every 6 levels), and the fastest hero lines grow SPD every 3 levels rather than 2: before
  that, act-3 foes sat at 4–12 SPD while Tricksters reached 34, so heroes outsped the endgame. Now
  endgame heroes land around 10–27 and late foes around 10–22.
- **Difficulty should be hard but winnable, and a person should do clearly better than the bot.**
  The owner found the game very easy, so it was calibrated against the synergy-minded autopilot
  (`bot.js` plus threat-aware hero moves): about 20% wins at ascent 0 (143 runs) and 5% at ascent 8.
  Normal fights are nearly always won (98%+); runs are decided by attrition and the bosses, which
  the bot passes about two times in three in every act. Before acts 2 and 3 were toughened, a party
  that reached act 3 won it 82% of the time. Measured and adjusted: act scaling, the Bog Hydra
  (softened; it ended twice as many runs as the Thornmother) and the Brass Colossus (toughened). The
  Hydra still ends more runs than the other bosses, partly because the bot doesn't prioritise its
  heads the way a person would.

- **Phones are a first-class target for combat.** Below 920px the battle's action bar (skills,
  Confirm, End turn, hint) is pinned to the bottom of the screen (`body.in-battle`), the HUD uses
  short labels, the board scrolls back into view at the start of a hero's turn, a drag on the board
  isn't a tap, and a long press only inspects. Confirm names its outcome ("Confirm: Slime −12"), a
  skill with one possible target aims at it straight away, and the HUD's speed button (1×–3×,
  saved in `localStorage`) scales every animation through `env.speed`.

- **Every status explains itself.** Statuses in the battle panel and status words in skill text
  ("Slows", "Shocks") are tooltips: hover with a mouse, tap on a phone (a tap on one inside a
  card shows the tip instead of pressing the card). The text lives in `STATUS_HELP` in `data.js`,
  and `STATUS_WORDS` maps skill-text words to it. A new status, or a change to what one does,
  updates `STATUS_HELP` too; a new status word in `describe()` gets a `STATUS_WORDS` entry.

## Testing

`node tools/threefold-autoplay.js [runs] [--chaos] [--asc N] [--par K] [--json FILE]` plays whole
runs headlessly with the heroes on autopilot and fails on any page error. Its header comment explains
how to supply Phaser when the browser can't reach cdnjs. `--par 6` plays six runs at once (the cloud
box has 4 cores; about 2 runs a minute), and `--json` logs each run's result and final build.
`node tools/threefold-balance.js FILE` then prints win rates by ascent, where runs end, and the act-3
win rate of runs holding each class line, team artifact and artifact (artifacts are what the party
ended with, so comparing within runs that reached act 3 evens out "found late"; it still needs
100+ runs before single artifacts mean much).

- `?auto` in the URL makes the heroes use the enemy AI and makes every menu choose for itself
  through `bot.js` (synergy-minded picks; see its header). Autopilot heroes also weigh how much foes
  could hit them on each tile (`threatMap` in battle.js), scaled by how hurt they are. They drop
  that caution once the foe rages, or they can stall forever against foes that can't move.
  It runs at 1/100 speed for animation waits and sets `window.__result` and `window.__log`.
- `&chaos` starts every hero promoted with four random skills and full artifact slots, to stress
  the odd mechanics.
- For a quick syntax check use `node --experimental-default-type=module --check js/<file>.js`. Plain
  `node --check` parses the files as CommonJS and misses errors that stop the game loading.
- Run a few `--chaos` runs after mechanic changes, and about 10 normal runs after balance changes.
  Then check a real click-through in a browser: autopilot skips the player-control code (move,
  undo, skill buttons, confirm).

## Gotchas

- Acts are looked up by id: `ACT_SLOTS` lists the two choices per slot, `run.acts` holds the ids
  drawn for this run, and `curAct()` in `main.js` resolves the current one (saves from before
  alternative acts have no `run.acts` and get the first of each slot). Never index `ACTS` by number.
- Enemy mechanics are flags on `FOES` copied onto the unit in `foeUnit`: `split`, `burst`,
  `rampart`, `items`, `stealth`, `swim`, `heads`, `chill`, `plating`, `overdrive`. Death effects
  (split, burst, returning stolen `loot`) live in `ko()`; turn-start ones (plating, overdrive,
  chill) in `startTurn()`. Swimmers pay 2 to enter water and can stand in it.
- Summoning stops at 3 of a kind on a side (`scoreAction`), which is what keeps the Hydra's
  regrowing heads in check.

- **Every module URL carries `?v=N`, and they must all match.** Cloudflare caches `/static`, and a
  module loaded under two URLs runs twice. When changing any JS, bump `?v=` together in every
  `import` line in `js/`, the `main.js` script tag in `index.html`, and the `game.css` link.
  `grep -rn "?v=" app/static/games/threefold` finds them.
- **Bump `SAVE_KEY` in `main.js`** when the run or hero format changes. Old saves are then ignored
  instead of crashing the new code.
- **Hidden canvas.** `#stage` (the canvas and side panel) is `display: none` while an HTML screen
  shows. When it reappears, `showStage` must call `game.scale.getParentBounds()` before
  `game.scale.refresh()`, or Phaser leaves the canvas 0px wide and the screen goes black.
- **Scenes restart.** `showStage`, `setScreen` and `game.scene.start` stop and start the `map` and
  `battle` scenes on every transition. Battle state is the module-level `B` in `battle.js`. The
  turn loop checks `B === b` after every await, because a battle can end mid-animation. Tween
  promises never resolve if their scene stops, so never await them after the battle has ended.
- **Speed.** Animation waits go through `sleep` and `tw`/`counter`, which scale by `env.speed`
  (0.01 under autopilot). Use them rather than raw `setTimeout` or tweens, or the autopilot slows
  to a crawl.
- **Audio rules:**
  - Browsers start audio only after a tap; `audio.js` resumes its context on any tap.
  - iPhones mute web audio with the silent switch unless `navigator.audioSession.type = 'playback'`.
  - Render at 44.1 kHz; older Safari rejects lower offline rates.
  - **Phaser's sound manager is off** (`audio: { noAudio: true }`). `audio.js` plays the rendered
    buffers on its own `AudioContext`, because iOS Safari, after the page has been in the background,
    can leave a context "interrupted" or "running" but silent, and resuming it doesn't help. So: on
    hide, stop the music and suspend; on return, try to resume (enough on desktop); and on iOS, the
    first tap after returning closes the old context, makes a new one and restarts the music.
    AudioBuffers aren't tied to a context, so nothing re-renders. Chromium shows none of this, so
    test audio changes on an iPhone.
  - Buffers are normalized after rendering, so a new sound's synth `vol` only sets its internal
    balance, not its loudness.
- **Check class passives with `isClass(u, id)`**, never `u.promo === id`: a tier-2 hero keeps
  their tier-1 passive. Foes have `line: []`.
- **Status vocabulary** (all on `u.st`, counted down in `endTurn` unless noted): poison, burn,
  slow, stun, blind, vuln, shock, doom (counts down at turn start), sleep (skips turns, ends when
  hit), confuse, root (no movement), disarm (no skills), weak (−30% damage), oil (fire ignites it),
  wet (lightning or frost on a wet target stuns it), focus (next damaging skill +60%), ward, guard,
  rally, movUp, imbue (hits add `imbueKind`), thorns, stealth, airborne. `DEBUFFS` and `BUFFS` in
  `battle.js` drive purify, dispel, Ruin Touch and Viral; add new statuses there too.
- **Odd skill machinery** in `useSkill`:
  - `delay`: the skill charges and goes off at the start of the caster's next turn (`u.pending`,
    drawn as pulsing tiles). Use `tgt: 'tile'` so it has somewhere to land.
  - `mimic`: `effective(u, s)` swaps in the last skill the caster's side used (`B.lastCast`). Call
    `effective`, not `skStats`, wherever a skill is about to be targeted or used.
  - `shape: 'coin'`: every foe or every ally, decided by `B.coin` when it's used.
  - `trap`: plants on the empty tiles of the area (`B.traps`), sprung in `enterTile` by the other
    side. The AI never lays traps.
  - Hero summons (`kind: 'summon'`) spawn allied foe units; `decoy` has `lure`, which the AI loves
    to hit.
- **Charm flips `u.side`.** The original is kept in `u.origSide` and restored when the charm ends or
  the unit dies. `checkEnd` counts `homeSide(u)` (which also sees through confusion's temporary `'mad'` side), so charming the last foe doesn't win the
  battle. Anything new that asks "is this a foe?" for bookkeeping (kills, rewards) should do the same.
  A unit that snaps out of a charm can't be charmed again for 2 turns (`st.resolve`), and the AI
  won't charm the last foe standing; without both, a hero with no cooldowns could stall forever.
- **Thorns** are computed, not stored: `thornsOf(u)` (class, items, the `st.thorns` buff), raised
  by `thornsNow` in `battle.js`: +50% while shielded (Spiked Bulwark), and doubled for the Briar
  Knight while shielded or bracing. They fire inside `damage()` for melee hits (any range with the Retribution Idol),
  with `reflected` set so they can't bounce. The thorns archetype is about toughness (DEF, max HP,
  shields, taunts, bracing), not brambles: the owner removed the bramble synergies, so don't add
  terrain payoffs back to it.
- **`shape: 'math'`** skills target every unit matching `rule` anywhere on the board (prime HP, even
  HP, row + column divisible by 3, poisoned). They're `tgt: 'self'` with no area tiles.
- **Silence (`cdLock`) only locks skills whose base cooldown is above 0**, so a silenced unit can
  always basic-attack. Don't lock cooldown-0 skills or units with one skill stop acting.
- **Skill artifact cards list what they fit** (`fitsLine` in `main.js`): the party's skills that
  `canSocket` accepts, counting full skills as if one slot were free.
- **IDs must stay distinct between `MODS` and `ITEMS`.** Pack entries are bare ids, and
  `isSkillArt(id)` tells them apart by looking in `MODS`. An id in both breaks the pack. Skill ids
  live in a separate namespace (`SKILLS`).
- **A skill artifact's `ok(o)`** sees the skill as already modified by earlier artifacts. Use
  `group` for mutually exclusive effects (two stat swaps, two shapes). `only` ties an artifact to
  one skill.
- **`burnOf`, `poisonOf` and `itemMult` in `rules.js` mirror `applyStatus` and `dmgMult` in
  `battle.js`.** Change a burn or poison formula, or add an always-on damage artifact, in both
  places or the previews lie.
- **Board overlays are regions.** Draw tile highlights with `region()` in `BattleScene.update`
  (fill every tile, outline only the region's outer edge) in the soft palette there; per-tile
  outlines double up where tiles touch.
- **Line of sight** applies to ranged skills unless they have `lob`. `describe` prints "Needs line of
  sight" from the same rule (`needsLos` in `battle.js`); keep the two in step.
- **Sprite rows must be exactly 16 characters** (8 for icons), with `.` for transparent. A
  wrong-length row draws garbage silently. Recolors reuse rows through `recolor()`.
- **`skStats` is called constantly**, by the AI (every reachable tile × skill × target) and by
  preview drawing every frame. Keep it cheap and side-effect free.
- **The AI is shared:** enemies, allied summons and autopilot heroes all use `planAI`. A new skill
  flag that should matter to the AI needs a term in `scoreAction`.
