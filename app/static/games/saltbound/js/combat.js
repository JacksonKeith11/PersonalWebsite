// The fight overlay: the two sides in their rows, enemy intents, the party's plan, and your dice
// tray and actions. When a round resolves, the server's effects are played back one at a time on
// a copy of the fight as it was, then the new state is shown.
import { S, send, mine } from './store.js?v=9';
import { h, icon, toast, hideTip } from './ui.js?v=9';
import { spriteURL } from './art.js?v=9';
import { reqText, checkReq, STATUS, dieLabel } from './rules.js?v=9';
import { render } from './main.js?v=9';
import * as sfx from './audio.js?v=9';

const C = { sel: new Set(), pending: null, tab: null, hidden: false, playing: false, display: null, hp: null, anim: {}, floats: {}, lastId: null, lastRound: null };
let host = null;

export function combatOpen() {
  const f = C.playing ? C.display : S.game?.fight;
  if (!f) return false;
  const inIt = mine().some(x => f.heroes.includes(x));
  return inIt || !C.hidden;
}
export function showFight() { C.hidden = false; render(); }
export function combatBusy() { return C.playing || queue.length > 0; }

const KEYS = ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'];
const INTENT = {
  attack: ['sword', 'var(--intent-attack)'], row: ['sword', 'var(--intent-attack)'], all: ['skull', 'var(--intent-attack)'],
  block: ['shield', 'var(--intent-defend)'], guard: ['shield', 'var(--intent-defend)'], heal: ['plus', 'var(--intent-heal)'],
  buff: ['up', 'var(--intent-buff)'], debuff: ['eye', 'var(--intent-debuff)'], summon: ['spark', 'var(--intent-buff)'],
  charge: ['bolt', 'var(--intent-buff)'], dazed: ['clock', 'var(--muted)'],
};
const INTENT_TEXT = {
  attack: 'Attack', row: 'Hits a whole row', all: 'Hits everyone', block: 'Defend', guard: 'Shields an ally', heal: 'Heals an ally',
  buff: 'Strengthens allies for the rest of the fight', debuff: 'Curses a hero', summon: 'Calls for help', charge: 'Gathering power…', dazed: 'Caught off guard: does nothing this round',
};

function fightTitle(f) {
  const st = S.static;
  if (f.kind === 'boss') return 'The Drowned Crown';
  if (f.kind === 'dungeon') return `${st.dungeons[f.region]} · fight ${f.step + 1} of 3`;
  if (f.kind === 'lair') return 'Lair';
  if (f.kind === 'event') return 'Trouble';
  return 'Skirmish';
}

