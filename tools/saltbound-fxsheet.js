// Every action's effect and a sample of enemy moves, played on a live fight and captured three
// frames apiece (150, 330, 560 ms), for checking the looks in js/skillfx.js by eye.
//
//   node tools/saltbound-fxsheet.js <out dir> [skills|foes]
//
// Needs a server on localhost:8765. Uses window.saltboundFx, which only debug pages (?bots) have.
const { chromium } = require('playwright');
const fs = require('fs');
const out = process.argv[2];
const only = process.argv[3]; // 'skills' | 'foes' | undefined
fs.mkdirSync(out, { recursive: true });
(async () => {
  const b = await chromium.launch(); const page = await b.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = []; page.on('pageerror', e => errors.push(String(e)));
  await page.goto('http://localhost:8765/games/saltbound?bots');
  await page.waitForSelector('.brand h1'); await page.fill('#name', 'Tester');
  await page.click('text=Start a new voyage'); await page.waitForSelector('.lobby');
  const picks = ['Vanguard', 'Arcanist', 'Mender'];
  for (let i = 0; i < 3; i++) { await page.click(`.slot:nth-child(${i + 1}) .class-opt:has-text("${picks[i]}")`); await page.waitForTimeout(300); }
  for (const i of [2, 3, 1]) { await page.selectOption(`.slot:nth-child(${i}) select`, 'bot'); await page.waitForTimeout(250); }
  await page.click('text=Set sail'); await page.waitForSelector('.topbar'); await page.waitForTimeout(1500);
  const me = await page.evaluate(() => window.saltbound.you);
  let took = false;
  for (let i = 0; i < 600; i++) {
    const st = await page.evaluate(() => { const f = window.saltbound.game?.fight; return { f: !!f, heroes: f?.heroes || [], n: f?.foes.filter(x => x.hp > 0).length }; });
    if (st.f && st.heroes.includes(0) && st.heroes.length >= 2 && !took) {
      for (const x of st.heroes) await page.evaluate(([x, m]) => window.saltboundSend({ t: 'assign', h: x, pid: m }), [x, me]);
      took = true; await page.waitForTimeout(4000); break;
    }
    await page.waitForTimeout(300);
  }
  await page.mouse.move(5, 895);
  const info = await page.evaluate(() => {
    const f = window.saltbound.game.fight;
    return { heroes: f.heroes, foes: f.foes.filter(x => x.hp > 0).map(x => x.id) };
  });
  console.log('fight', JSON.stringify(info));
  const box = await page.evaluate(() => {
    const rs = [...document.querySelectorAll('.stage [data-uid] img')].map(e => e.getBoundingClientRect());
    const x0 = Math.min(...rs.map(r => r.left)) - 90, x1 = Math.max(...rs.map(r => r.right)) + 90;
    const y0 = Math.min(...rs.map(r => r.top)) - 70, y1 = Math.max(...rs.map(r => r.bottom)) + 50;
    return { x: Math.max(0, x0), y: Math.max(0, y0), width: x1 - Math.max(0, x0), height: y1 - Math.max(0, y0) };
  });
  const frames = [150, 330, 560];
  const grab = async (name, fire) => {
    await page.evaluate(fire);
    let t0 = 0;
    for (let i = 0; i < frames.length; i++) {
      await page.waitForTimeout(frames[i] - t0); t0 = frames[i];
      await page.screenshot({ path: `${out}/${name}-${i}.png`, clip: box });
    }
    await page.waitForTimeout(900);
  };
  const H = info.heroes, F = info.foes;
  const party = H.map(x => 'h' + x);
  if (only !== 'foes') {
    const keys = await page.evaluate(() => window.saltboundFx.skills());
    const acts = await page.evaluate(() => window.saltbound.static.actions);
    for (const k of keys) {
      const t = acts[k]?.tgt;
      const tg = t === 'foes' ? F.map(x => 'f' + x) : t === 'self' ? ['h' + H[0]] : t === 'party' || t === 'allies' ? party
        : ['ally', 'other', 'downed'].includes(t) ? ['h' + H[1]] : ['f' + F[0]];
      await grab('s_' + k, `window.saltboundFx.skill(${JSON.stringify(k)}, ${H[0]}, ${JSON.stringify(tg)})`);
    }
  }
  if (only !== 'skills') {
    const foes = await page.evaluate(() => window.saltbound.static.foes);
    const seen = new Set();
    const list = [];
    for (const [fk, d] of Object.entries(foes)) {
      const moves = { ...(d.moves || {}), ...(d.pool || {}) };
      for (const m of Object.values(moves)) {
        const sig = fk + ':' + m.k;
        if (seen.has(sig) && !/Pistol|Breath|Beam|Bolt|Song|Wail|Curse|Wave|Keg|Broadside|Rockslide|Hook|Gale|Lightning|Toll/.test(m.name)) continue;
        seen.add(sig); list.push([fk, m]);
      }
    }
    for (const [fk, m] of list) {
      const it = { k: m.k, name: m.name, st: m.st, tgt: m.k === 'attack' || m.k === 'debuff' || m.k === 'thief' ? 'h' + H[0] : 'f' + F[0], self: m.self };
      const tg = m.k === 'all' ? party : ['attack', 'debuff', 'thief'].includes(m.k) ? ['h' + H[0]] : [];
      await page.evaluate(([fid, k]) => { const fo = window.saltbound.game.fight.foes.find(x => x.id === fid); fo.k = k; }, [F[0], fk]).catch(() => {});
      await grab(`f_${fk}_${m.name.replace(/[^A-Za-z]+/g, '')}`, `window.saltboundFx.foe(${F[0]}, ${JSON.stringify(it)}, ${JSON.stringify(tg)})`);
    }
  }
  console.log('errors', JSON.stringify(errors));
  await b.close();
})();
