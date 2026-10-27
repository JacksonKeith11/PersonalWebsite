// Offline reading for the library. Served from /books/sw.js (see routes.py), which fills in
// VERSION and SHELL. Books are saved for offline reading from the library's ⋯ menu (library.js
// writes them into a "book-<id>" cache); this answers from those caches when the network
// doesn't, and keeps the last library listing so the shelf opens offline.
const VERSION = "__VERSION__";
const SHELL = __SHELL__; // the pages' scripts, styles and fonts
const SHELL_CACHE = `shell-${VERSION}`;
const LIBRARY_CACHE = "library";
const WAIT = 4000; // ms to wait on a slow network before showing a saved copy

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL_CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    for (const key of await caches.keys()) {
      if (key.startsWith("shell-") && key !== SHELL_CACHE) await caches.delete(key);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return;
  const path = url.pathname;
  if (path.startsWith("/static/")) return e.respondWith(shell(req));
  if (path === "/books" || path === "/books/api/library") return e.respondWith(networkFirst(req, LIBRARY_CACHE, true));
  const m = path.match(/^\/books\/(read|api)\/([0-9a-f]{12})(\/.*)?$/);
  if (!m) return;
  const [, kind, id, rest] = m;
  if (!rest) return e.respondWith(caches.has(`book-${id}`).then((saved) => networkFirst(req, `book-${id}`, saved)));
  if (kind === "api" && /^\/(chapter|res)\//.test(rest)) e.respondWith(cacheFirst(req, `book-${id}`));
});

async function shell(req) {
  const cache = await caches.open(SHELL_CACHE);
  const hit = await cache.match(req);
  if (hit) return hit;
  const r = await fetch(req);
  if (r.ok) cache.put(req, r.clone());
  return r;
}

// Chapter text and images never change for a given ?v=, so a saved copy is always good.
async function cacheFirst(req, name) {
  if (await caches.has(name)) {
    const hit = await (await caches.open(name)).match(req);
    if (hit) return hit;
  }
  return fetch(req);
}

// The network's answer when there is one (kept, if `keep`, for next time offline); otherwise the
// kept copy, marked so the page can tell it's offline. A stalled connection gets the copy too.
async function networkFirst(req, name, keep) {
  const cache = keep ? await caches.open(name) : null;
  const hit = cache && (await cache.match(req, { ignoreVary: true }));
  const network = fetch(req).then((r) => {
    if (r.ok && cache) cache.put(req, r.clone());
    return r;
  });
  if (!hit) {
    try {
      return await network;
    } catch (err) {
      if (req.mode === "navigate") return offlinePage(new URL(req.url).pathname === "/books");
      throw err;
    }
  }
  const timeout = new Promise((resolve) => setTimeout(resolve, WAIT, null));
  const r = await Promise.race([network.catch(() => null), timeout]);
  if (r) return r;
  const headers = new Headers(hit.headers);
  headers.set("X-Offline", "1");
  return new Response(hit.body, { status: hit.status, statusText: hit.statusText, headers });
}

function offlinePage(library) {
  const what = library
    ? "Open the library once while online, and save books from their ⋯ menu to read them without a connection."
    : "This book isn't saved for offline reading. Books you save from the ⋯ menu in your library open without a connection.";
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex, nofollow">
<title>Offline</title><style>
body { font: 17px/1.5 -apple-system, system-ui, sans-serif; background: #fbf7ef; color: #2b2620; margin: 0; padding: 48px 20px; }
main { max-width: 480px; margin: 0 auto; } a { color: #7a5a2f; }
@media (prefers-color-scheme: dark) { body { background: #1b1916; color: #e8e2d6; } a { color: #d2b48a; } }
</style></head><body><main><h1>You're offline</h1>
<p>${what}</p>
<p><a href="/books">Back to the library</a></p></main></body></html>`;
  return new Response(html, { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } });
}
