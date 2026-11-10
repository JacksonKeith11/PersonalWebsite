// The DOM screens (title, lobby, results) and the HUD, plus controller navigation for every menu:
// the D-pad or left stick moves between [data-nav] elements, A / Enter presses, B / Esc goes back.
// An element with data-lr takes left/right itself (look and weapon pickers).
import { paintRig, atlas } from './rig.js?v=23';
import { heroFrames } from './hero.js?v=23';
import { sfx } from './audio.js?v=23';
import { skillKey, deviceOfSlot } from './input.js?v=23';

export const $ = (sel, el = document) => el.querySelector(sel);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export { esc };

// Menus live in #ui. One more can be laid over it (the in-run menu, openMenu): while it is up it is the
// one the controller and the keys steer, and #ui underneath can still be redrawn.
const base = () => document.getElementById('ui');
let overlay = null, under = null;   // the overlay's element; what was focused beneath it
const ui = () => overlay || base();
let focused = null;

export function openMenu(html) {
  closeMenu();
  under = focused; focused = null;
  overlay = document.createElement('div');
  overlay.id = 'menu';
  overlay.innerHTML = html;
  document.body.appendChild(overlay);
  hideTip();
  const first = overlay.querySelector('[data-autofocus]') || overlay.querySelector('[data-nav]');
  if (first) setFocus(first, false);
  return overlay;
}
export function closeMenu() {
  if (!overlay) return;
  overlay.remove(); overlay = null;
  hideTip();
  focused = under && document.contains(under) ? under : null;
  under = null;
}

// a stable name for a focusable element, so a redraw can put the focus back where it was
const keyOf = e => e.id ? '#' + e.id : [...e.attributes].filter(a => a.name.startsWith('data-') && a.name !== 'data-nav' && a.name !== 'data-lr').map(a => `${a.name}=${a.value}`).join('&');

export function show(html) {
  const el = base();
  if (overlay) { el.innerHTML = html; under = null; return el; }   // redrawn beneath the menu: leave the focus with the menu
  const was = focused && el.contains(focused) ? keyOf(focused) : null;
  el.innerHTML = html;
  focused = null;
  hideTip();
  const again = was && [...el.querySelectorAll('[data-nav]')].find(e => keyOf(e) === was);
  const first = again || el.querySelector('[data-autofocus]') || el.querySelector('[data-nav]');
  if (first) setFocus(first, false);
  // some screens add parts after show() returns (the lobby's hero rows): look again once they're in
  if (was && !again) queueMicrotask(() => {
    const late = !overlay && focused === first && [...el.querySelectorAll('[data-nav]')].find(e => keyOf(e) === was);
    if (late) setFocus(late, false);
  });
  return el;
}
export function hide() { base().innerHTML = ''; if (overlay) under = null; else { focused = null; hideTip(); } }

// A tooltip for anything with data-tip (text), data-tip-h (a heading) and data-tip-k (a line under it):
// the blessings and skills a hero holds. It shows on hover, and when a controller's focus lands on it.
let tipFor = null;
function tipEl() {
  let t = document.getElementById('tip');
  if (!t) { t = document.createElement('div'); t.id = 'tip'; t.hidden = true; document.body.appendChild(t); }
  return t;
}
function showTip(el) {
  const t = tipEl(), d = el.dataset;
  tipFor = el;
  t.innerHTML = `${d.tipH ? `<b>${esc(d.tipH)}</b>` : ''}${d.tipK ? `<i>${esc(d.tipK)}</i>` : ''}<span>${esc(d.tip)}</span>`;
  t.style.setProperty('--r', el.style.getPropertyValue('--r') || 'var(--gold)');
  t.hidden = false;
  const r = el.getBoundingClientRect(), w = t.offsetWidth, h = t.offsetHeight;
  t.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left + r.width / 2 - w / 2)) + 'px';
  t.style.top = (r.top - h - 8 >= 8 ? r.top - h - 8 : r.bottom + 8) + 'px';   // above it, or below when there's no room
}
function hideTip() { tipFor = null; const t = document.getElementById('tip'); if (t) t.hidden = true; }
addEventListener('mouseover', e => { const el = e.target.closest && e.target.closest('[data-tip]'); if (el) showTip(el); else if (tipFor && tipFor !== focused) hideTip(); });
addEventListener('scroll', () => { if (tipFor) hideTip(); }, true);
// a click moves the focus too, so a redraw puts it back on what was clicked, not on the screen's default
addEventListener('pointerdown', e => { const t = e.target.closest && e.target.closest('[data-nav]'); if (t && ui().contains(t)) setFocus(t, false); }, true);

