// Plays a whole game of Sketch Relay in three headless browsers (one of them phone-sized, drawing by
// touch). The host makes a room and the others join by its link; everyone writes, draws with the
// pointer and guesses; one player reloads mid-step and must get their job back; the host reads the
// books out and everyone must see the same pages, drawings included; then the album and back to the
// lobby. Fails if a page throws or logs an error, or any step doesn't happen in time. About 15 s.
//
//     node tools/relay-smoke.js [http://localhost:8080]    against a running server
//     node tools/relay-smoke.js --serve                    starts its own (tools/check-all.sh does this)
//     ... --shots <folder>                                 also saves a screenshot of each screen
//
// With --serve it exits 77 ("skipped") when Playwright or its browser isn't installed here.
const { spawn } = require('child_process');
const net = require('net');
const path = require('path');

const args = process.argv.slice(2);
const SERVE = args.includes('--serve');
const SHOTS = args.includes('--shots') ? args[args.indexOf('--shots') + 1] : null;
let BASE = args.find(a => a.startsWith('http')) || 'http://localhost:8080';
const skip = why => { console.log('skipped: ' + why); process.exit(77); };

let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { if (SERVE) skip('Playwright is not installed'); throw e; }

const freePort = () => new Promise(res => {
  const s = net.createServer();
  s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => res(p)); });
});

async function serve() {
  const port = await freePort();
  const os = require('os'), fs = require('fs');
  const data = fs.mkdtempSync(path.join(os.tmpdir(), 'relay-smoke-'));
  const proc = spawn('python3', ['-m', 'uvicorn', 'app.main:app', '--port', String(port), '--log-level', 'warning'],
    { cwd: path.join(__dirname, '..'), env: { ...process.env, DATA_DIR: data }, stdio: ['ignore', 'inherit', 'inherit'] });
  BASE = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 80; i++) {
    try { const r = await fetch(BASE + '/healthz'); if (r.ok) return proc; } catch (e) { /* not up yet */ }
    await new Promise(r => setTimeout(r, 250));
  }
  proc.kill();
  throw new Error('the server did not start');
}

