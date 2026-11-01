// The fight overlay: the party and the enemies (in their rows), enemy intents, the round so far, and your dice
// tray and actions. When a round resolves, the server's effects are played back one at a time on
// a copy of the fight as it was, then the new state is shown.
import { S, send, mine } from './store.js?v=39';
import { h, icon, toast, hideTip, bigBanner } from './ui.js?v=39';
import { spriteURL } from './art.js?v=39';
import { reqText, STATUS, dieLabel, dieTip, hitChance, countOk, expected, isRisky, faceText, foeTraits } from './rules.js?v=39';
import { render } from './main.js?v=39';
import * as sfx from './audio.js?v=39';

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
  attack: ['sword', 'var(--intent-attack)'], all: ['skull', 'var(--intent-attack)'],
  block: ['shield', 'var(--intent-defend)'], guard: ['shield', 'var(--intent-defend)'], heal: ['plus', 'var(--intent-heal)'],
  buff: ['up', 'var(--intent-buff)'], debuff: ['eye', 'var(--intent-debuff)'], summon: ['spark', 'var(--intent-buff)'],
  charge: ['bolt', 'var(--intent-buff)'], dazed: ['clock', 'var(--muted)'],
};
const INTENT_TEXT = {
  attack: 'Attack', all: 'Hits everyone', block: 'Defend', guard: 'Shields an ally', heal: 'Heals an ally',
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
  if (f.id !== C.lastId) { C.lastId = f.id; C.sel.clear(); C.pending = null; C.hidden = false; if (!S.seenHints.fight) toast('Pick dice, then an action they fit: it happens at once. Ready up when you’re done.'); }
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
      hs?.st?.undertow ? h('div.covered-chip.undertow', { tip: `Undertow\n${STATUS.undertow.text}` }, `Undertow: ${hs.st.undertow} at round end`) : null,
      (f.covered || []).includes(x) ? h('div.covered-chip', { tip: `Covered\n${S.static.combos.covered.text}` }, `Covered: next hit +3`) : null,
      hpBar(hpOf(x), max),
      previewRow('h' + x, prev),
      statusRow(st, hs?.down ? ['Knocked down'] : []),
      floats('h' + x));
  };
  const unitFoe = fo => {
    const d = S.static.foes[fo.k];
    const cl = ['unit', 'foe'];
    if (d.boss || d.big) cl.push('boss');
    if (fo.hp <= 0 && !fo.dying) cl.push('dead', 'gone');
    if (C.anim['f' + fo.id]) cl.push(C.anim['f' + fo.id]);
    if (isTarget('f' + fo.id, f)) cl.push('target');
    return h('div.' + cl.join('.'), { 'data-uid': 'f' + fo.id, onclick: () => targetClick('f' + fo.id), tip: foeTip(fo) },
      intentChip(fo, f),
      h('img.pix', { src: spriteURL(fo.k), alt: '' }),
      h('div.uname', null, fo.name),
      fo.aff || d.big || fo.bl ? h('div.foe-tags', null,
        fo.aff ? h('span.foe-tag', { tip: `${S.static.elites[fo.aff].name}\n${S.static.elites[fo.aff].text}` }, 'Elite') : null,
        d.big && !fo.bl ? h('span.foe-tag', { tip: `Big threat\nAt half health it's bloodied: ${d.bloodied?.text || ''}` }, 'Big') : null,
        fo.bl ? h('span.foe-tag.bloodied', { tip: `Bloodied\n${d.bloodied?.text || ''}` }, 'Bloodied') : null) : null,
      hpBar(Math.max(0, fo.hp), fo.max, true),
      previewRow('f' + fo.id, prev, fo.hp),
      statusRow(fo.st, [...(fo.might ? [`+${fo.might} might`] : []), ...(fo.st.warded ? ['Warded: ½ damage'] : []), ...(fo.st.exposed ? ['Exposed: +50%'] : [])], traitChips(d)),
      fo.hp > 0 ? comboHints(fo, f) : null,
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
  // Every enemy keeps its place for the whole fight (the fallen leave a gap), so nothing jumps around
  // while a round plays out.
  const allies = (f.allies || []).filter(a => a.hp > 0 || (C.playing && a.wasUp));
  const foesIn = row => f.foes.filter(fo => fo.row === row || (row === 'front' && fo.row !== 'back'));

  // three or more in a column: shrink them so the column fits
  const col = (label, units, party) => h('div.col' + (party ? '.herocol' : '') + (units.length >= 3 || party ? '.crowd' : '') + (!units.length ? '.empty' : ''), null, h('span.lbl', null, label), ...units);
  const stage = h('div.stage' + (C.anim.stage ? '.' + C.anim.stage : ''), null,
    h('div.side-units' + (allies.length ? '' : '.solo'), null,
      allies.length ? col('Allies', allies.map(unitAlly)) : null,
      col('Party', f.heroes.map(unitHero), true)),
    h('div.side-units', null,
      col('Front', foesIn('front').map(unitFoe)),
      col('Back', foesIn('back').map(unitFoe))),
    rollTray());

  const done = f.done || [];
  const combos = S.static.combos || {};
  const comboTip = 'Combos: what two heroes do together\n' + Object.values(combos).map(c => `${c.name}: ${c.text}`).join('\n');
  const plan = h('div.planstrip', null, h('span.eyebrow', null, 'This round'),
    h('span.chip.brass.combo-help', { tip: comboTip }, icon('spark'), 'Combos'),
    done.length ? done.map((p, i) => doneChip(p, i, f)) : h('span.muted', { style: { fontSize: '14px' } }, 'Actions happen the moment they’re played, in the order the party plays them. Enemies act once everyone is ready.'));

  let bottom;
  const spiritMine = mine().filter(x => f.spirit?.[x] && !f.spirit[x].used);
  // your dice stay on screen (locked) while an action plays out mid-round, so the next move is in view
  const live = S.game.fight;
  const sameRound = live && live.id === f.id && live.round === f.round;
  if (active !== null && (!C.playing || sameRound) && live?.hs[active]) bottom = tray(live, active, my);
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
      f.phase >= 2 ? h('span.chip', { style: { color: 'var(--info)', borderColor: 'var(--info)' } }, icon('wave'), f.phase >= 3 ? 'The Crown is alone: exposed and furious' : 'The Undertow drags someone under each round') : null,
      !mine().some(x => f.heroes.includes(x)) ? h('span.chip', null, icon('eye'), 'Watching') : null),
    stage, plan, bottom);
  C.rolled = false;
  requestAnimationFrame(() => drawArrows(box, f));
}