function setFocus(el, sound = true) {
  if (focused) focused.classList.remove('focus');
  focused = el;
  if (!el) return;
  el.classList.add('focus');
  el.dataset.tip ? showTip(el) : hideTip();
  if (document.activeElement !== el && (el.tagName === 'INPUT' || el.tagName === 'BUTTON')) el.focus({ preventScroll: true });
  el.scrollIntoView({ block: 'nearest' });
  if (sound) sfx.ui();
}

function move(dx, dy) {
  const all = [...ui().querySelectorAll('[data-nav]')].filter(e => e.offsetParent && !e.disabled);
  if (!all.length) return;
  if (!focused || !all.includes(focused)) { setFocus(all[0]); return; }
  const r = focused.getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  let best = null, bestS = Infinity;
  for (const e of all) {
    if (e === focused) continue;
    const q = e.getBoundingClientRect(), x = q.left + q.width / 2 - cx, y = q.top + q.height / 2 - cy;
    const along = x * dx + y * dy, across = Math.abs(x * dy - y * dx);
    if (along <= 4) continue;
    const s = along + across * 2.5;
    if (s < bestS) { bestS = s; best = e; }
  }
  if (best) setFocus(best);
}

// call every frame while a menu is up
export function navFrame(input) {
  const el = ui();
  if (!el.firstChild) return;
  if (document.activeElement && document.activeElement !== focused && el.contains(document.activeElement) && document.activeElement.matches('[data-nav]')) {
    setFocus(document.activeElement, false);
  }
  for (const d of input.devices()) {
    const typing = d.id === 'kb' && document.activeElement && document.activeElement.tagName === 'INPUT';
    const lr = focused && focused.hasAttribute('data-lr');
    if (d.pressed('up')) !(typing && d.id === 'kb' && false) && move(0, -1);
    if (d.pressed('down')) move(0, 1);
    if (d.pressed('left') && !typing) lr ? focused.dispatchEvent(new CustomEvent('lr', { detail: -1 })) : move(-1, 0);
    if (d.pressed('right') && !typing) lr ? focused.dispatchEvent(new CustomEvent('lr', { detail: 1 })) : move(1, 0);
    if (d.id !== 'kb' && d.pressed('confirm') && focused) { focused.tagName === 'INPUT' ? focused.focus() : focused.click(); }
    if (d.pressed('back')) { const b = el.querySelector('[data-back]'); if (b && (!typing || d.id !== 'kb')) { sfx.uiBack(); b.click(); } }
  }
}

// ------------------------------------------------------------------ portraits
let atlasImg = null;
export function setAtlasImage(img) { atlasImg = img; }

export function portrait(h, W, size = 72) {
  const cv = document.createElement('canvas');
  cv.width = 48; cv.height = 48;
  const g = cv.getContext('2d');
  g.imageSmoothingEnabled = false;
  if (atlasImg && W) paintRig(g, atlasImg, 'hero', heroFrames(h, W), { weapon: 40 }, 22, 46);
  cv.style.width = cv.style.height = size + 'px';
  return cv;
}

export const LOOK_NAMES = { knight: 'Knight', pilgrim: 'Pilgrim', hunter: 'Witch Hunter', sellsword: 'Sellsword' };

// ------------------------------------------------------------------ HUD
// The HUD. This browser's heroes each get a panel at the bottom left (one online; one per couch player,
// side by side): health, Focus, dash pips, then tiles for the flask (how many are left), each skill (its
// cooldown sweeping away, with the seconds) and the special (lit when there's Focus for it), each with
// the key to press. Everyone else is a small card at the top left; the boss's bars are top centre.
const FLASK = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M6 1h4v2l-1 1v2.2c2.4.9 4 2.7 4 5 0 2.3-2.2 3.8-5 3.8s-5-1.5-5-3.8c0-2.3 1.6-4.1 4-5V4L6 3z" fill="currentColor"/></svg>';
// a hero's HUD key hints, for the device driving it now (the keyboard's hero also answers to a spare controller)
export function hudKeys(id, dev) {
  const card = document.getElementById('card-' + id);
  if (!card) return;
  const kb = dev === 'kb', set = (sel, k) => { const e = card.querySelector(sel); if (e) e.textContent = k; };
  set('.flask kbd', kb ? 'R' : 'X'); set('.spc kbd', kb ? 'Q' : 'Y');
  card.querySelectorAll('.sk kbd').forEach((e, i) => { e.textContent = skillKey(dev, i); });
}
const tile = (cls, key, body, attrs = '') => `<span class="tile ${cls}" ${attrs}><kbd>${key}</kbd>${body}<u></u><i></i></span>`;

