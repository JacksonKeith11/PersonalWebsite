import json
from html import escape

ASSET_VERSION = 21
STYLE = "/static/style.css?v=9"
# What the pages load from this site, kept by the service worker (sw.js) so they open offline.
SHELL = [
    STYLE,
    *(f"/static/books/{name}?v={ASSET_VERSION}" for name in ("library.css", "library.js", "reader.css", "reader.js")),
    *(f"/static/books/fonts/charter_{style}.woff2" for style in ("regular", "italic", "bold", "bold_italic")),
    "/static/books/manifest.json",
    "/static/books/icon-180.png",
]
NAV = """<nav class="nav">
      <div class="nav-links">
        <a href="/">About</a>
        <a href="/resume">Resume</a>
        <a href="/projects">Projects</a>
        <a href="/books" aria-current="page">Library</a>
        <a href="/recipes">Recipes</a>
      </div>
    </nav>"""
FONTS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700'
    '&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet">'
)
HEAD = """<meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="robots" content="noindex, nofollow">
  <meta name="referrer" content="no-referrer">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="Library">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <link rel="manifest" href="/static/books/manifest.json">
  <link rel="apple-touch-icon" href="/static/books/icon-180.png">"""


def login(next_path: str = "/books", failed: bool = False) -> str:
    error = '<p class="notice err">Use 1–32 letters, numbers, dashes or underscores.</p>' if failed else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  {HEAD}
  <title>Library</title>
  {FONTS}
  <link rel="stylesheet" href="{STYLE}">
  <link rel="stylesheet" href="/static/books/library.css?v={ASSET_VERSION}">
</head>
<body>
  <main class="paper login">
    {NAV}
    <h1 class="page-title">Library</h1>
    <p class="intro">A private reading shelf for EPUBs. Upload a book and have it narrated as an
      audiobook when you want, so you can switch between reading and listening.</p>
    <ul class="features">
      <li>Read page by page with adjustable themes, fonts, text size and spacing</li>
      <li>Listen with the current paragraph highlighted as it's read aloud</li>
      <li>Your place is saved, and you can download the EPUB or the MP3 audiobook</li>
    </ul>
    <p class="hint">Enter a username to open your library. A new name starts an empty one, and you'll only
      see books uploaded under your name.</p>
    <form method="post" action="/books/login">
      <input type="hidden" name="next" value="{escape(next_path)}">
      <input name="username" placeholder="Username" aria-label="Username" autocomplete="username"
        autocapitalize="none" autocorrect="off" spellcheck="false" maxlength="32" autofocus required>
      <button type="submit" class="btn">Open</button>
    </form>
    {error}
  </main>
</body>
</html>
"""


def library(user: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  {HEAD}
  <title>Library</title>
  {FONTS}
  <link rel="stylesheet" href="{STYLE}">
  <link rel="stylesheet" href="/static/books/library.css?v={ASSET_VERSION}">
</head>
<body>
  <main class="paper library">
    {NAV}
    <div class="lib-head">
      <h1 class="page-title">Library</h1>
      <span class="who">{escape(user)} · <a id="switch-user" href="/books/logout">Switch user</a></span>
      <button id="link-toggle" class="btn add" type="button" aria-expanded="false">Add from link</button>
      <label class="btn add">Add book<input id="file" type="file" accept=".epub,application/epub+zip" multiple hidden></label>
    </div>
    <div id="link-panel" hidden>
      <form id="link-form" class="link-form">
        <input id="link-url" type="url" placeholder="Royal Road, SpaceBattles, Sufficient Velocity or QQ story link"
          aria-label="Story link" autocomplete="off" autocapitalize="none" autocorrect="off" spellcheck="false" required>
        <button type="submit" class="btn">Import</button>
      </form>
      <p class="link-hint">Royal Road and SpaceBattles block downloads from this server. Instead, drag
        <a id="bookmarklet" class="bookmarklet" href="#">Import to Library</a> to your bookmarks bar
        (or <button id="bookmarklet-copy" class="linkish" type="button">copy it</button> into a new bookmark's
        address), then use it on the story's page there. It works on the other forums too.</p>
    </div>
    <ul id="imports" class="imports" hidden></ul>
    <p id="notice" class="notice" hidden></p>
    <div id="books" class="books"></div>
    <p id="empty" class="empty" hidden>No books yet. Add an EPUB or a story link to get started.</p>
  </main>
  <script src="/static/books/library.js?v={ASSET_VERSION}"></script>
</body>
</html>
"""


