# Kingfall: work in progress (handoff)

Branch `claude/tender-archimedes-qf8a67` only. **Not on `main`: do not deploy until the skills work
below is finished and `tools/check-all.sh` passes.** Delete this file when done and fold what matters
into `docs/kingfall.md`.

The owner asked for two things:

1. Sword and staff attack animations must show the weapon really swinging (heroes were holding it
   awkwardly and thrusting it into their bodies).
2. Skills with cooldowns, shared across all weapons, chosen after each fight; at most two, swapping
   one out when over the limit.

## Done (in this commit)

- **Weapon poses fixed.** Cause: on the rig a weapon at angle 0 lies back along the arm, and attacks
  were written as if 0 pointed outward. `content/weapons.py` now has `sw(arm, blade)`, `off()` and
  `both()`, which take the blade's real direction (0 forward, 90 up, 180 back, -90 down); every hero
  attack for sword, greatsword, daggers, halberd and catalyst was rewritten with them (bow: only the
  special). Boss files `corvin`, `headsmen`, `mirror`, `king`: every `weapon=` of 30 or less had 180
  added (thrusts and raised blades now point the right way). Checked with `tools/kingfall-art/anim.py`
  strips; not yet seen in the running game. `alchemist.py` still has `weapon=0` / negative values that
  were not reviewed.
- **Skills, server data and Bonfire rules.** `content/skills.py`: eight skills (Ember Lance, Frost
  Nova, Judgement, Reaping Whirl, Phase Step, Rallying Cry, Litany of Mending, Stone Ward), `BASE`,
  `MAX_SKILLS = 2`, `offer()`. `room.py`: `Hero.skills` / `Hero.skill_offer`, both in `wire()` and in
  the checkpoint; three offered after every won fight; Bonfire message
  `{t: 'learn', h, i, at}` (`at` = slot to replace when full) or `{t: 'learn', h, skip: 1}`; reset in
  `start_run`. `content/__init__.py` `client()` sends `skills` and `max_skills`.

## Still to do

Server:
- `room.py` `resume()`: restore `h.skills` and `h.skill_offer` from the save (use `.get(..., [])`
  so old saves load).
- `fight.py`: add `use_skill(hid, msg, now)` (room.py already routes in-fight `{t: 'skill', h, sk,
  x, y, a}` to it; **it does not exist yet, so using a skill would raise**). It should: check the
  hero knows `sk` and its cooldown has passed (keep `fh.skill_ready = {}`, allow ~0.3 s slack);
  record `fh.skill_used[sk] = now`; apply instant effects (`empower` -> `fh.empowered`, `rally` ->
  `fh.vengeance` for the hero and allies within `radius`, `heal` -> `self.heal`, `ward` ->
  `fh.shield = max(fh.shield, ward)`); broadcast `{t: 'fx', k: 'skill', h, sk, x, y}`.
- `fight.py` `attack()`: handle `atk == 'skill'` with `msg['sk']`: only if used in the last ~3 s;
  return `(mult * skills.BASE / weapon base, poise, 'special')` so damage ignores the weapon. Apply the
  skill's `status` with `build_status` in `hit_boss`.

Browser (`app/static/games/kingfall/js/`):
- `input.js`: actions `skill1` (keys Z and 1; pad LT, so take button 6 out of `block`) and `skill2`
  (keys X and 2; pad d-pad).
- `hero.js` `LocalHero`: `this.skills` from `h.skills`, a cooldown timer per skill; from idle/run a
  press starts state `skill` (plays like an attack through `attackData()`/`checkHit`, kind
  `'skill:<id>'` so `strike()` sends `atk: 'skill', sk`); `blink` skills move at once and are
  invulnerable for `iframes`; send `{t: 'skill', ...}` when used. `an()` should report `k_<id>` and
  `heroPose` / `HeroView.drawSwing` should handle it (poses `cast` and `raise`; draw the shape in the
  skill's `col`).
- `fight.js`: on fx `skill`, a ring in the skill's colour and its name over the hero (for everyone).
- `ui.js` + `css/kingfall.css`: two skill chips on each local hero's HUD card, greyed with seconds left
  while cooling down.
- `main.js` Bonfire `panel()`: "Learn a skill" cards from `h.skill_offer` (name, text, cooldown);
  with two known, each card offers "Replace <skill>" for each slot; a "Pass" button; show known
  skills and their keys.

Then: `python3 tools/bump-version.py app/static/games/kingfall`, `tools/check-all.sh`, try it with
`?debug&boss=corvin`, update `docs/kingfall.md` ("How it plays now": weapons note on `sw()`, a Skills
section, controls), delete this file, and push to `main`.
