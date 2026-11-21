// Plays Overlords on an emulated phone (touch, portrait, then landscape), against three bots. Picks a
// commander; long-presses a shop card (its card shows, nothing is bought); taps one to buy; taps a bench
// unit, then a hex, to move it onto the board; taps the board unit and sells it from its card; opens and
// closes the traits and commander sheets; taps a unit in the fight to follow it; exits the match from the
// header; and checks the page never scrolls sideways or down. Fails if a page throws or logs an error. About 40 s.
//
//     node tools/overlords-phone.js [http://localhost:8080]    against a running server
//     node tools/overlords-phone.js --serve                    starts its own (tools/check-all.sh does this)
//     ... --shots <folder>                                     also saves a screenshot of each step
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

let chromium, devices;
try { ({ chromium, devices } = require('playwright')); } catch (e) { if (SERVE) skip('Playwright is not installed'); throw e; }

const freePort = () => new Promise(res => {
  const s = net.createServer();
  s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => res(p)); });
});

async function serve() {
  const port = await freePort();
  const os = require('os'), fs = require('fs');
  const data = fs.mkdtempSync(path.join(os.tmpdir(), 'overlords-phone-'));
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
const problems = [];
const check = (cond, what) => { console.log((cond ? 'ok   ' : 'FAIL ') + what); if (!cond) problems.push(what); };

async function play(browser, device, tag) {
  const ctx = await browser.newContext({ ...devices[device] });
  const p = await ctx.newPage();
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  const shot = async name => { if (SHOTS) await p.screenshot({ path: path.join(SHOTS, `${tag}-${name}.png`) }); };
  const st = () => p.evaluate(() => {
    const S = window.OV.S;
    return { phase: S.st.phase, me: S.st.players.find(x => x.id === window.OV.room.you), bench: S.st.me?.bench || [],
      sel: S.sel, hover: S.hover && { kind: S.hover.kind }, pinned: S.pinned };
  });
  const until = async (fn, ms = 3000) => { // polls the state until fn(state) holds
    const end = Date.now() + ms;
    let s;
    do { s = await st(); if (fn(s)) return s; await sleep(100); } while (Date.now() < end);
    return s;
  };
  const box = async () => p.$eval('#board', c => { const r = c.getBoundingClientRect(); return { x: r.left, y: r.top }; });
  const tapAt = async ([x, y]) => { const b = await box(); await p.touchscreen.tap(b.x + x, b.y + y); };
  const benchXY = i => p.evaluate(i => { const b = window.OV.G.bench[i]; return [b.x, b.y]; }, i);
  const hexXY = (c, r) => p.evaluate(([c, r]) => window.OV.hexXY(c, r), [c, r]);
  const shown = sel => p.$eval(sel, e => getComputedStyle(e).display !== 'none');

  await p.goto(BASE + '/games/overlords?debug');
  await p.fill('#name', 'Phone');
  await p.tap('#create');
  await p.waitForSelector('#lobby:not([hidden])');
  await p.tap('#start');
  await p.waitForSelector('#choose:not([hidden])');
  await shot('1-commander');
  await p.tap('#choose-options button');
  await p.waitForSelector('#choose', { state: 'hidden' });
  await sleep(300);
  await shot('2-plan');
  const dims = () => p.evaluate(() => [document.documentElement.scrollWidth, innerWidth, document.documentElement.scrollHeight, innerHeight]);
  let d = await dims();
  check(d[0] <= d[1] && d[2] <= d[3], `${tag}: the page fits the screen (${d})`);

  // a long press on a shop card shows it and buys nothing
  const gold0 = (await st()).me.gold;
  const card = await (await p.$('#shop .card')).boundingBox();
  const cdp = await ctx.newCDPSession(p);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: card.x + 20, y: card.y + 20 }] });
  await sleep(650);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  let s = await until(s => s.pinned);
  await sleep(300);
  s = await st();
  check(s.hover?.kind === 'shop' && s.pinned && s.me.gold === gold0, `${tag}: a long press shows a shop card without buying it`);
  await shot('3-longpress');
  await p.tap('#info .sheet-close');
  check(!(await st()).hover, `${tag}: the info card's close button closes it`);

  // buy with a tap, then tap the bench unit and a hex to put it on the board
  await p.tap('#shop .card:not([disabled])');
  s = await until(s => s.me.gold < gold0);
  check(s.me.gold < gold0, `${tag}: a tap on a shop card buys it`);
  const bi = s.bench.findIndex(Boolean);
  await tapAt(await benchXY(bi));
  s = await until(s => s.sel);
  check(s.sel?.from.b === bi, `${tag}: a tap on a bench unit picks it up`);
  await shot('4-selected');
  const onBoard = s.me.board.length;
  if (onBoard < s.me.limit) {
    await tapAt(await hexXY(3, 2));
    s = await until(s => s.me.board.length > onBoard);
    check(s.me.board.length > onBoard && !s.sel, `${tag}: a tap on a hex puts it there`);
  }
  const u = s.me.board[0];
  if (u) {
    await tapAt(await hexXY(u[3], u[4]));
    s = await until(s => s.sel);
    check(s.sel?.from.c === u[3], `${tag}: a tap on a board unit picks it up`);
    const g = s.me.gold;
    await p.tap('#info .sell-row button.sell');
    s = await until(s => s.me.gold > g);
    check(s.me.gold > g && !s.sel, `${tag}: Sell on its card sells it`);
  } else check(false, `${tag}: a unit on the board to sell`);

  // the sheets
  await p.tap('#sheet-tabs [data-sheet="traits"]');
  await sleep(150);
  check(await shown('#traits-box'), `${tag}: the traits sheet opens`);
  await shot('5-traits');
  await p.tap('#traits-box .sheet-close');
  await sleep(150);
  check(!(await shown('#traits-box')), `${tag}: and closes`);
  await p.tap('#sheet-tabs [data-sheet="cmd"]');
  await sleep(150);
  check(await shown('#cmd-sheet'), `${tag}: the commander sheet opens`);
  await p.tap('#cmd-sheet .sheet-close');

  // the fight: tap a unit and it stays in the info card
  await p.tap('#shop .card:not([disabled])').catch(() => {});
  await p.tap('#ready').catch(() => {});
  s = await until(s => s.phase === 'fight', 40000);
  await sleep(1200);
  const pos = await p.evaluate(() => {
    const { S } = window.OV;
    const u = S.pb && S.where && [...S.pb.units.values()].find(u => u.alive && S.where.get(u.id));
    return u ? S.where.get(u.id) : null;
  });
  if (pos) {
    await tapAt(pos);
    s = await until(s => s.pinned);
    check(s.hover?.kind === 'fight', `${tag}: a tap on a fighting unit shows it`);
    await sleep(500);
    await shot('6-fight');
  } else check(false, `${tag}: a unit in the fight to tap`);
  d = await dims();
  check(d[0] <= d[1] && d[2] <= d[3], `${tag}: still fits during the fight (${d})`);
  // Exit: asked first, then back on the menu
  await p.tap('#exit');
  await p.waitForSelector('#exit-confirm:not([hidden])');
  await p.tap('#exit-yes');
  await p.waitForSelector('#menu:not([hidden])', { timeout: 5000 });
  check(true, `${tag}: Exit leaves the match for the menu`);
  check(!errs.length, `${tag}: no page errors${errs.length ? ': ' + errs.join(' | ') : ''}`);
  await ctx.close();
}

(async () => {
  const server = SERVE ? await serve() : null;
  let browser;
  try { browser = await chromium.launch(); } catch (e) {
    if (server) server.kill();
    if (SERVE) skip("Playwright's browser is not installed");
    throw e;
  }
  setTimeout(() => { console.log('FAILED: still running after three minutes'); if (server) server.kill(); process.exit(1); }, 180000).unref();
  try {
    await play(browser, 'iPhone 13', 'portrait');
    await play(browser, 'iPhone 13 landscape', 'landscape');
  } catch (e) {
    problems.push(String(e.stack || e));
    console.log('FAIL ' + e);
  }
  await browser.close();
  if (server) server.kill();
  console.log(problems.length ? `FAILED: ${problems.length} problem(s)` : 'all ok');
  process.exit(problems.length ? 1 : 0);
})();
