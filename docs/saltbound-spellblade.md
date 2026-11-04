# Spellblade: the class's design

**Built (Nov 2026).** The owner's review settled the open questions: Sigils stack to **5**, only the
Spellblade carves them, Frost stays Weak, Runewright gives no party Armor, and the class gets
**several ways to infuse** rather than one skill. What was built differs from the draft below in
those ways, and in these:

- **Elemental Infusion is a starting action** (Rune Cut, Sigil Burst, Elemental Infusion), so carving,
  bursting and infusing are all there from level 1.
- **Six ways to infuse**: Elemental Infusion; Charged Bolt (any row: the die +2 and Shock, and the next
  melee hit +3 and Shocks); Runic Ward (Armor, and the next melee hit +2 with Frost); Sigil Burst's crit
  (the next two melee hits); Feedback Loop (a Burst of 3+ Sigils); Spellstrike (every damaging spell
  infuses the next melee hit, +2). Infusions add up to 4 hits, keep the bigger bonus and take the newest
  element.
- **Glyph Feedback was dropped** (a flat Armor trickle), and Deep Etching went with the cap of 5.

The live numbers are in `app/saltbound/classes.py` and `docs/saltbound.md` (Classes); the balance
results are at the end of this file. The draft as reviewed follows.

## The fantasy and the loop

The Spellblade's blade cuts runes into its enemies, and its spells set them off. Its spells can
also be poured into the blade, so the next cuts carry fire, frost or lightning.

- **Carve** (blade to spell): melee hits carve **Sigils** onto the enemy hit. Sigil is a new enemy
  status that stacks to 3 and doesn't wear off. Shown as glowing runes on the enemy.
- **Burst** (spell): actions that say "Burst" spend every Sigil on the target for a bonus per Sigil.
  The other spells use Sigils without spending them.
- **Infuse** (spell to blade): spells that **infuse** the blade make your next melee hits this
  round hit harder and carry an element.

A typical round: carve two or three Sigils onto one enemy with Rune Cut, then Burst it from any
row. Or, on a round when Burst is cooling down, infuse the blade and cut. The decisions are which
enemy to carve, when to spend, and whether a die goes on carving, infusing or bursting. All of
them are "dice values matter" or "order of play" decisions, which the skills doc names as what's fun.

**Tags**: *Edge* (carving and infused melee) and *Sigil* (bursting, spells that use Sigils).

## The frame

| | |
|---|---|
| Role | Melee and spell damage: single target, with spread from Sigils |
| HP | 27 (+4 a level), between the Ranger (24) and the Warden (26) |
| Base dice | d8 and d6, plain. A rune face lives in a dice pick instead (Rune-Etched Blade) |
| Start | Rune Cut, Sigil Burst |
| Weapon | **Etched Sword** (new common, d6): Slash (deal the die +1). Melee, no carving: carving is the class's |
| Armor | Padded Coat (existing) |
| Map ability | **Runewright** (below) |

Rune Cut is the free basic: it has no cooldown, so it can take every die a round. Everything else
waits at least a round, as for every class.

## Starting kit

| Action | Dice | Text | Notes |
|---|---|---|---|
| **Rune Cut** (basic) | 1 | Deal the die +1 and carve 1 Sigil. Crit: carve 2 more. | Strike is the die +2; the Sigil is the point traded for. |
| **Sigil Burst** (spell) | 1 | Any row: deal the die +3 per Sigil on the enemy, then its Sigils are spent. | cd 2. On 3 Sigils, a d8 averages 13.5; Channel's two dice average about 13. |

## Level-up pool

### Edge (carving and infused melee)

| Pick | Kind | Text | Why it's not a copy of something |
|---|---|---|---|
| **Elemental Infusion** | spell, 1 die, cd 2 | Infuse your blade: your next two melee hits this round deal +half the die and carry an element by the number: 1–2 Frost (Weak), 3–4 Shock, 5–6 Burn 2. | Low rolls get the status, high rolls the damage: no roll is wasted. Frost is Weak, not Freeze: a reliable Freeze would cancel attacks. |
| **Hilt Rune** | melee, 1 die, 5+ | On 5+: deal the die +3 and carve 2. Otherwise: deal half the die and carve 1. | The only fast way past one Sigil per die. A miss still carves. |
| **Sunder Glyph** | melee, 1 die, cd 2 | Deal the die and double the enemy's Sigils (to the cap). | Doubling is a verb no other action has. |
| **Counter-Glyph** | 1 die | Gain the die as Armor. The next enemy to hit you this round gets 2 Sigils. | Defence that sets up the next Burst. It carves, so Guard dice can't go on it. |
| **Whetted Runes** | passive | Rune Cut deals +1 per Sigil already on the enemy. | Gives a reason to keep carving instead of bursting: a real choice each round. |
| **Infused Steel** | passive | An infused melee hit carves 1 more Sigil. | Links infusing and carving: an infused round sets up next round's Burst. |
| **Bladesong** | passive | A melee hit right after one of your spells, or a spell right after a melee hit, deals +2. | Rewards weaving. Spellweave wants two different spells; this wants alternation. |
| **Rune-Etched Blade** | dice pick | Your weapon's lowest face becomes a rune face: it counts as the die's top face and the action carves 1 Sigil. | A low roll becomes the best one. |
| **Covenant Edge** | capstone | Your infusions last the whole fight. A new one replaces the element. | Turns every melee hit into an elemental one for the rest of the fight. |

### Sigil (bursting and spells that use Sigils)

