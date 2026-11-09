// The fight overlay: the party and the enemies (in their rows), enemy intents, the round so far, and your dice
// tray and actions. When a round resolves, the server's effects are played back one at a time on
// a copy of the fight as it was, then the new state is shown.
import { S, send, mine, controllerName } from './store.js?v=187';
import { h, icon, toast, hideTip, bigBanner } from './ui.js?v=187';
import { spriteURL, poseURL, warmPoses } from './art.js?v=187';
import { stageURL, stageKey } from './stage.js?v=187';
import { reqText, STATUS, dieLabel, dieTip, hitChance, countOk, expected, isRisky, faceText, foeTraits, fateFaces, fateText } from './rules.js?v=187';
import { render } from './main.js?v=187';
import { skillCard, upDef, upText } from './hud.js?v=187';
import { SKILL_FX, CLASS_LOOK, foeFx } from './skillfx.js?v=187';
import * as sfx from './audio.js?v=187';

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

// Leaves drifting down over an ambush-ground fight (each keeps its phase across redraws).
function leaves() {
  const now = performance.now();
  return h('div.leaves', { 'aria-hidden': 'true' }, ...[0, 1, 2, 3, 4, 5, 6].map(i => {
    const ms = 5200 + i * 700;
    return h('i', { style: { '--i': i, left: `${6 + i * 13 + (i % 2) * 4}%`, animationDuration: ms + 'ms', animationDelay: `-${Math.round((now + i * 1900) % ms)}ms` } });
  }));
}
// The battleground's rule, as a chip in the fight's header (Game.ground_of, A.GROUNDS).
function groundChip(f) {
  const G = S.static.grounds?.[f.ground.k];
  if (!G) return null;
  const good = f.ground.side === 'heroes';
  const who = f.ground.k === 'high' ? (good ? 'You hold the slope' : 'They hold the slope') : (good ? 'They’re caught in the trees' : 'You’re caught in the trees');
  return h('span.chip.ground' + (good ? '.good' : '.bad'), { tip: `${G.name} (${G.terrain})\n${G.text}` }, icon(f.ground.k === 'high' ? 'shield' : 'down'), `${G.name}: ${who}`);
}
function fightTitle(f) {
  const st = S.static;
  if (f.kind === 'boss') return S.game.final_name || 'The Drowned Crown';
  if (f.kind === 'dungeon') return `${st.dungeons[f.region]} · fight ${f.step + 1} of 3`;
  if (f.raid === 'free') return `Freeing ${S.game.places[f.tile]?.name || 'the town'}`;
  if (f.raid === 'stop') return 'Raiders on the road';
  if (f.kind === 'lair') return 'Lair';
  if (f.kind === 'event') return 'Trouble';
  if (S.world?.elev?.[f.tile] <= 1) return 'At sea';
  return 'Skirmish';
}

