// Plays Overlords in two headless browsers. The host makes a room and a friend joins by the link;
// the host starts with two bots, and both pick a commander from the three offered. The host buys a unit, drags it from the bench to the board and back,
// and sells one by dropping it on the shop; a full board refuses another unit. Both press Ready and
// the fight starts at once: each sees their own fight played back on the canvas, the friend switches
// to watching another fight, and the mute button works. When the fights end, everyone's HP and the
// next round's shop arrive (the damage chart shows during the fight). Fails if a page throws or logs an error. About 40 s.
//
//     node tools/overlords-smoke.js [http://localhost:8080]    against a running server
//     node tools/overlords-smoke.js --serve                    starts its own (tools/check-all.sh does this)
//     ... --shots <folder>                                     also saves a screenshot of each screen
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
  const data = fs.mkdtempSync(path.join(os.tmpdir(), 'overlords-smoke-'));
  const proc = spawn('python3', ['-m', 'uvicorn', 'app.main:app', '--port', String(port), '--log-level', 'warning'],
    { cwd: path.join(__dirname, '..'), env: { ...process.env, DATA_DIR: data, OVERLORDS_DB: path.join(data, 'overlords.db') }, stdio: ['ignore', 'inherit', 'inherit'] });
  BASE = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 80; i++) {
    try { const r = await fetch(BASE + '/healthz'); if (r.ok) return proc; } catch (e) { /* not up yet */ }
    await new Promise(r => setTimeout(r, 250));
  }
  proc.kill();
  throw new Error('the server did not start');
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

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

  const open = async (who, url) => {
    const ctx = await browser.newContext({ viewport: { width: 1300, height: 820 } });
    const p = await ctx.newPage();
    p.who = who;
    p.on('pageerror', e => problems.push(`${who}: ${e.message}`));
    p.on('console', m => { if (m.type() === 'error' && !m.text().includes('Failed to load resource')) problems.push(`${who}: ${m.text()}`); });
    p.setDefaultTimeout(10000);
    await p.goto(url);
    await p.fill('#name', who);
    return p;
  };
  const shot = async (p, name) => { if (SHOTS) await p.screenshot({ path: path.join(SHOTS, `${name}.png`) }); };
  const S = (p, f) => p.evaluate(f);
  const expect = (ok, what) => { if (!ok) throw new Error(what); };
  // screen position of a bench slot or a board hex, from the page's own layout
  const benchXY = (p, i) => p.evaluate(i => {
    const r = document.getElementById('board').getBoundingClientRect();
    const b = window.OV.G.bench[i];
    return { x: r.left + b.x, y: r.top + b.y };
  }, i);
  const hexXY = (p, c, row) => p.evaluate(([c, row]) => {
    const r = document.getElementById('board').getBoundingClientRect();
    const [x, y] = window.OV.hexXY(c, row);
    return { x: r.left + x, y: r.top + y };
  }, [c, row]);
  const drag = async (p, a, b) => {
    await p.mouse.move(a.x, a.y);
    await p.mouse.down();
    await p.mouse.move((a.x + b.x) / 2, (a.y + b.y) / 2, { steps: 4 });
    await p.mouse.move(b.x, b.y, { steps: 4 });
    await p.mouse.up();
    await sleep(300);
  };
  const me = p => S(p, () => { const { S, room } = window.OV; return { ...S.st.players.find(x => x.id === room.you), me: S.st.me }; });

  try {
    const host = await open('Ada', `${BASE}/games/overlords?debug`);
    await shot(host, '1-menu');
    await host.click('#create');
    await host.waitForSelector('#lobby:not([hidden])');
    const link = await host.inputValue('#share');
    const friend = await open('Bo', link + '&debug');
    await friend.click('#join');
    await friend.waitForSelector('#lobby:not([hidden])');
    await host.waitForFunction(() => document.querySelectorAll('#seats li').length === 2);
    await shot(host, '2-lobby');
    await host.click('#start');
    await host.waitForSelector('#game:not([hidden])');
    await friend.waitForSelector('#game:not([hidden])');
    expect((await S(host, () => window.OV.S.st.players.filter(p => p.seated).length)) === 4, 'two bots joined');
    for (const p of [host, friend]) {
      await p.waitForSelector('#choose:not([hidden])');
      await shot(p, `2b-commander-${p.who}`);
      await p.click('#choose-options button');
      await p.waitForSelector('#choose', { state: 'hidden' });
      await p.waitForSelector('#commander-box:not([hidden])');
    }

    // buying, dragging, selling
    let m = await me(host);
    expect(m.me.bench.filter(Boolean).length === 1, 'a free unit to start');
    const gold = m.gold;
    await host.click('#shop .card:not([disabled])');
    await host.waitForFunction(g => window.OV.S.st.players.find(x => x.id === window.OV.room.you).gold < g, gold);
    m = await me(host);
    expect(m.me.bench.filter(Boolean).length === 2 || m.board.length, 'the bought unit is on the bench');
    await drag(host, await benchXY(host, 0), await hexXY(host, 3, 3));
    m = await me(host);
    expect(m.board.length === 1 && m.board[0][3] === 3 && m.board[0][4] === 3, 'dragged onto the board');
    const second = m.me.bench.findIndex(Boolean);
    await drag(host, await benchXY(host, second), await hexXY(host, 2, 3));
    m = await me(host);
    expect(m.board.length === 1, 'a level-1 board holds one unit');
    await drag(host, await hexXY(host, 3, 3), await benchXY(host, 5));
    m = await me(host);
    expect(m.board.length === 0 && m.me.bench[5], 'dragged back to the bench');
    const before = m.gold;
    const shop = await host.$('#shop');
    const box = await shop.boundingBox();
    await drag(host, await benchXY(host, 5), { x: box.x + box.width / 2, y: box.y + box.height / 2 });
    m = await me(host);
    expect(m.gold > before && !m.me.bench[5], 'sold by dropping on the shop');
    await shot(host, '3-plan');

    // the fight
    await host.click('#ready');
    await friend.click('#ready');
    await host.waitForFunction(() => window.OV.S.st.phase === 'fight', null, { timeout: 4000 });
    await friend.waitForFunction(() => window.OV.S.pb && window.OV.S.pb.units.size > 0);
    await sleep(2500);
    expect(await S(friend, () => window.OV.S.pb.t > 1 && window.OV.S.pb.i > 0), 'the fight plays back');
    expect((await friend.textContent('#banner')).includes('vs'), 'the banner names the fight');
    await sleep(400);
    expect(await S(friend, () => !document.getElementById('meter').hidden && document.querySelectorAll('#meter .meter-row').length > 0),
      'the damage chart lists the fight\'s units');
    await shot(friend, '4-fight');
    // watch a bot's fight
    const rows = await friend.$$('#players li');
    for (const r of rows) {
      if ((await r.textContent()).includes('🤖')) { await r.click(); break; }
    }
    await friend.waitForFunction(() => window.OV.S.watch !== window.OV.room.you && window.OV.S.pb);
    await sleep(800);
    await shot(friend, '5-watching');
    await host.click('#mute');
    expect((await host.getAttribute('#mute', 'aria-pressed')) === 'true', 'mute');
    await host.click('#mute');

    // the next round
    await host.waitForFunction(() => window.OV.S.st.round === 2 && window.OV.S.st.phase === 'plan', null, { timeout: 40000 });
    m = await me(host);
    expect(m.me.shop.filter(Boolean).length > 0 && m.gold > 0, 'a new shop and income');
    expect(await S(host, () => window.OV.S.st.settled.length === 4), 'every player settled');
    // a monster win drops a component: put it on a unit by dragging it from the item strip
    m = await me(host);
    if (m.me.items.length) {
      const target = m.board.length ? await hexXY(host, m.board[0][3], m.board[0][4]) : await benchXY(host, m.me.bench.findIndex(Boolean));
      const chip = await (await host.$('#items .item')).boundingBox();
      await drag(host, { x: chip.x + chip.width / 2, y: chip.y + chip.height / 2 }, target);
      const after = await me(host);
      const held = [...after.board.map(u => u[5]), ...after.me.bench.filter(Boolean).map(u => u[3])].flat().length;
      expect(after.me.items.length === m.me.items.length - 1 && held >= 1, 'an item dragged onto a unit');
    }
    await shot(host, '6-round2');

    if (problems.length) throw new Error(problems.join('\n'));
    console.log('ok: a room, buying, dragging, selling, a fight played back and watched, the next round');
    code = 0;
  } catch (e) {
    console.log('FAILED: ' + e.message);
    if (problems.length) console.log(problems.join('\n'));
  } finally {
    await browser.close();
    if (server) server.kill();
    process.exit(code);
  }
})();
