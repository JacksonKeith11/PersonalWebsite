// A two-player Saltbound fight in two browsers, for checking what each player sees of the other.
//
//   python3 tools/saltbound-audit.py fight          (with SALTBOUND_DB set like the server's)
//   node tools/saltbound-mp.js [url] [out dir]
//
// "Alice" (the audit token) resumes the "audit: fight" save, "Bob" joins by room code, each plays one
// hero and a bot plays the third. Each plays an action while the other watches, both ready up, and
// the enemies act; screenshots of both screens go to the out dir at every step. Throughout, both
// pages are watched for things that mustn't happen while a fight is still playing out (a dialog or
// a level-up/objective banner over it), and for page errors; any of those fail the run.
const { chromium } = require('playwright');
const fs = require('fs');

const base = process.argv[2] || 'http://localhost:8765';
const out = process.argv[3] || 'mp';
fs.mkdirSync(out, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const problems = [];
  const open = async (token, name) => {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    page.on('pageerror', e => problems.push(`${name}: ${e}`));
    await page.addInitScript(([t, n]) => {
      localStorage.setItem('saltbound', JSON.stringify({ token: t, name: n, hints: { fight: 1, plan: 1, town: 1, loot: 1, sea: 1 } }));
      // the watcher: a dialog or a level/objective banner while the fight overlay is still up
      const seen = new Set();
      setInterval(() => {
        const fight = document.querySelector('.combat');
        if (!fight) return;
        const dialog = document.querySelector('#modal .scrim');
        const banner = [...document.querySelectorAll('.big-banner')].map(b => b.textContent).find(t => /Level|cleared/.test(t));
        for (const p of [dialog && 'a dialog opened over the fight', banner && `"${banner.trim().slice(0, 40)}" shown over the fight`]) {
          if (p && !seen.has(p)) { seen.add(p); console.log('SALTBOUND-PROBLEM ' + p); }
        }
      }, 100);
    }, [token, name]);
    page.on('console', m => { if (m.text().startsWith('SALTBOUND-PROBLEM ')) problems.push(`${name}: ${m.text().slice(18)}`); });
    return page;
  };
  const A = await open('audit', 'Alice');
  const B = await open('friend', 'Bob');
  const shot = async (p, tag) => { await p.screenshot({ path: `${out}/${tag}.png` }); console.log('shot', tag); };
  const play = async (p) => {
    // the first die on the first action, at the first target offered (if the fight is still on)
    const die = p.locator('.tray .die:not(.used)').first();
    if (!(await die.isVisible({ timeout: 3000 }).catch(() => false))) return false;
    await die.click();
    await p.keyboard.press('q');
    await p.waitForTimeout(150);
    if (await p.locator('.unit.target').count()) await p.locator('.unit.target').first().click();
    return true;
  };
  const ready = async (p) => { if (await p.locator('.tray').count()) await p.keyboard.press('Space'); };

  await A.goto(`${base}/games/saltbound?bots`);
  await A.locator('.save-row', { hasText: 'audit: fight' }).locator('button', { hasText: 'Resume' }).click({ timeout: 8000 });
  await A.waitForSelector('.lobby');
  const code = (await A.locator('.code-box .code').innerText()).trim();
  await B.goto(`${base}/games/saltbound?room=${code}`);
  await B.waitForSelector('.lobby', { timeout: 8000 });
  await A.click('.slot:nth-child(1) button:has-text("Play this hero")');
  await A.waitForTimeout(400);
  await B.click('.slot:nth-child(2) button:has-text("Play this hero")');
  await B.waitForTimeout(400);
  await A.selectOption('.slot:nth-child(3) select', 'bot');
  await A.waitForTimeout(400);
  await shot(A, '00-lobby-alice');
  await A.click('text=Set sail');
  await A.waitForSelector('.combat', { timeout: 10000 });
  await B.waitForSelector('.combat', { timeout: 10000 }).catch(() => {});
  await A.waitForTimeout(2500);
  await shot(A, '01-start-alice'); await shot(B, '01-start-bob');

  await play(A);
  for (const ms of [150, 450, 900]) { await B.waitForTimeout(ms === 150 ? 150 : ms / 2); await shot(B, `02-bob-sees-alice-${ms}`); }
  await A.waitForTimeout(1500);
  await play(B);
  for (const ms of [150, 450, 900]) { await A.waitForTimeout(ms === 150 ? 150 : ms / 2); await shot(A, `03-alice-sees-bob-${ms}`); }
  await A.waitForTimeout(1500);

  await ready(A);
  await A.waitForTimeout(800);
  await shot(A, '04-alice-ready'); await shot(B, '04-bob-while-alice-ready');
  await ready(B);
  for (let i = 0; i < 6; i++) { await A.waitForTimeout(700); await shot(A, `05-enemies-alice-${i}`); }
  await B.waitForTimeout(4000);
  await shot(A, '06-after-alice'); await shot(B, '06-after-bob');

  console.log(problems.length ? 'PROBLEMS:\n' + problems.join('\n') : 'no problems');
  await browser.close();
  process.exit(problems.length ? 1 : 0);
})();