// ------------------------------------------------------------------ rendering
export function renderCombat(el) {
  host = el;
  const f = C.playing ? C.display : S.game.fight;
  if (!f || !combatOpen()) { el.replaceChildren(); return; }
  if (f.id !== C.lastId) { C.lastId = f.id; C.sel.clear(); C.pending = null; C.hidden = false; if (!S.seenHints.fight) toast('Pick dice, then an action they fit. Ready up when you’re done.'); }
  if (f.round !== C.lastRound) { C.lastRound = f.round; C.sel.clear(); C.pending = null; C.rolled = true; }
  const g = S.game;
  const my = mine().filter(x => f.heroes.includes(x) && heroActive(f, x));
  if (C.tab === null || !my.includes(C.tab)) C.tab = my.includes(S.sel) ? S.sel : my[0] ?? null;
  const active = C.tab;
  const hpOf = x => (C.playing && C.hp ? C.hp[x] : g.heroes[x].hp);
  const prev = C.playing ? {} : preview(f);

  const unitHero = x => {
    const hs = f.hs[x], hero = g.heroes[x];
    const max = hero.maxhp;
    const st = hs ? hs.st : {};
    const cl = ['unit', 'hero'];
    if (hs?.down) cl.push('down');
    if (hs?.fled) cl.push('fled');
    if (C.anim['h' + x]) cl.push(C.anim['h' + x]);
    if (x === active) cl.push('mine-sel');
    if (isTarget('h' + x, f)) cl.push('target');
    const ready = hs?.ready && !C.playing;
    return h('div.' + cl.join('.'), { 'data-uid': 'h' + x, style: { '--seat': `var(--hero-${x})` }, onclick: () => targetClick('h' + x) },
      h('div.intent' + (ready ? '' : '.none'), { style: { '--c': 'var(--ok)' } }, icon('check'), 'Ready'),
      h('img.pix', { src: spriteURL(hero.cls), alt: '' }),
      h('div.uname', { style: { color: `var(--hero-${x})` } }, hero.name, f.taunt === x ? ' · taunting' : '', Object.values(f.guard || {}).includes(x) ? ' · guarding' : ''),
      hpBar(hpOf(x), max),
      previewRow('h' + x, prev),
      statusRow(st, hs?.down ? ['Knocked down'] : []),
      floats('h' + x));
  };
  const unitFoe = fo => {
    const d = S.static.foes[fo.k];
    const cl = ['unit', 'foe'];
    if (d.boss) cl.push('boss');
    if (fo.hp <= 0) cl.push('dead');
    if (C.anim['f' + fo.id]) cl.push(C.anim['f' + fo.id]);
    if (isTarget('f' + fo.id, f)) cl.push('target');
    return h('div.' + cl.join('.'), { 'data-uid': 'f' + fo.id, onclick: () => targetClick('f' + fo.id), tip: foeTip(fo) },
      intentChip(fo, f),
      h('img.pix', { src: spriteURL(fo.k), alt: '' }),
      h('div.uname', null, fo.name),
      hpBar(Math.max(0, fo.hp), fo.max),
      previewRow('f' + fo.id, prev, fo.hp),
      statusRow(fo.st, fo.might ? [`+${fo.might} might`] : []),
      floats('f' + fo.id));
  };
  const unitAlly = a => {
    const cl = ['unit', 'hero', 'summon'];
    if (a.hp <= 0) cl.push('dead');
    if (C.anim['s' + a.id]) cl.push(C.anim['s' + a.id]);
    return h('div.' + cl.join('.'), { 'data-uid': 's' + a.id, tip: `${a.name}\nSummoned by ${g.heroes[a.owner].name}${a.atk ? `. Hits ${a.all ? 'every enemy' : 'the weakest front enemy'} for ${a.atk} each round.` : '. Soaks up hits.'}` },
      h('div.intent.none', null, '·'),
      h('img.pix', { src: spriteURL(a.k), alt: '' }),
      h('div.uname', { style: { color: `var(--hero-${a.owner})` } }, a.name),
      hpBar(Math.max(0, a.hp), a.max),
      previewRow('s' + a.id, prev),
      h('div.sts'),
      floats('s' + a.id));
  };
  const alliesIn = row => (f.allies || []).filter(a => a.row === row && (a.hp > 0 || C.playing));
  const heroesIn = row => f.heroes.filter(x => f.hs[x].row === row);
  const foesIn = row => f.foes.filter(fo => fo.row === row && (fo.hp > 0 || C.playing));

  // three or more in a column: shrink them so the column fits
  const col = (label, units) => h('div.col' + (units.length >= 3 ? '.crowd' : ''), null, h('span.lbl', null, label), ...units);
  const stage = h('div.stage', null,
    h('div.side-units', null,
      col('Back', [...heroesIn('back').map(unitHero), ...alliesIn('back').map(unitAlly)]),
      col('Front', [...heroesIn('front').map(unitHero), ...alliesIn('front').map(unitAlly)])),
    h('div.side-units', null,
      col('Front', foesIn('front').map(unitFoe)),
      col('Back', foesIn('back').map(unitFoe))));

  const plan = h('div.planstrip', null, h('span.eyebrow', null, 'Plan'),
    f.plan.length ? f.plan.map((p, i) => planChip(p, i, f)) : h('span.muted', { style: { fontSize: '14px' } }, 'Placed actions show here, in the order they’ll happen.'));

  let bottom;
  const spiritMine = mine().filter(x => f.spirit?.[x] && !f.spirit[x].used);
  if (active !== null && !C.playing) bottom = tray(f, active, my);
  else if (spiritMine.length && !C.playing) bottom = spiritBar(f, spiritMine[0]);
  else {
    const waiting = f.heroes.filter(x => heroActive(f, x) && !f.hs[x].ready).map(x => g.heroes[x].name);
    bottom = h('div.watch', null, h('span', null, C.playing ? 'Resolving…' : waiting.length ? `Waiting for ${waiting.join(', ')}` : ''),
      !mine().some(x => f.heroes.includes(x)) ? h('button.btn', { onclick: () => { C.hidden = true; hideTip(); render(); } }, 'Back to the map') : null);
  }

  // keep the overlay element between renders so its entrance animation plays only once
  let box = el.firstElementChild;
  if (!box || !box.classList.contains('combat')) {
    box = h('div.combat.enter', { role: 'dialog', 'aria-label': 'Fight' });
    el.replaceChildren(box);
  }
  box.replaceChildren(
    h('div.combat-head', null,
      h('span.round', null, `Round ${f.round}`),
      h('h2', null, fightTitle(f)),
      f.phase >= 2 ? h('span.chip', { style: { color: 'var(--info)', borderColor: 'var(--info)' } }, icon('wave'), 'The back row is flooding: 3 damage a round') : null,
      !mine().some(x => f.heroes.includes(x)) ? h('span.chip', null, icon('eye'), 'Watching') : null),
    stage, plan, bottom);
  C.rolled = false;
  requestAnimationFrame(() => drawArrows(box, f));
}

