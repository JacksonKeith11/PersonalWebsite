# Saltbound (/games/saltbound)

Read this before changing anything in `app/saltbound/`, `app/static/games/saltbound/`, or the
`tools/saltbound-*` scripts.

**Status: built and public.** All ten classes play whole runs, and the game is listed on `/games`.
The first half of this doc is the design the owner signed off on, with the answers they gave while it
was built; "How it plays now" is the game as it is. When a change alters how the game works, update
"How it plays now" (not a new section at the end) in the same commit.

## What it is

A co-op strategy RPG for 1-3 players in the browser, in the same genre as IronOak's *For The
King*: a party crosses a hex overworld, fights turn-based battles on a separate screen, shops in
towns and races a worsening world to a final boss. It is its own game, not a copy: own setting,
own combat system (dice you assign, not slot rolls), own names, own UI. Don't borrow For The
King's content, names, art or layouts.

The setting is the **Sinking Archipelago**: islands are going under, and the rising tide is the
run's clock: every rise makes the enemies stronger. A run is one sitting of 60-90 minutes. Players are on a voice call, so there's no
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
  pool size and how often the tide rises. Nothing structural.

### The world

- **Hex map, generated per run from a seed** (stored in the save, so a restored run is
  identical). About 30×22 hexes: three regions around a central peak. About 30 map turns per run.
- **Map turns are planned simultaneously.** Each player queues their hero's path, sees the other
  heroes' planned paths as ghost trails, and clicks Ready. When all three are ready, everyone
  moves at once. No timer.
- **Vision outruns movement** (owner's request): heroes see land 5 hexes around them (Farsight and
  Wayfinder +1, Trackers spot enemies 2 further), more than a turn's walk, so the result of a move is
  in view. **The turn is forecast** (`Game.forecast`, sent with every view): from what the party
  can see, where each planned route ends, where each visible enemy group will step (red arrows),
  which fights start and who'll be pulled in (a crossed-swords marker with a dot per hero, dashed
  lines from each joiner), and what each hero lands on. A "This turn" panel says it in words, one
  line per hero, and the hex tooltip says whether walking there starts a fight and who'd join. The
  reachable area is lit, with a bold outline and red rings on enemies you could walk into. The
  forecast uses the same rules as the turn (`group_step` is shared with `move_groups`), and in
  testing matched what happened every time; hidden enemies can still ambush.
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

- **The tide rises every 3 turns** (Story 4) and **every enemy grows stronger** (owner's request,
  replacing the old flooding): `SURGE` in `tuning.py`, 0.45% HP and damage per rise (0.3% until Nov 2026), on top of
  difficulty and tier. The land never changes: no hex floods and no town sinks (the flood could cut a
  party off from the town it needed to cross to another island). After rise 10 more enemies come
  ashore. **Each rise brings something ashore** (owner's request: hide the percentage, show visible
  events that grow as the run goes on; see "Tide arrivals"). The top bar shows only the turns until
  the next rise (the percentage is hidden, owner's request); its tooltip names what the last rise brought.
  There's no turn limit: the growing enemies are the pressure.
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

  | Region | Enemies | Objective (dungeon: 3 fights with two forks; see "Dungeon forks") |
  |---|---|---|
  | Coral Shallows | drowned sailors, crabfolk, reef creatures | the Sunken Chapel |
  | Smugglers' Keys | pirates and a tide cult | the Black Fort |
  | Stormcrag | storm elementals, harpies, mountain beasts | the Lighthouse |
  | Central peak | | **The Drowned Crown**, the tide-king raising the sea; fought on the last dry peak |

### Combat

- **Starting a fight**: walking into an enemy starts a fight. Every hero within 1 hex of that
  hex joins, and so does every enemy within 1 hex. Moving together is how you team up.
- **Rows are for enemies only** (owner's request: hero rows let one person soak everything while
  the others took nothing, which feels bad in a multiplayer game). At most 5 enemies (3 front, 2
  back); melee reaches only their front row while it has anyone. Heroes and summons are one group:
  enemies pick targets by their own rule (random, weakest, strongest, or whoever hurt them most last
  round), so damage spreads unless someone chooses to take it (Guard, Taunt). There's no Shift.
- **Dice**: each hero has 2 base dice from their class plus one die each from weapon, armor and
  trinket: 5 at most. (A second trinket slot was tried and removed at the owner's request: the sixth
  die took Hard from about 37% to 51%. Save v7 moves a second trinket into the bag.) All of a hero's dice are rolled at the start of each round. Sizes d4-d12,
  plus special dice with custom faces (shield faces, blanks, ×2) from uncommon rarity up.
- **Actions** are cards with dice slots and a requirement, e.g. "Slash: one die ≥2, deal its
  value", "Fireball: two dice summing to 10+", "Lunge: exactly 6". A hero has 2 class actions,
  1-2 from their weapon, and any learned through levelling: 4-6 on screen.
- **A round**: dice are rolled; enemies show **intents** (what they'll do and to whom); the party
  plays dice on actions together, and **each action happens the moment it's played** (owner's
  request, after Slay the Spire 2's multiplayer): its dice roll, it hits or misses and its effects
  land before anyone plays another, so the order is whoever played first. There's no undo. You
  needn't wait to see a roll: plays **queue** (owner's request), so you can pour every die into
  the last weak enemy while the first roll is still animating; an action whose enemy died first
  goes to the weakest enemy in reach instead. When everyone has clicked Ready, summons and pets
  act, then enemies in speed order.
- **Enemies roll real dice** (owner's request: the same dice system as the heroes, so a "d6 attack"
  is visibly a d6). Each enemy has a pool of dice and named moves that use some of them (see
  Enemies). The intent shows the move's name, its dice and flat bonus ("2d6+3"), the range, any
  rider ("on doubles: Root", "5+: Stun") and who it's aimed at; when the enemy acts it rolls those
  dice in the roll tray, face by face, then shows the total. Weaken (Feint and the like) lowers the
  bonus; Pickpocket snatches the biggest die out of an intent; Spotter and Read the Blade make an
  enemy roll its dice early, so the intent shows the exact number.
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
  sits idle. (A support die for living heroes outside the fight was tried and removed at the owner's
  request: it took Hard from 42% to 59%, because the bots then fought dungeons alone.) The run ends when the pool is empty and the whole party is down.

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
- **Gold is per hero.** **A won fight's loot is one shared pool** (owner's request): everyone who won
  sees the pool and claims from it, first claim wins (`Game.offer_pool`, `s["pools"]`, a `pool`
  dialog per claim). The owner set its size: **4 items, 3 claims** (`POOL_SIZE`, `POOL_CLAIMS`), the
  claims going round the winners (alone, you claim three; two winners, two and one); the fight sets
  the rarity, not the size (a dungeon's last fight or Champion's Hall a rarity up). What nobody
  claims is left behind. Loot found alone (wrecks, quests, events) is a personal pick. Either way an
  item can go straight to an ally within a hex (`to` on the `choose` message; into their empty slot,
  else their bag). Heroes can trade freely on a shared hex or in a town. Every item shows what a town
  pays for it (40%, 60% with Haggler; `Game.sell_price`).
