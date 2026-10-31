// Screenshots of Saltbound's screens from a real game against a running server, for checking the
// UI against its tokens before pushing (see docs/saltbound.md).
//
//   node tools/saltbound-shots.js [url] [out dir] [WxH]
//
// Plays solo with ?bots: claims the Vanguard, gives the other two heroes to bots, and shoots the
// title, lobby, map, a fight, and whatever dialogs come up along the way.
const { chromium } = require('playwright');
const fs = require('fs');

const base = process.argv[2] || 'http://localhost:8765';
const out = process.argv[3] || 'shots';
const [W, H] = (process.argv[4] || '1440x900').split('x').map(Number);
fs.mkdirSync(out, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  const errors = [];
  page.on("pageerror", e => errors.push(String(e.stack || e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  const shot = async name => { await page.screenshot({ path: `${out}/${W}x${H}-${name}.png` }); console.log('shot', name); };
  await page.goto(`${base}/games/saltbound?bots`);
  await page.waitForSelector('.brand h1');
  await page.fill('#name', 'Tester');
  await page.waitForTimeout(500);
  await shot('title');
  await page.click('text=Start a new voyage');
  await page.waitForSelector('.lobby');
  await shot('lobby-empty');
  await page.click('.slot:nth-child(1) .class-opt:has-text("Vanguard")');
  await page.waitForTimeout(300);
  await page.click('.slot:nth-child(2) .class-opt:has-text("Arcanist")');
  await page.waitForTimeout(300);
  await page.click('.slot:nth-child(3) .class-opt:has-text("Mender")');
  await page.waitForTimeout(300);
  await page.selectOption('.slot:nth-child(2) select', 'bot');
  await page.waitForTimeout(200);
  await page.selectOption('.slot:nth-child(3) select', 'bot');
  await page.waitForTimeout(300);
  await shot('lobby');
  await page.selectOption('.slot:nth-child(1) select', 'bot');
  await page.waitForTimeout(300);
  await page.click('text=Set sail');
  await page.waitForSelector('.topbar');
  await page.waitForTimeout(1500);
  await shot('map');
  // Bots play all three heroes; when a fight starts with the first hero in it, take that hero over.
  const me = await page.evaluate(() => window.saltbound.you);
  let fights = 0, dialogs = 0, took = false;
  for (let i = 0; i < 400 && fights < 2; i++) {
    const st = await page.evaluate(() => {
      const g = window.saltbound.game; if (!g) return { end: true };
      return { phase: g.phase, inFight: !!(g.fight && g.fight.heroes.includes(0)), end: g.phase === 'end', turn: g.turn };
    });
    if (st.end) break;
    if (st.inFight && !took) {
      await page.evaluate(m => window.saltboundSend({ t: 'assign', h: 0, pid: m }), me);
      took = true;
      await page.waitForTimeout(800);
    }
    if (took && await page.$('.combat .tray')) {
      fights++;
      await page.waitForTimeout(600);
      await shot(`fight-${fights}`);
      for (let r = 0; r < 30 && await page.$('.combat .tray'); r++) {
        for (let k = 0; k < 4; k++) {
          await page.keyboard.press('q');
          await page.waitForTimeout(150);
          if (await page.$('.unit.target')) { await page.click('.unit.target'); await page.waitForTimeout(150); }
        }
        if (r === 0) await shot(`fight-${fights}-planned`);
        await page.keyboard.press('Space');
        await page.waitForTimeout(r === 0 ? 1200 : 2500);
        if (r === 0) await shot(`fight-${fights}-resolving`);
      }
      // hand the hero back to the bot until the next fight
      await page.evaluate(() => window.saltboundSend({ t: 'assign', h: 0, pid: 'bot' }));
      took = false;
      continue;
    }
    const pick = await page.$('.scrim .pick, .scrim .choice:not([disabled])');
    if (pick) { dialogs++; if (dialogs <= 3) await shot(`dialog-${dialogs}`); await pick.click().catch(() => {}); await page.waitForTimeout(400); continue; }
    const ok = await page.$('.scrim .btn.primary');
    if (ok) { await ok.click().catch(() => {}); await page.waitForTimeout(300); continue; }
    await page.waitForTimeout(500);
  }
  await shot('later');
  await page.click('.actionbar button:has-text("Hero")').catch(() => {});
  await page.waitForTimeout(400);
  await shot('hero-sheet');
  console.log('errors:', errors.length ? errors.join('\n') : 'none');
  await browser.close();
})();