export function buildHud(boss, heroes, colours, mineIds, skills = {}, weapons = {}) {
  const el = document.getElementById('hud');
  el.hidden = false;
  const mine = heroes.filter(h => mineIds.includes(h.id)), others = heroes.filter(h => !mineIds.includes(h.id));
  el.innerHTML = `
    <div class="cards">${others.map(h => `
      <div class="card" id="card-${h.id}" style="--c:${colours[h.colour]}">
        <div class="top"><b>${esc(h.name)}</b><span class="flasks"></span></div>
        <div class="bar hp"><i class="lag"></i><i class="v"></i></div>
        <div class="buffs"></div>
        <div class="downtxt"></div>
      </div>`).join('')}</div>
    <div class="mine">${mine.map(h => {
      const dev = deviceOfSlot(h.slot), W = weapons[h.weapon] || {}, kb = dev === 'kb';
      return `
      <div class="card me" id="card-${h.id}" style="--c:${colours[h.colour]}">
        <div class="buffs"></div>
        <div class="downtxt"></div>
        <div class="top"><b>${esc(h.name)}</b><span class="hpn"></span></div>
        <div class="bar hp"><i class="lag"></i><i class="v"></i></div>
        <div class="bar fo"><i></i></div>
        <div class="pips" title="Dashes"></div>
        <div class="tiles">
          ${tile('flask', kb ? 'R' : 'X', `${FLASK}<em></em><b>Flask</b>`)}
          ${(h.skills || []).map((id, i) => skills[id] ? tile('sk', skillKey(dev, i), `<b>${esc(skills[id].name)}</b>`, `data-sk="${id}" style="--k:${skills[id].col}"`) : '').join('')}
          ${W.special ? tile('spc', kb ? 'Q' : 'Y', `<b>${esc(W.special.name)}</b>`) : ''}
        </div>
      </div>`; }).join('')}</div>
    <div class="bossbar">${(boss.bodies || [boss]).map((b, e) => `<div class="bbody" id="bb-${e}"><div class="bname">${esc(b.name || boss.name)}</div>
      <div class="bar"><i class="lag"></i><i class="v"></i></div><div class="bar poise"><i></i></div>
      <div class="statuses">${STATUS.map(([k, name, col]) => `<span class="stm" data-st="${k}" style="--k:${col}" hidden><b>${name}</b><span class="bar"><i></i></span></span>`).join('')}</div></div>`).join('')}</div>
    <div class="lockhint"></div>`;
  return el;
}

// the statuses heroes build on a boss, in the server's order (STATUSES in fight.py)
const STATUS = [['burn', 'Burn', '#ff8a3a'], ['frost', 'Frost', '#7fe3ff'], ['bleed', 'Bleed', '#e04a5a'], ['rot', 'Rot', '#8be04e']];

const pct = (a, b) => `${Math.max(0, Math.min(100, (a / Math.max(1, b)) * 100))}%`;
function setBar(bar, v) {
  if (!bar) return;
  const [lag, val] = bar.querySelectorAll('i');
  if (val) { val.style.width = v; lag.style.width = v; } else lag.style.width = v;
}

