import os
import time
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

from . import db

TZ = ZoneInfo(os.environ.get("DISPLAY_TZ", "America/New_York"))


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


def render() -> str:
    rows = []
    current_day = None
    for u in db.recent_updates():
        local = datetime.fromtimestamp(u["published"], TZ)
        day = _day_label(local)
        if day != current_day:
            rows.append(f'<h2 class="day">{escape(day)}</h2>')
            current_day = day
        # AO3 only gives a date, stored as midnight UTC; don't show a fake time.
        when = "" if u["published"] % 86400 == 0 else local.strftime("%-I:%M %p")
        rows.append(
            f"""<div class="update">
  <span class="when">{escape(when)}</span>
  <span class="site">{escape(u["site"])}</span>
  <div class="what">
    <a class="story" href="{escape(u["story_url"])}">{escape(u["story_title"])}</a>
    <a class="chapter" href="{escape(u["url"])}">{escape(u["title"])}</a>
  </div>
</div>"""
        )
    if not rows:
        rows.append('<p class="empty">No updates yet. The first sync runs a minute or so after the server starts.</p>')

    status = "".join(
        f'<li><b>{escape(s["source"])}</b> — last success {_ago(s["last_ok"])}'
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
      grid-template-columns: 4.5rem 9rem 1fr;
      gap: 4px 12px;
      align-items: baseline;
      padding: 8px 0;
      border-bottom: 1px solid var(--rule);
    }}
    .when, .site {{ color: var(--muted); font-size: 0.9rem; white-space: nowrap; }}
    .what {{ min-width: 0; }}
    .story {{ color: var(--fg); font-weight: 600; margin-right: 8px; }}
    .chapter {{ overflow-wrap: anywhere; }}
    .empty {{ color: var(--muted); }}
    details {{ margin-top: 40px; color: var(--muted); font-size: 0.9rem; }}
    details ul {{ padding-left: 20px; }}
    .err {{ color: #a33; }}
    @media (max-width: 640px) {{
      .update {{ grid-template-columns: auto 1fr; }}
      .what {{ grid-column: 1 / -1; }}
    }}
  </style>
</head>
<body>
  <main class="paper">
    <h1 class="page-title">Updates</h1>
    {"".join(rows)}
    <details>
      <summary>Sync status</summary>
      <ul>{status or "<li>No syncs have run yet.</li>"}</ul>
    </details>
  </main>
</body>
</html>
"""
