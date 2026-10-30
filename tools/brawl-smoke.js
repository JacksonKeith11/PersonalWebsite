// Plays Board Brawl in two headless browsers against a running server: Alice makes a room, Bob
// joins with its code, Alice adds two bots and starts. Both then play with real key presses,
// clicks and drags (rolling, using items, shopping, mashing, guessing) until the game ends.
// Fails if a page throws or logs an error, or the game doesn't finish in time.
//
//     node tools/brawl-smoke.js [http://localhost:8080] [rounds] [screenshot dir]
//
// With a screenshot directory it saves Alice's screen at each phase and minigame.
const { chromium } = require('playwright');

const BASE = process.argv[2] || 'http://localhost:8080';
const ROUNDS = +(process.argv[3] || 3);
const SHOTS = process.argv[4] || null;
const LIMIT = (4 + ROUNDS * 2) * 60 * 1000;

async function open(browser, name, problems, viewport) {
  const page = await browser.newPage({ viewport });
  page.on('pageerror', e => problems.push(`${name}: ${e.message}`));
  page.on('console', m => { if (m.type() === 'error' && !m.text().includes('Failed to load resource')) problems.push(`${name}: ${m.text()}`); });
  await page.goto(`${BASE}/games/board-brawl?debug`);
  await page.fill('#name', name);
  return page;
}

const state = page => page.evaluate(() => {
  const b = window.brawl;
  if (!b || !b.S.st) return null;
  const st = b.S.st;
  const me = st.players.find(p => p.id === b.S.you);
  return { you: b.S.you, phase: st.phase, step: st.step, cur: st.cur, order: st.order, me, used: st.used,
    mg: st.mg && { key: st.mg.key, ids: st.mg.ids, artist: st.mg.params && st.mg.params.artist }, round: st.round, prices: st.prices };
});

const pick = a => a[Math.floor(Math.random() * a.length)];

async function act(page, s) {
  if (!s) return;
  const vp = page.viewportSize();
  if (s.phase === 'mgintro' && s.mg.ids.includes(s.you) && !s.me.ready) {
    await page.keyboard.press('Space');
  } else if (s.phase === 'board' && s.cur === s.you) {
    if (s.step === 'roll') {
      const items = await page.$$('#action button[data-act=item]:not([disabled])');
      if (items.length && Math.random() < 0.6) {
        await pick(items).click();
        const who = await page.$$('#action button[data-act=target]');
        if (who.length) await pick(who).click();
      } else {
        await page.click('#action button[data-act=roll]');
      }
    } else if (['path', 'buy', 'duel'].includes(s.step)) {
      const b = await page.$$(`#action button[data-act=${s.step}]`);
      if (b.length) await pick(b).click();
    } else if (s.step === 'shop') {
      const b = await page.$$('#action button[data-act=shop]:not([disabled])');
      if (b.length) await pick(b).click();
    }
  } else if (s.phase === 'mg' && s.mg.ids.includes(s.you)) {
    const k = s.mg.key;
    if (k === 'sketch' && s.artist !== s.you && s.mg.artist !== s.you) {
      if (await page.isVisible('#mg-text')) {
        await page.fill('#mg-text', pick(['ghost', 'bat', 'pumpkin', 'cat', 'witch']));
        await page.press('#mg-text', 'Enter');
      }
      return;
    }
    if (k === 'sketch') {
      const x = vp.width * (0.3 + Math.random() * 0.4), y = vp.height * (0.3 + Math.random() * 0.4);
      await page.mouse.move(x, y);
      await page.mouse.down();
      for (let i = 0; i < 8; i++) await page.mouse.move(x + Math.sin(i) * 60, y + i * 8);
      await page.mouse.up();
      return;
    }
    const keys = ['Space', 'Space', 'ArrowUp', 'ArrowLeft', 'ArrowRight', 'ArrowDown', 'Digit1', 'Digit2', 'Digit3', 'KeyQ', 'KeyS', 'KeyC', 'Enter', 'Digit7', 'KeyA', 'KeyD', 'KeyF', 'KeyJ', 'KeyK'];
    for (let i = 0; i < 4; i++) await page.keyboard.press(pick(keys));
    if (['bumper', 'candy', 'tag', 'drop', 'hexheat', 'squirm', 'shoot', 'bowl', 'pong', 'cheese', 'snowball', 'hockey', 'bash', 'redlight'].includes(k)) {
      const key = pick(['KeyW', 'KeyA', 'KeyS', 'KeyD']);
      await page.keyboard.down(key);
      await page.waitForTimeout(150);
      await page.keyboard.up(key);
    }
    await page.mouse.click(vp.width * Math.random(), vp.height * (0.2 + Math.random() * 0.75));
  }
}

(async () => {
  const problems = [];
  const browser = await chromium.launch();
  const alice = await open(browser, 'Alice', problems, { width: 1280, height: 800 });
  const bob = await open(browser, 'Bob', problems, { width: 390, height: 844 });  // a phone
  await alice.click('#create');
  await alice.waitForSelector('#lobby:not([hidden])');
  const code = await alice.textContent('#room-code');
  await bob.fill('#code', code);
  await bob.click('#join');
  await bob.waitForSelector('#lobby:not([hidden])');
  await alice.click('#bot-add');
  await alice.click('#bot-add');
  await alice.selectOption('#rounds', String(ROUNDS));
  await alice.waitForTimeout(300);
  if (SHOTS) await alice.screenshot({ path: `${SHOTS}/lobby.png` });
  await alice.click('#start');
  console.log(`room ${code}: started, ${ROUNDS} rounds`);

  const t0 = Date.now();
  const seen = new Set();
  let last = '';
  while (Date.now() - t0 < LIMIT) {
    const [a, b] = await Promise.all([state(alice), state(bob)]);
    if (!a) { await alice.waitForTimeout(200); continue; }
    const tag = `${a.phase}:${a.mg ? a.mg.key : ''}`;
    if (tag !== last) {
      last = tag;
      if (a.mg && a.phase === 'mg') console.log(`  round ${a.round}: ${a.mg.key}`);
      if (SHOTS && !seen.has(tag)) {
        seen.add(tag);
        const at = a.phase === 'mg' ? 6000 : a.phase === 'board' ? 2500 : 800;
        setTimeout(() => alice.screenshot({ path: `${SHOTS}/${tag.replace(':', '-')}.png` }).catch(() => {}), at);
        if (a.phase === 'mg') setTimeout(() => bob.screenshot({ path: `${SHOTS}/${tag.replace(':', '-')}-phone.png` }).catch(() => {}), at);
      }
    }
    if (a.phase === 'final') break;
    await Promise.all([act(alice, a), act(bob, b)]);
    await alice.waitForTimeout(250);
  }
  const final = await state(alice);
  await alice.waitForTimeout(1500);
  if (SHOTS) {
    await alice.screenshot({ path: `${SHOTS}/final.png` });
    await bob.screenshot({ path: `${SHOTS}/final-phone.png` });
  }
  await browser.close();
  if (!final || final.phase !== 'final') problems.push(`game didn't finish in time (stuck in ${final && final.phase}/${final && final.step})`);
  if (problems.length) {
    console.log('FAILED:\n' + [...new Set(problems)].join('\n'));
    process.exit(1);
  }
  console.log(`ok: played to the end in ${((Date.now() - t0) / 60000).toFixed(1)} min`);
})();
