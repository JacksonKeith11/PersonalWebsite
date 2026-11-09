// The DOM screens (title, lobby, results) and the HUD, plus controller navigation for every menu:
// the D-pad or left stick moves between [data-nav] elements, A / Enter presses, B / Esc goes back.
// An element with data-lr takes left/right itself (look and weapon pickers).
import { paintRig, atlas } from './rig.js?v=12';
import { heroFrames } from './hero.js?v=12';
import { sfx } from './audio.js?v=12';
import { skillKey, deviceOfSlot } from './input.js?v=12';

export const $ = (sel, el = document) => el.querySelector(sel);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export { esc };

const ui = () => document.getElementById('ui');
let focused = null;

// a stable name for a focusable element, so a redraw can put the focus back where it was
const keyOf = e => e.id ? '#' + e.id : [...e.attributes].filter(a => a.name.startsWith('data-') && a.name !== 'data-nav' && a.name !== 'data-lr').map(a => `${a.name}=${a.value}`).join('&');

export function show(html) {
  const el = ui();
  const was = focused && el.contains(focused) ? keyOf(focused) : null;
  el.innerHTML = html;
  focused = null;
  const again = was && [...el.querySelectorAll('[data-nav]')].find(e => keyOf(e) === was);
  const first = again || el.querySelector('[data-autofocus]') || el.querySelector('[data-nav]');
  if (first) setFocus(first, false);
  return el;
}
export function hide() { ui().innerHTML = ''; focused = null; }

function setFocus(el, sound = true) {
  if (focused) focused.classList.remove('focus');
  focused = el;
  if (!el) return;
  el.classList.add('focus');
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
export function buildHud(boss, heroes, colours, mineIds, skills = {}) {
  const el = document.getElementById('hud');
  el.hidden = false;
  el.innerHTML = `
    <div class="cards">${heroes.map(h => `
      <div class="card" id="card-${h.id}" style="--c:${colours[h.colour]}">
        <div class="top"><b>${esc(h.name)}</b><span class="flasks"></span></div>
        <div class="bar hp"><i class="lag"></i><i class="v"></i></div>
        ${mineIds.includes(h.id) ? '<div class="bar st"><i></i></div><div class="bar fo"><i></i></div>' : ''}
        ${mineIds.includes(h.id) && (h.skills || []).length ? `<div class="skills">${h.skills.map((id, i) => skills[id] ? `<span class="sk" data-sk="${id}" style="--k:${skills[id].col}">
          <kbd>${skillKey(deviceOfSlot(h.slot), i)}</kbd><b>${esc(skills[id].name)}</b><i></i></span>` : '').join('')}</div>` : ''}
        <div class="buffs"></div>
        <div class="downtxt"></div>
      </div>`).join('')}</div>
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
  for (const [id, row] of Object.entries(scene.heroRows)) {
    const c = document.getElementById('card-' + id);
    if (!c) continue;
    setBar(c.querySelector('.bar.hp'), pct(row.hp, row.mhp));
    c.querySelector('.flasks').textContent = '⚱'.repeat(row.flasks);
    c.classList.toggle('down', row.down > 0);
    // what's on them: a ward (and how much is left), extra damage (and for how long), a charged next hit
    const buffs = row.down ? '' : (row.shield > 0 ? `<span style="--k:#a8b0bc">Ward ${row.shield}</span>` : '')
      + (row.rally > 0 ? `<span style="--k:#ffb040">Damage up ${Math.ceil(row.rally)}s</span>` : '') + (row.emp ? '<span style="--k:#c8b4ff">Next hit charged</span>' : '');
    const bf = c.querySelector('.buffs');
    if (bf.dataset.v !== buffs) { bf.dataset.v = buffs; bf.innerHTML = buffs; }
    c.querySelector('.downtxt').textContent = row.down === 2 ? 'Fallen' : row.down === 1 ? (row.bleed ? `Down: revive within ${Math.ceil(row.bleed)}s` : 'Down') : '';
  }
  for (const l of scene.local) {
    const c = document.getElementById('card-' + l.id);
    if (!c) continue;
    const st = c.querySelector('.bar.st i'), fo = c.querySelector('.bar.fo i');
    if (st) st.style.width = pct(l.st, l.maxSt);
    if (fo) fo.style.width = pct(l.focus, l.HERO.focus);
    for (const chip of c.querySelectorAll('.sk')) {  // greyed, with the seconds left, while it cools down
      const left = l.skillCd[chip.dataset.sk] || 0, txt = left > 0 ? String(Math.ceil(left)) : '';
      chip.classList.toggle('cool', left > 0);
      chip.classList.toggle('no', !!l.denied && l.denied.id === chip.dataset.sk && performance.now() < l.denied.until);
      const n = chip.lastElementChild;
      if (n.textContent !== txt) n.textContent = txt;
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
