# Overlords (the game at /games/overlords)

Read this before changing anything in `app/overlords/`, `app/static/games/overlords/`, or the
`tools/overlords-*` scripts.

## What it is

An auto-battler for 2-4 players (the owner asked for one "like Dota Underlords, TFT or Guildrun" in
November 2026; the name Underlords is Valve's, so it's Overlords). Bots fill the empty seats unless
the host turns them off (easy, normal or hard); anyone joining after the start watches. Built
desktop first; since November 2026 it also plays on phones, upright or on their side (see **Phones**).

Everyone has their own 7x4 hex board, a bench of 8 and a shop of 5. Each round:

1. **Planning** (20 s in round 1, then 30 s; cut short when every person presses Ready): buy units
   (their price in gold), reroll the shop (2), buy 4 XP (4), drag units between bench and board, drop
   one on the shop to sell it (back for its price times its copies). Your level (1-8) is how many units
   may stand on the board, and sets the shop's odds (`SHOP_ODDS`). Three copies of a unit at one star
   merge into the next star (x1.8 HP and attack at two stars, x3.24 at three), where the first copy on
   the board stood, and at two and three stars its owner picks an extra ability for it (see **Extra
   abilities**). A locked shop survives into the next round.
2. **Fighting**: every fight of the round is simulated the moment the phase starts and sent to every
   browser whole, so anyone can watch any fight (click a player). The phase ends 3 s after the
   longest fight. The board is locked; the shop and bench still work.

Losing costs `loss_damage`: 1 + round / 3, plus each surviving enemy's stars, plus 3 more per round
from round 16. A fight that hits the 30 s cap is lost by both. Players start on 60 HP; last one
standing wins, except that once every person in the room is out, the match ends there and the bots
still standing are placed by HP (`only_bots_left`, `finish`; the owner asked for a loss to end it at once
rather than wait on the bots). A room of bots alone, as in the checks and the simulator, plays out.
Rounds 1, 2, 6 and 11 are monster rounds (`PVE`): everyone fights the same monsters, for gold
(`PVE_GOLD`: 3, 4, 6 and 8 to a winner; no items, which come from the armory). Income each round: 3, 4, then 5 gold, plus 1 per 8 saved (up to 5; per 10, then 6, until late November 2026, see Gotchas), plus
1-3 for a win or loss streak of 2+. Everyone starts with one free 1-cost unit. Before each fight,
bench units fill any empty board places up to the level (`fill_board`), so forgetting to place isn't
fatal. Copies come out of a shared pool (`POOL`, by tier) and go back when sold or when their owner
is knocked out.

**Tiers and prices.** A unit's tier (1-5) sets its shop odds, pool size and colour; its price doesn't
scale with it in a straight line (the owner asked, November 2026): 1, 2, 3, 5 and 8 gold (`PRICE`).
Tier-4 and tier-5 units have 8% and 15% more HP and attack than written (`TIER_POWER`, applied in
`U()`) to earn the steeper price. In code, `"tier"` is the tier and `"cost"` the price.

### Items, commanders, augments, drafts and the auction

