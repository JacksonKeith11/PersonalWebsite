# Overlords (the game at /games/overlords)

Read this before changing anything in `app/overlords/`, `app/static/games/overlords/`, or the
`tools/overlords-*` scripts.

## What it is

An auto-battler for 2-4 players (the owner asked for one "like Dota Underlords, TFT or Guildrun" in
November 2026; the name Underlords is Valve's, so it's Overlords). Bots fill the empty seats unless
the host turns them off (easy, normal or hard); anyone joining after the start watches. Desktop
first: the page needs about 1000 px of width and drags with a mouse.

Everyone has their own 7x4 hex board, a bench of 8 and a shop of 5. Each round:

1. **Planning** (20 s in round 1, then 30 s; cut short when every person presses Ready): buy units
   (their price in gold), reroll the shop (2), buy 4 XP (4), drag units between bench and board, drop
   one on the shop to sell it (back for its price times its copies). Your level (1-8) is how many units
   may stand on the board, and sets the shop's odds (`SHOP_ODDS`). Three copies of a unit at one star
   merge into the next star (x1.8 HP and attack at two stars, x3.24 at three), where the first copy on
   the board stood. A locked shop survives into the next round.
2. **Fighting**: every fight of the round is simulated the moment the phase starts and sent to every
   browser whole, so anyone can watch any fight (click a player). The phase ends 3 s after the
   longest fight. The board is locked; the shop and bench still work.

Losing costs `loss_damage`: 1 + round / 3, plus each surviving enemy's stars, plus 3 more per round
from round 16. A fight that hits the 30 s cap is lost by both. Players start on 60 HP; last one
standing wins. Rounds 1, 2, 6 and 11 are monster rounds (`PVE`): everyone fights the same monsters,
for gold (`PVE_GOLD`). Income each round: 3, 4, then 5 gold, plus 1 per 10 saved (up to 5), plus
1-3 for a win or loss streak of 2+. Everyone starts with one free 1-cost unit. Before each fight,
bench units fill any empty board places up to the level (`fill_board`), so forgetting to place isn't
fatal. Copies come out of a shared pool (`POOL`, by tier) and go back when sold or when their owner
is knocked out.

**Tiers and prices.** A unit's tier (1-5) sets its shop odds, pool size and colour; its price doesn't
scale with it in a straight line (the owner asked, November 2026): 1, 2, 3, 5 and 8 gold (`PRICE`).
Tier-4 and tier-5 units have 8% and 15% more HP and attack than written (`TIER_POWER`, applied in
`U()`) to earn the steeper price. In code, `"tier"` is the tier and `"cost"` the price.

### Items, commanders, augments and drafts

- **Items** (`ITEMS`): 8 components (Sword, Bow, Rod, Tear, Vest, Cloak, Belt, Sigil) drop from monster
  rounds (`PVE_DROPS`: 1, 1, 2 and 2 to a winner; a loser gets 1 where 2 drop) and come with draft
  picks. They wait on the item bench (`player.items`) until dragged onto a unit (or clicked, then the
  unit). A unit holds 3; a component dropped on a unit already holding one combines (`combine`) into one
  of 28 finished items (both components' stats plus an effect: crits, life-steal, splash, thorns, shred,
  stun immunity...). A Sigil with another component makes that component's emblem (seven, `EMBLEM_FROM`:
  the holder gains the trait, refused on a unit that has it); two Sigils make a Crown (one more place on
  the board, `Player.limit`). Augment crests give emblems of any trait. Items follow merges (up to 3 on
  the merged unit, the rest back to the item bench) and come back when a unit is sold.
- **Commanders** (`COMMANDERS`, 12): three offered at the start, picked on a screen before the first
  fight (the first is taken if none is picked). A passive, and a power that charges a round at a time
  (3-5 rounds) and is used from the left panel while planning. Powers for "next fight" go in
  `player.next_fx` and are spent at the fight's start. All of it is in `game.py` (`extras`,
  `use_power`, and the odd line in income, rolls and damage).
