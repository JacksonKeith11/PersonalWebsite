# Threefold Path (the game at /games/threefold-path)

Read this before changing anything in `app/static/games/` or `tools/threefold-autoplay.js`.

## What it is

A pixel-art tactical roguelike: a Warrior, Mage and Rogue climb three acts (Greenwood, Sunken
Crypt, Ember Peaks). Each act is a branching map of battles, elites, events and shops ending in a
boss. Battles are grid tactics on a 10×8 board, with speed-based turn order, terrain, flanking,
statuses and line of sight. Runs save to `localStorage`.

## Code map (`app/static/games/threefold/`)

The game is static files with no build step. `/games/threefold-path` serves `index.html`, which
loads Phaser 3.80.1 from cdnjs, then `js/main.js` as an ES module.

| File | Holds |
|---|---|
| `js/data.js` | All content: terrain, acts and encounters, `ARCHES` (archetypes), classes and skill pools, promotions (`PROMOS`, two tiers), `SKILLS`, `MODS` (skill artifacts), `ITEMS` (hero artifacts), `FOES`. Start here for content or balance changes. |
| `js/rules.js` | Pure rules shared by menus and battle: hero stats, `isClass`, `promoOptions`, `skStats` (a skill after its artifacts, the hero's artifacts and class passives), `thornsOf`, `describe`, `canSocket`, archetype-weighted reward pools, skill offers. |
| `js/battle.js` | `BattleScene` (Phaser drawing, tweens, particles), the turn loop, damage, statuses, movement, line of sight, terrain effects, the AI, and the battle side panel (HTML). |
| `js/main.js` | Run flow and every HTML screen: title, map side panel, rewards, equipping, learning skills, promotion, events, shop, party screen, saving, the Phaser game config. |
| `js/mapscene.js` | `MapScene`: the branching map, drawn and clickable. |
| `js/art.js` | Pixel art as text grids (16×16 sprites, 8×8 map icons) plus procedural tiles per theme, turned into canvases and Phaser textures. |
| `js/audio.js` | Every sound effect and music loop, synthesized at startup with `OfflineAudioContext` and played through Phaser's sound manager. |
| `js/ui.js` | DOM helpers `h()`, `sprImg()`, `bar()`. |
| `game.css` | Styling for the HTML screens and panels. |

Phaser only draws the map and the board. Everything text-heavy (menus, cards, the battle side
panel) is plain HTML in `#screen` and `#side`, so it stays crisp, accessible and phone-friendly.
Keep it that way.

## Design directives (agreed with the owner)

- **Healing is scarce; an act's attrition is the challenge.**
  - There's no healing after a fight. The fallen get up with 10% HP.
  - In-battle healing (Mend, lifesteal, overflow) can't restore wounds from earlier fights: it's
    capped at the HP the hero started the battle with (`u.cap`).
  - Inns heal 25% for 45g (40% in the shops just before a boss), and event heals are 10–25%.
  - A new act fully heals.
  - Don't add easy healing back.
- **No stalling.** After about 9 rounds (`CALM_TURNS` hero turns) foes gain +10% damage per round.
  This exists to stop "keep one enemy alive and heal in a corner".
- **Every hero promotes after each act boss**, choosing between two classes: a tier-1 class
  (`CLASSES.promos`) after Act 1, then a tier-2 master class (`PROMOS[t1].next`) after Act 2. That's
  6 + 12 classes. `p.line` lists a hero's classes and **all their passives stack**; `p.promo` is
  only the latest (sprite and title). Each class teaches a signature skill and adds 7–12 skills to
  the hero's pool.
- **Skill pools are deliberately maximalist.** The owner plays them and prunes what isn't fun, so
  prefer adding a strange skill over polishing a safe one. Removing a skill means deleting it from
  its pool (and from `SKILLS` if nothing else uses it). A pool naming a missing skill only fails at
  runtime, so grep for the id.
- **Skills come from class pools.** Heroes start with 3 (`CLASSES.start`) and learn from `pool`
  plus every class in their line, up to `MAX_SKILLS` = 4. Learning a fifth means forgetting one.
- **Archetypes give builds a direction.** Six tags in `ARCHES` (poison, elemental, shield, thorns,
  blood, time) sit on classes (`arch`) and artifacts (`tags`). `artifactPool` weights its order by
  how much of each archetype the party has (`partyArches`), so a build snowballs without being
  forced. Every archetype needs payoff artifacts that reward stacking it (detonate poison, damage vs
  shocked, scale with shield or thorns), not just more of the same status.
- **Classes and skills borrow from FFT, Tactics Ogre and Horizon's Gate** (Jump, Draw Out, Rampart,
  Arithmetician math targeting, Steal Heart, songs), reshaped to fit the grid and scarce healing.