// ------------------------------------------------------------------ what the plan and the intents will do
// Per unit: planned damage, healing and armor from the party's placed actions, and the damage
// enemies intend to deal it (after any Armor it has or is about to get).
function preview(f) {
  const out = {};
  const at = id => (out[id] ||= { dmg: 0, heal: 0, armor: 0, incoming: 0 });
  const alive = f.foes.filter(fo => fo.hp > 0);
  for (const p of f.plan) {
    const a = S.static.actions[p.a];
    if (!a || !p.est) continue;
    let ids;
    if (p.tgt) ids = [p.tgt];
    else if (a.tgt === 'foes') ids = alive.map(fo => 'f' + fo.id);
    else if (a.tgt === 'front') { const fr = alive.filter(fo => fo.row === 'front'); ids = (fr.length ? fr : alive).map(fo => 'f' + fo.id); }
    else if (a.tgt === 'party') ids = f.heroes.filter(y => !f.hs[y].down && !f.hs[y].fled).map(y => 'h' + y);
    else ids = ['h' + p.h];
    const key = p.est.k === 'dmg' ? 'dmg' : p.est.k === 'armor' ? 'armor' : p.est.k === 'heal' || p.est.k === 'lift' ? 'heal' : null;
    if (!key) continue;
    for (const id of ids) at(id)[key] += p.est.n;
  }
  const units = [...f.heroes.filter(y => !f.hs[y].down && !f.hs[y].fled).map(y => 'h' + y), ...(f.allies || []).filter(a => a.hp > 0).map(a => 's' + a.id)];
  const rowOf = id => (id[0] === 'h' ? f.hs[+id.slice(1)].row : (f.allies || []).find(a => 's' + a.id === id)?.row);
  for (const fo of alive) {
    const it = fo.intent;
    if (!it || !it.v || !['attack', 'row', 'all'].includes(it.k)) continue;
    for (const id of intentTargets(it, units, rowOf)) at(id).incoming += it.v;
  }
  return out;
}

function intentTargets(it, units, rowOf) {
  if (it.k === 'attack') return it.tgt && units.includes(it.tgt) ? [it.tgt] : [];
  if (it.k === 'all') return units;
  if (it.k === 'row') { const r = units.filter(u => rowOf(u) === (it.row || 'front')); return r.length ? r : units; }
  return [];
}

function previewRow(id, prev, hp) {
  const p = prev[id];
  if (!p) return h('div.preview');
  const chips = [];
  if (p.dmg) chips.push(h('span.pv.dmg', { tip: `Planned damage\nAbout ${p.dmg} from the actions placed so far, before Armor.` }, icon('sword'), p.dmg, hp !== undefined && p.dmg >= hp ? ' · lethal' : ''));
  if (p.heal) chips.push(h('span.pv.heal', { tip: 'Planned healing' }, icon('plus'), p.heal));
  if (p.armor) chips.push(h('span.pv.arm', { tip: 'Planned Armor' }, icon('shield'), p.armor));
  if (p.incoming) {
    let have = p.armor;
    if (id[0] === 'h') have += (S.game.fight?.hs[+id.slice(1)]?.st?.armor || 0);
    const net = Math.max(0, p.incoming - have);
    chips.push(h('span.pv.in', { tip: `Incoming\nEnemies intend ${p.incoming} damage here${have ? `; ${Math.min(have, p.incoming)} of it is blocked by Armor` : ''}.` }, icon('skull'), net, have ? h('span.faint', null, ` / ${p.incoming}`) : null));
  }
  return h('div.preview', null, ...chips);
}