- **Items**: weapon, armor and trinket slots (`I.SLOTS`; each gives a die and maybe an action or
  passive) plus
  a bag with no limit (owner's request; Deep Pockets became +1 reroll and +3 gold a win). 4 rarities (common, uncommon, rare, legendary). No durability. Consumables: potions,
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
  3. **Class claim**: a card per class with role, HP, base dice, map ability and sample skills.
     Players claim any free class and can swap until the host clicks Start; the host picks for
     unclaimed heroes. On resume, the saved heroes are shown instead.
  4. **Map**: the hex map in the middle; three hero cards down the left (HP, dice, moves left,
     Ready state); top bar with turn, tide and the rising tide's enemy strength; other heroes' planned paths as ghost
     trails, like Board Brawl's route previews.
  5. **Combat overlay**: full screen; the party in one column, enemies in their rows, facing each other
     across the middle at a good size (owner's request: big fighters, rows close together); intents
     above enemies (a Stunned enemy shows "Stunned · skips its turn" instead, and no arrow); each
     hero's dice tray and action cards along the bottom; allies' placements visible live. **What
     allies do is spelled out** (owner's request): a caption over the stage names an ally's action,
     its target and what it does; every action animates by kind (`abilityFx` in `combat.js`: a melee
     lunge and slash, an arrow, a spell orb and burst, a thrown bomb, a green glow on whoever is
     healed, a blue shimmer for Armor); and the "This round" strip lists each action with who did
     it, the damage, healing, Armor and kills it caused (`done[i].out`, from `Game.act_outcome`),
     with the roll and the details on hover. Hovering an ally's portrait lists their actions, and
     clicking one (when not aiming) opens their full sheet over the stage: every action with its
     cooldown, their passives and this round's dice (`allyPanel`); clicking your own other hero
     switches your tray to them. The big skills have signature effects (`SIGNATURE` in `combat.js`:
     Fireball's orb and explosions, Earthshaker's quake, Chain Lightning's bolt, Cleave's arc, Lunge's
     thrust, Volley's arrow rain, Doom's sigil, Renew's party glow, Sanctuary's dome, Hymn's notes,
     summoning circles and more); anything else uses the generic effect for its kind.
     Clicking an ally's hero card on the map opens their sheet read-only (skills, gear, about).
     **Multiplayer clarity** (owner's request, after a two-browser test): another player's hero shows
     who plays it ("Vanguard · Alice") and the dice they hold this round under the portrait (spent
     ones faded, rolled ones numbered), so combos can be planned; the caption names the action now
     playing from its first roll (it used to linger on the one before); a backlog of plays still to
     show speeds playback up to 4× with a "+N more" badge; the "This round" strip keeps its last three
     plays in full and folds each hero's earlier ones into one chip, scrolled to the newest; a new
     round opens with "Round N" in the roll tray; the line under the stage says who is acting and
     who's next; floating numbers sit over the portrait on a dark backing, never on a health bar.
  6. **The results screen** (owner's request: one per hero per turn, `renderDialogs` in `hud.js`): what
     happened to the hero (event outcomes, gold, blessings, jobs, and each pick they make) and every
     choice it left them, on one screen: an event's options first (what they lead to can change the
     rest), then level-ups (one pick, and the new skill can change what gear you want), then spoils (a
     pool's claims grouped into one section). Picks name their queue entry (`choose` takes `i`; a pool
     can be passed whole with `all`), so they can be made in any order once any event is answered. What
     happened stays on the screen, through a fight an event starts, until one Continue (Enter). Gold,
     blessings and jobs go on it when it's up, and are toasts otherwise.
  7. **Town and shop panel**.
  8. **Run end**: win or lose, a per-hero summary (damage, healing, kills, items), the seed, and a
     back-to-lobby button.

  Plus a settings and pause overlay openable from anywhere (volume, animation speed, save and
  quit). Moving between screens fades or slides in under 250 ms: no hard cuts, no blocking
  spinners.
- **Onboarding**: no tutorial level. Every keyword (Burn, Mark, shield face) has a hover tooltip.
  A short dismissible hint appears the first time each system shows up (first planning phase,
  first fight, first level-up, first rise of the tide), and the game remembers which have been seen.
- **Readability**: enemy intents show an icon, a number and a colour, from a palette that's safe
  for colourblind players. Text is at least 14 px. Each action card shows its chance to hit
  with the dice picked before it's played.
- **Controls**: keyboard and mouse first. 1-5 select a die, Q/W/E/R/T place it on an action, Space
  for Ready. Animation speed 1×, 2× or instant. Don't break phones, but don't spend
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

The tools that grew out of this are under "Testing" below.

### Answers given while building

Asked of the owner during step 1 (keep to these too):

- **Look**: brass accent (`#c9a24a`) on deep navy-slate panels; Fraunces for headings and Inter
  for UI text; painted pixel hex terrain.
- **Saves belong to their players**: a save is listed for every browser (token) that played in
  that run, and any of them can resume it into a new room.
- **The clock** (changed at the owner's request): each rise of the tide makes every enemy stronger
  (see "The world"). It once flooded the lowest land, sank towns and lost the run at rise 15.
- **Heroes outside a fight** watch it live and can go back to the map to pre-plan their next path or
  shop in their town while they wait.
- **Sprites are bespoke**, drawn by `tools/saltbound-art/` with Roguelike Tactics' pixel kit.
- **Heroes are not sea-themed; only the enemies are.** Hero sprites are ordinary fantasy
  adventurers and the classes' starting gear has plain names (Hand Axe, Oak Staff, Wool Robe), so
  heroes carry over to future maps like the class data does. Sea flavour belongs to enemies, the map
  and its events. Each hero had four sprite options in `heroes.py`; the owner picked the Shieldbearer
  holding the Spear-warden's spear (`vanguard1`), the Sorceress (`arcanist2`) and the Cleric (`mender1`).
  New classes get four options the same way. Picks live in `build.py`'s `PICKS`; rebuild after changing one.

Smaller calls made while building, not yet confirmed by the owner:

- Frozen enemies hit for half (instead of losing their "weakest intent"; they have only one).
- Hard was first a rise every 2 turns; it's now every 3 (like Normal), and harder enemies make it hard instead.
- `SURGE` is small because the bots are very sensitive to it: 2.5% a rise took Hard from 39% to 8%,
  1% to 18%, 0.5% to 26% (bots that split up). The owner asked for it stronger (Nov 2026): 1.2% with the
  new bosses gave 34%, 0.7% 38%, 0.45% 46% (100 runs each), so it's 0.45%.
- The fight screen is HTML (sprites as pixelated images) rather than a Phaser scene, so targets,
  tooltips and intents are plain DOM. Phaser draws only the map.
- Movement is planned by clicking a destination; the cheapest route there is used.
- A hero on a wreck, or picking loot, holds the next turn until they choose (it's a reward dialog).

## How it plays now

The design above is what the owner signed off on; this part is the game as built. Where they differ,
this part is right, and `classes.py`, `content/` and the code are the last word on numbers.

### The map's choices

The owner asked for the map and its choices to be more interesting (Nov 2026: items 1-6 of a review).
Before, every place was free and looked the same from outside, every fight was worth taking, and
there was no reason to hurry, so the best plan was to visit everything. Content and numbers are in
`content/archipelago.py` (from "the overworld's choices"); the rules are in `game.py`.

- **What a place offers shows before you go** (`Game.setup_places`, run once at the start of a run and
  by the v8 save migration): each event hex has its own event from the start (`ev`), and the map shows
  its title, a risk (`event_risk`: safe, a roll could go badly, could turn into a fight; red or amber
  dot) and which classes would have another option. Wrecks show their loot's rarity (a coloured dot).
  Shrines show their blessing. Towns show their trade.
- **Opportunities** (`tick_opps`, `spawn_opp`, `opp_land`; `OPPS`): from turn 3, every `OPP_EVERY` (5)
  turns, while fewer than two are about, one turns up 3-14 hexes from the nearest hero and lasts a few
  turns: a **merchant ship** docked in a town with three wares a rarity tier better (4 turns), **drifting
  cargo** on a shore (loot and 10 gold for whoever gets there first, 3 turns), or a **wandering healer**
  at a camp (heals each hero who arrives to full and lifts curses, 4 turns). They're sighted even in the
  fog, ringed in gold on the map with the turns left, and listed under "This turn" (click to find).
  The bots go for one when they can reach it in time (about 3 hexes a turn).
- **Garrisons** (`grow_garrisons`, `garrison_of`): every `GARRISON_EVERY` (6) turns, each objective not
  yet cleared grows. The first two growths add an escort to its boss fight (drawn from its escort pool),
  later ones give its boss `GARRISON_BOSS` (15%) more health each, up to six growths. An objective cleared before
  its garrison ever grew weakens the Drowned Crown by `CROWN_CUT` (10% of its health) each. The map
  shows a "+N" on the dungeon, the tooltip and the boss fork say what's added, the top bar's
  objectives say when it next grows. This is the run's real pressure to keep moving (`SURGE` is tiny).
- **Places with a price**: `GUARDED_WRECKS` (3) wrecks have enemies camped on them (a lair-like group
  with an elite, from the region's middle groups): beat them and the pool is all rare. `DARK_SHRINES`
  (2) shrines are dark: the `dark_shrine` event offers +2 damage for 8 turns with Seasick, or 8 starting
  Armor for 8 turns for 8 HP, or nothing. Every lair guards a named **rare prize** (`prize` on the
  group, shown in its tooltip), added to its loot pool when it's beaten.
- **Town trades** (`spec` on each town; `TOWN_SPECS`), dealt round so each appears: a **smithy**
  reforges an equipped item into a random one of the next rarity for the same slot (30/60/100 gold),
  a **temple** lifts curses free and sells the party one revive (75, once per temple), a
  **cartographer** sells a chart of a region (15: every hex of it seen, so its places, wrecks and lairs
  show), a **fence** pays 20 points more when selling (60%, 80% with Haggler). A town's trade has its
  own tab in the town drawer (the fence's is the market). The bots use the temple and the smithy.
- **Event chains** (`chain` in an outcome, `start_chain`, `tick_chains`): **A Torn Chart** marks a
  buried cache 5-12 hexes away (a new place: 15 gold and a three-pick of better loot); **The
  Moneylender** lends 40 gold, and `LOAN_DUE` (8) turns later **The Debt Comes Due** asks 60 back
  (a Herald talks it down to 30) or a fight; **The Castaway** costs 3 HP, and the next town anyone
  enters `CASTAWAY_AFTER` (5) or more turns later he's waiting with 15 gold and a pick of rare loot.
  `hidden` events (the collector, the dark shrine) are never placed on the map.

### Tide arrivals

The owner asked for the rising percentage to be hidden and for visible events that grow as time goes
on, without blocking land or removing towns (Nov 2026). `SURGE` still applies, unseen. Content and
numbers are `TIDE_ARRIVALS` and the `TIDE_*` settings in `content/archipelago.py`; the rules are
`Game.tide_arrivals`, `tide_arrival` and `tick_tide` in `game.py`.

- **Every rise brings one arrival, two from rise 6** (`TIDE_TWO_FROM`), drawn by weight, early weights
  before rise 6 (`TIDE_LATE`) and late ones after, so the first rises are mostly gifts and later ones
  mostly threats: **Wreckage** (a new wreck on a beach 3-9 hexes from the nearest hero, uncommon or rare
  late), **visitors** (an opportunity: ship, cargo or healer, allowed one past `OPP_MAX`), **Raiders**
  (from rise 2: a region group lands 4-8 hexes away), a **war-band** (from rise 4: elite-led, with a rare
  prize) and a **beached leviathan** (from rise 7: the region's big threat as a stationary lair with a
  rare prize). An arrival that can't land (no free beach in range, or the caps) gives way to another.
- **Caps**: at most `TIDE_GROUPS` (3) tide-landed groups at once, apart from `MAX_GROUPS` (the map is
  usually full of ordinary groups, which once blocked every landing); at most `TIDE_WRECKS` (3) unlooted
  tide wrecks. Unfought landings go back to sea after `TIDE_STAY` (6) turns, a leviathan after twice
  that, so later rises can bring new threats.
- **Shown at once**: the hex is revealed, landed groups show through fog for `TIDE_SIGHTED` (3) turns
  (`sighted`), the browser shows a blue "The tide rises" banner naming the arrivals, a toast for each,
  pans to the first, and "This turn" lists what's still there (click to find). The news is
  `s["tidenews"]`, kept until the next rise; each item carries `g` (the group id) for groups, so the
  line follows a group that has moved.

### Jobs (town notice boards)

The owner asked for better quests (Nov 2026). Numbers are in `content/archipelago.py` ("Jobs on town
notice boards"); the rules are in `game.py` (`town_jobs`, `make_job`, `do_quest`, `tick_jobs`,
`job_land`, `complete_quest`).

- **Each board offers two jobs of different kinds** (`JOBS_PER_BOARD`), made when a hero first
  stands in the town (the start town's at the start of the run), never when it's looked at. Taking
  one takes the board down.
- **Kinds**: **Delivery** (carry a parcel to another town), **Clear a lair** (the nearest lair to the
  town), **Bounty** (a named elite crew appears when the job is taken, 5-10 hexes out; it runs from heroes
  within 3, a hex a turn, using `group_step`, and is always shown on the map; catch it to finish),
  **Salvage** (a wreck 3-12 hexes away, perhaps a guarded one: a hero standing on it once any guards
  are gone picks up the cargo, and that hero must carry it back to the town; it fails if they fall for good).
- **A deadline and scaled pay**: each job has `turns` (the trip at `JOB_PACE` hexes a turn plus the
  kind's `JOB_SLACK`) and fails when they run out (a wanted crew gets away). It pays every hero
  `JOB_GOLD` + `JOB_PER_HEX` per hex of the trip + the kind's `JOB_BONUS`, and one more thing
  (`JOB_REWARDS`): a pick of loot for whoever finishes it, a named rare item, +1 revive, a free go at the
  town's trade (`voucher` on the town: the next reforge, chart or temple revive there is free), or the
  town restocking its shop with better wares; the gold is cut a little when the extra is worth more.
- **On the map**: each job's next stop has a parchment tag with the turns left; "This turn" lists the
  jobs (click to find) and says when a planned move finishes one or picks up salvage, and when a fight
  is a job; hex tooltips name job targets and wanted crews.
- **The bots** take the board's job worth most per turn (lairs and bounties from level 3), at most two
  at once, and head for a job's next stop while there's time to finish it and no dungeon is due.

### Fights

- **A round** (`Combat.new_round`): enrage, elite affixes, Crown of Thorns, Poison and regeneration
  (`round_upkeep`); each hero's dice (`deal_dice`, `round_dice`), then what enemies did to them
  (`dice_attacks`); spirit dice for the fallen; boss and enemy upkeep (`crown_round`, `foe_round`);
  the enemies' intents. The party plays actions, each resolving the moment it's played
  (`do_place` → `resolve_action` → `run_ops`). When everyone is ready, summons and pets act, then
  enemies fastest first (`resolve_round`), then end-of-round effects (`end_round`: Triage, Burn,
  Doom, statuses ticking down, Armor clearing, the Crown's phase).
- **Dice roll when their action resolves**, not while planning. Planning shows each die face-down with
  its kind and size; each action card shows the chance to hit with the dice picked. Exceptions: Seer
  dice are rolled and shown while planning, Augur dice show only high or low, Fate dice show two faces
  (one comes up). The server never sends what a hidden or Augur die will roll (`fight_view` strips
  `sv`).
- **Dice kinds** (`dk`): seer, augur, fate, exploding, steady, heirloom, guard, `link:<group>`.
  **Faces**: numbers, `S` shield (blocks 3, `SHIELD_BLOCK`), `X` skull (0, and you take 3), `W` wild
  (its top face, passes any condition), `F3`/`I3`/`P3` (a 3 that also Burns/Freezes/Poisons). Class
  dice are `CLASS_DICE` in `classes.py`; item dice follow rarity (common plain or weighted; uncommon
  augur, steady, elemental, shield; rare seer, fate, exploding; legendary combinations and wild faces).
- **Hit or miss**: an action's `req` (`min`, `odd`, `sum_min`, `or_face`...) is checked on the roll.
  Misses scale with the risk (owner's choice): needing 6+, a pair or a big sum does nothing on a miss;
  needing 3+ to 5+, odd, or a modest sum does about half the die (`miss` on the action). A miss first
  lets Steady dice reroll, then spends one of the hero's automatic rerolls (1 per fight, more from
  Lucky Coin, Quicksilver), then Bloodstone's blood reroll. Pairs and straights are bonuses in
  amounts, not requirements.
- **Cooldowns** (`"cd": N`): only basic attacks are usable every round (owner's request). `FREE` in
  `classes.py` lists what's exempt (each class's basic, the Vanguard's Brace, Block, Flee and weapon
  actions except Sweep and Tidal). Everything else has 2; the biggest skills 3. Lift is once per rest
  (`per_rest`, the hero's `spent` list).
- **Guard dice** (owner's choice): every armor's die and two charms' carry `guard` and only go on
  defensive actions (`is_defensive`, sent as each action's `def`). Every hero has Block, so a guard die
  is never wasted.
- **Instant actions** (`"instant": True`) change dice instead of rolling for an effect: Perfect Form
  (a die rolls its top face), Bloodprice (+2), Loaded Dice (link two dice), Inspire, Hymn of Valor,
  Lend a Hand, Quicksilver, Bottle It, Counterpoint (flip a low roll), Splitting Flask (one die into
  two half its size), Grafting (two dice into one with their sizes added), Second Opinion (an ally's
  biggest hidden die rolls twice in the open, keeps the better), Transfusion. Dice changed by an
  instant can't be taken back. New dice join mid-round through `new_die` (sources `split`, `graft`,
  `tempo`).
- **Statuses**: Burn, Poison, Freeze (enemies hit for half), Shock, Weak, Vulnerable, Stun, Armor, Mark,
  Root, Hex (next round the biggest die becomes a cursed die: skull, 1, 2, 3), Doom, Dodge, Riposte,
  Thorns, Crescendo, Lifeline. **Enemies that attack your dice**, resolved when the next round's dice
  are dealt: Barnacle Crust (`lock`: the biggest die is dealt but unusable), Filch (`steal`: the
  biggest die is gone), Static Charge (`static`: next round a die rolling 1 or 2 shocks you for 3).
  The Undertow and Swallowed are boss states (below).
- **No endless fights**: from round 11 (`ENRAGE_FROM`) every enemy gains +2 might each round.
- **Fight kinds and their numbers** (all in `tuning.py` except `FOE_HP`): every non-boss enemy has
  1.45× its listed health (`FOE_HP` in `content/archipelago.py`). Enemies met on the map (roaming
  groups and lairs) get another 2.2× health but deal 0.65× damage (`ROAM_HP`, `ROAM_DMG`), so those
  fights last without being deadlier; elites and big threats skip both. **Event fights**: anyone on
  or next to the hex (and not in another fight) joins; enemies deal 0.7× (`EVENT_DMG`) and their
  health scales with who's there (`EVENT_HP`: 0.9× alone, 1.4× for two, 1.9× for three). On Hard,
  dungeon and roaming fights take about 3.8 rounds and the boss about 7.
- **Cross-hero combos** (`COMBOS` in `classes.py` for the words, `combos.py` for the rules, numbers in
  `tuning.py`), all plannable: **Pincer** (your first hit on an enemy an ally already hit this round:
  +2, or +5 if one of your dice shows a number one of theirs showed; once per enemy per round),
  **Covered** (your first hit after an ally Guarded or Taunted for you: +3), **Shatter** (hitting an
  enemy an ally Froze: +4, the Freeze ends), **Wildfire** (Burn meets an ally's Poison or the reverse:
  it erupts for Burn + Poison and half that to every other enemy, once per enemy), and the Bell-Warden's
  crack (below). `combo_peek` lists what a hit would score without scoring it (the bots use it);
  `combo_bonus` scores. The fight shows what's on offer: gold chips under an enemy, a gold ring on a
  known die that would score, a Covered hero's card. Who put each status on an enemy is in
  `fo["st_by"]`; the dice each enemy was last hit with this round are in `f["lastdie"]`.
- **Summons** (the Warden's Sprout, Call Bear, Swarm, Ancient Guardian) stand with the heroes, soak
  attacks, act after the heroes and last only for the fight; two per Warden (Pack Leader +1), a new
  one replacing the oldest. **The Ranger's hawk** is a die, not a unit (Companion a d6; Alpha a d8 and
  it strikes the weakest enemy for 3 each round).
- **Fleeing**: a die on Flee takes the hero back to the hex they came from; not from dungeons or
  bosses.
- **Spirit dice** (`f["spirit"]`, `do_spirit`): each round every fallen hero gets a d6, rolled in the
  open, to give to someone fighting. It's optional and never holds up the round. The fight overlay
  offers it in its header (or the bottom bar when the player has nothing else to do there); the map's
  action bar offers it too. The bots give it to the ally still to play holding the fewest dice
  (`bot.support`).

### Classes

| Class | HP (per level) | Map ability | Role | Tags |
|---|---|---|---|---|
| Vanguard | 50 (+6) | **Trailbreaker**: rough ground costs 1 | Tank | Bulwark, Juggernaut |
| Duelist | 24 (+3) | **Ambush**: a fight they start gives the party a free first round | Single-target damage | Flurry, Precision |
| Berserker | 32 (+4) | **Forage**: camps heal them fully | High-risk damage | Bloodlust, Rampage |
| Ranger | 24 (+4) | **Tracker**: spots enemies 2 hexes further | Ranged damage | Marksman, Beastmaster |
| Arcanist | 23 (+4) | **Farsight**: sees 1 hex further; spots cursed loot | AoE and burst | Elementalist, Hexer |
| Mender | 17 (+3) | **Field Medic**: resting on their hex heals everyone there an extra 10% | Healer | Restoration, Warding |
| Scoundrel | 22 (+3) | **Light Fingers**: +1 loot choice | Debuffs and loot | Poisons, Tricks |
| Herald | 18 (+3) | **Silver Tongue**: shops 20% cheaper; extra event options | Buffs for allies | Anthem, Discord |
| Alchemist | 21 (+3) | **Brewer**: a potion at each rest | Items and gadgets | Bombs, Elixirs |
| Warden | 26 (+3) | **Wildspeak**: forest costs 1 | Summons and control | Grove, Thorns |

Each class has two base dice, starting actions, and a pool of actions, passives and capstones that
level-ups offer 1 of 3 from (leaning toward tags the hero already has). `classes.py` holds them all,
and the lobby shows a chosen class in full. Skills whose key no longer matches their name (the keys
stay so saves load): `aura` is Second Opinion, `blessed_supplies` Triage, `bedside_manner` Diagnosis,
`encore` Counterpoint, `potency` Splitting Flask, `bramble_skin` Grafting, `second_wind` Steal Tempo,
`thick_hide` Bulwark Faces, `steady` Shieldwall. A few work differently from what the name suggests:
Pinpoint doubles if that enemy is aiming at you (bait it); Pickpocket snatches the biggest die from an
intent; Read the Blade and Spotter make enemies roll early so the party sees the exact number; Doom
deals 20 minus the die, so low rolls are good; Undying Fury hits back for 8 when you're knocked down.

Hero sprites: the owner picked the Shieldbearer with the Spear-warden's spear (`vanguard1`), the
Sorceress (`arcanist2`), the Cleric (`mender1`) and the Huntress for the Ranger; the others use option
1 until picked (`PICKS` and `STEP2_PICKS` in `tools/saltbound-art/build.py`).

### Passive mods

A passive's, item's or blessing's effect is a `mods` dict summed per hero by `Game.mods(h)` and read
by name where it applies (`m.get("might", 0)`). **Every name is listed in `mods.py`** with what it
does. Content granting an unlisted name refuses to load, and `tools/saltbound-check.py` fails if the
rules read a name nothing grants (that's how `aura`'s old heal and `potion_bonus` were found dead).
To add an effect: list it in `mods.py`, grant it in the content, read it in the rules.

### Enemies

- **Dice and moves** (`foes.py`; the roster is `FOES` in `content/archipelago.py`). Each enemy has a
  pool of `dice` (the heroes' face and kind vocabulary) and `moves`; each round it picks one (`w`
  weights, or a boss's `seq`), which rolls the dice it names (`use` indices or the first `n`) and adds
  a flat bonus: the dice's average times the difficulty-and-region multiplier above 1, plus might (so
  difficulty shows as "+5", not as different dice). The intent shows the move's name, its dice and
  bonus, the range, riders and targets; the enemy rolls those dice in the roll tray when it acts.
- **Move kinds**: attack (`each`: every die its own hit; `sweep: N`: N targets share the total;
  `chain`: arcs to another for half), all, block, guard (`all`: every enemy), heal and buff (`self`:
  only itself), debuff (`st_min` gates it on a die), summon, charge (`next` names the move it
  charges, which has weight 0: the Thunder Wyvern's Draw Breath then Storm Breath), thief (a Harpy
  snatches a potion and flies off two rounds later unless killed; the killer gets it back), merge
  (Storm Wisps: health adds, an extra die per merge).
- **Riders**: `st`/`sn` on a hit; `st_min` only if a die rolls that much (a Siren's Seer die shows in
  advance whether its Lullaby lands); `pair` on doubles (Root, Stun, or `again`).
- **Targeting** (`tgt`): random, weakest, strongest, vengeful (whoever hurt it most last round). Guard
  and Taunt swing intents in the open (`retarget_intents`).
- **Traits**: Thorns, Pack, Leech, Volatile, `splits` (Jellyfloats split the first time they're
  hurt), `shell_min` (the Brine Golem ignores hits under 4), `undead`.
- **Move pools** (`POOLS`): every enemy draws one extra move when it appears (`fo["mv"]`; bosses add
  theirs to the end of their `seq`).
- **Elites** (`ELITES`): one affix on one enemy: Hulking, Frenzied, Ironclad, Venomous, Warlord,
  Vampiric, Spiteful (+1 might whenever a hero buffs, heals or shields) and Splitting (splits when two
  different heroes hit it in one round). 1.6× health (Hulking 2×), double XP and gold, and loot. They
  lead some roaming groups from the first objective on, sit in vaults and champion halls, and read
  "Hulking Crabfolk Brute".
- **Big single threats**: the Reef Maw, the Iron Bosun and the Storm Roc. Three dice, a pool move, and
  `bloodied` at half health, once: +2 might, new moves, and a new rule (`bloodied.rule`): the Maw
  **swallows** a hero (no dice, damage every round, spat out after the Maw takes 15% of its health,
  `SWALLOW_GUT`, or when nobody else is left), the Bosun calls a Deckhound every round (`allhands`),
  the Roc takes to the **air** (melee can't reach it). They hold champion halls and roam alone from
  two objectives cleared.
- **Dungeon bosses are puzzles** (`bosses.py`): the **Bell-Warden** shows a bell number each round;
  a hit with a die showing it cracks the bell (+6, `BELL_CRACK`, and its next attack is Weak; scored
  as a combo, so previews and bots see it). The **Lamp Keeper** takes half damage while lit, until
  three different heroes (or all standing, if fewer: `LAMP_DOUSE`) hit it in one round; then its next
  attack is Weak and it takes full damage through the next round. The **Gallows Admiral** runs out
  Deck Cannons that Load, Load, then Broadside everyone: kill the guns first.
- **Each dungeon boss has a second rule and a bloodied phase** (owner's request, Nov 2026: tougher
  bosses with several interesting mechanics). `bloodied` works for bosses as for big threats (at half
  health, once: might, moves that come up half the time, a `rule`). A boss rule can force a move that
  isn't in its `seq` (`fo["force"]`, read first by `choose_intent`; then `fo["next"]`, a charge's follow-up).
  - **Bell-Warden**: the **Death Knell** (`knell`) comes every `KNELL_EVERY` (3) rounds, hitting
    everyone and Hexing them; the countdown shows as a status (`st.knell`). Cracking the bell doesn't
    delay it (with three heroes the bell matched nearly every round, so the knell would never come) but
    Weakens it if done the round before. Bloodied (`requiem`): the knell every other round
    (`KNELL_REQUIEM`), and Grave Peal (everyone, Stun on a 6).
  - **Lamp Keeper**: **Gather the Light** (a charge in its `seq`) then the **Lighthouse Beam** (every
    hero, three dice, plus the charge's die). Dousing the lamp *in the gather round* scatters it
    (`foe_hit_hooks`); dousing in the beam round doesn't (it once did, and the beam almost never
    landed). Bloodied (`blaze`): a doused lamp relights the next round, and Searing Sweep Burns everyone.
  - **Gallows Admiral**, bloodied (`kegs`): while none is out, he rolls out a **Powder Keg** (`keg` in
    `FOES`): Fuse, Fuse, then it blows on everyone with the charge's extra die and is gone. A hero who
    breaks it first sets it off among the enemies (`keg_broken`: `KEG_BLAST` times Hard's enemy HP to
    each). At 4 base HP the bots broke every keg at once, which made the bloodied Admiral *easier*; at
    12 it costs real dice. Grapeshot: three dice, each its own hit.
- **No boss can be locked down** (owner's request): the bell and the lamp once made their boss lose
  its next action, and with three heroes the bell matched almost every round (the Bell-Warden lost 62%
  of its actions, the Lamp Keeper 42%, in bot runs); with skill Stuns on top a boss never acted. Now
  they Weaken instead, and **Steeled** (`bosses.py`) covers every boss and big threat: one that loses
  an action (Stunned, cancelled by Cacophony or Requiem, distracted at nobody, robbed of every die) is
  Steeled for the next round, when Stuns and cancels don't take, so it acts at least every other
  round. Intents set by heroes (and an ambush's free first round) carry `by_hero`, which is what Steels.
- **The Drowned Crown** (100 HP; it won 2% of its fights until the Deluge, and 39% with 120 HP too): phase 1, **warded** (half damage, `CROWN_WARD`) while a Tide Guard
  stands; it summons guards only in this phase. Phase 2 (two thirds health): the **Undertow** marks
  one hero each round, who takes 3× the fight's damage multiplier (`UNDERTOW`) at round end unless
  Armor or a Guard stops it. Phase 3 (a third): its guards drown and it's **exposed** (takes 50% more,
  `CROWN_EXPOSED`) and **furious** (an extra die on every attack). Each change of phase forces **the
  Deluge** next round (all four dice on everyone; with fury in phase 3, five), announced in the log and
  the phase banner. (An Undertow of 5 on top made the Crown win half its fights: too much.)
- **Dungeons** (`DUNGEONS`, `PATHS`; `dungeon_lineup`, `make_fork`, `do_fork`, `take_path` in
  `game.py`): three fights. The first is drawn from the dungeon's `open` pool; after it and after the
  second the party reaches a **fork** of two paths drawn at random, shown with enemies and rewards:
  the Main Passage (`mid`), the Champion's Hall (`champ`: one big threat or an elite; loot a rarity up), the Flooded Vault (a `mid` lineup with an elite; +12 gold each), a Quiet Shrine (no
  fight: heal 35%, curses lifted); and before the boss, Storm the Hall (boss and `escort`), Rest at
  the Threshold (heal 30%, one more escort) or the Back Way (enemies caught off guard; two picks).
  Everyone in the dungeon votes (`{"t": "fork", "n"}`); most votes wins, a tie is a coin toss. The
  next lineup is stored per dungeon in `s["dnext"]`, so the forecast can show it and a party that
  loses meets the same enemies.

### Items

About 80 items (`ITEMS` in `content/items.py`; 59 that drop): weapons give a die and actions, armor a guard die and
often a passive, trinkets an odd die, a passive or an action. Gear past the starting kit has a passive
of its own (`PASSIVES` in `items.py`, merged into each item's `mods` and `text`). **Situational finds** (owner's request: a common or uncommon should sometimes beat a rare): the
Shellbreaker Maul ignores Armor, the Oilskin Coat stops Burns, the Diver's Harness a Stun and Freeze,
the Smuggler's Cloak makes enemies ignore you (bad on a Vanguard: the bots know), the Gutting Knife
finishes the wounded, the Gull-Feather Bow punishes enemies aiming elsewhere, and so on. **Rule-benders**
(the end of `ITEMS`): Forked Staff (a single-target spell also hits another enemy for half), Siren's
Conch (whoever hits you is Marked), Tide Hourglass (your biggest unused die carries over), Powder
Heart (every die explodes, −6 max HP), Weighted Coin (a 1 counts as the top face), Bloodstone (out of
rerolls, a miss rerolls for 3 HP), Bosun's Whistle (combos +2), Bosun's Bell (an action: pass a die
to an ally; key `pass_die`) and Sea-Glass Lens (your armor's die can go on attacks). Shop rows and loot
cards compare with what you wear in that slot (the die, the change in average, the actions you'd
lose, the passive). No common may be strictly worse than starting gear (owner's request): the Fishing
Spear (a Rapier) and Sailcloth Wrap (a worse Wool Robe) were removed; save v5 swaps them for those.

**Skill texts** follow one style (owner's request: clearer): "the die" is the number it shows, "On
5+:" is what a roll meeting the requirement does and "Otherwise:" what a lower one does, "Any row"
comes first, and enemies' "intents" are called their coming attack or action.

## Balance now

The owner reviews every balance change: ask before changing a class or the difficulty, and give the
options with their trade-offs. **Hard's target is now about 50% for the bots (owner, Nov 2026, "for
now"; it was 30–35% while the bots split up) with no class far ahead; leave the difficulty
multipliers alone unless the owner asks.** Boss health is `BOSS_HP` in `content/archipelago.py`
(1.0: at 1.1–1.25 most losing parties died at their first dungeon).

- **Difficulty** (`DIFFICULTY` in `game.py`): Story 1.0× enemy HP and 0.95× damage, 4 revives, a rise
  every 4 turns; Normal 1.9× / 1.75×, 3 revives, a rise every 3; Hard 2.35× / 2.3×, 2 revives, a rise
  every 3. Enemies also gain 15% HP and 10% damage per tier (objective cleared), and `SURGE` per rise
  of the tide.
- **Objectives scale with the party** (owner's request, Nov 2026: so the expected power at each
  objective is easier to tune): dungeon fights (all three of an objective's, boss included) also take
  `DUNGEON_STEP_HP` / `DUNGEON_STEP_DMG` in `tuning.py` by objectives cleared: 0.85×/0.9× for the first,
  1.1×/1.05× for the second, 1.35×/1.2× for the third (`start_fight`, `f["hpmul"]`). With the tier on
  top, the first objective's enemies have 85% health and the third's 205%. The objectives' tooltip
  in the top bar shows the current step (`dungeon_step` in the view).
- **The overnight pick study** (owner's request: test skill win rates with long runs and rebalance
  outliers, optimising for skills that are interesting to play). Method: `--with=<class>` (every party
  includes that class, so its picks come up three times as often), 600 Hard runs per class, each pick
  judged by vs passed with a standard error (z). The spread of z was 1.4 (1.0 would be pure noise),
  and 20 of 144 picks were past ±2. **Almost every clearly bad pick was an action** that costs a die
  and a level but does less than the class's basic attack; the good ones were passives and upgrades
  of the basic attack. So the fix was to make those actions worth a die, not to nerf passives:
  Acid Flask (now a bomb: strip all Armor, Vulnerable 2, deal the die; was z −4.2), Shoulder Charge
  (½ die Armor, 4+: die +3 and drag; −3.7), Twin Cut (each die +2; −3.4), Volley (½ each die +1;
  −3.1), Aimed Shot (5+, a miss deals half; −3.0), Transfusion (heal die +2, next die +2; −2.9),
  Strangle (3+, die +2; −2.5), Lend a Hand (the die rolls 2 higher; −2.5), Swarm (wasps sting 2;
  −2.3), Entangle (also ½ die; −2.3), Smite (die +4, the lowest ally heals 2; −2.2), Rally Wall (½ sum
  Armor; −2.0), Doom (26 − die, at least 8; −1.9), Silver Voice (also +1 reroll; −2.1, a map-only
  pick). The strongest picks (Brace +4.2, Toss+ and Thornlash+ upgrades) were left alone: Brace's
  Vanguard is the weakest class, and upgrades look strong only because the bots rarely take them.
  Rounds two to four (500 runs per changed class each) reworked what was still low: Chain Lightning
  (odd: die +3, Shock, arcs to another enemy for half, `"to": "another"`; even: the die), Siphon (die
  +2), Retaliate (Armor + the whole die), Finisher (sum +3), Quicksilver (one die; the ally's next die
  +2), Counterpoint (a flipped die +1), Undying Fury (12), Shieldwall (also 6 Armor at the start of
  each fight; guard share 4, shields block 5), Shoulder Charge (no roll, cooldown 2: the die as Armor,
  die +2, drag). Berserker: 30 HP, 3 per level. Each round's new "worst" picks were mostly last
  round's fine ones (noise); the z spread fell from 1.42 to about 1.2.
- **Brace was the Vanguard's must-pick** (+18 to +20 points vs passed, every round). The owner asked
  for it weaker and the rest stronger: Brace is now the die +2 as Armor and 2 to the lowest ally (was
  twice the die and 3), and neutral as a pick; Rally Wall became **Hold the Line** (one die, cooldown 2:
  every hit on the party deals 2 less this round, you gain the die +3 Armor; same key); Shield Bash
  deals the die +3 (at least 6) and Stuns; Taunt adds thorns 2; Guard and Taunt give the die +4
  Armor; Spiked Plate thorns 3; Vanguard 54 HP. Those alone left Vanguard parties at 23% (500 runs):
  Brace really was its survival. So the starting passive Overguard also gives **8 Armor at the start
  of each fight**, which brought them back to 32% (200 runs; 5 Armor gave 30%, the old Brace 32%).
- **Bloodlust reworked** (owner's request; it looked worst in a 300-run pick comparison, −28, though
  within noise): heal 4 per kill (was 2), and the first kill each round gives a fresh d6 (`kill_die`),
  so a kill rolls into the next swing. Not yet measured.
- **When runs are lost** (Hard, 300 runs on the build just before the bag and boss changes, 208
  losses): by turn 1-9 5%, 10-19 19%, 20-29 17%, 30-39 34%, 40-49 21%, 50+ 4%; by objectives cleared
  0: 42%, 1: 26%, 2: 20%, 3 (at the Drowned Crown) 11%. Most losses come late, but four in ten losing
  parties never clear an objective.
- **Now** (the second trinket slot removed again, the Vanguard rework above): **Hard 38%** (300 runs,
  seed 30000, before the Vanguard's Overguard Armor), Vanguard parties 32%. Back near the target.
- **After the overnight pass** (second trinket slot, 21 new items, the 4-item pool, the reworks above;
  600 Hard runs on seed 30000): **Hard 51%**: Berserker 56%, Herald 55%, Mender 54%, Ranger 54%,
  Alchemist 52%, Duelist 52%, Scoundrel 50%, Warden 48%, Arcanist 47%, Vanguard 45%. **Normal 90%.**
  The gear changes, mostly the sixth die, took Hard from about 37% to 51%; the skill reworks barely
  moved the total. Hard is well above the 30–35% target: the owner's call (`SURGE`, Hard's
  multipliers, or a later second trinket slot).
- **After the tougher bosses** (Nov 2026: knell, beam, kegs, the Deluge, `SURGE` 0.45%, `BOSS_HP` 1.0,
  Crown 100 HP; 300 Hard runs, seed 5000): **Hard 43%** (target about 50%), runs of 55 turns. The
  Crown at 120 HP gave 41%. Fights won: bosses (the Crown) 66%, dungeon fights 89%. Losses by
  objectives cleared: 0: 98, 1: 29, 2: 8, 3 (at the Crown) 37, so most still die before their first
  objective. **Vanguard parties win 80%, every other class 33–45%**: far ahead (the new bosses' hits
  on everyone reward its Armor and Guards). The owner's call.
- **After the bots keep together** (support die removed; 300 Hard runs, seed 5000): **Hard 72%**, runs
  of 58 turns (was 46; waiting for each other costs turns), level 6.2. Vanguard 90%, Alchemist 76%,
  Scoundrel 76%, Herald 71%, Ranger 71%, Mender 70%, Arcanist 70%, Warden 69%, Berserker 68%, Duelist
  64%. Won: dungeon fights 95% (was 87%), bosses 99.5% (84%). Every earlier number here was measured with
  bots that fought a third of their dungeons alone, so Hard was tuned for a party that splits up; a
  party that stays together, as players do, finds it much easier. The owner's call.
- **After tide arrivals and support dice** (Nov 2026; 300 Hard runs, seed 5000): **Hard 59%**, runs of
  46 turns, level 5.8. Vanguard 75%, Alchemist 67%, Ranger 64%, Berserker 64%, Herald 56%, Warden 56%,
  Scoundrel 53%, Duelist 52%, Arcanist 51%, Mender 50%. The same 100 runs without the living heroes'
  support die: **42%** (the old 40%), so the support die is worth about 17 points and the tide arrivals
  (plus the simulator now giving the fallen's spirit dice) about nothing. Well above the 30–35% target;
  the owner's call: a smaller die (d4), only heroes within a few hexes, once per fight, or Hard's numbers.
- **After jobs** (two per board, deadlines, rewards, bounty and salvage; 300 Hard runs, seed 5000):
  first **Hard 50%** with runs of 46 turns (was 33): the bots did jobs ahead of the dungeons and levelled
  on the way, and garrisons stopped growing at four. Garrisons now grow to six (`GARRISON_MAX`) and the
  bots do jobs only until a dungeon is due: **Hard 43%**, 38 turns. Above the target; the owner's call.
- **After the map's choices** (previews, opportunities, garrisons, priced places, town trades, event
  chains; 300 Hard runs, seed 5000): first **Hard 47%**, mostly from the new rewards (rare pools,
  a revive for sale, reforging, drifting cargo) while the garrisons barely bit: the bots clear their
  first objective before turn 9. Garrisons every 6 turns (was 8), the temple's revive 75 gold (was 50)
  and reforging 30/60/100 (was 25/45/80) brought it to **Hard 40%**. Still above the 30–35% target,
  a little more than before (37–38%); the owner's call. The difficulty multipliers are unchanged.
- **Before that** (no bag limit, Steeled bosses, the bell and lamp Weaken instead of stunning): **Hard 37%**
  (35% seed 5000, 39% seed 9000), **Normal 86%**. Above the Hard target again: the unlimited bag
  (bots keep every potion and no gear is auto-sold) outweighed the tougher bosses. The owner's call.
- **Where the bots stand** (after the rising tide became `SURGE` and loot became a shared pool; 600
  runs on Hard from seeds 5000 and 9000, 200 on Normal): **Hard 29%** (28% and 31%), classes 24–35%
  on seed 9000 (Berserker 35, Alchemist 33, Ranger 33, Scoundrel 32, Duelist 32, Warden 31, Arcanist
  31, Herald 30, Mender 26, Vanguard 24; ±5 noise). **Normal 77%**, Story every run. Without `SURGE`
  the same code plays Hard 39% and Normal 82%. Before these changes: Hard 39% (Mender, Herald and
  Ranger 43%, Duelist 30%), Normal 89%.
- **The last pass** (owner's request: buff the Vanguard, trim the top classes rather than touch the
  multipliers): Vanguard 50 HP, Guard and Taunt give the die +3 Armor (was +2), Brace gives the weakest
  ally 3, Last Stand 6 Armor, Iron Will softens the first hit by 3. Extra HP alone did nothing for it
  (it falls from the hits it pulls); Armor on its pulls moved it most. Trims: Mender 17 HP, Lifeline
  heals half max HP (was full), Mend cools 3 rounds, Lift twice the die (was +2 more), Quick Lift once
  per rest at 6 HP (was once per fight at 8); Ranger 24 HP and Eagle Eye half again (was double);
  Arcanist 23 HP; Herald 18; Scoundrel 22.
- **Bot verification** (what the bots valued wrongly, all fixed): Lifeline was thrown on heroes about to
  drop, where it does nothing (a downed hero loses their statuses); gear and loot were picked by rarity
  alone (now `item_score`: rarity, die, and a passive only if the hero has actions it works with, e.g.
  no bomb bonuses on a hero without bombs); the Armor on Taunt and Guard ignored the hits they pull in;
  Bottle It was worth a flat 2.5 (now a share of the potion it makes); and planning odds ignored
  Bulwark Faces, Weighted Coin, Keen Edge and (in the browser) Sleight of Hand. Low use that's fair:
  Grafting (only worth it for a 9+ sum), Spotter, Splitting Flask. Lifeline's heal shows as 0 in the
  report because the heal isn't credited to the Mender.
- **Noise**: 300 runs gives each class about 90, so a class's rate moves about ±5 points between
  batches by chance and the overall ±3. Judge classes on 300 runs (`--seed=5000` for a second set), and
  a level-up pick's win rate (20–40 runs) as a hint. Judge picks by **vs passed** (runs that took it
  against runs offered it at the same moment that took something else), not **vs class**: a pick only
  counts once a run reaches its level, so vs class flatters late picks and capstones (in 600 Hard runs,
  137 of 139 picks beat their class's rate). At 300 runs a pick is taken ~20 times, so vs passed swings about
  ±25 points by chance: in 300 Hard runs (current build) its spread across picks (sd 14) was about
  what chance alone gives (13), and no pick stood out as harmful. It takes a targeted run
  (`--classes=`) to test one.
- **How to tune**: `python3 tools/saltbound-sim.py 300 hard --seed=5000 --report`. Read the class
  table (win rate, output per round, downs), the action tables (a basic attack taking most of a class's
  dice, risky actions that rarely hit, actions never used), level-up picks against win rate, and the
  balance flags. Change one lever at a time and rerun.
- **The bots keep the party together** (owner's request, Nov 2026: players would): `keep_together` in
  `bot.py`. A hero more than 2 hexes ahead of an ally waits for them, and a hero about to walk into a
  dungeon, the Peak or an enemy group stops beside it until everyone else is within a hex of it (who a
  fight pulls in). Before, every bot walked its own route at its own speed and the first to arrive went
  in: with all three alive, 34% of dungeon fights and 62% of boss fights were fought by one hero. Now
  those are 0%; roaming fights still catch one hero 18% of the time (enemies step onto the nearest).
  Turns ending with the party within a hex went from 69% to 73% (12 fast runs on Hard).
- **Bot behaviour shapes the numbers**: a class can look weak because the bot plays it badly. Before
  buffing a class, check its actions table for skills the bot never uses, and that the bot values what
  the skill does (until the shared hit sums, the bots ignored Eagle Eye, Pierce, Kindling's Burn, Forked
  Staff, Shrapnel and Wide Arcs).
- **Levers used so far**: HP and HP per level, a basic attack's bonus, cooldowns, a free defensive basic
  (Brace), starting passives (Overguard, Evasive), once per rest (Lift), narrowing a passive (Aegis,
  Field Medic), miss penalties, enemy health and damage by fight kind (`FOE_HP`, `ROAM_*`, `EVENT_*`),
  and (the owner's preference) reworking a dull level-up pick into one that makes you think rather than
  touching a class's basics. Hard runs mostly end around level 4-5, so starting HP moves a class more
  than HP per level.

## Code map

The server owns the game; the browser sends intents and draws the state it gets back. There is no
clock anywhere: the run changes only when someone acts.

| File | Holds |
|---|---|
| `app/saltbound/game.py` | `Game`: the whole run as one JSON-able dict (`Game.s`). Map turns, terrain and step costs, the tides and the rising tide, enemy groups, places (and what they show, `setup_places`), opportunities, garrisons, event chains, events, loot, levelling, towns and their trades, the forecast, `view()`, `static()`. |
| `app/saltbound/combat.py` | `Combat`, mixed into `Game`: starting fights, the round (`new_round` and its steps), placing actions, resolving, hurting and healing, the end of a fight (`finish_fight`, `fight_won`, `dungeon_advance`, `fight_lost`), `fight_view`. `Invalid` is the error shown to players. It's built from the mixins below. |
| `app/saltbound/dice.py` | Faces, condition checks, amount expressions (`amt`), and `Dice`: rolling, odds for planning (`outcomes`, `joint_outcomes`), `roll_for` with its rerolls. |
| `app/saltbound/actions.py` | `Actions`: targets, amount variables (`env` = `dice_env` + `target_env`), one handler per op (`_op_dmg`, `_op_status`...) and per instant (`_inst_flip`...), and the **shared hit sums** (`hit_base`, `hit_finish`, `hit_pierces`, `foe_damage_after`, `foe_soak`, `hit_spill`, `status_amount`) that the fight and the bots both use. |
| `app/saltbound/combos.py` | `Combos`: Pincer, Covered, Shatter, the Bell, Wildfire, Spiteful elites. |
| `app/saltbound/bosses.py` | `Bosses`: the Crown's phases and Undertow, the Bell-Warden, the Lamp Keeper, the Iron Bosun's crew, Harpies' flight, splitting, the Maw's swallow. |
| `app/saltbound/tuning.py` | The fight numbers (fight-kind scaling, combos, boss numbers, status lists). |
| `app/saltbound/mods.py` | Every passive mod name and what it does; `check_content`. |
| `app/saltbound/foes.py` | `Foes`: enemies' dice and moves (`foe_moves`, `foe_setup`, `foe_bloodied`), intents (`choose_intent`, `intent_numbers`), targeting, `retarget_intents`, acting (`foe_act`, `foe_do`). |
| `app/saltbound/classes.py` | The generic classes, their actions and passives, `SHORT` card text, `COMBOS`, levels and XP. |
| `app/saltbound/content/items.py` | Items (generic), item passives and the actions weapons give. |
| `app/saltbound/content/archipelago.py` | This map's enemies, pools, elites, dungeons and paths, the final boss, blessings and events. |
| `app/saltbound/world.py` | Hex geometry, terrain costs (`COST`, `FAST`), generating a run's map from its seed. |
| `app/saltbound/rng.py` | The seeded RNG (its state is in the save). |
| `app/saltbound/room.py` | Rooms: joining, the lobby, controllers, autosaving, testing bots. The socket and room codes are the shared `app/rooms.py`. |
| `app/saltbound/save.py` | SQLite saves (`data/saltbound.db`, one connection under a lock), versions and migrations. |
| `app/saltbound/bot.py` | The testing bots (map, dialogs, fights). In fights they plan the hand with a short beam search (`plan_hand`), scoring each placement over every way its dice could roll (`evaluate`, using the shared hit sums) against a `Board` of intents and their own earlier set-ups; they play the first placement, see how it rolled, and plan again. `instant_value` scores the dice tricks; `bot.order` lets heroes holding a set-up plan first. |
| `app/saltbound/routes.py` | `GET /games/saltbound`, the saves list, and the WebSocket. |
| `app/static/games/saltbound/css/tokens.css` | Every colour, size, radius, space and timing. |
| `css/ui.css` | The components, from tokens only. |
| `js/main.js` | The connection (the shared `games/shared/net.js`) and which screen to show. `?bots` turns on testing bots. |
| `js/store.js` | Shared client state, `send()`, who controls which hero. |
| `js/screens.js` | Title, lobby (a chosen class in full: `classDetails`), end of run, the painted backdrop. |
| `js/hud.js` | The map screen's HTML: top bar, party cards, action bar, log, drawers, dialogs, hints, map input and effects. |
| `js/combat.js` | The fight overlay and playing back a round's effects. |
| `js/hexmap.js` | `MapView` (Phaser): painted terrain, places, units, fog, reach, routes. |
| `js/rules.js` | Route planning (step costs and sight come from the server: `static.map`, each hero's `sight`), and how to describe requirements, dice and statuses. |
| `js/art.js` | `flat32()`, sprite canvases, place icons. `js/sprites.js` is generated: never edit it. |
| `js/ui.js` | `h()`, icons, tooltips, toasts, modals. `js/audio.js`: synthesized sound and music. |

## Testing

- `tools/check-all.sh` runs every fast check in the repo (about a minute); run it before pushing.
- `python3 tools/saltbound-check.py` forces every action and passive of every class through real
  fights (bots never use most instant tricks), checks the passive mods against `mods.py`, and that
  `js/rules.js`'s map size matches the server's. Run it after touching the rules or classes.
- `python3 tools/saltbound-sim.py [runs] [difficulty] [--report] [--seed=N] [--saves] [--with=class] [--fast] [--tally]`
  plays whole runs with bots across all cores. **Two kinds of test** (owner's rule):
  - **`--fast` checks that a feature works**: greedy bots (the best single placement per fight move, no
    look-ahead), about 4x quicker; they play worse, so their win rates say nothing about balance, but
    on Normal they still finish runs and reach every part of one. It prints a tally of what happened
    (fights by kind, log lines such as jobs done or opportunities sighted, effects, every event seen),
    so a new feature can be seen firing. 12 runs ~6 s, 40 ~15 s. Use it while building, with
    `--saves` for anything that touches the state. `tools/check-all.sh` runs `12 normal --saves --fast`.
  - **The full bots are for balance**, only for changes that directly affect it, and once, at the end
    of a batch of changes: 12 runs ~12 s, 100 ~1-1.5 min, 300 ~3-4 min (batches side by side slow
    each other). 100 runs pins a win rate to about ±10 points, 300 to about ±5: 100 for "did this swing
    difficulty a lot", 300 for class rates or a final number. `--tally` adds the tally.

  Batches of 50+ save their output to `data/saltbound-sim/` (`last-<difficulty>.txt`, `--fast` ones as
  `last-fast-<difficulty>.txt`, with the date and commit); `--last [difficulty]` prints them without
  playing. Answer balance questions from those or from "Balance now" first, and run fresh only when
  the code changed since and the question needs it. `--with=<class>` puts that class in every party,
  for studying its picks (500-600 runs per class). `--report` prints balance analytics
  (`tools/saltbound_stats.py`): class win rates and output, fights by kind, enemies, each class's
  actions, level-up picks, gear, flags. `--saves` checks a run saved and restored at every step
  finishes identically, and that the analytics hooks don't change a run. It exits non-zero on a stuck
  run or a save mismatch.
- `node tools/saltbound-mp.js [url] [out dir]` plays a **two-player fight** in two browsers (after
  `python3 tools/saltbound-audit.py fight`): Alice resumes the save, Bob joins by code, each plays a
  hero while the other watches, both ready up, and screenshots of both screens go to the out dir.
  It watches both pages the whole time and fails if a dialog or a level/objective banner appears
  over a fight still playing out, or on a page error. About a minute.
- **A refactor that shouldn't change play**: record full-run fingerprints first (play fixed seeds with
  `play()` from the simulator and hash `g.s`), refactor, and compare. Any bot or rules change shows.
- `node tools/saltbound-audit.js [url] [dir] [WxH] [scenario...]` reviews particular moments:
  `tools/saltbound-audit.py` plays bots to one (`start`, `loot`, `level`, `event`, `fight`, `fork`,
  `boss`, `won`, `lost`, and for the map `tide` (just after a rise that landed enemies), `opp`, `trade` (standing in a smithy, temple or cartographer
  town), `garrison` (a boss fork with a garrison), `board` (in a town with two jobs up), `job` (a bounty or salvage job under way), `results` (a hero with two kinds of choice waiting, e.g. a level-up and spoils)...) and saves it for the token "audit"; the browser resumes it and screenshots.
  Set `SALTBOUND_DB` the same for the server and the tool on a scratch database. `node
  tools/saltbound-shots.js [url] [dir] [WxH]` screenshots a whole bot-played run.

## Gotchas

- **The bots' scoring works out once per target what doesn't depend on the roll** (`evaluate`'s
  `prep`): `target_part`/`target_env_from` split `target_env`, `combo_parts`/`combo_sum` split
  `combo_peek` (in `combos.py`, beside it), and `die_sig` is cached while a bot thinks (`frozen`). A
  change to `target_env` or `combo_peek` belongs in its split too. This made the full bots about 25%
  faster with identical runs: check a change like it with run fingerprints (play fixed seeds, hash
  `g.s`, compare before and after), which must not change.

- **The view sends every key of a seen place** (all but a town's `quest`), so a place dict holds only
  what players may see; that's how an event's `ev`, a wreck's `rarity` and a town's `spec` reach the
  map. A new key that every place of a kind needs goes in `setup_places`, which fills only what's
  missing, so the save migration can call it too (with its own `Rng`, leaving the run's untouched).

- **Planning odds use the same face rules as rolling** (`face_rules` in `dice.py`: Bulwark Faces,
  Weighted Coin, Keen Edge); the browser gets each hero's `rollmods` in the fight view for its hit
  chances, and the bots' odds cache keys on them (`ROLL_MODS` in `tuning.py`). A new passive that
  changes what a die shows belongs in all three.
- **Spirit dice are given outside `waiting()`**: the fallen heroes holding them aren't waited on,
  so the simulator gives them at the top of its loop and the rooms' bots before anyone fighting acts.
  Until Nov 2026 the simulator never gave the fallen's dice at all, and those dice lacked `dk`, which
  crashed rolling the first time one was played.
- **The bots score a hit with the fight's own sums** (`hit_base`, `hit_finish`, `foe_damage_after`,
  `foe_soak`, `hit_spill`, `status_amount` in `actions.py`). A new damage rule belongs there, not
  inline in `_op_dmg`, or the bots won't see it. Their own additions are only guesses about what
  earlier placements in their plan will do (planned Vulnerable, Mark, Crescendo).
- **The bots cache dice outcomes** (`bot.dice_combos`) across calls and games in one process. The key
  must hold everything `joint_outcomes` and `dice_env` read: it once missed linked dice whose group
  had already rolled, and the hero's missing HP. A cache that disagrees with a fresh computation shows
  up as runs that differ from a no-cache run.
- Things the bots call must not change the state; they cache mods and max HP while they think
  (`bot.frozen`).
- All randomness comes from `Game.rng`, never the global `random`, or restored runs won't match.
- **A group's or lineup's enemy can be a dict** (`{"k": key, "aff": affix, "hp": wounds}`) rather than
  a key. The view and the forecast send keys plus a parallel `aff` list (`foeName(k, aff)` in
  `hud.js`).
- **Action keys are one namespace across classes and items**: the Alchemist has `toss`, so the Bosun's
  Bell is `pass_die`; the weapon Jab is `thrust` because `jab` is the Herald's Cutting Words.
- **Cache versions**: after changing CSS or JS run `python3 tools/bump-version.py
  app/static/games/saltbound`, which bumps every `?v=` together (a module loaded under two URLs runs
  twice). The page's `?v=` is also how the server tells a tab left open across a deploy to reload, so
  **restart a local server after bumping** or every tab reloads in a loop.
- A browser keeps only its five newest saves (`save.KEEP`), and resuming one re-saves it under the
  room's title; `tools/saltbound-audit.js` makes each audit save just before using it.
- **Effects play before the new state is drawn** (`main.js`): map moves start from the old hexes, and a
  fight's last round plays back before the map or end screen replaces it (`combatBusy()`).
- **Actions resolve as they're played**; each play sends its own effects and the client plays them back
  while the hero's dice stay playable, so plays queue (playback speeds up to 4× while more waits). In
  rooms, bots wait `BOT_FIGHT_DELAY` (1.2 s) between fight moves.
- **The stage never falls a round behind the dice** (owner's request): once a batch that ends a round
  (`round` or `fightend`) is queued, everything before it plays at 6×, and beyond the last three
  waiting plays they're skipped (the end's starting state already shows them, and "This round" lists
  them). So the stage trails the live round only while the enemies' moves play.
- **The tray is rebuilt only when what it shows changes** (`traySig` in `combat.js`): rebuilding it
  several times a second while a play animated dropped clicks (press on one button, release on its
  copy) and flickered tooltips. Anything new the tray shows belongs in `traySig`, or it goes stale.
  Fighters take clicks through one `pointerup` listener on the overlay, read where the pointer is let
  go, so a fighter redrawn mid-click still takes it.
- **"Ready when my dice are spent"** (a menu setting, `autoReady`): a hero you play readies once every
  die is used (crusted ones don't count), once per round, so unreadying sticks; after any hero readies,
  the tray moves to the next hero you play who still has to act (`readyUp`, `nextTab`).
- A combat effect the client should play must be listed in `COMBAT_FX` in `combat.js`, or it's
  silently dropped. Rolls play back in the roll tray (`rollTray()`); the stage is rebuilt on every
  render, so animated elements set a negative `animation-delay` from when they started.
- Hero cards in the party column are CSS grids: an absolutely positioned child (a float, a badge)
  is placed relative to its grid cell, not the card, unless it's given `grid-row`/`grid-column`.
- **Nothing from after a fight may land while it's still playing out**: the server's update arrives
  with the fight already won (and the party levelled), but the browser plays the fight back first.
  Map effects that follow a fight (level-up and objective banners, gold, the tide, blessings, event
  results) go through `afterCombat` in `combat.js`, which runs them once playback and the Victory
  banner are done; the results screen already waits on `combatOpen()`; and the health bars use the max HP from
  before the round (`C.maxhp`) while it plays. A hero who walks into a fight finishes the walk on the
  map first (`holdCombat`). `tools/saltbound-mp.js` checks the first two.
- `h('div#id.class')`: ids and classes in any order. `h()` sets CSS custom properties with
  `setProperty`; plain assignment drops them silently.
- **One look for dice, skills and intents** (owner's choice): a die is a cream tile with a coloured top
  edge for its source (`--src-*` tokens); a skill shows a requirement badge (`reqBadge`) coloured by
  your odds and one bold effect line from `SHORT` in `classes.py` (every action needs one); an intent
  is a small card with the move's name, its dice, bonus, range and a dot per target.
- `ui.css` has grown in layers: a later wide-screen rule beats an earlier phone rule of the same
  specificity, so the fight's phone overrides live at the very end of the file.
- Hidden enemy groups don't block planned paths (that would give them away); walking into one starts a
  fight. Bots and the forecast share `Game.group_step`, the one copy of how a roaming group steps.
- The engine is synchronous and turn-based, so rooms need no tick loop; bots act through
  `loop.call_later`.
- The title screen gets saved runs over HTTP (`GET /games/saltbound/saves?token=`) so they show before
  joining a room.
- Thorns and Volatile can knock a hero down during their own action: `maybe_resolve` ends the round if
  nobody is left acting. The swallow can knock out the last hero at the start of a round, so
  `new_round` checks the end after dealing dice.
