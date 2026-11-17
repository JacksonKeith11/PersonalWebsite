# Sketch Relay (the game at /games/sketch-relay)

Read this before changing anything in `app/relay/`, `app/static/games/relay/`, or the
`tools/relay-*` scripts.

## What it is

A drawing-and-guessing relay for 3-8 friends, each on their own phone or computer, usually in the
same room or on a call (so there's no chat). Someone makes a room and shares its four-letter code
or link; the others join; the host starts.

Everyone writes something to draw. Every step, each player's page is passed to the next player:
handed words, they draw them; handed a drawing, they write what they think it is. A game has as
many steps as players, so every player adds one page to every chain (a "book"). Then the host reads
the books out, one page per press of Next, on everyone's screen at once. After the last book comes
the album: everyone flips through all the books on their own, can save one as a PNG, and the host
can send everyone back to the lobby to play again.

There are no points and no bots (a bot can't draw anything worth guessing).

## How it works

- `app/relay/game.py`: `Room` is one table. Phases: `lobby`, `play`, `reveal`, `album`.
  `order` is the players in passing order (shuffled at the start) and `books[b]` is the list of
  pages started by `order[b]`. In step `k`, seat `i` works on book `(i - k) mod n` (`book_of`), so
  each step the books move one seat along. Step 0 is `write`, odd steps `draw`, even steps `guess`
  (`kind`). A page is `{"k": "text", "text"}` or `{"k": "draw", "strokes"}`, plus `by` (the
  player's id) and `auto` when the server stood in for them.
- There's no tick loop: nothing happens between messages except the step's clock, one
  `loop.call_later` (`Room.at`).
- Messages to the browser: `welcome` (ids and limits), `state` (the whole small state, to everyone,
  after every change), `task` (one player's job for the step: sent when the step starts and when
  they rejoin) and `books` (all the finished books: sent when the reveal starts and to anyone who
  joins after). Drawings travel only in `task` and `books`, never in `state`.
- From the browser: `timer`, `start`, `hurry`, `next`, `again` (host only) and `submit` (with the
  step it's for; a page for another step is dropped).
- `app/static/games/relay/js/pad.js`: what a drawing is, `paint`, the replay (`show`) and `Pad`,
  the sheet a player draws on. `js/main.js`: everything else. The page is plain DOM, no canvas
  framework; the look is the site's paper card.
- `app/relay/ideas.py`: stock prompts. Three are offered on the write step, and one stands in for
  a player who writes nothing.

## Design directives

- **Phones first.** Most players will be on a phone held upright: the sheet is the full width,
  the tools sit under it and wrap, and nothing needs a keyboard shortcut or a hover.
- **Nobody can stall the game.** A step ends when everyone *connected* has handed in. With the
  timer on, the clock running out ends it (browsers send what's on the pad or in the box; the
  server waits `GRACE` seconds and fills in the rest: a stock prompt, a blank sheet, "(no idea)").
  With it off, the host gets "Move on without them" once their own page is in.
- **Someone who drops comes back to the same seat** (the token in `localStorage`, as in the other
  games). Someone who joins mid-game watches and is dealt in at the next game.
- **The reveal is shared.** The host turns the pages and everyone sees the same page; drawings are
  replayed stroke by stroke as they're turned up. Authors are named only here, not during play.
- **Drawings are strokes, not pixels**: small to send, sharp at any size, and replayable.

## Gotchas

- **The sheet is 800 x 600 units whatever its size on screen.** Strokes are
  `{c, w, p: [x, y, ...]}` in those units, with `c` and `w` indexes into `PALETTE` and `WIDTHS` in
  `pad.js`. The server checks them against `N_COLORS` and `N_WIDTHS` in `game.py`: change the
  palette or brushes in both places. The last palette entry is white, the eraser.
- **A drawing has an ink limit** (`MAX_POINTS`, 8000 points), which keeps a drawing's message under
  `max_text` in `routes.py` (150 000 characters; `serve` silently drops anything longer). The pad
  thins each stroke when the pointer lifts and shows "Ink left" under 25%. Raise both together.
- **`task` arrives before the `state` that announces its step**, so `main.js` only shows a job
  whose step matches the state's, and sets the job up (clearing the pad) once per step (`S.setUp`),
  not on every state.
- **Reloading the page mid-drawing loses the drawing so far**: the pad's strokes live only in the
  page. The job itself comes back.
- **A canvas has no size until it's on the page and visible**: `fit` sizes it from `clientWidth`,
  so paint after un-hiding (the pad also repaints from a `ResizeObserver`).
- **A game with everyone disconnected waits**: the clock running out does nothing until someone
  is back, rather than playing the game out with stock pages.
- The games live in the web process's memory: a deploy ends every game in progress.

## Checking a change

- `python3 tools/relay-check.py` (a second): games of 3-8 pretend players through to the album,
  checking who is handed what, plus bad drawings, timeouts, leaving, rejoining and watching. In
  `tools/check-all.sh`.
- `node tools/relay-smoke.js --serve` (about 15 s): three headless browsers, one phone-sized and
  drawing by touch, play a whole game. In `tools/check-all.sh`; skipped where Playwright isn't
  installed. Add `--shots <folder>` for a screenshot of every screen.
- After changing its CSS or JS: `python3 tools/bump-version.py app/static/games/relay`.