// Curved arrows from each enemy to whoever its intent targets.
const ARROW = { attack: '#d0624f', row: '#d0624f', all: '#d0624f', debuff: '#a48ad8' };
function drawArrows(box, f) {
  const stage = box.querySelector('.stage');
  if (!stage) return;
  stage.querySelector('svg.arrows')?.remove();
  if (C.playing) return;
  const sr = stage.getBoundingClientRect();
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'arrows');
  svg.setAttribute('width', sr.width); svg.setAttribute('height', sr.height);
  const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
  for (const [k, c] of Object.entries({ red: ARROW.attack, violet: ARROW.debuff })) {
    defs.insertAdjacentHTML('beforeend', `<marker id="ah-${k}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${c}"/></marker>`);
  }
  svg.append(defs);
  const units = [...stage.querySelectorAll('.unit.hero:not(.down):not(.fled):not(.dead)')].map(el => el.dataset.uid);
  const rowOf = id => (id[0] === 'h' ? f.hs[+id.slice(1)].row : (f.allies || []).find(a => 's' + a.id === id)?.row);
  const pos = (el, side) => {
    const r = el.querySelector('img').getBoundingClientRect();
    return [side === 'left' ? r.left - sr.left - 4 : r.right - sr.left + 4, r.top - sr.top + r.height * 0.45];
  };
  for (const fo of f.foes) {
    const it = fo.intent;
    if (fo.hp <= 0 || !it || !ARROW[it.k]) continue;
    const fromEl = stage.querySelector(`[data-uid="f${fo.id}"]`);
    if (!fromEl) continue;
    const targets = it.k === 'debuff' ? (it.tgt ? [it.tgt] : []) : intentTargets(it, units, rowOf);
    const [x0, y0] = pos(fromEl, 'left');
    for (const t of targets) {
      const toEl = stage.querySelector(`[data-uid="${t}"]`);
      if (!toEl) continue;
      const [x1, y1] = pos(toEl, 'right');
      const mx = (x0 + x1) / 2, my = Math.min(y0, y1) - 40 - Math.abs(x0 - x1) * 0.06;
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', `M${x0},${y0} Q${mx},${my} ${x1},${y1}`);
      path.setAttribute('class', 'arrow');
      path.setAttribute('stroke', ARROW[it.k]);
      path.setAttribute('marker-end', `url(#ah-${it.k === 'debuff' ? 'violet' : 'red'})`);
      if (it.k !== 'attack') path.setAttribute('stroke-dasharray', '6 5');
      svg.append(path);
    }
  }
  stage.prepend(svg);
}

function heroActive(f, x) { const hs = f.hs[x]; return hs && !hs.down && !hs.fled; }

function hpBar(hp, max) {
  return h('div.bar', null, h('i', { style: { width: Math.max(0, Math.round(100 * hp / max)) + '%' } }), h('span', null, `${Math.max(0, hp)} / ${max}`));
}

function statusRow(st, extra = []) {
  const chips = [];
  for (const [k, v] of Object.entries(st || {})) {
    if (!v || k === 'doomt') continue;
    const s = STATUS[k];
    if (!s) continue;
    const n = k === 'stun' || k === 'freeze' || k === 'shock' ? '' : v;
    chips.push(h('span.st.' + (k === 'armor' ? 'armor' : s.bad ? 'bad' : 'good') + '.' + k, { tip: `${s.name}${n !== '' ? ' ' + n : ''}\n${s.text}` }, icon(s.icon), n));
  }
  for (const e of extra) chips.push(h('span.st', null, e));
  return h('div.sts', null, ...chips);
}

function floats(id) {
  const list = C.floats[id] || [];
  const now = performance.now();
  return list.map(fl => h('div.float.' + fl.cls, { style: { animationDelay: `-${Math.round(now - fl.t)}ms` } }, fl.text));
}

function foeTip(fo) {
  const d = S.static.foes[fo.k];
  return `${d.name}\n${fo.hp} / ${fo.max} HP · ${d.row} row · speed ${d.speed}${d.undead ? ' · undead' : ''}${d.beast ? ' · beast' : ''}`;
}

function intentChip(fo, f) {
  const it = fo.intent;
  if (!it || fo.hp <= 0) return h('div.intent.none', null, '·');
  const [ic, col] = INTENT[it.k] || ['spark', 'var(--muted)'];
  let to = '';
  if (it.tgt?.startsWith('h')) to = S.game.heroes[+it.tgt.slice(1)].name;
  else if (it.tgt?.startsWith('s')) to = (f.allies || []).find(a => 's' + a.id === it.tgt)?.name || 'a summon';
  else if (it.k === 'row') to = it.row === 'back' ? 'back row' : 'front row';
  else if (it.k === 'all') to = 'everyone';
  const stTxt = it.st ? ` + ${STATUS[it.st]?.name || it.st}` : '';
  const tip = `${INTENT_TEXT[it.k] || it.k}${it.v ? ` for ${it.v}` : ''}${stTxt}${to ? `\nTarget: ${to}` : ''}`;
  return h('div.intent', { style: { '--c': col }, tip }, icon(ic), it.v ?? '', it.st ? icon(STATUS[it.st]?.icon || 'spark') : null, to ? h('span.to', null, '→ ' + to) : null);
}

function planChip(p, i, f) {
  const a = S.static.actions[p.a];
  const g = S.game;
  let tgt = '';
  if (p.tgt?.startsWith('f')) tgt = f.foes.find(fo => 'f' + fo.id === p.tgt)?.name || '';
  else if (p.tgt?.startsWith('h')) tgt = g.heroes[+p.tgt.slice(1)].name;
  const mineP = mine().includes(p.h) && !f.hs[p.h].ready && !C.playing;
  return h('span.plan-chip', { style: { '--seat': `var(--hero-${p.h})` } },
    h('span.muted', null, `${i + 1}.`), h('b', null, a.name + (p.plus ? '+' : '')), tgt ? h('span.muted', null, '→ ' + tgt) : null,
    p.est ? h('span.est', null, `${p.est.n}${p.est.k === 'dmg' ? '' : p.est.k === 'heal' ? ' heal' : p.est.k === 'armor' ? ' armor' : ' HP'}`) : null,
    mineP ? h('button.x', { 'aria-label': 'Undo', tip: 'Take it back', onclick: () => send({ t: 'unplace', h: p.h, i }) }, icon('x')) : h('span', { style: { width: '6px' } }));
}

