# Board Brawl (the game at /games/board-brawl)

Read this before changing anything in `app/brawl/`, `app/static/games/brawl/`, or the
`tools/brawl-*` scripts.

## What it is

A Mario Party / Pummel Party-style board game for the owner and friends, 2-4 players, each on
their own phone or computer, usually while on a voice call (so there's no chat). Someone makes a
room and shares its four-letter code or link; the others join. The host can add bots and picks
the number of rounds (3-20, default 10). The first board is Haunted Hollow, a Halloween graveyard.

A round: everyone takes a turn (use one item, roll 1-10, walk, maybe buy the crown for 20 coins,
land on something); then the ghost drifts toward the leader; then everyone plays a minigame. After
the last round, three bonus crowns (most minigame wins, most coins held at once, most coins taken
from rivals) are handed out if the host left them on. Most crowns wins; coins break ties.

**The crown and the shops ask as you go by** (the owner asked for both). Passing the crown, or
landing on it, always stops you to ask if you'll buy it; if you can't afford it, the question
shows the price and your coins with Buy greyed out, and walks you on after 6 s (`WAIT["broke"]`).
Passing or landing on one of the three shops (each drawn with a stall beside it) opens it: buy as
many items as your coins and pockets allow, then keep walking (`Room.open_shop`, `shop_passing`).
A human who lets the timer run out leaves the shop without buying. Bots shopping on the way past
keep 14 coins back so they can still afford crowns.

**Forks show where each way leads** (the owner asked for this). At a fork the state carries
`routes`: for each way, every route the rest of the roll could take (`Room.routes`; a later fork
splits it, a web stops it short). The board draws each way as a dotted trail in its own colour
(`ROUTE_COLORS` in `board.js`) with a pin on every space it could end on, and each button says
what you'd land on and whether you'd pass the crown, a shop or the ghost. Pointing at a button or
a pin lights up just that way.

## The owner's design answers

The design came from a list of questions the owner answered. Keep to them:

- **Be mean.** Lots of ways to screw over other players: items, traps, webs, duels, bombs. No
  stealing crowns, though.
- **Catch-up for whoever's behind**: the ghost hunts the leader (end of each round it moves up to
  6 spaces toward them, and takes 10 coins if it reaches them; anyone walking through it loses 5);
  shops are half price for the bottom half; item gifts and ? events are weighted toward good
  things for players behind and bad things for the leader (`Room.gift`, `Room.event`); the last
  three rounds (the last one in a 3-round game) are the **Witching Hour**: blue and red spaces
  count double, and last place gets 10 coins and an item when it starts.
- **Halloween theme for the first map.** More maps may come; keep board data in `board.py`.
- **Every kind of space**: blue (+3), red (−3), ? events, chests (a free item), shops, duels,
  a pair of portals, player traps and webs, coin piles, and the moving ghost.
- **Lots of items, many weird** (`ITEMS` in `game.py`): double dice, coin trap, spider web,
  magic mirror (passive: bounces the next targeted item), curse doll (next roll 1-3), hex broom
  (walk the next roll backwards), pickpocket, zombie hand (drag someone to you), warp swap,
  pumpkin bomb (everyone within 3 spaces drops 8 coins in a pile anyone can pick up), chaos
  cauldron (shuffle everyone). One item per turn, three carried at most.
- **Every minigame format**: free-for-all, 2 v 2, 1 v the rest, and duels (from duel spaces:
  the winner takes up to 10 coins from the loser).
- **A big variety of minigame kinds**: action, reflex, mashing, timing, memory, counting, puzzle,
  trivia, draw-and-guess. Add more rather than polishing a few.
- **No chat**: they're on a call.
- **Only the board is Halloween.** Minigames don't have to be spooky; newer ones keep a plain
  look close to the games they're based on. (The first 26 kept their spooky names.)
- **Keyboard and mouse first.** The owner said there's no need to optimise for phones. Don't break
  what works on a phone, but don't spend effort there.

## Minigames

