// Plays a round of Scramble in two headless browsers (one phone-sized) with a bot. The host makes a
// room, adds a bot and sets three rounds; a friend joins by the link. Both must see the countdown,
// run and jump under their own controls, see each other and the bot move, be knocked out by a fall
// and put back at the flag, run through an item box and use what's in it (both screens must see it go
// off), and (carried to the line, since a browser can't be trusted to play well)
// finish and get the round's points. Fails if a page throws or logs an error. About 40 s.
//
//     node tools/scramble-smoke.js [http://localhost:8080]    against a running server
//     node tools/scramble-smoke.js --serve                    starts its own (tools/check-all.sh does this)
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
  const data = fs.mkdtempSync(path.join(os.tmpdir(), 'scramble-smoke-'));
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
    const host = await open('Ada', `${BASE}/games/scramble?debug`);
    await shot(host, '1-menu');
    await host.click('#create');
    await host.waitForSelector('#lobby:not([hidden])');
    const room = await host.textContent('#room-code');
    const friend = await open('Bo', `${BASE}/games/scramble?debug&room=${room}`, true);
    await friend.click('#join');
    await host.click('#bot-add');
    await host.selectOption('#rounds', '3');
    await friend.waitForFunction(() => document.querySelectorAll('#seats li').length === 3 && document.getElementById('rounds').value === '3');
    if (await friend.isVisible('#start')) throw new Error('a guest was offered the Start button');
    await shot(host, '2-lobby');
    await host.click('#start');

    const all = [host, friend];
    const me = p => p.evaluate(() => { const { S } = window.scramble; return { x: S.me.x, y: S.me.y, cp: S.me.cp, dead: S.me.dead, ground: S.me.ground }; });
    const seenAt = (p, name) => p.evaluate(n => {
      const { S } = window.scramble;
      const who = S.st.players.find(q => q.name === n);
      return S.others.get(who.id)?.tx ?? null;
    }, name);
    for (const p of all) {
      await p.waitForSelector('#game:not([hidden])');
      await p.waitForFunction(() => /^[123]$/.test(document.getElementById('banner').textContent));
    }
    await shot(friend, '3-countdown-phone');
    const start = await me(host);
    await host.keyboard.down('ArrowRight');   // held on the start line: nobody moves before "Go!"
    await host.waitForFunction(() => window.scramble.raceTime() > -0.3);
    if ((await me(host)).x !== start.x) throw new Error('a racer moved before the start');
    await host.waitForFunction(() => window.scramble.raceTime() > 0.6);
    // the host runs and jumps by keyboard, the friend by the buttons on the screen
    await host.keyboard.down('Space');   // held: a tap is only a short hop
    await host.waitForFunction(() => window.scramble.S.me.y < -90);
    await host.keyboard.up('Space');
    const box = await friend.locator('#t-right').boundingBox();
    await friend.evaluate(() => document.getElementById('t-right').dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true })));
    if (!box) throw new Error('the phone has no run button');
    await host.waitForTimeout(900);
    await host.keyboard.up('ArrowRight');
    await friend.evaluate(() => document.getElementById('t-right').dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true })));
    for (const p of all) if ((await me(p)).x < start.x + 150) throw new Error(`${p.who} didn't run`);
    await shot(host, '4-race');
    await shot(friend, '4-race-phone');
    // each sees the other, and the bot, somewhere down the course
    await host.waitForFunction(() => { const { S } = window.scramble; return [...S.others.values()].filter(o => o.tx > 100).length === 3; });
    const theirs = await seenAt(host, 'Bo'), really = (await me(friend)).x;
    if (Math.abs(theirs - really) > 60) throw new Error(`the host sees Bo at ${theirs}, but Bo is at ${really}`);

    // Into a pit: knocked out, then back at the last flag.
    await friend.evaluate(() => { const { S } = window.scramble; S.me.x = S.course.segs[2] + 100; S.me.y = -1; S.me.cp = 2; S.me.y = 400; });
    await friend.waitForFunction(() => window.scramble.S.me.dead);
    await friend.waitForFunction(() => { const { S } = window.scramble; return !S.me.dead && S.me.ground && Math.abs(S.me.x - S.course.segs[2] - 60) < 5; });

    // An item box: run through it, get an item, use it, and both screens see it go off.
    await host.evaluate(() => { const { S } = window.scramble; Object.assign(S.me, { x: S.course.boxes[0][0] - 60, y: -1, vx: 0, vy: 0, dead: false }); });
    await host.keyboard.down('ArrowRight');
    await host.waitForFunction(() => { const { S, room } = window.scramble; return S.st.players.find(p => p.id === room.you).item; });
    await host.keyboard.up('ArrowRight');
    await host.waitForSelector('#item:not([hidden])');
    await shot(host, '5-item');
    await host.keyboard.press('KeyE');
    for (const p of all) await p.waitForFunction(() => window.scramble.S.itemsSeen > 0);
    await host.waitForSelector('#item', { state: 'hidden' });

    // To the line. (The server won't believe a finish quicker than a flat-out run.)
    await host.waitForFunction(() => { const { S, raceTime } = window.scramble; return raceTime() > S.course.finish / 300 * 0.8 + 0.5; }, null, { timeout: 90000 });
    await host.evaluate(() => { const { S } = window.scramble; S.me.x = S.course.finish + 20; S.me.y = -1; });
    await host.waitForFunction(() => /Finished/.test(document.getElementById('banner').textContent));
    await friend.waitForFunction(() => / s left/.test(document.getElementById('banner').textContent));
    await shot(host, '6-finished');
    await friend.evaluate(() => { const { S } = window.scramble; S.me.x = S.course.finish + 20; S.me.y = -1; });
    for (const p of all) await p.waitForSelector('#results:not([hidden])', { timeout: 40000 });
    const st = await host.evaluate(() => window.scramble.S.st);
    const pts = Object.fromEntries(st.players.map(q => [q.name, q.pts]));
    if (pts.Ada !== 10 && pts.Bo !== 7 && pts.Ada + pts.Bo < 12) throw new Error(`odd points: ${JSON.stringify(pts)}`);
    if (await host.locator('#res-rows tr').count() !== 3) throw new Error('the results are missing a racer');
    await shot(host, '7-results');
    await shot(friend, '7-results-phone');
    // and the next round starts on its own
    for (const p of all) await p.waitForFunction(() => window.scramble.S.st.round === 2 && window.scramble.S.st.phase === 'race', null, { timeout: 15000 });
    // and in it, each still sees the other move (positions were once held back for a whole round's length)
    await host.waitForFunction(() => window.scramble.raceTime() > 0.6, null, { timeout: 10000 });
    await friend.evaluate(() => document.getElementById('t-right').dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true })));
    await host.waitForFunction(name => {
      const { S } = window.scramble, who = S.st.players.find(q => q.name === name);
      return (S.others.get(who.id)?.tx ?? 0) > 200;
    }, 'Bo', { timeout: 5000 }).catch(() => { throw new Error("in round 2 the host never saw Bo move"); });
    await friend.evaluate(() => document.getElementById('t-right').dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true })));

    if (problems.length) throw new Error('page errors:\n  ' + problems.join('\n  '));
    console.log('ok: two players and a bot raced a round: controls, knock-outs, items, the finish and the points all work');
    code = 0;
  } catch (e) {
    console.log('FAILED: ' + e.message + ((e.stack || '').split('\n').find(l => l.includes('smoke.js')) || ''));
    if (problems.length) console.log('page errors:\n  ' + problems.join('\n  '));
  }
  await browser.close();
  if (server) server.kill();
  process.exit(code);
})();
