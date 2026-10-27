// Small DOM helpers shared by the menus and the battle side panel.
import { spriteURL } from './art.js?v=11';

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