(async () => {
  const server = SERVE ? await serve() : null;
  let browser;
  try { browser = await chromium.launch(); } catch (e) {
    if (server) server.kill();
    if (SERVE) skip("Playwright's browser is not installed");
    throw e;
  }
  const problems = [];
  let code = 1;
  setTimeout(() => { console.log('FAILED: still running after two minutes'); if (server) server.kill(); process.exit(1); }, 120000).unref();

  const open = async (who, url, phone = false) => {
    // its own storage: a separate player
    const ctx = await browser.newContext(phone ? { viewport: { width: 390, height: 780 }, hasTouch: true, isMobile: true }
      : { viewport: { width: 1100, height: 800 } });
    const p = await ctx.newPage();
    p.who = who;
    p.on('pageerror', e => problems.push(`${who}: ${e.message}`));
    p.on('console', m => { if (m.type() === 'error' && !m.text().includes('Failed to load resource')) problems.push(`${who}: ${m.text()}`); });
    p.setDefaultTimeout(10000);
    await p.goto(url);
    await p.fill('#name', who);
    return p;
  };
  const shot = async (p, name) => {
    if (SHOTS) await p.screenshot({ path: path.join(SHOTS, `${name}.png`), fullPage: true });
  };
  const state = p => p.evaluate(() => window.relay.S.st);
  const job = p => p.evaluate(() => { const { S } = window.relay; return S.task && !S.task.done && S.task.step === S.st.step ? S.task.kind : null; });
  // how much of a canvas isn't white
  const inked = (p, sel) => p.evaluate(s => {
    const c = document.querySelector(s);
    const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
    let n = 0;
    for (let i = 0; i < d.length; i += 4) if (d[i] + d[i + 1] + d[i + 2] < 720) n++;
    return n;
  }, sel);

  // Draw a zigzag on the pad, by mouse or (on the phone) by touch.
  const scribble = async (p, touch) => {
    const box = await p.locator('#pad').boundingBox();
    const at = (fx, fy) => [box.x + box.width * fx, box.y + box.height * fy];
    const pts = [[0.2, 0.3], [0.4, 0.7], [0.6, 0.3], [0.8, 0.7]];
    if (touch) {
      // Playwright's touchscreen only taps, so send the pointer events a finger would
      await p.evaluate(points => {
        const pad = document.getElementById('pad');
        const fire = (type, [x, y]) => pad.dispatchEvent(new PointerEvent(type, { pointerId: 7, pointerType: 'touch', clientX: x, clientY: y, bubbles: true, cancelable: true }));
        fire('pointerdown', points[0]);
        for (const pt of points.slice(1)) fire('pointermove', pt);
        fire('pointerup', points[points.length - 1]);
      }, pts.map(([x, y]) => at(x, y)));
    } else {
      await p.mouse.move(...at(...pts[0]));
      await p.mouse.down();
      for (const pt of pts.slice(1)) await p.mouse.move(...at(...pt), { steps: 6 });
      await p.mouse.up();
    }
  };

  try {
    const host = await open('Ada', `${BASE}/games/sketch-relay?debug`);
    await shot(host, '1-menu');
    await host.click('#create');
    await host.waitForSelector('#lobby:not([hidden])');
    const room = await host.textContent('#room-code');
    if (!/^[A-Z]{4}$/.test(room)) throw new Error(`odd room code "${room}"`);
    if (!await host.isDisabled('#start')) throw new Error('one player could start a game');

    const link = `${BASE}/games/sketch-relay?debug&room=${room}`;
    const bo = await open('Bo', link);
    await bo.click('#join');
    const cy = await open('Cy', link, true);
    await cy.click('#join');
    const all = [host, bo, cy];
    await host.waitForFunction(() => document.querySelectorAll('#seats li').length === 3);
    if (await bo.isVisible('#start')) throw new Error('a guest was offered the Start button');
    await host.selectOption('#timer', 'relaxed');
    await cy.waitForFunction(() => document.getElementById('timer').value === 'relaxed');
    await shot(host, '2-lobby');
    await shot(cy, '2-lobby-phone');
    await host.click('#start');

    // Step 1: everyone writes (Bo takes one of the ideas).
    for (const p of all) await p.waitForSelector('#write:not([hidden])');
    await shot(cy, '3-write-phone');
    await host.fill('#write-text', 'A cat filing its taxes');
    await host.press('#write-text', 'Enter');
    await host.waitForSelector('#waiting:not([hidden])');
    await shot(host, '3-waiting');
    await bo.click('#ideas button');
    if (!await bo.inputValue('#write-text')) throw new Error('picking an idea filled nothing in');
    await bo.click('#write button[type=submit]');
    await cy.fill('#write-text', 'A haunted toaster');
    await cy.click('#write button[type=submit]');

    // Step 2: everyone draws. Bo reloads half way and must get the same job back.
    for (const p of all) await p.waitForSelector('#draw:not([hidden])');
    const prompt = await bo.textContent('#draw-prompt');
    await bo.goto(link);   // a reload (the room link, with the name already saved)
    await bo.waitForSelector('#draw:not([hidden])');
    if (await bo.textContent('#draw-prompt') !== prompt) throw new Error('a reload changed the prompt to draw');
    for (const p of all) {
      await p.click('#colors button[aria-label="Red"]');
      await scribble(p, p === cy);
      await p.click('#widths button[aria-label="Thick brush"]');
      await p.click('#colors button[aria-label="Blue"]');
      await scribble(p, p === cy);
      const strokes = await p.evaluate(() => window.relay.pad.strokes.length);
      if (strokes !== 2) throw new Error(`${p.who}: ${strokes} strokes on the pad after drawing two`);
      if (!await inked(p, '#pad')) throw new Error(`${p.who}: nothing showed on the pad`);
    }
    // undo, clear, and undo the clear
    await host.click('#undo');
    await host.click('#clear');
    if (await inked(host, '#pad')) throw new Error('Clear left ink on the pad');
    await host.click('#undo');
    if (await host.evaluate(() => window.relay.pad.strokes.length) !== 1) throw new Error("Undo didn't bring back a cleared drawing");
    await shot(host, '4-draw');
    await shot(cy, '4-draw-phone');
    for (const p of all) await p.click('#draw-done');

    // Step 3: everyone guesses what they were handed.
    for (const p of all) {
      await p.waitForSelector('#guess:not([hidden])');
      await p.waitForFunction(() => { const c = document.getElementById('guess-sheet'); return c.width > 300; });
    }
    await host.waitForTimeout(1500);   // the drawing is replayed
    for (const p of all) if (!await inked(p, '#guess-sheet')) throw new Error(`${p.who}: was handed a blank drawing`);
    await shot(bo, '5-guess');
    await shot(cy, '5-guess-phone');
    // Cy doesn't answer: the host moves on without them.
    await host.fill('#guess-text', 'Lightning over the sea');
    await host.press('#guess-text', 'Enter');
    await bo.fill('#guess-text', 'A very angry heartbeat');
    await bo.press('#guess-text', 'Enter');
    await host.waitForSelector('#hurry:not([hidden])');
    if (await bo.isVisible('#hurry')) throw new Error('a guest was offered "Move on without them"');
    await host.click('#hurry');

    // The books are read out: each press of Next shows one more page to everyone.
    for (const p of all) await p.waitForSelector('#books:not([hidden])');
    let pages = 0, timedOut = 0;
    for (let book = 0; book < 3; book++) {
      for (let shown = 1; shown <= 3; shown++) {
        for (const p of all) {
          await p.waitForFunction(([b, n]) => {
            const st = window.relay.S.st;
            return st.reveal && st.reveal[0] === b && st.reveal[1] === n && document.querySelectorAll('#pages li').length === n;
          }, [book, shown]);
        }
        pages++;
        if (shown === 2) {
          await host.waitForTimeout(1700);
          for (const p of all) if (!await inked(p, '#pages li:last-child canvas')) throw new Error(`${p.who}: a drawing in book ${book + 1} came out blank`);
        }
        if (shown === 3) {
          timedOut += (await host.textContent('#pages li:last-child .by')).includes('ran out of time') ? 1 : 0;
          if (book === 0) { await shot(host, '6-reveal'); await shot(cy, '6-reveal-phone'); }
        }
        if (await bo.isVisible('#next')) throw new Error('a guest was offered the Next button');
        await host.click('#next');
      }
    }
    if (timedOut !== 1) throw new Error(`${timedOut} guesses were marked as out of time, not Cy's one`);

    // The album: every book, to flip through and save; then back to the lobby.
    for (const p of all) await p.waitForSelector('#tabs:not([hidden])');
    if (await host.locator('#tabs button').count() !== 3) throw new Error('the album is missing a book');
    await cy.click('#tabs button:nth-child(2)');
    await cy.waitForFunction(() => document.querySelectorAll('#pages li').length === 3);
    const [download] = await Promise.all([cy.waitForEvent('download'), cy.click('#save')]);
    if (!/^sketch-relay-.+\.png$/.test(download.suggestedFilename())) throw new Error(`odd file name ${download.suggestedFilename()}`);
    await shot(host, '7-album');
    await shot(cy, '7-album-phone');
    await host.click('#again');
    for (const p of all) await p.waitForSelector('#lobby:not([hidden])');
    if ((await state(bo)).players.length !== 3) throw new Error('someone was lost on the way back to the lobby');

    // A room that doesn't exist.
    const lost = await open('Dee', `${BASE}/games/sketch-relay?room=QQQQ`);
    await lost.click('#join');
    await lost.waitForFunction(() => document.getElementById('status').textContent.includes('no room'));

    if (problems.length) throw new Error('page errors:\n  ' + problems.join('\n  '));
    console.log(`ok: three players wrote, drew and guessed; ${pages} pages read out; album and replay work`);
    code = 0;
  } catch (e) {
    console.log('FAILED: ' + e.message);
    if (problems.length) console.log('page errors:\n  ' + problems.join('\n  '));
  }
  await browser.close();
  if (server) server.kill();
  process.exit(code);
})();
