# Saltbound: balancing and designing skills

Read this with `docs/saltbound.md` before adding, reworking or tuning a level-up pick, a class's
starting kit, or anything that changes dice. It collects what the simulator has shown to be strong or
weak, what the owner has said makes a pick fun, and how to measure a change. The numbers behind it are
in "Balance now" in `docs/saltbound.md`; this is the distilled version.

## The goal

- **Hard is tuned to about 50% for the bots**, with no class far ahead (owner, Nov 2026, "for now").
  Normal is about 85–90%; Story nearly always wins. Leave the difficulty multipliers alone unless the
  owner asks: balance classes and picks instead.
- **The owner prefers picks that make you think over raw power.** When something is weak, rework it into
  a decision rather than adding a flat number; when something is strong, trim the thing that makes it
  strong rather than its whole identity.
- **The owner reviews balance changes**: give options and trade-offs before changing a class's basics or
  the difficulty.

## What tends to be powerful

From the pick studies (600 Hard runs per class in the first one, 400 in the Nov 2026 one) and the class
passes:

1. **Extra dice are the biggest lever in the game.** A sixth die (a second trinket slot) took Hard from
   about 37% to 51%; a support die for heroes outside a fight added about 17 points. Anything that hands
   out dice (Bloodlust's kill die, Steal Tempo, Anthem of Kings, Companion's hawk die, Splitting Flask)
   needs a tight trigger or a cost.
2. **Stuns and cancels on ordinary enemies.** A Stun deletes a whole attack. In Nov 2026 the five most
   over-performing picks all Stunned or cancelled: Lunge (+28 points vs passed), Earthshaker (+21),
   Concussion (+19), Cacophony (+18), Shield Bash (+15). Bosses are covered by **Steeled** (they act at
   least every other round), so the danger is roaming and dungeon fights. Keep Stuns on a hard roll (a 6,
   a shield face), a long cooldown (3), or a condition (Garrote: only if Poisoned), and never on a cheap,
   reliable action.
3. **Protection that scales with hits on everyone.** When the bosses started hitting the whole party,
   Vanguard parties won 80% against 33–45% for the rest: Armor, Guard and Taunt soaked every big
   party-wide hit. Party-wide Armor, damage reduction (Sanctuary, Hold the Line) and party heals grow
   with how much the enemies hit everyone.
4. **Defence that also feeds damage.** Strike adding half the Vanguard's Armor, with Armor carrying
   over, made the tank out-damage every class. A pick that converts one resource into another (Armor
   into damage, healing into Armor) needs a small ratio (a third) or a cost (Shield Throw spends what it
   throws).
5. **Passives and upgrades of the basic attack beat new actions.** They cost no die and no cooldown, and
   the basic is used every round. In the first study almost every clearly bad pick was an action and the
   good ones were passives and basic upgrades. In the Nov 2026 study actions averaged −3.7 points vs
   passed, passives +0.3 (part of that is the measuring bias below, part is real).
6. **Area damage, splash and spreading effects** add up quietly against the usual 3–5 enemies:
   Shrapnel's +3 splash (+14), Grand Curse (Hex on every enemy, +16), Earthshaker's damage half.
7. **Revives and "don't die" effects** are worth a lot because deaths are what lose runs. Lift is once
   until you rest, Quick Lift too, Unbreakable once per fight. A third revive source per fight (the
   rejected "Last Rites") would be too strong; Shared Burden makes the Mender pay half the hit.
8. **Starting HP beats HP per level**, since most Hard runs end around level 4–6.

## What tends to be weak

- **An action that does about what the free basic does, plus a cooldown.** The test: is it clearly
  better than putting the same dice on the class's basic attack (or on Block)? Twin Cut once dealt each
  die +2, which is just Riposte Cut twice, on a cooldown (−13). Called Shot dealt two dice's sum to a
  Marked enemy, less than two Shoots on that same enemy, each getting the Mark's +3 (−9). Drink Deep, Ward
  and Briar Wall were the same story.
- **An action that is just the basic played more than once.** "Two dice: hit once with each, and each
  hit carves a Sigil" is the basic twice on one card: the player gets nothing for using it except a
  cooldown, and loses the choice of splitting the hits between enemies. Before writing a multi-die or
  multi-hit action, write down what it does that **no sequence of the class's one-die actions can**:
  one hit big enough to break Armor, an effect that needs the sum or the dice's numbers together, a
  status that only lands from a combined hit, a verb no other action has. If the answer is "a bit more
  damage", it's a flat number on a card; make it a passive or an upgrade of the basic instead.
