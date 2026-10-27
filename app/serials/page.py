import math
import os
import time
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from . import db

TZ = ZoneInfo(os.environ.get("DISPLAY_TZ", "America/New_York"))
PAGE_SIZE = 50

ICONS = {
    "Royal Road": "royalroad",
    "AO3": "ao3",
    "SpaceBattles": "spacebattles",
    "Sufficient Velocity": "sufficientvelocity",
    "Questionable Questing": "questionablequesting",
    "fiction.live": "fictionlive",
}


def _ago(ts: float | None) -> str:
    if not ts:
        return "never"
    s = int(time.time() - ts)
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if s >= size:
            return f"{s // size}{unit} ago"
    return "just now"


def _day_label(d: datetime) -> str:
    today = datetime.now(TZ).date()
    delta = (today - d.date()).days
    if delta == 0:
        return "Today"
    if delta == 1:
        return "Yesterday"
    return d.strftime("%A, %b %-d" if delta < 7 else "%b %-d, %Y")


def _icon(site: str) -> str:
    name = ICONS.get(site)
    if not name:
        return f'<span class="icon" title="{escape(site)}">{escape(site[:1])}</span>'
    return f'<img class="icon" src="/static/icons/{name}.png" alt="{escape(site)}" title="{escape(site)}" width="20" height="20">'


def _pager(page: int, pages: int) -> str:
    if pages <= 1:
        return ""
    newer = f'<a class="btn" href="?page={page - 1}">← Newer</a>' if page > 1 else '<span class="btn disabled">← Newer</span>'
    older = f'<a class="btn" href="?page={page + 1}">Older →</a>' if page < pages else '<span class="btn disabled">Older →</span>'
    return f'<nav class="pager">{newer}<span class="pages">Page {page} of {pages}</span>{older}</nav>'


