(() => {
  "use strict";

  // Opened by the "Import to Library" bookmarklet (see library.js) on a story's site. Relays
  // between it and the importer: the importer names the pages it still needs, the bookmarklet
  // fetches them, and this sends them back until the book can be built.
  const SITES = /^https:\/\/([\w-]+\.)*(royalroad\.com|spacebattles\.com|sufficientvelocity\.com|questionablequesting\.com)$/;
  const status = document.getElementById("status");
  const bar = document.getElementById("progress");
  let site = null; // origin of the story's site, once the bookmarklet says hello
  let session = null;

  function show(text, isError = false, fraction = null) {
    status.textContent = text;
    status.classList.toggle("err", isError);
    bar.hidden = fraction == null;
    if (fraction != null) bar.firstChild.style.width = `${fraction * 100}%`;
  }

  async function round(body) {
    const r = await fetch("/books/api/import-pages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) return show(`Couldn't import: ${data.detail || `error ${r.status}`}`, true);
    if (data.need) {
      session = data.session;
      window.opener.postMessage({ type: "need", urls: data.need }, site);
      return;
    }
    for (;;) {
      const job = (await (await fetch("/books/api/imports")).json()).find((j) => j.id === data.id);
      if (!job) return show("Finished. Check your library.");
      const name = job.title ? `“${job.title}”` : "the book";
      const chapters = (n) => `${n} ${job.update ? "new " : ""}chapter${n === 1 ? "" : "s"}`;
      if (job.status === "done" && job.update) {
        return show(`${job.new ? `Added ${chapters(job.new)} to ${name}.` : `${name} has no new chapters.`} You can close this window.`);
      }
      if (job.status === "done") return show(`Added “${job.title}” to your library. You can close this window.`);
      if (job.status === "error") return show(`Couldn't import: ${job.error}`, true);
      const verb = job.update ? "Updating" : "Building";
      show(job.total ? `${verb} ${name} · ${job.done} of ${chapters(job.total)}` : `${verb} ${name}…`, false, job.total ? job.done / job.total : null);
      await new Promise((res) => setTimeout(res, 2000));
    }
  }

  const lost = () => show("Lost contact with the library. Try the bookmark again.", true);

  addEventListener("message", (e) => {
    if (e.source !== window.opener || !SITES.test(e.origin) || (site && e.origin !== site)) return;
    const msg = e.data || {};
    if (msg.type === "start") {
      site = e.origin;
      show("Looking at the story…");
      round({ url: msg.url }).catch(lost);
    } else if (msg.type === "progress") {
      show(`Fetching page ${msg.done + 1} of ${msg.total} from ${new URL(site).hostname}…`, false, msg.done / msg.total);
    } else if (msg.type === "pages") {
      show("Reading the pages…");
      round({ session, pages: msg.pages }).catch(lost);
    } else if (msg.type === "error") {
      show(`Couldn't import: ${msg.message}`, true);
    }
  });

  if (window.opener) window.opener.postMessage("ready", "*");
  else show("Open a story and use the Import to Library bookmark there.", true);
})();