// ------------------------------------------------------------------ what the plan and the intents will do
// Per unit: the damage enemies intend to deal it (after any Armor it has).
function preview(f) {
  const out = {};
  const at = id => (out[id] ||= { dmg: 0, heal: 0, armor: 0, incoming: 0, lo: 0, hi: 0 });
  const alive = f.foes.filter(fo => fo.hp > 0);
  const units = partyUnits(f);
  for (const fo of alive) {
    const it = fo.intent;
    if (!it || it.lo == null || !['attack', 'all'].includes(it.k) || fo.st.stun) continue;
    for (const id of intentTargets(it, units)) { const u = at(id); u.incoming += it.v; u.lo += it.lo; u.hi += it.hi; }
  }
  return out;
}

function partyUnits(f) {
  return [...f.heroes.filter(y => !f.hs[y].down && !f.hs[y].fled).map(y => 'h' + y), ...(f.allies || []).filter(a => a.hp > 0).map(a => 's' + a.id)];
}

// Who an intent will hit, once per hit (a unit can appear twice when two dice go its way).
function intentTargets(it, units) {
  if (it.k === 'all') return units;
  if (!['attack', 'debuff'].includes(it.k)) return [];
  return (it.tgts || (it.tgt ? [it.tgt] : [])).filter(u => units.includes(u));
}

// "2d6+3", with special dice marked: d6! explodes, d8~ steady, [4] already rolled, 3|5 one of two.
export function diceText(it) {
  const dice = it.dice || [];
  if (!dice.length) return '';
  const parts = [];
  const plain = {};
  for (const d of dice) {
    const nums = d.faces.map(x => (typeof x === 'number' ? x : parseInt(String(x).slice(1)) || 0));
    const top = Math.max(...nums);
    const odd = d.faces.some(x => typeof x !== 'number');
    if (d.v != null) parts.push(`[${d.tag === 'W' ? 'W' : d.v}]`);
    else if (d.fc) parts.push(d.fc.map(x => x[0] ?? 'W').join('|'));
    else if (odd || d.dk.length) parts.push(`d${top}${d.dk.includes('exploding') ? '!' : d.dk.includes('steady') ? '~' : ''}${odd ? '*' : ''}`);
    else plain[top] = (plain[top] || 0) + 1;
  }
  const groups = Object.entries(plain).sort((a, b) => b[0] - a[0]).map(([n, c]) => `${c > 1 ? c : ''}d${n}`);
  const b = it.bonus || 0;
  return [...groups, ...parts].join('+') + (b > 0 ? `+${b}` : b < 0 ? `−${-b}` : '');
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
    const lo = Math.max(0, p.lo - have), hi = Math.max(0, p.hi - have);
    chips.push(h('span.pv.in', { tip: `Incoming\nEnemies will roll ${p.lo === p.hi ? p.lo : `${p.lo}–${p.hi}`} damage here${have ? `, less ${have} Armor` : ''}.` }, icon('skull'), lo === hi ? lo : `${lo}–${hi}`, have ? h('span.faint', null, ` ◆${have}`) : null));
  }
  return h('div.preview', null, ...chips);
}

// Curved arrows from each enemy to whoever its intent targets.
const ARROW = { attack: '#d0624f', all: '#d0624f', debuff: '#a48ad8' };
function drawArrows(box, f) {
  const stage = box.querySelector('.stage');
  if (!stage) return;
  stage.querySelector('svg.arrows')?.remove();
  // arrows stay up while the party's own actions play out, so a Guard or Taunt visibly swings them
  if (C.playing && S.game.fight?.round !== f.round) return;
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
  const pos = (el, side) => {
    const r = el.querySelector('img').getBoundingClientRect();
    return [side === 'left' ? r.left - sr.left - 4 : r.right - sr.left + 4, r.top - sr.top + r.height * 0.45];
  };
  for (const fo of f.foes) {
    const it = fo.intent;
    if (fo.hp <= 0 || !it || !ARROW[it.k]) continue;
    const fromEl = stage.querySelector(`[data-uid="f${fo.id}"]`);
    if (!fromEl) continue;
    const targets = [...new Set(intentTargets(it, units))];
    const [x0, y0] = pos(fromEl, 'left');
    for (const t of targets) {
      const toEl = stage.querySelector(`[data-uid="${t}"]`);
      if (!toEl) continue;
      const [x1, y1] = pos(toEl, 'right');
      const mx = (x0 + x1) / 2, my = Math.min(y0, y1) - 40 - Math.abs(x0 - x1) * 0.06;
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', `M${x0},${y0} Q${mx},${my} ${x1},${y1}`);
      path.setAttribute('class', 'arrow' + (C.swung?.[fo.id] && performance.now() - C.swung[fo.id] < 900 ? ' swing' : ''));
      path.setAttribute('stroke', ARROW[it.k]);
      path.setAttribute('marker-end', `url(#ah-${it.k === 'debuff' ? 'violet' : 'red'})`);
      if (it.k !== 'attack') path.setAttribute('stroke-dasharray', '6 5');
      svg.append(path);
    }
  }
  stage.prepend(svg);
}

// What the acting hero could score on this enemy from what allies have already done this round:
// Pincer (an ally hit it), Shatter (an ally Froze it), Wildfire (an ally Burned or Poisoned it).
export function pincerNums(fo, f, x) {
  const last = f.lastdie?.[fo.id];
  if (!last || last[0] === x || (f.pincered || []).includes(fo.id)) return null;
  return [...new Set(last[1].filter(Boolean))].sort((a, b) => a - b);
}
function comboHints(fo, f) {
  const x = C.tab;
  if (x == null || !f.heroes.includes(x)) return null;
  const by = fo.st_by || {}, chips = [];
  const nums = pincerNums(fo, f, x);
  if (nums) chips.push(h('span.combo-hint', { tip: `Pincer\n${S.game.heroes[f.lastdie[fo.id][0]].name} hit it this round: your first hit on it deals +2, or +5 if one of your dice shows ${nums.join(' or ')}.` }, `Pincer +2 · ${nums.join('/')}: +5`));
  if (fo.st.freeze && by.freeze != null && by.freeze !== x) chips.push(h('span.combo-hint', { tip: 'Shatter\nAn ally Froze it: your next hit on it breaks the ice for +4 (the Freeze ends).' }, 'Shatter +4'));
  if (!fo.wildfire) {
    if (fo.st.burn && by.burn != null && by.burn !== x && !fo.st.poison) chips.push(h('span.combo-hint', { tip: 'Wildfire\nAn ally Burned it: Poison it and it erupts for Burn + Poison, and half that to every other enemy.' }, 'Wildfire: Poison it'));
    if (fo.st.poison && by.poison != null && by.poison !== x && !fo.st.burn) chips.push(h('span.combo-hint', { tip: 'Wildfire\nAn ally Poisoned it: Burn it and it erupts for Burn + Poison, and half that to every other enemy.' }, 'Wildfire: Burn it'));
  }
  return chips.length ? h('div.combo-hints', null, ...chips) : null;
}