- **Augments** (`AUGMENTS`, 64): one of three at rounds 3, 8 and 13, all of one tier (lesser, greater,
  grand, by `AUGMENT_TIER_ODDS`), with one reroll. Trait augments (Heart +1, Crest an emblem, Soul +2 to
  a trait's count) are only offered for traits among your units when there are enough of them. Unpicked
  offers are taken (the first) when the fight starts.
- **Drafts** (`DRAFT_ROUNDS`: 4, 9 and 14): a phase `draft` before planning. One unit per player plus
  two (tiers by `DRAFT_TIERS`), each holding a random component, held out of the pool; lowest HP picks
  first, 8 s a person (then at random), bots after 0.8 s. A pick with no bench room is sold on the spot
  and its component kept. What's left goes back to the pool.
- In a fight these reach `sim.Fight` as each side's `extras`: `bonus` (augment trait counts), `team`
  (fx for everyone), `front`, `revive_first`, `summon` and `rally`.

### Units and traits

50 units (13, 13, 11, 8 and 5 at tiers 1-5), five summons (Treant, Bog Imp, Skeleton, Turret, Mire
Spawn) and four monsters, all in `app/overlords/data.py`. Each unit has one origin and one or two
classes. Every trait can reach its top tier: origins with a 6 have 7 units, those topping at 4 have
5-6, and classes have 6-8. A trait counts the
*different* units carrying it on the board and switches on at thresholds (2/4/6 or 2/4). 16 traits:
origins Emberforged (attacks burn), Thornwood (regrow HP), Tidecallers (mana each second), Gravebound
(rise once), Skyborne (dodge), Ironhold (armor and resist), Starlit (cheaper abilities), Mirefolk
(attackers are chilled); classes Vanguard (shield at the start), Duelist (attack speed stacks), Ranger
(double strikes), Arcanist (the board's ability power), Mystic (the board's resist and a little
regrowth: resist alone did nothing, since most damage is physical), Assassin (leap to the back line,
crits), Summoner (stronger summons), Warden (max HP).

Abilities are data: a list of steps (`hit`, `heal`, `shield`, `buff`, `summon`, `dash`, `mana`), each
aimed by a selector (`target`, `around_target:1`, `line:5`, `chain:5`, `lowest_enemy`, `lowest_ally`,
...). A hit can drain (`heal_frac`); a summon can bring several (`count`); a `static` summon (the
Turret) never moves. The docstring at
the top of `data.py` lists them all. A new unit needs no new code unless it needs a new step or
selector (add it to `sim.Fight.step_*` / `select` and to `STEPS` / `SELECTORS`).

## The plan (from the owner's answers)

2-4 player free-for-all, hex board, original fantasy, about 20 minutes, Python-drawn pixel sprites,
records only (no unlocks), and all four extra systems, at the large size:

1. ~~The combat engine on 15 units~~ (done: `sim.py`, `tools/overlords-fight.py`)
2. ~~The match loop: shop, bench, board, economy, levels, matchups, bots; a placeholder client
   (coloured tokens), live watching of any fight, synthesized sound~~ (done)
3. ~~The full roster: 50 units across the five costs, all 16 traits filled out~~ (done, with a first
   balance pass)
4. ~~Items, 12 commanders, 64 augments, shared drafts~~ (done, with the non-linear prices)
5. ~~Art: sprites for every unit, poses, ability effects, a fight speed toggle~~ (done; the sounds were
   already synthesized in step 2)
6. Records in `data/overlords.db`, one big balance run, this doc, the games page, README and CLAUDE.md

Not on the games page yet (the owner can play it at `/games/overlords`): step 6 lists it.

### Art

- 59 sprites (50 units, 5 summons, 4 monsters), one 32x32 drawing each, by code in
  `tools/overlords-art/` (`units1.py`: Emberforged, Thornwood, Tidecallers, Gravebound; `units2.py`:
  Skyborne, Ironhold, Starlit, Mirefolk, the other summons and the monsters). They use Roguelike
  Tactics' kit and renderer (`tools/threefold-art/kit.py`: flat material letters, then outline and cel
  shading by code; `docs/game-art.md` has the rules: matte, muted, dark outlines, chunky), with
  Overlords' own humanoid builder (`Fig`: normal, short for dwarves, big, small; heads, helms, hoods,
  hats, crowns, beards, capes, wings) and weapons and creature parts in `kit.py`.
