# Books: EPUB library, reader, importer and narration

Read this before changing `app/books/` or `app/static/books/`.

## What it does

`/books` is a private EPUB library and reader with optional audiobook narration.

- **Accounts:** no password. A reader picks a username (cookie `books_user`, path `/books`) and sees
  only books whose `book.json` `owner` matches. Anyone else's book is a 404, never a 403.
- **On disk:** `store.py`'s docstring is the authoritative map of `data/books/`. Each book is a
  12-hex-character id folder with `book.json`, the original `book.epub`, the chapter HTML/JSON,
  `progress.json`, the `audio/` folder, and a `narrate` flag file.
- **`epub.py`** parses uploads into reader markup. The chapter HTML is rebuilt from a whitelist of
  tags, so nothing from the EPUB's own HTML (scripts, styles, attributes) reaches the page. Only
  size and float are carried over from its CSS. Every spoken block gets `data-s="<segment>"`, with
  the matching text in `chapters/<n>.json`.
- **`importer.py`** builds an EPUB from a Royal Road fiction or a SpaceBattles, SV or QQ thread
  (threadmarks via reader mode), then saves it like an upload. One import runs at a time, on a
  background thread, with requests a second apart. Jobs live in memory, so a restart drops
  unfinished ones.
- **The bookmarklet:** Royal Road and SpaceBattles block the server, so stories also come in
  through the "Import to Library" bookmarklet (`grab` in `library.js`). It opens `/books/receive`
  (`receive.js`) as a popup. The server's parsers run on pages the reader's browser fetched;
  `importer.gather` replies with the URLs it still needs, and the browser fetches those and sends
  them back, round after round.
- **Updating a book:** importing a story already in that reader's library updates the book in place
  ("Check for new chapters" in the ⋯ menu). Chapters it already has are copied from its EPUB.
  `rev` in `book.json` counts updates and versions every chapter, image and audio URL (`?v=<rev>`).
- **`worker.py`** runs in the `tts` container and narrates with Kokoro (voice `am_michael`). It only
  narrates books with a `narrate` file (made by "Make audiobook", or by pressing listen). The order
  is: the chapter someone pressed listen on (`priority.json`), the rest of that book, then other
  requested books newest first.
- **`pages.py`** renders the HTML shells (login, library, receive, reader) with `ASSET_VERSION` on
  every asset. The behavior is in `app/static/books/library.js` and `reader.js`.
- **Offline reading:** `sw.js` is a service worker served at `/books/sw.js` (not `/static`) so its
  scope covers `/books`. It's served with `pages.SHELL` and `ASSET_VERSION` filled in. It answers
  from the `book-<id>` caches that `library.js` fills when a reader saves a book from the ⋯ menu,
  and keeps the last library listing.

## Design directives

- **Test the reader against public-domain EPUBs** (e.g. Project Gutenberg), never the owner's books.
- **Fetch only what a reader asked for.** No crawling, no prefetching other stories, one second
  between requests. A Cloudflare challenge is a failure with a message telling the reader what to do
  instead; never retry past it.
- **Writes are atomic.** Use `store.write_text` / `write_json`, which write a temp file and rename
  it, or build in a hidden folder and rename (as `epub.save` does). The worker and the web app read
  the same files concurrently.
- **Private everywhere:** `PRIVATE_HEADERS` on dynamic responses, `IMMUTABLE` (a week, `private`)
  only on content that's fixed for a given id and rev.

## Gotchas

- **Bump `ASSET_VERSION`** in `pages.py` when changing any `app/static/books/` file. Cloudflare
  caches `/static`, and the service worker keys its shell cache on that version.
- **Bump `FORMAT`** in `epub.py` when changing how chapters come out of an EPUB. At startup
  `refresh_all` rebuilds older books from their stored EPUB. Narration survives if the spoken text
  is unchanged.
- **Book ids are content hashes:** `sha256(owner + "\0" + epub)[:12]`. Uploading the same file
  twice is a no-op, and two users get separate copies.
- **Narration can be played while it's still being written.** It grows in
  `audio/.<n>.mp3.tmp` with `<n>.partial.json` recording the bytes and segment start times. Only
  when `audio/<n>.json` exists is chapter n done. `routes._byte_range` serves the partial file with
  Range support because Safari won't play audio without it. MP3s are constant bitrate (48 kbps
  mono), so byte length maps to time and chapters can simply be concatenated for download. "Separate chapters (ZIP)" instead streams a
  stored (uncompressed) zip of one MP3 per chapter, `NN Title.mp3`, from `download-chapters.zip`.
- **Updates keep narration selectively.** `epub.update` keeps the audio of every section whose text
  didn't change and drops the rest. The worker notices a new `rev` and abandons narration started on
  old text.
- **Progress saved offline is replayed later** with the time it was saved (`at`). The server keeps
  whichever save is newer across devices.
- **iOS needs special handling:**
  - Audio can only start from a tap. The reader plays a blip of silence inside the tap to unlock
    the `<audio>` element.
  - The home-screen app's status bar color changes only when the meta tag is replaced, not edited.
  - Layout uses `env(safe-area-inset-*)` throughout `reader.css`.
- **Pagination uses CSS columns.** Each page is one column exactly as wide as the text area, and
  turning a page slides the strip. A relayout (an image loading, a settings change) returns to an
  anchored element rather than a page number, because the text moves.
- **Royal Road quirks:** `isUnlocked` reads false for every chapter when logged out; only
  subscription-tier chapters are really locked. Royal Road also hides decoy paragraphs with
  per-page classes set to `display: none`, and the importer strips them.
- **Site lists are in several places.** `SERVER_BLOCKED` in `importer.py` decides whether "Check for
  new chapters" runs on the server or through the bookmarklet. `BOOKMARKLET_SITES` and the `SITES`
  regex in `receive.js` must agree with it when adding a site.
- **The worker runs at `nice 10`.** It must stay importable without FastAPI or bs4, since its
  container has neither.
