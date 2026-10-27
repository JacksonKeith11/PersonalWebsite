(() => {
  "use strict";

  const ID = window.BOOK.id;
  const api = (path = "") => `/books/api/${ID}${path}`;
  const $ = (sel) => document.querySelector(sel);
  const flow = $("#flow");
  const viewport = $("#viewport");
  const audio = $("#audio");

  const FONTS = {
    original: '"Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif',
    georgia: "Georgia, serif",
    palatino: 'Palatino, "Palatino Linotype", "Book Antiqua", serif',
    system: '-apple-system, system-ui, "Segoe UI", sans-serif',
  };
  const SPEEDS = [0.8, 1, 1.2, 1.5, 1.75, 2];
  const SIZE_MIN = 14;
  const SIZE_MAX = 32;

  const settings = { size: 19, theme: "original", font: "original", spacing: "1.6", speed: 1 };
  try {
    Object.assign(settings, JSON.parse(localStorage.getItem("reader-settings") || "{}"));
  } catch {}

  let book;
  let chapter = -1;
  let page = 0;
  let pages = 1;
  let pageWidth = 1;
  let segs = [];
  let prefix = [];
  let totalChars = 1;
  let navigating = false;
  const cache = new Map();

  async function getJSON(url, options) {
    const r = await fetch(url, options);
    if (r.status === 401) location.reload();
    if (!r.ok) throw Object.assign(new Error(`HTTP ${r.status}`), { status: r.status });
    return r.json();
  }

  // ---------- layout and pagination ----------

  function fetchChapter(n) {
    if (!cache.has(n)) {
      const p = fetch(api(`/chapter/${n}`)).then((r) => {
        if (r.status === 401) location.reload();
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      });
      p.catch(() => cache.delete(n));
      cache.set(n, p);
    }
    return cache.get(n);
  }

  // Each page is one CSS column exactly as wide as the text area; turning a page slides the
  // column strip left by one viewport width.
  function measure() {
    const w = viewport.clientWidth;
    const gutter = Math.round(Math.max(20, Math.min(56, w * 0.07)));
    pageWidth = w;
    flow.style.width = `${w - 2 * gutter}px`;
    flow.style.marginLeft = `${gutter}px`;
    flow.style.columnWidth = `${w - 2 * gutter}px`;
    flow.style.columnGap = `${2 * gutter}px`;
    flow.style.setProperty("--page-h", `${viewport.clientHeight}px`);
  }

  function pageRange(el, origin = flow.firstElementChild.getBoundingClientRect().left) {
    const r = el.getBoundingClientRect();
    const first = Math.floor((r.left - origin + 2) / pageWidth);
    return [first, Math.max(first, Math.floor((r.right - origin - 2) / pageWidth))];
  }

  function paginate() {
    measure();
    const last = flow.lastElementChild;
    pages = last && last !== flow.firstElementChild ? pageRange(last)[1] + 1 : 1;
  }

  // The paragraph at the top of page p (it may have started on an earlier page).
  function segAtPage(p) {
    const origin = flow.firstElementChild.getBoundingClientRect().left;
    for (let i = 0; i < segs.length; i++) {
      const [a, b] = pageRange(segs[i], origin);
      if (b >= p) return a > p && i > 0 ? i - 1 : i;
    }
    return Math.max(0, segs.length - 1);
  }

  // The first paragraph that begins on page p, falling back to the one running through it.
  function segStartingOn(p) {
    const origin = flow.firstElementChild.getBoundingClientRect().left;
    for (let i = 0; i < segs.length; i++) {
      const a = pageRange(segs[i], origin)[0];
      if (a === p) return i;
      if (a > p) break;
    }
    return segAtPage(p);
  }

  function pageOfSeg(i) {
    const el = segs[Math.max(0, Math.min(segs.length - 1, i))];
    return el ? pageRange(el)[0] : 0;
  }

  async function settle() {
    const waits = [...flow.querySelectorAll("img")]
      .filter((img) => !img.complete)
      .map((img) => new Promise((done) => {
        img.addEventListener("load", done, { once: true });
        img.addEventListener("error", done, { once: true });
      }));
    await Promise.race([Promise.all(waits), new Promise((done) => setTimeout(done, 1500))]);
    if (document.fonts && document.fonts.ready) await document.fonts.ready;
  }

  async function openChapter(n, { segment = null, end = false } = {}) {
    n = Math.max(0, Math.min(book.chapters.length - 1, n));
    const html = await fetchChapter(n);
    chapter = n;
    flow.classList.add("instant");
    flow.innerHTML = `<span class="origin"></span>${html}`;
    segs = [...flow.querySelectorAll("[data-s]")];
    flow.querySelectorAll("img").forEach((img) => img.addEventListener("load", () => relayout(), { once: true }));
    if (listening && audioChapter === chapter && segs[curSeg]) segs[curSeg].classList.add("reading");
    await settle();
    paginate();
    go(end ? pages - 1 : segment != null ? pageOfSeg(segment) : 0, false);
    if (n + 1 < book.chapters.length) fetchChapter(n + 1).catch(() => {});
    updateChapterDownload();
  }

  async function relayout() {
    if (chapter < 0) return;
    const anchor = listening && audioChapter === chapter && curSeg >= 0 ? curSeg : segStartingOn(page);
    await settle();
    paginate();
    go(pageOfSeg(anchor), false);
  }

  function go(p, animate = true) {
    page = Math.max(0, Math.min(pages - 1, p));
    flow.classList.toggle("instant", !animate);
    flow.style.transform = `translateX(${-page * pageWidth}px)`;
    updateFooter();
    scheduleSave();
  }

  async function turn(dir) {
    if (navigating || !book) return;
    if (dir > 0 && page < pages - 1) return go(page + 1);
    if (dir < 0 && page > 0) return go(page - 1);
    const n = chapter + dir;
    if (n < 0 || n >= book.chapters.length) return;
    navigating = true;
    try {
      await openChapter(n, { end: dir < 0 });
    } finally {
      navigating = false;
    }
  }

  async function jump(n, segment) {
    navigating = true;
    try {
      await openChapter(n, { segment });
    } finally {
      navigating = false;
    }
  }

  // ---------- footer, progress ----------

  function percent() {
    const chars = book.chapters[chapter].chars;
    return Math.min(100, ((prefix[chapter] + (chars * (page + 1)) / pages) / totalChars) * 100);
  }

  function currentTocIndex() {
    const seg = segAtPage(page);
    let current = 0;
    book.toc.forEach((t, i) => {
      if (t.chapter < chapter || (t.chapter === chapter && t.segment <= seg)) current = i;
    });
    return current;
  }

  function updateFooter() {
    const left = pages - page - 1;
    const where = left === 0 ? "Last page in chapter" : `${left} page${left === 1 ? "" : "s"} left in chapter`;
    $("#page-info").textContent = `${where} · ${Math.floor(percent())}%`;
  }

  let saveTimer;
  function scheduleSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(saveNow, 800);
  }

  function saveNow() {
    clearTimeout(saveTimer);
    if (chapter < 0) return;
    const body = JSON.stringify({ chapter, segment: segStartingOn(page), percent: percent() });
    fetch(api("/progress"), { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true }).catch(() => {});
  }

  document.addEventListener("visibilitychange", () => document.hidden && saveNow());
  window.addEventListener("pagehide", saveNow);

  // ---------- input: tap, swipe, scroll, keys ----------

  const stage = $("#stage");
  let touch = null;
  let suppressClick = 0;

  stage.addEventListener("touchstart", (e) => {
    const t = e.touches[0];
    touch = { x: t.clientX, y: t.clientY };
  }, { passive: true });

  stage.addEventListener("touchend", (e) => {
    if (!touch) return;
    const t = e.changedTouches[0];
    const dx = t.clientX - touch.x;
    const dy = t.clientY - touch.y;
    touch = null;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < 40) return;
    suppressClick = Date.now();
    hideChrome();
    if (Math.abs(dx) > Math.abs(dy)) turn(dx < 0 ? 1 : -1);
    else turn(dy < 0 ? 1 : -1);
  }, { passive: true });

  stage.addEventListener("click", (e) => {
    if (Date.now() - suppressClick < 500 || e.target.closest("button, a")) return;
    if (document.body.classList.contains("chrome")) return hideChrome();
    const x = e.clientX / window.innerWidth;
    if (x < 0.3) turn(-1);
    else if (x > 0.7) turn(1);
    else document.body.classList.add("chrome");
  });

  // Trackpads keep sending wheel events for a while after a flick; one gesture turns one page.
  let wheelTotal = 0;
  let wheelLocked = false;
  let wheelTimer;
  stage.addEventListener("wheel", (e) => {
    e.preventDefault();
    clearTimeout(wheelTimer);
    wheelTimer = setTimeout(() => {
      wheelLocked = false;
      wheelTotal = 0;
    }, 220);
    if (wheelLocked) return;
    wheelTotal += Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
    if (Math.abs(wheelTotal) >= 40) {
      wheelLocked = true;
      hideChrome();
      turn(wheelTotal > 0 ? 1 : -1);
    }
  }, { passive: false });

  document.addEventListener("keydown", (e) => {
    if (e.target instanceof Element && e.target.closest("input")) return;
    if (e.key === "Escape") return closeSheets() || hideChrome();
    if (!$("#scrim").hidden) return;
    if (["ArrowRight", "ArrowDown", "PageDown", " "].includes(e.key)) {
      e.preventDefault();
      turn(1);
    } else if (["ArrowLeft", "ArrowUp", "PageUp"].includes(e.key)) {
      e.preventDefault();
      turn(-1);
    }
  });

  let resizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(relayout, 150);
  });

  function hideChrome() {
    document.body.classList.remove("chrome");
  }

  // ---------- sheets: contents, search, settings, menu ----------

  function openSheet(id) {
    closeSheets();
    hideChrome();
    $("#scrim").hidden = false;
    $(`#${id}`).hidden = false;
    if (id === "toc") renderToc();
    if (id === "search") setTimeout(() => $("#search-input").focus(), 60);
    if (id === "menu") refreshAudioSummary();
  }

  function closeSheets() {
    let open = false;
    document.querySelectorAll(".sheet").forEach((s) => {
      open = open || !s.hidden;
      s.hidden = true;
    });
    $("#scrim").hidden = true;
    return open;
  }

  document.querySelectorAll("[data-open]").forEach((b) => b.addEventListener("click", () => openSheet(b.dataset.open)));
  document.querySelectorAll(".sheet .close").forEach((b) => b.addEventListener("click", closeSheets));
  $("#scrim").addEventListener("click", closeSheets);

  function renderToc() {
    const list = $("#toc-list");
    list.textContent = "";
    const current = currentTocIndex();
    book.toc.forEach((t, i) => {
      const li = document.createElement("li");
      const b = document.createElement("button");
      b.textContent = t.title;
      b.style.paddingLeft = `${16 + t.depth * 18}px`;
      if (i === current) b.classList.add("current");
      b.addEventListener("click", () => {
        closeSheets();
        jump(t.chapter, t.segment);
      });
      li.append(b);
      list.append(li);
    });
    const cur = list.querySelector(".current");
    if (cur) cur.scrollIntoView({ block: "center" });
  }

  let searchTimer;
  let searchSeq = 0;
  $("#search-input").addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(runSearch, 300);
  });
  $("#search-form").addEventListener("submit", (e) => {
    e.preventDefault();
    runSearch();
    $("#search-input").blur();
  });

  async function runSearch() {
    const q = $("#search-input").value.trim();
    const seq = ++searchSeq;
    const list = $("#search-results");
    if (q.length < 2) {
      list.textContent = "";
      $("#search-count").textContent = "";
      return;
    }
    const results = await getJSON(api(`/search?q=${encodeURIComponent(q)}`));
    if (seq !== searchSeq) return;
    list.textContent = "";
    $("#search-count").textContent = results.length
      ? `${results.length}${results.length >= 200 ? "+" : ""} result${results.length === 1 ? "" : "s"}`
      : "No results";
    for (const r of results) {
      const li = document.createElement("li");
      const b = document.createElement("button");
      const title = document.createElement("span");
      title.className = "r-title";
      title.textContent = r.title;
      const snip = document.createElement("span");
      snip.className = "r-snip";
      const mark = document.createElement("mark");
      mark.textContent = r.match;
      snip.append(r.before, mark, r.after);
      b.append(title, snip);
      b.addEventListener("click", async () => {
        closeSheets();
        await jump(r.chapter, r.segment);
        showHit(r.segment, q);
      });
      li.append(b);
      list.append(li);
    }
  }

  // Mark the search term inside the paragraph and turn to the page it's on.
  function showHit(i, q) {
    const el = segs[i];
    if (!el) return;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const needle = q.toLowerCase();
    let node;
    while ((node = walker.nextNode())) {
      const at = node.data.toLowerCase().indexOf(needle);
      if (at < 0) continue;
      const range = document.createRange();
      range.setStart(node, at);
      range.setEnd(node, at + q.length);
      const mark = document.createElement("mark");
      mark.className = "hit";
      range.surroundContents(mark);
      go(pageRange(mark)[0], false);
      setTimeout(() => {
        mark.replaceWith(...mark.childNodes);
        el.normalize();
      }, 4000);
      return;
    }
    el.classList.add("flash");
    setTimeout(() => el.classList.remove("flash"), 2500);
  }

  function applySettings(layout = true) {
    const root = document.documentElement;
    root.dataset.theme = settings.theme;
    root.style.setProperty("--size", `${settings.size}px`);
    root.style.setProperty("--font", FONTS[settings.font] || FONTS.original);
    root.style.setProperty("--spacing", settings.spacing);
    $("#size-label").textContent = `${Math.round((settings.size / 19) * 100)}%`;
    document.querySelectorAll("#themes button").forEach((b) => b.classList.toggle("active", b.dataset.theme === settings.theme));
    document.querySelectorAll("#fonts button").forEach((b) => b.classList.toggle("active", b.dataset.font === settings.font));
    document.querySelectorAll("#spacing button").forEach((b) => b.classList.toggle("active", b.dataset.spacing === settings.spacing));
    // iOS only notices a new status bar color when the meta tag is replaced, not edited.
    const meta = document.querySelector('meta[name="theme-color"]');
    const fresh = meta.cloneNode();
    fresh.content = getComputedStyle(root).getPropertyValue("--bg").trim();
    meta.replaceWith(fresh);
    document.cookie = `reader_theme=${settings.theme}; path=/books; max-age=34560000; samesite=lax; secure`;
    try {
      localStorage.setItem("reader-settings", JSON.stringify(settings));
    } catch {}
    if (layout) relayout();
  }

  $("#smaller").addEventListener("click", () => {
    settings.size = Math.max(SIZE_MIN, settings.size - 1);
    applySettings();
  });
  $("#larger").addEventListener("click", () => {
    settings.size = Math.min(SIZE_MAX, settings.size + 1);
    applySettings();
  });
  document.querySelectorAll("#themes button").forEach((b) => b.addEventListener("click", () => {
    settings.theme = b.dataset.theme;
    applySettings(false);
  }));
  document.querySelectorAll("#fonts button").forEach((b) => b.addEventListener("click", () => {
    settings.font = b.dataset.font;
    applySettings();
  }));
  document.querySelectorAll("#spacing button").forEach((b) => b.addEventListener("click", () => {
    settings.spacing = b.dataset.spacing;
    applySettings();
  }));

  // ---------- downloads and audio status ----------

  let audioReady = new Set();

  async function refreshAudioStatus() {
    const status = await getJSON(api("/audio-status"));
    audioReady = new Set(status.ready);
    return status;
  }

  function setLink(el, href, enabled) {
    el.href = href;
    el.classList.toggle("disabled", !enabled);
  }

  function updateChapterDownload() {
    setLink($("#dl-chapter-mp3"), api(`/download.mp3?chapter=${chapter}`), audioReady.has(chapter));
  }

  async function refreshAudioSummary() {
    const s = await refreshAudioStatus();
    const done = s.ready.length;
    let text = done === s.total ? "Audiobook is fully narrated." : `Audio: ${done} of ${s.total} sections narrated.`;
    if (s.working) {
      const pct = Math.floor((s.working.segment / s.working.segments) * 100);
      text += ` Narrating “${book.chapters[s.working.chapter].title}” now (${pct}%).`;
    }
    $("#audio-summary").textContent = text;
    setLink($("#dl-book-mp3"), api("/download.mp3"), done > 0);
    $("#dl-book-mp3").textContent = done === s.total || done === 0 ? "Download audiobook (MP3)" : `Download audiobook so far (MP3, ${done}/${s.total})`;
    updateChapterDownload();
  }

  // ---------- narration ----------

  let listening = false;
  let audioChapter = -1;
  let timing = null;
  let curSeg = -1;
  let followPage = -1;
  let waitTimer;
  let unlocking = false;
  const silence = makeSilence();

  // iOS only lets a page start audio from a tap. Playing a blip of silence inside the tap
  // unlocks the <audio> element, so later chapters (and waits for narration) can play on their own.
  function makeSilence() {
    const n = 2400;
    const buf = new ArrayBuffer(44 + n * 2);
    const v = new DataView(buf);
    const str = (o, s) => [...s].forEach((c, i) => v.setUint8(o + i, c.charCodeAt(0)));
    str(0, "RIFF");
    v.setUint32(4, 36 + n * 2, true);
    str(8, "WAVE");
    str(12, "fmt ");
    v.setUint32(16, 16, true);
    v.setUint16(20, 1, true);
    v.setUint16(22, 1, true);
    v.setUint32(24, 24000, true);
    v.setUint32(28, 48000, true);
    v.setUint16(32, 2, true);
    v.setUint16(34, 16, true);
    str(36, "data");
    v.setUint32(40, n * 2, true);
    return URL.createObjectURL(new Blob([buf], { type: "audio/wav" }));
  }

  function setStatus(text) {
    $("#player-status").textContent = text;
  }

  function fmt(t) {
    t = Math.max(0, Math.floor(t));
    const h = Math.floor(t / 3600);
    const m = Math.floor((t % 3600) / 60);
    const s = String(t % 60).padStart(2, "0");
    return h ? `${h}:${String(m).padStart(2, "0")}:${s}` : `${m}:${s}`;
  }

  function onListenButton() {
    if (listening && audioChapter === chapter && segs[curSeg]) {
      const [a, b] = pageRange(segs[curSeg]);
      if (page >= a && page <= b) return audio.paused ? audio.play() : audio.pause();
    }
    startListening(chapter, segStartingOn(page));
  }

  function startListening(n, seg) {
    hideChrome();
    if (!listening || !audio.src) {
      unlocking = true;
      audio.src = silence;
      audio.play().catch(() => {});
    }
    if (!listening) {
      listening = true;
      document.body.classList.add("listening");
      $("#player").hidden = false;
      relayout();
    }
    playChapter(n, seg);
  }

  function stopListening() {
    listening = false;
    clearTimeout(waitTimer);
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
    timing = null;
    audioChapter = -1;
    if (segs[curSeg]) segs[curSeg].classList.remove("reading");
    curSeg = -1;
    document.body.classList.remove("listening");
    $("#player").hidden = true;
    relayout();
  }

  // Sections are playable while they're still being narrated: the timing then has
  // complete: false and covers only the paragraphs written so far.
  async function playChapter(n, seg = 0) {
    clearTimeout(waitTimer);
    audioChapter = n;
    timing = null;
    followPage = -1;
    setStatus("Loading audio…");
    let t = null;
    try {
      t = await getJSON(api(`/audio/${n}.json`));
    } catch (e) {
      if (audioChapter !== n || !listening) return;
      if (e.status !== 404) {
        setStatus("Couldn't load audio; retrying…");
        waitTimer = setTimeout(() => playChapter(n, seg), 5000);
        return;
      }
    }
    if (audioChapter !== n || !listening) return;
    if (t && t.complete !== false && !t.starts.length) return advance(n);
    if (!t || (t.complete === false && t.starts.length <= seg)) return waitFor(n, seg, () => playChapter(n, seg));
    if (t.complete !== false) audioReady.add(n);
    load(n, t, t.starts[Math.min(seg, t.starts.length - 1)] || 0);
  }

  async function load(n, t, at) {
    timing = t;
    unlocking = false;
    audio.src = api(`/audio/${n}.mp3`) + (t.complete === false ? `?bytes=${t.bytes}` : "");
    audio.defaultPlaybackRate = settings.speed;
    audio.playbackRate = settings.speed;
    const loaded = await new Promise((done) => {
      audio.addEventListener("loadedmetadata", () => done(true), { once: true });
      audio.addEventListener("error", () => done(false), { once: true });
    });
    if (audioChapter !== n || !listening) return;
    if (!loaded) {
      setStatus("Couldn't load audio; retrying…");
      waitTimer = setTimeout(() => continuePartial(n, at), 4000);
      return;
    }
    audio.currentTime = at;
    audio.playbackRate = settings.speed;
    audio.play().catch(() => setStatus("Tap play to start"));
    updateMediaSession();
  }

  // Ask for this section to be narrated next and check back until paragraph `seg` exists.
  async function waitFor(n, seg, retry) {
    fetch(api("/listen"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chapter: n }) });
    const s = await refreshAudioStatus().catch(() => null);
    if (audioChapter !== n || !listening) return;
    const w = s && s.working;
    let text = "Queued for narration; plays when ready";
    if (w && w.chapter === n) {
      const eta = w.seconds_per_segment ? (seg - w.segment) * w.seconds_per_segment : 0;
      text = eta > 90 ? `Narration reaches this page in about ${Math.round(eta / 60)} min` : "Narrating; starts in a moment…";
    }
    setStatus(text);
    waitTimer = setTimeout(retry, 3000);
  }

  // Reached the end of what's been narrated so far: pick up the newly written audio.
  async function continuePartial(n, at) {
    let t = null;
    try {
      t = await getJSON(api(`/audio/${n}.json`));
    } catch {}
    if (audioChapter !== n || !listening) return;
    if (t && (t.complete !== false || t.duration > at + 1)) return load(n, t, at);
    const seg = timing.starts.length;
    waitFor(n, seg, () => continuePartial(n, at));
  }

  async function advance(n) {
    const next = n + 1;
    if (next >= book.chapters.length) return stopListening();
    if (chapter === n) await jump(next, 0); // turn along with the narration when the reader is following it
    playChapter(next, 0);
  }

  audio.addEventListener("ended", () => {
    if (unlocking || !listening || !timing) return;
    if (timing.complete === false) continuePartial(audioChapter, audio.currentTime);
    else advance(audioChapter);
  });

  audio.addEventListener("timeupdate", () => {
    if (!timing || unlocking) return;
    const t = audio.currentTime;
    let i = 0;
    while (i + 1 < timing.starts.length && timing.starts[i + 1] <= t) i++;
    if (chapter === audioChapter) {
      if (i !== curSeg) {
        if (segs[curSeg]) segs[curSeg].classList.remove("reading");
        if (segs[i]) segs[i].classList.add("reading");
      }
      follow(i, t);
    }
    curSeg = i;
    const title = book.chapters[audioChapter].title;
    setStatus(`${title} · ${fmt(t)} / ${fmt(timing.duration)}${timing.complete === false ? "+" : ""}`);
  });

  // Turn pages along with the narration, but only when the narration itself reaches a new page,
  // so flipping ahead or back while listening isn't undone every second.
  function follow(i, t) {
    const el = segs[i];
    if (!el) return;
    const [a, b] = pageRange(el);
    let target = a;
    if (b > a) {
      const end = timing.starts[i + 1] ?? timing.duration;
      const frac = (t - timing.starts[i]) / Math.max(0.1, end - timing.starts[i]);
      target = a + Math.min(b - a, Math.floor(frac * (b - a + 1)));
    }
    if (target !== followPage) {
      followPage = target;
      if (target !== page) go(target);
    }
  }

  const ICON_PLAY = '<svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor" aria-hidden="true"><path d="M7 4.5v15l13-7.5z"/></svg>';
  const ICON_PAUSE = $("#playpause").innerHTML;
  audio.addEventListener("play", () => {
    if (unlocking) return;
    $("#playpause").innerHTML = ICON_PAUSE;
    $("#playpause").setAttribute("aria-label", "Pause");
  });
  audio.addEventListener("pause", () => {
    $("#playpause").innerHTML = ICON_PLAY;
    $("#playpause").setAttribute("aria-label", "Play");
  });

  function skip(seconds) {
    if (!timing) return;
    audio.currentTime = Math.max(0, Math.min(timing.duration - 0.5, audio.currentTime + seconds));
  }

  $("#listen-fab").addEventListener("click", onListenButton);
  $("#listen-top").addEventListener("click", onListenButton);
  $("#playpause").addEventListener("click", () => {
    if (!timing || unlocking) return; // nothing narrated to play yet
    if (audio.paused) audio.play();
    else audio.pause();
  });
  $("#back15").addEventListener("click", () => skip(-15));
  $("#fwd15").addEventListener("click", () => skip(15));
  $("#stop").addEventListener("click", stopListening);
  $("#speed").addEventListener("click", () => {
    settings.speed = SPEEDS[(SPEEDS.indexOf(settings.speed) + 1) % SPEEDS.length] || 1;
    audio.playbackRate = settings.speed;
    audio.defaultPlaybackRate = settings.speed;
    $("#speed").textContent = `${settings.speed}×`;
    applySettings(false);
  });
  $("#speed").textContent = `${settings.speed}×`;

  function updateMediaSession() {
    if (!("mediaSession" in navigator)) return;
    navigator.mediaSession.metadata = new MediaMetadata({
      title: book.chapters[audioChapter].title,
      artist: book.author,
      album: book.title,
      artwork: book.cover ? [{ src: new URL(book.cover, location.href).href }] : [],
    });
  }

  if ("mediaSession" in navigator) {
    const handlers = {
      play: () => audio.play(),
      pause: () => audio.pause(),
      seekbackward: () => skip(-15),
      seekforward: () => skip(15),
      seekto: (d) => {
        audio.currentTime = d.seekTime;
      },
      previoustrack: () => {
        if (audioChapter > 0) {
          if (chapter === audioChapter) jump(audioChapter - 1, 0);
          playChapter(audioChapter - 1, 0);
        }
      },
      nexttrack: () => listening && advance(audioChapter),
    };
    for (const [action, fn] of Object.entries(handlers)) {
      try {
        navigator.mediaSession.setActionHandler(action, fn);
      } catch {}
    }
  }

  // ---------- start ----------

  async function init() {
    applySettings(false);
    book = await getJSON(api());
    let sum = 0;
    prefix = book.chapters.map((c) => {
      const before = sum;
      sum += c.chars;
      return before;
    });
    totalChars = Math.max(1, sum);
    audioReady = new Set(book.audio.ready);
    const p = book.progress || { chapter: 0, segment: 0 };
    await openChapter(p.chapter, { segment: p.segment });
    if (!book.progress) document.body.classList.add("chrome");
  }

  init();
})();
