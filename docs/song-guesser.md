# Song Guesser (the game at /games/song-guesser)

Read this before changing anything in `app/static/games/song-guesser/` or
`tools/song-guesser-check.js`.

## What it is

A name-that-tune game. Each round picks a song and plays ten seconds of one section, rebuilt with
the browser's synthesizer. Stage 1 is a single instrument (usually the drums). Every wrong guess or
skip adds the next instrument and replays the clip, until the whole arrangement is playing; a wrong
guess then loses. The genre and release year show from the start. Guesses come from a search box
over every arranged song plus a few hundred more titles, so the list doesn't give the answer away.
Stats and the last 15 songs (not repeated) are kept in `localStorage` under `song-guesser`.

## Code map (`app/static/games/song-guesser/`)

Static files, no build step. `/games/song-guesser` serves `index.html`, which loads `js/main.js`
as an ES module.

| File | Holds |
|---|---|
| `js/songs.js` | `SONGS`, every arrangement as text (the format is documented at the top), and `EXTRA`, the titles that only pad out the guess list. Add songs here. |
| `js/synth.js` | `arrange()` turns a song into timed notes per part (drums, bass, chords, riff, melody); `renderPart()` renders one part with `OfflineAudioContext`; `mix()` sums parts into one stereo buffer. Also the grooves, chord rhythms and instrument recipes. |
| `js/main.js` | The round: picking a song, rendering and playing stages, the search box, guesses, stats. |
| `game.css` | Page styling on top of the site's `style.css`. |

## Design directives (agreed with the owner)

- **Synthesized, not recorded.** The owner chose hand-written arrangements over real audio split
  into stems: no copyrighted recordings, no new service, and the abstraction makes it harder, which
  is the point. Don't add audio files or a server side.
- **Biased toward indie rock.** `tier: 'indie'` songs are picked 4× as often as `'other'`, `'alt'`
  2×. The owner named Weezer, Neutral Milk Hotel and Interpol; keep them well represented.
- **Hardest instrument first.** The default order is drums, bass, chords, riff, melody. When a
  song's identity lives in one part (the Seven Nation Army or Billie Jean bass, the Clocks piano),
  set `order` so that part comes last.
- Rough is fine; wrong isn't. Arrangements are written from memory, checked against chord charts
  where possible (keys and progressions came from Hooktheory's TheoryTab pages). Melodies are
  approximations.

## Adding a song

1. Add it to `SONGS` in `js/songs.js`. Write one section, 2–8 bars, that loops to fill ten seconds.
   Every part loops on its own length, so keep each a whole number of bars and a multiple or
   divisor of the chord loop.
2. If it was in `EXTRA`, take it out there (the check flags duplicates).
3. Run `node tools/song-guesser-check.js`. It arranges every song, checks bar lengths and the guess
   list, and lists notes outside the key the chords imply (often typos).
4. Bump `?v=` (see below).

## Gotchas

- **Every URL carries `?v=N`, and they must all match.** Cloudflare caches `/static`. When changing
  any file, bump `?v=` together on the `game.css` link and the `main.js` script tag in
  `index.html`, and the two imports at the top of `main.js`. `grep -rn "?v=" app/static/games/song-guesser`
  finds them.
- **Rendering is the slow part.** A part takes a few hundred milliseconds to render, so `main.js`
  renders every stage in the background as soon as a round starts. Offline rendering keeps every
  node alive until the end, so `synth.js` reuses a small pool of filter/envelope chains per part
  (`pool()`) and creates only oscillators per note; per-note chains made it several times slower.
  Parts render in mono and are panned in `mix()` for the same reason.
- `mix()` normalizes each part by its loudness before applying its `FX.mix` level, so an instrument's
  `osc` levels set its tone, not how loud it is in the mix.
- Audio rules from the tactics game apply: audio starts only after a tap; iPhones need
  `navigator.audioSession.type = 'playback'` to play with the silent switch on; render at 44.1 kHz;
  and a context stuck after the page was in the background is replaced on the next Play.
- The headless check can't hear anything. After changing `synth.js` or an arrangement, listen in a
  browser.
