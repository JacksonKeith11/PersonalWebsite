// The fight overlay: the party and the enemies (in their rows), enemy intents, the round so far, and your dice
// tray and actions. When a round resolves, the server's effects are played back one at a time on
// a copy of the fight as it was, then the new state is shown.
import { S, send, mine, controllerName } from './store.js?v=88';
import { h, icon, toast, hideTip, bigBanner } from './ui.js?v=88';
import { spriteURL } from './art.js?v=88';
import { stageURL, stageKey } from './stage.js?v=88';
import { reqText, STATUS, dieLabel, dieTip, hitChance, countOk, expected, isRisky, faceText, foeTraits } from './rules.js?v=88';
import { render } from './main.js?v=88';
import { skillCard } from './hud.js?v=88';
import * as sfx from './audio.js?v=88';

const C = { sel: new Set(), pending: null, tab: null, hidden: false, playing: false, display: null, hp: null, anim: {}, floats: {}, lastId: null, lastRound: null,
  trayEl: null, traySig: null, autoDone: new Set() };
let host = null;

export function combatOpen() {
  const f = C.playing ? C.display : S.game?.fight;
  if (!f) return false;
  // a hero walking into the fight finishes the walk before the fight takes the screen
  if (performance.now() < holdUntil) return false;
  const inIt = mine().some(x => f.heroes.includes(x));
  return inIt || !C.hidden;
}
export function showFight() { C.hidden = false; render(); }
export function combatBusy() { return C.playing || queue.length > 0; }
let holdUntil = 0;
// Keep the fight off the screen for `ms` (while the map plays the walk that started it).
export function holdCombat(ms) {
  holdUntil = Math.max(holdUntil, performance.now() + ms);
  setTimeout(render, ms + 30);
}
// Run `fn` once the fight on screen has played out (its last blow and the Victory banner), or now if
// nothing is playing: level-ups, gold and the like shouldn't land in the middle of a fight's animations.
let idle = [];
export function afterCombat(fn) {
  if (combatBusy()) idle.push(fn);
  else fn();
}
function flushIdle() {
  const fns = idle;
  idle = [];
  for (const fn of fns) fn();
}

