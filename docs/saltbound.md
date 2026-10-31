# Saltbound (the planned game at /games/saltbound)

Read this before changing anything in `app/saltbound/`, `app/static/games/saltbound/`, or the
`tools/saltbound-*` scripts.

**Status: design only. Nothing is built yet.** This doc is the design the owner signed off on
after a long question-and-answer session. Build to it; when the build forces a change, update
this doc in the same commit. Once code exists, add a "Code map" and "Gotchas" section in the
style of `docs/brawl.md` and trim the planned sections below to match what was built.

## What it is

A co-op strategy RPG for 1-3 players in the browser, in the same genre as IronOak's *For The
King*: a party crosses a hex overworld, fights turn-based battles on a separate screen, shops in
towns and races a worsening world to a final boss. It is its own game, not a copy: own setting,
own combat system (dice you assign, not slot rolls), own names, own UI. Don't borrow For The
King's content, names, art or layouts.

The setting is the **Sinking Archipelago**: islands are going under, and the rising sea is the
run's clock. A run is one sitting of 60-90 minutes. Players are on a voice call, so there's no
chat.

## The owner's design answers

Keep to these. They came from the owner directly.

### Players and sessions

- **1-3 players online, always 3 heroes.** Rooms by code (Board Brawl's pattern). The host
  assigns unclaimed heroes to players present, so solo means one person runs all three. Balance
  is tuned only for a party of 3.
- **Bots are for testing only** (solo manual testing and the automated simulator), not for
  filling seats in real games.
- **A disconnected player is waited for.** The game pauses. The host can reassign that hero to
  someone still in the room, and can save and quit at any time.
- **No timer** on any decision.
- **Server is in charge** of all game state; the browser only sends intents and draws.
- **Saving** (for crashes, and for expansions later): autosave to SQLite after every resolved map
  turn and every combat round. Saves are JSON with a `version` field and one migration function
  per version bump; a save too old to migrate is rejected with a clear message, never loaded
  half-broken. Up to 5 saves per group (oldest overwritten), resumed from the lobby's saved-runs
  list with the room code. On resume, players claim the saved heroes.
- **No progress between runs.** Everything (all classes, items, events) is available from the
  first run.
- **Difficulty**, set by the host: Story, Normal, Hard. Changes enemy HP and damage, the revive
  pool size and how often the sea rises. Nothing structural.

### The world

- **Hex map, generated per run from a seed** (stored in the save, so a restored run is
  identical). About 30×22 hexes: three regions around a central peak. About 30 map turns per run.
- **Map turns are planned simultaneously.** Each player queues their hero's path, sees the other
  heroes' planned paths as ghost trails, and clicks Ready. When all three are ready, everyone
  moves at once. No timer.
- **Movement is a fixed 4 points per turn** (changed by class and gear), spent on terrain costs.
  Not rolled: you can't plan together around unknown numbers.

  | Terrain | Cost | Notes |
  |---|---|---|
  | Beach, grass, road | 1 | |
  | Forest, jungle | 2 | blocks sight |
  | Hills, rocks | 2 | |
  | Shallows | 2 on foot, 1 by skiff | open or closed by the tide |
  | Deep water | skiff only, 1 | |
  | Cliffs, peak | impassable except by path | |

- **The sea rises every 3 turns** (Story 4, Hard 2). The lowest band of hexes floods. Hexes about
  to flood are marked a full turn ahead. A hero on a hex as it floods either fights a sea
  encounter there (if one is generated) or is swept to the nearest dry hex and takes damage.
  Towns and side-quest sites can sink; the three objectives and the final peak can't.
- **Tides** replace day/night: every 4 turns the tide flips between low and high. Low tide opens
  sandbars and shallows; high tide closes them and makes sea encounters stronger. The current tide
  and turns until it changes always show in the top bar.
- **Skiffs**: each hero can buy or find their own at docks. Boarding or leaving costs 1 move.
  Not shared, so the party is free to split up.
- **Enemies are visible on the map** and roam a little each turn toward nearby heroes; you can walk
  around them. Plus fixed lairs that don't move.
- **On the map**: towns (shop, inn, quest board, docks), shrines (a temporary buff), events (text
  choices), wrecks (loot, the theme's chests), camps (rest), and the three objective dungeons. No
  sailing merchants in v1.
- **Regions and objectives**: clear all three objectives in any order to unlock the final boss.
  Towns also offer side quests.

  | Region | Enemies | Objective (dungeon, 3-4 fights) |
  |---|---|---|
  | Coral Shallows | drowned sailors, crabfolk, reef creatures | the Sunken Chapel |
  | Smugglers' Keys | pirates and a tide cult | the Black Fort |
  | Stormcrag | storm elementals, harpies, mountain beasts | the Lighthouse |
  | Central peak | | **The Drowned Crown**, the tide-king raising the sea; fought on the last dry peak |

### Combat

- **Starting a fight**: walking into an enemy starts a fight. Every hero within 1 hex of that
  hex joins, and so does every enemy within 1 hex. Moving together is how you team up.
- **Rows**: two per side, front and back. At most 5 enemies (3 front, 2 back), 3 heroes. Melee
  can only hit the front row unless it's empty. Back-row heroes take less damage from melee, but
  some actions need the front. Moving rows costs a die (some skills make it free).
- **Dice**: each hero has 2 base dice from their class plus one die each from weapon, armor and
  trinket: 5 at most. All of a hero's dice are rolled at the start of each round. Sizes d4-d12,
  plus special dice with custom faces (shield faces, blanks, ×2) from uncommon rarity up.
- **Actions** are cards with dice slots and a requirement, e.g. "Slash: one die ≥2, deal its
  value", "Fireball: two dice summing to 10+", "Lunge: exactly 6". A hero has 2 class actions,
  1-2 from their weapon, and any learned through levelling: 4-6 on screen.
- **A round**: dice are rolled; enemies show **intents** (what they'll do and to whom); the party
  places dice on actions together, seeing each other's placements live; everyone clicks Ready;
  hero actions resolve, then enemies act in speed order.
- **Luck you can steer**: every hero gets 1 reroll per fight (restored by resting), and some skills
  and items change dice (+1, flip, set, copy, give to an ally).
- **Fleeing**: on their turn a hero can spend a die of 4+ to flee, going back to the hex they came
  from. No fleeing from dungeons or bosses.
- **Statuses** (shared by heroes and enemies, each with an icon and a tooltip):

  | Status | Effect |
  |---|---|
  | Burn | takes N damage at end of round, N drops by 1 |
  | Poison | takes N damage at start of round, doesn't decay |
  | Freeze | loses its lowest die next round (enemies: weakest intent cancelled) |
  | Shock | next hit also hits a neighbour for half |
  | Weak | deals 25% less damage |
  | Vulnerable | takes 25% more damage |
  | Stun | skips its next action |
  | Armor | blocks N damage, cleared at end of round unless a skill says otherwise |
  | Mark | takes +3 damage from every hit |
  | Root | can't change rows or flee |

- **Death**: a hero at 0 HP is **knocked down**. An ally can pick them up mid-fight. If they're
  still down when the fight ends, one revive from the **shared pool of 3** (Story 4, Hard 2; a rare
  event can add one) is spent and they come back at low HP. With the pool empty, a knocked-down
  hero stays dead; a dead player keeps placing **one support die** a round for the party, so nobody
  sits idle. The run ends when the pool is empty and the whole party is down.

### Heroes

- **10 classes, each unique within a party.** Each has one map ability and one combat role, so
  the choice matters outside fights too.
- **Classes are generic, not tied to the archipelago**, so they carry over to future maps. A map
  ability only talks to systems every map has, through hooks the map engine calls:
  `on_move_cost`, `on_reveal`, `on_loot`, `on_rest`, `on_shop`, `on_event`, `on_combat_start`.
  Nothing in a class may mention water, tides or skiffs.
- **Levelling**: XP is shared, so the party levels together. Cap at level 8. Every level gives max
  HP automatically, and levels 3 and 6 upgrade one base die a size (d6 to d8). Every level-up also
  offers a **choice of 1 of 3** from the class's skill pool: new actions, passives, upgrades to
  skills already owned (Slash → Slash+), and from level 6, capstones. No rerolling the offer.
- **Tags, not branches**: each class has two tags (e.g. Vanguard's *Bulwark* and *Juggernaut*).
  Offers lean toward tags the hero already has, so builds come together without locking anyone
  in. Untagged skills are offered evenly.
- **Level-up picks** happen on the rewards screen after the fight that levelled the party. All
  three pick at once, each seeing the others' choices as they lock in.
- **Gold is per hero.** Loot goes to whoever gets the item (pick 1 from a choice of items).
  Heroes can trade freely on a shared hex or in a town.
- **Items**: weapon, armor and trinket slots (each gives a die and maybe an action or passive) plus
  4 bag slots. 4 rarities (common, uncommon, rare, legendary). No durability. Consumables: potions,
  bombs, scrolls.
- **Healing**: HP carries over between fights. Heal at inns (gold), at camps (spend the turn, heal
  half), with potions, or from the Mender. Wearing the party down is part of the time pressure.

### UI and presentation

The owner asked for the whole UI flow to look **clean and professional**. Take pains here.

- **Split**: Phaser draws only the world (the hex map, combat sprites, effects). Every bit of
  text, every panel and every menu is HTML/CSS on top, as Roguelike Tactics does.
- **Look**: a pixel-art world with a clean modern UI. One sans-serif font for UI text (e.g. Inter)
  and one serif for headings; flat dark panels with soft borders; one accent colour; strict
  spacing and type scales. **Every colour, size, radius and spacing step is a token in one
  stylesheet**; no hard-coded values in components.
- **Art**: pixel sprites drawn by Python, the same way as Roguelike Tactics (see
  `docs/game-art.md`), in a sibling tool folder.
- **Screens and flow**:
  1. **Title**: New run, Resume, Join by code.
  2. **Lobby**: room code and link, players, host settings (difficulty), saved runs.
  3. **Class claim**: a card per class with role, row, base dice, map ability and sample skills.
     Players claim any free class and can swap until the host clicks Start; the host picks for
     unclaimed heroes. On resume, the saved heroes are shown instead.
  4. **Map**: the hex map in the middle; three hero cards down the left (HP, dice, moves left,
     Ready state); top bar with turn, tide and next flood; other heroes' planned paths as ghost
     trails, like Board Brawl's route previews.
  5. **Combat overlay**: full screen; rows; intents above enemies; each hero's dice tray and action
     cards along the bottom; allies' placements visible live.
  6. **Rewards and level-up**: gold, loot pick, then the 1-of-3 skill offer.
  7. **Town and shop panel**, **event dialog**.
  8. **Run end**: win or lose, a per-hero summary (damage, healing, kills, items), the seed, and a
     back-to-lobby button.

  Plus a settings and pause overlay openable from anywhere (volume, animation speed, save and
  quit). Moving between screens fades or slides in under 250 ms: no hard cuts, no blocking
  spinners.
- **Onboarding**: no tutorial level. Every keyword (Burn, Mark, shield face) has a hover tooltip.
  A short dismissible hint appears the first time each system shows up (first planning phase,
  first fight, first level-up, first flood), and the game remembers which have been seen.
- **Readability**: enemy intents show an icon, a number and a colour, from a palette that's safe
  for colourblind players. Text is at least 14 px. Hovering a placed action previews its damage
  or healing.
- **Controls**: keyboard and mouse first. 1-5 select a die, Q/W/E/R/T place it on an action, Space
  for Ready, Z to undo. Animation speed 1×, 2× or instant. Don't break phones, but don't spend
  effort there.
- **Audio**: sound effects and music synthesized in the browser at startup, no audio files, as in
  the other games.
- **Events** are light and wry in tone, with extra options for certain classes (Herald,
  Scoundrel, Arcanist especially) so the event map abilities pay off.

### Build order and testing

1. The engine with 3 classes (Vanguard, Arcanist, Mender) until a full run works end to end:
   lobby, map, combat, levelling, saving and resuming, run end.
2. The other 7 classes.
3. Then list it on `/games` and the nav. Until then it lives at its unlisted URL, since every push
   to `main` goes live.

- **Headless simulator** (`tools/saltbound-sim.py`): runs whole seeded runs with bots on the
  server's own rules code. Hundreds per run, reporting win rate by difficulty and class
  combination, average run length in map turns, and save → load → continue round-trips (a run
  saved and restored at any point must finish identically).
- **Playwright smoke test** (`tools/saltbound-smoke.js`): three tabs join a room, claim classes and
  play a map turn and a combat round.
- **Screenshot check** (`tools/saltbound-shots.js`): every screen from seeded states at 1440×900
  and 1280×720, plus one phone-width check, looked over against the tokens before pushing UI
  changes.

## The classes

HP is at level 1. A shield face blocks 3 damage when placed on any action. "Starts with" actions
are always owned; the pool is what level-ups offer. Each skill's tag is in brackets (untagged
skills have none). The skill lists are a first pass: tune numbers with the simulator, and keep
each pool at 6 actions, 6 passives and 2 capstones.

| Class | Row | HP | Base dice | Map ability (hook) | Role | Tags |
|---|---|---|---|---|---|---|
| Vanguard | Front | 30 | d6, Shield die (1-4, two shield faces) | **Trailbreaker**: rough terrain costs 1 (`on_move_cost`) | Tank | Bulwark, Juggernaut |
| Duelist | Front | 24 | d8, d6 | **Ambush**: a fight they start gives the party a free first round (`on_combat_start`) | Single-target damage | Flurry, Precision |
| Berserker | Front | 34 | d10, d4 | **Forage**: camps heal them fully (`on_rest`) | High-risk damage | Bloodlust, Rampage |
| Ranger | Back | 22 | d8, d6 | **Tracker**: sees enemy moves 2 turns ahead; +1 move off roads (`on_reveal`, `on_move_cost`) | Ranged damage | Marksman, Beastmaster |
| Arcanist | Back | 18 | d12, d4 | **Farsight**: reveals fog in radius 3; spots cursed items in loot (`on_reveal`, `on_loot`) | AoE and burst | Elementalist, Hexer |
| Mender | Back | 22 | d6, d6 | **Field Medic**: resting on their hex heals everyone there by half (`on_rest`) | Healer | Restoration, Warding |
| Scoundrel | Either | 22 | d6, d6 | **Light Fingers**: +1 loot choice; disarms traps (`on_loot`, `on_event`) | Debuffs and loot | Poisons, Tricks |
| Herald | Back | 20 | d6, d4 | **Silver Tongue**: shops 20% cheaper; extra event options (`on_shop`, `on_event`) | Buffs for allies | Anthem, Discord |
| Alchemist | Back | 20 | d6, d6 | **Brewer**: makes a potion at each rest (`on_rest`) | Items and gadgets | Bombs, Elixirs |
| Warden | Back | 24 | d8, d6 | **Wildspeak**: neutral beasts ignore them; forest costs 1 (`on_combat_start`, `on_move_cost`) | Summons and control | Grove, Thorns |

The Pathfinder was designed and dropped; its "+2 move, reveal fog along path" became the
Scoundrel's *Wayfinder* passive.

### Vanguard

- **Starts with**: Strike (any die: deal its value); Guard (any die: the next hit on an ally hits
  you instead, with Armor equal to the die).
- **Actions**: Taunt (≥3: all enemies target you this round) [Bulwark]; Brace (any: Armor = die ×2)
  [Bulwark]; Rally Wall (a pair: your row gains 4 Armor) [Bulwark]; Shield Bash (a shield face: 3
  damage and Stun) [Juggernaut]; Retaliate (≥4: deal damage equal to your Armor) [Juggernaut];
  Shoulder Charge (≥5: hit a back-row enemy and drag it to the front) [Juggernaut].
- **Passives**: Thick Hide (+6 max HP); Iron Will (ignore the first Stun each fight); Steady
  (shield faces block 4) [Bulwark]; Spiked Plate (attackers take 2) [Juggernaut]; Overguard (half
  your Armor carries into the next round) [Bulwark]; Last Stand (at 25% HP or less, gain 5 Armor
  each round).
- **Capstones**: Unbreakable (once per fight, survive a lethal hit at 1 HP) [Bulwark]; Avalanche
  (Retaliate hits the whole front row) [Juggernaut].

### Duelist

- **Starts with**: Slash (≥2: deal its value); Parry (any: block its value; if the hit is fully
  blocked, riposte for 2).
- **Actions**: Twin Cut (two dice: deal each) [Flurry]; Whirl (up to three dice of 3 or less: each
  hits a random enemy) [Flurry]; Lunge (exactly 6: deal 12) [Precision]; Finisher (a straight of
  three: deal the sum ×2) [Precision]; Pinpoint (a die matching the target's intent number: 15,
  ignores Armor) [Precision]; Feint (any: reduce one enemy intent's damage by the die).
- **Passives**: Momentum (each action after your first in a round deals +1) [Flurry]; Keen Edge
  (6s count as 7) [Precision]; Riposte+ (riposte deals 4); Footwork (back-row enemies deal 2 less
  to you); Opportunist (+3 against Stunned or Rooted targets); Second Wind (heal 3 on a kill).
- **Capstones**: Thousand Cuts (Twin Cut takes up to four dice) [Flurry]; Perfect Form (once a
  round, set one die to any value) [Precision].

### Berserker

- **Starts with**: Hack (any: deal its value +2); Bloodprice (pay 3 HP: +2 to one die).
- **Actions**: Drink Deep (≥4: deal its value; on a kill, heal that much) [Bloodlust]; Frenzy (two
  dice: deal the sum, take 2) [Bloodlust]; Cleave (≥5: deal its value to the whole front row)
  [Rampage]; Earthshaker (dice summing to 12+: half to all enemies, Stun one at random) [Rampage];
  Reckless Swing (≥8: deal 15, take 4); Howl (any: Weak all enemies this round).
- **Passives**: Rage (+1 damage per 5 missing HP); Bloodlust (heal 3 on a kill) [Bloodlust]; Wide
  Arcs (Cleave hits the back row for half) [Rampage]; Pain Engine (each hit taken gives +1 to your
  lowest die next round) [Bloodlust]; Thick Skull (+4 max HP and immune to Weak);
  Undying Fury (when knocked down, act once more first) [Rampage].
- **Capstones**: Red Mist (under half HP, all your damage heals you for half) [Bloodlust];
  Unstoppable (Cleave and Earthshaker ignore Armor and rows) [Rampage].

### Ranger

- **Starts with**: Shoot (any: deal its value to any row); Hunter's Mark (any: Mark a target).
- **Actions**: Aimed Shot (≥6: double damage) [Marksman]; Called Shot (a pair: the sum to a Marked
  target, ignores Armor) [Marksman]; Sic 'Em (any: your pet deals the die +2) [Beastmaster]; Pack
  Tactics (any: you and your pet hit the same target, +4) [Beastmaster]; Volley (three dice: each
  hits a random enemy); Pinning Arrow (≥4: its value and Root).
- **Passives**: Eagle Eye (a die showing its maximum crits for double) [Marksman]; Companion (start
  every fight with a hawk or wolf pet that has its own d4) [Beastmaster]; Field Dressing (your pet
  heals you 2 a round) [Beastmaster]; Quiver (Volley takes a fourth die); Long Mark (Mark lasts 2
  rounds) [Marksman]; Camouflage (enemies target you last).
- **Capstones**: Deadeye (one die a round counts as its maximum) [Marksman]; Alpha (your pet's die
  becomes a d8 and it gains its own action) [Beastmaster].

### Arcanist

- **Starts with**: Bolt (any: deal its value); Channel (two dice: deal the sum −2 to one target).
- **Actions**: Fireball (two dice summing to 10+: half the sum to all enemies, Burn 2)
  [Elementalist]; Frost Lance (≥5: its value and Freeze) [Elementalist]; Chain Lightning (an odd
  die: its value and Shock) [Elementalist]; Hex (any: Weak and Vulnerable) [Hexer]; Siphon (≥4:
  deal its value, heal half) [Hexer]; Doom (exactly 1: the target takes 20 at the end of next
  round) [Hexer].
- **Passives**: Overcharge (a d12 showing 12 is rolled again and added); Kindling (Burn ticks +1)
  [Elementalist]; Cold Snap (Frozen targets take +3) [Elementalist]; Malediction (your debuffs last
  1 round longer) [Hexer]; Arcane Shield (start each fight with 6 Armor); Spell Echo (your first
  spell each fight casts twice, the second at half strength).
- **Capstones**: Cataclysm (Fireball hits all enemies for the full sum) [Elementalist]; Grand
  Curse (Hex hits every enemy) [Hexer].

### Mender

- **Starts with**: Mend (any: heal an ally the die +2); Lift (any: pick up a knocked-down ally at HP
  equal to the die ×2).
- **Actions**: Renew (a pair: heal the whole party the sum) [Restoration]; Lifeline (exactly 6: an
  ally heals fully at the end of the round) [Restoration]; Ward (any: an ally gains Armor = die ×2)
  [Warding]; Sanctuary (≥5: every hit on the party deals 3 less this round) [Warding]; Cleanse
  (any: remove an ally's debuffs and heal 2); Smite (≥4: deal its value, +3 against undead).
- **Passives**: Bedside Manner (+2 to all your heals) [Restoration]; Overflow (overhealing becomes
  Armor) [Warding]; Quick Hands (one free Lift per fight) [Restoration]; Blessed Supplies (potions
  used on or by the party heal 50% more); Aura (the party regenerates 1 HP a round) [Warding];
  Calm (your dice can't be Frozen).
- **Capstones**: Miracle (once per run, a revive that would be spent isn't) [Restoration]; Aegis
  (Sanctuary lasts the whole fight at −2) [Warding].

### Scoundrel

- **Starts with**: Stab (any: deal its value, +2 against a target that didn't target you); Slip
  (any: change rows for free; on a 5+, dodge the next hit).
- **Actions**: Envenom (any: Poison equal to half the die) [Poisons]; Garrote (≥5: its value, and
  Stun if the target is Poisoned) [Poisons]; Toxic Cloud (dice summing to 9+: Poison 3 on all
  enemies) [Poisons]; Pickpocket (≥4: reduce an enemy intent by the die and gain 3 gold) [Tricks];
  Loaded Dice (any: set another of your dice to this one's value) [Tricks]; Smoke Bomb (a pair: the
  whole party dodges the next hit).
- **Passives**: Virulence (Poison ticks +1) [Poisons]; Wayfinder (+2 move and reveal fog along
  your path, on the map) [Tricks]; Lucky Coin (+1 reroll per fight) [Tricks]; Sticky Fingers (+5
  gold after each fight); Evasive (the first hit on you each fight misses); Backstab (+4 against
  targets acting on someone else).
- **Capstones**: Plague (Poison spreads to a neighbour when its carrier dies) [Poisons]; Sleight
  of Hand (one free Loaded Dice a round) [Tricks].

### Herald

- **Starts with**: Inspire (any: an ally adds half the die to one of their dice); Jab (any: deal
  its value).
- **Actions**: Hymn of Valor (a pair: allies' dice all +1 this round) [Anthem]; Lend a Hand (any:
  give this die to an ally) [Anthem]; Crescendo (a straight of three: allies' next action deals
  50% more) [Anthem]; Dirge (any: Weak an enemy) [Discord]; Taunting Verse (≥4: an enemy's intent
  changes to a random target) [Discord]; Cacophony (dice summing to 8+: one enemy's intent is
  delayed a round) [Discord].
- **Passives**: Battle Hymn (the party deals +1 damage while you're standing) [Anthem]; Second
  Verse (dice you give count +1) [Anthem]; Heckler (each enemy's first intent each fight is 3
  weaker) [Discord]; Haggler (sell items for more); Silver Voice (event checks are easier);
  Encore (a free reroll on the first die you use for Inspire each round).
- **Capstones**: Anthem of Kings (every ally rolls an extra d4 each round) [Anthem]; Requiem (once
  per fight, cancel one enemy intent) [Discord].

### Alchemist

- **Starts with**: Toss (any: a bomb deals its value to one target and 1 to its neighbours); Tonic
  (any: heal an ally its value).
- **Actions**: Firebomb (≥4: its value to a whole row, Burn 1) [Bombs]; Acid Flask (any: Vulnerable,
  and strip Armor equal to the die) [Bombs]; Concussion (≥5: Stun) [Bombs]; Bottle It (any: turn
  this die into a consumable of that strength to keep for later) [Elixirs]; Quicksilver (a pair:
  an ally rerolls all their dice) [Elixirs]; Panacea (dice summing to 8+: cleanse the party and
  heal it the sum) [Elixirs].
- **Passives**: Volatile (bombs +2 damage) [Bombs]; Shrapnel (bomb splash +2) [Bombs]; Potency
  (potions 50% stronger) [Elixirs]; Distiller (Brewer makes two potions) [Elixirs]; Deep Pockets
  (+2 bag slots); Safety Goggles (immune to your own splash and to Burn).
- **Capstones**: Chain Reaction (enemies killed by bombs explode for half their max HP) [Bombs];
  Philosopher's Draught (Bottle It is free once a round and the bottle is doubled) [Elixirs].

### Warden

- **Starts with**: Thornlash (any: its value; on a 5+, Root); Sprout (any: summon a sapling with
  HP equal to the die ×2 into an empty front slot).
- **Actions**: Call Bear (dice summing to 9+: summon a bear, 15 HP, hits for 4) [Grove]; Swarm
  (three dice of 3 or less: summon three wasps, 1 HP, sting for 2) [Grove]; Regrowth (any: heal
  every summon and ally half the die) [Grove]; Entangle (any: Root and Weak) [Thorns]; Briar Wall (a
  pair: your front row gains Armor and deals 2 back to attackers) [Thorns]; Strangle (≥4: its value,
  doubled against Rooted targets) [Thorns].
- **Passives**: Deep Roots (summons +50% HP) [Grove]; Pack Leader (+1 summon at a time) [Grove];
  Bramble Skin (attackers take 2) [Thorns]; Overgrowth (Root lasts 2 rounds) [Thorns]; Verdant
  (summons heal 2 a round); Bark (start every fight with a sapling).
- **Capstones**: Ancient Guardian (once per fight, summon a treant) [Grove]; Crown of Thorns (all
  enemies take 2 at the start of every round) [Thorns].

## Enemies

About 18 regular enemies plus three dungeon bosses and the final boss for v1. Every enemy shows
its intent each round; give each 2-3 intents so fights read clearly. First pass:

| Region | Front | Back | Dungeon boss |
|---|---|---|---|
| Coral Shallows | Drowned Deckhand (plain hits), Crabfolk Brute (heavy Armor), Jellyfloat (Poison on touch) | Reef Eel (Shock), Barnacle Priest (heals allies), Siren (Stun) | **The Bell-Warden** (Sunken Chapel): rings a bell that Stuns, summons drowned |
| Smugglers' Keys | Cutthroat (fast, Vulnerable), Deckhound (fast, targets the weakest), Brine Golem (slow, huge hits) | Powder Monkey (bombs a row), Tide Cultist (buffs allies), Corsair Captain (elite, commands) | **The Gallows Admiral** (Black Fort): cannon volleys that hit rows, calls boarders |
| Stormcrag | Crag Ram (charges, knocks back), Cliff Hermit (Root) | Harpy (strikes the back row), Storm Wisp (Shock), Lightning Totem (charges a big hit), Thunder Wyvern (elite) | **The Lamp Keeper** (Lighthouse): a beam that sweeps rows, intents shift each round |

**The Drowned Crown**, in three phases: (1) on the peak with tide guards; (2) the sea rises mid-fight
and the back row floods (heroes there must move or take damage each round); (3) the Crown alone,
taking an extra intent each round. Enemies scale with the region's distance from the start and the
number of objectives cleared.

## Items and economy

- About 50 items in v1. Weapons always give a die and 1-2 actions (a harpoon's "Reel In", a
  staff's "Bolt+"); armor gives a die (often shield faces) and a passive; trinkets give an odd die
  or a rule bend.
- Rarity sets die size and how odd the faces get: common (plain d4-d6), uncommon (d6-d8, first
  special faces), rare (d8-d10, strong faces), legendary (d12 or custom dice that change the
  rules).
- Each hero starts with 20 gold, a class weapon and basic armor. Prices, inn costs and drop rates
  are tuned with the simulator so a hero can afford roughly one meaningful upgrade per town visit.

## Events

About 25 in v1, light and wry. Each has 2-4 choices; some need a class (the Herald talks their way
out, the Scoundrel picks the lock, the Arcanist reads the runes) or a die check against a stat-free
target (roll your best die, 5+ wins). Outcomes: gold, items, HP, a revive (rare), a shrine buff, a
curse, or a fight. The archipelago's events live with the map's content; class-gated options key
on the class, so new maps can reuse them.

## Planned shape of the code

Follow Board Brawl's layout (`app/brawl/`) for the server and Roguelike Tactics'
(`app/static/games/threefold/`) for the client. A sketch to start from, not a rule:

| Path | Holds |
|---|---|
| `app/saltbound/routes.py` | the page, the WebSocket (`/ws/saltbound/{code}`), the saved-runs list |
| `app/saltbound/room.py` | lobby, clients, claiming, the host, pausing while waiting for a player |
| `app/saltbound/rules.py` | dice, actions, statuses, damage: pure functions the simulator also uses |
| `app/saltbound/world.py` | seeded map generation, terrain, sea rise, tides, roaming enemies |
| `app/saltbound/combat.py` | starting a fight, rounds, intents, resolution, rewards |
| `app/saltbound/classes.py` | the 10 generic classes, their pools and tags, map-ability hooks |
| `app/saltbound/content/` | enemies, items and events, split per map so new maps can be added |
| `app/saltbound/save.py` | saving, loading, `version` and migrations |
| `app/saltbound/bot.py` | the testing bots |
| `app/static/games/saltbound/` | `index.html`, `css/tokens.css` plus component CSS, `js/` (net, screens, map and combat scenes, audio, generated sprites) |

All randomness comes from one seeded RNG whose state is in the save, never from the global
`random` module, or restored runs won't match.

The client's module URLs and stylesheet links carry a `?v=` to bump on every CSS/JS change, as the
other games do (Cloudflare caches static files).
