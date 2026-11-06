# Emberknight: the class's design

**Built (Nov 2026).** The owner's review: +1 per 5 Heat, cooling by half, a flat 5 HP to overheat, and
Pass the Flame only empowering (made stronger than one +3 hit). The balance results are at the end;
the live numbers are in `app/saltbound/classes.py` and `docs/saltbound.md` (Classes). What was
built differs from the draft below in these ways:

- **Overheat at 25, not 20** (see the results): the gauge, Heart of the Forge and the tooltips say 25.
- **Pass the Flame**: give an ally 5 of your Heat; their next **two** hits this round deal **+4 and half
  the die**, and each Burns 2. Its die adds no Heat (nor does Quench's).
- **Tuning pass**: Stoke deals the full die (was half); Backdraft cools in 2 rounds (was 3) and blunts
  the attack by a quarter of the Heat (was a sixth); Wildfire Core Burns a fifth of the Heat spent, at
  most 3 (was a quarter); Heart of the Forge is +5 (was +6).

The draft as reviewed follows.

## The mechanic

> Every die the Emberknight plays adds its rolled number to its **Heat**. Its hits deal **+1 for
> every 5 Heat**. If Heat reaches **20**, it **overheats**: it takes 5 damage and Heat drops to 10.
> At the end of each round, Heat cools by half.

- **When Heat is added**: after the action resolves, so a hit uses the Heat from before its own die.
  "I'm at 14; this hit gets +2, and its die decides whether I'm at +3 or overheating."
- **Shown as**: a gauge on the hero's card, marked at 5, 10, 15 and 20, with the current bonus
  beside it ("Heat 14 · +2").
- **Starts at 0** each fight (Banked Coals aside), and isn't shared: other heroes have no Heat.

Why it fits the game:

- **The number on the die counts twice.** A high roll hits hard and heats you fast; a low roll is
  safe near the top. Every die is a small call, which is the doc's "dice values matter".
- **Nothing to track off the hero.** One number, three rules, no new statuses on enemies.
- **No extra dice.** Heat changes what the normal dice do, so it stays clear of the doc's biggest
  balance risk.
- **Cooling by half keeps it moving.** Heat can't be banked forever, so each round is a fresh climb,
  and venting it (Flashover and the Temper picks) at the right moment is the class's big decision.
- **The downside is always the player's own choice.** Only your own dice push you over 20. No enemy
  or ally action does, so nothing the player did is undone by someone else.

**Tags**: *Blaze* (running hot, hitting hard) and *Temper* (controlling the heat, protecting the
party with it).

## The frame

| | |
|---|---|
| Role | Damage: single target, with area from venting |
| HP | 28 (+4 a level): between the Warden (26) and the Duelist (31) |
| Base dice | d8 and d6, plain |
| Start | Searing Strike, Flashover |
| Weapon | **Ember Mace** (new common, d6): Slash (now a cooldown special: the die +3, overkill carries on). Its hits get the Heat bonus like any |
| Armor | Padded Coat (existing) |
| Map ability | **Banked Coals** (below) |

Searing Strike is the free basic, so it can take every die a round. Everything else waits at least a
round, as for every class.

## Starting kit

| Action | Dice | Text | Notes |
|---|---|---|---|
| **Searing Strike** (basic) | 1 | Deal the die +2. Crit: add 5 Heat. | Was the die +1 (the Heat bonus made up the gap with Strike); +2 since weapon actions got cooldowns (Nov 2026: the Emberknight fell to 27% on Hard without its mace as a free second attack). |
| **Flashover** | 1 | Any row: spend all your Heat; every enemy takes half of it, +the die. | cd 2. At 18 Heat with a d6: about 12 to every enemy, then you start cold. |

## Level-up pool

### Blaze (running hot)

| Pick | Kind | Text | Why it's not a copy of something |
|---|---|---|---|
| **Stoke** | 1 die, cd 2 | Add twice the die to your Heat, and deal half the die. | The fast climb: a set-up the basic can't do. A low roll is a safe stoke. |
| **Inferno Cleave** | melee, 1 die, cd 2 | Hit every front-row enemy for the die. The Heat bonus counts on each hit. | The area option that grows with Heat, unlike Flashover, which spends it. |
| **Meteor Fist** | melee, 1 die, 5+, cd 2 | On 5+: deal the die +4, and the Heat bonus counts twice. Otherwise: deal half the die. | The risky payoff for running hot. A miss still adds the die's Heat. |
| **Cinder Lance** | spell, 1 die | Any row: spend up to 10 Heat, and deal the die plus the Heat spent. | A controlled single-target vent, for when Flashover's spread is wasted. |
| **Molten Edge** | passive | At 15+ Heat, your hits also Burn 1. | Rewards holding near the top. |
| **Fan the Flames** | passive | Each kill adds 5 Heat. | Momentum through a fight; the doc's kill triggers stay small. |
| **Spark Gap** | passive | A die that rolls 1 or 2 adds 5 Heat instead of its number. | Low rolls are good. |
| **Redline** (reworked) | passive | Overheating still costs 5 HP, but your next hit this round deals double. | The draft removed the damage; now it turns the cost into a payoff instead. |
| **Bellows** | dice pick | Your weapon die explodes while your Heat is 10 or more. | A die that changes with the gauge. |
| **Wildfire Core** | capstone | Flashover also Burns every enemy for a quarter of the Heat spent. | Turns the big vent into lingering damage. |

### Temper (controlling the heat)

| Pick | Kind | Text | Why it's not a copy of something |
|---|---|---|---|
| **Quench** | 1 die | Lose Heat equal to twice the die, and gain that much Armor (no more than the Heat lost). | Cooling as defence: a high roll near the top is a big shield. |
| **Ember Ward** | 1 die, cd 2 | Gain the die as Armor. Enemies that hit you this round Burn for 1 per 5 Heat you have. | Defence that grows with Heat instead of spending it. |
| **Pass the Flame** | 1 die, ally | Give an ally 5 of your Heat: their next hit this round deals +3 and Burns 2. | The class's link to the party: cooling yourself by helping. |
| **Backdraft** | spell, 1 die, cd 3 | Spend half your Heat. The enemy with the biggest intent takes it, and that intent deals a third of it less. | A vent that blunts an attack without cancelling it (no Stun). |
| **Bank the Coals** | passive | Heat cools by a quarter at round end, not half. | Longer climbs; more overheat risk to manage. |
| **Pilot Light** (reworked) | passive | Overheating costs 2 HP, not 5, and Heat drops to 15, not 10. | The draft's "never overheat" removed the downside; this softens it instead. |
| **Heat Sink** | passive | When you overheat, every ally gains 5 Armor. | Overheating on purpose becomes a party play, but it still costs you 5 HP. |
| **Hearthfire** | passive | At round end, if your Heat is 10+, your most wounded ally heals 3. | A small reason for the party to want you hot. |
| **Heart of the Forge** | capstone | At 20 you don't overheat: you burn white for the rest of the round (+6 on every hit), then Heat drops to 0. | The finale: race to 20, cash in, start cold. |

### Upgrades

Learning an action twice upgrades it as usual (+2 to every amount). For the Heat amounts: Stoke+
adds twice the die +2, Quench+ cools and shields 2 more, and Cinder Lance+ can spend up to 12.

## Map ability: Banked Coals

> Each fight starts with Heat equal to twice the map turns since your last fight, up to 10.

It works through `on_combat_start` (a turn counter on the hero), stays generic, and rewards travel
without punishing anything. A party that fights every turn gets nothing from it; one crossing the
map arrives at the next fight at +2.

## Checks against the skills doc

- **The basic test**: each action is checked against the same die on Searing Strike, which already
  carries the Heat bonus. Each one does something no number of Searing Strikes can: climb fast
  (Stoke), spread (Inferno Cleave, Flashover), cool (Quench, Pass the Flame), aim a vent (Cinder Lance,
  Backdraft), or pay off a risk (Meteor Fist).
- **No basic played twice**: there are no multi-die actions at all.
- **No pair or straight requirements**.
- **Risky actions pay**: Meteor Fist (5+) doubles the Heat bonus and adds +4; a miss still heats you.
- **Nothing erased**: Heat cools at round end, after the round's hits; Ember Ward's Burn lands during
  the enemies' turn; Hearthfire heals at round end and nothing clears healing.
- **No downside removed outright**: Redline, Pilot Light and Heat Sink each keep a cost (the HP, or
  overheating at all); Heart of the Forge trades the overheat for Heat dropping to 0.
- **No extra dice and no Stuns**.

## What it needs in the engine

- **Heat on the hero's fight state** (`x["heat"]`), added after each action from its dice
  (`resolve_action`), with the overheat check there too.
- **The bonus** in `dmg_bonus` (`heat // 5`, Meteor Fist's double, Heart of the Forge's +6), so the
  bots see it.
- **Cooling** in `end_round`, plus Hearthfire's heal.
- **Ops**: `heat` (add or spend, with an amount) and an amount variable `heat` for Flashover, Cinder
  Lance, Quench and Backdraft.
- **Mods** in `mods.py`: `molten_edge`, `fan_flames`, `spark_gap`, `redline`, `bellows`, `wildfire_core`,
  `bank_coals`, `pilot_light`, `heat_sink`, `hearthfire`, `white_heat`.
- **Map key** `banked_coals` in `start_fight` (turns since the last fight).
- **Bots**: Heat's future worth in `bot.evaluate`: a die is worth less when it would overheat (5 HP)
  unless Redline, Heat Sink or Heart of the Forge make that good, and venting is worth more the
  closer Heat is to 20.
- **Client**: the gauge on the hero card, the overheat effect, SHORT lines, skill effects, a sprite,
  and Ember Mace art.

## Open questions for the owner

1. Should the Heat bonus be +1 per 5 Heat, or +1 per 4 (stronger, overheating matters more)?
2. Should cooling be half (as drafted), or a flat 5 a round (steadier, easier to plan)?
3. Should Pass the Flame give allies real Heat (a gauge of their own for the round), or just the one
   empowered hit as drafted?
4. Should overheating cost 5 HP flat, or scale with level so it still matters late?

## Balance results

**First batch** (2026-11-05, 400 Hard runs, seed 5000, an Emberknight in every party, overheat at 20):
**Hard 52.0%**, about 4 points under the batches before it. The class dealt the most damage of any
(41.8 a round) but took 4.2 a round, more than anyone but the Vanguard: a scratch count found the bots
overheating about **twice a fight** (10 HP). Picks vs passed: Wildfire Core +14, Heart of the Forge
+10; Backdraft -11; nothing else past 10.

**After the tuning pass** (same 400 runs; overheat at 25, about once a fight, and the changes above):
**Hard 56.2%**, level with the batches before the class. Damage 42.4 a round (still the most), taken
3.8. Flashover is its big play (13% of plays, 30 damage a use). No pick is past 10 points vs passed:
Quench +10, Redline +8, Heart of the Forge +6; Wildfire Core -9, Ember Ward -8, Stoke -7. Earlier
batches showed unchanged picks moving up to 15 points between runs, so these are within the noise.