- **Items** (`ITEMS`) are bought whole in the **armory**, in four rarities of rising power and price
  (November 2026: first the owner moved components from monster drops into a shop, then asked for the
  components and recipes to go, for items bought directly in rarity tiers, and for items to come off
  units again):
  - **Common** (`rarity` 1, 2 gold): plain stats (Iron Sword +20 attack, Giant's Belt +300 HP...; 7).
  - **Rare** (2, 4 gold): a trick of its own plus one stat line (Mana Edge, Sunder Axe, Duelist's
    Guard, Twin Ward...; 14).
  - **Epic** (3, 6 gold): a stronger trick plus two stat lines (Twin Bow, Storm Rod, Grimoire, Bastion
    Plate, Colossus Belt...; 14), and the 16 emblems (the holder gains the trait, refused on a unit
    that has it).
  - **Legendary** (4, 9 gold): the 9 artifacts (Stopped Hourglass, Soulreaver, Phoenix Feather, Echoing
    Tome...) and the Crown (one more place on the board, `Player.limit`).
  The tricks are the old recipe items' effects; a stat line (`_S`) is one old component's stats, and an
  item's `stats` text lists them. `ITEM_PRICE`, `RARITIES`.

  The armory (`Player.armory`, `stock_armory`, `buy_item`, beside the item bench) offers `ARMORY_SIZE` (4)
  items a round, each slot's rarity drawn by `ARMORY_ODDS` for the round: Common and Rare only until
  round 4, Epic from 4, Legendary from 8 (5%) rising to 25% from round 16 (`armory_odds`). Within Epic an
  emblem one time in `EMBLEM_SHARE` (4); within Legendary a Crown one time in `CROWN_SHARE` (8)
  (`random_item`). It restocks each round (rerolls don't touch it), a locked shop keeps it, and a bought
  slot stays empty until the next round. The Forgemaster pays a gold less for everything. Bots buy the
  dearest first with the gold left after units (skipping emblems of traits they don't aim for), while
  their units have room or the item is rarer than one they hold, put each on the unit it suits (`bots.fit`:
  attack items on attackers, ability items on casters, armour on the front line, weighted by the unit's
  worth), and swap a weaker item off a full unit for it (`bots.equip`).

  Items wait on the item bench (`player.items`) until dragged onto a unit (or clicked, then the unit);
  a unit holds 3 (`MAX_ITEMS`). **Taking off** (`unequip`): click or tap your unit and its card lists
  its items with a Take off button each; the item goes back to the item bench. Not from the board mid-
  fight, and not a Crown whose extra board place is in use. Items follow merges (up to 3 on the merged
  unit, the rest back to the item bench) and come back when a unit is sold. In the browser every item
  wears its rarity's colour (`RARITY_COLORS`: grey, blue, purple, orange, the unit tiers' hues) on the
  item bench, in the armory and as a frame under units. Monster rounds give no items.
  Other sources: drafts (below), augments (Spare Parts a Rare, Armory an Epic, Arsenal two Epics, Ancient
  Armory and Relic Hunter an artifact, Crowned a Crown, Crests an emblem), the Alchemist (a Rare at rounds
  5, 10 and 15, and its power), the Forgemaster (a Common to start; its power an Epic, one time in four an
  artifact).
- **Commanders** (`COMMANDERS`, 16; the roster review added the Gambler, the Hexer, the Chronomancer and
  the Twinmaker, and gave the Warlord, Archmage, Blademaster and Survivor passives that do more than add
  a stat): three offered at the start, picked on a screen before the first
  fight. The first fight waits for everyone still connected to pick (the owner asked for no auto-pick
  while someone thinks): when the timer runs out, `tick` holds the phase while `choosing()` is non-empty,
  the browsers get `state.choosing` and say who they wait for; anyone who disconnects gets the first
  offer, so a vanished player can't stall the room (the checks' rooms must pick for their people). A passive, and a power that charges a round at a time
  (3-5 rounds) and is used from the left panel while planning. Powers for "next fight" go in
  `player.next_fx` and are spent at the fight's start. All of it is in `game.py` (`extras`,
  `use_power`, and the odd line in income, rolls and damage).