function tray(f, x, my) {
  const g = S.game, hero = g.heroes[x], hs = f.hs[x];
  const dice = hs.dice;
  const selDice = dice.filter(d => C.sel.has(d.id) && !d.used);
  const acts = hero.actions;
  const ready = hs.ready;
  const waiting = f.heroes.filter(y => heroActive(f, y) && !f.hs[y].ready && y !== x).map(y => g.heroes[y].name);
  // one button per kind of consumable, using the first of them
  const uses = [];
  hero.bag.forEach((k, i) => {
    if (S.static.items[k].slot !== 'use') return;
    const u = uses.find(x => x[0] === k);
    if (u) u[2]++; else uses.push([k, i, 1]);
  });
  return h('div.tray', null,
    h('div.tray-left', null,
      h('div.who', null,
        my.length > 1 ? h('div.seg', null, ...my.map(y => h('button', { 'aria-pressed': String(y === x), onclick: () => { C.tab = y; C.sel.clear(); C.pending = null; render(); } }, g.heroes[y].name)))
          : h('b', { style: { color: `var(--hero-${x})` } }, hero.name),
        h('span.chip', { tip: 'Your row\nMelee actions need the front row. Back-row heroes take 2 less from melee.' }, hs.row === 'front' ? 'Front row' : 'Back row')),
      dice.length ? h('div.dice', null, ...dice.map((d, i) => {
        const shield = d.v === 'S';
        return h('button.die' + (d.used ? '.used' : '') + (C.sel.has(d.id) && !d.used ? '.sel' : '') + (shield ? '.shield' : '') + (d.src === 'spirit' ? '.spirit' : '') + (C.rolled ? '.roll' : ''), {
          disabled: d.used || ready, 'aria-label': `Die ${i + 1}: ${shield ? 'shield' : d.v}`,
          tip: `${dieLabel(d.faces)} · ${{ base: 'class die', spirit: 'spirit die from a fallen ally', pet: 'your hawk’s die', anthem: 'from the Anthem of Kings', gift: 'given by an ally' }[d.src] || 'from your ' + d.src}${shield ? '\nShield face: worth 0, blocks 3 damage when used' : ''}\nFaces: ${d.faces.map(v => (v === 'S' ? '◆' : v)).join(' ')}`,
          onclick: () => toggleDie(d.id),
        }, h('span.k', null, i + 1), shield ? icon('shield') : d.v, h('span.src', null, { base: '', weapon: 'W', armor: 'A', trinket: 'T', spirit: '✦', pet: 'P', anthem: '♪', gift: 'G' }[d.src] ?? ''));
      })) : h('p.muted', null, 'No dice this round (Stunned).'),
      h('div.tray-tools', null,
        h('button.btn.sm', { disabled: ready || hs.rr <= 0 || selDice.length !== 1, tip: 'Reroll\nPick one unused die first.', onclick: () => { send({ t: 'reroll', h: x, die: selDice[0].id }); C.sel.clear(); sfx.play('dice'); } }, icon('refresh'), `Reroll · ${hs.rr}`),
        h('button.btn.sm.ghost', { disabled: ready || !f.plan.some(p => p.h === x), onclick: () => send({ t: 'unplace', h: x }) }, 'Undo', h('span.kbd', null, 'Z')),
        ...uses.map(([k, i, n]) => h('button.btn.sm.ghost', { disabled: ready, tip: `${S.static.items[k].name}\n${S.static.items[k].text}\nUsed at once; no die needed.`, onclick: () => useItem(x, k, i) }, icon('drop'), S.static.items[k].name + (n > 1 ? ` ×${n}` : ''))))),
    h('div.actions', null, ...acts.map((k, i) => actionCard(f, x, k, i, selDice, ready))),
    h('div.tray-right', null,
      C.pending ? h('p', { style: { color: 'var(--accent)', fontWeight: 600 } }, 'Choose a target', h('br'), h('span.muted', { style: { fontWeight: 400 } }, 'Esc to cancel')) : null,
      h('p.muted', { style: { fontSize: '14px' } }, ready ? (waiting.length ? `Waiting for ${waiting.join(', ')}` : 'Resolving…') : waiting.length ? `${waiting.join(', ')} still planning` : 'Everyone else is ready'),
      ready ? h('button.btn.lg', { onclick: () => send({ t: 'fready', h: x, on: false }) }, 'Unready')
        : h('button.btn.primary.lg', { onclick: () => { send({ t: 'fready', h: x }); C.sel.clear(); C.pending = null; } }, icon('check'), 'Ready', h('span.kbd', null, 'Space'))));
}

