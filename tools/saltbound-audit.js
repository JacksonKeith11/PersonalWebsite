// Screenshots of Saltbound at saved moments (made by tools/saltbound-audit.py) against a running
// server, for reviewing the UI: loot, level-ups, events, fights, the boss, the end of a run.
//
//   node tools/saltbound-audit.js [url] [out dir] [WxH] [scenario ...]
//
// Each scenario resumes "audit: <name>" as the token "audit", plays hero 0 and gives the others to bots.
const { chromium } = require('playwright');
const fs = require('fs');
const { execFileSync } = require('child_process');

const base = process.argv[2] || 'http://localhost:8765';
const out = process.argv[3] || 'audit';
const [W, H] = (process.argv[4] || '1440x900').split('x').map(Number);
const names = process.argv.slice(5).length ? process.argv.slice(5) : ['start', 'loot', 'level', 'event', 'fight', 'fork', 'boss', 'won', 'lost'];
fs.mkdirSync(out, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const errors = [];
  for (const name of names) {
    // a browser keeps only its five newest saves, so make each one just before it's used
    execFileSync('python3', [`${__dirname}/saltbound-audit.py`, name], { stdio: 'inherit' });
    const page = await browser.newPage({ viewport: { width: W, height: H } });
    page.on('pageerror', e => errors.push(`${name}: ${e}`));
    page.on('console', m => { if (m.type() === 'error') errors.push(`${name}: ${m.text()}`); });
    await page.addInitScript(() => localStorage.setItem('saltbound', JSON.stringify({ token: 'audit', name: 'Auditor', hints: { fight: 1, plan: 1, town: 1, loot: 1 } })));
    const shot = async tag => { await page.screenshot({ path: `${out}/${W}x${H}-${name}${tag ? '-' + tag : ''}.png` }); console.log('shot', name, tag || ''); };
    try {
      await page.goto(`${base}/games/saltbound?bots`);
      const row = page.locator('.save-row', { hasText: `audit: ${name}` });
      await row.locator('button', { hasText: 'Resume' }).click({ timeout: 8000 });
      await page.waitForSelector('.lobby');
      await page.click('.slot:nth-child(1) button:has-text("Play this hero")');
      await page.waitForTimeout(300);
      for (const i of [2, 3]) { await page.selectOption(`.slot:nth-child(${i}) select`, 'bot'); await page.waitForTimeout(200); }
      await page.click('text=Set sail');
      await page.waitForSelector('.topbar, .combat, .endscreen, .end', { timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(1800);
      await shot();
      if (name === 'start') {
        // the town (its button is named after the town), each of the hero sheet's tabs, and the menu
        const town = page.locator('.actionbar button').filter({ hasNotText: /Rest|Hero|Ready/ });
        if (await town.count()) {
          await town.first().click(); await page.waitForTimeout(600); await shot('town');
          for (const tab of await page.locator('.drawer .tabs button').all()) { await tab.click(); await page.waitForTimeout(300); await shot('town-' + (await tab.innerText()).toLowerCase()); }
          await page.keyboard.press('Escape'); await page.waitForTimeout(300);
        }
        const hero = page.locator('.actionbar button', { hasText: 'Hero' });
        if (await hero.count()) {
          await hero.first().click(); await page.waitForTimeout(600);
          for (const tab of await page.locator('.drawer .tabs button').all()) { await tab.click(); await page.waitForTimeout(300); await shot('hero-' + (await tab.innerText()).toLowerCase()); }
          await page.keyboard.press('Escape'); await page.waitForTimeout(300);
        }
        const menu = page.locator('.topbar .right button').last();
        if (await menu.count()) { await menu.click(); await page.waitForTimeout(500); await shot('menu'); await page.keyboard.press('Escape'); }
      }
      if (name === 'loot' || name === 'level' || name === 'event') {
        const pick = page.locator('.scrim .pick-btns .btn.primary, .scrim button.pick, .scrim .choice:not([disabled])').first();
        if (await pick.count()) { await pick.click(); await page.waitForTimeout(1200); await shot('after'); }
      }
    } catch (e) { errors.push(`${name}: ${e.message.split('\n')[0]}`); }
    await page.close();
  }
  console.log('errors:', errors.length ? errors.join('\n') : 'none');
  await browser.close();
})();