- **Requiring a pair (or a straight).** Dice are hidden until the action resolves, so the player can't
  pick two dice that match; a pair requirement is a lottery. Two d6 match 1 time in 6, a d6 and a d8 1
  in 8, a d8 and a d10 1 in 10, and an action that does nothing otherwise mostly sits unused. Pairs and
  straights belong in the amounts as a bonus on an action that's already worth playing (Renew, Twin Cut,
  Called Shot), never in the requirement. The one exception is a class that can see or steer the match
  (the Scoundrel's linked dice make Smoke Bomb's pair likely); without that, don't.
- **Multi-die actions**: they have to beat the sum of what each die would do alone, plus whatever bonus
  per hit (Mark, Pincer, Crescendo) they give up by being one hit. Budget about +3 to +4 per extra die.
- **Risky actions** (5+, 6+, a big sum, a pair) need to pay about a quarter more on average than a safe
  action with the same die, and a miss that does nothing needs more again. Misses scale with the risk:
  3+ to 5+ deals about half the die on a miss, 6+ and pairs deal nothing.
- **Effects at the end of the round that the round's own rules erase.** Armor clears at the end of the
  round, so Armor granted then does nothing (the rejected "Mana Ward"). Check when a new effect lands
  against what clears or ticks then (`end_round`, `deal_dice`).
- **Holding a die back for later** competes with spending it now on Block or the basic. "Leave a die
  unused for +2 later" loses to throwing it now; a banking reward has to beat that.
- **Map-only, gold or economy picks** (Haggler, Silver Voice, Sticky Fingers, Distiller) do nothing in
  the fights that decide runs, and the bots barely use the economy.
- **Durations (+1 round) and narrow immunities** (Calm, Long Mark, Malediction) rarely change a fight.

## What tends to be fun

The owner's directions, and what the reworks found:

