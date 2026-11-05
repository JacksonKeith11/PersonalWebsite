# Psion: a class proposal (for review, not built)

A draft class built on information: it sees its own dice and nudges them. For the owner to review
before anything is built. Numbers are first guesses, sized with the tests in `saltbound-skills.md`,
and get measured once it's in, as the Spellblade's, Emberknight's and Dragonborn's were.

## The mechanic

> The Psion's dice are rolled at the start of each round and **shown** while it plans (all of them
> Seer dice). Each round it has **Focus**: spending 1 turns one of its dice **up or down by 1**.
> It starts with **2 Focus** a round, **3 from level 3** and **4 from level 6**. Focus doesn't carry over.

- **Limits**: a die can't go below 1 or above its top face. Shield, skull and wild faces can't be
  nudged. A die that's already been played can't be nudged.
- **Shown as**: three Focus pips on the hero card, and small up and down arrows on each visible die
  in the tray.
- **Mind Link**: the Psion can spend Focus on an ally. 1 Focus **reveals** one of the ally's hidden
  dice (it's rolled now and shown, as a Seer die is), and each further Focus nudges it by 1. The ally
  sees the change in their own tray.

Why it fits the game:

- **It turns the weakest kind of action into the class's strength.** For every other class, "exactly
  6" or "a pair" is a lottery, because dice stay hidden until they resolve; the skills doc forbids
  pair requirements for that reason, except for "a class that can see or steer the match". The Psion
  is that class, so its kit is built from exact numbers, pairs and straights.
- **A puzzle every round.** "3, 5, 5: one Focus makes the 3 a 4 for a straight, or I keep the pair."
- **The fantasy is in the rules.** It knows what's coming and bends it.
- **Party play.** Mind Link is the voice-call class: "I'll make your d8 a 6 for the Lunge."
- **No extra dice and no Stuns.** Focus moves numbers by 1; it can't make value from nothing.

**Tags**: *Telepathy* (minds: allies' dice, enemies' intents) and *Telekinesis* (force: damage,
Armor, moving enemies).

## The frame

| | |
|---|---|
| Role | Precise damage and party support |
| HP | 22 (+3 a level): fragile, like the Arcanist (23) and the Mender (21) |
| Base dice | d6 and d6: dice the same size match more often, which suits pairs |
| Start | Mind Spike, Kinetic Shield, Mind Link |
| Weapon | **Focus Crystal** (new common, d6): Zap (any row: deal the die and Shock) |
| Armor | Wool Robe (existing) |
| Map ability | **Precognition** (below) |

Mind Spike is the free basic, so it can take every die a round. Everything else waits at least a
round, as for every class (Mind Link, which takes no die, is limited by Focus instead).

## Starting kit

| Action | Dice | Text | Notes |
|---|---|---|---|
| **Mind Spike** (basic) | 1 | Any row: deal the die. **On exactly 6, deal 12 instead.** | Any row in exchange for no +2. A 5 plus 1 Focus is a 12. |
| **Kinetic Shield** | 1 | Gain the die +2 as Armor. **On exactly 1, gain 8 instead.** | cd 2. Low rolls become a choice, not a waste. |
| **Mind Link** | no die | Spend 1 Focus: reveal one of an ally's hidden dice (rolled now and shown). Each further Focus nudges it by 1. | In the starting kit (owner's call), so the party play is there from level 1. |

## Level-up pool

### Telekinesis (exact numbers, force)

| Pick | Kind | Text | Why it's not a copy of something |
|---|---|---|---|
| **Mind Crush** | 2 dice, a pair, cd 2 | One enemy takes three times the pair's number. Otherwise: nothing. | A pair of 5s is 15 in one hit: the payoff only a class that steers can rely on. |
| **Psionic Storm** | 3 dice, a straight, cd 3 | Every enemy takes the highest die +4. Otherwise: nothing. | The area option; three dice in a row, which Focus makes reachable. |
| **Telekinetic Hurl** | 1 die, cd 2 | Any row: deal the die and drag the enemy to the front row. On exactly 1, it's thrown at another enemy: 6 to each. | Moves an enemy into melee reach; a 1 is a big hit. |
| **Gravity Well** | 1 die, cd 2 | Every back-row enemy is dragged to the front row and takes half the die. | Sets up the melee allies, all at once. |
| **Overclock** | passive | +1 Focus each round, but each Focus past your usual costs 1 HP. | More steering, paid in the class's scarcest thing. |
| **Resonant Pair** | passive | Playing a pair on any action gives 1 Focus back. | Rewards building pairs, and chains them. |
| **Kinetic Rebound** | passive | Kinetic Shield's Armor left at the end of the round hits the enemy that hit you hardest, once. | Defence that pays back, at a small ratio. |
| **Perfect Foresight** | capstone | Once per fight, set one of your dice to any number. | The finale: the exact 6, the pair, the straight, guaranteed once. |

### Telepathy (minds)

