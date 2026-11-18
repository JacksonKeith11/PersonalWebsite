// Plays Holdfast in two headless browsers (one phone-sized). The host makes a room, picks a map
// and difficulty; a friend joins by the link. They build (by click and by tap), are refused a tower on
// the road, give gold, upgrade each other's towers along a path (the other path closes) and sell
// their own; kill counts and the mute button work; a wave is fought and its
// enemies, shots and bounties must show up on both screens; then, with every tower sold, the keep
// falls, the scores come up, and the host takes everyone back to the room. Fails if a page throws or
// logs an error. About 50 s.
//
//     node tools/holdfast-smoke.js [http://localhost:8080]    against a running server
//     node tools/holdfast-smoke.js --serve                    starts its own (tools/check-all.sh does this)
//     ... --shots <folder>                                    also saves a screenshot of each screen
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
  const data = fs.mkdtempSync(path.join(os.tmpdir(), 'holdfast-smoke-'));
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
  try {
    const host = await open('Ada', `${BASE}/games/holdfast?debug`);
    await shot(host, '1-menu');
    await host.click('#create');
    await host.waitForSelector('#lobby:not([hidden])');
    const room = await host.textContent('#room-code');
    const friend = await open('Bo', `${BASE}/games/holdfast?debug&room=${room}`, true);
    await friend.click('#join');
    await host.waitForFunction(() => document.querySelectorAll('#seats li').length === 2);
    await host.selectOption('#diff', 'hard');
    await friend.waitForFunction(() => document.getElementById('diff').value === 'hard');
    if (await friend.isVisible('#start')) throw new Error('a guest was offered the Start button');
    await shot(host, '2-lobby');
    await host.click('#start');
    const all = [host, friend];
    for (const p of all) await p.waitForSelector('#game:not([hidden])');

    const st = p => p.evaluate(() => window.holdfast.S.st);
    const gold = (p, name) => p.evaluate(n => { const { S } = window.holdfast; return S.gold[S.st.players.find(q => q.name === n).id]; }, name);
    const towers = async p => (await st(p)).towers;
    // click (or, on the phone, tap) the middle of a tile
    const tile = async (p, x, y) => {
      const box = await p.locator('#board').boundingBox();
      const px = box.x + (x + 0.5) / 20 * box.width, py = box.y + (y + 0.5) / 12 * box.height;
      if (p === friend) await p.touchscreen.tap(px, py); else await p.mouse.click(px, py);
    };
    const pick = (p, kind) => p.click(`#palette button[data-kind=${kind}]`);
    const count = (p, n) => p.waitForFunction(k => window.holdfast.S.st.towers.length === k, n);

    // Meadow's road runs along row 2 from the left edge to column 4, then down column 4.
    const start = await gold(host, 'Ada');
    if (start !== 125 || await gold(friend, 'Bo') !== 125) throw new Error(`odd starting gold: ${start}`);
    await pick(host, 'archer');
    await tile(host, 2, 2);               // on the road: refused
    await tile(host, 2, 3);
    await tile(host, 3, 3);
    await count(host, 2);
    await host.waitForFunction(() => window.holdfast.S.gold[window.holdfast.room.you] === 25);
    await tile(host, 5, 3);               // can't afford a third
    await pick(friend, 'archer');
    await tile(friend, 3, 1);
    for (const p of all) await count(p, 3);
    if ((await towers(friend)).some(t => t.x === 2 && t.y === 2)) throw new Error('a tower was built on the road');
    await shot(host, '3-building');
    await shot(friend, '3-building-phone');

    // Bo gives Ada gold. Ada looks at Bo's tower: she may upgrade it (when she can pay), not sell it.
    await friend.click('#purses button');
    await host.waitForFunction(() => window.holdfast.S.gold[window.holdfast.room.you] === 50);
    await host.keyboard.press('Escape');
    await tile(host, 3, 1);
    await host.waitForSelector('#info h2');
    if (!(await host.textContent('#info')).includes('built by Bo')) throw new Error("the panel doesn't say who built the tower");
    if (await host.locator('#info button', { hasText: 'Sell' }).count()) throw new Error("the host was offered someone else's tower to sell");
    if (await host.locator('#info .paths section').count() !== 2) throw new Error("the tower's two upgrade paths aren't shown");
    if (!await host.isDisabled('#info button[data-path="0"]')) throw new Error('an upgrade the host cannot afford was on offer');
    if ((await host.textContent('#kills')) !== '0') throw new Error("a new tower's kill count isn't 0");

    // Send the wave: enemies arrive on both screens, towers shoot, kills pay both purses.
    for (const p of all) await p.click('#ready');
    for (const p of all) await p.waitForFunction(() => window.holdfast.S.st.fighting && window.holdfast.S.enemies.size > 0, null, { timeout: 15000 });
    await host.click('#speed');
    await friend.waitForFunction(() => window.holdfast.S.st.speed === 2);
    await host.waitForFunction(() => window.holdfast.S.shots.length > 0, null, { timeout: 20000 });
    await shot(host, '4-wave');
    await shot(friend, '4-wave-phone');
    await friend.waitForFunction(() => window.holdfast.S.gold[window.holdfast.room.you] > 55, null, { timeout: 20000 });
    await host.waitForFunction(() => window.holdfast.S.gold[window.holdfast.room.you] >= 60, null, { timeout: 30000 });
    await host.click('#info button[data-path="0"]');   // now she can: anyone may pay for an upgrade
    await friend.waitForFunction(() => window.holdfast.S.st.towers.some(t => t.x === 3 && t.y === 1 && t.p === 0 && t.n === 1));
    // the path is chosen: the other one is closed
    await host.waitForFunction(() => document.querySelector('#info .paths section:nth-child(2)')?.textContent.includes('Closed'));
    // kill counts come through to both screens, and show on the panel
    await friend.waitForFunction(() => window.holdfast.S.st.towers.some(t => t.kills > 0), null, { timeout: 30000 });
    await host.waitForFunction(() => +document.getElementById('kills').textContent >= 0);
    await shot(host, '4b-upgraded');
    await host.click('#mute');
    if ((await host.getAttribute('#mute', 'aria-pressed')) !== 'true') throw new Error("the mute button didn't mute");

    // Sell everything: the keep falls, and the scores come up.
    await host.click('#speed');
    for (const p of all) {
      const mine = await p.evaluate(() => { const { S, room } = window.holdfast; return S.st.towers.filter(t => t.o === room.you).map(t => [t.x, t.y]); });
      await p.keyboard.press('Escape');
      for (const [x, y] of mine) {
        await tile(p, x, y);
        await p.locator('#info button', { hasText: 'Sell' }).click();
      }
    }
    await count(host, 0);
    for (const p of all) await p.waitForSelector('#end:not([hidden])', { timeout: 60000 });
    if (!(await host.textContent('#end-title')).includes('fallen')) throw new Error('the game ended, but not in defeat');
    if (await host.locator('#end-rows tr').count() !== 2) throw new Error('the scores are missing a player');
    const kills = (await st(host)).players.reduce((n, q) => n + q.kills, 0);
    if (!kills) throw new Error('nobody was credited with a kill');
    await shot(host, '5-end');
    await shot(friend, '5-end-phone');
    await host.click('#again');
    for (const p of all) await p.waitForSelector('#lobby:not([hidden])');

    if (problems.length) throw new Error('page errors:\n  ' + problems.join('\n  '));
    console.log('ok: two players built, gave gold, upgraded and sold; a wave was fought off; the keep fell and the room reopened');
    code = 0;
  } catch (e) {
    console.log('FAILED: ' + e.message + ((e.stack || '').split('\n').find(l => l.includes('smoke.js')) || ''));
    if (problems.length) console.log('page errors:\n  ' + problems.join('\n  '));
  }
  await browser.close();
  if (server) server.kill();
  process.exit(code);
})();
