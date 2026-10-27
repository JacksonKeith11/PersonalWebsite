(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const COLORS = ["#7a5a2f", "#4e6151", "#5b4a6b", "#7b3f3f", "#3f5a73", "#6b5d3a"];
  let refreshTimer;

  function el(tag, props = {}, ...children) {
    const node = Object.assign(document.createElement(tag), props);
    node.append(...children.filter((c) => c != null));
    return node;
  }

  function notice(text, isError = false) {
    const n = $("#notice");
    n.hidden = !text;
    n.textContent = text || "";
    n.classList.toggle("err", isError);
  }

  function audioLine(a) {
    if (a.ready.length === a.total) return "Audio ready";
    if (!a.requested) return a.percent ? `Audio ${a.percent}% · stopped` : "";
    if (a.working) return `Narrating · ${a.percent}%`;
    return a.percent ? `Audio ${a.percent}%` : "Audio queued";
  }

  const narrating = (a) => a.requested && a.ready.length < a.total;

  function cover(b) {
    if (b.cover) return el("div", { className: "cover" }, el("img", { src: b.cover, alt: "" }));
    let hash = 0;
    for (const c of b.id) hash = (hash * 31 + c.charCodeAt(0)) >>> 0;
    const div = el("div", { className: "cover" }, el("div", { className: "placeholder" }, el("b", { textContent: b.title }), el("span", { textContent: b.author })));
    div.style.background = COLORS[hash % COLORS.length];
    return div;
  }

  function card(b) {
    const pct = Math.floor(b.percent);
    const progress = b.percent >= 99.5 ? "Finished" : b.opened ? `${pct}%` : "New";
    const bar = el("div", { className: "bar" }, el("i"));
    bar.firstChild.style.width = `${b.percent}%`;
    const link = el("a", { href: `/books/read/${b.id}` },
      cover(b),
      el("div", { className: "title", textContent: b.title }),
      el("div", { className: "author", textContent: b.author }),
      bar,
      el("div", { className: "meta" }, el("span", { textContent: progress }), el("span", { textContent: audioLine(b.audio) })),
    );

    const mp3Ready = b.audio.percent > 0;
    const del = el("button", { className: "danger", textContent: "Delete" });
    del.addEventListener("click", async () => {
      if (!confirm(`Delete “${b.title}” and its audio?`)) return;
      await fetch(`/books/api/${b.id}`, { method: "DELETE" });
      load();
    });
    // Narration only runs when asked for (here, or by pressing listen in the reader).
    let narrate = null;
    if (b.audio.ready.length < b.audio.total) {
      narrate = el("button", {
        textContent: b.audio.requested ? "Stop making audiobook" : b.audio.percent ? "Resume making audiobook" : "Make audiobook",
      });
      narrate.addEventListener("click", async () => {
        await fetch(`/books/api/${b.id}/narrate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ on: !b.audio.requested }),
        });
        load();
      });
    }
    const menu = el("details", { className: "more" },
      el("summary", { textContent: "⋯", title: "More" }),
      el("ul", {},
        el("li", {}, el("a", { href: `/books/api/${b.id}/download.epub`, download: "", textContent: "Download EPUB" })),
        el("li", {}, el("a", {
          href: `/books/api/${b.id}/download.mp3`,
          download: "",
          className: mp3Ready ? "" : "off",
          textContent: b.audio.percent >= 100 || !mp3Ready ? "Download audiobook (MP3)" : `Download audio so far (${b.audio.percent}%)`,
        })),
        narrate && el("li", {}, narrate),
        el("li", {}, del),
      ),
    );
    return el("div", { className: "book" }, link, menu);
  }

  async function load() {
    clearTimeout(refreshTimer);
    const r = await fetch("/books/api/library");
    if (r.status === 401) return location.reload();
    const books = await r.json();
    // Most recently read first, then newest uploads.
    books.sort((a, b) => Math.max(b.opened, b.added) - Math.max(a.opened, a.added));
    const openMenus = new Set([...document.querySelectorAll(".more[open]")].map((d) => d.dataset.id));
    const grid = $("#books");
    grid.textContent = "";
    for (const b of books) {
      const c = card(b);
      c.querySelector(".more").dataset.id = b.id;
      if (openMenus.has(b.id)) c.querySelector(".more").open = true;
      grid.append(c);
    }
    $("#empty").hidden = books.length > 0;
    if (books.some((b) => narrating(b.audio))) refreshTimer = setTimeout(load, 15000);
  }

  document.addEventListener("click", (e) => {
    document.querySelectorAll(".more[open]").forEach((d) => {
      if (!d.contains(e.target)) d.open = false;
    });
  });

  $("#file").addEventListener("change", async (e) => {
    const files = [...e.target.files];
    e.target.value = "";
    for (const [i, file] of files.entries()) {
      notice(`Uploading ${file.name}${files.length > 1 ? ` (${i + 1} of ${files.length})` : ""}…`);
      const r = await fetch("/books/api/upload", { method: "POST", body: file });
      if (!r.ok) {
        const detail = await r.json().catch(() => ({}));
        notice(`${file.name}: ${detail.detail || `upload failed (${r.status})`}`, true);
        await load();
        return;
      }
    }
    notice(files.length ? "Added. Choose Make audiobook in its ⋯ menu to narrate it." : "");
    load();
  });

  // Imports from a story link run on the server; poll while any are going.
  let importsTimer;
  const finished = new Set();

  function importLine(j) {
    const name = j.title ? `“${j.title}”` : j.url;
    if (j.status === "queued") return `Waiting to import ${name}`;
    if (j.status === "running") return j.total ? `Importing ${name} · ${j.done} of ${j.total} chapters` : `Importing ${name}…`;
    if (j.status === "done") return `Added ${name}.`;
    return `Couldn't import ${name}: ${j.error}`;
  }

  async function loadImports() {
    clearTimeout(importsTimer);
    const r = await fetch("/books/api/imports");
    if (!r.ok) return;
    const jobs = await r.json();
    const list = $("#imports");
    list.textContent = "";
    let reload = false;
    for (const j of jobs) {
      const li = el("li", { className: j.status === "error" ? "err" : "" }, el("span", { className: "what", textContent: importLine(j) }));
      if (j.status === "running" && j.total) {
        const bar = el("div", { className: "bar" }, el("i"));
        bar.firstChild.style.width = `${(j.done / j.total) * 100}%`;
        li.append(bar);
      }
      if (j.status === "done" || j.status === "error") {
        const x = el("button", { className: "dismiss", textContent: "×", title: "Dismiss", ariaLabel: "Dismiss" });
        x.addEventListener("click", async () => {
          await fetch(`/books/api/imports/${j.id}`, { method: "DELETE" });
          loadImports();
        });
        li.append(x);
      }
      if (j.status === "done" && !finished.has(j.id)) {
        finished.add(j.id);
        reload = true;
      }
      list.append(li);
    }
    list.hidden = jobs.length === 0;
    if (reload) load();
    if (jobs.some((j) => j.status === "queued" || j.status === "running")) importsTimer = setTimeout(loadImports, 3000);
  }

  $("#link-toggle").addEventListener("click", () => {
    const panel = $("#link-panel");
    panel.hidden = !panel.hidden;
    $("#link-toggle").setAttribute("aria-expanded", String(!panel.hidden));
    if (!panel.hidden) $("#link-url").focus();
  });

  // The "Import to Library" bookmarklet, for Royal Road and the forums, which block this server but
  // not the reader's browser. It opens /books/receive as a popup (which has the books_user cookie);
  // the server's parsers ask through it for the pages they need, and the browser fetches them here,
  // a second apart, and sends them back. Self-contained, since it's serialized into the link.
  function grab(origin) {
    const fail = (m) => alert("Import to Library: " + m);
    const sites = /(^|\.)(royalroad\.com|spacebattles\.com|sufficientvelocity\.com|questionablequesting\.com)$/;
    if (!sites.test(location.hostname)) return fail("open a story on Royal Road, SpaceBattles, Sufficient Velocity or Questionable Questing first.");
    const win = window.open(origin + "/books/receive", "books-receive", "popup,width=480,height=320");
    if (!win) return fail("allow pop-ups for this site and try again.");
    const send = (msg) => win.postMessage(msg, origin);
    const wait = (ms) => new Promise((r) => setTimeout(r, ms));
    // The parsers don't need scripts and the like, except Royal Road's chapter list and story details.
    const trim = (html) => {
      const doc = new DOMParser().parseFromString(html, "text/html");
      for (const el of doc.querySelectorAll("script, noscript, svg, iframe, link, template")) {
        if (el.type !== "application/ld+json" && !/window\.chapters\s*=/.test(el.textContent)) el.remove();
      }
      return doc.documentElement.outerHTML;
    };
    let last = 0;
    let busy = false;
    addEventListener("message", async (e) => {
      if (e.source !== win || e.origin !== origin) return;
      if (e.data === "ready") return send({ type: "start", url: location.href });
      if (!e.data || e.data.type !== "need" || busy) return;
      busy = true;
      try {
        const pages = {};
        for (const [i, url] of e.data.urls.entries()) {
          if (win.closed) return;
          send({ type: "progress", done: i, total: e.data.urls.length });
          await wait(last + 1000 - Date.now());
          last = Date.now();
          // Always this site: the server's link may name another of its hostnames (www. or not).
          const u = new URL(url);
          const r = await fetch(u.pathname + u.search, { credentials: "include" });
          if (!r.ok) throw new Error(`${location.hostname} returned an error (${r.status}).`);
          pages[url] = trim(await r.text());
        }
        send({ type: "pages", pages });
      } catch (err) {
        send({ type: "error", message: String((err && err.message) || err) });
      } finally {
        busy = false;
      }
    });
  }

  const bookmarklet = "javascript:" + encodeURIComponent(`(${grab})(${JSON.stringify(location.origin)})`);
  $("#bookmarklet").href = bookmarklet;
  $("#bookmarklet").addEventListener("click", (e) => {
    e.preventDefault();
    notice("Drag that link to your bookmarks bar, then use it on a story's page.");
  });
  $("#bookmarklet-copy").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(bookmarklet);
      notice("Copied. Add a bookmark, paste this as its address, and use it on a story's page.");
    } catch {
      notice("Couldn't copy. Drag the Import to Library link to your bookmarks instead.", true);
    }
  });

  $("#link-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const input = $("#link-url");
    const r = await fetch("/books/api/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: input.value }),
    });
    if (!r.ok) {
      const detail = await r.json().catch(() => ({}));
      notice(detail.detail || `Import failed (${r.status})`, true);
      return;
    }
    notice("");
    input.value = "";
    loadImports();
  });

  load();
  // Books already finished before this page loaded are in the library; don't reload for them.
  fetch("/books/api/imports").then((r) => (r.ok ? r.json() : [])).then((jobs) => {
    for (const j of jobs) if (j.status === "done") finished.add(j.id);
    loadImports();
  });
})();
