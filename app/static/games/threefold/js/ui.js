// Small DOM helpers shared by the menus and the battle side panel.
import { spriteURL } from './art.js?v=40';
import { STATUS_HELP, STATUS_WORDS } from './data.js?v=40';
import { describeParts } from './rules.js?v=40';

export function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') el.className = v;
    else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
    else if (v !== false && v != null) el.setAttribute(k, v === true ? '' : v);
  }
  for (const c of kids.flat()) {
    if (c == null || c === false) continue;
    el.append(c.nodeType ? c : document.createTextNode(String(c)));
  }
  return el;
}

export const sprImg = (name, cls = '') => h('img', { class: 'spr ' + cls, src: spriteURL(name), alt: '' });

export function bar(v, max, foe, shield = 0) {
  const total = Math.max(max, v + shield);
  return h('div', { class: 'bar' + (foe ? ' foe' : '') },
    h('i', { style: `width:${Math.max(0, 100 * v / total)}%` }),
    shield > 0 ? h('b', { style: `width:${100 * shield / total}%` }) : null);
}

// ---------- status tooltips ----------
// Any element with data-tip shows it in one floating box: on hover with a mouse, on tap on a phone.
export const tip = (label, key) => STATUS_HELP[key] ? h('span', { class: 'tip', tabindex: 0, 'data-tip': STATUS_HELP[key] }, label) : label;
// The same, with the text given directly (an artifact's description, say).
export const tipNote = (label, text) => text ? h('span', { class: 'tip', tabindex: 0, 'data-tip': text }, label) : label;

// Skill text with the status words in it ("Slows", "Shocks") made hoverable.
const WORD_RE = new RegExp(`\\b(${Object.keys(STATUS_WORDS).join('|')})\\b`, 'g');
export function tipText(str) {
  const out = [];
  let last = 0;
  for (const m of str.matchAll(WORD_RE)) {
    out.push(str.slice(last, m.index), tip(m[0], STATUS_WORDS[m[0]]));
    last = m.index + m[0].length;
  }
  out.push(str.slice(last));
  return out;
}

// A skill's description laid out for reading: one line of basics (reach, power, cooldown), then its
// extra effects as chips (costs in red), then its flavour text.
export function skillText(o, src) {
  const d = describeParts(o, src), chip = (t, cls) => h('span', { class: 'fx' + (cls ? ' ' + cls : '') }, tipText(t));
  return h('div', { class: 'sk' },
    h('div', { class: 'sk-head' }, d.head.join(' · ')),
    d.fx.length || d.cost.length ? h('div', { class: 'sk-fx' }, d.fx.map(t => chip(t)), d.cost.map(t => chip(t, 'cost'))) : null,
    o.txt ? h('div', { class: 'sk-txt' }, o.txt) : null);
}

let box = null, anchor = null, touch = false;
function place() {
  const r = anchor.getBoundingClientRect(), b = box.getBoundingClientRect(), pad = 8;
  let x = r.left + r.width / 2 - b.width / 2, y = r.top - b.height - 6;
  if (y < pad) y = r.bottom + 6;
  x = Math.max(pad, Math.min(window.innerWidth - b.width - pad, x));
  box.style.left = `${x}px`; box.style.top = `${y}px`;
}
function showTip(el) {
  anchor = el;
  box.textContent = el.dataset.tip;
  box.hidden = false;
  place();
}
function hideTip() { anchor = null; if (box) box.hidden = true; }
export function initTips() {
  box = h('div', { id: 'tipbox', role: 'tooltip', hidden: true });
  document.body.append(box);
  const at = e => e.target.closest && e.target.closest('[data-tip]');
  document.addEventListener('pointerdown', e => { touch = e.pointerType !== 'mouse'; }, true);
  document.addEventListener('pointerover', e => { if (e.pointerType === 'mouse' && at(e)) showTip(at(e)); });
  document.addEventListener('pointerout', e => { if (e.pointerType === 'mouse' && anchor && at(e) === anchor && !anchor.contains(e.relatedTarget)) hideTip(); });
  document.addEventListener('focusin', e => { if (!touch && at(e)) showTip(at(e)); });
  document.addEventListener('focusout', () => { if (!touch) hideTip(); });
  // on a phone a tap on a status shows its tip instead of pressing the card it sits in
  document.addEventListener('click', e => {
    const el = at(e);
    if (el && touch) { e.preventDefault(); e.stopPropagation(); if (anchor === el) hideTip(); else showTip(el); }
    else if (!el) hideTip();
  }, true);
  document.addEventListener('scroll', hideTip, true);
  // the battle panel redraws often; drop the tip once its word is gone
  setInterval(() => { if (anchor && !anchor.isConnected) hideTip(); }, 250);
}