- Each origin has a palette (`kit.ORIGIN`) so a trait reads at a glance: Emberforged charcoal and
  fire, Thornwood bark and leaves, Tidecallers teal and coral, Gravebound bone and violet, Skyborne
  pale blue, white and gold, Ironhold steel and brass dwarves, Starlit midnight and silver elves
  (pointed ears), Mirefolk olive frogfolk.
- Five poses per sprite, derived from the drawing as Saltbound does (`kit.poses`): idle, attack (leans
  in), cast (leans back), hurt, fallen (lies down). `python3 tools/overlords-art/build.py` writes the
  atlas (`art/units.png`, a row a sprite, a column a pose) and `js/atlas.js` (rows, poses, and the PNG's
  hash in its URL, since Cloudflare caches `/static`). Never edit either by hand; preview with
  `python3 tools/overlords-art/sheet.py out.png [names] [--poses]`. After a build, bump the game's
  `?v=` as usual. `overlords-check.py` fails if a unit has no sprite.
- In the browser (`drawUnit`): the sprite stands on a ring in its owner's colour (filled by tier), big
  units (tier 4-5 and the giants) drawn larger; it bobs when idle, faces whoever it last attacked,
  takes the attack/cast/hurt pose for a moment after each, lies down and fades when it dies. Spells
  draw from the ability's data: a bolt in the caster's origin colour to each target hit at the moment
  of the cast, a burst for `around_target`/`around_self`, a beam for `line`; heals sparkle, burning
  flickers, stuns circle the head with stars.
- **Fights 1×/2×** (header, remembered): plays fights at double speed. The server's timing doesn't
  change; a fast player just sees the result sooner and waits for the others.
- The owner hasn't reviewed the looks yet (in the other games the owner picks from options): expect
  changes unit by unit.

## How it works

- `data.py`: units, traits, the match's numbers and helpers (`trait_counts`, `trait_level`,
  `income`, `streak_gold`, `loss_damage`).
- `sim.py`: the fight. 7x8 pointy-top hexes in odd-r offset coordinates; a player's own board is
  7x4 with row 3 at the front, and the away board is turned round (`to_grid`: (c, r) -> (6-c, 7-r),
  which keeps neighbours neighbours because odd and even rows swap together). Each 0.05 s tick, each
  living unit (in a fixed shuffled order) casts if its mana is full, attacks its target if in range,
  else steps along the shortest free path (BFS) to a hex in range. Mana: 10 an attack, 4% of damage
  taken (at most 8 a hit), none for 1 s after a cast. From 18 s every hit grows 25% a second
  (overtime), so fights end. The result is a timeline of events (listed at the top of `sim.py`),
  `start` rows, the survivors and damage done. About 7 ms a fight.
- `game.py`: the room. Phases `lobby`, `draft`, `plan`, `fight`, `over`; a 0.25 s loop moves between them on
  timers. Everyone's boards are public (`state.players[].board`); each person's shop, bench and XP
  come in `state.me`. Fights arrive as `{"t": "fights", "elapsed", "list": [{home, away, pve, ghost,
  res}]}`. With an odd number alive, one player fights a copy of another (`ghost`: only the real
  player takes the result). Pairings avoid a repeat opponent when they can.
- `bots.py`: `arrange` (melee in front, toughest in the middle; ranged at the back, assassins last)
  and the bots' turn (`play`): two traits to aim for, a level schedule, gold kept for interest from
  round 5, rerolls when rich or below their panic HP, the commander's power when charged, items on
  their most valuable units (`equip`), and picks of commander, augment and draft. They act through the
  same room methods as a browser.
- Browser: `js/main.js` (screens, canvas, dragging, the shop, panels), `js/fight.js` (`Playback`:
  rebuilds a fight at any time from its timeline; switching fights catches up silently),
  `js/sound.js` (every sound synthesized with Web Audio; hits rate-limited; mute remembered). The
  menu and lobby are the shared `games/shared/lobby.js`. `?debug` exposes `window.OV` for the smoke
  test.

## Design directives

- The server decides everything; the browser only draws and asks. Fights are deterministic for a
  seed: keep `sim.py` free of wall-clock time and global randomness (use `self.rng`).
- Units, traits, abilities and match numbers live in `data.py` as data; prefer a new step or
  selector over special-casing a unit in the sim.