| Key | Name | Kind | Formats | Runs |
|---|---|---|---|---|
| `pump` | Boo-lloon Pump | alternating ← → | ffa, duel, team | server counts pumps |
| `draw` | Quick Draw | reflex | ffa, duel, team | browser |
| `needle` | Stop the Needle | timing | ffa, duel, team | browser |
| `memory` | Copycat Spell | memory | ffa, duel, team | browser |
| `count` | Count the Creeps | counting, three rounds | ffa, duel, team | browser |
| `whack` | Whack-a-Bat | reflex | ffa, duel, team | browser |
| `math` | Potion Math | sums race (Trivia's rules) | ffa, duel, team | server |
| `odd` | Odd Ghost Out | puzzle | ffa, duel, team | browser |
| `trivia` | Trivia Night | trivia | ffa, duel, team | server |
| `sketch` | Sketchy Spirits | draw and guess | ffa (3+ players, 2+ humans) | server |
| `tug` | Tug of Doom | mashing | team | server |
| `bumper` | Bumper Ring | action | ffa, duel, team | server, 20 Hz |
| `candy` | Candy Grab | action | ffa, duel, team | server, 20 Hz |
| `tag` | Ghost Tag | freeze tag | 1vn | server, 20 Hz |
| `drop` | Pumpkin Drop | action | 1vn | server, 20 Hz |

The owner asked for more, based on Mario Party fan favourites, and allowed 3D. These are in
`arcade.py` and `games-more.js`; each class's docstring names the game it's based on:

| Key | Name | Based on | Kind | Formats | Runs |
|---|---|---|---|---|---|
| `hexheat` | Hex Heat | Hexagon Heat | action, **3D** | ffa, duel, team | server, 20 Hz |
| `squirm` | Spellbook Squirm | Booksquirm | action, **3D** | ffa, duel, team | server, 20 Hz |
| `says` | Skeleton Says | Shy Guy Says | listening | ffa, duel, team | server |
| `lift` | Pumpkin Lift | Face Lift | precision | ffa, duel, team | browser |
| `hide` | Hide and Go Boo! | Hide and Go BOOM! | bluffing | 1vn | server |
| `bowl` | Skull Bowling | Bowl Over | action | 1vn | server, 20 Hz |
| `graves` | Grave Robbers | Air to a Fortune / Grab Bag | mind games | ffa, duel, team | server |
| `potato` | Hot Pumpkin | Lit Potato | hot potato | ffa (3+ players) | server, 20 Hz |
| `shoot` | Slime Shooters | Shell Shocked | shooter | ffa, duel, team | server, 20 Hz |
| `pong` | Skull Pong | Paddle Battle | four-way pong | ffa, duel | server, 20 Hz |
| `band` | Monster Mash | Mario Bandstand | rhythm | ffa, duel, team | browser |

Then a third batch, from a Reddit thread of favourites the owner pasted in, in `classics.py` and
`games-classic.js`, plain-looking:

| Key | Name | Based on | Kind | Formats | Runs |
|---|---|---|---|---|---|
| `cheese` | Say Cheese! | Slaparazzi | action | ffa, duel, team | server, 20 Hz |
| `ticktock` | Tick Tock Hop | Tick Tock Hop | timing | ffa, duel, team | server |
| `cutter` | Cookie Cutter | Crazy Cutters / Trace Race | mouse precision | ffa, duel, team | browser |
| `hotel` | Hotel Hustle | Hotel Goomba | guessing race | ffa, duel, team | browser |
| `gallery` | Shooting Gallery | Aim of the Game | mouse aim | ffa, duel, team | browser |
| `clock` | Ten Seconds Flat | the stop-the-clock game | timing | ffa, duel, team | browser |
| `beanstalk` | Beanstalk | the vine-growing game | reflex race | ffa, duel, team | browser |
| `messy` | Messy Memory | Messy Memory | memory | ffa, duel, team | browser |
| `snowball` | Snowball Summit | Snowball Summit | action | ffa, duel, team | server, 20 Hz |
| `hockey` | Speed Hockey | Speed Hockey | sport | team, duel | server, 20 Hz |

Then three more one-against-the-rest games, because 1 v 3 had the fewest games and so repeated
most, in `showdown.py` and `games-showdown.js`:

| Key | Name | Based on | Kind | Formats | Runs |
|---|---|---|---|---|---|
| `bash` | Candy Bash | Bash 'n' Cash | chase the sack | 1vn | server, 20 Hz |
| `look` | Look Away | Look Away | bluffing | 1vn | server |
| `redlight` | Red Light, Green Light | the playground game | timing | 1vn | server, 20 Hz |

Tick Tock Hop forgives a jump that reaches the server up to `GRACE` (0.15 s) after a hand
reached you, so latency doesn't get people knocked out. Speed Hockey's bot keepers aim a little
off on purpose, or bot matches end 0-0.

Balance notes: Hide and Go Boo! has 6 coffins and 3 opens against 3 hiders (4 against 2), and the
seeker wins by finding more than half, which a random seeker does about half the time; Slime
Shooters' bots fire rarely and miss often, or a match is over in seconds.

**One against the rest is tuned so the one wins 40-60% of bot games.** Check with
`python3 tools/brawl-balance.py [keys] [games]` after any change. What it took:
- Ghost Tag was a walkover for the ghost (a chaser in a walled box always corners you). It's
  freeze tag now: a frozen runner thaws when a friend touches them, or after `THAW` (3.5 s)
  anyway, and the ghost needs everyone frozen at once. Same speed as the runners; its dash
  recharges faster.
- Pumpkin Drop was a walkover for the dodgers; `FALL`, `BLAST` and `DROP_CD` are tuned to it,
  and it is touchy: a tenth of a second on `FALL` swings it by 30 points.
- Red Light, Green Light needs most of the runners home (2 of 3), not one, and the runners'
  `ACCEL` (how quickly they stop) decides it. Also touchy.
- Bot runners and dodgers must play like people or the tuning means nothing:
  `OneVsMany.escape` looks ahead in 16 directions and keeps out of corners (the old `flee`
  ran into them), and bot dodgers and runners react after 0.2-0.6 s, not at once.

Other tuning from the owner's audit: Boo-lloon Pump alternates ← and → to 60 (it was 5 s of
mashing Space); Potion Math is a race on Trivia's rules, with a bonus for the first right answer
and a cost for a wrong one (it was ten sums typed alone); Count the Creeps is three rounds; Hot
Pumpkin needs three players (as a duel it was a coin flip, over in 8 s); Hex Heat's safe tiles
thin out each round, down to one, and people who fall together are ranked by how near they were
to a safe tile (half its games ended in a draw); Skeleton Says ramps faster
and lasts at most 45 s. Someone watching a game played on the players' own screens (a duel
they're not in) gets a big scoreboard rather than a small list.

