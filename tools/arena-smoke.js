// Plays Frag Arena in two headless browsers against a running server and checks they see each
// other, bots join and fight, shots land and nothing throws.
//
//     node tools/arena-smoke.js [http://localhost:8080]
//
// three.js comes from cdnjs; set THREE_FILE to a local copy of three.module.min.js (0.170.0) to
// serve it from disk instead. Rendering is slow without a GPU; the checks allow for that.
const { chromium } = require('playwright');
const fs = require('fs');

const BASE = (process.argv[2] || 'http://localhost:8080') + '/games/frag-arena?debug';

async function open(browser, name, problems) {
  const page = await browser.newPage({ viewport: { width: 960, height: 540 } });
  page.on('pageerror', e => problems.push(`${name}: ${e.message}`));
  page.on('console', m => { if (m.type() === 'error' && !m.text().includes('Failed to load resource')) problems.push(`${name}: ${m.text()}`); });
  if (process.env.THREE_FILE) {
    const body = fs.readFileSync(process.env.THREE_FILE);
    await page.route('**/three.module.min.js', r => r.fulfill({ body, contentType: 'application/javascript' }));
  }
  await page.goto(BASE);
  await page.waitForFunction(() => window.arena && window.arena.S.ready, null, { timeout: 20000 });
  // pointer lock can't be granted headlessly, so join the way the Play button would
  await page.evaluate(n => {
    const a = window.arena;
    a.net.send({ t: 'name', name: n });
    a.net.send({ t: 'spawn' });
    a.S.playing = true;
    document.getElementById('menu').hidden = true;
  }, name);
  await page.waitForFunction(() => window.arena.S.alive, null, { timeout: 5000 });
  return page;
}

(async () => {
  const problems = [];
  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const a = await open(browser, 'Alice', problems);
  const b = await open(browser, 'Bob', problems);
  await a.evaluate(() => { for (let i = 0; i < 3; i++) window.arena.net.send({ t: 'bot', op: 'add' }); });
  await a.evaluate(() => window.arena.keys.add('KeyW'));
  await a.mouse.down();
  await a.waitForTimeout(1500);
  await a.mouse.up();
  await a.evaluate(() => window.arena.keys.delete('KeyW'));
  await a.waitForTimeout(12000);

  const seen = await b.evaluate(() => [...window.arena.S.roster.values()].map(p => p.name));
  const remote = await b.evaluate(() => window.arena.view.players.size);
  const fired = await a.evaluate(() => window.arena.S.ammo[0] < window.arena.S.weapons[0].start);
  const deaths = await a.evaluate(() => [...window.arena.S.roster.values()].reduce((n, p) => n + p.deaths, 0));
  await a.evaluate(() => window.arena.net.send({ t: 'bot', op: 'clear' }));
  await a.waitForTimeout(500);
  const left = await b.evaluate(() => [...window.arena.S.roster.values()].filter(p => p.bot).length);
  await browser.close();

  const checks = [
    ['Bob sees Alice and three bots', seen.includes('Alice') && seen.filter(n => !['Alice', 'Bob'].includes(n)).length === 3],
    ['Bob draws the other players', remote >= 4],
    ['Alice fired the machine gun', fired || deaths > 0],
    ['someone got fragged', deaths > 0],
    ['removing the bots worked', left === 0],
    ['no errors in either page', problems.length === 0],
  ];
  for (const [what, ok] of checks) console.log(`${ok ? 'ok  ' : 'FAIL'} ${what}`);
  if (problems.length) console.log(problems.join('\n'));
  process.exit(checks.every(c => c[1]) ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