- **Augments** (`AUGMENTS`, 80: 66 from the roster review, ten build-arounds and four for the auction): one of three at rounds 3, 8 and 13, all of one tier (lesser, greater,
  grand, by `AUGMENT_TIER_ODDS`), with one reroll. Trait augments (Heart +1, Crest an emblem, Soul +2 to
  a trait's count) are only offered for traits among your units when there are enough of them. Their
  cards also say what the trait does at each tier (`traitLine` in `main.js`; the owner asked for the
  emblems to be explained), as do emblems' info cards, and the augments in the commander panel show the
  trait on hover or tap. Unpicked offers are taken (the first) when the fight starts.
- **Build-around augments** (ten, the owner asked for Guildrun-style ones, late November 2026): they
  grow with the board, worked out every fight in `Player.extras` (`build_arounds`, `build_count`), so the
  unit cards show them. `per`: so much for each unit counted (Kinship: your most common origin;
  Spellweave: Arcanists, Mystics and Summoners; Bladework: Duelists, Rangers and Assassins; Shield Wall:
  units on the front row, for the front row; War Chest: gold held, per 3, up to 20). `when`: once a
  condition holds (Melting Pot: five different origins). `stars`: units of at least that star (Elite
  Guard; `extras["stars"]`). `convert`: one stat into another once everything else is counted
  (`Fight.convert`: Giant's Heart, extra max HP into attack; Runeplate, extra armor and resist into
  ability power; Quickening, extra attack speed into mana a second; "extra" is beyond the unit's own
  numbers, `Unit.raw`). Bots rate them by what their board would get now (`pick_augment`).
- **Drafts** (`DRAFT_ROUNDS`: 4, 9 and 14): a phase `draft` before planning. One unit per player plus
  two (tiers by `DRAFT_TIERS`), each holding a random item (`DRAFT_ITEM_RARITY`: Rare at 4, Epic at 9,
  an artifact at 14), held out of the pool; lowest HP picks first, 8 s a person (then at random), bots
  after 0.8 s. A pick with no bench room is sold on the spot and its item kept. What's left goes back to the pool.
- **The auction** (`AUCTION_ROUNDS`: 6 and 11, the monster rounds that close each act; the owner asked for
  it, after Guildrun's end-of-act auction, late November 2026): a phase `auction` before planning (and
  before that round's draft, had it one). Three lots (`start_auction`): a two-star unit of
  `AUCTION_UNIT`'s tier holding an item of its rarity (Epic at 6, an artifact at 11; its three copies held
  out of the pool), a relic (kind `relic`: four Legendary items won nowhere else, `RELICS`) and an
  auction augment (tier 4, never offered at the augment rounds: Legion, one more board place,
  `Player.slots`, bids from 12 (`AUCTION_LOT_MIN`); War Banner; Ancestral Echo; Iron Will, the front row's `Player.front_fx`). Sealed
  bids (`bid`: each 0 or at least the lot's `min`, `AUCTION_MIN` unless `AUCTION_LOT_MIN` says more, together no more than your gold; resent bids replace the
  last); the state shows the lots and who has bid, never amounts. It closes after `AUCTION_TIME` or once
  every connected person has bid (bots bid at once, so a room of bots doesn't wait); the highest bid of
  all takes its lot (ties to the lower HP) and pays it, that bidder drops out, and so on: nobody wins
  more than one lot (`resolve_auction`; without that rule saving bots won everything and the saver style
  led at 2.0; `award`: a unit with no bench
  room is sold on the spot, its item kept); unsold units go back. No shopping during it. The results ride
  in `state.auction_results` while planning (the banner lists them). Bots bid each lot's worth to them,
  more for their style's favourite (`AUCTION_LIKES`), with some luck, and keep `AUCTION_SAVE` gold the
  round before.
- In a fight these reach `sim.Fight` as each side's `extras`: `bonus` (augment trait counts), `team`
  (fx for everyone), `front`, `stars`, `convert`, `revive_first`, `summon`, `rally`, `fallen_rally` (the Warlord), and the
  ones aimed at the *other* side: `hex_strongest`, `hex_all` (the Hexer) and `drain` (the Chronomancer).

### Units and traits

60 units (13, 14, 14, 11 and 8 at tiers 1-5), six summons (Treant, Bog Imp, Skeleton, Turret, Mire
Spawn, Sapling) and four monsters, all in `app/overlords/data.py`. Each unit has one origin and one or
two classes. Every trait can reach its top tier: origins have 6-9 units, classes 6-10. A trait counts the
*different* units carrying it on the board and switches on at thresholds (2/4/6 or 2/4). 16 traits:
origins Emberforged (attacks burn), Thornwood (regrow HP), Tidecallers (mana each second), Gravebound
(rise once), Skyborne (dodge), Ironhold (armor and resist), Starlit (cheaper abilities), Mirefolk
(attackers are chilled); classes Vanguard (shield at the start), Duelist (attack speed stacks), Ranger
(double strikes), Arcanist (the board's ability power), Mystic (the board's resist and a little
regrowth: resist alone did nothing, since most damage is physical), Assassin (leap to the back line,
crits), Summoner (stronger summons), Warden (max HP).

Abilities are data: a list of steps (`hit`, `heal`, `shield`, `buff`, `summon`, `dash`, `mana`, and
since the roster review `grow`, `taunt`, `vanish`, `cleanse`, `pull`, `zone`, `raise`, `devour`), each
aimed by a selector (`target`, `around_target:1`, `line:5`, `chain:5`, `cluster:1`, `lowest_enemy`,
`highest_hp`, `lowest_ally`, `nearest_allies:2`, ...). A hit can drain (`heal_frac`), mark (`amp`),
wound, burn mana, knock back, execute, hit harder on the hurt (`missing`) or refund mana on a kill; any
step can land later (`delay`, marked on the ground first). A summon can bring several (`count`); a
`static` summon (the Turret) never moves. A unit can also have a `passive` (fx, as items give) with a
`passive_text`. The docstring at the top of `data.py` lists them all. A new unit needs no new code
unless it needs a new step or selector (add it to `sim.Fight.step_*` / `select` and to `STEPS` /
`SELECTORS`, and teach `fight.js` and `abilityNumbers` in `main.js` any new event or field).

**The roster review** (November 2026, the owner asked for units, items and commanders that are more
interesting and unique): every unit got a trick of its own (Bramble Guard and Bog Knight taunt, Marsh
Lurker vanishes and strikes from the mud, the Toad Brawler and Kraken Caller pull, Iron Sentinel, Cloud
Monk and Wind Archer knock back, the Mire Witch and Forge Hound mark, Thornling wounds,
Ember Mage's meteor lands where enemies bunch, Thorn Dryad, Lava Giant and Ember Wyrm leave burning
ground, Starlit Novice and Rune Smith grow, the Lich and Bone Tyrant raise the fallen, the Bog
Colossus swallows, Grave Digger, Sky Sprite and Grave Knight execute, Ghoul Reaver chains kills...), ten
units were added (Toad Brawler; Cinder Priest, Bog Knight, Wind Archer; Moonshadow, Bog Colossus, Rune
Smith; Ember Wyrm, Old Mossheart, Bone Tyrant: tier 5 had no Emberforged, Thornwood or Gravebound
unit), the items and commanders above changed, and nine artifacts came in.

### Extra abilities

The owner asked (November 2026), taking Guildrun's choice of abilities at each rank as the model, for
units with special abilities and a choice of an extra one when three copies level a unit up. Every unit
keeps its own ability; at 2 stars, and again at 3, its owner picks one more (`TALENTS`, "talents" in
code, "extra abilities" on screen):
- The options at a star (`talent_options`) are the extra ability of each of the unit's traits at that
  star (every trait has one at 2 and one at 3: 32), then one that strengthens its own ability (2:
  Empowered {ability}, 30% stronger; 3: Mastered {ability}, 30% stronger and 20% less mana;
  `talent_name` fills in the ability's name). So every unit has three or four, and units sharing traits
  share options. Trait ones work without the trait being active: Kindling (attacks and ability burn),
  Deep Roots, Flowing Tide, Undying, Featherstep, Iron Skin, Starlight, Sludge, Bulwark, Momentum, Split
  Shot, Arcane Focus, Mending, Ambusher, Bigger Brood, Stalwart; at 3 Inferno Heart, Thornmail, Tidal
  Surge, Death Knell, Tailwind, Unbreakable, Supernova, Bog Grip (attacks mark), Challenge, Executioner,
  Deadeye, Spellsurge, Sanctuary, Shadowstep, Grove Call (saplings), Colossal.
- Each is `fx`, as items use, applied after items (`sim.Fight`). New fx for them: `cast_power` (the
  ability's power, including what it summons: `boost_summon`), `cast_burn` (the ability burns what it
  hits), `mark_on_hit` (attacks mark for `MARK_SECS`).
- A unit dict has `"talents"` (picked keys, in star order). Nothing else is stored: what's waiting
  (`Room.talent_offer`) is the next star in `TALENT_STARS` the unit has reached without a pick, so a
  unit that becomes 3 stars without its 2-star pick picks that first. `choose_talent` (message
  `{"t": "talent", "id", "k"}`) works in planning, fights and drafts and takes effect from the next fight.
  A merge keeps the first copy's picks (else the first copy that has any); selling loses them.
- Nothing is picked for a person: an unpicked unit fights without one. The choose overlay opens for
  each waiting unit (after any commander or augment pick), with Later; a gold + on the unit and a
  button on its card bring it back. On phones the floating "Choose an extra ability" button is hidden
  (it covered the shop), so the + and the card do it. Bots pick at once (`bots.pick_talents`, favouring
  their planned traits).
- The browsers get them in `state.me.talent_offers` ([{id, unit, star, options}]), as the fifth field of
  bench rows and the seventh of board rows, and as the eleventh of a fight's `start` rows (fight info).

Tuned with a scratch head-to-head (one unit with each trait pick against the same board with the
own-ability pick instead, 120 fights each): all within 43-62% after one pass (Spellsurge, Grove Call and
Challenge were far weaker at first; Tailwind, Colossal and Featherstep stronger).

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
6. ~~Records in `data/overlords.db`, one big balance run, this doc, the games page, README and
   CLAUDE.md~~ (done, November 2026: the plan is complete)

Listed on the games page (after Holdfast); since the phone work it says it works on phones and computers.

### Records

`save.py`, SQLite at `data/overlords.db` (`OVERLORDS_DB` overrides it; the check and the smoke test
use a temporary one). Only records, no unlocks, as the owner chose. A finished match with at least
one person in it is saved: each player's place, commander, augments, final traits and final board
(taken when they go out, `Player.final`). People are known by their browser's token, stored hashed
(`save.who`), so the record follows a browser, not a name. The lobby shows your record (games, wins,
top-two finishes, average place, favourite commander and trait, the last five matches) and the Hall
of Overlords (most wins, then the best average place, under each browser's latest name); the end
screen shows every player's commander and final traits and your updated record. Records are read only
in the lobby and at the end (`send_state`), and a database error never stops a match (logged).
`Room.saving` is off in the checks' and the simulator's rooms.

### Art

- 70 sprites (60 units, 6 summons, 4 monsters), one 32x32 drawing each, by code in
  `tools/overlords-art/` (`units1.py`: Emberforged, Thornwood, Tidecallers, Gravebound; `units2.py`:
  Skyborne, Ironhold, Starlit, Mirefolk, the other summons and the monsters; `units3.py`: the ten units
  of the roster review and the Sapling). They use Roguelike
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
- **Icons and portraits** (November 2026, the owner asked for more art): `icons.py` draws 16x16 icons
  on a 16x16 grid (the same letters, shading and outline): every item (emblems are the trait's glyph in a
  gold badge), every trait's glyph, and the projectiles ranged attacks and spells fly as (`proj:*`,
  chosen in `main.js` `PROJ`, by unit, else by origin). `portraits.py` draws each commander as a 32x32
  bust, facing the viewer. `build.py` writes them to `art/icons.png` and `art/portraits.png` (with the
  two ground tiles the board's hexes are filled with, `GROUND`), and their maps to `js/atlas.js`
  (`ICONS`, `PORTRAITS`). In the page, `icon()`, `portrait()` and `sprite()` in `main.js` make an
  element from a sheet (crisp, at any size): items on the item bench and under units, trait icons in
  the trait list and on shop cards, the unit's sprite on shop cards (behind a gradient, so the name
  stays readable), in drafts, in the info panel and the damage chart, commanders' portraits on the
  choice screen, the commander panel and the players list. `overlords-check.py` fails if an item,
  trait or commander has no art.
- **Fights 1×/2×** (header, remembered): plays fights at double speed. The server's timing doesn't
  change; a fast player just sees the result sooner and waits for the others.
- The owner hasn't reviewed the looks yet (in the other games the owner picks from options): expect
  changes unit by unit.

### Charts

- **Damage** (right panel, the owner asked for damage charts): each unit's damage dealt (stacked by
  type: physical, magic, true, burn; a colour set checked for colour-blind readers against the panel),
  damage taken (before shields soak it), or healing and shields given, for the watched player's fight:
  live as it plays back, then the last round's fight while planning (`S.lastFights`). Built from the
  fight's events (`tally` in `main.js`): `d` carries its source and type, `h` and `s` their healer.
  Burning ticks every 0.05 s, so the sim tells it in lumps of `BURN_LUMP` per source (before, a tick
  under 1 HP was never told at all).
- **HP over the match** (end screen): every player's HP after each round (`Player.hp_log`, sent only
  when the match is over), a line each in their colour, named at the end, a round's numbers on hover.

### Leaving a match

The **Exit** button in the header asks first (if you're still in the match), then sends `forfeit` and
goes back to the menu. `Room.forfeit` knocks the player out on the spot (`knock_out`: the last place
still open, units back to the pool), as if their HP had hit 0; they can't come back in, though they can
watch if they rejoin the room. If that leaves only bots standing, the match ends there (`finish`: the bots
placed by HP) and is recorded. Closing the tab instead keeps the seat, as before: the board fights on
untended and the browser can rejoin.

### Phones

(November 2026, the owner asked for it to be more mobile friendly.) Below 820 px of width or 560 px of
height (`COMPACT` in `main.js`, the same media query as the block at the end of `game.css`; keep them
matching), the side panels fold away:
- Upright: the header wraps to two lines, the players become a strip above the board (portrait and HP;
  tap to watch), and items, the shop's four buttons and the five cards sit below it. On its side: players
  down the left, the board in the middle (the banner over its empty top), items and shop on the right.
- **Sheets**: Traits, Commander (it reads "Power ⚡" when the power is ready) and Damage open from the
  buttons beside the items, one at a time, from the bottom (on its side, from the right):
  `body[data-sheet]`, set by `openSheet`; the sections are moved by CSS only (`aside { display:
  contents }`), so desktop and phone share one set of elements.
- **Touch**: dragging still works (the canvas is `touch-action: none`). A tap on your unit picks it up
  (`S.sel`, outlined in gold, your half tinted); a tap on an empty hex or bench slot moves it there, a tap
  on it again puts it down; its info card has **Sell**. A tap on any other unit, on a trait, or on a unit in
  a fight shows its card (`S.pinned`: it stays, with a close button, a fight unit's numbers live), and a
  long press does the same for shop cards and items without buying or picking (`hoverInfo`). The info card
  floats over the top of the board; opening a sheet closes it. Mouse hover is unchanged, and the tap rules
  apply only to touch and pens (`pointerType`), so a desktop click never moves a unit.

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
  player takes the result). Pairings avoid a repeat opponent when they can, and are decided when
  planning starts (`pair_up` into `Room.next_pairs`, sent as `state.pairs` during planning; `next_foe`),
  so everyone sees whose board they'll meet; `begin_fight` uses them, pairing again only if someone left.
- **Who you fight next** (the owner asked for it, November 2026): the player list marks your next opponent
  (`next foe`, or `next: a copy` for a ghost fight; ⚔ on phones), the banner names them, and while you look
  at your own board theirs is drawn faded on the top half where it will stand (`foeUnits` in `main.js`,
  mirrored as `to_grid` does), its units' cards on hover or tap (`foeAt`: `foe: true`, `owner`, their
  traits). On monster rounds the monsters show there instead (`rules.pve_boards`).
- `bots.py`: `arrange` (melee in front, toughest in the middle; ranged at the back, assassins last;
  the column orders can be changed) and the bots' turn (`play`): a style (`STYLES`, below), two traits to
  aim for, a level schedule (the Oracle reaches 5 a round early), gold kept by style (`keep_gold`), free and
  cheap rerolls whenever they help, more when rich or below their panic HP, shop powers (gold, rerolls, XP, units, items) before
  shopping and fight powers only against players, items where they fit (`equip`, `fit`), and picks of
  commander, augment, draft and extra abilities (`pick_talents`). Then `place`, once every bot has played
  (`start_plan`): hard bots fight the board they meet next (or the monsters) with each of `SHAPES` on
  one seed and keep the arrangement that ends best. They act through the same room methods as a browser.
- **Bot styles** (the owner asked for bots that play differently, November 2026): each bot gets one at
  random when the match starts (`Player.style`, shown in the 🤖's tooltip): `tempo` spends everything;
  `econ` banks gold from round 4, a step of interest more each round up to its cap, levels with what's
  over and spends it all at level 8 or under 30 HP; `fast` levels a round early all match and favours dear
  units; `trait` goes all in on whichever trait it has most units of by round 5. A fifth, a reroller
  (stay low, three-star cheap units), was tried and dropped: see Gotchas.
- **The info card** (`infoBody` in `main.js`: `unitCard`, `itemCard`, `traitCard`; the owner asked for a
  UI pass in November 2026 so item descriptions, unit stats and trait bonuses read clearly). A unit's
  numbers are the server's: `Player.card_stats` sets a fight up (`sim.Fight`, not run) with the player's
  board and `extras` and reads `sim.Unit.stats()` (traits, items, picks, augments and the commander
  counted; bench units get items and picks only, as they don't fight). They ride as the eighth field of
  board rows and the sixth of bench rows, and as the twelfth of fights' `start` rows, so fight cards (yours
  and the enemy's) have them too. The card shows them as tiles beside the bare unit's (green and red),
  each tile's meaning on hover, armor and resist as damage cut, the unit's traits with what each is doing
  for it (or would, fielded, for shop and bench units), its ability's numbers times its ability power and
  Empowered pick, and each item's effect. The trait list says what each trait gives now (or at its first
  tier); a trait's card lists its tiers with the one reached marked, counts augments, and lists emblem
  holders. Effects in words: `FX_WORDS` / `describeFx` (every key traits use).
- Browser: `js/main.js` (screens, canvas, dragging and tapping, the shop, panels and phone sheets), `js/fight.js` (`Playback`:
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

- On touch, `pointerleave` fires as the finger lifts, so hover handlers must ignore touch (`hoverInfo`
  does) or every card flashes and vanishes. Disabled buttons get no pointer events at all, so a long press
  can't show a draft option that isn't yours to pick.

- The fights message is sent *before* the state that switches to the fight phase, so the browser
  builds its Playback when that state arrives (and on `fights` if the phase is already fight).
- Untargetable units (vanished, swallowed, or the Hourglass's moment out of time) are left out of
  `Fight.foes`, so nothing aims at or hits them; zones and burning still reach them. A side whose units
  are all out of reach doesn't lose: the fight goes on until they come back.
- A knockback on a melee unit shoves its own target out of reach, so it has to walk after it: the first
  balance run had the Iron Colossus and Gale Dancer weak for it, and they lost theirs. Knockbacks suit
  ranged units and short stuns.
- Monsters and summons are `summon: True`; executes work on them too (an early version skipped them,
  which made executes do nothing in monster rounds).
- `raise` puts skeletons where units fell (`Fight.corpses`); two units can fall on the same hex, so
  each spot is checked free as it's used (doubling up once broke the board's record, `occ`). The check
  steps random fights and fails if two units ever share a hex.
- `d` events carry the HP left after shields; shields soak damage first, so the number shown can
  exceed the HP lost. `v` snapshots every 0.5 s correct HP, mana and shields.
- During a draft, `Room.ends` follows the current pick's deadline, so code (and the checks' clock)
  that winds to `ends` keeps moving. Draft options are held out of the pool while on offer: count them
  when checking the pool adds up.
- Marks (abilities' `amp`, Bog Grip's `mark_on_hit`) share `Unit.amp` with the Hexer's hex, so they go
  through `Fight.mark`: a mark never replaces a stronger one that's still on and never shortens one.
  Before November 2026 a Mire Witch's or Forge Hound's mark cut the Hexer's all-fight hex to 4 s.
- The card numbers are worked out in `Room.public` on every state, so only when a person is in the room
  (bot-only rooms, as in the checks and the simulator, skip them: a few tenths of a millisecond a player).
  A new fx key a fight knows should go in `Unit.stats` if it changes a number the card shows.
- On desktop the info card floats over the left column (`position: absolute` in `.main`), not at the foot
  of the right one: it needed the height, and over the right column it hid the trait being hovered,
  which flickered. Phones keep it fixed at the top, at most 42% of the screen and scrolling, with Sell and
  the pick button moved up under the unit's name: any taller and it covered the hexes tap-to-move needs
  (the phone check caught it).
- **Interest** was 1 per 10 saved, and saving lost: in head-to-heads normal bots that spent everything
  placed 2.18 against 2.82 for ones keeping 20-30 gold. So the owner asked for saving to be worth it, and
  the style tournament (`tools/overlords-styles.py`: every match seats the four styles, shuffled; 300
  normal matches a try, about ±0.07) chose 1 per 6 (`INTEREST_PER`): per 10 had the saver last at 2.82, per 8 at 2.73, per 7 at 2.56,
  per 6 at 2.45 (second, and winning as often as the leader), per 5 first at 2.24 (too much). Dearer XP
  (5 gold) made the saver worse. Then the auction gave saved gold a second use and the saver led at
  2.0-2.1 even with one lot each (without auctions the four styles were 2.41-2.66), so interest went to
  1 per 8: saver 2.33, fast 2.45, trait 2.46, tempo 2.76 (per 7 with weaker unit lots came out the same).
  Retest with the tournament before touching `income`, interest, XP or the auction.
- **Three-stars of cheap units are out of reach.** The reroller bot kept 10 gold, stayed on level 5 and
  rerolled the rest for up to three cheap targets: with about 7 gold a round it reached 8 of 9 copies of
  its best by round 11, too late, and placed 3.1-3.3 whatever was tried (level 6, 1-gold rerolls, pools
  of 18/15/12/8/6). Tier 4 and 5 can't three-star at all (pools of 7 and 5; 9 copies needed). Making it a
  real strategy would take a much richer economy; the owner hasn't asked for that.
- Measured bot changes: shop powers before shopping were worth about 0.07 of a place (the Oracle's reroll
  used to come after the bot had shopped, so the next round's roll threw it away); matching items to
  units, nothing measurable. Hard bots against the old hard bots: 1.97 against 3.03 (79% of wins);
  without `place`, 2.07.
- `place` runs `len(SHAPES)` real fights per hard bot per round (about 25 ms a bot), on the server's
  loop; normal and easy bots run none, so the simulator's default (normal) stays quick.
- A unit can die in its own turn (an Ember Mantle's burn kills a foe whose death burst kills the holder),
  so the tick loop checks it's still alive before it acts; before November 2026 the holder went on to
  cast while dead and a dash crashed the fight (`occ` had no hex for it). The check covers it.
- Trait counts ignore duplicates and summons. Summons and monsters have `"summon": True` and cost 0,
  which keeps them out of the shop and the pool.
- The auction holds its unit's three copies out of the pool, like a draft's options: the checks' `copies`
  counts them. Relics are kind `relic` so `random_item` (the armory, drafts, augments, powers) never
  draws one; keep it that way for anything auction-only.
- The simulator winds the clock to `Room.ends`, so its minutes count each auction's full 25 s, though a
  bots-only auction closes at once (nobody to wait for).
- `Room.clock` is swappable: the check winds it on to play whole matches instantly. Real code must
  use `self.clock()`, not `time.monotonic()`, for phase timers.
- A mana-from-damage loop once let a lone 1-star Star Queen shield herself for 25 s against six
  units; that's what `MANA_HURT_MAX` and `MANA_LOCK` prevent. Watch for it with any new shield or
  heal that scales with hits taken.

## Checks and numbers

- `python3 tools/overlords-check.py` (~5 s, in `check-all.sh`): data, every ability fires at every
  star, every item in a fight, each of the roster review's tricks (taunts, vanishing, pulls, shoves, zones,
  delayed blows, raising, swallowing, executes, wounds, multishot, death bursts, the Hexer and
  Chronomancer, saplings), nobody ever sharing a hex, determinism, board rotation, 300 random fights finish, the room's rules
  (buying, merging, limits, moving, selling, the locked board), items (rarities, prices rising, equipping,
  taking off, emblems, the Crown), every commander power, every augment, a draft, the armory (buying,
  prices by rarity, the Forgemaster's discount, a locked shop keeps it, its odds early and late, no
  monster drops), extra abilities (options at every star for every unit, picking once, kept through a
  merge, lost with a sale, a skipped 2-star pick first, bots picking, and Stalwart, Empowered, Sludge,
  Bog Grip and Kindling working in a fight), the unit cards' numbers (board, bench and fight rows, and
  none worked out in a room of bots), the first fight waiting for a commander, Exit, the match
  ending when the last person is out, opponents paired when planning starts (the fights follow them, the
  browsers see them, a hard bot tries every arrangement, someone leaving re-pairs), a unit killed in its
  own turn not acting, the auction (three lots, bids checked, the winner pays, no shopping meanwhile,
  unsold units back in the pool, results shown, relics never in the armory), build-around augments (the
  counts, the front row, gold, stars and conversions in `extras`, the fight and the unit cards; auction
  augments never offered as an ordinary pick), and three whole bot matches with the pool conserved.
- `node tools/overlords-smoke.js --serve` (~30 s, in `check-all.sh`): two browsers, a room with two
  bots, commanders picked, buy/drag/sell, a fight played back and watched, the next round, an item
  bought in the armory and dragged onto a unit.
- `node tools/overlords-phone.js --serve` (~15 s, in `check-all.sh`): an emulated phone with touch,
  upright then on its side: the page fits the screen, Exit, a long press shows a shop card without buying, a tap
  buys, tap-to-move onto the board, Sell from the card, the traits and commander sheets, a tap on a unit in
  the fight.
- `python3 tools/overlords-sim.py [N] [--level L]`: whole bot matches (a quarter of a second each):
  rounds and minutes, each commander's average place (2.5 is even), the most picked augments.
  `--fast` plays 4.
- `python3 tools/overlords-styles.py [N] [--level L]`: the bot style tournament (two minutes for 300
  normal matches): each style's average place. Rerun it before changing income, interest, XP or prices.
- `python3 tools/overlords-fight.py [N] [--size S]`: each unit's win rate against boards of the
  same costs (50% is right at every cost); `--traits [N]` each trait at each tier against
  cost-matched boards; `--show SEED` prints one fight. Both together: about a minute.

Latest numbers (late November 2026: units and traits after the second balance pass; whole matches after
the auction, build-around augments and interest at 1 per 8; ~6 minutes to rerun the three tools, plus the
style tournament):
- Units, 2000 cost-matched 7-unit fights (`overlords-fight.py 2000 --size 7`): 18 ms a fight, average
  21 s, 1.7% hit the cap. 58 of 60 within 42-58% (each about ±2.5% at ~400 fights): just outside,
  Thornling 40% (weak) and Bone Tyrant 58.5%. This pass: Duelist's stacks 0.13/0.14/0.16 (was
  0.09/0.11/0.12; Duelist 2 was 38%), Ashling 50 mana, Iron Crossbow's bolt 260/390/580 and 70 mana, Iron
  Duelist's Riposte 45/70/100 attack, Thorn Shaman 920 HP and 70 mana, Starlit Archer's passive 20%, Ghoul
  Reaver 580 HP and a smaller Feast; Assassins gained dodge (15/18/22%), which also lifted Ghoul Reaver and
  Marsh Lurker. A scratch spot test (800 fights with the unit always fielded) agrees with the tool within
  noise (Ghoul Reaver 61% in both before its trim).
- Traits, 120 fights a tier (`--traits 120`, about ±4.5%, and noisier than that in practice: Assassin 2
  read 42% here and 56% in a 300-a-tier spot run): first tiers 42-57%, the 4-tiers of the 2/4 traits
  58-82%, the top tiers of 6 at 66-82%. Every ladder rises.
- Whole bot matches (`overlords-sim.py 300`, normal bots, a random style each, after the auction and
  build-arounds): 17.4 rounds (14-21), about 17 minutes at full timers (the simulator counts each
  auction's 25 s). Commanders 2.11 (Gambler) to 2.78 (Beastmaster). About ±0.15 of noise.
- New augments, 200 matches (small samples, about ±0.25 at 20 picks): Bladework 1.92 over 51 picks and
  Elite Guard 1.86 over 21 were trimmed afterwards (4% to 3% a unit; 20% and 20 to 15% and 15, not yet
  rerun); the rest 2.1-3.0, within noise. Bots rarely take Kinship or Spellweave (their boards seldom
  count enough). At the auction, unit lots always sell (14-17 gold), relics most of the time (7-11),
  auction augments about half the time.
- The style tournament (`overlords-styles.py 300`), interest per 8 with auctions: econ 2.33, fast 2.45,
  trait 2.46, tempo 2.76. (Before the auction, at per 6: fast 2.31, econ 2.43, trait 2.58, tempo 2.68;
  hard bots then: fast 2.27, trait 2.35, tempo 2.59, econ 2.78.)