The format is picked each round (`Room.start_minigame`): with 2 players always free-for-all; with
3, free-for-all or 1 v 2; with 4, free-for-all, 2 v 2 or 1 v 3. Games come from a shuffled bag per
format so they don't repeat until the bag's empty. Prizes: free-for-all 10/6/3/1; 2 v 2 8 each to
the winners (3 each on a draw); 1 v the rest 15 to the one, or 6 each to the rest. **A duel always has a loser** (the owner asked):
a dead heat goes to a coin toss, and the results say so.

**Adding a minigame** takes a server class in `minigames.py`, `arcade.py`, `classics.py` or `showdown.py` (in
`GAMES`, with `modes`, `dur`, `key_of` and `label`, plus bots) and a browser class in
`games-solo.js`, `games-live.js`, `games-more.js`, `games-classic.js` or `games-showdown.js` (in `SOLO`,
`LIVE`, `MORE`, `CLASSIC` or `SHOWDOWN`, extending `Game` from `base.js`,
or `Arena` for the arena games). `Survival` in `arcade.py` gives last-one-standing games their
ranking and end. Arena games on a light floor set `nameColor` and `meColor` so names stay
readable. Solo games get their content in `params` and
report `prog` and `done`; their bots are scripted (`Scripted.plans`). Team games are ranked by
`team_key`, by default their best player's key; override it when the team total matters. Run
`python3 tools/brawl-check.py` afterwards.

## Code map

