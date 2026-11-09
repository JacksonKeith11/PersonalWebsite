// Plays the start of a Kingfall run in headless browsers. One player: makes a debug room, picks a
// starting skill in the lobby, uses it (and checks the server announced it), wins the fight, learns a
// second at the Bonfire and uses that. Then two players in one room: each must see what the other does
// (a skill and its animation, a ward on the other's hero and HUD card, a projectile in flight, the boss
// hurt and its Burn meter filling), and both must get through the Bonfire into the next fight. Fails if
// a page throws or logs an error or any step doesn't happen in time. About forty seconds.
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
  setTimeout(() => { console.log('FAILED: still running after three minutes'); if (server) server.kill(); process.exit(1); }, 180000).unref();

  const open = async (who, query) => {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });  // its own storage: a separate player
    const p = await ctx.newPage();
    p.on('pageerror', e => problems.push(`${who}: ${e.message}`));
    p.on('console', m => { if (m.type() === 'error' && !m.text().includes('Failed to load resource')) problems.push(`${who}: ${m.text()}`); });
    p.setDefaultTimeout(20000);
    await p.goto(`${BASE}/games/kingfall?debug&${query}`);
    return p;
  };
  // In a fight (the `stage`th of the run, from 0): count the server's skill announcements, so a test can
  // wait for the next one. The game reuses its one fight scene object, so the count is tied to the fight.
  const fight = async (p, stage) => {
    await p.waitForFunction(stage => window.kf && kf.S.lobby && kf.S.lobby.state === 'fight' && kf.S.lobby.stage === stage && kf.S.scene && kf.S.scene.boss
      && kf.S.scene.local.length && kf.S.scene.fightMsg === kf.S.fightMsg && kf.S.scene.smokeFor !== kf.S.fightMsg, stage);
    await p.evaluate(() => {
      const sc = kf.S.scene;
      sc.smoke = 0; sc.smokeFor = kf.S.fightMsg;
      if (sc.smokeHook) return;
      sc.smokeHook = true;
      const fx = sc.fx.bind(sc);
      sc.fx = m => { if (m.k === 'skill') sc.smoke++; fx(m); };
    });
  };
  const ENTRANCE = 2400;  // the boss's entrance: it can't be hurt until it's over
  const press = async (p, key) => { await p.keyboard.down(key); await p.waitForTimeout(80); await p.keyboard.up(key); };
  const cast = async (p, key, slot) => {
    const n = await p.evaluate(() => kf.S.scene.smoke);
    await press(p, key);
    await p.waitForFunction(n => kf.S.scene.smoke > n, n);
    const cd = await p.evaluate(i => { const l = kf.S.scene.local[0]; return l.skillCd[l.skills[i].id]; }, slot);
    if (!(cd > 0)) throw new Error('no cooldown after using skill ' + (slot + 1));
    await p.waitForSelector('.sk.cool');  // the HUD shows it cooling down
  };
  const learn = async p => {
    await p.waitForSelector('.bonfire [data-learn]');
    await p.click('[data-learn]');
    await p.waitForFunction(() => { const h = kf.S.lobby.heroes.find(h => h.conn === kf.S.me); return h.skills.length === 2 && !h.skill_offer.length; });
    await p.click('[data-ready]');
  };

  // One player: a starting skill, used; a second learned at the Bonfire, used.
  const solo = async () => {
    const p = await open('solo', 'boss=corvin');
    await p.click('#create');
    await p.waitForSelector('[data-skill]');
    const before = await p.evaluate(() => kf.S.lobby.heroes[0].start_skill);
    await p.click('[data-skill]');
    await p.waitForFunction(b => kf.S.lobby.heroes[0].start_skill !== b, before);
    await p.click('#start');
    await fight(p, 0); await p.waitForTimeout(ENTRANCE);
    await cast(p, 'z', 0);
    await p.evaluate(() => kf.win());
    await learn(p);
    await fight(p, 1); await p.waitForTimeout(ENTRANCE);
    if ((await p.$$('.sk')).length !== 2) throw new Error('the HUD should show two skills');
    await cast(p, 'x', 1);
    await p.context().close();
  };

  // Two players in one room: what each browser shows of the other. Ann (the host) wards herself; Bea
  // throws a lance at the boss. Each must see the other's skill, Bea must see Ann's ward on Ann's hero
  // and HUD card, Ann must see Bea's lance fly and the boss's health and Burn meter move. Then both
  // learn a skill at the Bonfire and the second fight starts for both.
  const duo = async () => {
    const ann = await open('Ann', 'boss=corvin');
    await ann.click('#create');
    await ann.waitForFunction(() => kf.S.lobby && kf.S.lobby.heroes.length === 1);
    const room = await ann.evaluate(() => kf.S.code);
    await ann.evaluate(() => kf.net.send({ t: 'set', h: kf.S.lobby.heroes[0].id, skill: 'ward' }));
    const bea = await open('Bea', 'room=' + room);
    await bea.click('#join');
    await bea.click('#joinkb');
    await bea.waitForFunction(() => kf.S.lobby.heroes.some(h => h.conn === kf.S.me));
    await bea.evaluate(() => kf.net.send({ t: 'set', h: kf.S.lobby.heroes.find(h => h.conn === kf.S.me).id, skill: 'lance' }));
    await ann.waitForFunction(() => kf.S.lobby.heroes.length === 2 && kf.S.lobby.heroes.every(h => h.start_skill === (h.conn === kf.S.me ? 'ward' : 'lance')));
    await ann.click('#start');
    await Promise.all([fight(ann, 0), fight(bea, 0)]);
    for (const p of [ann, bea]) if ((await p.$$('#hud .card')).length !== 2) throw new Error('the HUD should show both heroes');
    await ann.evaluate(() => kf.safe());  // the heroes stand about while the test looks: this boss only walks, never attacks
    await ann.waitForTimeout(ENTRANCE);
    const annId = await ann.evaluate(() => kf.S.scene.local[0].id);

    // Ann's ward, as Bea sees it: the announcement, Ann's casting animation, the ward on her hero and card
    const seen = Promise.all([
      bea.waitForFunction(() => kf.S.scene.smoke > 0),
      bea.waitForFunction(id => kf.S.scene.remote[id].buf.some(r => r[5] === 'k_ward'), annId),
    ]);
    seen.catch(() => {});
    await cast(ann, 'z', 0);
    await seen;
    await bea.waitForFunction(id => kf.S.scene.heroRows[id].shield > 0 && kf.S.scene.remote[id].view.st.shield > 0, annId);
    await bea.waitForFunction(id => /Ward/.test(document.querySelector(`#card-${id} .buffs`).textContent), annId);

    // Bea's lance, as Ann sees it: the shot in flight, then the boss hurt and burning. The boss walks
    // about, so a throw can miss: she aims afresh and throws again when the lance is back (8 s).
    const soon = { timeout: 2500 };
    const hurt = (p, opt) => p.waitForFunction(() => { const B = kf.S.scene.boss.bodies[0]; return B.hp < B.mhp && B.meters[0] > 0; }, null, opt);
    for (let tries = 1; ; tries++) {
      const aim = await bea.evaluate(() => {
        const sc = kf.S.scene, B = sc.boss.bodies[0], cam = sc.cameras.main, r = sc.game.canvas.getBoundingClientRect();
        return { x: r.left + (B.x - cam.worldView.x) * cam.zoom, y: r.top + (B.y - 14 - cam.worldView.y) * cam.zoom };
      });
      await bea.mouse.move(aim.x, aim.y);
      await bea.waitForTimeout(150);
      const shot = ann.waitForFunction(() => kf.S.scene && kf.S.scene.remoteShots.some(s => s.k === 'proj'), null, soon).then(() => true, () => false);
      await cast(bea, 'z', 0);
      const sawShot = await shot, wasHurt = sawShot && await hurt(bea, soon).then(() => true, () => false);
      if (wasHurt) break;
      if (tries === 4) throw new Error("Bea's lance never reached the boss on Ann's screen in four throws");
      await bea.waitForFunction(() => !(kf.S.scene.local[0].skillCd.lance > 0));
    }
    for (const p of [ann, bea]) {
      await hurt(p);
      await p.waitForSelector('#bb-0 .stm[data-st="burn"]:not([hidden])');
    }

    await ann.evaluate(() => kf.win());
    await Promise.all([learn(ann), learn(bea)]);
    for (const p of [ann, bea]) {
      await fight(p, 1);
      await p.waitForFunction(() => document.querySelectorAll('.sk').length === 2);
    }
    await ann.context().close(); await bea.context().close();
  };

  try {
    await solo();
    await duo();
    if (problems.length) throw new Error('a page reported: ' + problems.join(' | '));
    console.log("ok: one player started with a skill, used it, learned and used a second; two players saw each other's skill, ward and shot, and the boss's Burn");
    code = 0;
  } catch (e) {
    const where = (e.stack || '').split('\n').find(l => l.includes('kingfall-smoke.js')) || '';
    console.log('FAILED: ' + e.message.split('\n')[0] + ' ' + where.trim());
    if (problems.length) console.log('page errors: ' + problems.join(' | '));
  } finally {
    await browser.close();
    if (server) server.kill();
  }
  process.exit(code);
})();
