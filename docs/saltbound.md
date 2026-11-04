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
  identical). About 30×22 hexes: three regions around a central peak, **drawn per run from eleven**
  (see "Regions and biomes"). About 30 map turns per run.
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
  | Deep water | skiff only, 1 | a current: 0 downstream, 2 against; a reef: high tide only; by a whirlpool +1; a whirlpool: never |
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
  Towns also offer side quests. Each run draws its three regions from eleven (owner's request,
  2026-11-04: each objective its own biome, the three randomised per game):

  | Region (key) | Land | Enemies | Objective (dungeon: 3 fights with two forks; see "Dungeon forks") and boss |
  |---|---|---|---|
  | Coral Shallows (`coral`) | the original islands | drowned sailors, crabfolk, reef creatures | the Sunken Chapel: the Bell-Warden |
  | Smugglers' Keys (`keys`) | the original islands | pirates and a tide cult | the Black Fort: the Gallows Admiral |
  | Stormcrag (`storm`) | the original islands | storm elementals, harpies, mountain beasts | the Lighthouse: the Lamp Keeper |
  | Cinderreach (`ash`) | ash fields and a volcano | imps, magma beasts, obsidian golems, fire cultists | the Caldera Forge: the Slag Tyrant |
  | the Shifting Sands (`dunes`) | dunes and salt flats | scorpions, raiders, mummies, a sphinx | the Buried Tomb: the Sun-Eaten King |
  | the Stillwood (`petrified`) | a petrified forest | stone treants, basilisks, gargoyles, sleeping statues | the Heartwood Vault: the Heartwood Gorgon |
  | the Verdant Deep (`jungle`) | jungle | panthers, dart frogs, strangler vines, witch doctors | the Strangled Ziggurat: the Mother of Vines |
  | Aetherhold (`heaven`) | golden meadows and marble | seraphs, cherubs, haloed knights, fallen angels | the Celestial Spire: the Radiant Arbiter |
  | the Prism Wood (`crystal`) | a crystal forest | crystal golems, shardlings, prism spiders | the Heart Geode: the Shard Queen |
  | the Drowsing Vale (`dream`) | dreamlands | sleepwalkers, dream eaters, jesters, mirror shades | the Sleeping Palace: the Somnarch |
  | the Frostpeaks (`frost`) | snowy mountains and a frozen sea | frost wolves, ice wraiths, mammoths, a frost giant | the Glacier Throne: the Rime Matriarch |
  | Central peak | | | **The Drowned Crown**, the tide-king raising the sea; fought on the last dry peak |

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
  | Armor | blocks N damage; a hero's clears at end of round unless a skill says otherwise, an enemy's when the enemies' next turn starts |
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
  1. **Title**: New run, Resume, Join by code; the ten heroes stand idling under the name.
  2. **Lobby**: room code and link, players, host settings (difficulty), saved runs.
  3. **Class claim**: a card per class with role, HP, base dice, map ability and sample skills.
     Players claim any free class and can swap until the host clicks Start; the host picks for
     unclaimed heroes. On resume, the saved heroes are shown instead.
  4. **Map**: the hex map in the middle; three hero cards down the left (portrait, HP and Ready
     state; the selected hero's card adds gold, moves and dice, so the cards don't cover the map);
     "This turn" bottom left (collapsible), the log closed until opened (each remembers how you left
     it), first-time hints bottom right; towns are labelled and heroes sharing a hex fan out; the terrain
     (`paintTerrain`) blends where kinds of land meet, shades drops in height, runs dirt roads between
     towns (each to its nearest by land) and has glints moving on the sea (`placeWaves`); top bar with turn, tide, the rising tide's enemy strength and the next objective by name (the nearest not cleared, found ones first, then the Drowned Peak; an objective not found yet points at the middle of its region; clicking finds it on the map, clicking again moves on to the next); other heroes' planned paths as ghost
     trails, like Board Brawl's route previews.
  5. **Combat overlay**: full screen, over a painted backdrop of where the fight is (`js/stage.js`:
     each region's open ground, each dungeon's interior, the Crown's peak; painted in code at 400×150
     like the map's terrain and scaled up crisp), fighters casting shadows on its floor and breathing
     while they wait; the party in one column, enemies in their rows, facing each other
     across the middle at a good size (owner's request: big fighters, rows close together); intents
     above enemies (a Stunned enemy shows "Stunned · skips its turn" instead, and no arrow); each
     hero's dice tray and action cards along the bottom; allies' placements visible live. **What
     allies do is spelled out** (owner's request): a caption over the stage names an ally's action,
     its target and what it does; every action animates by kind (`abilityFx` in `combat.js`: a melee
     lunge and slash, an arrow, a spell orb and burst, a thrown bomb, a green glow on whoever is
     healed, a blue shimmer for Armor); and the "This round" strip lists each action with who did
     it, the damage, healing, Armor and kills it caused (`done[i].out`, from `Game.act_outcome`),
     with the roll and the details on hover. Before it, "Enemy turn" recaps what the enemies did on
     their last turn (`f["last"]`, recorded on the server by `Combat.recap` from the effects the enemy
     turn and the round's end give off): a chip per enemy action, with the damage, blocks and
     knock-downs it dealt to each hero or summon, folding into one chip once the party has played. Hovering an ally's portrait lists their actions, and
     clicking one (when not aiming) opens their full sheet over the stage: every action with its
     cooldown, their passives and this round's dice (`allyPanel`); clicking your own other hero
     switches your tray to them. The big skills have signature effects (`SIGNATURE` in `combat.js`:
     Fireball's orb and explosions, Earthshaker's quake, Chain Lightning's bolt, Cleave's arc, Lunge's
     thrust, Volley's arrow rain, Doom's sigil, Renew's party glow, Sanctuary's dome, Hymn's notes,
     summoning circles and more), and **every other action has its own look too** (`SKILL_FX` in
     `js/skillfx.js`, built from a kit of colourable effects: shots that fly, lob or tumble, impacts,
     vines, jaws, smoke, rising glyphs, drains back to the hero), each with a body motion (lunge, charge,
     spin, brace, cast, retreat). A new action needs an entry there, or it falls back to the generic
     effect for its kind. **Enemies' moves animate as well** (`foeFx` there, called on each `fact`): each
     kind of enemy lunges, pounces, slams or charges with its own impact, or shoots its own projectile
     (`LOOK`), and a move's name can override that (`BY_NAME`: pistols, songs, breaths, beams, tidal
     waves, cannon broadsides, rockslides, hooks); area moves wash over the whole party, and a status
     rider rings the target in its colour.
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
  8. **Run end**: win or lose, the party in a row with an award under whoever led each column (most
     damage, healing, kills, hits taken; the fallen greyed, a slow ray burst behind a win), then the
     per-hero summary table, the seed and a back-to-lobby button. Dungeon forks open each path card
     with the enemies waiting down it (or the shrine where none do), and a level-up shows the hero's
     portrait.

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
  its title, a risk (`event_risk`: safe, a roll could go badly, could turn into a fight) and which
  classes would have another option. The risk is in its icon (`event`, `event_risky`, `event_fight` in
  `art.js`: a sealed note whose wax seal is green, amber or red, the fight's with a dagger through it;
  a seen event is a plain note), and a gold ✦ beside it means someone in the party has a class with
  an option there. Wrecks show their loot's rarity (a coloured dot).
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
  with an elite, from the region's middle groups): beat them and the pool is all rare, plus an enchant material. `DARK_SHRINES`
  (2) shrines are dark: the `dark_shrine` event offers +2 damage for 8 turns with Seasick, or 8 starting
  Armor for 8 turns for 8 HP, or nothing. Every lair guards a named **rare prize** (`prize` on the
  group, shown in its tooltip), added to its loot pool when it's beaten.
- **Town trades** (`spec` on each town; `TOWN_SPECS`), dealt round so each appears: a **smithy**
  reforges an equipped item into a random one of the next rarity for the same slot (30/60/100 gold;
  any work on it is lost), or **tempers** it (see Worked gear under Items),
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

### The sea, the land's secrets, raids and the weather

The owner asked for the overworld to be improved, looking at similar games (Nov 2026: items 1, 3, 5,
6 and 8 of a review: the sea after *Sunless Sea* and *Dredge*, battlegrounds after *Battle Brothers*,
raids after *Wildermyth*'s incursions and *FTL*'s fleet, lookouts after *Heroes*' observatories and
*Zelda*'s towers, the map's readability). The world's extras are made by `world.add_features` (from
the run's seed with a generator of its own, after the islands and places); their numbers are in
`content/archipelago.py` ("the sea, the land's secrets, raids, weather"); the rules are in `game.py`.

- **Currents** (`world["cur"]`: a hex -> the next hex downstream; `LANES` (3) one-way lanes of 6-9
  hexes, preferring ones that join two regions' waters): a skiff riding one pays **nothing** a hex,
  against it 2. One turn's route can be up to `PATH_MAX` (20) hexes, so a current carries a skiff a
  long way. Drawn as pale chevrons with light dashes running downstream.
- **Reefs** (`reef`, 6 single hexes near the coast): at low tide the rocks are out and no skiff can
  cross; at high tide one can (a dark shape under the water). **Whirlpools** (`pool`, up to 2, out at
  sea): no skiff can enter one, and the hexes round it cost a skiff 1 more. Both are in
  `Game.step_cost` and its copy in `rules.js` (`tools/saltbound-check.py` checks they agree).
- **Places out at sea**, reached only by skiff: two **smugglers' coves** (`COVE_GOLD` and a three-pick of
  uncommon or rare loot), three **flotsam** (`FLOTSAM_GOLD` and a two-pick) and a **drowned shrine**
  (`sea` on a shrine: Siren's Favour, +1 damage and +6 max HP for 8 turns; never dark; the first hero
  there also gets an enchant material).
- **Sea beasts** (`sea` on a group; `SEA_GROUPS`, the Reef Maw now and then from two objectives
  cleared): `SEA_MAX` (3) groups out on the water, one coming back every `SPAWN_EVERY` turns while
  there are fewer. At high tide they hunt skiffs within `SEA_HUNT` hexes, a hex a turn, over open
  water; at low tide they lie still. They never chase heroes on land, and land groups never chase
  skiffs. `MAX_GROUPS` counts only land groups (`land_groups`). Fights at sea have their own backdrop
  (`sea` in `stage.js`) and are titled "At sea".
- **Battlegrounds** (`GROUNDS`, `Game.ground_of`, `Combat.apply_ground`): a roaming or lair fight on
  hills or a peak is on **high ground**: whoever was already standing there starts with Armor (each
  hero 6; each enemy a sixth of its health). In a forest it's **ambush ground**: whoever is caught
  standing in the trees is Weak for the first round. "Already there" and "caught" come from `by`: a
  hero walking in means the enemies were there. So on a hill, wait for them; in the woods, strike
  first. The forecast says it per fight, the hex tooltip says what walking in would mean, and the fight
  shows a chip (green when it helps the party).
- **Lookouts** (one on each region's high ground): the first hero to climb one sees everything
  `LOOKOUT_SIGHT` (8) hexes round it, hidden grottos too. **Grottos** (one per region, `hidden`):
  invisible (the view leaves them out, and so does the forecast) until a hero walks within
  `GROTTO_SPOT` (1) hex (a Farsighted hero 2) or climbs a lookout near one. A **hoard** holds
  `GROTTO_GOLD`, a three-pick of rare loot and an enchant material; a **spring** heals whoever drinks fully and gives the
  party a revive.
- **Raids** (`raid` on a group; `spawn_raid`, `raid_road`, `occupy`, `raids_beaten`): from turn
  `RAID_FROM` (8), every `RAID_EVERY` (8) turns, an objective not yet cleared sends a band (its
  region's enemies, elite-led) to take a town 6-14 turns' march away (`RAID_RANGE`), at most
  `RAID_MAX` (2) at once. A raid keeps to its road a hex a turn (`raid_road`: the shortest walk over
  land, off towns and places), ignoring heroes, so standing in its way means a fight; it's always shown,
  with its road dashed red to a ringed town and the turns left. **Beat it on the road**: `RAID_BOUNTY`
  gold each, and its objective's garrison skips its next growth (`garrison_skip`). **If it reaches the
  town with nobody there**, the town is occupied: its shop, inn, board and trade are shut (the raiders
  stand on its hex, so walking in is a fight), and the objective's garrison grows at once. Freeing it
  pays `FREE_GOLD` each and restocks its shop (`restock`). A hero standing in the town when the raid
  arrives fights it there. No merchant ship docks at an occupied town.
- **Squalls** (`squalls` in the state; `tick_squalls`, `in_squall`): from turn `SQUALL_FROM` (4),
  every `SQUALL_EVERY` (6) turns while fewer than `SQUALL_MAX` (2) are about, a squall gathers over
  Stormcrag's waters and drifts a hex a turn toward the middle of the map for `SQUALL_TURNS` (7). A
  hero inside one (within `SQUALL_R` (1)) sees only `SQUALL_SIGHT` (2) hexes, for the map and for
  enemies. Drawn as a dark cloud with rain, above the fog, with a dashed ring where it goes next.
- **Reading the map**: the objectives and the peak are **landmarks** (`world_msg`'s `landmarks`),
  drawn tall above the fog so the party always knows which way to go (the Lighthouse's beam sweeps
  until it's cleared); "Next" in the top bar points at them. Zoomed all the way out, region names
  label the map. A **minimap** (bottom right; hidden on phones) shows what's been seen, the heroes,
  objectives, raids, opportunities and squalls, and the camera's view; click it to look there. The
  surf washes in and out (two foam frames cross-faded), currents flow and whirlpools turn. "This
  turn" keeps the heroes' lines at the top and the world's news (arrivals, raids, squalls,
  opportunities, jobs) in a list under them that scrolls when it's long.
- **The bots** go after a raid they can catch before it arrives, steer clear of occupied towns when
  they need healing, and visit lookouts, found grottos and (once every hero has a skiff) sea places.

### Regions and biomes

Owner's request (2026-11-04): each objective has its own biome, and which three a run gets is random.

- **Drawing them**: `world.generate(seed, pool)` draws three of `A.REGION_POOL` (the eleven keys of
  `DUNGEONS`) with its own `Rng(seed ^ 0x0B1EC7)`, lays them round the peak in that order and stores
  them as `world["regions"]`. Everything reads a run's regions through `Wd.regions(w)` /
  `Game.regions()`; a world from an older save has no list and gets the original three, so old saves
  play as before (checked: an old-style run plays to the end). The browser reads `world.regions`
  (`worldRegions()` in `hud.js`). `Game.near_region(t)` is the region a hex belongs to, or for the peak
  and the small islands the drawn region whose objective is nearest (whose enemies guard a wreck or a
  lair there); `Game.region_here(t)` is the hex's region only if it was drawn.
- **Content**: the eight new regions live in `content/biomes.py`, merged into `archipelago.py`'s tables
  on import (FOES, POOLS, GROUPS, LAIRS, DUNGEONS, BIG, REGION_NAMES, BUFFS, EVENTS; crits into
  `foes.FOE_CRIT`). Each has six regular enemies, an elite, a roaming big threat (`BIG`, also its
  Champion's Hall), a boss with a five-move `seq` and a bloodied rule, three lineups per dungeon step,
  eight roaming groups by tier, two lairs, three events of its own and (the Vale) four dreams.
- **The land**: a hex keeps its base kind (`bio`: beach, grass, forest, hills, peak), which every rule
  reads (costs, high ground, lookouts, grottos, map talents); a drawn region only changes how it's
  painted and named (`SKIN` and `PROPS` in `hexmap.js`, `SKINS` in `biomes.py` for the tooltip names:
  Ash field, Deep jungle, Glacier...). Each region's map rule is in `biome.py` (a mixin on `Game`); its
  one-line summary is `RULES` (the objectives tooltip):

  | Region | Map rule | Battleground (`A.GROUNDS`, by the region's terrain) |
  |---|---|---|
  | Cinderreach | The volcano (its objective's hex) erupts every `ERUPT_EVERY` (7) turns from turn 5, with a turn's warning (forecast line, toast): `LAVA_FLOWS` (2) flows run downhill up to `LAVA_LEN` (5) hexes and block them (`s["lava"]`) for `LAVA_TURNS` (4) turns. Never on a hero, group, town or place. | **Embers** (ash fields, black sand): both sides start Burning 1. |
  | the Shifting Sands | `SINKS` (6) quicksand hexes (`world["sink"]`) cost `SINK_COST` (4) moves; sandstorms (sight 1) drift over the dunes; `OASES` (2) heal fully and lift curses, once per hero. | **Sinking sand** (dunes): whoever walked in is Rooted for round 1. |
  | the Stillwood | Blessings and curses don't run down for a hero standing there (`timeless`); `FOSSILS` (2) beds give a three-pick of better loot and `FOSSIL_XP` (10). | **Stone sleep** (petrified woods, only when the party walks in): the enemies (not bigs or bosses) start asleep. |
  | the Verdant Deep | Deep jungle (its forest) costs `JUNGLE_COST` (3); walking through cuts a trail (`s["trails"]`) that costs 1 for everyone for `TRAIL_TURNS` (8) turns; inside it you see `JUNGLE_SIGHT` (2). Map talents still make it 1. | **Ambush ground** as in any forest. |
  | Aetherhold | `GATES` (2) pairs of light-gates: one end there, one near the start town or far off on another region; ending a move on one carries you to its twin (`gate`'s `to`). Resting heals `GRACE_REST` (20%) more; its shrines bless everyone on the hex. | **Hallowed ground** (meadows): both sides heal 3 each round from round 2. |
  | the Prism Wood | Everyone sees `PRISM_SIGHT` (2) further there, and its enemies notice heroes from `PRISM_HUNT` (5); `GEODES` (2) hold an enchant material each. | **Resonance** (crystal forest): every hit from either side deals +2 (`dmg_bonus` for heroes, might for enemies). |
  | the Drowsing Vale | Resting anywhere there (not on a place) heals at least `DREAM_REST` (50%, a camp's) and brings a dream (an event with `dream`, never placed). | **Lulling flowers** (lavender): whoever walked in is drowsy: heroes Hexed, enemies Weak. |
  | the Frostpeaks | Open water within `ICE_REACH` (2) of its land (and nearer it than any other) is frozen (`world["ice"]`): terrain `ice`, 2 moves, no skiff, sea beasts can't enter; blizzards (sight 2) drift over it; ending a turn on its glacier or summit away from a town or camp gives **Frostbite** (−5 max HP, 4 turns; a town or camp thaws it). | **Snowdrift** (snowfields): whoever walked in is half buried: heroes lose a die to the cold, enemies Rooted. |

- **Storms** generalise the squall: each has a `kind` (`A.STORMS`: squall over Stormcrag's water,
  sandstorm over the Sands' land, blizzard over the Frostpeaks), formed only if its region was drawn,
  with its own sight (`Game.storm_sight`); the map draws rain, blown sand or snow.
- **New enemy traits** (in `combat.py`'s round upkeep and death, `bosses.py`, `foes.py`): `regen` N,
  `armor_round` N, `ember` N (Burns every hero when it dies), `aura_heal` N (the other enemies heal
  each round), `sleeper` (asleep, intent "Asleep", until a hero hits it). Shown as chips by
  `foeTraits` in `rules.js`.
- **Generic bloodied rules** (`Bosses.bloodied_rule`, run each round once bloodied): `summon` (a new
  enemy each round), `thorns` (`thorns_x`, growing by `grow`), `curse` (a status on all, the
  healthiest or a random hero every `every` rounds), `fall` (a hero is marked `falling` and takes a
  blow at the round's end that Armor or a Guard stops, with a status: Falling Magma, the Avalanche),
  `ward` (half damage while one of `by` stands: the Radiant Arbiter behind her Sentinels), `regen`.
  The Great Sandworm reuses the Reef Maw's `swallow`.
- **Balance passes** (fast bots, 60 Normal runs): Cinderreach and the Stillwood started near 50%
  (the originals near 90%); embers, ember deaths, falling magma, the stone enemies' Armor, the stun
  gazes and the curses were cut, which brought every region to 80-100% (the originals 100%). Then
  full bots, 300 Hard runs, seed 5000 (baseline 46%): **29.7%** at first (elite escorts stacking in
  garrisons, bosses too strong) → escorts made regulars, fewer boss dice, slower bloodied rules:
  **32.3%** → the new regions' regular enemies at 90% health (`REGULAR_HP`), boss health down to
  64-72, the Rime Matriarch freezing one random hero, the Shard Queen's thorns static: **47.3%**.
  By region (won, objective cleared): the Drowsing Vale 54%, the Verdant Deep 54%, the Stillwood
  50%, the Sands 48%, Aetherhold 46%, the Frostpeaks 44%, Cinderreach 41%, the Prism Wood 41%
  (the originals 43-57%).
- **Art**: `tools/saltbound-art/foes2.py` (73 sprites, built into `sprites.js` with the rest),
  `stage.js` (an open-ground scene and a dungeon interior per region: `ash`...`frost`, `forge`, `tomb`,
  `heartwood`, `ziggurat`, `spire`, `geode`, `palace`, `glacier`), `hexmap.js` (ground palettes, props,
  ice, quicksand rings, lava with pulsing cores and trails in `drawBiome`, a landmark per objective),
  `art.js` (oasis, fossil, geode and gate icons), `skillfx.js` (`LOOK` per enemy, name patterns for
  fire, frost, sand, spores and light).

### Quests, regional gear and boons

Owner's request (2026-11-04): more events and quests for the new regions, special rewards, and 50 more
weapons, armor and trinkets.

- **Quests** (`content/quests.py`, run by the `Quests` mixin in `quests.py`): each of the eight newer
  regions has one (`A.QUESTS`), offered by a **quest-giver** (place kind `quest`, `q` = the region, a
  banner on the map) that `Game.place_quests` puts near the middle of each drawn region at setup
  (old saves have none). A quest is three events: the giver's, then two **sites** chosen in the region
  (`quest_site`, 3-7 hexes on from where the last step was done). A choice moves it with
  `"quest": "start"` (a `kind: "trail"` entry in `s["quests"]`, beside the town jobs, so the log, the
  forecast and the map tag show it: a gold ★ tag, no deadline) or `"quest": "next"`. A fight's choice
  carries **`win`**: an outcome played (`Game.outcome`, from `fight_won`) only if the party wins, so a
  lost fight or a step turned down leaves the site to come back to; nothing fails a quest. Each last
  step offers a choice: fight the region's big threat for its **relic**, or a check (or a class
  option) for a **boon** plus a forge material.
- **New outcome keys**: `give` (one particular item, offered as a pick: it can be handed on or left),
  `mat` (a material into the bag, a key or `"random"` for an enchant one), `win`; a `buff` may now be
  a boon.
- **Boons** (`BOONS`, merged into `A.BUFFS` with `perm`): buffs that never run out (the turn tick skips
  them; the UI says "for good"; a temple's cleanse and an oasis only lift curses). Three bend their
  region's map rule, read by `Biomes.boon_mods` (cheap, for route-finding) and mirrored by `perk` in
  `rules.js`: **Sandstrider** (`sandwalk`: quicksand costs what the land under it does), **Jungle-Born**
  (`junglewalk`: deep jungle costs 1), **Frostborn** (`frostborn`: no Frostbite, the frozen sea costs 1).
  The others are fight mods (Emberheart, Stoneblood, Haloed, Clear-Eyed, Lucid Dreamer).
- **Relics** (`unique`, in `content/gear2.py`): eight legendaries, one per quest, never in the loot
  (`I.RELICS`; `I.GEAR` leaves them out): Phoenix Plume, Sun-King's Khopesh, Heart of the Stillwood,
  Fang of the Jade Serpent, Wings of the Arbiter, the Heartprism, Somnarch's Lantern, Rimeheart.
- **Regional gear** (`content/gear2.py`, merged into `items.ITEMS` before the guard dice are set): 52
  pieces (22 weapons, 16 armor, 14 trinkets), six or seven per region, each tagged `region`.
  **`Game.gear()`** is the run's loot list: the catalogue less the regional pieces of regions it didn't
  draw (every loot, shop, prize, ship, reforge and job-reward pick goes through it). Their passives use
  only mod keys the engine already reads, written out in `text`. Eight new weapon actions, one per
  region (`gear2.ACTIONS`: Cinder Cleave, Scouring Wind, Stone Gaze, Vine Lash, Smite, Prism Ray, Lull,
  Glacial Strike), and one armor action, Stoneform (the die +2 as Armor).
- **Materials**: the **Fate Feather** (enchant: a Fate die) joins the random pool (`I.MATERIALS`).
  **Starmetal** (hone) and **Wyrm's Ember** (mark) are forge materials (`forge`, `I.FORGE_MATS`), only
  from quests and events: they do what the smith's Hone or Mark would, free, and **don't count against
  the work limit** (their work is recorded as `star:hone` / `star:mark`; `Game.works` skips it; the
  pips show it as a round gold pip).
- **More events**: two more per region (16, `region`), several selling or hiding a particular regional
  piece (`give`) or a forge material: the Smith in the Caldera, the Starfall Crater, the Ice Forge...
- **Bots**: go to a quest-giver they can see within 6 hexes, and to a quest site from level 3 (even
  when a dungeon is due, if it's within 8); they take the first choice (the fight) when healthy, so in
  the simulator almost every drawn quest is finished: the batch numbers are a party that does them all.
  They put forge materials into the weapon, else the trinket, else the armor.

### Events in multiplayer

The owner asked for events to be shared between the three players (Nov 2026: item 7 of a review of
three-player multiplayer). Rules in `game.py` (`do_choose`, `resolve_event`, `share_bad`,
`do_suggest`, `do_ask`); the browser's side is `renderPartyEvents` and the event, huddle and help
sections of the results screen in `hud.js`.

- **Everyone sees an ally's event as it happens.** While a hero is at an event, the other players get
  a strip under the top bar ("Bob is at: The Stranded Skiff") that opens into the story, each choice
  with its odds and stakes, and what it means for them: it could start a fight (anyone within a hex is
  pulled in; flagged red when they are), good outcomes reach everyone on the hex, or it has a party
  check they could chip in to. When it's settled, everyone gets a toast of the outcome.
- **Ask the party, and suggest.** The hero at the event can ask the party (`ask`): the strip opens on
  everyone's screen with a toast and a sound. Anyone can suggest a choice (`suggest`, stored as `sugg`
  on the event's dialog); suggestions show on the chooser's buttons ("Alice suggests this"). They're
  only advice.
- **Party checks are chipped in to.** Choosing a party check (`check.die == "party"`) with allies on the
  hex opens a huddle (`huddle` on the event's dialog) and gives each of them a `help` dialog: chip in
  (roll your best die too; the best roll counts) or not. If the check fails, everyone who chipped in
  shares its harm: its HP loss, gold loss and curses (`share_bad`); a fight pulls in everyone nearby
  anyway. The check rolls once every ally has answered, or when the chooser rolls early; the chooser
  can also take it back and pick something else. Both sides see the odds alone and with help. Before,
  a party check simply used the best die of anyone on the hex.
- **The bots** chip in while they have half their health or more, and a bot at an event waits for its
  huddle to be answered.

### Animation and feedback

The owner asked for every idea of a review of the UI's graphics and animation (Nov 2026). Everything
here respects `prefers-reduced-motion` (each block of CSS ends with its own guard).

- **Pose frames** (`art.js` `poseCanvas`/`poseURL`, `POSES`): every character has one drawn frame; the
  fights' other poses are made from its pixel grid before the outline and shading, so they get the
  same finish. `attack` leans into the swing, `cast` and `hurt` lean back (hurt further, knocked a
  pixel back), `fallen` lies on its back (a creature wider than it's tall rolls belly-up instead). A
  fighter shows the pose for the motion it's playing (`POSE_OF` in `combat.js`: a lunge, slam or
  charge is `attack`; cast, brace, a big heal or the victory hop `cast`; a hit `hurt`; a kill or
  being knocked down `fallen`). `warmPoses` decodes a character's poses the first time it's drawn.
- **Map tokens** (`hexmap.js`): heroes and enemies bob while they wait (`bob`), hop on every hex as
  they move (`playMove`), a hero in a skiff rocks on the swell, a group that will step toward the
  party this turn shows a bouncing "!" (from the forecast's `steps`), and where a fight starts crossed
  blades flash with sparks (`clash`, from the `fight` effect) before the fight opens (`holdCombat`
  waits for it).
- **Dice**: a big die in the roll tray flickers through its own faces, blurred, as it tumbles
  (`flickFaces`, from the faces the roll passes along), then lands; a shield, skull, wild or elemental
  face flips in with its own colour; a crit lands with a squash-and-stretch thump and a gold ring. In
  the hand, a Swell die is drawn bigger with every round it waits and pops when it grows; an Echo die
  copying a play gets a link line drawn from the hero who made it.
- **The enemy turn**: while an enemy rolls, it lifts and glows red, its intent card lights, and a
  dashed aim line draws to each target (`fxLine`). Damage soaked by Armor chips off in shield shards;
  a health bar that loses health keeps a pale trail that drains down to the new value (`noteLag`,
  `hpBar`'s `lag`).
- **Statuses on the fighters** (`statusAura`, `statusCls`): over the sprite (each fighter's sprite sits
  in a `.fig` with an overlay the same size), Poison drips, Burn throws up embers, Shock sparks, Mark is
  a scope ring, a Stun circles stars (and tilts the sprite), Root grows vines at the feet, Freeze
  frosts the sprite over with ice at its feet, Vulnerable pulses red, Hex throws off motes, Weak sags
  the sprite. Each loop keeps its phase across redraws.
- **Battlegrounds on the stage** (`stageURL(key, ground)`): high ground paints a lit rocky slope under
  the side holding it; ambush ground hangs dark trees and undergrowth over the edges, with leaves
  drifting down.
- **Victory**: the heroes still standing hop with their arms raised, and the banner counts up the
  gold each and the XP (the `fightend` effect carries them for a won fight).
- **Loot and level-ups**: loot cards are dealt face down and flip over, flaring in their rarity's
  colour (uncommon green, rare blue, legendary gold); a level-up pick flies from the dialog into its
  hero's card, which flashes gold.
- **The tide and the weather**: when the tide rises a wave of light washes across the map and each
  arrival comes in where it lands (rings, and a boat from the nearest open water for wreckage and
  landings: `arrive`); the hexes under a squall go dark; at high tide the whole map is a shade darker
  and bluer.

### Fights

- **A round** (`Combat.new_round`): enrage, elite affixes, Crown of Thorns, Poison and regeneration
  (`round_upkeep`); each hero's dice (`deal_dice`, `round_dice`), then what enemies did to them
  (`dice_attacks`); spirit dice for the fallen; boss and enemy upkeep (`crown_round`, `foe_round`);
  the enemies' intents. The party plays actions, each resolving the moment it's played
  (`do_place` → `resolve_action` → `run_ops`). When everyone is ready, summons and pets act, then
  enemies fastest first (`resolve_round`), then end-of-round effects (`end_round`: Triage, Burn,
  Doom, statuses ticking down, the heroes' Armor clearing, the Crown's phase).
- **Enemy Armor lasts from one enemy turn to the next** (owner's request, Nov 2026): it clears when
  the enemies' turn starts (`resolve_round`), not at the end of the round. Before, what a Block, a
  Guard or a shield face gave was wiped the moment the round ended, so it never met a hero's attack
  (only Ironclad's, given at the start of the round, did). No balance run was done after the change.
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
- **Crits** (owner's request: the number on the die should matter more): a die that lands on its top
  face (a 6 on a d6, an 8 on a d8; **a d10 or bigger on its top two faces**, so big dice crit about as
  often as small ones: `crit_floor`; a wild face, or a value pushed past the top by Inspire and the
  like, counts too; shields and skulls never do) makes the action also do its **crit**. Every class's
  basic, every weapon action, Block and every armor action has one (`crits.py`: `CRITS[key] = (ops,
  card line, sentence)`; importing it writes `crit`, `crit_short` and a closing "Crit: ..." sentence
  onto the action). The extra ops run after the action's own when it hits (`Combat.act`, `is_crit`),
  and the bots count them in each outcome they weigh (`bot.evaluate`). The card shows a gold
  "crit: ..." line under the effect, with a tooltip saying what a crit is (`CRIT_TIP`); in a fight the
  roll tray rings a die that crits and the hero gets a gold "Crit!". Crits are kept to a flavour each
  class owns (Strike gains Armor, Stab Poisons 1, Toss Burns, Shoot carries on to another enemy, Riposte
  Cut strikes again and gains 3 Armor, Hack hits again for half and heals 5) and are never a Stun. The
  Scoundrel's are small on purpose: its two linked dice roll the same, so they crit together. About one action in five crits. **Balance (2026-11-03, seed 5000):** with crits, armor actions and weapon
  faces Hard went from 46% to 83%; the owner chose to answer with enemy crits and harder-hitting
  enemies (Hard `foe_dmg` 2.3 → 2.8, Normal 1.75 → 2.3). Now **Hard 45%** (300 runs; classes 35–58%:
  Scoundrel 58, Ranger 50, Warden 49, Alchemist 48, Mender 46, Vanguard 43, Herald 42, Arcanist 41,
  Duelist 37, Berserker 35) and **Normal 90%** (150 runs). Then the class pass (enemy Armor breaks
  became statuses, big dice crit on their top two faces, Scoundrel Poison crits 1, Riposte Cut and
  Hack crits gained Armor and healing): **Hard 44%**, classes 35–52% (Ranger 52, Scoundrel 46, Alchemist
  and Arcanist 46, Herald 45, Warden 44, Mender 43, Berserker 43 (was 35), Vanguard 42, Duelist 35). The
  Duelist dealt the most damage but died the most (0.70 a run), so its HP went 27 → 31: parties with a
  Duelist now win 52% (150 hard runs, `--with=duelist`).
- **Cooldowns** (`"cd": N`): only basic attacks are usable every round (owner's request). `FREE` in
  `classes.py` lists what's exempt (each class's basic, the Vanguard's Brace, Block, Flee and weapon
  actions except Sweep and Tidal). Everything else has 2; the biggest skills 3. Lift is once per rest
  (`per_rest`, the hero's `spent` list).
- **Swell and Echo dice** (owner's request: dice that change what you plan around). The **Swell die**
  (Building Rage for the Berserker, Sap Rising for the Warden) starts each fight as a d4 and grows a
  step each round it's left unused: d10 +2, d12 +7, d20 +12 (`SWELL` in `tuning.py`); using it starts it
  over. Each step pays more per round waited than spending it every round (2.5 a round; then 3.75,
  4.5, 5.6), so holding it is the play and the decision is when to cash it in (the owner asked that the
  growth be worth more than using it each turn). Enemies' die attacks (Hex, theft, Barnacle Crust)
  never take it. The bots hold it until it's a d12 +7, unless the fight is nearly won or they're about
  to go down. The **Echo die** (Echo Chorus for the Herald, Mirror Step for the Duelist) is a d8 until
  an ally uses a die this round; then it shows the biggest number of that ally's last play
  (`Combat.echo_out`, after every action and instant), so the order of play is a party decision, and a
  copied number always matches for Pincer.
- **Dice picks** (owner's request: more level-ups that change dice): passives that change a hero's
  dice for the fight (`Combat.dice_picks`; `NEW_DICE_PICKS` in `classes.py` adds them to the pools):
  Shield Rim (Vanguard: the armor die's two lowest faces become shield faces), Wild Surge (Arcanist:
  the biggest die's two lowest faces are wild), Steady Hands (Mender: every die is Steady), Fated Blade (Duelist:
  the weapon die is a Fate die), Powder Edge (Berserker: the weapon die explodes), Hawk's Eye (Ranger:
  the Augur die is a Seer die), Loaded Bones (Scoundrel: linked dice's 1s and 2s are wild), Reactive Mix
  (Alchemist: the weapon die's two lowest numbers burn and poison), plus the Swell and Echo picks.
  Measured (2026-11-03, 300 hard runs, seed 5000: **Hard 48%**, classes 40–55%), picks against those
  passed up at the same level-up: Building Rage +12, Hawk's Eye +8, Mirror Step, Reactive Mix and Sap
  Rising +4, Steady Hands +3, the rest within noise, except Loaded Bones −26, Wild Surge −16 and Shield
  Rim −9. A same-seed A/B (60 runs each) put the first two at −10 and −5, so they were small, not
  broken: one face each barely moved a die. Each now changes its die's two lowest faces (not yet
  re-measured).
- **Guard dice** (owner's choice): every armor's die carries `guard` and only goes on
  defensive actions (`is_defensive`, sent as each action's `def`). Every hero has a defensive action
  for it, so a guard die is never wasted.
- **Armor actions** (owner's request: armor should play differently): every armor brings its own
  defensive action, which **takes Block's place** for its wearer (`guard` on the item, from
  `GUARD_ACT`; `Game.actions_of` swaps it in; the actions are `ARMOR_ACTIONS` in `items.py`): Hunker
  Down (die +1 Armor: the plain coats), Patch Up (die Armor, heal 2: the healers' robes), Coral Growth
  (heal 3: Coral Mail, whose old "Block heals 2" passive it replaced), Bristle (attackers take 2:
  Barnacle Plate, Sharkskin), Sidestep (5+: dodge the next hit: Mistweave, Smuggler's Cloak), Echo
  Shell (attacks aimed at you −2: Siren's Conch; `to: "aiming"`), Cover (you or an ally: Diver's
  Harness, Whaleplate, Gilded Cuirass) and Tidewall (the party +2: Tidelord's Aegis). Plain Block is
  left only for a hero with no armor. The hero sheet and item rows name the action.
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
  one replacing the oldest. Enemies pick targets when they choose their intents, at the start of the
  round, from the heroes and summons standing then; so a summon would protect nobody in the round it
  arrives. Two rules fix that (owner's request, Nov 2026; `summon`, `summon_pull` in `combat.py`):
  **a new summon draws one attack** (the first enemy to act with a single-target attack on a hero, one
  aimed at its Warden first; not while a Taunt holds), and **a replacement takes over the attacks aimed
  at the summon it replaced** (they used to fall back on a random target, often a hero). The bots count
  the drawn hit when valuing a summon (`bot.evaluate`). **The Ranger's hawk** is a die, not a unit (Companion a d6; Alpha a d8 and
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
| Vanguard | 46 (+5) | **Trailbreaker**: rough ground costs 1 | Tank | Bulwark, Juggernaut |
| Duelist | 31 (+4) | **Ambush**: a fight they start gives the party a free first round | Single-target damage | Flurry, Precision |
| Berserker | 32 (+4) | **Forage**: camps heal them fully | High-risk damage | Bloodlust, Rampage |
| Ranger | 24 (+4) | **Tracker**: spots enemies 2 hexes further | Ranged damage | Marksman, Beastmaster |
| Arcanist | 23 (+4) | **Farsight**: sees 1 hex further; spots cursed loot | AoE and burst | Elementalist, Hexer |
| Mender | 21 (+4) | **Field Medic**: resting on their hex heals everyone there an extra 10% | Healer | Restoration, Warding |
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

- **Enemy crits** (owner's request, to answer the heroes' crits): an attack or party-wide move whose
  die lands on its top face (a d10 or bigger: its top two; or explodes past it) crits, with its
  kind's effect (`FOE_CRIT` in `foes.py`, written onto `A.FOES` as `crit` and `crit_text`): mostly a
  **status** on whoever it hits (owner's request: statuses, not effects that undo what a player did;
  an Armor break was tried and removed): Poison 2 (Deckhand, Cutthroat, Deckhound), Weak (Jellyfloat,
  Barnacle Priest, Crag Ram, Harpy, Storm Roc), Vulnerable (Crab, Tide Guard), Mark (Siren, Corsair
  Captain, Lamp Keeper), Shock (Reef Eel, the storm enemies), Root (Cliff Hermit, Iron Bosun), Burn 2
  (the powder), Hex (Tide Cultist), a crusted die (Brine Golem); the bosses and a few heavy hitters
  hit for half again (`half`). The roll tray rings the die and says "Crit!", the
  intent's tooltip says what its crit does, and the bots expect it (`foe_hits`: the chance times half
  again, or ~2 for a rider). Debuffs, blocks and heals never crit.
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

About 145 items (`ITEMS` in `content/items.py`, with the regional gear, relics and materials from `content/gear2.py`; 111 that can drop, of which a run sees the original 59 plus its regions' pieces, `Game.gear()`; each has a pixel icon, `ICON` in `js/itemart.js`): weapons give a die and actions, armor a guard die and
often a passive, trinkets an odd die, a passive or an action. Gear past the starting kit has a passive
of its own (`PASSIVES` in `items.py`, merged into each item's `mods` and `text`). **Situational finds** (owner's request: a common or uncommon should sometimes beat a rare): the
Shellbreaker Maul ignores Armor, the Oilskin Coat stops Burns, the Diver's Harness a Stun and Freeze,
the Smuggler's Cloak turns the first enemy each round that would attack you onto someone else (its own
mod, `cloak`; the Ranger's Camouflage passive is the stronger "only when there's no one else"), the Gutting Knife
finishes the wounded, the Gull-Feather Bow punishes enemies aiming elsewhere, and so on. **Rule-benders**
(the end of `ITEMS`): Forked Staff (a single-target spell also hits another enemy for half), Siren's
Conch (whoever hits you is Marked), Tide Hourglass (your biggest unused die carries over), Powder
Heart (every die explodes, −6 max HP), Weighted Coin (a 1 counts as the top face), Bloodstone (out of
rerolls, a miss rerolls for 3 HP), Bosun's Whistle (combos +2), Bosun's Bell (an action: pass a die
to an ally; key `pass_die`) and Sea-Glass Lens (your armor's die can go on attacks). Shop rows and loot
cards compare with what you wear in that slot (the die, the change in average, the actions you'd
lose, the passive). An armor's die shows its **Block average** (`blockAvg` in `hud.js`), and armor
compares on that: a shield face is 3 Armor on Block but 0 on an attack, so shield-heavy armor is
steadier, not stronger, unless a Vanguard's Shieldwall makes each shield worth 5. Only armor dice are
guard dice (`GUARD_TRINKETS` is empty: Lucky Shell and Pearl Charm used to be, a hidden cost no other
trinket had). No common may be strictly worse than starting gear (owner's request): the Fishing
Spear (a Rapier) and Sailcloth Wrap (a worse Wool Robe) were removed; save v5 swaps them for those.

**Weapon faces** (owner's request): every found weapon but the Heirloom Sword (whose faces grow
with the party's level) has a special face or two, in its theme: freeze faces on the harpoons, the
Driftwood Staff, the Leviathan Rod and the Forked Staff; poison on the Gutting Knife; a burn on the
Flintlock; shield faces on the Coral Blade, Boarding Axe, Shellbreaker Maul and Crownbreaker; a wild
top face on the Chaplain's Censer, Captain's Sabre, Gull-Feather Bow and Reef Lantern (a wild face
always crits). Starting weapons stay plain.

**Item audit (2026-11-03).** Fixed: Tide Hammer's die became `[2..8, S]` (it was worse than the
starting Great Axe); Drowned Idol has one 12, not two (it averaged ~17 a roll); a freeze face now
freezes before its own hit, so Frostbite and the Frost Locket (now three freeze faces) count on it;
Bosun's Bell's passed die rolls 2 higher; Sharkskin's thorns 1→3 (it trailed the common Barnacle
Plate); Rum Flask heals 5 a kill and rests 15% better; Ember Charm's Burns +2; Spyglass is a seer d8;
Captain's Medal and Leviathan Rod's texts now say what they do (above half health; Weak for the first
round). Measured after, with the **loot picks** table (300 hard runs, seed 5000, 46% won): every item is
within about ±10 points of the runs that passed it up at the same moment, inside the noise (±6 at
~130 picks). The most negative were Salt-Crusted Locket −11, Boarding Axe and Cork Vest −10, Brass
Compass −9, Flintlock and Sharkskin −8; the most positive Frost Locket +9. Tide Hourglass's runs win
42% whether they take it or not (other legendaries' 60–65%), so where it's offered, not the item,
sets that.

**Worked gear** (owner's request, 2026-11-04: a way to invest in a weapon you like rather than gamble
it on a reforge). Every piece of gear takes at most `WORK_CAP` (2) **works**, shown as diamond pips on
its row (`workPips` in `hud.js`), tempering and enchanting together:

- **Tempering, at a smithy** (`do_temper`, `temper_options`): **Hone** raises the die's lowest number
  by `HONE_UP` (3), no higher than its top number (numbers stay in order); **Mark** turns the lowest
  number into a special face in the item's own style (`temper_face`): a shield on armor, else more of
  the die's burn, freeze or poison (as strong as its strongest such face), else a wild face. The first
  work on an item costs 15/20/30/45 gold for a common/uncommon/rare/legendary, the second twice that
  (`TEMPER_COST`; owner's request: rarer gear costs more to work, as it does to reforge). The smithy tab shows each option's
  die before you pay.
- **Enchant materials** (`MATERIALS` in `items.py`: Powder Salt for Exploding, Still Pearl for Steady,
  Seer's Glass for Seer): rare consumables that are never sold or dropped at random. The sea shrine
  gives one to the first hero there (`mat_taken`), a grotto's hoard holds one, and a guarded wreck's
  pool has one beside its rare gear. Any other won fight's loot pool holds one `FIGHT_MAT_CHANCE` (6%)
  of the time (owner's request: rarely from fights too), about 0.6 a run on Normal from ~11 pools. From the bag, "Into <item>" rubs it into a piece of gear you
  wear, out of fights (`enchant`, through `do_use` with a `slot`); a die can't take a kind it
  already has. Enemies that snatch consumables leave materials alone.
- **Where the work lives**: worked gear gets its own key, `<item>@<n>` (`rework`), with a record in
  `s["forged"]` (base item, die, kinds, the works done), so the work goes wherever that item goes:
  the bag, an ally, a sale. `Game.item(key)` resolves any key (use it, never `I.ITEMS[key]`);
  `I.base(key)` gives the catalogue key. The view sends the records as `forged`, which the browser
  merges into `static.items` and `static.prices`; item icons use the base key. A worked item sells
  for `WORK_RESALE` (10) more per work. Selling, dropping or reforging it forgets its record.
- **Bots** put materials into the weapon, else the trinket, else the armor; at a smithy they reforge
  only unworked gear, then temper (Mark on weapons and trinkets, Hone on armor) with 25 gold to spare.
- **Measured** (2026-11-04, 300 Hard runs, seed 5000): **Hard 45.3%** against 46.0% before, inside
  the noise, with about 2 works a run (646 temper and enchant effects). Gold already goes on inns,
  reforges and gear, so the bots work little; players who save for it will get more out of it. Not
  re-tuned: the owner reviews balance.

**Skill texts** follow one style (owner's request: clearer): "the die" is the number it shows, "On
5+:" is what a roll meeting the requirement does and "Otherwise:" what a lower one does, "Any row"
comes first, and enemies' "intents" are called their coming attack or action.

## Balance now

`docs/saltbound-skills.md` distils what follows into guidance for tuning and designing picks:
what tends to be strong, weak and fun, the design checklist, and how to measure.

**Latest (Nov 2026, after the quests, regional gear and boons; 300 Hard runs, seed 5000): 56.3%**,
up from 47.3% with the eleven regions alone. The bots finish almost every drawn quest (a relic or a
boon each), and runs are much longer (114 turns on average, from 69; 37 rises, from 22) as they
detour for them; classes 48-65% (Scoundrel 65, Vanguard 48), regions 48-63%. Not retuned yet: it's
over the ~50% target, for the owner to decide (levers: the quest finales' fights, the relics' and
boons' strength, or the bots' detours).

**Before that (after the sea, battlegrounds, raids, lookouts and grottos; 300 Hard runs, seed
5000): 46.0%** (48% before, within noise), classes 40-52% (Herald 52, Mender 40). Runs are longer
(73 turns on average, from 59) with more roaming fights (6.5 a run, from 4.9): the bots chase raids
and fight sea beasts. More losses come before the first objective (67 of 162, from 43 of 157),
mostly early raid interceptions. Nothing was retuned.

The owner reviews every balance change: ask before changing a class or the difficulty, and give the
options with their trade-offs. **Hard's target is now about 50% for the bots (owner, Nov 2026, "for
now"; it was 30–35% while the bots split up) with no class far ahead; leave the difficulty
multipliers alone unless the owner asks.** Boss health is `BOSS_HP` in `content/archipelago.py`
(1.0: at 1.1–1.25 most losing parties died at their first dungeon).

- **Summons draw an attack on arrival** (Nov 2026; 300 Hard runs with a Warden in every party, seed
  5000, before and after): **Warden parties 39% → 50%**, the Warden's deaths 0.67 → 0.55 a run and
  damage taken 3.3 → 2.6 a round; the Crown won 45% → 34% of its fights. The bots summon more now that
  they count the drawn hit: Sprout 5151 → 6360 casts, Swarm 632 → 1326, Call Bear 53 → 400.
- **Difficulty** (`DIFFICULTY` in `game.py`): Story 1.0× enemy HP and 0.95× damage, 4 revives, a rise
  every 4 turns; Normal 1.9× / 1.75×, 3 revives, a rise every 3; Hard 2.35× / 2.3×, 2 revives, a rise
  every 3. Enemies also gain 15% HP and 10% damage per tier (objective cleared), and `SURGE` per rise
  of the tide.
- **Objectives scale with the party** (owner's request, Nov 2026: so the expected power at each
  objective is easier to tune): dungeon fights (all three of an objective's, boss included) also take
  `DUNGEON_STEP_HP` / `DUNGEON_STEP_DMG` in `tuning.py` by objectives cleared: 0.85×/0.9× for the first,
  1.0×/1.0× for the second, 1.15×/1.1× for the third (`start_fight`, `f["hpmul"]`). With the tier on
  top, the first objective's enemies have 85% health and the third's 150%. (Steps of 1.1 and 1.35 made
  the later objectives too steep: Hard 36%, most losses at the second and third.) The objectives' tooltip
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
- **Vanguard and Herald level-ups replaced** (owner's request, Nov 2026: swap the least fun picks for
  ones at the right power; 300 Hard runs, seed 5000): **Hard 48%**, every class 42–55%: Vanguard 55%,
  Berserker 52%, Scoundrel 52%, Alchemist 49%, Arcanist 49%, Ranger 48%, Mender 47%, Duelist 45%,
  Warden 42%, Herald 42% (was 34%).
  - **Out** (flat numbers with no decision in them; their definitions stay so saves load): the Vanguard's
    Iron Will, Last Stand and Spiked Plate; the Herald's Haggler and Silver Voice (map-only) and Heckler.
  - **Vanguard in**: **Shield Throw** (any row: the die plus half your Armor, then lose that half:
    spend defence for reach), **Rallying Shout** (two dice, cooldown 3: the party is cleansed and gains
    half the sum as Armor; good against the bosses' Hex and Burn), **Interpose** (Guard every round, but
    no Armor from it: an `override`). In this batch they read −17, −12 and −6 vs passed: within noise.
  - **Herald in**: **Mocking Jest** (any row: the die +1 and Mark: a set-up for everyone's hits; +20),
    **Rousing Chorus** (instant, cooldown 3: every ally's next die rolls higher by half the die, at least
    2; `_inst_chorus`; −28, from about 27 runs: noise or weak, watch it), **Bolster** (Inspire, Lend a
    Hand and Rousing Chorus also give 3 Armor; `bolster` mod; +12). **Crescendo** now takes one die
    (cooldown 3; was two dice, −18): +5.
  - Bots: the instant values count Bolster's Armor and the Chorus; Cleanse counts a Hex (+3).
- **Flat picks replaced, then a pick study** (owner's request, Nov 2026: find the skills that move the
  win rate most, rebalance outliers, and replace dull ones with ones like Slice & Dice's and Dicey
  Dungeons', where the dice values matter). After all of it, with enemy Armor lasting to their next turn
  (300 Hard runs, seed 5000): **Hard 44%** (was 48%), runs of 61 turns, level 6.2; losses by objectives
  cleared 0: 43, 1: 37, 2: 41, 3: 48. Scoundrel 59%, Mender 51%, Vanguard 50%, Duelist 43%, Ranger 42%,
  Alchemist 40%, Warden 39%, Herald 38%, Arcanist 38%, Berserker 35% (±5 noise per class; the same
  batch before the enemy-Armor change gave 45%, Berserker 43%, Duelist 39%). Below the ~50% target, with
  the Scoundrel ahead: the owner's call.
  - **Out of the pools** (flat numbers, durations, immunities or map-only; definitions kept so saves
    load), each replaced in its class's pool with tags carried over: Arcane Shield → **Backlash Ward**
    (a missed spell gives Armor equal to its dice, `miss_armor`), Overcharge → **Spellweave** (+3 on a
    spell after a different spell this round), Malediction → **Wither** (spells +1 per kind of debuff
    on the target), Calm → **Clean Bill** (an ally healed to full gets +2 on their next die, carried
    into next round if their dice are spent), Miracle → **Shared Burden** (cap: once per fight the
    Mender takes half of a knock-down blow and the ally none, `burden`), Footwork → **Engage** (+4 against
    enemies at full health), Thick Skull → **Heedless** (a skull face counts as the top face and still
    hurts, `skull_top`, in `face_rules`, `ROLL_MODS` and `rules.js`), Undying Fury → **Rampage** (an
    action that kills is ready again next round), Field Dressing → **Quarry** (+2 per round in a row
    you've hit that enemy, up to +6), Long Mark → **Pass the Mark** (a Marked enemy's Mark jumps to
    another enemy when it dies), Sticky Fingers → **Dirty Trick** (a kill snatches the biggest die from
    another enemy's coming attack), Virulence → **Fester** (every hit on a Poisoned enemy adds 1
    Poison), Backstab (which repeated Stab's own bonus) → **Unseen** (+2 while no enemy aims at you),
    Battle Hymn → **Call and Response** (after the Herald acts, each ally's next damaging action that
    round deals +3, `cue`; not "matching numbers", which Pincer already rewards), Volatile → **Short
    Fuse** (a bomb showing 1 or 2 deals as if it were an 8, in `hit_base`), Deep Pockets → **Reagents**
    (bombs +1 per bomb already thrown this fight, up to +5), Verdant → **Bloom** (a summon's death heals
    the party half its max HP), and after the study, Distiller → **Catalyst** (bombs also Poison 1).
    The damage ones live in `dmg_bonus` (so the bots see them); the bookkeeping (spells cast, bombs
    thrown, the Quarry streak, cues) is `Combat.after_action`, called by actions and instants.
  - **The study** (400 Hard runs per class with `--with`, 4,000 in all, seed 20000, on the new pool):
    vs passed has a bias by kind of pick (actions −3.7 points on average, passives +0.3, capstones
    +1.1: a run counts once per offer, and actions are taken early), so judge picks against their kind.
    Even so, the z spread was 2.15. **Stuns were the outliers**: Lunge (+28 after the bias), Earthshaker
    (+21), Concussion (+19), Cacophony (+18), Shield Bash (+15), plus Shrapnel (+14) and Grand Curse
    (+16, left alone: the Arcanist is the weakest class). The low ones were mostly actions that barely
    beat the class's free basic: Twin Cut (−13; two Riposte Cuts did as much), Drink Deep (−12), Second
    Opinion (−11), Distiller (−11), Envenom (−11), Ward (−10), Called Shot (−9; two Shoots on a Marked
    enemy out-damaged it), Briar Wall (−9), Hymn of Valor (−8). Classes in that batch: Vanguard and
    Scoundrel 55%, Berserker, Mender, Duelist 49%, Alchemist 48%, Ranger 47%, Herald and Warden 41%,
    Arcanist 40%. Of the 17 new picks, 14 were within noise; Bloom (+10), Reagents (+9) and Call and
    Response (+7) a little high, Backlash Ward (−7) a little low.
  - **Tuned**: Lunge no longer Stuns; Earthshaker drops one enemy's coming attack by half the sum
    instead of Stunning; Concussion and Shield Bash Stun on a 6 (Shield Bash also on a shield face);
    Shrapnel +2 (was 3); Twin Cut each die +4 (was +2); Drink Deep the die +4 (was +2); Second Opinion
    best of three rolls (was two); Envenom Poisons half the die +1 and deals half the die; Ward twice the
    die (was 1½×); Called Shot sum +8; Briar Wall half the sum (was a third); Hymn of Valor +2, +3 on a
    match (was +1, +2). The bots' values for Hymn and Second Opinion follow.
- **Strike and Overguard split, Mender and Duelist buffed** (owner's request, Nov 2026; 300 Hard runs,
  seed 5000): **Hard 47%**. Vanguard 60%, Scoundrel 51%, Duelist 50% (was 29%), Mender 49% (was 28%),
  Berserker 49%, Ranger 48%, Arcanist 48%, Alchemist 47%, Warden 39%, Herald 34% (Battle Hymn's trim).
  Losses by objectives cleared 0: 42, 1: 26, 2: 41, 3: 49.
  - **The Vanguard's Armor tricks are level-ups now**: Strike is the die +2 for everyone; **Shield
    Weight** (Juggernaut) adds a third of Armor to it (an `override`); Overguard is only 5 starting
    Armor; **Iron Stance** (Bulwark) carries a third of Armor into the next round (the `overguard` mod).
  - **The bots valued healing low**: a point healed was worth 0.6–1.0, a point of Armor that stops a hit
    1.0, though HP lost stays lost after the fight. Now 1.0–2.0 (`heal_value`), and Overflow's Armor
    from overhealing counts. Mend went from 5.7% of the Mender's actions to 9.7%.
  - **Mender**, after the proactive "barrier healer" idea (healers who prevent damage as well as
    restore it, and whose overhealing isn't wasted): Mend heals the die +3 (was the die), Overflow
    (healing past full becomes Armor) is a starting passive, 21 HP +4 a level (was 17 +3).
  - **Duelist**, after the counter-attacker (Darkest Dungeon's riposte Highwayman): Riposte Cut deals 3
    more to an enemy aiming at the Duelist (`aimed`), Parry ripostes for 4 (was 2), 27 HP +4 (was 24 +3).
- **After objective scaling, the Vanguard nerf and the pick pass** (Nov 2026; 300 Hard runs, seed
  5000): **Hard 42%** (target about 50%), runs of 61 turns, level 6.0. Losses by objectives cleared
  0: 50, 1: 48, 2: 36, 3: 41, spread evenly as the scaling meant. Vanguard 59%, Alchemist 52%, Scoundrel
  50%, Herald 47%, Ranger 44%, Berserker 41%, Arcanist 36%, Warden 33%, Duelist 29%, Mender 28%.
  - **The Vanguard** (was 80%, then 73%): its Armor fed Strike (die +2 + half Armor) and carried over
    by half, so the tank out-damaged every class; now Strike is die +1 + a third of Armor and Overguard
    carries a third. Its defending stays, with smaller numbers: Guard and Taunt the die +2 Armor (was
    +4), Brace the die +1 (was +2; still 2 to the weakest ally), Hold the Line −1 on party hits and the
    die +2 (was −2, +3), Overguard 5 starting Armor (was 8), Shield Bash cooldown 3, 46 HP +5 a level
    (was 54 +7). The first round (Strike, Guard, Taunt, Overguard, HP) took it only to 73%: its party's
    deaths (0.28 a run against about 0.6) were the edge, so the second round trimmed the protection.
  - **The pick pass**: picks that came out as outliers in two independent samples (300 runs on seed
    5000 and 600 on seed 9000; a single 300-run sample's z spread was 1.16, near noise): weak ones made
    worth a die, strong ones trimmed. Chain Lightning (z −2.9) no longer needs an odd number; Reckless
    Swing (−2.6) hits on 7+, a miss deals half the die, 2 self-damage; Finisher (−2.6) sum +6; Taunting
    Verse (−3.2) 3+ and Marks, a miss −3; Lend a Hand (−2.5) the die rolls 4 higher; Quicksilver (−3.2)
    next die +3, cooldown 2; Splitting Flask (−2.8) halves one size bigger. Concussion (+3.0) cooldown 3;
    Battle Hymn (+2.8) only while the Herald is above half HP. The bots' values for Lend a Hand and
    Quicksilver (`instant_value`) had ignored the die bonus; they count it now. All of this is in the 42% above.
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
| `app/saltbound/crits.py` | The crit each action does when a die lands on its top face (`CRITS`), written onto the actions on import, and `is_crit`. |
| `app/saltbound/actions.py` | `Actions`: targets, amount variables (`env` = `dice_env` + `target_env`), one handler per op (`_op_dmg`, `_op_status`...) and per instant (`_inst_flip`...), and the **shared hit sums** (`hit_base`, `hit_finish`, `hit_pierces`, `foe_damage_after`, `foe_soak`, `hit_spill`, `status_amount`) that the fight and the bots both use. |
| `app/saltbound/combos.py` | `Combos`: Pincer, Covered, Shatter, the Bell, Wildfire, Spiteful elites. |
| `app/saltbound/bosses.py` | `Bosses`: the Crown's phases and Undertow, the Bell-Warden, the Lamp Keeper, the Iron Bosun's crew, Harpies' flight, splitting, the Maw's swallow. |
| `app/saltbound/tuning.py` | The fight numbers (fight-kind scaling, combos, boss numbers, status lists). |
| `app/saltbound/mods.py` | Every passive mod name and what it does; `check_content`. |
| `app/saltbound/foes.py` | `Foes`: enemies' dice and moves (`foe_moves`, `foe_setup`, `foe_bloodied`), intents (`choose_intent`, `intent_numbers`), targeting, `retarget_intents`, acting (`foe_act`, `foe_do`). |
| `app/saltbound/classes.py` | The generic classes, their actions and passives, `SHORT` card text, `COMBOS`, levels and XP. |
| `app/saltbound/content/items.py` | Items (generic), item passives and the actions weapons give. |
| `app/saltbound/content/archipelago.py` | This map's enemies, pools, elites, dungeons and paths, the final boss, blessings and events. |
| `app/saltbound/world.py` | Hex geometry (`step_dir` for a hex direction), terrain costs (`COST`, `FAST`), generating a run's map from its seed, and its extras (`add_features`: currents, reefs, whirlpools, places at sea, lookouts, grottos). |
| `app/saltbound/biome.py` | `Biomes`, mixed into `Game`: the other regions' map rules (lava and eruptions, quicksand, trails, ice, sight, Frostbite, timeless Stillwood, dreams, oases, fossils, geodes, light-gates). |
| `app/saltbound/quests.py` | `Quests`, mixed into `Game`: placing the quest-givers, offering a quest's steps, moving a trail on (`quest_move`), choosing its sites. |
| `app/saltbound/content/quests.py` | The quests (`QUESTS`, `QUEST_OF`), their events, the boons (`BOONS`), and two more events per region, merged into `archipelago.py`. |
| `app/saltbound/content/gear2.py` | The regional gear (52 pieces), the relics, the Fate Feather and the forge materials, and their weapon actions, merged into `items.py`. |
| `app/saltbound/content/biomes.py` | The eight other regions' enemies, crits, groups, lairs, dungeons, big threats, names, land names (`SKINS`), rules (`RULES`), blessings and events, merged into `archipelago.py`. |
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
| `js/itemart.js` | Item icons: a 12×12 base shape per kind of thing (axe, robe, shell...) painted in a material with an accent and a glow, then outlined. `ICON` maps each item to its look; a new item needs a line there (or it gets its slot's default). |
| `js/skillfx.js` | What every action and enemy move looks like (`SKILL_FX`, `foeFx`), from the effects kit `combat.js` passes in (`fxKit`); the styles are the stylesheet's "skill effects" section. |
| `js/stage.js` | The fights' painted backdrops (`stageKey` picks one for a fight, `stageURL` paints it once). |
| `js/hexmap.js` | `MapView` (Phaser): painted terrain (with two surf frames), currents and whirlpools, places, units, fog, reach, routes; above the fog the squalls, raid roads, landmarks and region names; the minimap. |
| `js/rules.js` | Route planning (step costs and sight come from the server: `static.map`, each hero's `sight`, the world's `cur`/`reef`/`pool` via `seaMap`), and how to describe requirements, dice and statuses. |
| `js/art.js` | `flat32()`, sprite canvases, place icons. `js/sprites.js` is generated: never edit it. |
| `js/ui.js` | `h()`, icons, tooltips, toasts, modals. `js/audio.js`: synthesized sound and music. |

## Testing

- `tools/check-all.sh` runs every fast check in the repo (about a minute); run it before pushing.
- **On Windows**, run the Python tools with `PYTHONUTF8=1` (the default code page can't read
  `rules.js`), use `python` rather than `python3`, and cap a long batch's workers (`--jobs=12`):
  the dev PC once powered off under a sustained all-core simulator batch.
- `python3 tools/saltbound-check.py` forces every action and passive of every class through real
  fights (bots never use most instant tricks), checks the passive mods against `mods.py`, that
  `js/rules.js`'s map size and `PATH_MAX` match the server's, and runs the browser's `stepCost` in Node
  (`tools/saltbound-steps.mjs`) against `Game.step_cost` for every step by the sea, at both tides,
  afloat or not, with and without a skiff. Run it after touching the rules, classes or step costs.
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
- The `--report`'s **Loot picks** table is the fair way to judge gear: each item's taken runs against
  runs offered it at the same moment that took something else (`vs passed`), as for level-ups. "Gear
  worn at the end" flatters rarer items, since runs that die early never upgrade.
- `node tools/saltbound-fxsheet.js <out dir> [skills|foes]` plays every action's effect and a sample of
  enemy moves on a live fight (through `window.saltboundFx`, on `?bots` pages) and saves three frames
  of each, for checking the looks by eye.
- `node tools/saltbound-mp.js [url] [out dir]` plays a **two-player fight** in two browsers (after
  `python3 tools/saltbound-audit.py fight`): Alice resumes the save, Bob joins by code, each plays a
  hero while the other watches, both ready up, and screenshots of both screens go to the out dir.
  It watches both pages the whole time and fails if a dialog or a level/objective banner appears
  over a fight still playing out, or on a page error. About a minute.
- **A refactor that shouldn't change play**: record full-run fingerprints first (play fixed seeds with
  `play()` from the simulator and hash `g.s`), refactor, and compare. Any bot or rules change shows.
- `node tools/saltbound-audit.js [url] [dir] [WxH] [scenario...]` reviews particular moments:
  `tools/saltbound-audit.py` plays bots to one (`start`, `loot`, `level`, `event`, `fight`, `fork`,
  `boss`, `won`, `lost`, and for the map `tide` (just after a rise that landed enemies), `raid` (a raid on
  the road and a squall), `occupied`, `seafight`, `ground` (round 1 of a fight with a battleground), `opp`, `trade` (standing in a smithy, temple or cartographer
  town), `garrison` (a boss fork with a garrison), `partyevent` (everyone on one hex, hero 1 at a party-check event, for two players), `smithy` (in a smithy with 160 gold, the weapon honed once, Powder Salt and Seer's Glass in the bag), `board` (in a town with two jobs up), `job` (a bounty or salvage job under way), `results` (a hero with two kinds of choice waiting, e.g. a level-up and spoils)...) and saves it for the token "audit"; the browser resumes it and screenshots.
  Set `SALTBOUND_DB` the same for the server and the tool on a scratch database. `node
  tools/saltbound-shots.js [url] [dir] [WxH]` screenshots a whole bot-played run.

## Gotchas

- **A trail is a job without a deadline** (`kind: "trail"` in `s["quests"]`): code that walks the jobs
  must skip or handle it (it has no `until`, `reward` or `left`; the bots' job sort would crash on it).
  An event's fight carries its `win` and `ev` into the fight dict, so `fight_won` can play the prize.
- **Boons are buffs with `perm`**: anything that counts turns down or lists buffs with their turns
  must check it. A map boon has to be mirrored in `rules.js` (`perk`); `saltbound-check.py`'s step
  check gives the second hero all three.
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

- **A fighter's sprite is inside a `.fig`** (with its status overlay): layout rules target `.unit > .fig`,
  animations and sizes `.unit .fig > img`, and the idle bob keeps its low specificity with
  `:where(.fig)` so hit, lunge and kill animations still replace it. A new sprite rule follows the same
  pattern, and anything looking for a fighter's sprite finds it with `[data-uid] img`.
- **An item key can be worked gear** (`coral_blade@3`): look items up with `Game.item(key)` (the
  bots with `g.item`) and prices with `Game.price`, never `I.ITEMS[key]` or `I.price`, and compare a
  key against the catalogue (`k != key` in a pool of catalogue items, tallies by item) through
  `I.base(key)`. `I.ITEMS` is still right for catalogue-wide lists (`I.GEAR`, rarity pools).
- **Regions are per world**: never loop over `A.DUNGEONS` or a fixed list for a run's objectives;
  use `Game.regions()` (`Wd.regions(w)`), and `region_here(t)` for "is this hex in a drawn region".
  `A.DUNGEONS`, `GROUPS` and the rest hold all eleven. The world's fixed extras (`add_biomes`) are
  placed only for drawn regions.
- **A step cost lives in two places**: the other regions' land (`Biomes.land_cost`: deep jungle and
  trails, quicksand, ice; lava blocks) has its copy in `rules.js` `stepCost`, and `saltbound-check.py`
  compares them on seeds that between them draw every region, with lava and trails laid down.
- **A save keeps five runs per browser** (`save.KEEP`): an audit that makes more saves than that before
  using them loses the oldest.
- **Hidden places stay hidden everywhere**: a grotto is in `world["places"]` from the start, but the
  view leaves out any place with `hidden` and no `found`, and the forecast doesn't say a hero lands
  on one. Anything new that lists or names places must skip them too, or it gives them away (the
  bots skip them as well). Groups and spawns still keep off their hexes, which can't be seen.
- **A current step costs 0**, so a route's length isn't bounded by its cost: `do_path` takes at most
  `PATH_MAX` hexes, and `reach` in `rules.js` stops at the same number of hops. Change both together
  (the check compares them).
- **Sea beasts and land groups never meet a hero of the other kind**: `group_step` hunts only heroes
  whose `afloat` matches the group's `sea`, and a catch counts only then (`move_groups`, the
  forecast). A raid steps along its road whatever is in it.
- **The world message carries the sea** (`cur`, `reef`, `pool`) and the `landmarks`; the client
  reads the sea's extras through `seaMap(world)`, cached per world object.
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
- **Menu screens redraw in place** (`showScreen` in `screens.js`): the lobby rebuilds on every room
  update, and `.screen` fades in, so a fresh `.screen` each time made every class pick flash the
  page. Redrawing the screen already up keeps its element (and its panels' scroll); only moving to
  another screen (title, lobby, end) builds a new one and fades.
- **The fighters' idle bob uses the `translate` property, at low specificity** (`:where()` in `ui.css`): a
  hit, lunge or kill animation (`.unit.hit img`...) uses `transform` and must replace it, so a more
  specific idle rule would swallow every hit. Its stagger is a variable (`--idle-at`) for the same reason.
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