| File | Holds |
|---|---|
| `app/brawl/board.py` | Haunted Hollow: the spaces (built from strings of kinds along a loop and two cross paths), forks, portals, and distance helpers. |
| `app/brawl/game.py` | `Room`: joining by code, rejoining, the lobby, turns, items, spaces, the ghost, catch-up, minigame formats and prizes, duels, the end; `ROOMS`. |
| `app/brawl/minigames.py` | The minigames' server halves, and their bots; `GAMES`, the full list. |
| `app/brawl/arcade.py` | More minigames, after Mario Party favourites; `Survival`, for last-one-standing games. |
| `app/brawl/classics.py` | Minigames from the owner's friends' favourites thread. |
| `app/brawl/showdown.py` | More one-against-the-rest minigames. |
| `app/brawl/content.py` | Trivia questions, draw-and-guess words, potion sums. |
| `app/brawl/routes.py` | `GET /games/board-brawl` and the WebSocket at `/games/board-brawl/ws`. |
| `app/static/games/brawl/index.html`, `game.css` | The page: menu, lobby, board screen, overlays. |
| `js/main.js` | The connection, rendering the room state, the turn controls, the overlays. |
| `js/board.js` | Draws the board, scenery, pieces, dice and effects on a canvas. |
| `js/mg.js` | The minigame stage: sizing, countdown, timer, input routing. |
| `js/base.js` | `Game`, the base class for minigames' browser halves, with drawing helpers. |
| `js/games-solo.js`, `js/games-live.js`, `js/games-more.js`, `js/games-classic.js`, `js/games-showdown.js` | The minigames' browser halves. |
| `js/view3d.js` | The three.js view the 3D minigames draw into. |
| `js/art.js` | Ghosts, pumpkins, bats, spiders, skulls, crowns, candy, tokens, graves, trees, webs: canvas paths. |
| `js/audio.js` | Synthesized sound effects. |

## How it works

- **The server owns the game.** The browser sends intentions (`roll`, `item`, `path`, `buy`,
  `shop`, `duel`, `ready`, and minigame input) and draws the room state the server sends whenever
  it changes (`state`), with `fx` listing one-off effects to animate. Arena minigames also get `mg`
  snapshots 20 times a second (10 for others). Draw-and-guess sends the secret word only to the
  artist (`Minigame.private`).
- **One alarm at a time.** The game only ever waits for one thing (a roll, a choice, a step, the
  dice on screen), so `Room.at(delay, fn)` keeps a single pending alarm. `wait_for` gives humans
  25-40 s before acting for them, and bots about a second.
- **Nobody holds the game up.** A disconnected player is played by the bot code until they come
  back (same browser token: `localStorage` `brawl`, and a per-tab id, as in Frag Arena). Their
  place, coins and items are kept; the room lingers 30 minutes after the last person leaves.
- **Solo minigames trust the browser**, like Frag Arena's movement. Fine for friends.
- **Rooms live in the web process's memory**, like Frag Arena: one uvicorn worker, and a deploy
  ends every game in progress.

## Gotchas

- **A tab left open across a deploy is told to reload.** The browser sends its `?v=` in its hello;
  `routes.py` reads the page's and, if they differ, answers `reload` (or, for a tab from before
  this check, an error saying to reload). Old game code against a new server breaks minigames in
  odd ways (a one-round Count the Creeps waiting on a three-round server looked stuck).
- **Hex Heat's `tile_at` must allow up to `SIZE`** from the nearest centre: that's where a tile's
  corners are, and a smaller cutoff turned the points where three tiles meet into holes, so
  people fell while crossing the board.
- **Every module URL carries `?v=N`, and they must all match** (Cloudflare caches `/static`, and a
  module loaded under two URLs runs twice). When changing any of the game's JS or CSS, bump them
  together: `grep -rn "?v=" app/static/games/brawl`.
- `base.js` exists so the game modules and `mg.js` don't import each other (a circular import
  would hit `Game` before it's defined).
- The minigame canvas is 420-800 logical units wide (the screen's width in CSS pixels, within
  those bounds) and as tall as suits the screen, so games must lay out from `this.W` and `this.H`
  (`area()` and `side()` in `base.js` help) and work in portrait on a phone.
- **3D minigames** set `transparent` so the stage clears its 2D canvas instead of painting it, and
  draw into a WebGL canvas underneath (`View3D`). three.js 0.170.0 comes from cdnjs through the
  page's import map, and is only fetched when a 3D game starts. `View3D.toStage` turns a world
  point into stage units, for names and labels. Dispose of the view in `end()`.
- The smoke test runs Chromium without `--use-angle=swiftshader`: that flag routes 2D canvases
  through software GL too, which makes the board crawl and screenshots time out.
- Two tabs of one browser are two players (for testing), but a reload is the same player.
- `python3 tools/brawl-balance.py` says how often the one wins each 1 v 3 minigame.
- `python3 tools/brawl-check.py` plays every minigame in every format with bots, then whole games,
  on a fake clock. `node tools/brawl-smoke.js [url] [rounds] [shots dir]` plays a real game in two
  headless browsers (one phone-sized) against a running server, with real clicks and key presses.
- `?debug` on the page URL exposes `window.brawl` for the smoke test.
