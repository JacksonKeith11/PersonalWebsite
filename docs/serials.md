# Serial updates page

Read this before changing anything in `app/serials/`.

## What it does

An unlisted page (`/<SERIALS_PATH>`, behind `SERIALS_PASSWORD`) lists new chapters of the
serials the owner follows, newest first, grouped by day, 50 per page.

- `scheduler.py` runs one daemon thread. Every source syncs every 2 minutes, and each result is
  recorded in the `status` table, so failures show on the page instead of crashing anything.
- `sources/email_inbox.py` covers **AO3, Royal Road and fiction.live**, entirely from notification
  emails. It reads a Gmail label (`GMAIL_LABEL`, default `serials`) over IMAP with an app password.
  Those three sites are never contacted.
- `sources/xenforo.py` covers **SpaceBattles, Sufficient Velocity and Questionable Questing**. It
  logs in and reads each forum's "What's new → Threadmarks" listing, filtered to watched threads and
  threadmark category 1 (the main story). That's one request per sync per forum, up to 5 pages.
- `db.py` is SQLite at `data/serials.db`, with tables `updates`, `state` (key/value) and `status`.
  `Update.key` is unique per chapter, and saving upserts on it.
- `page.py` renders the HTML (inline CSS) and the login page, which the books library doesn't
  share.
- `http.py` provides one httpx client factory and `get` with backoff on 429, 5xx and transport
  errors. The books importer reuses it.

## Design directives

- **Keep requests to the sites minimal.** Use email wherever a site sends notifications, and one
  listing request per forum per sync. Never fetch per thread or per story.
- **No backfill.** Only emails sent after the first successful sync count (`email_since` in
  `state`), even if older mail gets the label later.
- The page is private: `noindex`, `no-store`, behind `auth`.

## Gotchas

- **Rejected credentials are remembered.** A rejected Gmail or forum password is fingerprinted in
  `state` (`rejected:<source>`), and that source stops retrying until the credentials change in
  `.env`, so a typo can't trigger account lockouts. If a source says "not retrying", fix `.env` and
  restart.
- **IMAP UIDs are only valid within one UIDVALIDITY.** When it changes, `imap_last_uid` resets to 0.
  The search `UID n:*` always returns the newest message even when it's older than n, so results
  are filtered with `> last_uid`.
- **Royal Road emails take two forms.** Older ones have direct chapter links. Newer ones only link
  through a click tracker, so the chapter title comes from the plain text ("... titled X") and the
  link from "read it at <url>". Chapter titles can contain " titled ", so the text is split on the
  exact fiction title first.
- **AO3 times can be fake.** AO3 gives only a date for some updates, stored as midnight UTC, and the
  page hides the time when `published % 86400 == 0`.
- **The same chapter is often linked twice in one email** (the title, then a "Read" button).
  `_process` merges by key and keeps the non-placeholder title.
- **Forum sessions persist.** One httpx client per forum lives in memory, so the session cookie
  survives between syncs. The scheduler logs in only when the page shows `data-logged-in="false"`.
- **Adding a column** means an `ALTER TABLE` guarded by a `PRAGMA table_info` check in `_db()`,
  like the existing `author` column. There are no migrations otherwise.
- Times display in `DISPLAY_TZ`, default `America/New_York`.
