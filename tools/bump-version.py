"""Bump the cache version (`?v=`) of everything under a static folder (or one file), everywhere
it's linked.

Cloudflare caches static files by URL, so a changed CSS or JS file needs a new `?v=` on every link
to it, or browsers keep the old copy. Every link to a file under the folder gets the folder's
highest version plus one: the page, the modules importing each other, and pages elsewhere that
link in (so bumping app/static/games/shared updates each game's import of it).

    python3 tools/bump-version.py app/static/games/saltbound   # after changing Saltbound's CSS/JS
    python3 tools/bump-version.py app/static/style.css          # one file: the site's stylesheet
    python3 tools/bump-version.py --check                       # links to one file that disagree

The books' files use ASSET_VERSION in app/books/pages.py, which bumping app/static/books (or anything
the books' pages link, like style.css) updates too.
"""

import os
import re
import sys
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
STATIC = os.path.join(ROOT, "app", "static")
BOOKS_PAGES = os.path.join(ROOT, "app", "books", "pages.py")
REF = re.compile(r"""(?P<path>[A-Za-z0-9_./-]+\.(?:js|css|mjs))\?v=(?P<v>\d+)""")


def sources():
    for base, _, files in os.walk(STATIC):
        for name in files:
            if name.endswith((".html", ".js", ".css")):
                yield os.path.join(base, name)
    yield BOOKS_PAGES


def target(src, path):
    """The file a link points at: absolute /static/ links, or relative to the linking file."""
    if path.startswith("/static/"):
        return os.path.normpath(os.path.join(STATIC, path[len("/static/"):]))
    if path.startswith("/"):
        return None
    return os.path.normpath(os.path.join(os.path.dirname(src), path))


def refs():
    """{source file: [(match, target file)]}"""
    out = {}
    for src in sources():
        text = open(src, encoding="utf-8").read()
        found = [(m, target(src, m["path"])) for m in REF.finditer(text)]
        if found:
            out[src] = found
    return out


def check():
    seen = defaultdict(set)
    for src, found in refs().items():
        for m, tgt in found:
            if tgt:
                seen[tgt].add(m["v"])
    bad = {t: v for t, v in seen.items() if len(v) > 1}
    for t, v in sorted(bad.items()):
        print(f"{os.path.relpath(t, ROOT)}: linked with ?v={', '.join(sorted(v, key=int))}")
    return not bad


def bump(folder):
    folder = os.path.normpath(os.path.abspath(folder))
    inside = lambda t: t and (t == folder or t.startswith(folder + os.sep))
    all_refs = refs()
    versions = [int(m["v"]) for found in all_refs.values() for m, t in found if inside(t)]
    if not versions and not inside(os.path.join(STATIC, "books", "x")):
        sys.exit(f"nothing under {folder} is linked with a ?v=")
    new = max(versions or [0]) + 1
    changed = 0
    books_shell = False
    for src, found in all_refs.items():
        text = open(src, encoding="utf-8").read()
        out, last = [], 0
        for m, t in found:
            if inside(t):
                out.append(text[last:m.start("v")] + str(new))
                last = m.end("v")
                changed += 1
        if last:
            out.append(text[last:])
            open(src, "w", encoding="utf-8").write("".join(out))
            books_shell |= src == BOOKS_PAGES
    # the books' service worker caches its shell (style.css included) by ASSET_VERSION
    if books_shell or inside(os.path.join(STATIC, "books", "x")):
        text = open(BOOKS_PAGES, encoding="utf-8").read()
        text = re.sub(r"^ASSET_VERSION = (\d+)", lambda m: f"ASSET_VERSION = {int(m[1]) + 1}", text, flags=re.M)
        open(BOOKS_PAGES, "w", encoding="utf-8").write(text)
        changed += 1
    print(f"{os.path.relpath(folder, ROOT)}: ?v={new} ({changed} links)")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args == ["--check"]:
        sys.exit(0 if check() else 1)
    for a in args:
        bump(a)
    sys.exit(0 if check() else 1)