const KEYS = ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'];
const INTENT = {
  attack: ['sword', 'var(--intent-attack)'], all: ['skull', 'var(--intent-attack)'],
  block: ['shield', 'var(--intent-defend)'], guard: ['shield', 'var(--intent-defend)'], heal: ['plus', 'var(--intent-heal)'],
  buff: ['up', 'var(--intent-buff)'], debuff: ['eye', 'var(--intent-debuff)'], summon: ['spark', 'var(--intent-buff)'],
  charge: ['bolt', 'var(--intent-buff)'], dazed: ['clock', 'var(--muted)'],
  thief: ['coin', 'var(--intent-debuff)'], merge: ['spark', 'var(--intent-buff)'],
};
const INTENT_TEXT = {
  attack: 'Attack', all: 'Hits everyone', block: 'Defend', guard: 'Shields an ally', heal: 'Heals an ally',
  buff: 'Strengthens allies for the rest of the fight', debuff: 'Curses a hero', summon: 'Calls for help', charge: 'Gathering power…', dazed: 'Caught off guard: does nothing this round', thief: 'Snatches a potion', merge: 'Merges with another',
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
    const max = C.playing && C.maxhp ? C.maxhp[x] ?? hero.maxhp : hero.maxhp;
    const st = hs ? hs.st : {};
    const cl = ['unit', 'hero'];
    if (hs?.down) cl.push('down');
    if (hs?.fled) cl.push('fled');
    if (C.anim['h' + x]) cl.push(C.anim['h' + x]);
    if (x === active) cl.push('mine-sel');
    if (isTarget('h' + x, f)) cl.push('target');
    const ready = hs?.ready && !C.playing;
    return h('div.' + cl.join('.'), { 'data-uid': 'h' + x, style: { '--seat': `var(--hero-${x})` }, tip: mine().includes(x) ? null : heroTip(x, hs) },
      h('div.intent' + (ready ? '' : '.none'), { style: { '--c': 'var(--ok)' } }, icon('check'), 'Ready'),
      h('img.pix', { src: spriteURL(hero.cls), alt: '' }),
      // another player's hero: who plays it (by the name), and the dice they hold this round (for combos)
      h('div.uname', { style: { color: `var(--hero-${x})` } }, hero.name, mine().includes(x) ? null : h('span.ctl-name', null, ` · ${controllerName(x)}`),
        f.taunt === x ? ' · taunting' : '', Object.values(f.guard || {}).includes(x) ? ' · guarding' : ''),
      !mine().includes(x) && hs?.dice?.length ? h('div.ally-dice', { tip: `${hero.name}'s dice this round\nFaded ones are spent; a number shows once it's rolled.` },
        ...hs.dice.map(dd => h('span.die-mini' + (dd.used ? '.used' : ''), { tip: `${dieLabel(dd)}\n${dieTip(dd)}` }, dd.v != null ? String(dd.v) : `d${topOf(dd)}`))) : null,
      hs?.swallowed ? h('div.covered-chip.undertow', { tip: 'Swallowed: no dice, and you take damage each round until the Reef Maw spits you out.' }, 'Swallowed!') : null,
      hs?.static ? h('div.covered-chip.undertow', { tip: 'Static: any of your dice that rolls 1 or 2 shocks you for 3 this round.' }, 'Static: 1–2 shocks you') : null,
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
    return h('div.' + cl.join('.'), { 'data-uid': 'f' + fo.id, tip: foeTip(fo) },
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
      fo.hp > 0 ? foeState(fo, f) : null,
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
  const col = (label, units, party) => h('div.col' + (party ? '.herocol' : '') + (units.length >= 2 || party ? '.crowd' : '') + (!units.length ? '.empty' : ''), null, h('span.lbl', null, label), ...units);
  const stage = h('div.stage' + (C.anim.stage ? '.' + C.anim.stage : ''), { style: { '--stage-art': `url(${stageURL(stageKey(f, S.world))})` } },
    h('div.side-units' + (allies.length ? '' : '.solo'), null,
      allies.length ? col('Allies', allies.map(unitAlly)) : null,
      col('Party', f.heroes.map(unitHero), true)),
    h('div.side-units', null,
      col('Front', foesIn('front').map(unitFoe)),
      col('Back', foesIn('back').map(unitFoe))),
    rollTray(),
    C.inspect != null && f.heroes.includes(C.inspect) ? allyPanel(f, C.inspect) : null,
    C.playing && queue.length ? h('div.queue-badge', { tip: 'Plays still to show: they play faster until caught up' }, `+${queue.length} more`) : null,
    C.caption ? h('div.act-caption', { style: { '--seat': `var(--hero-${C.caption.h})` } }, h('b', null, C.caption.text), h('span', null, C.caption.what)) : null);

  const done = f.done || [];
  const combos = S.static.combos || {};
  const comboTip = 'Combos: what two heroes do together\n' + Object.values(combos).map(c => `${c.name}: ${c.text}`).join('\n');
  const live0 = S.game.fight;
  // while a round plays back, only once it's this round's (an older one would sit over the new enemy turn)
  const recap = !C.playing || (live0 && live0.id === f.id && live0.round === f.round) ? recapChips(f, done.length > 0) : [];
  const plan = h('div.planstrip', null, ...recap, h('span.eyebrow', null, 'This round'),
    h('span.chip.brass.combo-help', { tip: comboTip }, icon('spark'), 'Combos'),
    done.length ? stripChips(done, f) : recap.length ? null : h('span.muted', { style: { fontSize: '14px' } }, 'Actions happen the moment they’re played, in the order the party plays them. Enemies act once everyone is ready.'));

  let bottom, giveBelow = false;
  const spiritMine = mine().filter(x => f.spirit?.[x] && !f.spirit[x].used);
  // your dice stay on screen (locked) while an action plays out mid-round, so the next move is in view
  const live = S.game.fight;
  const sameRound = live && live.id === f.id && live.round === f.round;
  if (active !== null && (!C.playing || sameRound) && live?.hs[active]) {
    // the tray is rebuilt only when something it shows changes: rebuilding it under the pointer while
    // a play animates (several times a second) dropped clicks and flickered tooltips
    const sig = traySig(live, active, my);
    if (sig !== C.traySig || !C.trayEl) { C.traySig = sig; C.trayEl = tray(live, active, my); }
    bottom = C.trayEl;
  }
  else if (spiritMine.length && !C.playing) { bottom = spiritBar(f, spiritMine[0]); giveBelow = true; }
  else {
    const waiting = f.heroes.filter(x => heroActive(f, x) && !f.hs[x].ready).map(x => g.heroes[x].name);
    bottom = h('div.watch', null, h('span', null, C.playing ? playingLine() : waiting.length ? `Waiting for ${waiting.join(', ')}` : ''),
      !mine().some(x => f.heroes.includes(x)) ? h('button.btn', { onclick: () => { C.hidden = true; hideTip(); render(); } }, 'Back to the map') : null);
  }

  // keep the overlay element between renders so its entrance animation plays only once
  let box = el.firstElementChild;
  if (!box || !box.classList.contains('combat')) {
    box = h('div.combat.enter', { role: 'dialog', 'aria-label': 'Fight' });
    // clicks on fighters are read where the pointer is let go, so a fighter redrawn between press and
    // release (a play animating) still takes the click
    box.addEventListener('pointerdown', e => { C.down = e.button === 0 && !!e.target.closest?.('[data-uid]'); });
    box.addEventListener('pointerup', e => {
      if (!C.down || e.button !== 0) return;
      C.down = false;
      const u = document.elementFromPoint(e.clientX, e.clientY)?.closest?.('.combat [data-uid]');
      if (u && !u.closest('.tray')) targetClick(u.dataset.uid);
    });
    el.replaceChildren(box);
  }
  const head = h('div.combat-head', null,
      h('span.round', null, `Round ${f.round}`),
      h('h2', null, fightTitle(f)),
      f.phase >= 2 ? h('span.chip', { style: { color: 'var(--info)', borderColor: 'var(--info)' } }, icon('wave'), f.phase >= 3 ? 'The Crown is alone: exposed and furious' : 'The Undertow drags someone under each round') : null,
      !mine().some(x => f.heroes.includes(x)) ? h('span.chip', null, icon('eye'), 'Watching') : null,
      // a fallen hero's spirit die, whenever the bar below isn't offering it
      spiritMine.length && !giveBelow ? spiritBar(f, spiritMine[0], true) : null);
  // swap the parts in place; an unchanged tray stays put
  [head, stage, plan, bottom].forEach((k, i) => {
    const old = box.children[i];
    if (old === k) return;
    if (old) old.replaceWith(k); else box.append(k);
  });
  while (box.children.length > 4) box.lastElementChild.remove();
  C.rolled = false;
  if (live) maybeAutoReady(live);
  requestAnimationFrame(() => {
    drawArrows(box, f);
    // keep the newest play in view when one is added (not while someone scrolls back through them)
    const strip = box.querySelector('.planstrip');
    if (strip && done.length !== C.stripLen) { C.stripLen = done.length; strip.scrollLeft = strip.scrollWidth; }
  });
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
    if (fo.hp <= 0 || !it || !ARROW[it.k] || fo.st.stun) continue;
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
function foeState(fo, f) {
  // what makes this enemy different right now, in words
  const chips = [];
  const live = f.heroes.filter(y => f.hs[y] && !f.hs[y].down && !f.hs[y].fled).length;
  if (fo.bell && !fo.cracked) chips.push(h('span.combo-hint', { tip: `The bell\nHit the Bell-Warden with a die showing ${fo.bell} to crack the bell: +6 damage, and its next attack is Weak.` }, `Bell ${fo.bell}: hit it with a ${fo.bell}`));
  if (fo.st?.knell) chips.push(h('span.st', { tip: `Death Knell\n${STATUS.knell.text}` }, icon('clock'), fo.st.knell === 1 ? 'Knell next round' : `Knell in ${fo.st.knell}`));
  if (fo.k === 'lamp_keeper' && fo.intent?.m === 'gather') chips.push(h('span.combo-hint', { tip: 'Gathering light\nPut the lamp out this round (hit it with different heroes) and the Lighthouse Beam scatters. Otherwise it fires next round.' }, 'Douse it now to scatter the beam'));
  if (S.static.foes[fo.k]?.keg) chips.push(h('span.combo-hint', { tip: 'Powder Keg\nIt blows up on the whole party after its fuse burns down. Break it first and it blows up among the enemies instead.' }, 'Break it: it blows on them'));
  if (fo.k === 'lamp_keeper') chips.push(fo.lit === false ? h('span.st', { tip: 'The lamp is out: full damage until the end of next round.' }, 'Dark: full damage')
    : h('span.combo-hint', { tip: `Lit\nTakes half damage. Hit it with ${Math.min(3, live)} different heroes in one round to put the lamp out: in the dark it takes full damage this round and next, and its next attack is Weak.` }, `Lit: ½ damage · ${(fo.hitr || []).length}/${Math.min(3, live)} heroes`));
  if (fo.air) chips.push(h('span.st.bad', { tip: 'Airborne: melee attacks can’t reach it. Use ranged attacks and spells.' }, 'Airborne: no melee'));
  if (fo.loot) chips.push(h('span.st.bad', { tip: 'It has your potion. Kill it before it flies off to get it back.' }, `Has ${S.static.items[fo.loot]?.name || 'loot'} · flees in ${fo.flee_in}`));
  if (fo.merged) chips.push(h('span.st', { tip: 'Merged: every attack rolls an extra die for each merge.' }, `Merged ×${fo.merged + 1}`));
  if (fo.gut) chips.push(h('span.st.bad', { tip: 'A hero is inside. Deal this much more damage to it and it spits them out.' }, `Spits out in ${fo.gut} dmg`));
  return chips.length ? h('div.combo-hints', null, ...chips) : null;
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

const ST_SHORT = { steeled: 'Steeled', vuln: 'Vuln', stun: 'Stunned', freeze: 'Frozen', root: 'Rooted', shock: 'Shocked', hex: 'Hexed', crescendo: 'Crescendo', lifeline: 'Lifeline' };
function statusRow(st, extra = [], tail = []) {
  const chips = [];
  for (const [k, v] of Object.entries(st || {})) {
    if (!v || ['doomt', 'warded', 'exposed', 'undertow', 'knell'].includes(k)) continue;
    const s = STATUS[k];
    if (!s) continue;
    const n = ['stun', 'freeze', 'shock', 'warded', 'exposed', 'steeled'].includes(k) ? '' : v;
    // icon, short name and number, so a status reads at a glance ("Armor 3", "Rooted")
    chips.push(h('span.st.' + (k === 'armor' ? 'armor' : s.bad ? 'bad' : 'good') + '.' + k, { tip: `${s.name}${n !== '' ? ' ' + n : ''}\n${s.text}` }, icon(s.icon),
      h('span.st-name', null, ST_SHORT[k] || s.name), n !== '' ? h('b', null, n) : null));
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
  if (t.round) {
    return h('div.roll-tray.round-mark', { style: since(t.t), role: 'status' },
      h('div.rt-info', null, h('span.rt-who', null, 'New round'), h('span.rt-act', null, `Round ${t.round}`), h('span.rt-need', null, 'Fresh dice for everyone')));
  }
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
  if (u.startsWith('f')) return (f.foes || []).find(fo => 'f' + fo.id === u)?.name || 'an enemy';
  return (f.allies || []).find(a => 's' + a.id === u)?.name || 'a summon';
}

// An enemy's intent: what move, which dice, the range, and who it's aimed at. The tooltip spells
// out every rule the move has.
function intentChip(fo, f) {
  const it = fo.intent;
  if (!it || fo.hp <= 0) return h('div.intent.none', null, '·');
  // a Stunned enemy skips its next action, so what it meant to do no longer matters
  if (fo.st.stun) return h('div.intent.card', { style: { '--c': 'var(--muted)' }, tip: 'Stunned\nSkips its action this round.' },
    h('div.it-name', null, h('span.ic', null, icon('spark')), 'Stunned'), h('div.it-row', null, h('span.it-what', null, 'skips its turn')));
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
  else if (it.k === 'charge') lines.push(A_CHARGE(fo) + (it.next ? ` Next round: ${S.static.foes[fo.k].moves[it.next]?.name || 'something big'}.` : ''));
  else if (it.k === 'thief') lines.push('Snatches a potion from this hero’s bag. Kill it within two rounds of the theft to get it back.');
  else if (it.k === 'merge') lines.push('Merges with another of its kind: their health adds up, and it rolls an extra die.');
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
  // what it did: the damage, healing, Armor, kills and statuses it set off
  const o = p.out || {};
  const what = outcomeText(o);
  const nums = [];
  if (o.dmg) nums.push(h('span.o-dmg', null, icon('sword'), o.dmg));
  if (o.heal) nums.push(h('span.o-heal', null, icon('plus'), o.heal));
  if (o.armor) nums.push(h('span.o-armor', null, icon('shield'), o.armor));
  if (o.kills) nums.push(h('span.o-kill', null, icon('skull'), o.kills > 1 ? `×${o.kills}` : ''));
  const rolled = (p.vals || []).length ? `Rolled ${p.vals.join(', ')}. ` : '';
  return h('span.plan-chip' + (p.hit === false ? '.missed' : ''), { style: { '--seat': `var(--hero-${p.h})` },
    tip: `${g.heroes[p.h].name}: ${a.name}${p.plus ? '+' : ''}${tgt ? ' → ' + tgt : ''}\n${rolled}${p.hit === false ? 'Missed. ' : ''}${what || 'No visible effect.'}\n${a.text}` },
    h('span.muted', null, `${i + 1}.`), h('span.who', null, mine().includes(p.h) ? g.heroes[p.h].name : controllerName(p.h)), h('b', null, a.name + (p.plus ? '+' : '')), tgt ? h('span.muted', null, '→ ' + tgt) : null, res,
    ...nums, h('span', { style: { width: '6px' } }));
}
// What the enemies' last turn did (`f.last`, recorded by the server): a chip per enemy action, with
// what it did to each hero or summon; once the party has played this round, one folded chip.
function recapChips(f, folded) {
  const turn = (f.last || []).filter(e => e.f != null || e.ev.length);
  if (!turn.length) return [];
  const g = S.game;
  const nameOf = u => u.startsWith('h') ? g.heroes[+u.slice(1)].name
    : u.startsWith('s') ? (f.allies || []).find(a => 's' + a.id === u)?.name || 'Summon'
    : f.foes.find(fo => 'f' + fo.id === u)?.name || 'Enemy';
  const stName = k => STATUS[k]?.name || k[0].toUpperCase() + k.slice(1);
  const party = u => u.startsWith('h') || u.startsWith('s');
  const rows = turn.map(e => {
    const per = new Map();
    for (const ev of e.ev) {
      if (!ev.to || (e.f != null && !party(ev.to) && ev.to !== 'f' + e.f)) continue;
      if (!per.has(ev.to)) per.set(ev.to, { dmg: 0, block: 0, heal: 0, armor: 0, down: false, st: [] });
      const o = per.get(ev.to);
      if (ev.k === 'dmg') { o.dmg += ev.n || 0; o.block += ev.block || 0; }
      else if (ev.k === 'heal') o.heal += ev.n || 0;
      else if (ev.k === 'armor') o.armor += ev.n || 0;
      else if (ev.k === 'down' || ev.k === 'die') o.down = true;
      else if (ev.k === 'st' && ev.s) o.st.push(ev.s);
    }
    const hits = [...per].filter(([u, o]) => party(u) && (o.dmg || o.block || o.down || o.st.length));
    const self = e.f != null ? per.get('f' + e.f) : null;
    const words = (u, o) => {
      const p = [];
      if (o.dmg || o.block) p.push(`${o.dmg} damage${o.block ? ` (${o.block} blocked)` : ''}`);
      if (o.heal) p.push(`healed ${o.heal}`);
      if (o.armor) p.push(`${o.armor} Armor`);
      if (o.st.length) p.push(o.st.map(stName).join(', '));
      if (o.down) p.push(u.startsWith('h') ? 'knocked down' : u.startsWith('s') ? 'destroyed' : 'dies');
      return `${nameOf(u)}: ${p.join(', ') || 'nothing'}`;
    };
    const lines = [...per].filter(([u]) => e.f == null || party(u) || u === 'f' + e.f).map(([u, o]) => words(u, o));
    return { e, hits, self, tip: `${e.who}${e.a ? ': ' + e.a : ''}\n${lines.join('\n') || 'No visible effect.'}` };
  });
  const head = h('span.eyebrow', { tip: 'What the enemies did on their last turn' }, 'Enemy turn');
  if (folded) {
    const dmg = rows.reduce((a, r) => a + r.hits.reduce((b, [, o]) => b + o.dmg, 0), 0);
    const downs = rows.reduce((a, r) => a + r.hits.filter(([u, o]) => o.down && u.startsWith('h')).length, 0);
    return [head, h('span.plan-chip.folded.foe-chip', { tip: rows.map(r => r.tip).join('\n\n') },
      h('span.muted', null, `${rows.length} action${rows.length === 1 ? '' : 's'}`),
      dmg ? h('span.o-dmg', null, icon('sword'), dmg) : null,
      downs ? h('span.o-kill', null, icon('skull'), downs > 1 ? `×${downs}` : '') : null,
      h('span', { style: { width: '6px' } })), h('span.strip-gap')];
  }
  return [head, ...rows.map(({ e, hits, self, tip }) => h('span.plan-chip.foe-chip', { tip },
    h('span.who', null, e.who), e.a ? h('b', null, e.a) : null,
    ...hits.flatMap(([u, o]) => [
      h('span.muted', null, '→ ' + nameOf(u)),
      o.dmg || !o.block ? h('span.o-dmg', null, icon('sword'), o.dmg) : null,
      o.block ? h('span.o-armor', { }, icon('shield'), o.block) : null,
      o.down ? h('span.o-kill', null, icon('skull')) : null]),
    !hits.length && self?.armor ? h('span.o-armor', null, icon('shield'), self.armor) : null,
    !hits.length && self?.heal ? h('span.o-heal', null, icon('plus'), self.heal) : null,
    h('span', { style: { width: '6px' } }))), h('span.strip-gap')];
}

// The round strip: the last three plays in full; each hero's earlier ones folded into one chip with
// their totals (hover for the list), so the newest never scroll out of sight.
function stripChips(done, f) {
  const KEEP = 3;
  if (done.length <= KEEP + 1) return done.map((p, i) => doneChip(p, i, f));
  const older = done.slice(0, done.length - KEEP), out = [];
  const byHero = new Map();
  older.forEach((p, i) => { if (!byHero.has(p.h)) byHero.set(p.h, []); byHero.get(p.h).push([p, i]); });
  for (const [x, list] of byHero) {
    const sum = k => list.reduce((a, [p]) => a + ((p.out || {})[k] || 0), 0);
    const tip = list.map(([p, i]) => `${i + 1}. ${S.static.actions[p.a].name}${p.hit === false ? ' (missed)' : ''}: ${outcomeText(p.out || {}) || 'no visible effect'}`).join('\n');
    out.push(h('span.plan-chip.folded', { style: { '--seat': `var(--hero-${x})` }, tip: `${heroWho(x)}, earlier this round\n${tip}` },
      h('span.who', null, mine().includes(x) ? S.game.heroes[x].name : controllerName(x)), h('span.muted', null, `×${list.length}`),
      sum('dmg') ? h('span.o-dmg', null, icon('sword'), sum('dmg')) : null,
      sum('heal') ? h('span.o-heal', null, icon('plus'), sum('heal')) : null,
      sum('armor') ? h('span.o-armor', null, icon('shield'), sum('armor')) : null,
      sum('kills') ? h('span.o-kill', null, icon('skull'), sum('kills') > 1 ? `×${sum('kills')}` : '') : null,
      h('span', { style: { width: '6px' } })));
  }
  return [...out, ...done.slice(-KEEP).map((p, j) => doneChip(p, done.length - KEEP + j, f))];
}

// An action's outcome in words, for the round strip's tooltips.
function outcomeText(o) {
  const parts = [];
  if (o.dmg) parts.push(`${o.dmg} damage`);
  if (o.kills) parts.push(o.kills > 1 ? `${o.kills} kills` : 'a kill');
  if (o.heal) parts.push(`healed ${o.heal}`);
  if (o.armor) parts.push(`${o.armor} Armor`);
  if (o.hurt) parts.push(`cost ${o.hurt} HP`);
  const st = (o.st || []).map(k => STATUS[k]?.name).filter(Boolean);
  if (st.length) parts.push(st.join(', '));
  return parts.length ? parts[0][0].toUpperCase() + parts.join(', ').slice(1) + '.' : '';
}

// Everything the tray shows, so it's rebuilt only when one of them changes.
function traySig(f, x, my) {
  const g = S.game, hero = g.heroes[x], hs = f.hs[x];
  return JSON.stringify([f.id, f.round, x, my, hs, hero.actions, hero.bag, hero.spent, f.hymn, f.foes, f.lastdie,
    f.heroes.map(y => [f.hs[y]?.ready, f.hs[y]?.down, f.hs[y]?.fled]), [...C.sel], C.pending?.msg ?? null, C.playing && !hs.ready]);
}

// After a hero readies, the tray moves to the next hero you play who still has to act.
function nextTab(x) {
  const f = S.game.fight;
  if (!f) return;
  const my = mine().filter(y => f.heroes.includes(y) && heroActive(f, y));
  const next = my.find(y => y !== x && !f.hs[y].ready);
  if (next !== undefined) { C.tab = next; C.sel.clear(); C.pending = null; }
}
function readyUp(x) {
  send({ t: 'fready', h: x });
  C.sel.clear(); C.pending = null;
  nextTab(x);
}

// The "Ready when my dice are spent" setting: once a hero you play has used every die (a Barnacle-
// crusted one can't be used, so it doesn't count), they ready up, once per round; unreadying sticks.
function maybeAutoReady(live) {
  if (!S.settings.autoReady) return;
  const spent = hs => hs.dice.every(d => d.used || d.locked);
  for (const x of mine()) {
    const hs = live.hs[x];
    if (!live.heroes.includes(x) || !hs || hs.ready || !heroActive(live, x) || !spent(hs)) continue;
    const key = `${live.id}:${live.round}:${x}`;
    if (C.autoDone.has(key)) continue;
    C.autoDone.add(key);
    // a beat first: an instant action can hand back a fresh die
    setTimeout(() => {
      const f = S.game.fight, h2 = f?.hs[x];
      if (f && f.id === live.id && f.round === live.round && h2 && !h2.ready && heroActive(f, x) && spent(h2)) { readyUp(x); render(); }
    }, 450);
  }
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
        : h('button.btn.primary.lg' + (hs.dice.length && hs.dice.every(d => d.used) ? '.nudge' : ''), { onclick: () => { readyUp(x); render(); } }, icon('check'), 'Ready', h('span.kbd', null, 'Space'))));
}

// A die in the tray: face-down (its kind and size) until it rolls, unless it's a Seer die (shown),
// an Augur die (high or low) or a Fate die (two faces).
// A die in the tray: a cream tile with its size (or its number, once known) big in the middle, a
// coloured top edge for where it comes from, and one icon for anything special about it.
const SRC = { base: ['Class die', 'var(--src-class)'], weapon: ['Weapon die', 'var(--src-weapon)'], armor: ['Armor die', 'var(--src-armor)'],
  trinket: ['Trinket die', 'var(--src-trinket)'], spirit: ['Spirit die from a fallen ally', 'var(--src-spirit)'], pet: ['Your hawk’s die', 'var(--src-pet)'],
  anthem: ['From the Anthem of Kings', 'var(--src-spirit)'], gift: ['Given by an ally', 'var(--src-spirit)'], hex: ['Cursed: a hex swapped your biggest die', 'var(--danger)'],
  split: ['Split off by your flask', 'var(--src-class)'], graft: ['Grafted from two dice', 'var(--src-class)'], tempo: ['Stolen tempo: a fresh die', 'var(--src-spirit)'], bloodlust: ['Bloodlust: a fresh die from a kill', 'var(--src-spirit)'] };
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
  const bells = d.v != null && !d.used && f0 ? f0.foes.filter(fo => fo.hp > 0 && fo.bell && !fo.cracked && fo.bell === d.v) : [];
  if (pinc.length || bells.length) cls += '.combo';
  if (d.locked) cls += '.locked';
  const tip = `${srcName}\n${dieTip(d)}${d.v == null && !d.fc ? `\nHidden until its action happens. Averages about ${expected(d).toFixed(1)}.` : ''}${d.bonus ? `\nRolls ${d.bonus} higher.` : ''}${pinc.length ? `\nPincer +5 on ${pinc.join(', ')}: it matches an ally's die.` : ''}${bells.length ? '\nMatches the bell: hit the Bell-Warden with it to crack the bell.' : ''}${d.locked ? '\nCrusted over by a Barnacle Priest: you can’t use it this round.' : ''}`;
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
  const chance = fits && n > 0 ? hitChance(a.req, selDice, f.hymn || 0, hs.rollmods) : auto && isRisky(a.req) ? hitChance(a.req, auto, f.hymn || 0, hs.rollmods) : null;
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

function spiritBar(f, d, compact = false) {
  const g = S.game, sp = f.spirit[d];
  const targets = f.heroes.filter(x => heroActive(f, x));
  const say = `${g.heroes[d].name}’s spirit lingers. Give your die `;
  return h(compact ? 'div.give-row' : 'div.watch', null,
    h('span', null, say, h('b', { style: { color: 'var(--accent)' } }, sp.v), ' to:'),
    ...targets.map(x => h('button.btn' + (compact ? '.sm' : ''), { onclick: () => send({ t: 'spirit', h: d, to: x }) }, g.heroes[x].name)));
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
      const p = hitChance(a.req, combo, f.hymn || 0, f.hs[x]?.rollmods);
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
  // not aiming anything: clicking a hero shows what they can do (your own switches your tray to them)
  if (!C.pending && id.startsWith('h')) {
    const x = +id.slice(1);
    if (mine().includes(x) && S.game.fight?.hs[x] && heroActive(S.game.fight, x)) { C.tab = x; C.sel.clear(); C.inspect = null; }
    else C.inspect = C.inspect === x ? null : x;
    render();
    return;
  }
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
  if (e.key === 'Escape' && C.inspect != null) { C.inspect = null; render(); return; }
  if (x === null) return;
  const hs = f.hs[x];
  if (!hs) return;
  if (e.code === 'Space') { e.preventDefault(); if (hs.ready) { send({ t: 'fready', h: x, on: false }); C.sel.clear(); C.pending = null; } else { readyUp(x); render(); } return; }
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
const COMBAT_FX = new Set(['round', 'combo', 'froll', 'roll', 'reroll', 'sact', 'act', 'fact', 'dmg', 'heal', 'armor', 'st', 'die', 'down', 'lift', 'summon', 'retarget', 'flee', 'drag', 'fightend', 'phase', 'revive', 'dead', 'coins']);

const queue = [];
export function combatFx(list, before) {
  const fx = list.filter(f => COMBAT_FX.has(f.k));
  if (list.some(f => f.k === 'fight')) sfx.play('fight');
  if (list.some(f => f.k === 'round')) sfx.play('dice');
  if (!fx.length) return;
  const ends = fx.some(f => f.k === 'round' || f.k === 'fightend');
  queue.push({ fx, ends, before: before ? JSON.parse(JSON.stringify(before)) : null });
  // The stage never falls a round behind the dice: once a round has ended, the plays before its end
  // hurry (6×, see playNext), and beyond the last three they're skipped (the end's starting state
  // already shows them, and "This round" lists them).
  const j = queue.findIndex(q => q.ends);
  if (j > 3) queue.splice(0, j - 3);
  if (!C.playing) playNext();
}

// Rounds play back one after another, each from the state just before it.
function playNext() {
  const next = queue.shift();
  if (!next) { if (!C.playing) flushIdle(); return; }
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
  // max HP too: a level-up the fight earned shouldn't show on the health bars before it's over
  C.maxhp = Object.fromEntries(before.heroes.map((x, i) => [i, x.maxhp]));
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
    setTimeout(step, wait / (speed * (queue.some(q => q.ends) ? 6 : queue.length ? 1 + Math.min(queue.length, 4) * 0.75 : 1)));
  };
  setTimeout(step, 150 / speed);
}

function finish(ended) {
  const close = () => {
    C.playing = false; C.display = null; C.hp = null; C.maxhp = null; C.anim = {}; C.floats = {}; C.tray = null; C.caption = null;
    if (queue.length) { playNext(); return; }
    render();
    flushIdle();
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
// A hero's sheet in a fight, opened by clicking them: every action with its cooldown, their passives
// and this round's dice, so you can see what an ally can do for you.
function allyPanel(f, x) {
  const g = S.game, hero = g.heroes[x], hs = f.hs[x] || {};
  const acts = hero.actions.filter(k => !['block', 'shift', 'flee'].includes(k));
  const passives = hero.skills.filter(k => S.static.passives[k.replace(/\+$/, '')]);
  const weapon = hero.equip.weapon ? S.static.items[hero.equip.weapon] : null;
  const cdNote = k => { const n = hs.cds?.[k.replace(/\+$/, '')]; return n ? h('span.chip', { style: { color: 'var(--warn, #e0a84a)' } }, icon('clock'), `ready in ${n}`) : null; };
  return h('div.ally-panel', { style: { '--seat': `var(--hero-${x})` }, onclick: e => e.stopPropagation() },
    h('header', null,
      h('img.pix', { src: spriteURL(hero.cls), alt: '' }),
      h('div', { style: { flex: 1 } }, h('b', null, hero.name), h('span.muted', null, `${S.static.classes[hero.cls].name === hero.name ? '' : S.static.classes[hero.cls].name + ' · '}${hero.hp} / ${hero.maxhp} HP${hs.ready ? ' · ready' : ''}`)),
      h('button.btn.icon.ghost', { 'aria-label': 'Close', onclick: () => { C.inspect = null; render(); } }, icon('x'))),
    (hs.dice || []).length ? h('div.ap-dice', null, h('span.muted', null, 'Dice this round'),
      ...hs.dice.map(d => h('span.die-mini' + (d.used ? '.used' : ''), { tip: dieTip(d) }, d.v != null ? String(d.v) : dieLabel(d)))) : null,
    h('div.ap-body', null,
      h('h4', null, 'Actions'),
      ...acts.map(k => h('div.ap-act', null, skillCard(k, (weapon?.acts || []).includes(k.replace(/\+$/, '')) ? weapon.name : null), cdNote(k))),
      passives.length ? h('h4', null, 'Passives') : null,
      ...passives.map(k => skillCard(k))));
}

// An ally's actions in a fight, for the tooltip on their portrait: what each does and when it's ready.
function heroTip(x, hs) {
  const hero = S.game.heroes[x];
  const cn = S.static.classes[hero.cls].name;
  const lines = [hero.name === cn ? cn : `${hero.name} · ${cn}`];
  for (const k of hero.actions.filter(k => !['block', 'shift', 'flee'].includes(k))) {
    const a = S.static.actions[k.replace(/\+$/, '')];
    if (!a) continue;
    const cd = hs?.cds?.[k.replace(/\+$/, '')];
    lines.push(`${a.name}${k.endsWith('+') ? '+' : ''}${cd ? ` (ready in ${cd})` : ''}: ${a.text}`);
  }
  lines.push('Click for their full sheet.');
  return lines.join('\n');
}

// ------------------------------------------------------------------ what an action looks like
// Each action plays out on the stage so it's clear what it did: a melee hero lunges and the target
// is slashed, a ranged one looses an arrow, a spell flies as an orb and bursts, a heal glows green on
// whoever it heals, Armor shimmers blue. The effects sit in a fixed layer over the page, so the
// stage can redraw underneath them.
function abilityKind(ad) {
  const ops = ad.ops || [];
  if (ops.some(o => o.op === 'heal' || o.op === 'lift')) return 'heal';
  if (ops.some(o => o.op === 'dmg' || o.op === 'bomb')) return ad.melee ? 'melee' : ad.spell ? 'spell' : ad.bomb ? 'bomb' : 'ranged';
  if (ops.some(o => ['armor', 'guard', 'taunt', 'block', 'sanct'].includes(o.op))) return 'armor';
  if (ad.spell) return 'spell';
  return 'buff';
}
// Who an action lands on: its target, or everyone a group action reaches.
function abilityTargets(f, ad, d) {
  const live = (d.foes || []).filter(fo => fo.hp > 0);
  const party = (d.heroes || []).filter(x => !d.hs[x]?.down).map(x => 'h' + x);
  switch (ad.tgt) {
    case 'foes': return live.map(fo => 'f' + fo.id);
    case 'front': { const fr = live.filter(fo => fo.row !== 'back'); return (fr.length ? fr : live).map(fo => 'f' + fo.id); }
    case 'party': case 'allies': return party;
    case 'self': return ['h' + f.h];
    default: return typeof f.tgt === 'string' ? [f.tgt] : ['h' + f.h];
  }
}
function fxLayer() {
  let el = document.getElementById('fx-layer');
  if (!el) { el = document.createElement('div'); el.id = 'fx-layer'; document.body.appendChild(el); }
  return el;
}
function unitCenter(id) {
  const img = host?.querySelector(`[data-uid="${id}"] img`);
  if (!img) return null;
  const r = img.getBoundingClientRect();
  return [r.left + r.width / 2, r.top + r.height / 2];
}
function fxAt(id, cls, ms = 650) {
  const c = unitCenter(id);
  if (!c) return;
  const el = document.createElement('div');
  el.className = 'fx ' + cls;
  el.style.left = c[0] + 'px'; el.style.top = c[1] + 'px';
  fxLayer().appendChild(el);
  setTimeout(() => el.remove(), ms);
}
function fxShot(from, to, cls, done) {
  const a = unitCenter(from), b = unitCenter(to);
  if (!a || !b) { done?.(); return; }
  const el = document.createElement('div');
  el.className = 'fx shot ' + cls;
  el.style.left = a[0] + 'px'; el.style.top = a[1] + 'px';
  const ang = Math.atan2(b[1] - a[1], b[0] - a[0]) * 180 / Math.PI;
  fxLayer().appendChild(el);
  const ms = 260 / (S.settings.speed || 1);
  const anim = el.animate([{ transform: `translate(-50%, -50%) rotate(${ang}deg)` },
    { transform: `translate(calc(-50% + ${b[0] - a[0]}px), calc(-50% + ${b[1] - a[1]}px)) rotate(${ang}deg)` }], { duration: ms, easing: 'ease-in' });
  anim.onfinish = () => { el.remove(); done?.(); };
}
// A screen-wide flash of colour, for the biggest moments.
function fxScreen(cls, ms = 500) {
  const el = document.createElement('div');
  el.className = 'fx-screen ' + cls;
  fxLayer().appendChild(el);
  setTimeout(() => el.remove(), ms);
}
// A jagged bolt of lightning between two units, drawn as SVG in the effects layer.
function fxBolt(from, to, ms = 420) {
  const a = unitCenter(from), b = unitCenter(to);
  if (!a || !b) return;
  const pts = [a];
  for (let i = 1; i < 7; i++) {
    const t = i / 7;
    pts.push([a[0] + (b[0] - a[0]) * t + (Math.random() - 0.5) * 36, a[1] + (b[1] - a[1]) * t + (Math.random() - 0.5) * 36]);
  }
  pts.push(b);
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'fx-svg');
  for (const [w, c] of [[9, 'rgba(150, 200, 255, 0.35)'], [3, '#e9f4ff']]) {
    const pl = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    pl.setAttribute('points', pts.map(p => p.join(',')).join(' '));
    pl.setAttribute('stroke', c); pl.setAttribute('stroke-width', w); pl.setAttribute('fill', 'none'); pl.setAttribute('stroke-linejoin', 'bevel');
    svg.appendChild(pl);
  }
  fxLayer().appendChild(svg);
  setTimeout(() => svg.remove(), ms);
}
// Signature effects for the skills that deserve a show. Each gets the targets and whether it missed,
// and returns the kind of animation for the hero (melee lunges); anything not listed uses the
// generic effect for its kind.
const SIGNATURE = {
  fireball: (f, t, miss, later) => { fxShot('h' + f.h, t[0] || 'h' + f.h, 'fireorb', () => { if (!miss) { fxScreen('fire'); t.forEach(u => fxAt(u, 'fireburst', 800)); flash('stage', 'shake', 380); } }); return 'spell'; },
  earthshaker: (f, t, miss, later) => { later(() => { if (!miss) { flash('stage', 'quake', 600); fxScreen('dust', 600); t.forEach((u, i) => later(() => fxAt(u, 'quake', 700), i * 70)); } }, 160); return 'melee'; },
  cleave: (f, t, miss, later) => { later(() => t.forEach(u => fxAt(u, 'arc' + (miss ? ' miss' : ''), 500)), 140); return 'melee'; },
  reckless_swing: (f, t, miss, later) => { later(() => { t.forEach(u => fxAt(u, 'bigslash' + (miss ? ' miss' : ''), 520)); if (!miss) flash('stage', 'shake', 380); }, 180); return 'melee'; },
  lunge: (f, t, miss, later) => { later(() => t.forEach(u => { fxAt(u, 'thrust' + (miss ? ' miss' : ''), 420); if (!miss) later(() => fxAt(u, 'star', 520), 120); }), 120); return 'melee'; },
  finisher: (f, t, miss, later) => { [0, 110, 220].forEach(ms => later(() => t.forEach(u => fxAt(u, 'slash', 420)), ms + 120)); if (!miss) later(() => fxScreen('white', 240), 360); return 'melee'; },
  chain_lightning: (f, t, miss, later) => { t.forEach(u => fxBolt('h' + f.h, u)); if (!miss) { later(() => fxScreen('bolt', 200), 40); t.forEach(u => fxAt(u, 'zap', 500)); } return 'spell'; },
  storm_bolt: (f, t, miss) => { t.forEach(u => fxBolt('h' + f.h, u)); if (!miss) t.forEach(u => fxAt(u, 'zap', 500)); return 'spell'; },
  frost_lance: (f, t, miss) => { t.forEach(u => fxShot('h' + f.h, u, 'ice', () => fxAt(u, 'iceburst' + (miss ? ' miss' : ''), 700))); return 'spell'; },
  doom: (f, t) => { t.forEach(u => fxAt(u, 'sigil', 1200)); return 'spell'; },
  smite: (f, t, miss) => { t.forEach(u => fxAt(u, 'beam' + (miss ? ' miss' : ''), 700)); return 'spell'; },
  volley: (f, t, miss, later) => { t.forEach((u, i) => [0, 90, 180].forEach(ms => later(() => fxAt(u, 'rain', 520), ms + i * 40))); return 'ranged'; },
  aimed_shot: (f, t, miss, later) => { t.forEach(u => { fxAt(u, 'crosshair', 520); later(() => fxShot('h' + f.h, u, 'ranged', () => fxAt(u, 'pierce' + (miss ? ' miss' : ''), 520)), 300); }); return 'ranged'; },
  called_shot: (f, t, miss, later) => SIGNATURE.aimed_shot(f, t, miss, later),
  toxic_cloud: (f, t, miss) => { if (!miss) t.forEach(u => fxAt(u, 'cloud', 1100)); return 'buff'; },
  taunt: (f, t) => { fxAt('h' + f.h, 'shout', 800); return 'armor'; },
  guard: (f, t) => { t.forEach(u => fxShot('h' + f.h, u, 'shieldorb', () => fxAt(u, 'shieldfx', 700))); fxAt('h' + f.h, 'shieldfx', 700); return 'armor'; },
  renew: (f, t) => { t.forEach((u, i) => setTimeout(() => fxAt(u, 'healglow big', 1000), i * 90)); fxScreen('green', 400); return 'heal'; },
  regrowth: (f, t) => SIGNATURE.renew(f, t),
  panacea: (f, t) => SIGNATURE.renew(f, t),
  sanctuary: (f, t) => { t.forEach(u => fxAt(u, 'dome', 900)); fxScreen('gold', 300); return 'armor'; },
  rally_wall: (f, t) => { t.forEach(u => fxAt(u, 'dome', 900)); return 'armor'; },
  briar_wall: (f, t) => { t.forEach(u => fxAt(u, 'dome thorny', 900)); return 'armor'; },
  hymn_of_valor: (f, t) => { (f.heroes || t).forEach(u => fxAt(u, 'notes', 1100)); fxScreen('gold', 300); return 'buff'; },
  crescendo: (f, t) => { t.forEach(u => fxAt(u, 'notes', 1100)); return 'buff'; },
  call_bear: (f, t) => { fxAt('h' + f.h, 'circle', 1000); return 'buff'; },
  ancient_guardian: (f, t) => { fxAt('h' + f.h, 'circle big', 1200); fxScreen('green', 400); return 'buff'; },
  swarm: (f, t) => { fxAt('h' + f.h, 'circle', 900); return 'buff'; },
};
function abilityFx(f, ad, d) {
  if (!ad || !S.settings.speed) return null;
  const kind = abilityKind(ad);
  const from = 'h' + f.h, miss = f.hit === false;
  const tgts = abilityTargets(f, ad, d);
  const sig = SIGNATURE[f.a];
  if (sig) return sig({ ...f, heroes: (d.heroes || []).filter(x => !d.hs[x]?.down).map(x => 'h' + x) }, tgts, miss, (fn, ms) => setTimeout(fn, ms / (S.settings.speed || 1)));
  const land = (cls, ms) => tgts.forEach(t => fxAt(t, cls + (miss ? ' miss' : ''), ms));
  const later = (fn, ms) => setTimeout(fn, ms / (S.settings.speed || 1));
  if (kind === 'melee') later(() => land('slash', 420), 150);
  else if (kind === 'ranged' || kind === 'spell' || kind === 'bomb') {
    tgts.forEach(t => fxShot(from, t, kind, () => fxAt(t, (kind === 'ranged' ? 'pierce' : 'burst ' + kind) + (miss ? ' miss' : ''), 520)));
  } else if (kind === 'heal') {
    tgts.forEach(t => t === from ? fxAt(t, 'healglow', 900) : fxShot(from, t, 'heal', () => fxAt(t, 'healglow', 900)));
  } else if (kind === 'armor') land('shieldfx', 700);
  else land('sparkfx', 600);
  return kind;
}
// A line over the stage saying what an ally just did, for a couple of seconds.
// The caption for an ally's action: whose (the player and hero), what, at whom, and what it does.
// `rolling`: set as its dice roll, before the hit is known. It clears when the next action starts,
// or after a few seconds of nothing else.
function makeCaption(f, ad, d, rolling) {
  const tgt = typeof f.tgt === 'string' && f.tgt !== 'h' + f.h ? unitName(d, f.tgt) : '';
  const id = (C.caption?.id || 0) + 1;
  setTimeout(() => { if (C.caption?.id === id) { C.caption = null; render(); } }, 2600);
  return { h: f.h, id,
    text: `${heroWho(f.h)}: ${ad.name}${f.echo ? ' (echo)' : ''}${tgt ? ' → ' + tgt : ''}${!rolling && f.hit === false ? ' (missed)' : ''}`,
    what: (ad.short && ad.short[1]) || ad.text };
}
// A hero as the table knows them: "Alice · Vanguard" when someone else plays it, else the hero's name.
export function heroWho(x) {
  const hero = S.game.heroes[x];
  if (mine().includes(x)) return hero.name;
  const who = controllerName(x);
  return who && who !== '—' ? `${who} · ${hero.name}` : hero.name;
}
// A die's biggest number, for a compact label (d6, d12).
const topOf = d => Math.max(...d.faces.map(x => (typeof x === 'number' ? x : parseInt(String(x).slice(1)) || 0)));
// The line under the stage while a round plays back: who's acting now, and who's next.
function playingLine() {
  const now = C.tray?.foe || (C.tray?.h != null ? heroWho(C.tray.h) : null);
  const next = nextActor();
  if (now && next && next !== now) return `${now} is acting · next: ${next}`;
  if (now) return `${now} is acting`;
  return next ? `Next: ${next}` : 'Resolving…';
}
// Who acts next while enemies and summons take their turns, for the line under the stage.
function nextActor() {
  if (!C.fx) return null;
  const d = C.display;
  for (let i = C.fxAt + 1; i < C.fx.length; i++) {
    const f = C.fx[i];
    if (f.k === 'froll' || f.k === 'fact') return d?.foes.find(fo => fo.id === f.f)?.name || null;
    if (f.k === 'sact') return (d?.allies || []).find(a => a.id === f.s)?.name || null;
    if (f.k === 'act' || f.k === 'roll') return heroWho(f.h);
  }
  return null;
}

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
    case 'round': {
      // a new round opens with its number in the roll tray
      if (f.n <= 1) return 0;
      C.tray = { round: f.n, t: performance.now() };
      C.caption = null;
      return 700;
    }
    case 'roll': {
      C.tray = null;
      if (!f.dice.length) return 0;
      // the action these dice are for comes next
      const act = C.fx.slice(C.fxAt).find(x => x.k === 'act' && x.h === f.h && !x.instant);
      const now = performance.now();
      C.tray = { h: f.h, a: act?.a, t: now, dice: f.dice.map(x => ({ ...x, t: now })) };
      // the caption names the action now playing, from its first roll (never the one before it)
      C.caption = act && !mine().includes(f.h) && S.static.actions[act.a] ? makeCaption(act, S.static.actions[act.a], d, true) : null;
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
      const ad = S.static.actions[f.a];
      // an ally's action is spelled out over the stage: who, what, at whom, and what it does
      if (!mine().includes(f.h) && ad && !f.echo) C.caption = makeCaption(f, ad, d, false);
      else if (mine().includes(f.h)) C.caption = null;
      if (f.instant) return 0;
      const kind = abilityFx(f, ad, d);
      flash('h' + f.h, kind === 'melee' ? 'melee' : 'act', 360);
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
      return 480;
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
      C.caption = null;
      C.tray = { fid: f.f, foe: fo?.name || 'Enemy', name: f.name, range: f.lo != null ? `${f.lo}–${f.hi}` : '', t: now, verdict, label, total,
        bonus: f.bonus || 0, vt: now + 420 / (S.settings.speed || 1), dice: dice.map((x, j) => ({ ...x, id: 'f' + f.f + '.' + j, t: now })) };
      flash('f' + f.f, 'act');
      sfx.play('dice');
      setTimeout(render, 440 / (S.settings.speed || 1));
      return 760;
    }
    case 'fact': {
      if (C.tray?.fid !== f.f) C.tray = null;
      C.caption = null;
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
      const name = S.static.combos?.[f.c]?.name || { bell: 'Bell cracked' }[f.c] || f.c;
      addFloat(f.to, `${name}! +${f.n}`, 'combo');
      sfx.play('rare');
      return 420;
    }
    case 'st': {
      const name = STATUS[f.s]?.name || { guarded: 'Guarded', taunt: 'Taunt', stunned: 'Stunned', cleansed: 'Cleansed', unbreakable: 'Unbreakable!', sanct: 'Sanctuary', might: 'Might', weakened: 'Weakened', distracted: 'Distracted', dazed: 'Dazed', dodged: 'Dodged!', inspired: 'Inspired', hymn: 'Hymn', rerolls: '+2 rerolls', thorns: 'Thorns!', enraged: 'Enraged!', explodes: 'Bursts!', bloodied: 'Bloodied!', rallies: 'Rallies!', undertow: 'Undertow next', dragged: 'Dragged under!', scattered: 'Light scattered!', unwarded: 'Ward broken!',
        robbed: 'Die stolen!', locked: 'Die crusted over!', static: 'Static shock!', snatched: 'Snatched!', merged: 'Merged!', splits: 'Splits!', shrugs: 'Shrugs it off', doused: 'Lamp out!', swallowed: 'Swallowed!', 'spat out': 'Spat out!', 'out of reach': 'Out of reach!', spite: 'Spite +1', steeled: 'Steeled: resists!', flees: 'Flees!', recovered: 'Got it back!', flipped: 'Flipped!', split: 'Split!', grafted: 'Grafted!', second_opinion: 'Second opinion', triage: 'Triage', tempo: 'Tempo!', bloodlust: 'Bloodlust! +d6', rampage: 'Rampage! Ready again', shielded: 'Shared Burden!', hexed: 'Hexed!', grows: 'Its die grows!', charged: 'Charged!', arced: 'Arced!', robbed: 'Robbed!', resisted: 'Resisted', burn: 'Burn', freeze: 'Frozen', poison: 'Poison' }[f.s] || f.s;
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
    case 'sact': C.tray = null; C.caption = null; flash('s' + f.s, 'act'); sfx.play('swing'); return 300;
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
      bigBanner(f.n === 2 ? 'The tide turns' : 'The Crown stands alone', (f.n === 2 ? 'Each round the Undertow drags someone under: Armor or a Guard stops it' : 'Exposed: it takes 50% more, but every attack rolls an extra die') + '. Next round: the Deluge', 'danger', 2600);
      flash('stage', 'shake', 500);
      sfx.play('phase');
      return 1400;
    }
    default: return 120;
  }
}