function heroActive(f, x) { const hs = f.hs[x]; return hs && !hs.down && !hs.fled; }

// Heroes' bars are coloured by health (green, amber, red); enemies' stay red.
export function hpClass(hp, max, foe) {
  if (foe) return '.foe';
  const f = hp / max;
  return f > 0.6 ? '.ok' : f > 0.3 ? '.mid' : '.low';
}
function hpBar(hp, max, foe = false) {
  return h('div.bar' + hpClass(hp, max, foe), null, h('i', { style: { width: Math.max(0, Math.round(100 * hp / max)) + '%' } }), h('span', null, `${Math.max(0, hp)} / ${max}`));
}

function statusRow(st, extra = [], tail = []) {
  const chips = [];
  for (const [k, v] of Object.entries(st || {})) {
    if (!v || ['doomt', 'warded', 'exposed', 'undertow'].includes(k)) continue;
    const s = STATUS[k];
    if (!s) continue;
    const n = ['stun', 'freeze', 'shock', 'warded', 'exposed'].includes(k) ? '' : v;
    chips.push(h('span.st.' + (k === 'armor' ? 'armor' : s.bad ? 'bad' : 'good') + '.' + k, { tip: `${s.name}${n !== '' ? ' ' + n : ''}\n${s.text}` }, icon(s.icon), n));
  }
  for (const e of extra) chips.push(h('span.st', null, e));
  return h('div.sts', null, ...chips, ...tail);
}

// The dice an action just rolled, big in the middle of the fight: they tumble, land, then say hit or miss.
function rollTray() {
  const t = C.tray;
  if (!t) return null;
  const now = performance.now();
  const since = t0 => ({ animationDelay: `-${Math.round(now - t0)}ms` });
  const ad = t.a ? S.static.actions[t.a] : null;
  // tags come as faces (S, X, W) or as the status an elemental face adds
  const EL = { burn: 'F', freeze: 'I', poison: 'P', F: 'F', I: 'I', P: 'P' };
  const shown = x => faceText(['S', 'X', 'W'].includes(x.tag) ? x.tag : EL[x.tag] ? EL[x.tag] + x.v : x.v);
  if (t.foe) {
    const late = now >= t.vt;
    const foeFace = x => (x.tag === 'X' || x.tag === 'S' || x.tag === 'W' ? faceText(x.tag) : x.tag ? faceText(x.tag + x.v) : x.v);
    return h('div.roll-tray.foe-roll' + (t.verdict && late ? '.' + t.verdict : ''), { style: since(t.t), role: 'status' },
      h('div.rt-info', null, h('span.rt-who', null, t.foe), h('span.rt-act', null, t.name || 'Attack'), h('span.rt-need', null, t.range ? `Rolls ${t.range}` : '')),
      h('div.rt-dice', null, ...t.dice.map(x => h('div.big-die.foe' + (x.re != null ? '.re' : ''), { style: since(x.t) },
        h('span', { style: since(x.t) }, foeFace(x)),
        x.re != null ? h('small', null, `${x.re} → again`) : x.ex != null ? h('small', null, `boom +${x.ex}`) : null)),
        t.bonus ? h('div.rt-bonus', null, `${t.bonus > 0 ? '+' : '−'}${Math.abs(t.bonus)}`) : null),
      h('div.rt-slot', null, late && t.total != null ? h('div.rt-total', { style: since(t.vt) }, `= ${t.total}`) : null,
        t.verdict && late ? h('div.rt-verdict.' + t.verdict, { style: since(t.vt) }, t.label) : null));
  }
  return h('div.roll-tray' + (t.verdict ? '.' + t.verdict : ''), { style: { '--seat': `var(--hero-${t.h})`, ...since(t.t) }, role: 'status' },
    h('div.rt-info', null,
      h('span.rt-who', null, S.game.heroes[t.h].name),
      ad ? h('span.rt-act', null, ad.name) : null,
      ad && isRisky(ad.req) ? h('span.rt-need', null, `Needs ${reqText(ad.req)}`) : null),
    h('div.rt-dice', null, ...t.dice.map(x => h('div.big-die' + (x.re ? '.re' : ''), { style: since(x.t) },
      h('span', { style: since(x.t) }, shown(x)),
      x.re ? h('small', null, x.re === 'steady' ? 'Steady' : 'Reroll') : null))),
    h('div.rt-slot', null, t.verdict ? h('div.rt-verdict.' + t.verdict, { style: since(t.vt) }, t.verdict === 'miss' ? 'Miss' : 'Hit!') : null));
}

function traitChips(d) {
  return foeTraits(d).map(([n, txt]) => h('span.trait', { tip: `${n}\n${txt}` }, n));
}

function floats(id) {
  const list = C.floats[id] || [];
  const now = performance.now();
  return list.map(fl => h('div.float.' + fl.cls, { style: { animationDelay: `-${Math.round(now - fl.t)}ms` } }, fl.text));
}

function foeTip(fo) {
  const d = S.static.foes[fo.k];
  const all = { ...d.moves, ...(d.pool || {}), ...(d.bloodied?.moves || {}) };
  const moves = (fo.mv || Object.keys(d.moves)).map(k => all[k]?.name).filter(Boolean);
  const el = fo.aff ? S.static.elites[fo.aff] : null;
  return `${fo.name}\n${fo.hp} / ${fo.max} HP · ${d.row} row · acts ${speedWord(d.speed)}${d.undead ? ' · undead' : ''}${d.beast ? ' · beast' : ''}`
    + `\nMoves: ${moves.join(', ')}`
    + (el ? `\nElite (${el.name}): ${el.text}` : '')
    + (d.bloodied ? `\n${fo.bl ? 'Bloodied' : 'At half health'}: ${d.bloodied.text}` : '')
    + (d.final ? '\nPhase 1: warded (half damage) while a Tide Guard stands.\nPhase 2, from two thirds health: the Undertow drags one hero under each round (Armor or a Guard stops it).\nPhase 3, from a third: alone, exposed (+50% damage taken) and furious (an extra die on every attack).' : '')
    + foeTraits(d).map(([n, t]) => `\n${n}: ${t}`).join('');
}

function speedWord(n) { return n >= 7 ? 'very fast' : n >= 5 ? 'fast' : n >= 3 ? 'at a steady pace' : 'slowly'; }

function unitName(f, u) {
  if (!u) return '';
  if (u.startsWith('h')) return S.game.heroes[+u.slice(1)].name;
  return (f.allies || []).find(a => 's' + a.id === u)?.name || 'a summon';
}