| Pick | Kind | Text | Why it's not a copy of something |
|---|---|---|---|
| **Read Intent** | no die, 1 Focus | An enemy rolls its intent's dice now; the party sees the exact numbers. | Information for everyone (Read the Blade does it for one hero's pick). |
| **Psychic Scream** | 1 die, cd 3 | Every enemy is Weak this round. On 5+, the one with the biggest intent is also Vulnerable. | Party-wide protection, with a set-up on top. |
| **Mind Fog** | 1 die, cd 2 | Any row: the enemy's attack this round deals the die less, and it can't crit. | Blunts one attack without cancelling it. |
| **Puppet Strings** | 2 dice, double 6s, cd 3 | The enemy's attack this round hits another enemy instead. Otherwise: deal half the sum. | A turned attack, gated behind two 6s (owner's call; the doc keeps cancels on hard rolls). If it's still too strong, cd 4 or three 6s. |
| **Empathic Link** | passive | Revealing an ally's die with Mind Link costs no Focus. | Makes the Psion the party's eyes. |
| **Shared Vision** | passive | Each ally's biggest die is a Seer die (rolled and shown while they plan). | Information on allies' rolls, every round. |
| **Calm Mind** | passive | If you end the round with Focus unspent, heal 2 per Focus left. | A reason not to spend it all: the doc's "a miss still gives something". |
| **Hive Mind** | capstone | Every ally gets 1 Focus of their own each round, for their own dice. | Spreads the mechanic to the party. |

### Upgrades

Learning an action twice upgrades it as usual (+2 to every amount): Mind Spike+ deals the die +2 (14
on a 6), Mind Crush+ three times the pair +2.

## Map ability: Precognition

> At events, each risky option shows its odds ("4+ on a d6 · 50%").

It works through `on_event`, stays generic, and fits the class: it sees outcomes before choosing.

## Checks against the skills doc

- **Pairs and straights as requirements**: allowed here only because the Psion sees its dice and can
  steer them; the doc's exception. They still pay as risky actions (Mind Crush three times the pair;
  Psionic Storm the highest die +4 to every enemy), and do nothing on a miss.
- **The basic test**: each action is checked against the same die on Mind Spike. Each does something
  no number of Mind Spikes can: spend a pair or a straight, move enemies, protect, turn an attack,
  share information.
- **No basic played twice**: the two- and three-die actions each need a pattern that no single die
  has.
- **Information as power**: the Herald's single Seer d4 and Deadeye are already strong. Focus (2, 3 at
  level 3, 4 at level 6) is the main dial to tune, and Shared Vision and Hive Mind need measuring most.
- **Nothing erased**: Focus is spent while planning; Calm Mind heals at the round's end; Kinetic
  Rebound's Armor is read before the end of the round clears it.
- **No extra dice and no Stuns**. Puppet Strings turns an attack on a hard roll (exactly 6) and a
  long cooldown; bosses are covered by Steeled.

## What it needs in the engine

- **Seer on all the Psion's dice** in `round_dice` (the `seer` die kind already exists).
- **Focus** on the hero's fight state (`x["focus"]`), refilled in `new_round` (2, +1 at levels 3 and 6).
- **A `nudge` message** (`{"t": "nudge", "die": id, "by": 1 or -1, "h": owner}`): checks Focus, the
  limits, and that the die is unplayed; for an ally's hidden die, Mind Link reveals it first (as
  `show_die` does for Seer dice).
- **Requirements**: `exact`, `pair` and `straight` exist already; the actions add amounts `pairv`
  (the pair's number) and `hi` (the highest die).
- **Ops**: `turn` (Puppet Strings: an enemy's attack retargeted to another enemy), `reveal`
  (Read Intent: an enemy's dice rolled now, as Spotter does).
- **Mods** in `mods.py`: `overclock`, `resonant_pair`, `kinetic_rebound`, `foresight`, `empathic_link`,
  `shared_vision`, `calm_mind`, `hive_mind`.
- **Map key** `precognition` in the event view.
- **Bots**: a small search over nudges: for each way to spend up to 3 Focus (a few dozen per hand),
  plan the hand as now and keep the best. Mind Link: try a reveal on each ally's biggest hidden die.
- **Client**: Focus pips, up and down arrows on visible dice (and on an ally's revealed die), the
  odds on event options, SHORT lines, skill effects, a sprite (four options to pick from) and Focus
  Crystal art.

## Open questions for the owner

Decided: Focus starts at 2 and grows (3 at level 3, 4 at level 6); Mind Link is in the starting kit;
Puppet Strings needs double 6s (three 6s if that's still too strong).

Still open: the look. Four options in `tools/saltbound-art/heroes2.py` (`OPTIONS["psion"]`), kept out
of `sprites.js` until the class is built (`REVIEW` in `build.py`):

1. **Robed Mystic**: deep blue robe, shaved head with a glowing third-eye mark, a crystal floating over the hand.
2. **Mind-Knight**: silver-blue plate, a smooth helm with a glowing visor band, a crystal blade.
3. **Floating Seer**: hooded in purple, hovering with no feet showing, glowing eyes, stones orbiting.
4. **Void Monk**: blindfolded, bare-armed with glowing wrapped hands, a halo of floating shards.