| Pick | Kind | Text | Why it's not a copy of something |
|---|---|---|---|
| **Arc Rune** | spell, 1 die, cd 2 | Any row: deal the die, and every enemy with Sigils takes 2 per Sigil. The Sigils stay. | The area option: spread Sigils with carving, then hit them all. |
| **Detonate** | spell, 1 die, cd 3 | Any row: Burst the enemy (the die +3 per Sigil, spent). Its neighbours each take the Sigils' share (+3 per Sigil) as well. | A big Burst that spills over. Kept apart from Arc Rune: one spends, one keeps. |
| **Runic Ward** | spell, 1 die | Gain the die +1 as Armor, plus 1 per Sigil on all enemies (at most +6). | Defence that grows with how far the setup has got. |
| **Brand** | spell, 1 die, 6+, cd 3 | Only on an enemy with 2+ Sigils. On 6+: Burst it, and it's Weak and Vulnerable for 2 rounds. Otherwise: nothing. | The risky payoff, paying for its miss. No Stun: Stuns on reliable actions are the doc's top warning. |
| **Feedback Loop** | passive | Bursting 3 or more Sigils infuses your blade, with the Burst's die setting the element and damage. | The class's loop in one rule: cut, burst, cut harder. |
| **Glyph Feedback** | passive | Each Sigil you spend gives you 1 Armor. | Defence from offence, at a small ratio, as the doc asks. |
| **Quiet Glyph** | passive | On a 1 or 2, a Burst counts each Sigil as +5. | Low rolls are good. |
| **Open Circuit** | passive | Allies' spells and bombs deal +2 per Sigil on their target, without spending them. | The cross-hero pick: the Arcanist and Alchemist cash in your carving. |
| **Runestorm** | capstone | Sigil Burst hits every enemy with Sigils, each for its own count. | The finale: carve the room, then set it all off. |

### Removed from earlier drafts, and why

- **Etched Flurry** (two dice, two carving hits): Rune Cut twice, on a cooldown.
- **Carve the Pair** (two matching dice): dice are hidden until they resolve, so it was a lottery.
- **Glyph Lunge** (melee that reaches the back row through Sigils): the class's own spells already
  reach any row and hit harder, so it lost to Sigil Burst every time.
- **Duality** (odd: spell, even: melee): it was fiddly to read and didn't push the loop.
- **Sympathetic Runes** (Sigils jump on a kill): too close to the Scoundrel's Pass the Mark.

## Map ability: Runewright

> Every fight, each enemy starts with 1 Sigil. After the Spellblade rests, the next fight starts them
> at 2 instead, and the party has 3 Armor in round one. Resting in a town makes that the next two fights.

It works through `on_combat_start` and `on_rest`, so it stays generic. With Open Circuit, the
whole party's spells and bombs use those starting Sigils too.

Risk: the first round becomes strong. Sigil Burst on 2 Sigils is the die +6, from any row, on the
first play. If that's too much, lower what each Sigil adds to Burst (+3 now), not Runewright.

## Checks against the skills doc

- **The basic test**: each action is checked against the same dice on Rune Cut. Two Rune Cuts give
  2 Sigils and the dice +2. Sigil Burst on those 2 Sigils is one die +6, from any row.
- **No basic played twice**: every action has something no number of Rune Cuts can do (spend, spread,
  double, infuse, armour, or a risky payoff).
- **No pair or straight requirements**.
- **Risky actions pay**: Hilt Rune (5+) carves even on a miss; Brand (6+) is a full Burst plus two
  statuses.
- **Nothing erased**: Sigils don't decay; infusion lasts the round it's cast in (Covenant Edge aside),
  so it can't be cast at the end of the round for nothing; Runewright's Armor is in round one.
- **No extra dice and no Stuns**: none of the picks hand out dice or Stun.

## What it needs in the engine

- **Status `sigil`**: stacks to 3 (5 is an option), doesn't decay. A tooltip, an icon on the enemy,
  and a label in `combat.js`.
- **Ops**: `carve` (adds Sigils, honouring the cap), `burst` (spends the target's Sigils into the
  damage), and an amount variable `sig` (the target's Sigils), for Arc Rune, Runic Ward and
  Whetted Runes.
- **Infusion state on the hero**: `x["infuse"] = {"n": hits, "dmg": v//2, "el": ...}`, used by
  melee `dmg` in `hit_base` or `dmg_bonus` so the bots see it, and cleared in `end_round`.
- **Mods** in `mods.py`: `whetted`, `infused_carve`, `bladesong`, `feedback_loop`, `glyph_armor`,
  `quiet_glyph`, `open_circuit`, `covenant`, `runestorm`.
- **Map key** `runewright`: in `on_combat_start` (starting Sigils and Armor) and `on_rest`
  (a counter of fights).
- **Crits** in `crits.py` for Rune Cut (carve 2 more) and the Etched Sword's Slash.
- **Bots**: Sigils' future value in `bot.evaluate`, about 2 per Sigil while Burst is ready within a
  round. Without it the bots never carve on purpose, and the sims would understate the class.
- **Client**: a portrait, the class's colour, the lobby card, SHORT lines for each action, and
  Etched Sword art.
- **Party size**: classes are unique within a party, so this makes 11 to pick from, with no other changes.

## Open questions for the owner

1. Should Sigils cap at 3 or 5? 3 keeps Burst readable; 5 makes Sunder Glyph and Whetted Runes bigger.
2. Should Sigils be the Spellblade's alone, or should allies be able to carve too (a generic item passive, say)?
3. Does Frost-as-Weak feel right, or should low rolls get a real Freeze at a cost (once per round)?
4. Should Runewright's party Armor stay, or is the starting Sigil enough?
