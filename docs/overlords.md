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
   (their cost in gold), reroll the shop (2), buy 4 XP (4), drag units between bench and board, drop
   one on the shop to sell it (back for its cost times its copies). Your level (1-8) is how many units
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
fatal. Copies come out of a shared pool (`POOL`, by cost) and go back when sold or when their owner
is knocked out.

### Units and traits

15 units so far (three per cost, 1-5), one summon (Treant) and four monsters, all in
`app/overlords/data.py`. Each unit has one origin and one or two classes. A trait counts the
*different* units carrying it on the board and switches on at thresholds (2/4/6 or 2/4). 16 traits:
origins Emberforged (attacks burn), Thornwood (regrow HP), Tidecallers (mana each second), Gravebound
(rise once), Skyborne (dodge), Ironhold (armor and resist), Starlit (cheaper abilities), Mirefolk
(attackers are chilled); classes Vanguard (shield at the start), Duelist (attack speed stacks), Ranger
(double strikes), Arcanist (the board's ability power), Mystic (the board's resist), Assassin (leap to
the back line, crits), Summoner (stronger summons), Warden (max HP).

Abilities are data: a list of steps (`hit`, `heal`, `shield`, `buff`, `summon`, `dash`), each aimed by
a selector (`target`, `around_target:1`, `line:6`, `chain:5`, `lowest_ally`, ...). The docstring at
the top of `data.py` lists them all. A new unit needs no new code unless it needs a new step or
selector (add it to `sim.Fight.step_*` / `select` and to `STEPS` / `SELECTORS`).

## The plan (from the owner's answers)

2-4 player free-for-all, hex board, original fantasy, about 20 minutes, Python-drawn pixel sprites,
records only (no unlocks), and all four extra systems, at the large size:

1. ~~The combat engine on 15 units~~ (done: `sim.py`, `tools/overlords-fight.py`)
2. ~~The match loop: shop, bench, board, economy, levels, matchups, bots; a placeholder client
   (coloured tokens), live watching of any fight, synthesized sound~~ (done)
3. The full roster: 50 units across the five costs, all 16 traits filled out
4. Items (8 components from monster rounds and drafts, 36 combined, 3 a unit), 12 commanders (picked
   from 3 at the start: a passive and an active that charges over rounds), ~60 augments in three tiers
   (1 of 3 at rounds 3, 8 and 13, one free reroll), and a shared draft at rounds 4, 9 and 14 (lowest
   HP picks first, in turn, units holding items)
5. Art and sound: sprites from `tools/overlords-art/` (reusing Kingfall's `pix.py`/`anim.py`), idle,
   attack, cast and death frames, ability effects, a fight speed toggle
6. Records in `data/overlords.db`, one big balance run, this doc, the games page, README and CLAUDE.md

Not on the games page yet (the owner can play it at `/games/overlords`); list it once it has art.

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
- `game.py`: the room. Phases `lobby`, `plan`, `fight`, `over`; a 0.25 s loop moves between them on
  timers. Everyone's boards are public (`state.players[].board`); each person's shop, bench and XP
  come in `state.me`. Fights arrive as `{"t": "fights", "elapsed", "list": [{home, away, pve, ghost,
  res}]}`. With an odd number alive, one player fights a copy of another (`ghost`: only the real
  player takes the result). Pairings avoid a repeat opponent when they can.
- `bots.py`: `arrange` (melee in front, toughest in the middle; ranged at the back, assassins last)
  and the bots' turn (`play`): two traits to aim for, a level schedule, gold kept for interest from
  round 5, rerolls when rich or below their panic HP. They act through the same room methods as a
  browser.
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
  `tools/overlords-fight.py` once.

## Gotchas

- The fights message is sent *before* the state that switches to the fight phase, so the browser
  builds its Playback when that state arrives (and on `fights` if the phase is already fight).
- `d` events carry the HP left after shields; shields soak damage first, so the number shown can
  exceed the HP lost. `v` snapshots every 0.5 s correct HP, mana and shields.
- Trait counts ignore duplicates and summons. Summons and monsters have `"summon": True` and cost 0,
  which keeps them out of the shop and the pool.
- `Room.clock` is swappable: the check winds it on to play whole matches instantly. Real code must
  use `self.clock()`, not `time.monotonic()`, for phase timers.
- A mana-from-damage loop once let a lone 1-star Star Queen shield herself for 25 s against six
  units; that's what `MANA_HURT_MAX` and `MANA_LOCK` prevent. Watch for it with any new shield or
  heal that scales with hits taken.

## Checks and numbers

- `python3 tools/overlords-check.py` (~3 s, in `check-all.sh`): data, every ability fires at every
  star, determinism, board rotation, 300 random fights finish, the room's rules (buying, merging,
  limits, moving, selling, the locked board), and three whole bot matches with the pool conserved.
- `node tools/overlords-smoke.js --serve` (~30 s, in `check-all.sh`): two browsers, a room with two
  bots, buy/drag/sell, a fight played back and watched, the next round.
- `python3 tools/overlords-fight.py [N] [--size S]`: unit and trait win rates on random boards;
  `--show SEED` prints one fight.

Latest numbers (November 2026, 15 units, 800 random 6-unit fights): 7 ms a fight, average 18.6 s,
1% hit the cap. Win rate rises with cost (1-cost 39-45%, 5-cost 54-63%). Worth a look in the
balance pass: Storm Herald is weak for a 4-cost (48%), Emberforged (38%) and Duelist (42%) lag,
Summoner (69%) and Warden (64%) look strong, though random boards rarely build around a trait.
Bot matches take 16-17 rounds, about 14 minutes at full timers (the target is ~20: lengthen with
more rounds or lower loss damage once the roster is full).
