# Dragonborn: a class proposal (for review, not built)

A draft class for the owner to review before anything is built. It's built around **Scales**, which
carry over between fights, but only about half of its picks touch Scales. The rest are plain dragon:
claws, wings, a tail, a roar, a hoard. Numbers are first guesses, sized with the tests in
`saltbound-skills.md`, and get measured once it's in, as the Spellblade's and Emberknight's were.

## Why Scales carry over

Fights are short. In the last 400 Hard runs (2026-11-05) a roaming fight lasted 3.0 rounds, a
dungeon fight 2.9, an event fight 3.9, and only bosses went longer (5.5). Enemies spread their hits
over three heroes and the summons, so a Dragonborn takes about one hit a round. A stack that started
empty each fight would reach 2 or 3 by the time the fight was all but over.

So Scales **stay on the hero between fights**, and the big decision moves to the map: "I'm carrying 5
Scales. Breathe on this roaming pack, or save them for the dungeon?"

## The mechanic

> Every hit that lands on the Dragonborn grows a **Scale** (up to 5). At the start of each round it
> gains **1 Armor per Scale**. **Breath** sheds every Scale: every enemy takes the die +2 per Scale.
> Scales stay between fights; only shedding them (Breath and the picks that say so) clears them, and
> being knocked down loses half (rounded up).

- **Shown as**: five scale pips on the hero card, in fights and on the map.
- **A hit that lands**: any enemy hit that reaches the Dragonborn, even if Armor stops all of it. Burn,
  Poison and other ticks don't count.
- **Knocked down**: loses half the stack (rounded up: 5 becomes 2), so a stack is never "free"
  protection, without wiping out several fights' building.

Why it fits the game:

- **A choice at two scales.** In a fight: shed now for the area hit, or keep the Armor for another
  round. On the map: which fight is worth the stack.
- **It opens fights.** With Scales carried in, Breath's biggest hit comes in round one, when it's
  worth the most, instead of in round three, after the fight is decided.
- **Nothing to track off the hero.** Enemies build the stack, and Breath clears it.
- **Nothing erased.** Scales arrive as hits land, and their Armor comes at the start of the round,
  when nothing clears it.

**Tags**: *Wrath* (dealing damage) and *Hide* (protecting itself and the party).

## The frame

| | |
|---|---|
| Role | Bruiser: sturdy, with area damage in bursts |
| HP | 34 (+4 a level): between the Duelist (31) and the Vanguard (46) |
| Base dice | d8 and d6, plain |
| Start | Claw, Breath |
| Weapon | **Talon Gauntlets** (new common, d6): Slash (deal the die +1) |
| Armor | Hide Vest (existing) |
| Map ability | **Dragon's Rest** (below) |

Claw is the free basic, so it can take every die a round. Everything else waits at least a round,
as for every class.

## Starting kit

| Action | Dice | Text | Notes |
|---|---|---|---|
| **Claw** (basic) | 1 | Deal the die +2. Crit: Poison 1 (the wound festers). | Strike's numbers; the crit is the class's flavour. |
| **Breath** | 1 | Any row: shed all your Scales; every enemy takes the die +2 per Scale. | cd 2. A full stack with a d6: 13.5 to every enemy. |

## Level-up pool

Scale picks are marked **S**. Eight of the eighteen.

### Wrath (dealing damage)

