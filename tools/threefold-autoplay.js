// Plays Roguelike Tactics headlessly with the heroes on autopilot, to catch errors and gauge balance.
//
//   node tools/threefold-autoplay.js [runs=3] [--chaos] [--asc N] [--par K] [--json FILE]
//
// Serves app/ itself on a free port. Needs Playwright with Chromium. If the browser can't reach
// cdnjs, download Phaser first and point PHASER_FILE at it:
//   curl -sSo /tmp/phaser.min.js https://cdnjs.cloudflare.com/ajax/libs/phaser/3.80.1/phaser.min.js
//   PHASER_FILE=/tmp/phaser.min.js node tools/threefold-autoplay.js 5
// --chaos starts every hero promoted with four random skills, every artifact slot filled: a stress
// test of the odd mechanics rather than a balance check.
// --asc N plays at ascent N. --par K plays K runs at once (default 1). --json FILE appends one line
// per run (win, act, the final build) for tools/threefold-balance.js to summarise.
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
const runs = +(args.find(a => /^\d+$/.test(a)) || 3);
const chaos = args.includes('--chaos');
const opt = name => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : null; };
const asc = +(opt('--asc') || 0), par = Math.max(1, +(opt('--par') || 1)), jsonFile = opt('--json');
const port = 8700 + Math.floor(Math.random() * 200);

(async () => {
  const server = spawn('python3', ['-m', 'http.server', String(port)], { cwd: path.join(__dirname, '..', 'app'), stdio: 'ignore' });
  await new Promise(r => setTimeout(r, 800));
  const browser = await chromium.launch();
  let failures = 0, wins = 0, next = 0;
  const one = async i => {
    const page = await browser.newPage();
    const errors = [];
    if (process.env.PHASER_FILE) {
      const body = fs.readFileSync(process.env.PHASER_FILE);
      await page.route('**/phaser.min.js', r => r.fulfill({ body, contentType: 'application/javascript' }));
    }
    await page.route('https://fonts.**', r => r.abort());
    page.on('pageerror', e => errors.push(e.message + ' ' + (e.stack || '').split('\n')[1]));
    page.on('console', m => { if (m.type() === 'error' && !/fonts|net::ERR/.test(m.text())) errors.push(m.text()); });
    await page.goto(`http://localhost:${port}/static/games/threefold/index.html?auto${chaos ? '&chaos' : ''}${asc ? `&asc=${asc}` : ''}`);
    const t0 = Date.now();
    try { await page.waitForFunction(() => window.__result, null, { timeout: 600000, polling: 1000 }); }
    catch (e) { errors.push('timed out'); }
    const r = await page.evaluate(() => ({ ...window.__result, log: window.__log || [] }));
    if (r.win) wins++;
    console.log(`run ${i + 1}: ${r.win ? 'WIN' : `lost in act ${r.act}`}, ${r.battles} battles won, ${((Date.now() - t0) / 1000) | 0}s`);
    // act, kind (n/e/b), level : W or L (hero HP after) [what was left standing]
    console.log('  ' + r.log.map(l => `${l.act}${l.kind[0]}${l.lvl}:${l.win ? 'W' : 'L'}(${l.heroes})${l.win ? '' : ` [${l.foes}]`}`).join(' '));
    for (const e of [...new Set(errors)]) { console.log('  ERROR ' + e); failures++; }
    if (jsonFile) fs.appendFileSync(jsonFile, JSON.stringify({ win: !!r.win, act: r.act, battles: r.battles, chaos, build: r.build, log: r.log }) + '\n');
    await page.close();
  };
  try {
    await Promise.all(Array.from({ length: Math.min(par, runs) }, async () => { while (next < runs) await one(next++); }));
  } finally {
    await browser.close();
    server.kill();
  }
  console.log(`${wins}/${runs} wins, ${failures} errors`);
  process.exit(failures ? 1 : 0);
})();
