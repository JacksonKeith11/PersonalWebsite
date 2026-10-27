(() => {
  "use strict";

  // Opened by the "Import to Library" bookmarklet (see library.js) on a Royal Road page, which
  // sends the pages it fetched once this page says it's ready.
  const ROYAL_ROAD = /^https:\/\/(www\.)?royalroad\.com$/;
  const status = document.getElementById("status");
  const bar = document.getElementById("progress");
  let busy = false;

  function show(text, isError = false, fraction = null) {
    status.textContent = text;
    status.classList.toggle("err", isError);
    bar.hidden = fraction == null;
    if (fraction != null) bar.firstChild.style.width = `${fraction * 100}%`;
  }

  async function build(msg) {
    busy = true;
    show("Sending the chapters to your library…");
    const r = await fetch("/books/api/import-pages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: msg.url, pages: msg.pages }),
    });
    if (!r.ok) {
      const detail = await r.json().catch(() => ({}));
      return show(`Couldn't import: ${detail.detail || `error ${r.status}`}`, true);
    }
    const { id } = await r.json();
    for (;;) {
      const job = (await (await fetch("/books/api/imports")).json()).find((j) => j.id === id);
      if (!job) return show("Finished. Check your library.");
      if (job.status === "done") return show(`Added “${job.title}” to your library. Narration has started; you can close this window.`);
      if (job.status === "error") return show(`Couldn't import: ${job.error}`, true);
      const name = job.title ? `“${job.title}”` : "the book";
      show(job.total ? `Building ${name} · ${job.done} of ${job.total} chapters` : `Building ${name}…`, false, job.total ? job.done / job.total : null);
      await new Promise((res) => setTimeout(res, 2000));
    }
  }

  addEventListener("message", (e) => {
    if (e.source !== window.opener || !ROYAL_ROAD.test(e.origin) || busy) return;
    const msg = e.data || {};
    if (msg.type === "progress") show(`Fetching chapter ${msg.done + 1} of ${msg.total} from Royal Road…`, false, msg.done / msg.total);
    else if (msg.type === "error") show(`Couldn't import: ${msg.message}`, true);
    else if (msg.type === "pages") build(msg).catch(() => show("Lost contact with the library. Try the bookmark again.", true));
  });

  if (window.opener) window.opener.postMessage("ready", "*");
  else show("Open a story on Royal Road and use the Import to Library bookmark there.", true);
})();
