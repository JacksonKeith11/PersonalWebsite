// Plays the start of a Kingfall run in a headless browser: makes a debug room, picks a starting skill
// in the lobby, starts, uses the skill (and checks the server announced it), wins the fight, learns a
// second skill at the Bonfire, goes on and uses that one too. Fails if a page throws or logs an error
// or any step doesn't happen in time. About fifteen seconds.
//
//     node tools/kingfall-smoke.js [http://localhost:8080]    against a running server
//     node tools/kingfall-smoke.js --serve                    starts its own (tools/check-all.sh does this)
//
// With --serve it exits 77 ("skipped") when Playwright or its browser isn't installed here.
const { spawn } = require('child_process');
const net = require('net');

const SERVE = process.argv.includes('--serve');
let BASE = process.argv.slice(2).find(a => a.startsWith('http')) || 'http://localhost:8080';
const skip = why => { console.log('skipped: ' + why); process.exit(77); };

let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { if (SERVE) skip('Playwright is not installed'); throw e; }

const freePort = () => new Promise(res => {
  const s = net.createServer();
  s.listen(0, '127.0.0.1', () => { const p = s.address().port; s.close(() => res(p)); });
});

async function serve() {
  const port = await freePort();
  const os = require('os'), fs = require('fs'), path = require('path');
  const data = fs.mkdtempSync(path.join(os.tmpdir(), 'kingfall-smoke-'));
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
  try {
    const p = await browser.newPage({ viewport: { width: 1280, height: 720 } });
    p.on('pageerror', e => problems.push(e.message));
    p.on('console', m => { if (m.type() === 'error' && !m.text().includes('Failed to load resource')) problems.push(m.text()); });
    p.setDefaultTimeout(20000);
    await p.goto(`${BASE}/games/kingfall?debug&boss=corvin`);
    await p.click('#create');
    await p.waitForSelector('[data-skill]');
    const before = await p.evaluate(() => kf.S.lobby.heroes[0].start_skill);
    await p.click('[data-skill]');
    await p.waitForFunction(b => kf.S.lobby.heroes[0].start_skill !== b, before);
    await p.click('#start');

    // in a fight: count the server's skill announcements, then press the key and wait for one
    const fight = async () => {
      await p.waitForFunction(() => window.kf && kf.S.scene && kf.S.scene.boss && kf.S.scene.local.length && kf.S.lobby.state === 'fight');
      await p.evaluate(() => {
        const sc = kf.S.scene;
        if (sc.smoke !== undefined) return;
        sc.smoke = 0;
        const fx = sc.fx.bind(sc);
        sc.fx = m => { if (m.k === 'skill') sc.smoke++; fx(m); };
      });
      await p.waitForTimeout(2400);  // the boss's entrance
    };
    const cast = async (key, slot) => {
      const n = await p.evaluate(() => kf.S.scene.smoke);
      await p.keyboard.down(key); await p.waitForTimeout(80); await p.keyboard.up(key);
      await p.waitForFunction(n => kf.S.scene.smoke > n, n);
      const cd = await p.evaluate(i => { const l = kf.S.scene.local[0]; return l.skillCd[l.skills[i].id]; }, slot);
      if (!(cd > 0)) throw new Error('no cooldown after using skill ' + (slot + 1));
      await p.waitForSelector('.sk.cool');  // the HUD shows it cooling down
    };
    await fight();
    await cast('z', 0);
    await p.evaluate(() => kf.win());
    await p.waitForSelector('.bonfire [data-learn]');
    await p.click('[data-learn]');
    await p.waitForFunction(() => kf.S.lobby.heroes[0].skills.length === 2 && !kf.S.lobby.heroes[0].skill_offer.length);
    await p.click('[data-ready]');
    await p.waitForFunction(() => !kf.S.scene);  // the first fight's scene is gone
    await fight();
    if ((await p.$$('.sk')).length !== 2) throw new Error('the HUD should show two skills');
    await cast('x', 1);
    if (problems.length) throw new Error('the page reported: ' + problems.join(' | '));
    console.log('ok: started with a skill, used it, learned a second at the Bonfire, used that');
    code = 0;
  } catch (e) {
    console.log('FAILED: ' + e.message);
    if (problems.length) console.log('page errors: ' + problems.join(' | '));
  } finally {
    await browser.close();
    if (server) server.kill();
  }
  process.exit(code);
})();