// An enemy's intent: what move, which dice, the range, and who it's aimed at. The tooltip spells
// out every rule the move has.
function intentChip(fo, f) {
  const it = fo.intent;
  if (!it || fo.hp <= 0) return h('div.intent.none', null, '·');
  const [ic, col] = INTENT[it.k] || ['spark', 'var(--muted)'];
  const aims = it.k === 'all' ? ['everyone'] : (it.tgts || (it.tgt ? [it.tgt] : [])).map(u => unitName(f, u));
  const counts = {};
  for (const a of aims) counts[a] = (counts[a] || 0) + 1;
  const to = Object.entries(counts).map(([n, c]) => (c > 1 ? `${n} ×${c}` : n)).join(', ');
  const range = it.lo != null ? (it.lo === it.hi ? `${it.lo}` : `${it.lo}–${it.hi}`) : it.k === 'buff' ? `+${it.v}` : '';
  const hits = it.each ? (it.dice || []).length : it.sweep || 1;
  const lines = [it.name || INTENT_TEXT[it.k] || it.k];
  const dt = diceText(it);
  if (it.k === 'attack') lines.push(`Rolls ${dt}: ${range} damage${it.each ? ' with each die, a separate hit' : it.sweep ? ` to ${it.sweep} of you at once` : ''}.`);
  else if (it.k === 'all') lines.push(`Rolls ${dt}: ${range} damage to everyone.`);
  else if (['block', 'guard', 'heal'].includes(it.k)) lines.push(`Rolls ${dt}: ${range} ${it.k === 'heal' ? (it.self ? 'healing for itself' : 'healing for its most hurt ally') : it.k === 'guard' ? (it.all ? 'Armor for every enemy' : 'Armor for its most hurt ally') : 'Armor for itself'}.`);
  else if (it.k === 'buff') lines.push(it.self ? `It gains +${it.v} might for the rest of the fight.` : `Every enemy gains +${it.v} might for the rest of the fight.`);
  else if (it.k === 'summon') lines.push(`Calls a ${S.static.foes[it.f]?.name || 'friend'} into the fight.`);
  else if (it.k === 'charge') lines.push(A_CHARGE(fo));
  else if (it.k === 'dazed') lines.push('Does nothing this round.');
  if (it.st) lines.push(`${it.st_min ? `If a die rolls ${it.st_min}+: ` : it.k === 'debuff' ? '' : 'On a hit: '}${STATUS[it.st]?.name || it.st}${it.k === 'debuff' && it.dice?.[0]?.v != null ? ` (its die shows ${it.dice[0].v}${it.st_min ? it.dice[0].v >= it.st_min ? ': it will land' : ': it will miss' : ''})` : ''}.`);
  if (it.pair) lines.push(`On doubles: ${it.pair.again ? 'it strikes twice' : STATUS[it.pair.st]?.name || it.pair.st}.`);
  if (it.chain) lines.push('Then arcs to someone else for half.');
  if (it.charged) lines.push('Charged: rolls an extra die.');
  if (it.guarded != null) lines.push(`Guarded: it now comes at ${unitName(f, it.guarded)}.`);
  if (to) lines.push(`Target: ${to}`);
  const sure = it.k === 'debuff' && it.st_min && it.dice?.[0]?.v != null ? (it.dice[0].v >= it.st_min ? '.sure' : '.fizzle') : '';
  // the card: name; the dice it will roll, drawn as little dice, the bonus, and the range big;
  // then who it's aimed at (a dot in their colour) and any rider
  const tgtIds = it.k === 'all' ? [] : (it.tgts || (it.tgt ? [it.tgt] : []));
  const seen = new Set();
  const who = tgtIds.filter(u => !seen.has(u) && seen.add(u)).map(u => h('span.who', { style: { '--seat': u.startsWith('h') ? `var(--hero-${u.slice(1)})` : 'var(--muted)' } },
    h('i'), unitName(f, u).split(' ')[0] + (counts[unitName(f, u)] > 1 ? ` ×${counts[unitName(f, u)]}` : '')));
  const tags = [];
  if (it.st) tags.push(h('span.rider', null, icon(STATUS[it.st]?.icon || 'spark'), (it.st_min ? `${it.st_min}+: ` : '') + (STATUS[it.st]?.name || it.st)));
  if (it.pair) tags.push(h('span.rider', null, 'pair: ', it.pair.again ? 'twice' : STATUS[it.pair.st]?.name || it.pair.st));
  if (it.chain) tags.push(h('span.rider', null, icon('bolt'), 'arcs'));
  const dice = (it.dice || []).map(d => {
    const nums = d.faces.map(x => (typeof x === 'number' ? x : parseInt(String(x).slice(1)) || 0));
    const top = Math.max(...nums);
    const odd = d.faces.some(x => typeof x !== 'number');
    const label = d.v != null ? (d.tag === 'W' ? 'W' : String(d.v)) : d.fc ? d.fc.map(x => x[0] ?? 'W').join('|') : `d${top}`;
    return h('span.md' + (d.v != null ? '.known' : '') + (d.fc ? '.fate' : '') + (d.dk.includes('exploding') ? '.boom' : '') + (d.dk.includes('steady') ? '.steady' : '') + (odd ? '.odd' : ''), null, label);
  });
  const b = it.bonus || 0;
  const body = it.dice?.length
    ? h('div.it-row', null, h('span.it-dice', null, ...dice, b ? h('span.bn', null, b > 0 ? `+${b}` : `−${-b}`) : null),
        range ? h('b.it-range', null, range, hits > 1 ? h('small', null, ` ×${hits}`) : null) : null)
    : h('div.it-row', null, icon(ic), h('span.it-what', null, range || { buff: 'buff', summon: 'calls help', charge: 'charging', dazed: 'nothing' }[it.k] || ''));
  return h('div.intent.card' + sure + (it.guarded != null ? '.guarded' : ''), { style: { '--c': col }, tip: lines.join('\n') },
    h('div.it-name', null, h('span.ic', null, icon(ic)), it.name || INTENT_TEXT[it.k] || '', it.guarded != null ? h('span.gd', null, icon('shield')) : null),
    body,
    who.length || it.k === 'all' || tags.length ? h('div.it-foot', null, it.k === 'all' ? h('span.who.all', null, h('i'), 'everyone') : null, ...who, ...tags) : null);
}

function A_CHARGE(fo) {
  const d = S.static.foes[fo.k];
  return d.dice.some(x => (x.dk || []).includes('grow')) ? 'Its die grows 4 faces bigger.' : 'Its next attack rolls an extra die.';
}

