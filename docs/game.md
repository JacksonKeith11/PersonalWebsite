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
| `js/data.js` | All content: terrain, acts and encounters, classes and skill pools, promotions, `SKILLS`, `MODS` (skill artifacts), `ITEMS` (hero artifacts), `FOES`. Start here for content or balance changes. |
| `js/rules.js` | Pure rules shared by menus and battle: hero stats, `skStats` (a skill after its artifacts and the hero's artifacts), `describe`, `canSocket`, reward pools, skill offers. |
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
- **Skills come from class pools.** Heroes start with 3 (`CLASSES.start`) and learn from `pool`
  (promotions add their own), up to `MAX_SKILLS` = 4. Learning a fifth means forgetting one.
- **Skill modifiers are artifacts, and artifacts are the main battle reward.**
  - Skill artifacts (`MODS`) socket into a skill (`MAX_MODS` = 2) and rewrite it: the stat it
    scales with, its targeting, its effect.
  - Hero artifacts (`ITEMS`) are worn (`MAX_RELICS` = 3) and change stats or add passives.
  - Unequipped ones wait in `run.stash`, the pack.
- **Upgrades should be strange.** New artifacts should change how a skill or hero plays, not just
  add numbers.
- **Show the numbers.** `describe(o, src)` prints the result next to the scaling ("75% MAG = 9").
  Pass a source wherever a skill is described.
- **Pixel art only, no image or audio files.** New sprites are 16×16 text grids in `art.js`; new
  sounds are synth recipes in `audio.js`.
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
- **IDs must stay distinct between `MODS` and `ITEMS`.** Pack entries are bare ids, and
  `isSkillArt(id)` tells them apart by looking in `MODS`. An id in both breaks the pack. Skill ids
  live in a separate namespace (`SKILLS`).
- **A skill artifact's `ok(o)`** sees the skill as already modified by earlier artifacts. Use
  `group` for mutually exclusive effects (two stat swaps, two shapes). `only` ties an artifact to
  one skill.
- **Line of sight** applies to ranged skills unless they have `lob`. `describe` prints "Needs line of
  sight" from the same rule (`needsLos` in `battle.js`); keep the two in step.
- **Sprite rows must be exactly 16 characters** (8 for icons), with `.` for transparent. A
  wrong-length row draws garbage silently. Recolors reuse rows through `recolor()`.
- **`skStats` is called constantly**, by the AI (every reachable tile × skill × target) and by
  preview drawing every frame. Keep it cheap and side-effect free.
- **The AI is shared:** enemies, allied summons and autopilot heroes all use `planAI`. A new skill
  flag that should matter to the AI needs a term in `scoreAction`.