function actionCard(f, x, k, i, selDice, ready) {
  const base = k.replace(/\+$/, '');
  const a = S.static.actions[base];
  const hs = f.hs[x];
  const once = a.once && (hs.once.includes(base) || f.plan.some(p => p.h === x && p.a === base));
  const meleeBlocked = a.melee && hs.row !== 'front';
  const noFlee = base === 'flee' && (f.kind === 'dungeon' || f.kind === 'boss');
  const n = a.req.n ?? 1;
  const fits = !ready && !once && !meleeBlocked && !noFlee && (n === 0 ? selDice.length === 0 : checkReq(a.req, selDice));
  const dis = ready || once || noFlee;
  const why = meleeBlocked ? '\nNeeds the front row.' : once ? '\nOnce per fight.' : noFlee ? '\nThere’s no running from this one.' : '';
  return h('button.action' + (fits ? '.fits' : ''), {
    disabled: dis, tip: `${a.name}${k.endsWith('+') ? '+' : ''}\n${reqText(a.req)}\n${a.text}${a.melee ? '\nMelee: reaches the front row.' : ''}${why}`,
    onclick: () => pickAction(f, x, k, selDice),
  },
    h('div.top', null, h('b', null, a.name + (k.endsWith('+') ? '+' : '')), h('span.req', null, reqText(a.req))),
    h('p', null, a.text),
    i < KEYS.length ? h('span.kbd', null, KEYS[i].toUpperCase()) : null);
}

function spiritBar(f, d) {
  const g = S.game, sp = f.spirit[d];
  const targets = f.heroes.filter(x => heroActive(f, x));
  return h('div.watch', null,
    h('span', null, `${g.heroes[d].name}’s spirit lingers. Give your die `, h('b', { style: { color: 'var(--accent)' } }, sp.v), ' to:'),
    ...targets.map(x => h('button.btn', { onclick: () => send({ t: 'spirit', h: d, to: x }) }, g.heroes[x].name)));
}

// ------------------------------------------------------------------ input
function toggleDie(id) {
  if (C.sel.has(id)) C.sel.delete(id); else C.sel.add(id);
  C.pending = null;
  sfx.play('click');
  render();
}

function needsTarget(a) { return ['foe', 'ally', 'other', 'downed'].includes(a.tgt); }

function pickAction(f, x, k, selDice) {
  const base = k.replace(/\+$/, '');
  const a = S.static.actions[base];
  const n = a.req.n ?? 1;
  let dice = selDice;
  if (n > 0 && !dice.length) {
    // nothing picked: try the best single die that fits
    const free = f.hs[x].dice.filter(d => !d.used);
    if (n === 1) {
      const ok = free.filter(d => checkReq(a.req, [d])).sort((p, q) => (typeof q.v === 'number' ? q.v : 0) - (typeof p.v === 'number' ? p.v : 0));
      if (ok.length) dice = [ok[0]];
    }
    if (!dice.length) { toast(`Pick dice first: ${a.name} needs ${reqText(a.req).toLowerCase()}.`); return; }
  }
  if (n === 0 && dice.length) dice = [];
  if (n > 0 && !checkReq(a.req, dice)) { toast(`Those dice don’t fit ${a.name}: ${reqText(a.req).toLowerCase()}.`, 'err'); sfx.play('error'); return; }
  if (a.melee && f.hs[x].row !== 'front') { toast('Melee needs the front row. Use Shift to move up.', 'err'); return; }
  const msg = { t: 'place', h: x, a: base, dice: dice.map(d => d.id) };
  if (needsTarget(a)) {
    const opts = targetsFor(f, x, a, dice);
    if (!opts.length) {
      toast(a.req.match_intent ? 'No enemy’s intent matches that die.' : a.req.marked ? 'Mark an enemy first.' : 'There’s no one to use that on.');
      return;
    }
    if (opts.length === 1) { send({ ...msg, tgt: opts[0] }); C.sel.clear(); sfx.play('place'); render(); return; }
    C.pending = { msg, opts };
    render();
    return;
  }
  send(msg);
  C.sel.clear();
  sfx.play('place');
  render();
}

function useItem(x, k, i) {
  const it = S.static.items[k];
  const f = S.game.fight;
  const u = it.use;
  const msg = { t: 'use', h: x, bag: i };
  let opts = null;
  if (u.heal) opts = f.heroes.filter(y => heroActive(f, y)).map(y => 'h' + y);
  else if (u.bomb) opts = f.foes.filter(fo => fo.hp > 0).map(fo => 'f' + fo.id);
  else if (u.lift) opts = f.heroes.filter(y => f.hs[y].down).map(y => 'h' + y);
  if (opts && !opts.length) { toast('There’s no one to use that on.'); return; }
  if (opts && opts.length > 1) { C.pending = { msg, opts, item: true }; render(); return; }
  send({ ...msg, tgt: opts ? opts[0] : null });
}