function doneChip(p, i, f) {
  const a = S.static.actions[p.a];
  const g = S.game;
  let tgt = '';
  if (p.tgt?.startsWith('f')) tgt = f.foes.find(fo => 'f' + fo.id === p.tgt)?.name || '';
  else if (p.tgt?.startsWith('h')) tgt = g.heroes[+p.tgt.slice(1)].name;
  const res = p.hit === true && isRisky(a.req) ? h('span.res.hit', null, 'hit') : p.hit === false ? h('span.res.miss', null, 'miss') : null;
  return h('span.plan-chip' + (p.hit === false ? '.missed' : ''), { style: { '--seat': `var(--hero-${p.h})` }, tip: `${g.heroes[p.h].name}: ${a.name}${p.plus ? '+' : ''}${tgt ? ' → ' + tgt : ''}` },
    h('span.muted', null, `${i + 1}.`), h('b', null, a.name + (p.plus ? '+' : '')), tgt ? h('span.muted', null, '→ ' + tgt) : null, res,
    h('span', { style: { width: '6px' } }));
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
        null),
      dice.length ? h('div.dice', null, ...dice.map((d, i) => dieButton(d, i, ready))) : h('p.muted', null, 'No dice this round (Stunned).'),
      h('div.tray-tools', null,
        h('span.chip', { tip: 'Automatic rerolls\nWhen one of your actions misses, a die rolls again, as long as you have one left this fight.' }, icon('refresh'), `${hs.rr} reroll${hs.rr === 1 ? '' : 's'}`),
        f.hymn ? h('span.chip.brass', { tip: 'Hymn of Valor\nEvery die the party rolls this round is this much higher.' }, `+${f.hymn} hymn`) : null,
        hs.inspire ? h('span.chip.brass', { tip: 'Inspired\nYour next die rolls this much higher.' }, `+${hs.inspire} next die`) : null,
        ...uses.map(([k, i, n]) => h('button.btn.sm.ghost', { disabled: ready, tip: `${S.static.items[k].name}\n${S.static.items[k].text}\nUsed at once; no die needed.`, onclick: () => useItem(x, k, i) }, icon('drop'), S.static.items[k].name + (n > 1 ? ` ×${n}` : ''))))),
    h('div.actions', null, ...acts.map((k, i) => actionCard(f, x, k, i, selDice, ready))),
    h('div.tray-right', null,
      C.pending ? h('p', { style: { color: 'var(--accent)', fontWeight: 600 } }, 'Choose a target', h('br'), h('span.muted', { style: { fontWeight: 400 } }, 'Esc to cancel')) : null,
      h('p.muted', { style: { fontSize: '14px' } }, C.playing && !hs.ready ? 'Keep playing: your actions queue up' : hs.ready ? (waiting.length ? `Waiting for ${waiting.join(', ')}` : 'Enemies are acting…') : waiting.length ? `${waiting.join(', ')} still acting` : 'Everyone else is ready'),
      hs.ready ? h('button.btn.lg', { onclick: () => send({ t: 'fready', h: x, on: false }) }, 'Unready')
        : h('button.btn.primary.lg' + (hs.dice.length && hs.dice.every(d => d.used) ? '.nudge' : ''), { onclick: () => { send({ t: 'fready', h: x }); C.sel.clear(); C.pending = null; } }, icon('check'), 'Ready', h('span.kbd', null, 'Space'))));
}

// A die in the tray: face-down (its kind and size) until it rolls, unless it's a Seer die (shown),
// an Augur die (high or low) or a Fate die (two faces).
// A die in the tray: a cream tile with its size (or its number, once known) big in the middle, a
// coloured top edge for where it comes from, and one icon for anything special about it.
const SRC = { base: ['Class die', 'var(--src-class)'], weapon: ['Weapon die', 'var(--src-weapon)'], armor: ['Armor die', 'var(--src-armor)'],
  trinket: ['Trinket die', 'var(--src-trinket)'], spirit: ['Spirit die from a fallen ally', 'var(--src-spirit)'], pet: ['Your hawk’s die', 'var(--src-pet)'],
  anthem: ['From the Anthem of Kings', 'var(--src-spirit)'], gift: ['Given by an ally', 'var(--src-spirit)'], hex: ['Cursed: a hex swapped your biggest die', 'var(--danger)'] };
const KIND_ICON = { seer: 'eye', exploding: 'spark', steady: 'refresh', heirloom: 'star', guard: 'shield' };
function dieButton(d, i, ready) {
  const [srcName, srcCol] = SRC[d.src] || [`From your ${d.src}`, 'var(--border-strong)'];
  let face, cls = '';
  const size = dieLabel(d.faces);
  if (d.v !== null && d.v !== undefined) {
    face = d.tag === 'S' ? icon('shield') : d.tag === 'X' ? '☠' : h('span.num', null, String(d.v));
    cls = '.known';
  } else if (d.fc) {
    face = h('span.fate', null, d.fc[0], h('i', null, '|'), d.fc[1]);
    cls = '.known';
  } else if (d.hint) {
    face = h('span.hint', null, d.hint === 'high' ? '▲' : '▼', h('small', null, d.hint));
  } else {
    face = h('span.size', null, d.top ? '★' : size);
  }
  const kinds = (d.dk || []).filter(k => KIND_ICON[k]);
  const marks = [];
  if (d.bonus) marks.push(h('span.mk.bonus', null, `+${d.bonus}`));
  if (d.link) marks.push(h('span.mk', null, icon('link')));
  const f0 = S.game.fight;
  const pinc = d.v != null && !d.used && f0 ? f0.foes.filter(fo => fo.hp > 0 && pincerNums(fo, f0, C.tab)?.includes(d.v)).map(fo => fo.name) : [];
  if (pinc.length) cls += '.combo';
  const tip = `${srcName}\n${dieTip(d)}${d.v == null && !d.fc ? `\nHidden until its action happens. Averages about ${expected(d).toFixed(1)}.` : ''}${d.bonus ? `\nRolls ${d.bonus} higher.` : ''}${pinc.length ? `\nPincer +5 on ${pinc.join(', ')}: it matches an ally's die.` : ''}`;
  return h('button.die.tile' + cls + (d.used ? '.used' : '') + (C.sel.has(d.id) && !d.used ? '.sel' : '') + (kinds.includes('guard') ? '.guard' : '') + (C.rolled ? '.roll' : ''), {
    style: { '--src': srcCol }, disabled: d.used || ready, 'data-id': d.id, 'aria-label': `Die ${i + 1}: ${size}${d.v != null ? ', showing ' + d.v : ''}`, tip, onclick: () => toggleDie(d.id),
  }, h('span.k', null, i + 1), face,
    kinds.length ? h('span.kinds', null, ...kinds.map(k => icon(KIND_ICON[k]))) : null,
    d.v != null && !d.fc ? h('span.sz', null, size) : null,
    marks.length ? h('span.marks', null, ...marks) : null);
}

