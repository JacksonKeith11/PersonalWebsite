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

## Minigames

| Key | Name | Kind | Formats | Runs |
|---|---|---|---|---|
| `pump` | Boo-lloon Pump | mashing | ffa, duel, team | server counts pumps |
| `draw` | Quick Draw | reflex | ffa, duel, team | browser |
| `needle` | Stop the Needle | timing | ffa, duel, team | browser |
| `memory` | Copycat Spell | memory | ffa, duel, team | browser |
| `count` | Count the Creeps | counting | ffa, duel, team | browser |
| `whack` | Whack-a-Bat | reflex | ffa, duel, team | browser |
| `math` | Potion Math | puzzle | ffa, duel, team | browser |
| `odd` | Odd Ghost Out | puzzle | ffa, duel, team | browser |
| `trivia` | Trivia Night | trivia | ffa, duel, team | server |
| `sketch` | Sketchy Spirits | draw and guess | ffa (3+ players, 2+ humans) | server |
| `tug` | Tug of Doom | mashing | team | server |
| `bumper` | Bumper Ring | action | ffa, duel, team | server, 20 Hz |
| `candy` | Candy Grab | action | ffa, duel, team | server, 20 Hz |
| `tag` | Ghost Tag | action | 1vn | server, 20 Hz |
| `drop` | Pumpkin Drop | action | 1vn | server, 20 Hz |

The format is picked each round (`Room.start_minigame`): with 2 players always free-for-all; with
3, free-for-all or 1 v 2; with 4, free-for-all, 2 v 2 or 1 v 3. Games come from a shuffled bag per
format so they don't repeat until the bag's empty. Prizes: free-for-all 10/6/3/1; 2 v 2 8 each to
the winners (3 each on a draw); 1 v the rest 15 to the one, or 6 each to the rest.

**Adding a minigame** takes a server class in `minigames.py` (in `GAMES`, with `modes`, `dur`,
`key_of` and `label`, plus bots) and a browser class in `games-solo.js` or `games-live.js` (in
`SOLO` or `LIVE`, extending `Game` from `base.js`). Solo games get their content in `params` and
report `prog` and `done`; their bots are scripted (`Scripted.plans`). Team games are ranked by
`team_key`, by default their best player's key; override it when the team total matters. Run
`python3 tools/brawl-check.py` afterwards.

## Code map

| File | Holds |
|---|---|
| `app/brawl/board.py` | Haunted Hollow: the spaces (built from strings of kinds along a loop and two cross paths), forks, portals, and distance helpers. |
| `app/brawl/game.py` | `Room`: joining by code, rejoining, the lobby, turns, items, spaces, the ghost, catch-up, minigame formats and prizes, duels, the end; `ROOMS`. |
| `app/brawl/minigames.py` | The minigames' server halves, and their bots. |
| `app/brawl/content.py` | Trivia questions, draw-and-guess words, potion sums. |
| `app/brawl/routes.py` | `GET /games/board-brawl` and the WebSocket at `/games/board-brawl/ws`. |
| `app/static/games/brawl/index.html`, `game.css` | The page: menu, lobby, board screen, overlays. |
| `js/main.js` | The connection, rendering the room state, the turn controls, the overlays. |
| `js/board.js` | Draws the board, scenery, pieces, dice and effects on a canvas. |
| `js/mg.js` | The minigame stage: sizing, countdown, timer, input routing. |
| `js/base.js` | `Game`, the base class for minigames' browser halves, with drawing helpers. |
| `js/games-solo.js`, `js/games-live.js` | The minigames' browser halves. |
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

- **Every module URL carries `?v=N`, and they must all match** (Cloudflare caches `/static`, and a
  module loaded under two URLs runs twice). When changing any of the game's JS or CSS, bump them
  together: `grep -rn "?v=" app/static/games/brawl`.
- `base.js` exists so the game modules and `mg.js` don't import each other (a circular import
  would hit `Game` before it's defined).
- The minigame canvas is 800 logical units wide and 450-1400 tall to match the screen's shape, so
  games must lay out from `this.W` and `this.H`, and work in portrait on a phone.
- Two tabs of one browser are two players (for testing), but a reload is the same player.
- `python3 tools/brawl-check.py` plays every minigame in every format with bots, then whole games,
  on a fake clock. `node tools/brawl-smoke.js [url] [rounds] [shots dir]` plays a real game in two
  headless browsers (one phone-sized) against a running server, with real clicks and key presses.
- `?debug` on the page URL exposes `window.brawl` for the smoke test.
