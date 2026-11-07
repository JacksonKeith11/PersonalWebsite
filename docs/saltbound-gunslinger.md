# Gunslinger: the class's design

**Built (Nov 2026)** at the owner's request, with the Drifter look (option 1 of four: tan duster, cowboy hat,
a revolver drawn and a second in its holster). The live numbers are in `app/saltbound/classes.py` (the
Gunslinger block, `CYLINDER`, `COCKED`, `QUICK_DRAW`); the measured results are in `docs/saltbound.md`.

## The mechanic: the Cylinder

- The Gunslinger's revolver holds **6 rounds** (`x["ammo"]` on its fight state; Speed Loader: 8). It's full
  at the start of every fight.
- An action with `shot` fires rounds: 1, or `"all"` (Fan the Hammer, High Noon fire every round left). It
  can't be played on an empty cylinder (`Combat.do_place`; the bots skip it in `candidates`).
- **The Silver Round**: a one-round shot that fires the last round in the cylinder deals **double** on its
  main hit (`Actions.hit_base`; not on a hit with `to`, such as Ricochet Rounds' bounce). Lucky Chamber
  makes the third round silver too. `silver` in an amount is 1 for that shot, `ammo` the rounds left
  before it (rounds are spent after the shot lands, in `Combat.fire_rounds`).
- **Reload** (a die, any face) refills the cylinder (`_op_reload`). On a 1–3 it also cocks the hammer
  (`cocked`, a round-only status): the next shot this round deals +3. So a bad roll still does something.
- **Pistol Whip** (die +1, front row, no rounds) is the fallback for an empty cylinder.

The decision it makes: reload early and push the Silver Round back, or count the shots so the last one
lands on the boss or the big hitter. The count is shown as pips on the hero card; the next round glows
silver when it's the Silver Round.

**Quick Draw** (the map ability, `quick_draw`): when a fight it's in starts, the Gunslinger fires first:
the enemy with the biggest attack takes 6 (`Combat.quick_draw`; was 4).

## The kit

Dice d8 + d6, 29 HP (+4 a level; was 26 and +3). Starts with Fire, Reload, Pistol Whip, the Six-Shooter (Warning Shot:
any row, half the die, Weak this round) and the Padded Coat.

| | Quickdraw (the cylinder) | Trickshot (the aim) |
|---|---|---|
| Actions | Fan the Hammer (cd 2: every round left, the die +2 each, as one hit); Take Cover (cd 2: the die +2 Armor, load 2 rounds); Suppressing Fire (cd 3, 3 rounds: every enemy takes half the die, every attack −2); **High Noon** (capstone, once a fight: every round left, every enemy takes the die +1 per round) | Cover Fire (cd 2: the die; its attack −the die); Showdown (cd 2: the die +3; if it's aiming at you, Weak too); Trick Shot (cd 2: the die +2, and the die to an enemy in the other row); Disarming Shot (cd 3: the die; Weak, 2 rounds on 5+); Aces and Eights (cd 2: the die +3, ×3 on a 1 or an 8); Piercing Round (cd 2: the die +4 through Armor) |
| Passives | Speed Loader (8 rounds); Count Your Shots (+1 per round already fired, to +4); Dry Fire (Pistol Whip +4 on an empty cylinder); Hammer Back (Reload cocks on any roll, +5); Fresh Cartridge (a kill puts a round back); Two Guns (the Silver Round also hits another enemy for the die +3); Gunsmoke (Reload also gives the die as Armor) | Ricochet Rounds (Fire on an even die: 3 to another enemy); Silver Bullets (the Silver Round ignores Armor, Vulnerable 2); Long Barrel (+2 on ranged hits on the back row); Silver Lining (the Silver Round heals the most wounded 5); Finish the Job (+2 on enemies below half); **Lucky Chamber** (capstone: the third round is silver too) |

Crits: Fire puts a round back; Pistol Whip makes it Weak; Warning Shot makes it Vulnerable.

## Notes from building it

- **Keys**: the Khopesh already had a `disarm` action, so the Gunslinger's is `disarming_shot`; the Forked
  Staff has `ricochet`, so the passive is `ricochet_rounds` (its mod is `ricochet`).
- **Showdown** first doubled against an enemy aiming at the Gunslinger, which is the Duelist's Pinpoint; it
  makes the enemy Weak instead.
- **The bots** price each round a shot spends at `bot.ROUND_WORTH` (1.3, about a sixth of a die) and value
  Reload by the rounds it puts back (`reload_value`). The planner scores each die on the cylinder as it is
  now, so it never saw "Reload, then Fire" and Pistol Whipped an empty gun with two dice left:
  `bot.reload_first` reloads with the smallest die first in that case (not with Dry Fire, which makes the
  whip a fair play).
- **The second set** (owner's request): Suppressing Fire, Aces and Eights, Piercing Round, Two Guns, Gunsmoke,
  Silver Lining, Finish the Job. A first "Second Gun" (Pistol Whip reaches any row) had the bots whipping more
  than firing, so the cylinder stopped mattering: it became Two Guns.
- **Pistol Whip+** has its own upgrade (it loads a round): the usual melee upgrade, "reaches any row", made
  it the die +3 at any row with no rounds, a better Fire.
- `bot.ROUND_WORTH` was 1.3 at first; the bots then whipped with a full cylinder (Fire came out only 0.5
  ahead). A round fired also brings the Silver Round on, so it's 0.6.
- `tools/saltbound-check.py` refills the cylinder before each placement, since Fan the Hammer and High
  Noon empty it.

## Results

200 Normal runs with a Gunslinger in every party (path bots, seed 5000, 2026-11-07): 64.0% at 26 HP and
Quick Draw 4; **68.0% at 29 HP (+4 a level) and Quick Draw 6**. The all-class Normal batch had classes at
65-87%, so it sits in the lower middle. Pick numbers and the next steps are in `docs/saltbound.md`; after the seven
more picks, 400 Hard runs with a Gunslinger in every party: **53.8%** (the all-class Hard batch: 59.7%,
classes 53-69%).