// The requirement as a die-shaped badge: what the die must roll ("4+", "odd", "Σ10+"), or "any".
export function reqBadge(req) {
  const n = req.n ?? 1;
  let main = 'any', sub = n === 0 ? '' : n > 1 ? (req.upto ? `1–${n} dice` : `${n} dice`) : '';
  if (n === 0) main = 'free';
  else if (req.min !== undefined) main = `${req.min}+`;
  else if (req.max !== undefined) main = `≤${req.max}`;
  else if (req.exact !== undefined) main = `=${req.exact}`;
  else if (req.sum_min !== undefined) main = `Σ${req.sum_min}+`;
  else if (req.odd) main = 'odd';
  else if (req.even) main = 'even';
  else if (req.pair) main = 'pair';
  else if (req.straight) main = 'run';
  if (req.or_face === 'S') sub = 'or ◆';
  if (req.marked) sub = 'Marked';
  return { main, sub, risky: main !== 'any' && main !== 'free' };
}

function actionCard(f, x, k, i, selDice, ready) {
  const base = k.replace(/\+$/, '');
  const a = S.static.actions[base];
  const hs = f.hs[x];
  const once = a.once && hs.once.includes(base);
  const spent = a.per_rest && (S.game.heroes[x].spent || []).includes(base);
  const cooling = a.cd ? (hs.cds?.[base] || 0) : 0;
  const meleeBlocked = false;
  const noFlee = base === 'flee' && (f.kind === 'dungeon' || f.kind === 'boss');
  const n = a.req.n ?? 1;
  const guardOff = !a.def && selDice.some(d => d.dk?.includes('guard'));
  const fits = !ready && !once && !spent && !cooling && !meleeBlocked && !noFlee && !guardOff && (n === 0 ? selDice.length === 0 : countOk(a.req, selDice));
  // with nothing picked, the dice a click would use: shown on hover, and their odds on the card
  const auto = n > 0 && !selDice.length ? autoDice(f, x, a) : null;
  const noDice = n > 0 && !selDice.length && !auto;
  const chance = fits && n > 0 ? hitChance(a.req, selDice, f.hymn || 0) : auto && isRisky(a.req) ? hitChance(a.req, auto, f.hymn || 0) : null;
  const dis = ready || once || spent || noFlee || cooling > 0 || noDice;
  const why = spent ? '\nSpent: it comes back when you rest.' : guardOff ? '\nGuard dice only go on defensive actions.' : once ? '\nOnce per fight.' : noFlee ? '\nThere’s no running from this one.'
    : cooling ? `\nCooling down: ready ${cooling > 1 ? `in ${cooling} rounds` : 'next round'}.`
    : noDice ? `\nNo dice left that it can take${!a.def && hs.dice.some(d => !d.used && d.dk?.includes('guard')) ? ' (Guard dice only go on defensive actions)' : ''}.`
    : auto ? `\nClick to use ${auto.map(d => dieLabel(d)).join(' + ')}: the dice lit up below.` : '';
  const ids = auto ? auto.map(d => d.id) : [];
  const light = on => { for (const id of ids) document.querySelector(`.tray .die[data-id="${CSS.escape(id)}"]`)?.classList.toggle('auto', on); };
  const cdText = a.cd ? `\nCooldown: after using it, wait ${a.cd - 1} round${a.cd === 2 ? '' : 's'} before using it again.` : '';
  const bd = reqBadge(a.req);
  const [ico, eff, miss] = a.short || ['spark', a.text, null];
  const oddCls = chance === null ? '' : chance >= 0.6 ? '.good' : chance >= 0.3 ? '.mid' : '.bad';
  return h('button.action.v2' + (fits ? '.fits' : '') + (guardOff ? '.guard-off' : '') + (a.def ? '.def' : '') + (noDice ? '.nodice' : ''), {
    disabled: dis, onmouseenter: () => light(true), onmouseleave: () => light(false), onfocus: () => light(true), onblur: () => light(false), tip: `${a.name}${k.endsWith('+') ? '+' : ''}\n${reqText(a.req)}\n${a.text}${a.melee ? '\nMelee: reaches only the enemies’ front row.' : ''}${cdText}${why}`,
    onclick: () => pickAction(f, x, k, selDice),
  },
    h('div.rq' + (bd.risky ? '.risky' : '') + oddCls, { tip: `Needs: ${reqText(a.req)}${chance !== null ? `\n${Math.round(chance * 100)}% to hit with ${auto ? 'the dice it would use' : 'your picked dice'}` : ''}` },
      h('b', null, bd.main), chance !== null && bd.risky ? h('small', null, `${Math.round(chance * 100)}%`) : bd.sub ? h('small', null, bd.sub) : null),
    h('div.ab', null,
      h('div.top', null, h('b', null, a.name + (k.endsWith('+') ? '+' : '')),
        cooling ? h('span.cd.on', null, icon('clock'), cooling > 1 ? `${cooling}` : '1')
          : a.cd ? h('span.cd', { tip: `Cooldown ${a.cd}\nAfter using it, wait ${a.cd - 1} round${a.cd === 2 ? '' : 's'}.` }, icon('clock'), a.cd) : null),
      h('div.eff', null, icon(ico), h('span', null, eff + (k.endsWith('+') ? ' (+2)' : ''))),
      miss ? h('div.miss', null, `miss: ${miss}`) : null),
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

// The dice a click on an action uses when none are picked. Guard dice go to defensive actions first
// and never to anything else. A risky action takes the dice likeliest to hit it; anything else the
// best ones (by what they show, or roll on average). Null when no dice fit.
function autoDice(f, x, a) {
  const n = a.req.n ?? 1;
  const guard = d => (d.dk?.includes('guard') ? 1 : 0);
  const free = f.hs[x].dice.filter(d => !d.used && (a.def || !guard(d)))
    .sort((p, q) => (a.def ? guard(q) - guard(p) : 0) || expected(q) - expected(p));
  if (a.req.upto) return free.length ? free.slice(0, n) : null;
  if (free.length < n) return null;
  if (!isRisky(a.req) || free.length === n) return countOk(a.req, free.slice(0, n)) ? free.slice(0, n) : null;
  let best = null, bestP = -1;
  const pick = (start, combo) => {
    if (combo.length === n) {
      const p = hitChance(a.req, combo, f.hymn || 0);
      if (p > bestP + 1e-9) { bestP = p; best = combo.slice(); }
      return;
    }
    for (let i = start; i < free.length; i++) { combo.push(free[i]); pick(i + 1, combo); combo.pop(); }
  };
  pick(0, []);
  return best && countOk(a.req, best) ? best : null;
}

function needsTarget(a) { return ['foe', 'ally', 'other', 'downed'].includes(a.tgt); }

function pickAction(f, x, k, selDice) {
  const base = k.replace(/\+$/, '');
  const a = S.static.actions[base];
  const n = a.req.n ?? 1;
  let dice = selDice;
  if (n > 0 && !dice.length) {
    dice = autoDice(f, x, a);
    if (!dice) { toast(`${a.name} needs ${n} ${n === 1 ? 'die' : 'dice'}, and you don’t have that many left.`); return; }
  }
  if (n === 0 && dice.length) dice = [];
  if (!a.def && dice.some(d => d.dk?.includes('guard'))) { toast('Guard dice only go on defensive actions: Block, Armor, healing and the like.', 'err'); sfx.play('error'); return; }
  if (n > 0 && !countOk(a.req, dice)) { toast(`${a.name} takes ${a.req.upto ? 'up to ' : ''}${n} ${n === 1 ? 'die' : 'dice'}.`, 'err'); sfx.play('error'); return; }
  const msg = { t: 'place', h: x, a: base, dice: dice.map(d => d.id) };
  if (needsTarget(a)) {
    const opts = targetsFor(f, x, a, dice);
    if (!opts.length) {
      toast(a.req.marked ? 'Mark an enemy first.' : 'There’s no one to use that on.');
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
  // during playback you can keep acting, as long as the playback is still this round
  if (!f || !combatOpen() || (C.playing && (C.display?.id !== f.id || C.display?.round !== f.round))) return;
  const x = C.tab;
  if (e.key === 'Escape' && C.pending) { C.pending = null; render(); return; }
  if (x === null) return;
  const hs = f.hs[x];
  if (!hs) return;
  if (e.code === 'Space') { e.preventDefault(); send({ t: 'fready', h: x, on: !hs.ready }); C.sel.clear(); C.pending = null; return; }
  if (hs.ready) return;
  const n = parseInt(e.key, 10);
  if (n >= 1 && n <= 9) { const d = hs.dice[n - 1]; if (d && !d.used) toggleDie(d.id); return; }
  const ai = KEYS.indexOf(e.key.toLowerCase());
  if (ai >= 0) {
    const k = S.game.heroes[x].actions[ai];
    if (k) pickAction(f, x, k, hs.dice.filter(d => C.sel.has(d.id) && !d.used));
  }
});

// ------------------------------------------------------------------ playing back a round
const COMBAT_FX = new Set(['combo', 'froll', 'roll', 'reroll', 'sact', 'act', 'fact', 'dmg', 'heal', 'armor', 'st', 'die', 'down', 'lift', 'summon', 'retarget', 'flee', 'drag', 'fightend', 'phase', 'revive', 'dead', 'coins']);

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
    C.fx = fx; C.fxAt = i;
    const f = fx[i++];
    const wait = apply(f);
    render();
    // more waiting behind this one: hurry, so queued actions keep pace with the party
    setTimeout(step, wait / (speed * (queue.length ? 1 + Math.min(queue.length, 3) * 0.5 : 1)));
  };
  setTimeout(step, 150 / speed);
}

function finish(ended) {
  const close = () => {
    C.playing = false; C.display = null; C.hp = null; C.anim = {}; C.floats = {}; C.tray = null;
    if (queue.length) { playNext(); return; }
    render();
  };
  if (!ended) { close(); return; }
  // the fight's last moment stays up under the banner; loot and the map come after
  C.tray = null;
  render();
  banner(ended.result);
  setTimeout(close, 1300 / (S.settings.speed || 1));
}

function banner(result) {
  sfx.play(result === 'won' ? 'win' : 'lose');
  if (result === 'won') bigBanner('Victory', '', 'gold', 1600);
  else bigBanner(result === 'fled' ? 'Escaped' : 'Defeat', '', 'danger', 1600);
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
    case 'roll': {
      C.tray = null;
      if (!f.dice.length) return 0;
      // the action these dice are for comes next
      const act = C.fx.slice(C.fxAt).find(x => x.k === 'act' && x.h === f.h && !x.instant);
      const now = performance.now();
      C.tray = { h: f.h, a: act?.a, t: now, dice: f.dice.map(x => ({ ...x, t: now })) };
      flash('h' + f.h, 'act');
      sfx.play('dice');
      return 760;
    }
    case 'reroll': {
      const x = C.tray?.h === f.h && C.tray.dice.find(y => y.id === f.die);
      if (x) { Object.assign(x, { v: f.v, tag: null, re: f.why || 'reroll', t: performance.now() }); sfx.play('dice'); return 700; }
      addFloat('h' + f.h, `Reroll: ${f.v}`, 'txt'); sfx.play('dice'); return 360;
    }
    case 'act': {
      if (f.instant) return 0;
      flash('h' + f.h, 'act');
      const ad = S.static.actions[f.a];
      if (C.tray?.h === f.h && C.tray.a === f.a && !f.echo) {
        sfx.play(f.hit === false ? 'error' : 'swing');
        if (ad && isRisky(ad.req)) {
          C.tray.verdict = f.hit === false ? 'miss' : 'hit'; C.tray.vt = performance.now();
          if (f.hit !== false) sfx.play('hitwin');
          return 640;
        }
        return 240;
      }
      addFloat('h' + f.h, (ad?.name || '') + (f.echo ? ' (echo)' : '') + (f.hit === false ? ': miss' : ''), f.hit === false ? 'miss' : 'txt');
      sfx.play(f.hit === false ? 'error' : 'swing');
      return 380;
    }
    case 'froll': {
      // an enemy rolls its dice in the open: each die lands, then the total (or what went wrong)
      const fo = foe('f' + f.f);
      const now = performance.now();
      const dice = f.dice || [];
      const each = fo?.intent?.each;
      const total = each || !dice.length ? null : Math.max(0, dice.reduce((a, x) => a + (x.v || 0), 0) + (f.bonus || 0));
      const span = (f.hi ?? 0) - (f.lo ?? 0), third = span / 3;
      const NOTE = { explodes: ['heavy', 'Explodes!'], doubles: ['heavy', 'Doubles!'], skull: ['glancing', 'Skull!'], rider: ['heavy', fo?.intent?.st ? `${STATUS[fo.intent.st]?.name || ''}!` : 'Lands!'] };
      let [verdict, label] = NOTE[f.note] || [null, null];
      if (!verdict && total != null && span > 2) {
        if (total >= f.hi - third) [verdict, label] = ['heavy', 'Heavy!'];
        else if (total <= f.lo + third) [verdict, label] = ['glancing', 'Glancing'];
      }
      C.tray = { fid: f.f, foe: fo?.name || 'Enemy', name: f.name, range: f.lo != null ? `${f.lo}–${f.hi}` : '', t: now, verdict, label, total,
        bonus: f.bonus || 0, vt: now + 420 / (S.settings.speed || 1), dice: dice.map((x, j) => ({ ...x, id: 'f' + f.f + '.' + j, t: now })) };
      flash('f' + f.f, 'act');
      sfx.play('dice');
      setTimeout(render, 440 / (S.settings.speed || 1));
      return 760;
    }
    case 'fact': {
      if (C.tray?.fid !== f.f) C.tray = null;
      flash('f' + f.f, 'act');
      if (f.ik !== 'dazed') sfx.play('swing');
      return 300;
    }
    case 'dmg': {
      if (f.to.startsWith('h')) { const x = +f.to.slice(1); C.hp[x] = (C.hp[x] ?? 0) - f.n; }
      else if (f.to.startsWith('s')) { const al = ally(f.to); if (al) al.hp -= f.n; }
      else { const fo = foe(f.to); if (fo) { fo.hp -= f.n; if (fo.hp <= 0) fo.dying = true; } }
      if (f.block) addFloat(f.to, `◆${f.block}`, 'arm');
      // a big hit: 12 or more, or 40% of its health (at least 8)
      const max = f.to.startsWith('h') ? S.game.heroes[+f.to.slice(1)].maxhp : (foe(f.to) || ally(f.to))?.max || 99;
      const big = f.n >= 12 || (f.n >= 8 && f.n >= max * 0.4);
      if (f.n > 0 || !f.block) addFloat(f.to, big ? `−${f.n}!` : `−${f.n}`, big ? 'dmg.big' : 'dmg');
      flash(f.to, big ? 'bighit' : 'hit', big ? 420 : 300);
      if (big) { flash('stage', 'shake', 380); sfx.play('crit'); } else sfx.play(f.n > 0 ? 'hit' : 'block');
      return big ? 460 : 300;
    }
    case 'heal': {
      if (f.to.startsWith('h')) { const x = +f.to.slice(1); C.hp[x] = (C.hp[x] ?? 0) + f.n; }
      else if (f.to.startsWith('s')) { const al = ally(f.to); if (al) al.hp += f.n; }
      else { const fo = foe(f.to); if (fo) fo.hp += f.n; }
      if (f.n) { addFloat(f.to, `+${f.n}`, f.n >= 10 ? 'heal.big' : 'heal'); sfx.play('heal'); if (f.n >= 10) flash(f.to, 'healbig', 600); }
      return f.n ? 260 : 60;
    }
    case 'armor': addFloat(f.to, `+${f.n} ◆`, 'arm'); sfx.play('block'); return 220;
    case 'combo': {
      const name = S.static.combos?.[f.c]?.name || f.c;
      addFloat(f.to, `${name}! +${f.n}`, 'combo');
      sfx.play('rare');
      return 420;
    }
    case 'st': {
      const name = STATUS[f.s]?.name || { guarded: 'Guarded', taunt: 'Taunt', stunned: 'Stunned', cleansed: 'Cleansed', unbreakable: 'Unbreakable!', sanct: 'Sanctuary', might: 'Might', weakened: 'Weakened', distracted: 'Distracted', dazed: 'Dazed', dodged: 'Dodged!', inspired: 'Inspired', hymn: 'Hymn', rerolls: '+2 rerolls', thorns: 'Thorns!', enraged: 'Enraged!', explodes: 'Bursts!', bloodied: 'Bloodied!', rallies: 'Rallies!', undertow: 'Undertow next', dragged: 'Dragged under!', unwarded: 'Ward broken!', hexed: 'Hexed!', grows: 'Its die grows!', charged: 'Charged!', arced: 'Arced!', robbed: 'Robbed!', resisted: 'Resisted', burn: 'Burn', freeze: 'Frozen', poison: 'Poison' }[f.s] || f.s;
      if (f.to === 'party' || f.to === 'foes') return 200;
      const landed = f.to.startsWith('f') && (f.s === 'stun' || f.s === 'dazed' || f.s === 'freeze');
      addFloat(f.to, landed ? name + '!' : name, landed ? 'stun' : 'txt');
      if (landed) { flash(f.to, 'stunned', 700); sfx.play('stun'); }
      if (f.to.startsWith('f')) { const fo = foe(f.to); if (fo && STATUS[f.s]) fo.st[f.s] = (fo.st[f.s] || 0) + 1; }
      return landed ? 380 : 220;
    }
    case 'die': {
      const u = f.to.startsWith('s') ? ally(f.to) : foe(f.to);
      if (f.to.startsWith('f')) {
        // a kill bursts before it fades
        flash(f.to, 'kill', 520);
        sfx.play('kill');
        setTimeout(() => { if (u) { u.hp = 0; u.dying = false; } render(); }, 380 / (S.settings.speed || 1));
        return 520;
      }
      if (u) u.hp = 0; sfx.play('die'); return 320;
    }
    case 'sact': C.tray = null; flash('s' + f.s, 'act'); sfx.play('swing'); return 300;
    case 'down': { const x = +f.to.slice(1); if (d.hs[x]) d.hs[x].down = true; sfx.play('die'); return 380; }
    case 'lift': { const x = +f.to.slice(1); if (d.hs[x]) d.hs[x].down = false; C.hp[x] = f.n; addFloat(f.to, 'Back up!', 'heal.big'); flash(f.to, 'revive', 800); sfx.play('revive'); return 520; }
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
    case 'retarget': {
      // a Guard, Taunt or distraction swings an enemy's attack: copy the new aim and flash it
      const fo = foe('f' + f.f);
      const live = S.game.fight?.foes.find(x => x.id === f.f);
      if (fo && live?.intent) fo.intent = JSON.parse(JSON.stringify(live.intent));
      (C.swung ||= {})[f.f] = performance.now();
      flash('f' + f.f, 'swung', 700);
      addFloat('f' + f.f, `→ ${unitName(d, f.to)}`, 'txt');
      sfx.play('block');
      return 520;
    }
    case 'flee': { if (d.hs[f.h]) d.hs[f.h].fled = true; return 300; }
    case 'drag': { const fo = foe(f.to); if (fo) fo.row = 'front'; return 220; }
    case 'coins': addFloat('h' + f.h, `+${f.n} gold`, 'gold'); sfx.play('coin'); return 260;
    case 'revive': addFloat('h' + f.h, 'Revived', 'heal.big'); flash('h' + f.h, 'revive', 800); sfx.play('revive'); return 600;
    case 'dead': bigBanner(`${S.game.heroes[f.h].name} has fallen`, 'No revives were left', 'danger', 2400); sfx.play('lose'); return 1200;
    case 'phase': {
      bigBanner(f.n === 2 ? 'The tide turns' : 'The Crown stands alone', f.n === 2 ? 'Each round the Undertow drags someone under: Armor or a Guard stops it' : 'Exposed: it takes 50% more, but every attack rolls an extra die', 'danger', 2600);
      flash('stage', 'shake', 500);
      sfx.play('phase');
      return 1400;
    }
    default: return 120;
  }
}