def receive(user: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  {HEAD}
  <title>Import to Library</title>
  {FONTS}
  <link rel="stylesheet" href="{STYLE}">
  <link rel="stylesheet" href="/static/books/library.css?v={ASSET_VERSION}">
</head>
<body>
  <main class="paper receive">
    <h1 class="page-title">Import to Library</h1>
    <p id="status" class="notice">Waiting for the story's page…</p>
    <div id="progress" class="bar" hidden><i></i></div>
    <p class="hint">Signed in as {escape(user)} · <a href="/books" target="_blank" rel="noopener">Open your library</a></p>
  </main>
  <script src="/static/books/receive.js?v={ASSET_VERSION}"></script>
</body>
</html>
"""


# Page colors of the reader themes; iOS paints the home screen app's status bar with the one
# the page loads with, so the server renders it from the reader_theme cookie.
THEME_BG = {"original": "#ffffff", "sepia": "#f8f1e3", "gray": "#4a4a4d", "night": "#121212"}


def reader(book: dict, theme: str = "original") -> str:
    theme = theme if theme in THEME_BG else "original"
    return f"""<!doctype html>
<html lang="en" data-theme="{theme}">
<head>
  {HEAD}
  <meta name="theme-color" content="{THEME_BG[theme]}">
  <title>{escape(book["title"])}</title>
  <link rel="stylesheet" href="/static/books/reader.css?v={ASSET_VERSION}">
</head>
<body data-book="{escape(book["id"])}">
  <div id="stage">
    <div id="viewport"><div id="flow"></div></div>
    <div id="footer"><span id="page-info"></span></div>
    <button id="listen-fab" class="icon-btn" aria-label="Listen" title="Listen from this page">{ICON_HEADPHONES}</button>
  </div>

  <header id="topbar" class="chrome">
    <a class="icon-btn" href="/books" aria-label="Library" title="Library">{ICON_BACK}</a>
    <div class="top-title">{escape(book["title"])}</div>
    <button class="icon-btn" data-open="toc" aria-label="Contents" title="Contents">{ICON_LIST}</button>
    <button class="icon-btn" data-open="search" aria-label="Search" title="Search">{ICON_SEARCH}</button>
    <button class="icon-btn" data-open="settings" aria-label="Text settings" title="Text settings"><span class="aa">Aa</span></button>
    <button class="icon-btn" id="listen-top" aria-label="Listen" title="Listen">{ICON_HEADPHONES}</button>
    <button class="icon-btn" data-open="menu" aria-label="More" title="More">{ICON_MORE}</button>
  </header>

  <div id="scrim" hidden></div>

  <section id="toc" class="sheet" hidden>
    <div class="sheet-head"><h2>Contents</h2><button class="close" aria-label="Close">×</button></div>
    <ol id="toc-list" class="sheet-body"></ol>
  </section>

  <section id="search" class="sheet" hidden>
    <div class="sheet-head"><h2>Search</h2><button class="close" aria-label="Close">×</button></div>
    <form id="search-form"><input id="search-input" type="search" placeholder="Search this book" autocomplete="off"></form>
    <p id="search-count" class="muted"></p>
    <ol id="search-results" class="sheet-body"></ol>
  </section>

  <section id="settings" class="sheet" hidden>
    <div class="sheet-head"><h2>Text</h2><button class="close" aria-label="Close">×</button></div>
    <div class="sheet-body">
      <div class="row size-row">
        <button id="smaller" class="pill" aria-label="Smaller text"><span style="font-size:14px">A</span></button>
        <span id="size-label"></span>
        <button id="larger" class="pill" aria-label="Larger text"><span style="font-size:22px">A</span></button>
      </div>
      <div class="row themes" id="themes">
        <button data-theme="original" class="swatch">Original</button>
        <button data-theme="sepia" class="swatch">Sepia</button>
        <button data-theme="gray" class="swatch">Gray</button>
        <button data-theme="night" class="swatch">Night</button>
      </div>
      <div class="fonts" id="fonts">
        <button data-font="original">Original</button>
        <button data-font="charter">Charter</button>
        <button data-font="georgia">Georgia</button>
        <button data-font="palatino">Palatino</button>
        <button data-font="system">San Francisco</button>
      </div>
      <div class="row spacing-row">
        <span>Line spacing</span>
        <div class="seg" id="spacing">
          <button data-spacing="1.4">Tight</button><button data-spacing="1.6">Normal</button><button data-spacing="1.85">Loose</button>
        </div>
      </div>
    </div>
  </section>

  <section id="menu" class="sheet" hidden>
    <div class="sheet-head"><h2>{escape(book["title"])}</h2><button class="close" aria-label="Close">×</button></div>
    <div class="sheet-body menu-list">
      <p class="muted">{escape(book["author"])}</p>
      <a class="menu-item" href="/books/api/{escape(book["id"])}/download.epub" download>Download EPUB</a>
      <a class="menu-item" id="dl-book-mp3" href="/books/api/{escape(book["id"])}/download.mp3" download>Download audiobook (MP3)</a>
      <a class="menu-item" id="dl-chapter-mp3" href="#" download>Download this chapter's audio</a>
      <button class="menu-item" id="narrate" type="button" hidden></button>
      <p id="audio-summary" class="muted"></p>
      <a class="menu-item" href="/books">Back to library</a>
    </div>
  </section>

  <div id="player" hidden>
    <div id="player-status"></div>
    <div class="player-controls">
      <button id="back15" class="icon-btn" aria-label="Back 15 seconds" title="Back 15 seconds">{ICON_BACK15}</button>
      <button id="playpause" class="icon-btn big" aria-label="Pause">{ICON_PAUSE}</button>
      <button id="fwd15" class="icon-btn" aria-label="Forward 15 seconds" title="Forward 15 seconds">{ICON_FWD15}</button>
      <button id="speed" class="pill">1×</button>
      <button id="stop" class="icon-btn" aria-label="Stop listening" title="Stop listening">×</button>
    </div>
  </div>
  <audio id="audio" preload="auto"></audio>

  <script>window.BOOK = {json.dumps({"id": book["id"], "title": book["title"]}).replace("</", "<\\/")};</script>
  <script src="/static/books/reader.js?v={ASSET_VERSION}"></script>
</body>
</html>
"""


def _svg(path: str) -> str:
    return (
        '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>'
    )


ICON_BACK = _svg('<path d="M15 18l-6-6 6-6"/>')
ICON_LIST = _svg('<path d="M8 6h13M8 12h13M8 18h13"/><circle cx="3.5" cy="6" r="1"/><circle cx="3.5" cy="12" r="1"/><circle cx="3.5" cy="18" r="1"/>')
ICON_SEARCH = _svg('<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>')
ICON_MORE = _svg('<circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/>')
ICON_HEADPHONES = _svg('<path d="M3 18v-6a9 9 0 0118 0v6"/><path d="M21 19a2 2 0 01-2 2h-1v-6h3zM3 19a2 2 0 002 2h1v-6H3z"/>')
ICON_PAUSE = _svg('<path d="M9 5v14M15 5v14"/>')
ICON_BACK15 = _svg('<path d="M3 12a9 9 0 109-9 9 9 0 00-6.4 2.6L3 8"/><path d="M3 3v5h5"/><text x="12" y="15.5" font-size="7" text-anchor="middle" fill="currentColor" stroke="none">15</text>')
ICON_FWD15 = _svg('<path d="M21 12a9 9 0 11-9-9 9 9 0 016.4 2.6L21 8"/><path d="M21 3v5h-5"/><text x="12" y="15.5" font-size="7" text-anchor="middle" fill="currentColor" stroke="none">15</text>')