// What a crit is, for every crit line's tooltip.
export const CRIT_TIP = 'Crit\nWhen a die lands on its top face (a 6 on a d6, an 8 on a d8, or a wild face), the action also does its crit. A d10 or bigger crits on its top two faces.';
// Whether a rolled die crits: on its top face (a d10 or bigger: its top two) or pushed past it.
// Shields and skulls never do. The same rule as crits.py's crit_floor.
function critDie(v, tag, faces) {
  if (!faces || v == null || tag === 'S' || tag === 'X') return false;
  if (tag === 'W') return true;
  const nums = [...new Set(faces.filter(f => typeof f === 'number' || /^[FIP]\d/.test(String(f))).map(f => (typeof f === 'number' ? f : parseInt(String(f).slice(1)))))].sort((a, b) => b - a);
  if (!nums.length) return false;
  return v >= (faces.length >= 10 && nums.length > 1 ? nums[1] : nums[0]);
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
    if (!hs?.down) cl.push(...statusCls(st));
    if (hs?.attune && !hs.down) cl.push('att-' + hs.attune, ...(hs.converge ? ['att-converge'] : []));
    if (C.anim['h' + x]) cl.push(C.anim['h' + x]);
    if (x === active) cl.push('mine-sel');
    if (isTarget('h' + x, f)) cl.push('target');
    const ready = hs?.ready && !C.playing;
    return h('div.' + cl.join('.'), { 'data-uid': 'h' + x, style: { '--seat': `var(--hero-${x})` }, tip: mine().includes(x) ? null : heroTip(x, hs) },
      h('div.intent' + (ready ? '' : '.none'), { style: { '--c': 'var(--ok)' } }, icon('check'), 'Ready'),
      poseImg(hero.cls, 'h' + x, hs?.down, st, hs),
      // another player's hero: who plays it (by the name), and the dice they hold this round (for combos)
      h('div.uname', { style: { color: `var(--hero-${x})` } }, hero.name, mine().includes(x) ? null : h('span.ctl-name', null, ` · ${controllerName(x)}`),
        f.taunt === x ? ' · taunting' : '', Object.values(f.guard || {}).includes(x) ? ' · guarding' : ''),
      !mine().includes(x) && hs?.dice?.length ? h('div.ally-dice', { tip: `${hero.name}'s dice this round\nFaded ones are spent; a number shows once it's rolled.` },
        ...hs.dice.map(dd => allyDie(x, dd))) : null,
      hs?.swallowed ? h('div.covered-chip.undertow', { tip: 'Swallowed: no dice, and you take damage each round until the Reef Maw spits you out.' }, 'Swallowed!') : null,
      hs?.static ? h('div.covered-chip.undertow', { tip: 'Static: any of your dice that rolls 1 or 2 shocks you for 3 this round.' }, 'Static: 1–2 shocks you') : null,
      hs?.st?.undertow ? h('div.covered-chip.undertow', { tip: `${S.game.final_drag || 'Undertow'}\nThe final boss’s blow lands on you at the end of the round for this much. Armor blocks it; an ally’s Guard takes it for you.` }, `${S.game.final_drag || 'Undertow'}: ${hs.st.undertow} at round end`) : null,
      hs?.st?.infuse ? infusedChip(hs) : null,
      hs && hs.heat != null ? heatGauge(hs) : null,
      hs && hs.impact != null ? impactGauge(hs, hero) : null,
      hs?.hawk ? hawkChip(f, hs) : null,
      hero.cls === 'dragonborn' ? scalePips(hero.scales || 0) : null,
      hs && hs.ammo != null ? ammoPips(hs) : null,
      hs && hs.sheathed != null ? resolveGauge(hs) : null,
      hero.cls === 'mender' && hs ? graceBar(hs.grace || 0, hs.radiant) : null,
      hs?.attune ? attuneChip(hs) : null,
      hs?.berserk ? h('div.covered-chip.berserk', { tip: 'Berserk\nYou lost a third of your HP this fight: every die explodes and your hits deal +2, but you can’t use defensive actions.' }, 'Berserk!') : null,
      hs?.combo && f.foes.find(o => o.id === hs.combo.id && o.hp > 0) ? h('div.covered-chip', { tip: `Combo\nEach hit on ${f.foes.find(o => o.id === hs.combo.id).name} this round deals +1 per hit before it. Hitting another enemy starts over.` },
        `Combo ×${hs.combo.n} on ${f.foes.find(o => o.id === hs.combo.id).name}`) : null,
      hpBar(hpOf(x), max, false, 'h' + x),
      previewRow('h' + x, prev),
      statusRow(st, hs?.down ? ['Knocked down'] : []),
      floats('h' + x));
  };
  const unitFoe = fo => {
    const d = S.static.foes[fo.k];
    const cl = ['unit', 'foe'];
    if (d.boss || d.big) cl.push('boss');
    if (fo.hp <= 0 && !fo.dying) cl.push('dead', 'gone');
    else cl.push(...statusCls(fo.st));
    if (C.anim['f' + fo.id]) cl.push(C.anim['f' + fo.id]);
    if (isTarget('f' + fo.id, f)) cl.push('target');
    if (fo.hp > 0 && f.chord && f.chord.seq === f.seq && f.chord.t === 'f' + fo.id) cl.push('chorded');
    if (fo.hp > 0 && fo.reacted !== f.round && REACT_ELS.some(s => fo.st?.[s] && fo.st_by?.[s] != null)) cl.push('reactable');
    return h('div.' + cl.join('.'), { 'data-uid': 'f' + fo.id, tip: foeTip(fo) },
      intentChip(fo, f),
      poseImg(fo.k, 'f' + fo.id, false, fo.st),
      h('div.uname', null, fo.name),
      fo.aff || d.big || fo.bl ? h('div.foe-tags', null,
        fo.aff ? h('span.foe-tag', { tip: `${S.static.elites[fo.aff].name}\n${S.static.elites[fo.aff].text}` }, 'Elite') : null,
        d.big && !fo.bl ? h('span.foe-tag', { tip: `Big threat\nAt half health it's bloodied: ${d.bloodied?.text || ''}` }, 'Big') : null,
        fo.bl ? h('span.foe-tag.bloodied', { tip: `Bloodied\n${d.bloodied?.text || ''}` }, 'Bloodied') : null) : null,
      hpBar(Math.max(0, fo.hp), fo.max, true, 'f' + fo.id),
      previewRow('f' + fo.id, prev, fo.hp),
      statusRow(fo.st, [...(fo.res ? [`${{ fire: '🔥', acid: '🧪', frost: '❄' }[fo.res] || ''} ${fo.res} residue`] : []), ...(fo.might ? [`+${fo.might} might`] : []), ...(fo.st.warded ? ['Warded: ½ damage'] : []), ...(fo.st.exposed ? ['Exposed: +50%'] : [])], traitChips(d), fo),
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
      poseImg(a.k, 's' + a.id, false),
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

  // two or more in a column (and the party, always): compact cards; three or more enemies: packed, each
  // card one row with its intent beside it, so the column fits a laptop screen (ui.css .col.packed)
  const col = (label, units, party) => h('div.col' + (party ? '.herocol' : '') + (units.length >= 2 || party ? '.crowd' : '')
    + (!party && units.length >= 3 ? '.packed' : '') + (!units.length ? '.empty' : ''), null, h('span.lbl', null, label), ...units);
  const stage = h('div.stage' + (C.anim.stage ? '.' + C.anim.stage : ''), { style: { '--stage-art': `url(${stageURL(stageKey(f, S.world), f.ground)})` } },
    f.ground?.k === 'woods' ? leaves() : null,
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
      f.ground ? groundChip(f) : null,
      f.harm ? harmonyChips(f.harm) : null,
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
    else if (d.fc) parts.push(d.fc.map(x => (x[0] == null ? 'W' : fateText(x))).join('|'));
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
  drawVines(stage, sr, svg, f);
  stage.prepend(svg);
}
// The Warden's Rootweb: green vines between the Entwined (Rooted) enemies while a Warden fights.
function drawVines(stage, sr, svg, f) {
  if (!f.heroes.some(y => heroActive(f, y) && S.game.heroes[y].cls === 'warden')) return;
  const pts = f.foes.filter(fo => fo.hp > 0 && fo.st.root).map(fo => stage.querySelector(`[data-uid="f${fo.id}"] img`)).filter(Boolean).map(el => {
    const r = el.getBoundingClientRect();
    return [r.left - sr.left + r.width / 2, r.bottom - sr.top - r.height * 0.12];
  });
  for (let i = 0; i + 1 < pts.length; i++) {
    const [x0, y0] = pts[i], [x1, y1] = pts[i + 1];
    const mx = (x0 + x1) / 2, my = Math.max(y0, y1) + 26;
    for (const [cls, dy] of [['vine', 0], ['vine thin', -8]]) {
      const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      path.setAttribute('d', `M${x0},${y0} Q${mx},${my + dy} ${x1},${y1}`);
      path.setAttribute('class', cls);
      svg.append(path);
    }
  }
}

// Chord: the numbers hero x's next action needs to show to copy an ally's hit on this enemy (null
// when there's no chord on it for them: it has to be the very next action, by another hero).
export function chordNums(fo, f, x) {
  const ch = f.chord;
  if (!ch || ch.seq !== f.seq || ch.t !== 'f' + fo.id || ch.hs.includes(x)) return null;
  return ch.vals;
}
// The elemental reactions: two statuses from two heroes meet on one enemy (combos.py REACTIONS).
const REACTS = { 'burn+shock': 'overload', 'burn+freeze': 'thermal', 'burn+poison': 'blightfire', 'freeze+shock': 'fracture',
  'poison+shock': 'conduction', 'freeze+root': 'frostlock', 'burn+root': 'kindling' };
const REACT_ELS = ['burn', 'freeze', 'shock', 'poison', 'root'];
const reactOf = (a, b) => REACTS[[a, b].sort().join('+')];
// "4", "4 or 6", "2, 4 or 6"
const orList = xs => xs.length > 1 ? `${xs.slice(0, -1).join(', ')} or ${xs[xs.length - 1]}` : String(xs[0]);
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
  if (fo.st?.root && f.heroes.some(y => heroActive(f, y) && S.game.heroes[y].cls === 'warden')) {
    const n = f.foes.filter(o => o.hp > 0 && o.st?.root && o !== fo).length;
    chips.push(h('span.combo-hint', { tip: 'Entwined (the Warden’s Rootweb)\nEvery hit on it sends 2 damage along the vines to each other Entwined (Rooted) enemy. With no other, it takes 1 more from each hit instead.' }, n ? `Entwined: hits splash ${n === 1 ? 'the other' : 'all ' + n}` : 'Entwined: hits +1'));
  }
  if (fo.air) chips.push(h('span.st.bad', { tip: 'Airborne: melee attacks can’t reach it. Use ranged attacks and spells.' }, 'Airborne: no melee'));
  if (fo.loot) chips.push(h('span.st.bad', { tip: 'It has your potion. Kill it before it flies off to get it back.' }, `Has ${S.static.items[fo.loot]?.name || 'loot'} · flees in ${fo.flee_in}`));
  if (fo.merged) chips.push(h('span.st', { tip: 'Merged: every attack rolls an extra die for each merge.' }, `Merged ×${fo.merged + 1}`));
  if (fo.gut) chips.push(h('span.st.bad', { tip: 'A hero is inside. Deal this much more damage to it and it spits them out.' }, `Spits out in ${fo.gut} dmg`));
  return chips.length ? h('div.combo-hints', null, ...chips) : null;
}
function comboHints(fo, f) {
  const x = C.tab, hs = f.hs[x];
  // only for a hero who could still answer it: in the fight, not readied, with a die to play
  if (x == null || !f.heroes.includes(x) || !hs || hs.ready || !(hs.dice || []).some(d => !d.used && !d.locked)) return null;
  const chips = [];
  const nums = chordNums(fo, f, x);
  if (nums) {
    const n = f.chord.bonus?.[x] ?? Math.min(f.chord.base, 15) * f.chord.hs.length;
    const who = f.chord.hs.map(y => S.game.heroes[y].name).join(' and ');
    chips.push(h('span.combo-hint.chord', { tip: `Chord\n${who} just hit it. Make your next action a hit on it with a die showing ${orList(nums)}, before anyone else acts, and it copies that hit: +${n}.` },
      `Chord: a ${orList(nums)} now, +${n}`));
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
// Which pose a fighter's sprite shows (art.js poseURL), from the motion it's playing: leaning into
// a swing, leaning back to cast or brace, knocked back by a hit, lying down when out.
const POSE_OF = { act: 'attack', melee: 'attack', charge: 'attack', spin: 'attack', 'f-lunge': 'attack', 'f-pounce': 'attack', 'f-slam': 'attack', 'f-charge': 'attack',
  cast: 'cast', brace: 'cast', retreat: 'cast', 'f-cast': 'cast', 'f-brace': 'cast', healbig: 'cast', revive: 'cast', victory: 'cast',
  hit: 'hurt', bighit: 'hurt', stunned: 'hurt', kill: 'fallen' };
function poseImg(k, uid, out, st, hs) {
  warmPoses(k);
  const pose = out ? 'fallen' : POSE_OF[C.anim[uid]] || null;
  return h('span.fig', null, h('img.pix' + (pose ? '.pose-' + pose : ''), { src: poseURL(k, pose), alt: '' }),
    out ? null : attuneAura(hs), out ? null : statusAura(st), out ? null : hawkPerch(uid));
}
// The Ranger's hawk over whoever it's with: gold while it hunts an enemy, sky blue while it watches a hero.
function hawkPerch(uid) {
  const f = S.game?.fight;
  if (!f || !f.heroes.some(y => f.hs[y]?.hawk === uid)) return null;
  return h('span.aura.hawk-perch.' + (uid[0] === 'f' ? 'hunt' : 'watch'), { 'aria-hidden': 'true' },
    h('i', { style: { animationDelay: `-${Math.round(performance.now() % 1800)}ms` } }));
}
// The Arcanist's attunement on the sprite itself: flames lick up from it (Fire), snowflakes circle it
// (Frost) or arcs crackle round it (Storm), with a glow in that colour; ready to Converge, a ring of all
// three turns behind it. Phases are kept across redraws, as for statusAura.
const ATT = { fire: ['flame', 5, 1300], frost: ['flake', 4, 3600], storm: ['arc', 3, 900] };
function attuneAura(hs) {
  if (!hs?.attune || !ATT[hs.attune]) return null;
  const [cls, n, ms] = ATT[hs.attune], now = performance.now();
  return h('span.aura.attune', { 'aria-hidden': 'true' },
    hs.converge ? h('i.prism', { style: { animationDelay: `-${Math.round(now % 2400)}ms` } }) : null,
    ...Array.from({ length: n }, (_, i) => h('i.' + cls, { style: { '--i': i, animationDelay: `-${Math.round((now + i * ms / n) % ms)}ms` } })));
}
// What a fighter's statuses look like on the fighter itself, over the sprite: Poison drips, Burn
// throws up embers, Shock sparks, Mark is a crosshair, a Stun circles stars, Root grows vines at the
// feet, Freeze frosts the sprite over, Weak sags it. Each loop keeps its phase across redraws (the
// stage is rebuilt many times a second), so nothing restarts.
const AURA = {
  poison: ['drip', 3, 1400], burn: ['ember', 4, 1200], shock: ['spark', 3, 700], mark: ['cross', 1, 4000],
  stun: ['star', 3, 1600], root: ['vine', 3, 2600], freeze: ['frost', 3, 3000], vuln: ['crack', 1, 1800], hex: ['hexmote', 2, 2200],
};
function statusAura(st) {
  const on = Object.keys(AURA).filter(k => st?.[k]);
  if (!on.length) return null;
  const now = performance.now();
  return h('span.aura', { 'aria-hidden': 'true' }, ...on.flatMap(k => {
    const [cls, n, ms] = AURA[k];
    return Array.from({ length: n }, (_, i) => h('i.' + cls, { style: { '--i': i, animationDelay: `-${Math.round((now + i * ms / n) % ms)}ms` } }));
  }));
}
// classes on a fighter for statuses that change the sprite itself (Freeze tints it, Weak sags it)
function statusCls(st) { return ['freeze', 'weak', 'stun'].filter(k => st?.[k]).map(k => 'st-' + k); }

// A health bar; just after a hit, a pale trail shows what was lost and drains down to the new value.
function hpBar(hp, max, foe = false, uid = null) {
  const pct = Math.max(0, Math.round(100 * hp / max));
  const lag = uid && C.lag?.[uid], now = performance.now();
  const trail = lag && now - lag.t < LAG_MS && lag.from > pct
    ? h('b.lag', { style: { '--from': lag.from + '%', '--to': pct + '%', animationDelay: `-${Math.round(now - lag.t)}ms` } }) : null;
  return h('div.bar' + hpClass(hp, max, foe), null, trail, h('i', { style: { width: pct + '%' } }), h('span', null, `${Math.max(0, hp)} / ${max}`));
}
const LAG_MS = 950;
function noteLag(uid, hp, max) {
  const now = performance.now(), old = (C.lag ||= {})[uid];
  const from = old && now - old.t < LAG_MS ? old.from : Math.max(0, Math.round(100 * hp / max));
  C.lag[uid] = { from, t: now };
  setTimeout(render, LAG_MS + 20);
}

// The Herald's Harmonies over the fight: three bars the whole party plays around.
const HARM = { valor: ['Valor', 'every ally hit deals +1 per level'], aegis: ['Aegis', 'each ally starts the round with 1 Armor per level'],
  discord: ['Dissonance', 'every enemy hit on the party deals 1 less per level'] };
function harmonyChips(harm) {
  return h('span.harmonies', null, ...Object.entries(HARM).map(([k, [name, does]]) => h('span.chip.harm.' + k, {
    tip: `${name} ${harm[k] || 0}\n${does[0].toUpperCase() + does.slice(1)}. The Herald's songs raise it; every Harmony falls by 1 at the end of the round.` },
  name, h('span.pips', null, ...[0, 1, 2].map(i => h('i' + (i < (harm[k] || 0) ? '.on' : '')))), harm[k] > 3 ? '+' : null)));
}
// The Arcanist's Attunement and Flux: its element (and what its spells add), and Flux toward a Convergence.
const ELEMENTS = { fire: ['🔥', 'Fire', 'Burn 1'], frost: ['❄', 'Frost', 'its attack −2'], storm: ['⚡', 'Storm', 'arcs for 2'] };
function attuneChip(hs) {
  const [ic, name, does] = ELEMENTS[hs.attune] || ELEMENTS.fire, flux = hs.flux || 0;
  return h('div.covered-chip.attune.' + hs.attune, { tip: `Attuned to ${name}\nYour damaging spells also: ${does}. A spell of another element moves your attunement and gives 1 Flux; at 3 Flux your next spell Converges: +50%, and all three elements.` },
    `${ic} ${name}`, h('span.flux', null, hs.converge ? ' · Converge!' : ' · ' + '●'.repeat(flux) + '○'.repeat(Math.max(0, 3 - flux))));
}
// The Mender's Grace: healing fills it; at 25 the next heal is Radiance (the whole party, cleansed).
function graceBar(n, ready) {
  return meter('grace', n / 25, ready, ready ? 'Radiance ready' : `Grace ${n} / 25`,
    `Grace ${n} / 25\nHealing you do fills it. At 25, your next heal is Radiance: it lands on the whole party and cleanses them.`);
}
// A class's gauge on its hero card (Heat, Grace, Impact): a bar that fills to its cap, glowing when hot.
function meter(kind, frac, hot, label, tip) {
  return h('div.heat-gauge' + (kind ? '.' + kind : '') + (hot ? '.hot' : ''), { tip },
    h('i', { style: { width: Math.max(0, Math.min(100, frac * 100)) + '%' } }), h('span', null, label));
}
// The Dragonborn's Scales: up to 5, 1 Armor each at the start of every round, kept between fights.
export function scalePips(n) {
  return h('div.scale-pips', { tip: `Scales ${n} / 5\nEvery enemy hit that lands grows one. Each gives 1 Armor at the start of every round. Breath sheds them for damage to every enemy. They stay between fights; knocked down loses half.` },
    ...[0, 1, 2, 3, 4].map(i => h('i' + (i < n ? '.on' : ''))), h('span', null, `Scales ${n}`));
}
// The Gunslinger's cylinder: a pip per round; the next one, if it's the Silver Round, shines.
function ammoPips(hs) {
  const n = hs.ammo, cap = hs.cap || 6, silver = n === 1 || (hs.lucky && n === cap - 2);
  return h('div.scale-pips.ammo' + (silver ? '.silver' : ''), { tip: `Rounds ${n} / ${cap}\nEach shot fires a round; you can't shoot with the cylinder empty (Reload, or Pistol Whip). The last round is the Silver Round: a single shot with it deals double.${hs.st?.cocked ? '\nHammer cocked: your next shot this round deals more.' : ''}` },
    ...Array.from({ length: cap }, (_, i) => h('i' + (i < n ? '.on' : '') + (i === n - 1 && silver ? '.ag' : ''))),
    h('span', null, n ? `${n} round${n === 1 ? '' : 's'}${silver ? ' · silver next' : ''}` : 'Empty: reload'));
}
// The Samurai's blade (Sheathed or Drawn) and its Resolve, which the Draw spends.
function resolveGauge(hs) {
  const n = hs.resolve || 0, cap = hs.rcap || 15;
  return meter('resolve', n / cap, hs.sheathed && n >= cap, `${hs.sheathed ? 'Sheathed' : 'Drawn'} · Resolve ${n}`,
    `${hs.sheathed ? 'Sheathed' : 'Drawn'} · Resolve ${n} / ${cap}\nWhile Sheathed, Resolve grows each round, the first enemy to hit you each round is cut for half of it, and your attacks are the Draw (the die + all your Resolve) and Scabbard Strike. Drawn, you Cut; Sheathe to start building again. Any other attack while Sheathed draws the blade and loses the Resolve.`);
}
// The Ranger's hawk: who it's with, and what that does.
function hawkChip(f, hs) {
  const u = hs.hawk, fo = u[0] === 'f' ? f.foes.find(o => 'f' + o.id === u) : null;
  const who = fo ? fo.name : S.game.heroes[+u.slice(1)]?.name;
  return h('div.covered-chip.hawk', { tip: fo ? `Your hawk is hunting ${who}\nYour hits on it deal +1, and the hawk pecks it for 2 after the party acts.` : `Your hawk is watching ${who}\nThe first enemy hit on them each round deals 3 less.` },
    fo ? `Hawk: hunting ${who}` : `Hawk: watching ${who}`);
}
// The Vanguard's Impact: damage its Armor soaks is stored (to 10, 20 with Immovable) for Payback.
function impactGauge(hs, hero) {
  const n = hs.impact, cap = (hero.skills || []).some(k => k.replace('+', '') === 'immovable') ? 20 : 10;
  return meter('impact', n / cap, n >= cap, `Impact ${n}${hs.imp2 ? ' · ×2' : ''}`,
    `Impact ${n} / ${cap}\nDamage your Armor blocks is stored as Impact (hits you take for allies with Guard and Taunt too). Payback deals the die plus all of it. It lasts the fight.${hs.imp2 ? '\nBraced: Impact gained this round is doubled.' : ''}`);
}
// The Emberknight's Heat: a gauge to 25 with its bonus (+1 per 5); at 25 it overheats.
function heatGauge(hs) {
  const n = hs.heat, bonus = Math.floor(n / 5) + (hs.white || 0);
  return meter(null, n / 25, n >= 20, hs.white ? `White heat · +${bonus}` : `Heat ${n} · +${bonus}`,
    `Heat ${n} / 25\nYour hits deal +1 per 5 Heat (+${bonus} now). Every die you play adds its number; at 25 you overheat (5 damage, back to 10). It cools by half at the end of the round.`);
}
// The Spellblade's infused blade: its next melee hits deal more and carry an element.
const ELEMENT = { frost: ['Frost', 'makes the enemy Weak'], shock: ['Shock', 'Shocks the enemy'], burn: ['Flame', 'Burns the enemy for 2'] };
// An ally's die on their card; with Mind Link, a hidden one can be revealed (1 Focus) and a shown one nudged.
function allyDie(x, dd) {
  const me = C.tab, f = S.game.fight, mh = f?.hs?.[me];
  const link = me != null && me !== x && (S.game.heroes[me]?.skills || []).includes('mind_link') && mh && !mh.ready && !dd.used;
  const free = link && (S.game.heroes[me].skills || []).includes('empathic_link');
  const label = dd.v != null ? String(dd.v) : `d${topOf(dd)}`;
  if (!link) return h('span.die-mini' + (dd.used ? '.used' : ''), { tip: `${dieLabel(dd)}\n${dieTip(dd)}` }, label);
  if (dd.v == null) {
    return h('button.die-mini.link', { disabled: !free && !mh.focus, tip: `Mind Link: ${free ? 'free' : '1 Focus'} to reveal this die`, onclick: () => send({ t: 'nudge', h: me, of: x, die: dd.id, by: 0 }) }, label);
  }
  return h('span.die-mini.linked', { tip: `${dieLabel(dd)}\nMind Link: 1 Focus nudges it` },
    h('button', { disabled: !mh.focus, onclick: () => send({ t: 'nudge', h: me, of: x, die: dd.id, by: -1 }) }, '−'), label,
    h('button', { disabled: !mh.focus, onclick: () => send({ t: 'nudge', h: me, of: x, die: dd.id, by: 1 }) }, '+'));
}
function infusedChip(hs) {
  const inf = hs.inf || {}, [name, does] = ELEMENT[inf.el] || ['Arcane', ''];
  const n = hs.st.infuse;
  return h('div.covered-chip.infused.' + (inf.el || 'arcane'), { tip: `Infused blade: ${name}\nYour next ${n === 1 ? 'melee hit deals' : n + ' melee hits deal'} +${inf.dmg || 0} and ${does}. It fades at the end of the round.` },
    `${name} blade: ${n} × +${inf.dmg || 0}`);
}
const ST_SHORT = { steeled: 'Steeled', vuln: 'Vuln', stun: 'Stunned', freeze: 'Frozen', root: 'Rooted', shock: 'Shocked', hex: 'Hexed', crescendo: 'Crescendo', lifeline: 'Lifeline' };
// `fo`: the enemy, for who put each status on it (a dot in their colour) and what it would react with.
function statusRow(st, extra = [], tail = [], fo = null) {
  const chips = [];
  const f = S.game.fight;
  for (const [k, v] of Object.entries(st || {})) {
    if (!v || ['doomt', 'warded', 'exposed', 'undertow', 'knell'].includes(k)) continue;
    const s = STATUS[k];
    if (!s) continue;
    const n = ['stun', 'freeze', 'shock', 'warded', 'exposed', 'steeled'].includes(k) ? '' : v;
    const by = fo?.st_by?.[k];
    const el = fo && REACT_ELS.includes(k) && by != null;
    const reacts = el && fo.reacted !== f?.round ? REACT_ELS.filter(o => o !== k && reactOf(k, o)) : [];
    const tip = `${s.name}${n !== '' ? ' ' + n : ''}${el ? ` (from ${S.game.heroes[by]?.name})` : ''}\n${s.text}`;
    // icon, short name and number, so a status reads at a glance ("Armor 3", "Rooted"); a dot in the
    // colour of the hero who put it on, and a glow when another hero's status would set it off
    chips.push(h('span.st.' + (k === 'armor' ? 'armor' : s.bad ? 'bad' : 'good') + '.' + k + (reacts.length ? '.reacts' : ''), { tip }, icon(s.icon),
      h('span.st-name', null, ST_SHORT[k] || s.name), n !== '' ? h('b', null, n) : null,
      el ? h('i.st-by', { style: { '--seat': `var(--hero-${by})` } }) : null));
  }
  for (const e of extra) chips.push(h('span.st', null, e));
  return h('div.sts', null, ...chips, ...tail);
}

// While a big die tumbles it flickers through a few of its own faces (blurred), then lands on the
// roll; a shield, skull or wild face flips in, and a crit lands with a thump.
const FLICK = { S: '◆', X: '☠', W: '★' };
function flickFaces(x) {
  const fs = (x.faces || [1, 2, 3, 4, 5, 6]).map(v => (typeof v === 'number' ? String(v) : FLICK[v] || v.replace(/^[FIP]/, '')));
  const seed = String(x.id ?? '').split('').reduce((a, c) => a + c.charCodeAt(0), 0) + (x.v || 0);
  return [0, 1, 2, 3].map(k => fs[(seed * 7 + k * 5) % fs.length]);
}
function bigDie(x, cls, face, since, extra) {
  const special = ['S', 'X', 'W'].includes(x.tag) ? '.special.f' + x.tag : ['F', 'I', 'P', 'burn', 'freeze', 'poison'].includes(x.tag) ? '.special.fel' : '';
  return h('div.big-die' + cls + (x.re ? '.re' : '') + (x.crit ? '.crit' : '') + special, { style: since(x.t) },
    h('i.flick', { style: since(x.t) }, h('s.strip', { style: since(x.t) }, ...flickFaces(x).map(v => h('b', null, v)))),
    h('span', { style: since(x.t) }, face), extra);
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
      h('div.rt-dice', null, ...t.dice.map(x => bigDie({ ...x, re: x.re != null }, '.foe', foeFace(x), since,
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
    h('div.rt-dice', null, ...t.dice.map(x => bigDie(x, '', shown(x), since,
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
  if ((it.k === 'attack' || it.k === 'all') && S.static.foes[fo.k]?.crit_text) lines.push(`Crit (a die on its top face; a d10 or bigger, its top two): ${S.static.foes[fo.k].crit_text}.`);
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
    const label = d.v != null ? (d.tag === 'W' ? 'W' : String(d.v)) : d.fc ? d.fc.map(x => (x[0] == null ? 'W' : fateText(x))).join('|') : `d${top}`;
    return h('span.md' + (d.v != null ? '.known' : '') + (d.fc ? '.fate' : '') + (d.dk.includes('exploding') ? '.boom' : '') + (d.dk.includes('steady') ? '.steady' : '') + (odd ? '.odd' : ''), null, label);
  });
  const b = it.bonus || 0;
  const body = it.dice?.length
    ? h('div.it-row', null, h('span.it-dice', null, ...dice, b ? h('span.bn', null, b > 0 ? `+${b}` : `−${-b}`) : null),
        range ? h('b.it-range', null, range, hits > 1 ? h('small', null, ` ×${hits}`) : null) : null)
    : h('div.it-row', null, icon(ic), h('span.it-what', null, range || { buff: 'buff', summon: 'calls help', charge: 'charging', dazed: 'nothing' }[it.k] || ''));
  // Break: a boss's big move stops if the party deals this much to it, from two heroes, before it acts
  const brk = it.brk ? Math.min(1, (fo.brk_d || 0) / it.brk) : 0;
  if (it.brk) lines.push(`Break: deal ${it.brk} to it before it acts, from at least two heroes, and this move is broken (${fo.brk_d || 0} so far, from ${(fo.brk_by || []).length} hero${(fo.brk_by || []).length === 1 ? '' : 'es'}).`);
  return h('div.intent.card' + sure + (it.guarded != null ? '.guarded' : '') + (it.brk ? '.breakable' : ''), { style: { '--c': col }, tip: lines.join('\n') },
    h('div.it-name', null, h('span.ic', null, icon(ic)), it.name || INTENT_TEXT[it.k] || '', it.guarded != null ? h('span.gd', null, icon('shield')) : null),
    body,
    it.brk ? h('div.it-break', null, h('span.bk-label', null, 'Break'), h('span.bk-bar', null, h('b', { style: { width: `${Math.round(brk * 100)}%` } })),
      h('span.bk-num', null, `${fo.brk_d || 0}/${it.brk}`)) : null,
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
    h('span.muted', null, `${i + 1}.`), h('span.who', null, stripWho(p.h)), h('b', null, a.name + (p.plus ? '+' : '')), tgt ? h('span.muted', null, '→ ' + tgt) : null, res,
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
      h('span.who', null, stripWho(x)), h('span.muted', null, `×${list.length}`),
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
  return JSON.stringify([f.id, f.round, x, my, hs, hero.actions, hero.bag, hero.spent, f.hymn, f.foes, f.chord, f.seq,
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
    if (S.static.items[k].slot !== 'use' || S.static.items[k].enchant || S.static.items[k].forge) return;
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
        ...focusTools(x, hs, dice, ready),
        ...trinketButtons(x, hs, ready),
        hawkButton(x, hs, ready),
        hs.inspire ? h('span.chip.brass', { tip: 'Inspired\nYour next die rolls this much higher.' }, `+${hs.inspire} next die`) : null,
        ...uses.map(([k, i, n]) => h('button.btn.sm.ghost', { disabled: ready, tip: `${S.static.items[k].name}\n${S.static.items[k].text}\nUsed at once; no die needed.`, onclick: () => useItem(x, k, i) }, icon('drop'), S.static.items[k].name + (n > 1 ? ` ×${n}` : ''))))),
    h('div.actions', null, ...acts.map((k, i) => actionCard(f, x, k, i, selDice, ready))),
    h('div.tray-right', null,
      C.pending ? h('p', { style: { color: 'var(--accent)', fontWeight: 600 } }, 'Choose a target', h('br'), h('span.muted', { style: { fontWeight: 400 } }, 'Esc to cancel')) : null,
      h('p.muted', { style: { fontSize: '14px' } }, C.playing && !hs.ready ? 'Keep playing: your actions queue up' : hs.ready ? (waiting.length ? `Waiting for ${waiting.join(', ')}` : 'Enemies are acting…') : waiting.length ? `${waiting.join(', ')} still acting` : 'Everyone else is ready'),
      hs.ready ? h('button.btn.lg', { onclick: () => send({ t: 'fready', h: x, on: false }) }, 'Unready')
        : h('button.btn.primary.lg' + (hs.dice.length && hs.dice.every(d => d.used) ? '.nudge' : ''), { onclick: () => { readyUp(x); render(); } }, icon('check'), 'Ready', h('span.kbd', null, 'Space'))));
}

// The Scoundrel's trinkets, lifted on crits and kills: each used once, without a die.
const TRINKET = { smoke: ['Smoke Pellet', '💨', 'hero', 'The next hit on you or an ally misses.'], caltrops: ['Caltrops', '✴', null, 'Every front-row enemy’s attack this round deals 2 less.'],
  flash: ['Flash Powder', '✨', 'foe', 'An enemy is Weak this round.'], venom: ['Vial of Venom', '🧪', 'foe', 'Poison an enemy for 3.'],
  coin: ['Loaded Coin', '🪙', 'hero', 'One of your dice, or an ally’s, rolls 2 higher.'], purse: ['Stolen Purse', '👛', null, '+6 gold, and your next die rolls 2 higher.'] };
// The Ranger's hawk: once a round, no die, send it to an enemy (to hunt) or a hero (to watch).
function hawkButton(x, hs, ready) {
  if (!hs.hawk) return null;
  const f = S.game.fight, moved = hs.hawk_r === f.round;
  return h('button.btn.sm.ghost.trinket', { disabled: ready || moved, tip: `Send your hawk${moved ? ' (it has moved this round)' : ''}\nOnce a round, no die needed. On an enemy it hunts: your hits on it deal +1 and it pecks it for 2. On a hero it watches: the first hit on them each round deals 3 less.`, onclick: () => {
    const opts = [...f.foes.filter(fo => fo.hp > 0).map(fo => 'f' + fo.id), ...f.heroes.filter(y => heroActive(f, y)).map(y => 'h' + y)].filter(u => u !== hs.hawk);
    if (!opts.length) return;
    C.pending = { msg: { t: 'hawk', h: x }, opts, item: true }; render();
  } }, '🪶 Send hawk');
}
function trinketButtons(x, hs, ready) {
  const f = S.game.fight;
  return (hs.trinkets || []).map((t, i) => {
    const [name, ic, want, text] = TRINKET[t.k] || ['Trinket', '?', null, ''];
    return h('button.btn.sm.ghost.trinket', { disabled: ready, tip: `${name}${t.uses > 1 ? ` (×${t.uses})` : ''}\n${text}\nLifted from an enemy; used at once, no die needed.`, onclick: () => {
      const msg = { t: 'trinket', h: x, i };
      const opts = want === 'foe' ? f.foes.filter(fo => fo.hp > 0).map(fo => 'f' + fo.id) : want === 'hero' ? f.heroes.filter(y => heroActive(f, y)).map(y => 'h' + y) : null;
      if (opts && opts.length > 1) { C.pending = { msg, opts, item: true }; render(); return; }
      send({ ...msg, tgt: opts ? opts[0] : null });
    } }, ic + ' ' + name);
  });
}
// The Psion's Focus (and Hive Mind's): select one shown die, then nudge it up or down by 1; Perfect
// Foresight sets it once a fight.
function focusTools(x, hs, dice, ready) {
  const hero = S.game.heroes[x];
  if (!hs.focus && !(hero.skills || []).includes('mind_link')) return [];
  const out = [h('span.chip.focus', { tip: 'Focus\nSpend 1 to nudge one of your shown dice up or down by 1. With Mind Link, 1 reveals one of an ally’s hidden dice (click it on their card), and more nudges it. Unspent Focus is lost at the end of the round.' },
    icon('eye'), `${hs.focus || 0} Focus`)];
  const sel = [...C.sel].map(id => dice.find(d => d.id === id)).filter(d => d && !d.used);
  const d = sel.length === 1 ? sel[0] : null;
  if (!d || d.v == null || ['S', 'X', 'W'].includes(d.tag) || ready) return out;
  const nums = d.faces.map(f => typeof f === 'number' ? f : parseInt(String(f).slice(1))).filter(n => !isNaN(n));
  const lo = Math.min(...nums), top = Math.max(...nums);
  if (hs.focus) {
    out.push(h('button.btn.sm.ghost', { disabled: d.v <= lo, tip: 'Spend 1 Focus: this die goes down by 1', onclick: () => send({ t: 'nudge', h: x, die: d.id, by: -1 }) }, '▼ −1'));
    out.push(h('button.btn.sm.ghost', { disabled: d.v >= Math.max(top, d.v), tip: 'Spend 1 Focus: this die goes up by 1', onclick: () => send({ t: 'nudge', h: x, die: d.id, by: 1 }) }, '▲ +1'));
  }
  if ((hero.skills || []).includes('perfect_foresight') && !hs.foresaw) {
    out.push(h('select.sm', { tip: 'Perfect Foresight: once a fight, set this die to any of its numbers', onchange: e => e.target.value && send({ t: 'nudge', h: x, die: d.id, set: parseInt(e.target.value) }) },
      h('option', { value: '' }, 'Set to…'), ...[...new Set(nums)].sort((a, b) => a - b).map(n => h('option', { value: String(n) }, String(n)))));
  }
  return out;
}

// A die in the tray: face-down (its kind and size) until it rolls, unless it's a Seer die (shown),
// an Augur die (high or low) or a Fate die (two faces).
// A die in the tray: a cream tile with its size (or its number, once known) big in the middle, a
// coloured top edge for where it comes from, and one icon for anything special about it.
const SRC = { base: ['Class die', 'var(--src-class)'], weapon: ['Weapon die', 'var(--src-weapon)'], armor: ['Armor die', 'var(--src-armor)'],
  trinket: ['Trinket die', 'var(--src-trinket)'], spirit: ['Spirit die from a fallen ally', 'var(--src-spirit)'], pet: ['Your hawk’s die', 'var(--src-pet)'],
  anthem: ['From the Anthem of Kings', 'var(--src-spirit)'], gift: ['Given by an ally', 'var(--src-spirit)'], hex: ['Cursed: a hex swapped your biggest die', 'var(--danger)'],
  split: ['Split off by your flask', 'var(--src-class)'], graft: ['Grafted from two dice', 'var(--src-class)'], tempo: ['Stolen tempo: a fresh die', 'var(--src-spirit)'], bloodlust: ['Bloodlust: a fresh die from a kill', 'var(--src-spirit)'],
  echo: ['Echo die: it copies an ally', 'var(--src-spirit)'], swell: ['Swell die: it grows while you leave it', 'var(--src-class)'] };
const KIND_ICON = { seer: 'eye', exploding: 'spark', steady: 'refresh', heirloom: 'star', guard: 'shield', echo: 'link', swell: 'up' };
function dieButton(d, i, ready) {
  const [srcName, srcCol] = SRC[d.src] || [`From your ${d.src}`, 'var(--border-strong)'];
  let face, cls = '';
  const size = dieLabel(d.faces);
  if (d.v !== null && d.v !== undefined) {
    face = d.tag === 'S' ? icon('shield') : d.tag === 'X' ? '☠' : d.tag === 'R' ? h('span.num', null, d.rolled ? `♫${d.v}` : '♫') : h('span.num', null, String(d.v));
    cls = '.known';
  } else if (d.fc) {
    const [a, b] = fateFaces(d).map(fateText);
    face = h('span.fate', null, a, h('i', null, '|'), b);
    cls = '.known';
  } else if (d.hint) {
    face = h('span.hint', null, d.hint === 'high' ? '▲' : '▼', h('small', null, d.hint));
  } else {
    face = h('span.size', null, d.top ? '★' : size);
  }
  const kinds = (d.dk || []).filter(k => KIND_ICON[k]);
  // once the number shows, the size takes the bottom-left corner: room for one kind icon beside it
  const shownKinds = d.v != null && !d.fc ? kinds.slice(0, 1) : kinds;
  const marks = [];
  if (d.bonus) marks.push(h('span.mk.bonus', null, `+${d.bonus}`));
  if (d.link) marks.push(h('span.mk', null, icon('link')));
  const f0 = S.game.fight;
  const chordFoes = d.v != null && !d.used && f0 ? f0.foes.filter(fo => fo.hp > 0 && chordNums(fo, f0, C.tab)?.includes(d.v)).map(fo => fo.name) : [];
  const bells = d.v != null && !d.used && f0 ? f0.foes.filter(fo => fo.hp > 0 && fo.bell && !fo.cracked && fo.bell === d.v) : [];
  if (chordFoes.length || bells.length) cls += '.combo';
  if (d.locked) cls += '.locked';
  const tipLines = [srcName, dieTip(d)];
  if (d.v == null && !d.fc) tipLines.push(`Hidden until its action happens. Averages about ${expected(d).toFixed(1)}.`);
  if (d.bonus) tipLines.push(`Rolls ${d.bonus} higher.`);
  if (d.faces.includes('R') && !d.rolled) tipLines.push(`♫ copies the last number an ally played this round: a ${f0?.hs?.[C.tab]?.rollmods?.resonant ?? 3} right now.`);
  if (chordFoes.length) tipLines.push(`Chord on ${chordFoes.join(', ')}: hit it with this next and it copies your ally's hit.`);
  if (bells.length) tipLines.push('Matches the bell: hit the Bell-Warden with it to crack the bell.');
  if (d.locked) tipLines.push('Crusted over by a Barnacle Priest: you can’t use it this round.');
  const tip = tipLines.join('\n');
  // a Swell die is drawn bigger with every round it waits (its step: d4, d10+2, d12+7, d20+12)
  if (d.src === 'swell') cls += '.swell.s' + Math.max(0, [4, 10, 12, 20].indexOf(d.faces.length));
  return h('button.die.tile' + cls + (d.used ? '.used' : '') + (C.sel.has(d.id) && !d.used ? '.sel' : '') + (kinds.includes('guard') ? '.guard' : '') + (C.rolled ? '.roll' : ''), {
    style: { '--src': srcCol }, disabled: d.used || ready, 'data-id': d.id, 'aria-label': `Die ${i + 1}: ${size}${d.v != null ? ', showing ' + d.v : ''}`, tip, onclick: () => toggleDie(d.id),
  }, h('span.k', null, i + 1), face,
    shownKinds.length ? h('span.kinds', null, ...shownKinds.map(k => icon(KIND_ICON[k]))) : null,
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
  const a = upDef(k, x);
  const hs = f.hs[x];
  const once = a.once && hs.once.includes(base);
  const spent = a.per_rest && (S.game.heroes[x].spent || []).includes(base);
  const cooling = a.cd ? (hs.cds?.[base] || 0) : 0;
  const meleeBlocked = false;
  // the Samurai's blade the wrong way for it, or the Gunslinger's cylinder empty
  const wrongStance = a.stance && hs.sheathed != null && hs.sheathed !== (a.stance === 'sheathed');
  const empty = a.shot && (hs.ammo || 0) <= 0;
  // what the class's gauge means for this card right now: the Silver Round next, the Resolve a Draw would spend
  const silverNext = a.shot === 1 && hs.ammo > 0 && (hs.ammo === 1 || (hs.lucky && hs.ammo === (hs.cap || 6) - 2));
  const live = silverNext ? ' · Silver Round: ×2' : (base === 'the_draw' || base === 'flash_draw') && hs.sheathed ? ` · Resolve ${hs.resolve || 0}` : '';
  const noFlee = base === 'flee' && (f.kind === 'dungeon' || f.kind === 'boss');
  const n = a.req.n ?? 1;
  const guardOff = !a.def && selDice.some(d => d.dk?.includes('guard'));
  const fits = !ready && !once && !spent && !cooling && !meleeBlocked && !noFlee && !guardOff && !wrongStance && !empty && (n === 0 ? selDice.length === 0 : countOk(a.req, selDice));
  // with nothing picked, the dice a click would use: shown on hover, and their odds on the card
  const auto = n > 0 && !selDice.length ? autoDice(f, x, a) : null;
  const noDice = n > 0 && !selDice.length && !auto;
  const chance = fits && n > 0 ? hitChance(a.req, selDice, f.hymn || 0, hs.rollmods) : auto && isRisky(a.req) ? hitChance(a.req, auto, f.hymn || 0, hs.rollmods) : null;
  const dis = ready || once || spent || noFlee || cooling > 0 || noDice || wrongStance || empty;
  const why = wrongStance ? (a.stance === 'sheathed' ? '\nYour blade is drawn: Sheathe it first.' : '\nYour blade is sheathed: the Draw brings it out.')
    : empty ? '\nYour cylinder is empty: Reload first.' : spent ? '\nSpent: it comes back when you rest.' : guardOff ? '\nGuard dice only go on defensive actions.' : once ? '\nOnce per fight.' : noFlee ? '\nThere’s no running from this one.'
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
    disabled: dis, onmouseenter: () => light(true), onmouseleave: () => light(false), onfocus: () => light(true), onblur: () => light(false), tip: `${a.name}${k.endsWith('+') ? '+' : ''}\n${reqText(a.req)}\n${a.text}${upText(k, a)}${a.melee ? '\nMelee: reaches only the enemies’ front row.' : ''}${cdText}${why}`,
    onclick: () => pickAction(f, x, k, selDice),
  },
    h('div.rq' + (bd.risky ? '.risky' : '') + oddCls, { tip: `Needs: ${reqText(a.req)}${chance !== null ? `\n${Math.round(chance * 100)}% to hit with ${auto ? 'the dice it would use' : 'your picked dice'}` : ''}` },
      h('b', null, bd.main), chance !== null && bd.risky ? h('small', null, `${Math.round(chance * 100)}%`) : bd.sub ? h('small', null, bd.sub) : null),
    h('div.ab', null,
      h('div.top', null, h('b', null, a.name + (k.endsWith('+') ? '+' : '')),
        cooling ? h('span.cd.on', null, icon('clock'), cooling > 1 ? `${cooling}` : '1')
          : a.cd ? h('span.cd', { tip: `Cooldown ${a.cd}\nAfter using it, wait ${a.cd - 1} round${a.cd === 2 ? '' : 's'}.` }, icon('clock'), a.cd) : null),
      h('div.eff', null, icon(ico), h('span', null, eff + (k.endsWith('+') ? ' (+2)' : ''), live ? h('b.live', null, live) : null)),
      miss ? h('div.miss', null, `miss: ${miss}`) : null,
      a.crit_short ? h('div.crit', { tip: CRIT_TIP }, `crit: ${a.crit_short}`) : null),
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
  const a = upDef(k, x);
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
  if (u.throw) opts = u.throw.all ? null : f.foes.filter(fo => fo.hp > 0).map(fo => 'f' + fo.id);
  else if (u.heal || u.cleanse) opts = f.heroes.filter(y => heroActive(f, y)).map(y => 'h' + y);
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
    if (a.melee) {
      const fr = alive.filter(fo => fo.row === 'front');
      // Pinned Prey: the Ranger's hawk holds its enemy within melee reach
      const pinned = alive.filter(fo => f.heroes.some(y => f.hs[y]?.hawk === 'f' + fo.id && (S.game.heroes[y].skills || []).includes('pinned_prey')));
      if (fr.length) pool = [...fr, ...pinned.filter(fo => !fr.includes(fo))];
    }
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
    // a greyed-out card (cooling, spent, the blade the wrong way, an empty cylinder...) says why, as a click can't reach it
    const card = document.querySelectorAll('.tray .actions > .action')[ai];
    if (card?.disabled) {
      const why = (card.dataset.tip || '').split('\n').pop();
      if (why) toast(why);
      return;
    }
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
    C.playing = false; C.display = null; C.hp = null; C.maxhp = null; C.anim = {}; C.floats = {}; C.hitBy = null; C.tray = null; C.caption = null;
    if (queue.length) { playNext(); return; }
    render();
    flushIdle();
  };
  if (!ended) { close(); return; }
  // the fight's last moment stays up under the banner, the heroes still standing celebrate; loot
  // and the map come after
  C.tray = null;
  if (ended.result === 'won') for (const x of C.display?.heroes || []) if (!C.display.hs[x]?.down && !C.display.hs[x]?.fled) flash('h' + x, 'victory', 1300);
  render();
  banner(ended);
  setTimeout(close, 1300 / (S.settings.speed || 1));
}

// The end-of-fight banner; a win counts up its gold and XP.
function banner(ended) {
  const result = ended.result;
  sfx.play(result === 'won' ? 'win' : 'lose');
  if (result === 'won') bigBanner('Victory', ended.xp != null ? countUp([[ended.gold, 'gold each', 'coin'], [ended.xp, 'XP', 'star']]) : '', 'gold', 1700);
  else bigBanner(result === 'fled' ? 'Escaped' : 'Defeat', '', 'danger', 1600);
}
function countUp(parts) {
  const out = h('span.count-up');
  for (const [n, label, ic] of parts) {
    if (!n) continue;
    const num = h('b', null, '+0');
    out.append(h('span', null, icon(ic), num, ' ' + label));
    const t0 = performance.now(), ms = 650;
    const tick = () => { const k = Math.min(1, (performance.now() - t0 - 250) / ms); num.textContent = '+' + Math.round(n * Math.max(0, 1 - (1 - k) ** 3)); if (k < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  }
  return out;
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
    lines.push(`${a.name}${k.endsWith('+') ? '+' : ''}${cd ? ` (ready in ${cd})` : ''}: ${a.text}${upText(k, a)}`);
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
function fxAt(id, cls, ms = 650, col = null, glyph = null) {
  const c = unitCenter(id);
  if (!c) return;
  const el = document.createElement('div');
  el.className = 'fx ' + cls;
  if (col) el.style.setProperty('--c', col);
  if (glyph) el.dataset.g = glyph;
  el.style.left = c[0] + 'px'; el.style.top = c[1] + 'px';
  fxLayer().appendChild(el);
  setTimeout(() => el.remove(), ms);
}
// The front of a hero's sprite (heroes face right), where a gun's muzzle or a blade's hilt is.
function unitFront(id) {
  const img = host?.querySelector(`[data-uid="${id}"] img`);
  if (!img) return null;
  const r = img.getBoundingClientRect();
  return id.startsWith('f') ? [r.left + r.width * 0.15, r.top + r.height * 0.45] : [r.right - r.width * 0.15, r.top + r.height * 0.45];
}
function fxPoint(p, cls, ms, col) {
  const el = document.createElement('div');
  el.className = 'fx ' + cls;
  if (col) el.style.setProperty('--c', col);
  el.style.left = p[0] + 'px'; el.style.top = p[1] + 'px';
  fxLayer().appendChild(el);
  setTimeout(() => el.remove(), ms);
  return el;
}
// A spray of particles from a unit, or drawn into it (o.inward). o: { n, r: reach in px, dir and cone
// in degrees (a cone of spray, else all round), ms, cls: 'petal' and the like, fall: px they drop }
function fxSparks(id, col, o = {}) {
  const p = unitCenter(id);
  if (!p) return;
  const n = o.n || 10, ms = (o.ms || 520) / (S.settings.speed || 1);
  for (let i = 0; i < n; i++) {
    const deg = o.cone != null ? (o.dir || 0) + (Math.random() - 0.5) * o.cone : (360 * (i + Math.random())) / n;
    const rad = deg * Math.PI / 180, r = (o.r || 70) * (0.55 + Math.random() * 0.7);
    const out = [Math.cos(rad) * r, Math.sin(rad) * r + (o.fall || 0)];
    const [a, b] = o.inward ? [out, [0, 0]] : [[0, 0], out];
    const el = fxPoint(p, 'spark' + (o.cls ? ' ' + o.cls : ''), ms + 40, col);
    const tf = (q, s) => `translate(calc(-50% + ${q[0]}px), calc(-50% + ${q[1]}px)) rotate(${deg}deg) scale(${s})`;
    el.animate([{ transform: tf(a, 1), opacity: 1 }, { transform: tf(b, o.inward ? 0.6 : 0.3), opacity: o.inward ? 0.9 : 0 }],
      { duration: ms * (0.75 + Math.random() * 0.25), easing: o.inward ? 'ease-in' : 'cubic-bezier(0.2, 0.7, 0.3, 1)', fill: 'forwards' });
  }
}
// A gun going off: a flash at the muzzle and a streak of light to the target (o.past: px it carries on
// beyond it, for a round that goes through; a miss flies wide).
function fxMuzzle(id, col) { const p = unitFront(id); if (p) fxPoint(p, 'muzzle', 220 / (S.settings.speed || 1), col); }
function fxTracer(from, to, col, o = {}) {
  const a = unitFront(from), b = unitCenter(to);
  if (!a || !b) return;
  const end = o.miss ? [b[0] + 30, b[1] - 46] : b;
  const len = Math.hypot(end[0] - a[0], end[1] - a[1]) + (o.past || 0);
  const ms = (o.ms || 320) / (S.settings.speed || 1);
  const el = fxPoint(a, 'tracer' + (o.cls ? ' ' + o.cls : ''), ms + 40, col);
  el.style.width = len + 'px';
  el.style.transform = `translateY(-50%) rotate(${Math.atan2(end[1] - a[1], end[0] - a[0])}rad)`;
  // the streak races out to the target, then its tail catches up
  el.animate([{ clipPath: 'inset(0 100% 0 0)', opacity: 1 }, { clipPath: 'inset(0 0 0 0)', opacity: 1, offset: 0.3 }, { clipPath: 'inset(0 0 0 40%)', opacity: 0.9, offset: 0.6 }, { clipPath: 'inset(0 0 0 85%)', opacity: 0 }],
    { duration: ms, easing: 'ease-out', fill: 'forwards' });
}
// A clean cut straight across a unit: a long line that draws itself at an angle, then splits apart.
function fxSplit(id, col, deg = -20, ms = 520) {
  const c = unitCenter(id);
  if (!c) return;
  const el = fxPoint(c, 'split', ms / (S.settings.speed || 1), col);
  el.style.setProperty('--r', deg + 'deg');
  el.style.setProperty('--ms', ms / (S.settings.speed || 1) + 'ms');
}
// A capstone's name across the screen, before it plays.
function fxCutin(text, sub, col, ms = 900) {
  const el = document.createElement('div');
  el.className = 'fx-cutin';
  el.style.setProperty('--c', col);
  el.style.setProperty('--ms', ms / (S.settings.speed || 1) + 'ms');
  el.append(Object.assign(document.createElement('b'), { textContent: text }), Object.assign(document.createElement('span'), { textContent: sub }));
  fxLayer().appendChild(el);
  setTimeout(() => el.remove(), ms / (S.settings.speed || 1));
}
// o: { c: colour (--c), arc: px the shot lifts mid-flight (a lob; negative dips), spin: it tumbles,
//      ms: its flight time (a bullet is quick) }
function fxShot(from, to, cls, done, o = {}) {
  const a = unitCenter(from), b = unitCenter(to);
  if (!a || !b) { done?.(); return; }
  const el = document.createElement('div');
  el.className = 'fx shot ' + cls;
  if (o.c) el.style.setProperty('--c', o.c);
  el.style.left = a[0] + 'px'; el.style.top = a[1] + 'px';
  const ang = o.spin ? 0 : Math.atan2(b[1] - a[1], b[0] - a[0]) * 180 / Math.PI;
  fxLayer().appendChild(el);
  const ms = (o.ms || (o.arc ? 380 : 260)) / (S.settings.speed || 1);
  const dx = b[0] - a[0], dy = b[1] - a[1];
  const at = (t, lift, rot) => ({ transform: `translate(calc(-50% + ${dx * t}px), calc(-50% + ${dy * t - lift}px)) rotate(${rot}deg)` });
  const frames = o.arc
    ? [at(0, 0, ang), at(0.5, o.arc, ang + (o.spin ? 360 : 0)), at(1, 0, ang + (o.spin ? 720 : 0))]
    : [at(0, 0, ang), at(1, 0, ang + (o.spin ? 720 : 0))];
  const anim = el.animate(frames, { duration: ms, easing: o.arc ? 'linear' : 'ease-in' });
  anim.onfinish = () => { el.remove(); done?.(); };
}
// A line between two units that draws itself, holds, then fades: an enemy's aim, an Echo's link.
function fxLine(from, to, cls, ms = 900, col = null) {
  const a = unitCenter(from), b = unitCenter(to);
  if (!a || !b) return;
  const el = document.createElement('div');
  el.className = 'fx line ' + cls;
  if (col) el.style.setProperty('--c', col);
  const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
  el.style.left = a[0] + 'px'; el.style.top = a[1] + 'px'; el.style.width = len + 'px';
  el.style.transform = `rotate(${Math.atan2(b[1] - a[1], b[0] - a[0])}rad)`;
  el.style.setProperty('--ms', (ms / (S.settings.speed || 1)) + 'ms');
  fxLayer().appendChild(el);
  setTimeout(() => el.remove(), ms / (S.settings.speed || 1));
}
// A screen-wide flash of colour, for the biggest moments.
function fxScreen(cls, ms = 500, col = null) {
  const el = document.createElement('div');
  el.className = 'fx-screen ' + cls;
  if (col) el.style.setProperty('--c', col);
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
  reckless_swing: (f, t, miss, later) => { later(() => { t.forEach(u => fxAt(u, 'bigslash' + (miss ? ' miss' : ''), 520)); if (!miss) flash('stage', 'shake', 380); }, 180); return 'melee'; },
  lunge: (f, t, miss, later) => { later(() => t.forEach(u => { fxAt(u, 'thrust' + (miss ? ' miss' : ''), 420); if (!miss) later(() => fxAt(u, 'star', 520), 120); }), 120); return 'melee'; },
  finisher: (f, t, miss, later) => { [0, 110, 220].forEach(ms => later(() => t.forEach(u => fxAt(u, 'slash', 420)), ms + 120)); if (!miss) later(() => fxScreen('white', 240), 360); return 'melee'; },
  chain_lightning: (f, t, miss, later) => { t.forEach(u => fxBolt('h' + f.h, u)); if (!miss) { later(() => fxScreen('bolt', 200), 40); t.forEach(u => fxAt(u, 'zap', 500)); } return 'spell'; },
  frost_lance: (f, t, miss) => { t.forEach(u => fxShot('h' + f.h, u, 'ice', () => fxAt(u, 'iceburst' + (miss ? ' miss' : ''), 700))); return 'spell'; },
  volley: (f, t, miss, later) => { t.forEach((u, i) => [0, 90, 180].forEach(ms => later(() => fxAt(u, 'rain', 520), ms + i * 40))); return 'ranged'; },
  aimed_shot: (f, t, miss, later) => { t.forEach(u => { fxAt(u, 'crosshair', 520); later(() => fxShot('h' + f.h, u, 'ranged', () => fxAt(u, 'pierce' + (miss ? ' miss' : ''), 520)), 300); }); return 'ranged'; },
  renew: (f, t) => { t.forEach((u, i) => setTimeout(() => fxAt(u, 'healglow big', 1000), i * 90)); fxScreen('green', 400); return 'heal'; },
};
// The effects kit skillfx.js builds its looks from (see the top of that file).
function fxKit(from, tgts, miss, d) {
  const later = (fn, ms = 0) => (ms > 0 ? setTimeout(fn, ms / (S.settings.speed || 1)) : fn());
  const x = {
    from, t: tgts, miss, later,
    party: [...(d.heroes || []).filter(y => !d.hs[y]?.down && !d.hs[y]?.fled).map(y => 'h' + y), ...(d.allies || []).filter(a => a.hp > 0).map(a => 's' + a.id)],
    foes: (d.foes || []).filter(fo => fo.hp > 0).map(fo => 'f' + fo.id),
    on: (id, cls, c, ms = 650, delay = 0, g) => later(() => fxAt(id, cls + (miss && id !== from ? ' miss' : ''), ms, c, g), delay),
    hit: (cls, c, ms, delay, g) => tgts.forEach(u => x.on(u, cls, c, ms, delay, g)),
    me: (cls, c, ms, delay, g) => x.on(from, cls, c, ms, delay, g),
    shot: (cls, c, impact, o = {}) => (o.to || tgts).forEach((u, i) => later(() => {
      const [a, b] = o.back ? [u, from] : [from, u];
      fxShot(a, b, cls, impact ? () => x.on(b, impact[0], impact[1] ?? c, impact[2], 0, impact[4]) : null, { c, arc: o.arc, spin: o.spin, ms: o.ms });
    }, (o.delay || 0) + i * (o.stagger ?? 0))),
    sparks: (id, c, o = {}, delay = 0) => later(() => fxSparks(id, c, o), delay),
    // sparks off each target that was hit (none on a miss)
    burst: (c, o = {}, delay = 0) => { if (!miss) tgts.forEach(u => x.sparks(u, c, o, delay)); },
    muzzle: (c, delay = 0) => later(() => fxMuzzle(from, c), delay),
    tracer: (to, c, o = {}, delay = 0) => later(() => fxTracer(o.from || from, to, c, { miss, ...o }), delay),
    split: (id, c, deg, delay = 0, ms) => later(() => fxSplit(id, c, deg, ms), delay),
    ring: (id, c, delay = 0, big) => x.on(id, 'shock' + (big ? ' big' : ''), c, 640, delay),
    line: (a, b, cls, ms, delay = 0, c = null) => later(() => fxLine(a, b, cls, ms, c), delay),
    punch: (delay = 0) => later(() => flash('stage', 'punch', 240), delay),
    back: (cls, c, impact, o = {}) => x.shot(cls, c, impact, { ...o, back: true }),
    bolt: (a, b) => fxBolt(a, b),
    screen: (cls, ms, c) => fxScreen(cls, ms, c),
    shake: (delay = 0) => later(() => flash('stage', 'shake', 380), delay),
    quake: (delay = 0) => later(() => { flash('stage', 'quake', 600); fxScreen('dust', 600); }, delay),
    move: (id, cls, ms) => flash(id, cls, ms),
  };
  return x;
}
// For checking every look by eye (tools/saltbound-fxsheet.js): plays an action's or an enemy move's
// effect on the open fight. Only on debug pages (?bots), like window.saltbound.
if (new URLSearchParams(location.search).has('bots')) window.saltboundFx = {
  skills: () => Object.keys(SKILL_FX).concat(Object.keys(SIGNATURE)),
  skill(a, h, tgts) {
    const d = S.game.fight, ad = S.static.actions[a];
    // nothing is playing back, so keep drawing while it moves
    const iv = setInterval(render, 40); setTimeout(() => clearInterval(iv), 2400);
    return abilityFx({ a, h, tgt: tgts[0], hit: true }, ad, d, tgts);
  },
  foe(fid, it, tgts) {
    const d = S.game.fight, fo = d.foes.find(x => x.id === fid);
    const ms = foeFx(fxKit('f' + fid, tgts, false, d), { ...fo }, it, m => { flash('f' + fid, 'f-' + m, FOE_MOTION_MS[m] || 360); render(); });
    return ms;
  },
};
const FOE_MOTION_MS = { lunge: 380, pounce: 460, slam: 520, charge: 560, cast: 420, brace: 420 };
// how a hero's body moves as they act (the stylesheet's .unit.<motion> img)
// (shoot: a gun's or a bow's kick back, not a step forward; fan: several in a row; iai: a dash through)
const MOTION_MS = { melee: 360, charge: 520, spin: 560, retreat: 600, brace: 420, cast: 420, act: 360, shoot: 260, fan: 560, iai: 460, ready: 260 };
// How long a cooldown skill winds up before it lands (a capstone's banner comes first).
const WINDUP_MS = 260, CUTIN_MS = 620;
// the generic kinds (abilityKind) as body motions: a spell or a heal is cast, Armor braces, a shot kicks
const KIND_MOTION = { ranged: 'shoot', spell: 'cast', heal: 'cast', buff: 'cast', armor: 'brace', bomb: 'act' };

// Plays an action's look and the hero's motion. A cooldown skill winds up first (its class's sigil at
// the hero's feet, light drawn into them), and a once-a-fight capstone opens with its name across the
// screen; returns how long that takes, so the damage numbers wait for it. (`only`: the targets, for the
// effects sheet.)
function abilityFx(f, ad, d, only) {
  if (!ad || !S.settings.speed) return 0;
  const sp = S.settings.speed || 1;
  const from = 'h' + f.h, miss = f.hit === false;
  const tgts = only || abilityTargets(f, ad, d);
  const look = CLASS_LOOK[S.game.heroes[f.h]?.cls] || CLASS_LOOK.default;
  const big = !!(ad.cd || ad.once) && !f.echo;
  const cutin = big && ad.once ? CUTIN_MS : 0, pre = big ? cutin + WINDUP_MS : 0;
  if (cutin) fxCutin(ad.name, S.game.heroes[f.h]?.name || '', look.c, cutin + 260);
  if (big) setTimeout(() => {
    fxAt(from, 'windup', WINDUP_MS + 260, look.c, look.g);
    fxSparks(from, look.c, { n: 12, r: 90, inward: true, ms: WINDUP_MS });
    flash(from, 'charging', WINDUP_MS);
  }, cutin / sp);
  const play = () => {
    const kind = playLook(f, ad, d, tgts, from, miss);
    const motion = MOTION_MS[kind] ? kind : KIND_MOTION[kind] || 'act';
    flash(from, motion, MOTION_MS[motion]);
  };
  if (pre) setTimeout(play, pre / sp); else play();
  return pre / sp;
}
function playLook(f, ad, d, tgts, from, miss) {
  const kind = abilityKind(ad);
  const sig = SIGNATURE[f.a];
  if (sig) return sig({ ...f, heroes: (d.heroes || []).filter(x => !d.hs[x]?.down).map(x => 'h' + x) }, tgts, miss, (fn, ms) => setTimeout(fn, ms / (S.settings.speed || 1)));
  if (SKILL_FX[f.a]) return SKILL_FX[f.a](fxKit(from, tgts, miss, d));
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
// Who played a move, short, for the round strip: the hero's name, or for another player's one hero
// that player's name. A bot, or a player with several heroes, is named by the hero ("Bot" said nothing).
function stripWho(x) {
  const hero = S.game.heroes[x], c = S.room?.ctl?.[x];
  if (mine().includes(x) || c === 'bot' || !c || S.room.ctl.filter(y => y === c).length > 1) return hero.name;
  return controllerName(x);
}
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

// What each combo looks like when it goes off (the 'combo' effect): its colour, the line under its
// banner, and an effect on the enemy it hit.
const COMBO_LOOK = {
  chord: { c: '#ffd36b', sub: 'Combo: the same number, back to back', fx: (u, c) => { fxAt(u, 'shock big', 640, c); fxAt(u, 'notes', 1000); fxSparks(u, c, { n: 18, r: 100 }); } },
  overload: { c: '#bfe0ff', sub: 'Reaction: Burn + Shock', fx: (u, c) => { fxAt(u, 'zap', 520); fxAt(u, 'fireburst', 800); fxScreen('bolt', 220); fxSparks(u, c, { n: 20, r: 130 }); flash('stage', 'shake', 380); } },
  thermal: { c: '#ff9a5a', sub: 'Reaction: Burn + Freeze', fx: (u, c) => { fxAt(u, 'smoke', 900, 'rgba(240, 245, 250, 0.8)'); fxAt(u, 'shards full', 560); fxSparks(u, c, { n: 14, r: 90 }); flash('stage', 'punch', 240); } },
  blightfire: { c: '#c4f03a', sub: 'Reaction: Burn + Poison', fx: (u, c) => { fxAt(u, 'fireburst', 800); fxAt(u, 'cloud', 1100); fxSparks(u, c, { n: 14, r: 90, dir: -90, cone: 120, cls: 'bubble', ms: 900 }); } },
  fracture: { c: '#9fdcff', sub: 'Reaction: Freeze + Shock', fx: (u, c) => { fxAt(u, 'iceburst', 700); fxAt(u, 'shards full', 560); fxScreen('white', 160); fxSparks(u, c, { n: 18, r: 110, cls: 'mote' }); flash('stage', 'punch', 240); } },
  conduction: { c: '#8ee04a', sub: 'Reaction: Shock + Poison', fx: (u, c) => { fxAt(u, 'zap', 520, c); fxAt(u, 'hoop', 600, c); fxSparks(u, c, { n: 16, r: 140, cls: 'bubble', ms: 800 }); } },
  frostlock: { c: '#bfe6ff', sub: 'Reaction: Root + Freeze', fx: (u, c) => { fxAt(u, 'vines', 900, '#6fd36a'); fxAt(u, 'iceburst', 800); fxAt(u, 'squeeze', 700, c); fxSparks(u, c, { n: 12, r: 80, inward: true, cls: 'mote', ms: 500 }); } },
  kindling: { c: '#ffa030', sub: 'Reaction: Root + Burn', fx: (u, c) => { fxAt(u, 'vines', 800, '#6fd36a'); fxAt(u, 'pillar', 800, c); fxSparks(u, c, { n: 14, r: 90, dir: -90, cone: 120 }); } },
  break: { c: '#ff5a4a', sub: 'Its big move is broken', fx: (u, c) => { fxAt(u, 'shock big', 640, c); fxAt(u, 'shards full', 560); fxScreen('white', 200); fxSparks(u, c, { n: 20, r: 120 }); flash('stage', 'shake', 380); } },
};
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

// What a status event floats over a fighter when it isn't one of the STATUS names (rules.js).
const ST_FLOAT = {
  guarded: 'Guarded', taunt: 'Taunt', stunned: 'Stunned', cleansed: 'Cleansed', unbreakable: 'Unbreakable!',
  sanct: 'Sanctuary', might: 'Might', weakened: 'Weakened', distracted: 'Distracted', dazed: 'Dazed',
  dodged: 'Dodged!', inspired: 'Inspired', hymn: 'Hymn', rerolls: '+2 rerolls', thorns: 'Thorns!',
  enraged: 'Enraged!', explodes: 'Bursts!', bloodied: 'Bloodied!', rallies: 'Rallies!', undertow: 'Undertow next',
  dragged: 'Dragged under!', scattered: 'Light scattered!', unwarded: 'Ward broken!', die_stolen: 'Die stolen!',
  locked: 'Die crusted over!', static: 'Static shock!', snatched: 'Snatched!', merged: 'Merged!', splits: 'Splits!',
  shrugs: 'Shrugs it off', doused: 'Lamp out!', swallowed: 'Swallowed!', 'spat out': 'Spat out!',
  'out of reach': 'Out of reach!', spite: 'Spite +1', steeled: 'Steeled: resists!', flees: 'Flees!',
  recovered: 'Got it back!', sigil: 'Carved!', burst: 'Burst!', glanced: 'Glancing blow', smoke: 'Smoke!',
  lifted_smoke: 'Lifted: Smoke Pellet', lifted_caltrops: 'Lifted: Caltrops', lifted_flash: 'Lifted: Flash Powder',
  lifted_venom: 'Lifted: Venom', lifted_coin: 'Lifted: Loaded Coin', lifted_purse: 'Lifted: a purse',
  harm_valor: 'Valor +1', harm_aegis: 'Aegis +1', harm_discord: 'Dissonance +1', harm_spent: 'Crescendo!',
  chilled: 'Chilled', converged: 'Convergence!', converge_ready: 'Flux full!', berserk: 'Berserk!',
  radiant: 'Grace full!', radiance: 'Radiance!', caustic: 'Caustic burst!', steam: 'Steam!', brittle: 'Brittle!',
  nudged: 'Nudged', revealed: 'Revealed!', puppeted: 'Turned!', foreseen_die: 'Foreseen!', foreseen: 'Foreseen!',
  echo: 'Echo!', focus: '+1 Focus', scale: '+Scale', shed: 'Shed!', ascended: 'Ascended!', overheat: 'Overheat!',
  web: 'Rootweb!', hawk_hunt: 'Hunted!', hawk_watch: 'Hawk watching', hawk_soak: 'Hawk!',
  impact_full: 'Impact full!', white_heat: 'White heat!', kindled: 'Kindled!', infused_frost: 'Frost blade!',
  infused_shock: 'Storm blade!', infused_burn: 'Flame blade!', flipped: 'Flipped!', split: 'Split!',
  embers: 'Embers!', falling: 'Look out above!', crushed: 'Crushed!', grafted: 'Grafted!',
  second_opinion: 'Second opinion', triage: 'Triage', tempo: 'Tempo!', bloodlust: 'Bloodlust! +d6',
  rampage: 'Rampage! Ready again', shielded: 'Shared Burden!', hexed: 'Hexed!', grows: 'Its die grows!',
  charged: 'Charged!', arced: 'Arced!', robbed: 'Robbed!', resisted: 'Resisted', burn: 'Burn', freeze: 'Frozen',
  poison: 'Poison', carried: 'Carried on!', rallied: 'Rallied: +3', tethered: 'Tethered', refreshed: 'Ready again!',
  drowsy: 'Drowsy', asleep: 'Asleep', wakes: 'Wakes!', mirrored: 'Mirrored!',
  'nothing to mirror': 'Nothing to mirror', counter: 'Pike set', chill: 'Rime', wound: 'Wounded', mummy: 'Mummified',
  snare: 'Snared', cued: 'Next hit up!', lucky: '+1 reroll', reloaded: 'Reloaded!', resolve: 'Resolve',
  sheathed: 'Sheathed', drawn: 'Drawn!', iai: 'Iai!', one_cut: 'One cut!', silver_round: 'Silver Round!',
  quick_draw: 'Quick Draw!', cocked: 'Hammer cocked'
};
function apply(f) {
  const d = C.display;
  if (['dmg', 'heal', 'armor', 'st', 'die', 'down', 'lift', 'drag'].includes(f.k) && typeof f.to !== 'string') return 0;
  const foe = id => d.foes.find(fo => 'f' + fo.id === id);
  const ally = id => (d.allies || []).find(a => 's' + a.id === id);
  switch (f.k) {
    case 'round': {
      C.hitBy = null;
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
      const held = d.hs[f.h]?.dice || [];
      const ad0 = act && S.static.actions[act.a];
      C.lastHero = f.h;
      C.tray = { h: f.h, a: act?.a, t: now, dice: f.dice.map(x => ({ ...x, t: now, faces: held.find(y => y.id === x.id)?.faces, crit: !!ad0?.crit_short && critDie(x.v, x.tag, held.find(y => y.id === x.id)?.faces) })) };
      // the caption names the action now playing, from its first roll (never the one before it)
      C.caption = act && !mine().includes(f.h) && S.static.actions[act.a] ? makeCaption(act, S.static.actions[act.a], d, true) : null;
      flash('h' + f.h, 'ready', MOTION_MS.ready);
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
      // what it hits next sprays sparks: the class's colour for a cooldown skill, white for the rest
      C.hitBy = { h: f.h, big: !!(ad?.cd || ad?.once), c: (CLASS_LOOK[S.game.heroes[f.h]?.cls] || CLASS_LOOK.default).c };
      const pre = Math.round(abilityFx(f, ad, d));
      if (C.tray?.h === f.h && C.tray.a === f.a && !f.echo) {
        sfx.play(f.hit === false ? 'error' : 'swing');
        if (ad && isRisky(ad.req)) {
          C.tray.verdict = f.hit === false ? 'miss' : 'hit'; C.tray.vt = performance.now();
          if (f.hit !== false) sfx.play('hitwin');
          return 640 + pre;
        }
        return 240 + pre;
      }
      addFloat('h' + f.h, (ad?.name || '') + (f.echo ? ' (echo)' : '') + (f.hit === false ? ': miss' : ''), f.hit === false ? 'miss' : 'txt');
      sfx.play(f.hit === false ? 'error' : 'swing');
      return 480 + pre;
    }
    case 'froll': {
      C.hitBy = null;
      // an enemy rolls its dice in the open: each die lands, then the total (or what went wrong)
      const fo = foe('f' + f.f);
      const now = performance.now();
      const dice = f.dice || [];
      const each = fo?.intent?.each;
      const total = each || !dice.length ? null : Math.max(0, dice.reduce((a, x) => a + (x.v || 0), 0) + (f.bonus || 0));
      const span = (f.hi ?? 0) - (f.lo ?? 0), third = span / 3;
      const NOTE = { crit: ['heavy', 'Crit!'], explodes: ['heavy', 'Explodes!'], doubles: ['heavy', 'Doubles!'], skull: ['glancing', 'Skull!'], rider: ['heavy', fo?.intent?.st ? `${STATUS[fo.intent.st]?.name || ''}!` : 'Lands!'] };
      let [verdict, label] = NOTE[f.note] || [null, null];
      if (!verdict && total != null && span > 2) {
        if (total >= f.hi - third) [verdict, label] = ['heavy', 'Heavy!'];
        else if (total <= f.lo + third) [verdict, label] = ['glancing', 'Glancing'];
      }
      C.caption = null;
      C.tray = { fid: f.f, foe: fo?.name || 'Enemy', name: f.name, range: f.lo != null ? `${f.lo}–${f.hi}` : '', t: now, verdict, label, total,
        bonus: f.bonus || 0, vt: now + 420 / (S.settings.speed || 1), dice: dice.map((x, j) => ({ ...x, id: 'f' + f.f + '.' + j, t: now, faces: fo?.intent?.dice?.[j]?.faces,
          crit: f.note === 'crit' && critDie(x.v, x.tag, fo?.intent?.dice?.[j]?.faces) })) };
      // the enemy about to act stands out, and its aim draws itself to whoever it's after
      flash('f' + f.f, 'acting', 1150);
      if (fo?.intent && S.settings.speed) {
        const it = fo.intent;
        const party = [...(d.heroes || []).filter(y => !d.hs[y]?.down && !d.hs[y]?.fled).map(y => 'h' + y), ...(d.allies || []).filter(a => a.hp > 0).map(a => 's' + a.id)];
        const tgts = it.k === 'all' ? party : (it.tgts || (it.tgt ? [it.tgt] : [])).filter(u => typeof u === 'string' && party.includes(u));
        tgts.forEach(u => fxLine('f' + f.f, u, 'aim', 1100));
      }
      sfx.play('dice');
      setTimeout(render, 440 / (S.settings.speed || 1));
      return 760;
    }
    case 'fact': {
      C.hitBy = null;
      if (C.tray?.fid !== f.f) C.tray = null;
      C.caption = null;
      if (f.ik !== 'dazed') sfx.play('swing');
      // the enemy's move plays out (skillfx.js foeFx): a lunge or a shot at whoever it aims at
      const fo = foe('f' + f.f), it = fo?.intent;
      if (!fo || !it || f.ik === 'dazed' || !S.settings.speed) { flash('f' + f.f, 'act'); return 300; }
      const party = [...(d.heroes || []).filter(y => !d.hs[y]?.down && !d.hs[y]?.fled).map(y => 'h' + y), ...(d.allies || []).filter(a => a.hp > 0).map(a => 's' + a.id)];
      const tgts = it.k === 'all' ? party : (it.tgts || (it.tgt ? [it.tgt] : [])).filter(u => typeof u === 'string' && (u.startsWith('f') || party.includes(u)));
      const ms = foeFx(fxKit('f' + f.f, tgts, false, d), fo, it, m => flash('f' + f.f, 'f-' + m, FOE_MOTION_MS[m] || 360));
      return Math.max(300, ms || 0);
    }
    case 'dmg': {
      if (f.n > 0) {
        if (f.to.startsWith('h')) { const x = +f.to.slice(1); noteLag(f.to, C.hp[x] ?? 0, C.maxhp?.[x] ?? S.game.heroes[x].maxhp); }
        else { const fo = foe(f.to); if (fo) noteLag(f.to, fo.hp, fo.max); }
      }
      if (f.to.startsWith('h')) { const x = +f.to.slice(1); C.hp[x] = (C.hp[x] ?? 0) - f.n; }
      else if (f.to.startsWith('s')) { const al = ally(f.to); if (al) al.hp -= f.n; }
      else { const fo = foe(f.to); if (fo) { fo.hp -= f.n; if (fo.hp <= 0) fo.dying = true; } }
      // Armor takes the hit first: it chips off in shards, then the rest reaches the health bar
      if (f.block) { addFloat(f.to, `◆${f.block}`, 'arm'); fxAt(f.to, 'shards' + (f.n ? '' : ' full'), 560); }
      // a big hit: 12 or more, or 40% of its health (at least 8)
      const max = f.to.startsWith('h') ? S.game.heroes[+f.to.slice(1)].maxhp : (foe(f.to) || ally(f.to))?.max || 99;
      const big = f.n >= 12 || (f.n >= 8 && f.n >= max * 0.4);
      if (f.n > 0 || !f.block) addFloat(f.to, big ? `−${f.n}!` : `−${f.n}`, big ? 'dmg.big' : 'dmg');
      flash(f.to, big ? 'bighit' : 'hit', big ? 420 : 300);
      if (big) { flash('stage', 'shake', 380); sfx.play('crit'); } else sfx.play(f.n > 0 ? 'hit' : 'block');
      // a hero's blow throws sparks off what it hits; a cooldown skill's are bigger, in its class's colour
      if (C.hitBy && f.n > 0 && !f.to.startsWith('h') && S.settings.speed) {
        const hb = C.hitBy;
        fxSparks(f.to, hb.big ? hb.c : '#fff4d8', { n: hb.big ? (big ? 18 : 11) : 6, r: hb.big ? 84 : 52, dir: 0, cone: 200 });
        if (hb.big && big) { fxAt(f.to, 'shock big', 640, hb.c); flash('stage', 'punch', 240); }
      }
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
      // Chord, an elemental reaction or a Break: a banner across the screen and its own effect
      const name = S.static.combos?.[f.c]?.name || { bell: 'Bell cracked' }[f.c] || f.c;
      addFloat(f.to, f.n ? `${name}! +${f.n}` : `${name}!`, 'combo');
      sfx.play('rare');
      const look = COMBO_LOOK[f.c];
      if (!look || !S.settings.speed) return 420;
      fxCutin(f.c === 'chord' ? `Chord ×${f.lvl || 2}` : name, look.sub, look.c, 760);
      look.fx(f.to, look.c);
      return 760;
    }    case 'st': {
      if (f.s === 'crit') {
        // a crit: a gold callout over the hero, and the stage gives a jolt
        addFloat(f.to, 'Crit!', 'crit');
        flash(f.to, 'critfx', 520);
        sfx.play('crit');
        return 360;
      }
      if (f.s === 'echo') {
        // an Echo die copies the play that just happened: a link from that hero to this one
        const src = C.lastHero;
        if (src != null && 'h' + src !== f.to) fxLine('h' + src, f.to, 'echo', 900);
        addFloat(f.to, 'Echo!', 'txt');
        flash(f.to, 'echoed', 700);
        return 360;
      }
      const name = STATUS[f.s]?.name || ST_FLOAT[f.s] || f.s;
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
    case 'sact': C.hitBy = null; C.tray = null; C.caption = null; flash('s' + f.s, 'act'); sfx.play('swing'); return 300;
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