function targetsFor(f, x, a, dice = []) {
  const alive = f.foes.filter(fo => fo.hp > 0);
  if (a.tgt === 'foe') {
    let pool = alive;
    if (a.melee) { const fr = alive.filter(fo => fo.row === 'front'); if (fr.length) pool = fr; }
    if (a.req.match_intent) pool = pool.filter(fo => fo.intent?.v != null && fo.intent.v === dice[0]?.v);
    if (a.req.marked) pool = pool.filter(fo => fo.st.mark);
    return pool.map(fo => 'f' + fo.id);
  }
  if (a.tgt === 'downed') return f.heroes.filter(y => f.hs[y].down).map(y => 'h' + y);
  const heroes = f.heroes.filter(y => heroActive(f, y) && (a.tgt !== 'other' || y !== x));
  return heroes.map(y => 'h' + y);
}

function isTarget(id) { return !!C.pending && C.pending.opts.includes(id); }

function targetClick(id) {
  if (!C.pending || !C.pending.opts.includes(id)) return;
  send({ ...C.pending.msg, tgt: id });
  C.pending = null;
  C.sel.clear();
  sfx.play('place');
  render();
}

document.addEventListener('keydown', e => {
  if (e.target.matches?.('input, select, textarea')) return;
  const f = S.game?.fight;
  if (!f || C.playing || !combatOpen()) return;
  const x = C.tab;
  if (e.key === 'Escape' && C.pending) { C.pending = null; render(); return; }
  if (x === null) return;
  const hs = f.hs[x];
  if (!hs) return;
  if (e.code === 'Space') { e.preventDefault(); send({ t: 'fready', h: x, on: !hs.ready }); C.sel.clear(); C.pending = null; return; }
  if (hs.ready) return;
  if (e.key === 'z' || e.key === 'Z') { send({ t: 'unplace', h: x }); return; }
  const n = parseInt(e.key, 10);
  if (n >= 1 && n <= 9) { const d = hs.dice[n - 1]; if (d && !d.used) toggleDie(d.id); return; }
  const ai = KEYS.indexOf(e.key.toLowerCase());
  if (ai >= 0) {
    const k = S.game.heroes[x].actions[ai];
    if (k) pickAction(f, x, k, hs.dice.filter(d => C.sel.has(d.id) && !d.used));
  }
});

// ------------------------------------------------------------------ playing back a round
const COMBAT_FX = new Set(['sact', 'act', 'fact', 'dmg', 'heal', 'armor', 'st', 'die', 'down', 'lift', 'summon', 'shift', 'flee', 'drag', 'fightend', 'phase', 'revive', 'dead']);

const queue = [];
export function combatFx(list, before) {
  const fx = list.filter(f => COMBAT_FX.has(f.k));
  if (list.some(f => f.k === 'fight')) sfx.play('fight');
  if (list.some(f => f.k === 'round')) sfx.play('dice');
  if (!fx.length) return;
  queue.push({ fx, before: before ? JSON.parse(JSON.stringify(before)) : null });
  if (!C.playing) playNext();
}

// Rounds play back one after another, each from the state just before it.
function playNext() {
  const next = queue.shift();
  if (!next) return;
  const { fx, before } = next;
  const speed = S.settings.speed;
  const prev = before?.fight;
  const ended = fx.find(f => f.k === 'fightend');
  if (!speed || !prev) {
    if (ended) banner(ended.result);
    playNext();
    return;
  }
  C.display = prev;
  C.hp = Object.fromEntries(before.heroes.map((x, i) => [i, x.hp]));
  C.playing = true;
  C.floats = {};
  render();
  let i = 0;
  const step = () => {
    if (i >= fx.length) { finish(ended); return; }
    const f = fx[i++];
    const wait = apply(f);
    render();
    setTimeout(step, wait / speed);
  };
  setTimeout(step, 150 / speed);
}

function finish(ended) {
  C.playing = false; C.display = null; C.hp = null; C.anim = {}; C.floats = {};
  if (ended) banner(ended.result);
  if (queue.length) { playNext(); return; }
  render();
}

function banner(result) {
  sfx.play(result === 'won' ? 'win' : 'lose');
  const el = h('div.banner' + (result === 'won' ? '' : '.lost'), null, h('div', null, result === 'won' ? 'Victory' : 'Defeat'));
  document.body.append(el);
  setTimeout(() => el.remove(), 1500);
}