def render(page: int = 1) -> str:
    pages = max(1, math.ceil(db.count_updates() / PAGE_SIZE))
    page = min(max(page, 1), pages)

    rows = []
    current_day = None
    for u in db.recent_updates(PAGE_SIZE, (page - 1) * PAGE_SIZE):
        local = datetime.fromtimestamp(u["published"], TZ)
        day = _day_label(local)
        if day != current_day:
            rows.append(f'<h2 class="day">{escape(day)}</h2>')
            current_day = day
        # AO3 only gives a date, stored as midnight UTC; don't show a fake time.
        when = "" if u["published"] % 86400 == 0 else local.strftime("%-I:%M %p")
        by = f'<span class="author">by {escape(u["author"])}</span>' if u["author"] else ""
        rows.append(
            f"""<div class="update">
  {_icon(u["site"])}
  <span class="when">{escape(when)}</span>
  <div class="what">
    <a class="story" href="{escape(u["story_url"])}">{escape(u["story_title"])}</a>{by}
    <span class="chapter">{escape(u["title"])}</span>
  </div>
  <a class="btn read" href="{escape(u["url"])}" target="_blank" rel="noopener noreferrer">Read</a>
</div>"""
        )
    if not rows:
        rows.append('<p class="empty">No updates yet. The first sync runs a minute or so after the server starts.</p>')

    status = "".join(
        f'<li>{_icon(s["source"]) if s["source"] in ICONS else ""}<b>{escape(s["source"])}</b> — last success {_ago(s["last_ok"])}'
        + (f' <span class="err">· {escape(s["error"])}</span>' if s["error"] else "")
        + "</li>"
        for s in db.statuses()
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <meta name="referrer" content="no-referrer">
  <title>Updates</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css?v=7">
  <style>
    .day {{ margin: 32px 0 8px; }}
    .day:first-of-type {{ margin-top: 8px; }}
    .update {{
      display: grid;
      grid-template-columns: 20px 4.5rem 1fr auto;
      gap: 4px 14px;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid var(--rule);
    }}
    .icon {{
      width: 20px;
      height: 20px;
      object-fit: contain;
      border-radius: 3px;
      vertical-align: middle;
    }}
    span.icon {{
      display: inline-grid;
      place-items: center;
      background: var(--rule);
      font-size: 0.75rem;
      font-weight: 600;
    }}
    .when {{ color: var(--muted); font-size: 0.9rem; white-space: nowrap; }}
    .what {{ min-width: 0; }}
    .story {{ color: var(--fg); font-weight: 600; margin-right: 8px; }}
    .author {{ color: var(--muted); font-size: 0.9em; margin-right: 8px; }}
    .chapter {{ color: var(--muted); overflow-wrap: anywhere; }}
    .btn {{
      display: inline-block;
      padding: 4px 14px;
      border: 1px solid var(--accent);
      border-radius: 4px;
      color: var(--accent);
      font-size: 0.9rem;
      font-weight: 600;
      text-align: center;
      white-space: nowrap;
    }}
    a.btn:hover {{ background: var(--accent); color: var(--paper); text-decoration: none; }}
    .btn.disabled {{ border-color: var(--rule); color: var(--rule); }}
    .read {{ min-width: 4.5rem; }}
    .pager {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-top: 28px;
    }}
    .pages {{ color: var(--muted); font-size: 0.9rem; }}
    .empty {{ color: var(--muted); }}
    details {{ margin-top: 40px; color: var(--muted); font-size: 0.9rem; }}
    details ul {{ padding-left: 0; list-style: none; }}
    details li {{ margin-bottom: 6px; }}
    details .icon {{ width: 16px; height: 16px; margin-right: 6px; vertical-align: -3px; }}
    .err {{ color: #a33; }}
    @media (max-width: 640px) {{
      .update {{ grid-template-columns: 18px 3.3rem 1fr auto; gap: 4px 10px; }}
      .update .icon {{ width: 18px; height: 18px; }}
      .when {{ font-size: 0.8rem; }}
      .what {{ font-size: 0.95rem; line-height: 1.4; }}
      .read {{ min-width: 0; padding: 4px 10px; font-size: 0.85rem; }}
    }}
  </style>
</head>
<body>
  <main class="paper">
    <h1 class="page-title">Updates</h1>
    {"".join(rows)}
    {_pager(page, pages)}
    <details>
      <summary>Sync status</summary>
      <ul>{status or "<li>No syncs have run yet.</li>"}</ul>
    </details>
  </main>
</body>
</html>
"""


def render_login(failed: bool = False, title: str = "Updates", next_path: str = "/") -> str:
    error = '<p class="err">Wrong password.</p>' if failed else ""
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <meta name="referrer" content="no-referrer">
  <title>{escape(title)}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Source+Sans+3:wght@400;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/static/style.css?v=7">
  <style>
    .paper {{ max-width: 420px; }}
    form {{ display: flex; gap: 10px; margin-top: 16px; }}
    input[type=password] {{
      flex: 1;
      min-width: 0;
      padding: 8px 12px;
      border: 1px solid var(--rule);
      border-radius: 4px;
      background: #fff;
      color: var(--fg);
      font: inherit;
    }}
    input[type=password]:focus {{ outline: 2px solid var(--accent); outline-offset: -1px; }}
    button {{
      padding: 8px 18px;
      border: 1px solid var(--accent);
      border-radius: 4px;
      background: var(--accent);
      color: var(--paper);
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }}
    .err {{ color: #a33; margin: 12px 0 0; }}
  </style>
</head>
<body>
  <main class="paper">
    <h1 class="page-title">{escape(title)}</h1>
    <form method="post" action="/login">
      <input type="hidden" name="next" value="{escape(next_path)}">
      <input type="password" name="password" placeholder="Password" aria-label="Password" autocomplete="current-password" autofocus required>
      <button type="submit">Enter</button>
    </form>
    {error}
  </main>
</body>
</html>
"""
