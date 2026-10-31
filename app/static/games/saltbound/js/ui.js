// DOM helpers, the icon set, tooltips, toasts and modals. Everything on screen is built with h().

export const $ = id => document.getElementById(id);

export function h(tag, attrs, ...kids) {
  const m = tag.match(/#([\w-]+)/);
  const id = m && m[1];
  const [name, ...classes] = tag.replace(/#[\w-]+/, '').split('.');
  const el = document.createElement(name || 'div');
  if (id) el.id = id;
  if (classes.length) el.className = classes.join(' ');
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === 'class') el.className += (el.className ? ' ' : '') + v;
      else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else if (k === 'tip') el.dataset.tip = v;
      else if (k === 'html') el.innerHTML = v;
      else el.setAttribute(k, v === true ? '' : v);
    }
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

// ------------------------------------------------------------------ icons: 24px line icons
const P = {
  coin: '<circle cx="12" cy="12" r="8"/><path d="M12 8v8M9.5 10h4a1.5 1.5 0 0 1 0 3h-3a1.5 1.5 0 0 0 0 3h4"/>',
  heart: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
  shield: '<path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z"/>',
  sword: '<path d="M14 4h6v6L9 21l-3-3zM5 15l4 4M3 21l3-3"/>',
  boot: '<path d="M7 3h6v9l6 3v4H5V9"/><path d="M5 15h14"/>',
  wave: '<path d="M2 15c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2M2 19c2.5 0 2.5-2 5-2s2.5 2 5 2 2.5-2 5-2 2.5 2 5 2M12 3v7M9 7l3 3 3-3"/>',
  moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
  star: '<path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z"/>',
  feather: '<path d="M20 4c-8 0-13 5-13 12v4M7 16h7M10 12h7c2-2 3-5 3-8"/>',
  flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
  menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
  list: '<path d="M9 6h11M9 12h11M9 18h11M4 6h1M4 12h1M4 18h1"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  skull: '<path d="M12 3a7 7 0 0 0-7 7c0 2.5 1.3 4 3 5v3h8v-3c1.7-1 3-2.5 3-5a7 7 0 0 0-7-7z"/><circle cx="9.5" cy="10.5" r="1.5"/><circle cx="14.5" cy="10.5" r="1.5"/><path d="M10 18v3M14 18v3"/>',
  flame: '<path d="M12 21c-4 0-6-2.5-6-6 0-4 4-6 4-10 3 2 4 4 4 6 1-1 1.5-2 1.5-3 2 2 2.5 4 2.5 7 0 3.5-2 6-6 6z"/>',
  drop: '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
  snow: '<path d="M12 3v18M4.2 7.5l15.6 9M4.2 16.5l15.6-9M9.5 4.5L12 7l2.5-2.5M9.5 19.5L12 17l2.5 2.5"/>',
  bolt: '<path d="M13 2L4 14h7l-1 8 9-12h-7z"/>',
  down: '<path d="M12 4v15M6 13l6 6 6-6"/>',
  up: '<path d="M12 20V5M6 11l6-6 6 6"/>',
  crack: '<path d="M12 3l-2 6 4 3-3 4 2 5M5 5l14 14"/>',
  target: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
  root: '<path d="M12 3v8M12 11c-3 0-5 2-5 5v5M12 11c3 0 5 2 5 5v5M12 11v10"/>',
  clock: '<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  eye: '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  spark: '<path d="M12 3v5M12 16v5M3 12h5M16 12h5M6 6l3 3M15 15l3 3M18 6l-3 3M9 15l-3 3"/>',
  dice: '<rect x="4" y="4" width="16" height="16" rx="3"/><circle cx="9" cy="9" r="1.2"/><circle cx="15" cy="15" r="1.2"/><circle cx="15" cy="9" r="1.2"/><circle cx="9" cy="15" r="1.2"/>',
  bag: '<path d="M5 8h14l-1 12H6zM9 8V6a3 3 0 0 1 6 0v2"/>',
  anchor: '<circle cx="12" cy="5" r="2"/><path d="M12 7v14M8 11h8M5 14a7 7 0 0 0 14 0"/>',
  bed: '<path d="M3 18V8M3 14h18v4M21 14v-2a3 3 0 0 0-3-3h-7v5M7 12a1.5 1.5 0 1 0 0-.1"/>',
  scroll: '<path d="M7 4h11a2 2 0 0 1 2 2v2h-4M7 4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2V8M7 4a2 2 0 0 1 2 2v12M11 9h4M11 13h4"/>',
  refresh: '<path d="M20 12a8 8 0 1 1-2.3-5.7M20 4v5h-5"/>',
  check: '<path d="M5 12l5 5 9-10"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  person: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>',
  link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4 12H2M22 12h-2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1"/>',
  hand: '<path d="M8 13V5a1.5 1.5 0 0 1 3 0v6M11 11V4a1.5 1.5 0 0 1 3 0v7M14 11V5a1.5 1.5 0 0 1 3 0v8c0 4-2.5 8-7 8-3 0-4.5-1.5-6-4l-2-3.5a1.5 1.5 0 0 1 2.5-1.5L8 15"/>',
  rest: '<path d="M4 18h16M6 18l3-8h6l3 8M10 10l2-5 2 5"/>',
  sail: '<path d="M12 3v15M12 4l7 11h-7M12 7L6 15h6M3 19c3 2 15 2 18 0"/>',
};
export function icon(name, cls = '') {
  const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  s.setAttribute('viewBox', '0 0 24 24');
  s.setAttribute('class', 'icon-svg ' + cls);
  s.setAttribute('fill', 'none');
  s.setAttribute('stroke', 'currentColor');
  s.setAttribute('stroke-width', '1.8');
  s.setAttribute('stroke-linecap', 'round');
  s.setAttribute('stroke-linejoin', 'round');
  s.setAttribute('aria-hidden', 'true');
  s.innerHTML = P[name] || P.spark;
  return s;
}

// ------------------------------------------------------------------ tooltips: any element with data-tip
const tip = () => $('tip');
let tipFor = null;
document.addEventListener('pointerover', e => {
  const el = e.target.closest?.('[data-tip]');
  if (!el) { if (tipFor) { tip().hidden = true; tipFor = null; } return; }
  if (el === tipFor) return;
  tipFor = el;
  const [title, ...rest] = el.dataset.tip.split('\n');
  tip().replaceChildren(h('b', null, title), ...rest.map(r => h('div', null, r)));
  tip().hidden = false;
  place(el);
});
document.addEventListener('pointerout', e => {
  if (tipFor && !tipFor.contains(e.relatedTarget)) { tip().hidden = true; tipFor = null; }
});
function place(el) {
  const r = el.getBoundingClientRect(), t = tip(), tr = t.getBoundingClientRect();
  let x = r.left + r.width / 2 - tr.width / 2, y = r.top - tr.height - 8;
  if (y < 8) y = r.bottom + 8;
  x = Math.max(8, Math.min(innerWidth - tr.width - 8, x));
  t.style.left = x + 'px'; t.style.top = y + 'px';
}
export function hideTip() { tip().hidden = true; tipFor = null; }

// ------------------------------------------------------------------ toasts
export function toast(text, kind = '') {
  const el = h('div.toast' + (kind ? '.' + kind : ''), null, text);
  $('toasts').append(el);
  setTimeout(() => el.remove(), kind === 'big' ? 2600 : 3200);
}

// ------------------------------------------------------------------ modal
export function modal(content, { wide = false, onClose = null, enter = true } = {}) {
  const box = h('div.modal.panel' + (wide ? '.wide' : ''), { role: 'dialog', 'aria-modal': 'true' }, content);
  const scrim = h('div.scrim' + (enter ? '.enter' : ''), null, box);
  if (onClose) scrim.addEventListener('click', e => { if (e.target === scrim) onClose(); });
  return scrim;
}

export const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