- Original names and designs only: the genre is fine, another game's units, traits or look are not.
- Balance at the end of a batch (CLAUDE.md): change everything first, then run
  `tools/overlords-fight.py` once. Aim for units at 43-57% against their own cost, and traits at
  roughly 55-65% at their first tier rising to 80-90% at a top tier of 6 (a board built around a trait
  against boards that aren't).
- When matching strings to edit `data.py`, beware lines two units share (Bramble Guard and Iron
  Warlord once had the same shield line).

## Gotchas

- The fights message is sent *before* the state that switches to the fight phase, so the browser
  builds its Playback when that state arrives (and on `fights` if the phase is already fight).
- `d` events carry the HP left after shields; shields soak damage first, so the number shown can
  exceed the HP lost. `v` snapshots every 0.5 s correct HP, mana and shields.
- During a draft, `Room.ends` follows the current pick's deadline, so code (and the checks' clock)
  that winds to `ends` keeps moving. Draft options are held out of the pool while on offer: count them
  when checking the pool adds up.
- Trait counts ignore duplicates and summons. Summons and monsters have `"summon": True` and cost 0,
  which keeps them out of the shop and the pool.
- `Room.clock` is swappable: the check winds it on to play whole matches instantly. Real code must
  use `self.clock()`, not `time.monotonic()`, for phase timers.
- A mana-from-damage loop once let a lone 1-star Star Queen shield herself for 25 s against six
  units; that's what `MANA_HURT_MAX` and `MANA_LOCK` prevent. Watch for it with any new shield or
  heal that scales with hits taken.

## Checks and numbers

- `python3 tools/overlords-check.py` (~5 s, in `check-all.sh`): data, every ability fires at every
  star, every item in a fight, determinism, board rotation, 300 random fights finish, the room's rules
  (buying, merging, limits, moving, selling, the locked board), equipping and combining, emblems, the
  Crown, every commander power, every augment, a draft, and three whole bot matches with the pool
  conserved.
- `node tools/overlords-smoke.js --serve` (~30 s, in `check-all.sh`): two browsers, a room with two
  bots, commanders picked, buy/drag/sell, a fight played back and watched, the next round, an item
  dragged onto a unit when one dropped.
- `python3 tools/overlords-sim.py [N] [--level L]`: whole bot matches (a quarter of a second each):
  rounds and minutes, each commander's average place (2.5 is even), the most picked augments.
  `--fast` plays 4.
- `python3 tools/overlords-fight.py [N] [--size S]`: each unit's win rate against boards of the
  same costs (50% is right at every cost); `--traits [N]` each trait at each tier against
  cost-matched boards; `--show SEED` prints one fight. Both together: about a minute.

Latest numbers (November 2026, all 50 units, after the first balance pass; ~1 minute to rerun):
- Units, 2000 cost-matched 7-unit fights: 10 ms a fight, average 20.8 s, 1% hit the cap. 44 of 50
  units within 42-58% of their cost; just outside: Ashling 41%, Kraken Caller 40% (weak), Tide
  Acolyte 59%, Storm Herald 60%, Moss Brute 58%, Lava Giant 58% (strong).
- Traits, 120 fights a tier (about ±4.5%): every trait rises tier by tier; first tiers 41-58%, the
  4-tiers of the 2/4 traits 59-86%, the top tiers of 6 at 76-91%. Lowest first tiers (41-43%):
  Duelist, Ranger, Assassin, Arcanist, Summoner, Mirefolk. Gravebound 6 (91%) is the strongest top.
- Whole bot matches (400, `tools/overlords-sim.py`, ~2 minutes; November 2026, after items,
  commanders, augments and drafts): 17.6 rounds (15-20), about 17 minutes at full timers, close to
  the ~20 the owner wanted (people take longer than bots' instant turns). Commanders' average place,
  after one tuning pass (the Sage won 44% at first): 2.29 (Sage) to 2.73 (Merchant); Quartermaster
  2.69 and Oracle 2.65 are the weaker end. These are bots' numbers: bots use powers as soon as
  they're charged and don't plan around the Oracle's or the Merchant's economy, so people may find
  those better than this says. Bots favour trait augments; crests place best (2.35-2.74).