- **Skill modifiers are artifacts, and artifacts are the main battle reward.**
  - Skill artifacts (`MODS`) socket into a skill (`MAX_MODS` = 2) and rewrite it: the stat it
    scales with, its targeting, its effect.
  - Hero artifacts (`ITEMS`) are worn (`MAX_RELICS` = 3) and change stats or add passives.
  - Unequipped ones wait in `run.stash`, the pack.
- **Upgrades should be strange.** New artifacts should change how a skill or hero plays, not just
  add numbers.
- **Show the numbers.** `describe(o, src)` prints the result next to the scaling ("75% MAG = 9"),
  including burn and poison per turn ("Burns 2 turns (30% MAG = 5/turn)"). Pass a source wherever a
  skill is described. Equipping an artifact shows what it changes: `outputOf` before → after for
  each skill, plus stat changes for hero artifacts (`wearPreview` in `main.js`).
- **Pixel art only, no image or audio files.** New sprites are 16×16 text grids in `art.js`; new
  sounds are synth recipes in `audio.js`.
- **Later acts scale harder** (`foeUnit`: +12% HP and +8% ATK/MAG per act on top of the per-level
  curve) to answer every hero promoting after each boss.
- **Difficulty should be hard but winnable.** The random-choice autopilot currently wins about 1 run
  in 6, losing mostly to bosses across all three acts. A person managing HP should do clearly
  better.

## Testing

`node tools/threefold-autoplay.js [runs] [--chaos]` plays whole runs headlessly with the heroes
on autopilot and fails on any page error. Its header comment explains how to supply Phaser when
the browser can't reach cdnjs.

- `?auto` in the URL makes the heroes use the enemy AI and makes every menu choose for itself.
  It runs at 1/100 speed for animation waits and sets `window.__result` and `window.__log`.
- `&chaos` starts every hero promoted with four random skills and full artifact slots, to stress
  the odd mechanics.
- Run a few `--chaos` runs after mechanic changes, and about 10 normal runs after balance changes.
  Then check a real click-through in a browser: autopilot skips the player-control code (move,
  undo, skill buttons, confirm).

## Gotchas

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
  - Browsers start audio only after a tap. Phaser unlocks on the first input, and `audio.js` also
    resumes the context on any tap.
  - iPhones mute web audio with the silent switch unless `navigator.audioSession.type = 'playback'`.
  - Render at 44.1 kHz; older Safari rejects lower offline rates.
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
- **Thorns** are computed, not stored: `thornsOf(u)` (class, items, the `st.thorns` buff), doubled
  in brambles for `thornproof` units by `thornsNow` in `battle.js`. They fire inside `damage()` for
  melee hits (any range with the Retribution Idol), with `reflected` set so they can't bounce.
- **`shape: 'math'`** skills target every unit matching `rule` anywhere on the board (prime HP, even
  HP, row + column divisible by 3, poisoned). They're `tgt: 'self'` with no area tiles.
- **Silence (`cdLock`) only locks skills whose base cooldown is above 0**, so a silenced unit can
  always basic-attack. Don't lock cooldown-0 skills or units with one skill stop acting.
- **IDs must stay distinct between `MODS` and `ITEMS`.** Pack entries are bare ids, and
  `isSkillArt(id)` tells them apart by looking in `MODS`. An id in both breaks the pack. Skill ids
  live in a separate namespace (`SKILLS`).
- **A skill artifact's `ok(o)`** sees the skill as already modified by earlier artifacts. Use
  `group` for mutually exclusive effects (two stat swaps, two shapes). `only` ties an artifact to
  one skill.
- **`burnOf`, `poisonOf` and `itemMult` in `rules.js` mirror `applyStatus` and `dmgMult` in
  `battle.js`.** Change a burn or poison formula, or add an always-on damage artifact, in both
  places or the previews lie.
- **Line of sight** applies to ranged skills unless they have `lob`. `describe` prints "Needs line of
  sight" from the same rule (`needsLos` in `battle.js`); keep the two in step.
- **Sprite rows must be exactly 16 characters** (8 for icons), with `.` for transparent. A
  wrong-length row draws garbage silently. Recolors reuse rows through `recolor()`.
- **`skStats` is called constantly**, by the AI (every reachable tile × skill × target) and by
  preview drawing every frame. Keep it cheap and side-effect free.
- **The AI is shared:** enemies, allied summons and autopilot heroes all use `planAI`. A new skill
  flag that should matter to the AI needs a term in `scoreAction`.