- **Dice values matter, not just their sizes.** Slice & Dice and Dicey Dungeons are the models: a pick
  that cares what number came up gives every roll a story. Good patterns already in the game:
  - pairs and straights as bonuses (Finisher's straight, Twin Cut's pair, Renew's pair, Smoke Bomb);
  - **low rolls being good** (Doom: 26 minus the die; Short Fuse: a 1 or 2 bomb hits like an 8);
  - bad faces turned around (Heedless: the Berserker's skull counts as its top face, still hurting);
  - dice you can see and steer (Seer, Augur and Fate dice; Read the Blade; Second Opinion);
  - dice verbs: flip, split, graft, link, pass (Counterpoint, Splitting Flask, Grafting, Loaded Dice).
- **The order of play matters.** Spellweave (a different spell earlier this round), Call and Response
  (the Herald acts first), Pincer and Covered (an ally set it up), Acid Flask ("throw it before the big
  hits"). These give the party something to plan together on the voice call.
- **Target choice matters.** Engage (enemies at full health), Quarry (keep hitting the same one), Pass the
  Mark (the order of kills), Pinpoint and Riposte Cut (whoever is aiming at you), Stab (whoever isn't).
- **Cross-hero synergy.** Wildfire (Burn meets Poison), Shatter (Freeze), Fester (anyone's hits grow the
  Scoundrel's Poison), Catalyst (bombs Poison, so an ally's Burn erupts).
- **A miss or a bad moment still gives something.** Backlash Ward (a missed spell gives Armor), Bloom (a
  summon dying heals the party), Shared Burden.
- **Readable on one line.** Every action has a `SHORT` card line, every status a tooltip, and skill texts
  follow one style ("the die", "On 5+:", "Otherwise:", "Any row" first). If it can't be said in a line,
  it's probably too fiddly.
- **No lockdown, no waiting.** No boss can be locked down (Steeled), and no decision has a timer.

What the owner has called dull: a flat +N, a +1 duration, an immunity, a map-only or gold perk, an effect
that fires only when you're already losing (Undying Fury), a once-per-run effect you never see (Miracle),
and a bonus that repeats one the class already has (Backstab on top of Stab).

## Designing a new pick: the checklist

1. **The decision.** Say in one sentence what it makes the player do differently. If the answer is
   "nothing", it's a flat number.
2. **The Block and basic test.** Compare it with the same dice on Block and on the class's basic attack,
   over a typical round. A new action must clearly beat both in its situation; a new passive must matter
   in most fights. A two-die action is compared with the class's two best one-die plays, not one: name
   what it does that they can't (see "the basic played more than once" above). And check the requirement
   can come up: no pair or straight as a requirement, and a 6+ or big sum needs a payoff to match.
3. **Nothing erases it.** Check its timing against `end_round` and `deal_dice` (Armor clears, `inspire`
   resets, statuses tick).
4. **Overlap.** Search `classes.py`, `COMBOS` and the item passives in `content/items.py` for the same
   effect. Heroes have no rows (only enemies do), so nothing may move, place or protect allies by row.
   Pincer already rewards matching numbers; Stab already rewards enemies aiming elsewhere.
5. **Build it so the bots see it.** Damage rules go in `dmg_bonus` or `hit_base` in `actions.py` (the
   shared hit sums), never inline in `_op_dmg`. A face rule goes in `face_rules` (`dice.py`), `ROLL_MODS`
   (`tuning.py`) and `faceRules` (`js/rules.js`). An instant needs a value in `bot.instant_value`, and a
   status rider needs one in `bot.evaluate`. Bookkeeping about what was played (spells cast, bombs
   thrown, streaks) goes in `Combat.after_action`.
6. **The plumbing.** List each new mod in `mods.py`; put it in the class's `pool` with the tags of the
   pick it joins; give actions a `SHORT` line (and a basic, weapon or armor action a crit in `crits.py`: one effect
   in the class's flavour, never a Stun, said in a few words on the card); add pop-up labels for any new `fx("st", s=...)` to the
   label map in `combat.js`; bump the cache versions. Keep an old pick's definition when it leaves a
   pool, so saves load.
7. **Check it fires.** `python3 tools/saltbound-check.py` (every action and passive through real fights),
   `python3 tools/saltbound-sim.py 24 normal --saves --fast`, and for a rare trigger a scratch script
   that gives the class the pick from the start and counts it firing.

## Measuring

- **One balance batch at the end of a set of changes**: `python3 tools/saltbound-sim.py 300 hard
  --seed=5000 --report` (about 3 minutes). 300 runs pins the overall rate to about ±3 points and each
  class to about ±5.
- **A pick study** (only when the question is which picks matter): `--with=<class>` puts that class in
  every party; 400 Hard runs per class is about 3 minutes each, 30 minutes for all ten. Pool the `--json`
  outputs and compare each pick's **won if taken** with **won if passed** (runs offered it at the same
  moment that took something else).
- **The study's bias**: a run counts once per offer, and survival decides how many offers it gets, so
  picks usually taken early read low. In Nov 2026 actions averaged −3.7 points, passives +0.3, capstones
  +1.1. Judge a pick against its own kind. Records from one run aren't independent, so z-scores read
  high: the z spread was 2.15 where pure chance gives 1. Trust large effects over hundreds of takes, and
  treat upgrades (taken 10–70 times) as hints.
- **Bots shape the numbers.** A pick can look weak because the bot never plays it or misvalues it
  (healing was valued at 0.6–1.0 a point until Nov 2026; Eagle Eye, Pierce and Burn riders were once
  ignored). Before buffing, check the class's action table in `--report` for skills the bot rarely uses.
  The bots pick level-ups by kind plus seeded noise (`bot.level_score`), not by the fight they're in, so
  the comparison is close to a fair experiment.
- **Party behaviour moved Hard more than any pick**: bots that stayed together took Hard from 43% to 72%
  before the bosses were retuned. Treat old numbers from before a bot change as a different game.

## The Nov 2026 pass, for reference

- Replaced as dull: Arcane Shield, Overcharge, Malediction, Calm, Miracle, Footwork, Thick Skull, Undying
  Fury, Field Dressing, Long Mark, Sticky Fingers, Virulence, Backstab, Battle Hymn, Volatile, Deep
  Pockets, Verdant, Distiller. Their replacements are listed in "Balance now" in `docs/saltbound.md`.
- Trimmed as strong: Lunge (no Stun), Earthshaker (staggers instead of Stunning), Concussion and Shield
  Bash (Stun on a 6), Shrapnel.
- Buffed as weak: Twin Cut, Drink Deep, Second Opinion, Envenom, Ward, Called Shot, Briar Wall, Hymn of
  Valor.
- Still worth watching: Bloom, Reagents and Call and Response came out a little strong in their first
  study, Backlash Ward a little weak; Grand Curse and Cacophony are strong but belong to the two weakest
  classes (Arcanist, Herald).