| Pick | Kind | Text | S | Why it's not a copy of something |
|---|---|---|---|---|
| **Tail Sweep** | melee, 1 die, cd 2 | Hit every front-row enemy for the die +1. | | The class's every-fight area option, Scales or not. |
| **Sky Dive** | 1 die, cd 2 | Any row: deal the die +3. If the enemy is in the back row, it's Weak this round. | | A melee class reaching the back row by wing, not by spell. |
| **Rending Bite** | melee, 1 die, cd 2 | Deal the die +2 and Poison 2. If it kills, heal the die. | | Damage over time and sustain, for a class without a healer's dice. |
| **Focused Breath** | 1 die, cd 2 | Any row: shed up to 3 Scales; one enemy takes the die +4 per Scale. | S | The single-target vent, for when Breath's spread is wasted. |
| **Searing Breath** | passive | Breath also Burns every enemy for 1 per Scale shed. | S | Makes a full stack linger: Burn 5 on everything is about 15 more damage to each over the rounds after. |
| **Wyrmfire Claws** | passive | Every Claw Burns 1; a crit Burns 3 as well as Poisoning. | | A basic upgrade (the doc's strongest kind of pick): fire on every swing. |
| **Hoard's Gleam** | passive | +1 damage on every hit per 60 gold you carry (up to +3). | | The dragon's hoard: a reason to keep gold, not spend it. |
| **Ancestral Fury** | passive | When Breath sheds 5 Scales, your next hit this round deals double. | S | The payoff for waiting for a full stack. |
| **Dragon's Wrath** | capstone | Breath sheds only half your Scales (rounded down), and every enemy takes the full amount anyway. | S | Breathe every fight without starting over. |

### Hide (protecting itself and the party)

| Pick | Kind | Text | S | Why it's not a copy of something |
|---|---|---|---|---|
| **Draconic Roar** | 1 die, cd 3 | Every enemy is Weak this round; on 5+, for 2 rounds. | | Party-wide protection by fear, not Armor. |
| **Dread Gaze** | 1 die, cd 2 | An enemy's attack this round turns on you instead, and it deals the die less. | | A Taunt for one enemy, with a cost to it. |
| **Wing Buffet** | 1 die, cd 2 | Every front-row enemy's attack this round deals half the die less. | | Spread protection that doesn't move anyone or cancel anything. |
| **Wing Guard** | 1 die, cd 2 | Gain the die as Armor, and take the next attack aimed at an ally. If it lands, you grow 2 Scales. | S | Guard that feeds the stack: the class's tank play. |
| **Molt** | 1 die | Shed one Scale to heal the die +3. | S | Spending a Scale for HP instead of damage. |
| **Brood Bond** | 1 die, ally | Give an ally 2 of your Scales for the fight: they gain 2 Armor at the start of each round. | S | The class's link to the party. |
| **Thick Hide** | passive | At the start of each fight, grow a Scale if you have fewer than 3. | S | A fresh Dragonborn never starts from nothing. |
| **Ancient Blood** | passive | Once per fight, the first time you drop below half HP, heal 6. | | Sustain in the dragon's way. Small, as the doc asks of "don't die" effects. |
| **Draconic Ascension** | capstone | Once per fight, below half HP: unfurl for the rest of the fight, +3 on every hit and 4 Armor each round. | | The last-stand finale, triggered by the fight, not by Scales. |

### Upgrades

Learning an action twice upgrades it as usual (+2 to every amount): Breath+ is the die +2 more,
then +2 per Scale; Focused Breath+ +4 per Scale and +2.

## Map ability: Dragon's Rest

> Resting grows a Scale (2 at a camp or in a town).

It works through `on_rest`, stays generic, and fits the carry-over: a Dragonborn that rests before a
dungeon walks in with a bigger stack, and one that breathed in the last fight can rebuild without
taking hits. (It replaced the draft's Hoarded Fury, a free first round with a full stack, at the
owner's request.)

## Checks against the skills doc

- **The basic test**: each action is checked against the same die on Claw. Each does something no
  number of Claws can: spread (Breath, Tail Sweep), reach (Sky Dive, Focused Breath), protect (Roar,
  Gaze, Buffet, Wing Guard), heal (Molt, Rending Bite), or give (Brood Bond).
- **No basic played twice**: no multi-die actions.
- **No pair or straight requirements**.
- **Risky actions pay**: Draconic Roar's 5+ only lengthens it; nothing does nothing on a miss.
- **Nothing erased**: Scales' Armor at round start; Wing Buffet and Dread Gaze act on this round's
  attacks, before they land.
- **Defence that grows with hits** (the doc's strongest kind of thing): the cap of 5, Armor once a
  round rather than a cut on every hit, and losing the stack when knocked down keep it in check.
- **No extra dice and no Stuns**. Dread Gaze and Wing Buffet blunt attacks without cancelling them.

## What it needs in the engine

- **Scales on the hero** (`hero["scales"]`, not the fight state, so they carry over), grown in
  `hurt_hero` and cleared on being knocked down.
- **Armor at round start** in `deal_dice` (Brood Bond's on the ally's fight state).
- **Ops**: `shed` (all, or up to n, with the shed count in the amount as `shed`), and an amount
  variable `scales`; a `shove`-free design, so no new targeting.
- **Mods** in `mods.py`: `searing_breath`, `wyrmfire`, `hoard_gleam`, `ancestral_fury`, `dragons_wrath`,
  `thick_hide_s`, `ancient_blood`, `ascension`.
- **Map key** `dragons_rest` in `Game.rest`.
- **Bots**: Scales' worth in `bot.evaluate`: a full stack is worth keeping in a small fight and
  spending in a big one (enemy HP left against the Breath's total), and on the map, no change.
- **Client**: the scale pips on the hero card and map tooltip, SHORT lines, skill effects, the sprite
  the owner picks (below), and Talon Gauntlets art.

## Risks

- **A Dragonborn that never breathes** is 5 Armor every round of every fight, close to the Vanguard's
  Shieldwall (6 Armor once a fight) but lasting. The balance run checks that saving doesn't beat
  spending; if it does, Scales could give Armor only while you hold 3 or fewer.
- **Hoard's Gleam** reads the hero's gold, which the bots barely spend; it may look better in the sims
  than in play.
- **Brood Bond** lasts the fight on an ally, so it's worth more in long fights (bosses) than short ones.

## Looks

Four options in `tools/saltbound-art/heroes2.py` (`OPTIONS["dragonborn"]`), kept out of `sprites.js`
until the class is built (`REVIEW` in `build.py`):

1. **Red Wyrmkin** (scaled): red scales, swept-back horns, a pale belly, a leather harness, bare claws, a tail.
2. **Bronze Drake** (scaled): bronze scales and a frill, a green travelling cloak, a long spear, a tail.
3. **Dragon Knight** (armoured): dark green plate, a helm shaped like a dragon's head with horns, wing pauldrons, a sword.
4. **Wyrm Guard** (armoured): gold and teal scale mail, a helm crested with wings, a red shield with a dragon on it.

## Decided

- Knocked down loses half the Scales (rounded up), not all.
- Breath has the usual cooldown of 2.
- Hoarded Fury is replaced by Dragon's Rest.
- Searing Breath and Wyrmfire Claws are stronger than drafted (Burn 1 per Scale; Burn 1 on every Claw).

Still open: which look.