export function updateHud(scene) {
  scene.boss.bodies.forEach((B, e) => {
    const bb = document.getElementById('bb-' + e);
    if (!bb) return;
    setBar(bb.querySelector('.bar:not(.poise)'), pct(B.hp, B.mhp));
    bb.querySelector('.poise i').style.width = pct(B.poise, B.mpoise);
    bb.style.opacity = B.hp > 0 ? 1 : 0.4;
    // a meter appears once someone has built some of that status, fills toward its burst, and glows
    // while the status is in force (the 4 s after a burst; Rot while it's eating)
    bb.querySelectorAll('.stm').forEach((el, i) => {
      const v = (B.meters || [])[i] || 0, on = !!(B.live || [])[i];
      el.hidden = !(v > 0 || on) || B.hp <= 0;
      el.classList.toggle('live', on);
      el.querySelector('i').style.width = v + '%';
    });
  });
  const text = (el, v) => { if (el && el.textContent !== v) el.textContent = v; };
  for (const [id, row] of Object.entries(scene.heroRows)) {
    const c = document.getElementById('card-' + id);
    if (!c) continue;
    setBar(c.querySelector('.bar.hp'), pct(row.hp, row.mhp));
    text(c.querySelector('.flasks'), '●'.repeat(row.flasks));
    text(c.querySelector('.hpn'), `${Math.max(0, Math.ceil(row.hp))} / ${row.mhp}`);
    c.classList.toggle('down', row.down > 0);
    c.classList.toggle('low', !row.down && row.hp / row.mhp < 0.3);
    // what's on them: a ward (and how much is left), extra damage (and for how long), a charged next hit
    const buffs = row.down ? '' : (row.shield > 0 ? `<span style="--k:#a8b0bc">Ward ${row.shield}</span>` : '')
      + (row.rally > 0 ? `<span style="--k:#ffb040">Damage up ${Math.ceil(row.rally)}s</span>` : '') + (row.emp ? '<span style="--k:#c8b4ff">Next hit charged</span>' : '');
    const bf = c.querySelector('.buffs');
    if (bf.dataset.v !== buffs) { bf.dataset.v = buffs; bf.innerHTML = buffs; }
    text(c.querySelector('.downtxt'), row.down === 2 ? 'Fallen' : row.down === 1 ? (row.bleed ? `Down: revive within ${Math.ceil(row.bleed)}s` : 'Down') : '');
    const fl = c.querySelector('.tile.flask');
    if (fl) { text(fl.querySelector('em'), String(row.flasks)); fl.classList.toggle('empty', !row.flasks); }
  }
  // a tile's cooldown: `u` (1 just used .. 0 ready) is the share still shaded, `n` the number over it
  const cool = (el, u, n) => {
    const v = u > 0 ? (u * 100).toFixed(0) + '%' : '0%';
    if (el.dataset.u !== v) { el.dataset.u = v; el.style.setProperty('--u', v); }
    el.classList.toggle('cool', u > 0);
    text(el.lastElementChild, n);
  };
  for (const l of scene.local) {
    const c = document.getElementById('card-' + l.id);
    if (!c) continue;
    const fo = c.querySelector('.bar.fo i');
    if (fo) fo.style.width = pct(l.focus, l.HERO.focus);
    for (const chip of c.querySelectorAll('.sk')) {  // shaded, with the seconds left, while it cools down
      const S = l.skills.find(k => k.id === chip.dataset.sk), left = Math.max(0, l.skillCd[chip.dataset.sk] || 0);
      cool(chip, S ? Math.min(1, left / (S.cd * (l.S.skill_cd || 1))) : 0, left > 0 ? String(Math.ceil(left)) : '');
      chip.classList.toggle('no', !!l.denied && l.denied.id === chip.dataset.sk && performance.now() < l.denied.until);
    }
    const sp = c.querySelector('.tile.spc');  // the special fills with Focus
    if (sp) { const need = l.specialCost(); cool(sp, l.focus >= need ? 0 : 1 - l.focus / need, ''); }
    // dashes: a pip each, the one coming back filling from the left; they shake when a dodge is refused
    const pips = c.querySelector('.pips');
    if (pips) {
      if (pips.children.length !== l.maxDash) pips.innerHTML = '<i><b></b></i>'.repeat(l.maxDash);
      [...pips.children].forEach((pip, i) => {
        const f = Math.max(0, Math.min(1, l.dashes - i)), v = f >= 1 ? '1' : String(Math.round(f * 20) / 20);
        if (pip.dataset.v !== v) { pip.dataset.v = v; pip.classList.toggle('on', f >= 1); pip.firstChild.style.width = f * 100 + '%'; }
      });
      pips.classList.toggle('no', performance.now() < l.noDash);
    }
  }
  const lh = document.querySelector('.lockhint');
  if (lh) lh.textContent = scene.local.some(l => l.locked) ? 'Locked on' : '';
}

export function banner(kind) {
  const el = document.getElementById('hud');
  const b = document.createElement('div');
  b.className = 'banner ' + kind;
  b.innerHTML = kind === 'won' ? 'VANQUISHED' : 'FALLEN<small>the party is down</small>';
  el.appendChild(b);
  setTimeout(() => b.remove(), 3300);
}

export function hideHud() { const el = document.getElementById('hud'); el.hidden = true; el.innerHTML = ''; }
