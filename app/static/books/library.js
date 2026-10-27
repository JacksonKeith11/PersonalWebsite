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
    if (a.working) return `Narrating · ${a.percent}%`;
    return a.percent ? `Audio ${a.percent}%` : "Audio queued";
  }

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
    if (books.some((b) => b.audio.ready.length < b.audio.total)) refreshTimer = setTimeout(load, 15000);
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
    notice(files.length ? "Added. Narration has started in the background." : "");
    load();
  });

  // Imports from a story link run on the server; poll while any are going.
  let importsTimer;
  const finished = new Set();

  function importLine(j) {
    const name = j.title ? `“${j.title}”` : j.url;
    if (j.status === "queued") return `Waiting to import ${name}`;
    if (j.status === "running") return j.total ? `Importing ${name} · ${j.done} of ${j.total} chapters` : `Importing ${name}…`;
    if (j.status === "done") return `Added ${name}. Narration has started in the background.`;
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
    const form = $("#link-form");
    form.hidden = !form.hidden;
    $("#link-toggle").setAttribute("aria-expanded", String(!form.hidden));
    if (!form.hidden) $("#link-url").focus();
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