let floatId = 0;
function addFloat(id, text, cls) {
  const list = (C.floats[id] ||= []);
  const fl = { id: ++floatId, text, cls, t: performance.now() };
  list.push(fl);
  setTimeout(() => { const l = C.floats[id]; if (l) { const j = l.indexOf(fl); if (j >= 0) l.splice(j, 1); } }, 900);
}
function flash(id, cls, ms = 300) {
  C.anim[id] = cls;
  setTimeout(() => { if (C.anim[id] === cls) delete C.anim[id]; }, ms);
}

function apply(f) {
  const d = C.display;
  if (['dmg', 'heal', 'armor', 'st', 'die', 'down', 'lift', 'drag'].includes(f.k) && typeof f.to !== 'string') return 0;
  const foe = id => d.foes.find(fo => 'f' + fo.id === id);
  const ally = id => (d.allies || []).find(a => 's' + a.id === id);
  switch (f.k) {
    case 'act': {
      flash('h' + f.h, 'act');
      addFloat('h' + f.h, S.static.actions[f.a]?.name + (f.echo ? ' (echo)' : ''), 'txt');
      sfx.play('swing');
      return 380;
    }
    case 'fact': {
      flash('f' + f.f, 'act');
      if (f.ik !== 'dazed') sfx.play('swing');
      return 300;
    }
    case 'dmg': {
      if (f.to.startsWith('h')) { const x = +f.to.slice(1); C.hp[x] = (C.hp[x] ?? 0) - f.n; }
      else if (f.to.startsWith('s')) { const al = ally(f.to); if (al) al.hp -= f.n; }
      else { const fo = foe(f.to); if (fo) fo.hp -= f.n; }
      if (f.block) addFloat(f.to, `◆${f.block}`, 'arm');
      if (f.n > 0 || !f.block) addFloat(f.to, `−${f.n}`, 'dmg');
      flash(f.to, 'hit');
      sfx.play(f.n > 0 ? 'hit' : 'block');
      return 300;
    }
    case 'heal': {
      if (f.to.startsWith('h')) { const x = +f.to.slice(1); C.hp[x] = (C.hp[x] ?? 0) + f.n; }
      else if (f.to.startsWith('s')) { const al = ally(f.to); if (al) al.hp += f.n; }
      else { const fo = foe(f.to); if (fo) fo.hp += f.n; }
      if (f.n) { addFloat(f.to, `+${f.n}`, 'heal'); sfx.play('heal'); }
      return f.n ? 260 : 60;
    }
    case 'armor': addFloat(f.to, `+${f.n} ◆`, 'arm'); sfx.play('block'); return 220;
    case 'st': {
      const name = STATUS[f.s]?.name || { guarded: 'Guarded', taunt: 'Taunt', stunned: 'Stunned', cleansed: 'Cleansed', unbreakable: 'Unbreakable!', sanct: 'Sanctuary', might: 'Might', weakened: 'Weakened', distracted: 'Distracted', dazed: 'Dazed', dodged: 'Dodged!' }[f.s] || f.s;
      if (f.to === 'party' || f.to === 'foes') return 200;
      addFloat(f.to, name, 'txt');
      if (f.to.startsWith('f')) { const fo = foe(f.to); if (fo && STATUS[f.s]) fo.st[f.s] = (fo.st[f.s] || 0) + 1; }
      return 220;
    }
    case 'die': { const u = f.to.startsWith('s') ? ally(f.to) : foe(f.to); if (u) u.hp = 0; sfx.play('die'); return 320; }
    case 'sact': flash('s' + f.s, 'act'); sfx.play('swing'); return 300;
    case 'down': { const x = +f.to.slice(1); if (d.hs[x]) d.hs[x].down = true; sfx.play('die'); return 380; }
    case 'lift': { const x = +f.to.slice(1); if (d.hs[x]) d.hs[x].down = false; C.hp[x] = f.n; addFloat(f.to, 'Back up!', 'txt'); return 300; }
    case 'summon': {
      if (f.s) {
        const next = S.game.fight?.allies?.find(a => a.id === f.s);
        d.allies ||= [];
        if (next && !d.allies.some(a => a.id === f.s)) d.allies.push(JSON.parse(JSON.stringify(next)));
        addFloat('s' + f.s, 'Summoned', 'txt');
        return 300;
      }
      const next = S.game.fight?.foes.find(fo => fo.id === f.f);
      if (next && !d.foes.some(fo => fo.id === f.f)) d.foes.push(JSON.parse(JSON.stringify(next)));
      return 300;
    }
    case 'shift': { if (d.hs[f.h]) d.hs[f.h].row = f.row; return 220; }
    case 'flee': { if (d.hs[f.h]) d.hs[f.h].fled = true; return 300; }
    case 'drag': { const fo = foe(f.to); if (fo) fo.row = 'front'; return 220; }
    case 'phase': return 600;
    default: return 120;
  }
}
