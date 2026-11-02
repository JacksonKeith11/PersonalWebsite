// The run's HTML over the map: top bar, party cards, the action bar, the log, the town and hero
// drawers, dialogs (events, loot, level-ups), first-time hints, and wiring the map's clicks.
import { S, send, mine, controllerName, isOnline, saved, persist } from './store.js?v=49';
import { $, h, icon, toast, modal, hideTip, bigBanner } from './ui.js?v=49';
import { spriteURL } from './art.js?v=49';
import { reach, routeTo, terrain, TERRAIN_NAME, dieLabel, dieTip, faceText, faceTip, KIND_TEXT, reqText, visibleTiles, dist as hexDist, expected } from './rules.js?v=49';
import { MapView } from './hexmap.js?v=49';
import { renderCombat, combatFx, combatOpen, showFight, hpClass, reqBadge } from './combat.js?v=49';
import { disconnect } from './main.js?v=49';
import * as sfx from './audio.js?v=49';

const UI = { drawer: null, log: true, outcomes: [], hover: -1, preview: null, menu: false };
let root = null, map = null, mapWorld = null;

export function teardownGame() {
  if (map) { map.destroy(); map = null; }
  root = null; mapWorld = null;
  UI.drawer = null; UI.outcomes = [];
}

const seat = h => `var(--hero-${h})`;
const cls = k => S.static.classes[k];
const actionDef = k => S.static.actions[k.replace(/\+$/, '')];
const skillDef = k => S.static.actions[k.replace(/\+$/, '')] || S.static.passives[k.replace(/\+$/, '')];
const item = k => S.static.items[k];

function sel() { return S.sel; }
function selHero() { return S.game.heroes[sel()]; }
function canPlan(h) {
  const g = S.game;
  if (!g.plans[h] || !g.heroes[h].alive) return false;
  if (g.phase === 'plan') return true;
  if (g.phase === 'fork') return !g.fork?.heroes.includes(h);
  return (g.phase === 'fight' || g.phase === 'reward') && !(g.fight && g.fight.heroes.includes(h));
}
function inTown(h) { const p = S.game.places[S.game.heroes[h].tile]; return p && p.kind === 'town' ? p : null; }

// ------------------------------------------------------------------ building the screen
export function renderGame() {
  const g = S.game;
  if (!root || mapWorld !== S.world) {
    teardownGame();
    root = h('div.game', null,
      h('div.map#map'),
      h('div#topbar'), h('div#party.party'), h('div#forecast'), h('div#actionbar'), h('div#log'), h('div#hint'),
      h('div.zoom', null,
        h('button.btn.icon', { 'aria-label': 'Zoom in', tip: 'Zoom in\nOr use the mouse wheel', onclick: () => map?.zoomBy(1) }, icon('plus')),
        h('button.btn.icon', { 'aria-label': 'Zoom out', tip: 'Zoom out', onclick: () => map?.zoomBy(-1) }, h('span', { style: { fontSize: '20px', lineHeight: 1 } }, '−')),
        h('button.btn.icon', { 'aria-label': 'Find my hero', tip: 'Find my hero', onclick: () => map?.centerOn(selHero().tile) }, icon('target'))),
      h('div#drawer'), h('div#modal'), h('div#combat'), h('div#hextip.hextip', { hidden: true }), h('div#menu'));
    $('app').replaceChildren(root);
    mapWorld = S.world;
    map = new MapView($('map'), S.world, { click: onTileClick, hover: onTileHover });
    map.centerOn(g.heroes[sel()]?.tile ?? S.world.start, false);
  }
  updateMap();
  renderTopbar();
  renderParty();
  renderActionbar();
  renderForecast();
  renderLog();
  renderDrawer();
  renderDialogs();
  renderHint();
  renderMenu();
  renderCombat($('combat'));
}

function updateMap() {
  const g = S.game, h0 = sel();
  const planning = mine().includes(h0) && canPlan(h0) && !g.plans[h0]?.ready && !g.pending[h0]?.length;
  map.setState(g, { sel: h0, mine: mine(), reach: planning ? reach(S.world, g, S.static, h0) : null, preview: UI.preview });
}

// ------------------------------------------------------------------ map input
function onTileClick(t) {
  const g = S.game, h0 = sel();
  if (combatOpen()) return;
  if (!mine().includes(h0)) return;
  if (!canPlan(h0)) { toast('Not now: wait for the fight to finish.'); return; }
  if (g.pending[h0]?.length) { toast('Answer what’s in front of you first.'); return; }
  if (g.plans[h0].ready) { toast('Unready to change your route.'); return; }
  const hero = g.heroes[h0];
  if (t === hero.tile) { send({ t: 'path', h: h0, path: [] }); UI.preview = null; return; }
  const r = reach(S.world, g, S.static, h0);
  const path = routeTo(r, t);
  if (!path || !path.length) { toast(S.game.seen[t] === '1' ? 'You can’t reach that hex this turn.' : 'You can’t see that far.'); sfx.play('error'); return; }
  send({ t: 'path', h: h0, path });
  UI.preview = null;
  sfx.play('click');
}

function onTileHover(t, x, y) {
  const tip = $('hextip');
  if (!tip) return;
  if (t < 0 || t === undefined) { tip.hidden = true; if (UI.preview) { UI.preview = null; updateMap(); } return; }
  const g = S.game, h0 = sel();
  const seen = g.seen[t] === '1';
  const lines = [];
  if (!seen) lines.push(h('b', null, 'Unexplored'), h('div', null, 'Get closer to see what’s there.'));
  else {
    const ter = terrain(S.world, g, t);
    const p = g.places[t];
    const regions = S.static.regions;
    lines.push(h('b', null, placeTitle(p) || TERRAIN_NAME[ter] || ter));
    if (p) lines.push(h('div', null, placeText(p)));
    lines.push(h('div.muted', null, `${TERRAIN_NAME[ter] || ter}${S.world.reg[t] ? ' · ' + regions[S.world.reg[t]] : ''}`));
    const vis = visibleTiles(g);
    const gr = g.groups.find(x => x.tile === t);
    if (gr && (vis.has(t) || gr.lair)) lines.push(h('div', { style: { color: 'var(--danger)' } }, (gr.lair ? 'Lair: ' : 'Enemies: ') + gr.foes.map((k, i) => foeName(k, gr.aff?.[i])).join(', ')));
    if (p?.kind === 'dungeon' && !g.cleared?.includes(p.region) && g.dnext?.[p.region]) {
      const nx = g.dnext[p.region], step = (g.dungeon?.[p.region] || 0) + 1;
      lines.push(h('div', { style: { color: 'var(--danger)' } }, `Fight ${step} of 3 (${S.static.paths[nx.path]?.name || ''}): ` + nx.foes.map(x => typeof x === 'string' ? foeName(x) : foeName(x.k, x.aff)).join(', ')));
    }
    const heroesHere = g.heroes.filter(x => x.alive && x.tile === t).map(x => x.name);
    if (heroesHere.length) lines.push(h('div', null, heroesHere.join(', ')));
  }
  if (mine().includes(h0) && canPlan(h0) && !g.plans[h0].ready) {
    const r = reach(S.world, g, S.static, h0);
    const b = r.best.get(t);
    if (b && t !== g.heroes[h0].tile) {
      lines.push(h('div.cost', null, `${b.cost} of ${g.heroes[h0].moves} moves`));
      const vis2 = visibleTiles(g);
      const gr = g.groups.find(x => x.tile === t && vis2.has(t));
      const near = g.heroes.map((x, i) => i).filter(i => i !== h0 && g.heroes[i].alive && g.forecast?.ends[i] !== undefined && hexDist(g.forecast.ends[i], t) <= 1).map(i => g.heroes[i].name);
      if (gr) lines.push(h('div', { style: { color: 'var(--danger)' } }, `Walking in starts the fight.${near.length ? ` ${near.join(' and ')} would join (within a hex).` : ' Nobody else is close enough to join.'}`));
      else if (g.groups.some(x => vis2.has(x.tile) && !x.lair && hexDist(x.tile, t) <= 1)) lines.push(h('div', { style: { color: 'var(--warn, #e0a050)' } }, 'Next to enemies: they may step onto you.'));
      const path = routeTo(r, t);
      if (JSON.stringify(path) !== JSON.stringify(UI.preview)) { UI.preview = path; updateMap(); }
    } else if (UI.preview) { UI.preview = null; updateMap(); }
  }
  tip.replaceChildren(...lines);
  tip.hidden = false;
  const tr = tip.getBoundingClientRect();
  tip.style.left = Math.min(innerWidth - tr.width - 12, x + 16) + 'px';
  tip.style.top = Math.min(innerHeight - tr.height - 12, y + 16) + 'px';
}

function placeTitle(p) {
  if (!p) return null;
  const st = S.static;
  return {
    town: p.name, dungeon: st.dungeons[p.region], peak: 'The Drowned Peak', shrine: 'Shrine', camp: 'Camp', event: 'Something curious',
    wreck: 'Wreck', lair: 'Lair',
  }[p.kind];
}
function placeText(p) {
  const g = S.game;
  switch (p.kind) {
    case 'town': return 'Shop, inn and notice board' + (p.docks ? ', with docks for skiffs.' : '.');
    case 'dungeon': return g.cleared.includes(p.region) ? 'Cleared.' : `An objective: ${3 - (g.dungeon[p.region] || 0)} fights deep, the way forking between them. No retreat.`;
    case 'peak': return g.cleared.length >= 3 ? 'The Drowned Crown waits at the top.' : `Sealed until all three objectives are cleared (${g.cleared.length} of 3).`;
    case 'shrine': return 'A blessing, once for each hero.';
    case 'camp': return 'Rest here to heal half your HP.';
    case 'event': return p.done ? 'Already seen to.' : 'Step on it to find out.';
    case 'wreck': return p.done ? 'Picked clean.' : 'Loot, for whoever gets there first.';
    case 'lair': return p.done ? 'Cleared.' : 'A nest of tougher enemies, guarding good loot.';
  }
  return '';
}

// ------------------------------------------------------------------ top bar
function renderTopbar() {
  const g = S.game;
  const xpPct = g.xp_next ? Math.round(100 * (g.xp - g.xp_this) / (g.xp_next - g.xp_this)) : 100;
  $('topbar').replaceChildren(h('div.topbar', null,
    h('div.logo', null, 'Salt', h('span', null, 'bound')),
    h('div.stats', null,
      h('div.stat', { tip: `Turn ${g.turn}\nEveryone plans, then everyone moves at once.` }, h('span.lbl', null, 'Turn'), h('b', null, g.turn)),
      h('div.stat.opt', { tip: `${g.tide === 'low' ? 'Low' : 'High'} tide\n${g.tide === 'low' ? 'Sandbars and shallows are walkable.' : 'Shallows are under water: skiffs only.'}\nTurns in ${g.next_tide} turn${g.next_tide === 1 ? '' : 's'}.` },
        icon('moon'), h('b', null, g.tide === 'low' ? 'Low tide' : 'High tide'), h('span.lbl', null, `· ${g.next_tide}`)),
      h('div.stat' + (g.rises >= g.grow_from ? '.warn' : ''), { tip: `The rising tide\nRises every ${g.rise_every} turns, next in ${g.next_rise}. Each rise makes every enemy stronger (HP and damage).\nRisen ${g.rises} time${g.rises === 1 ? '' : 's'}: enemies are ${g.surge}% stronger.${g.rises >= g.grow_from ? '\nMore enemies come ashore with every rise now.' : ''}` },
        icon('wave'), h('b', null, `Enemies +${g.surge}%`), h('span.lbl', null, `· rises in ${g.next_rise}`)),
      h('div.stat', { tip: `Party level ${g.level}\n${g.xp_next ? `${g.xp} / ${g.xp_next} XP` : 'Max level'}\nXP is shared: everyone levels together.` },
        icon('star'), h('b', null, `Level ${g.level}`), h('div.xpbar', null, h('i', { style: { width: xpPct + '%' } }))),
      h('div.stat', { tip: 'Revives\nShared by the party. A knocked-down hero who’s still down at the end of a fight uses one.' },
        icon('feather'), h('b', null, g.revives)),
      h('div.stat', { tip: `Objectives\n${['coral', 'keys', 'storm'].map(r => `${S.static.dungeons[r]}: ${g.cleared.includes(r) ? 'cleared' : 'not yet'}`).join('\n')}` },
        icon('flag'), h('span.pips', null, ...[0, 1, 2].map(i => h('i' + (i < g.cleared.length ? '.on' : '')))))),
    h('div.right', null,
      h('button.btn.icon.ghost', { 'aria-label': 'Log', tip: 'Log', onclick: () => { UI.log = !UI.log; renderLog(); } }, icon('list')),
      h('button.btn.icon.ghost', { 'aria-label': 'Menu', tip: 'Menu', onclick: () => { UI.menu = !UI.menu; UI.menuFresh = true; renderMenu(); } }, icon('menu')))));
}

// ------------------------------------------------------------------ party cards
function heroState(h0) {
  const g = S.game, hero = g.heroes[h0];
  if (!hero.alive) return ['Fallen', ''];
  if (!isOnline(h0)) return ['Disconnected', 'off'];
  if (g.fight && g.fight.heroes.includes(h0)) return ['In a fight', 'wait'];
  if (g.pending[h0]?.length) return [{ event: 'Reading an event', loot: 'Picking loot', pool: 'Claiming loot', level: 'Levelling up' }[g.pending[h0][0].type], 'wait'];
  const p = g.plans[h0];
  if (g.phase === 'plan' && p) return p.ready ? ['Ready', 'ready'] : p.rest ? ['Resting', ''] : ['Planning', ''];
  return ['', ''];
}

function renderParty() {
  const g = S.game, my = mine(), host = S.room.host === S.you;
  $('party').replaceChildren(...g.heroes.map((hero, i) => {
    const [stTxt, stCls] = heroState(i);
    const pct = Math.max(0, Math.round(100 * hero.hp / hero.maxhp));
    const card = h('div.hero-card' + (i === sel() ? '.sel' : '') + (hero.alive ? '' : '.dead'), {
      style: { '--seat': seat(i) },
      // your hero: select it; an ally: open their sheet (skills first) to see what they can do
      onclick: () => {
        if (my.includes(i)) { S.sel = i; UI.preview = null; if (UI.drawer?.who != null) UI.drawer = null; renderGame(); }
        else openDrawer('hero', 'skills', i);
        map.centerOn(hero.tile);
      },
      tip: my.includes(i) ? null : `${hero.name}\nClick to see their skills and gear.`,
    },
      h('div.hero-top', null,
        h('img.pix', { src: spriteURL(hero.cls), alt: '' }),
        h('div.who', null, h('b', null, hero.name), h('span', null, `${cls(hero.cls).name} · ${controllerName(i)}${my.includes(i) ? ' (you)' : ''}`)),
        h('span.hero-state.' + (stCls || 'x'), null, stTxt)),
      h('div.bar' + hpClass(hero.hp, hero.maxhp), null, h('i', { style: { width: pct + '%' } }), h('span', null, `${Math.max(0, hero.hp)} / ${hero.maxhp}`)),
      h('div.hero-meta', null,
        h('span', { tip: 'Gold' }, icon('coin'), hero.gold),
        h('span', { tip: 'Moves per turn' }, icon('boot'), hero.moves),
        hero.skiff ? h('span', { tip: 'Has a skiff: can cross open water' }, icon('sail'), 'Skiff') : null,
        Object.keys(hero.buffs).length ? h('span', { tip: Object.keys(hero.buffs).map(b => `${S.static.buffs[b].name}: ${S.static.buffs[b].text} (${hero.buffs[b]} turns)`).join('\n') }, icon('spark'), Object.keys(hero.buffs).length) : null),
      h('div.mini-dice', null, ...hero.dice.map(d => h('span.mini-die', { tip: dieTip(d) }, dieLabel(d)))),
      host && !isOnline(i) && hero.alive ? h('button.btn.sm', { onclick: e => { e.stopPropagation(); reassign(i); } }, 'Hand to someone') : null);
    return card;
  }));
}

function reassign(h0) {
  const r = S.room;
  const others = r.people.filter(p => p.on);
  const box = modal([
    h('h2', null, `Who plays ${S.game.heroes[h0].name}?`),
    h('p.lead', null, `${controllerName(h0)} is disconnected. The voyage waits for them, or someone here can take over.`),
    h('div.choices', null, ...others.map(p => h('button.choice', { onclick: () => { send({ t: 'assign', h: h0, pid: p.id }); box.remove(); } }, h('span.grow', null, p.name)))),
    h('button.btn.ghost', { onclick: () => box.remove() }, 'Keep waiting'),
  ], { onClose: () => box.remove() });
  document.body.append(box);
}

// ------------------------------------------------------------------ action bar
function renderActionbar() {
  const g = S.game, h0 = sel(), hero = g.heroes[h0];
  const el = $('actionbar');
  if (!mine().includes(h0) || g.phase === 'end') { el.replaceChildren(); return; }
  if (g.fight && g.fight.heroes.includes(h0)) { el.replaceChildren(); return; }
  const p = g.plans[h0];
  const town = inTown(h0);
  let title, sub;
  const btns = [];
  if (!hero.alive) {
    title = `${hero.name} has fallen`;
    sub = g.revives > 0 ? 'They’ll be back next turn: the party has a revive.' : 'Give your spirit die to an ally in fights.';
  } else if (g.pending[h0]?.length) {
    title = 'Something needs your answer'; sub = 'Choose in the dialog to carry on.';
  } else if (g.phase === 'fork') {
    title = 'The party in the dungeon is picking a path';
    sub = 'Plan your next move or visit a town while you wait.';
  } else if (g.phase === 'fight' || g.phase === 'reward') {
    title = g.phase === 'fight' ? 'A fight is under way' : 'Waiting for picks';
    sub = 'Plan your next move or visit a town while you wait.';
    if (g.phase === 'fight') btns.push(h('button.btn', { onclick: showFight }, icon('eye'), 'Watch the fight'));
  } else if (p?.ready) {
    const waiting = g.waiting.filter(x => x !== h0).map(x => g.heroes[x].name);
    title = 'Ready'; sub = waiting.length ? `Waiting for ${waiting.join(', ')}` : 'Setting off…';
  } else if (p?.rest) {
    title = `${hero.name} will rest`;
    sub = restText(h0);
  } else if (p?.path.length) {
    title = `Route set · ${p.path.length} hex${p.path.length === 1 ? '' : 'es'}`; sub = 'Click another hex to change it, or your own to stay.';
  } else {
    title = `Plan ${hero.name}’s move`; sub = `${hero.moves} moves · click a lit hex to plan a route`;
  }
  if (hero.alive && !g.pending[h0]?.length && p) {
    if (g.phase === 'plan' || canPlan(h0)) {
      if (!p.ready) btns.push(h('button.btn' + (p.rest ? '.primary' : ''), { tip: `Rest\n${restText(h0)}`, onclick: () => send({ t: 'rest', h: h0, on: !p.rest }) }, icon('rest'), p.rest ? 'Resting' : 'Rest'));
      if (town) btns.push(h('button.btn', { onclick: () => openDrawer('town') }, icon('anchor'), town.name));
    }
    btns.push(h('button.btn', { onclick: () => openDrawer('hero'), tip: 'Hero sheet\nDice, actions, gear and bag' }, icon('bag'), 'Hero'));
    if (g.phase === 'plan') {
      btns.push(p.ready
        ? h('button.btn', { onclick: () => send({ t: 'ready', h: h0, on: false }) }, 'Unready')
        : h('button.btn.primary.lg', { onclick: () => send({ t: 'ready', h: h0 }) }, icon('check'), 'Ready', h('span.kbd', null, 'Space')));
    }
  } else if (hero.alive) {
    btns.push(h('button.btn', { onclick: () => openDrawer('hero') }, icon('bag'), 'Hero'));
  }
  el.replaceChildren(h('div.actionbar', null,
    h('div.hint', null, h('b', null, title), h('span', null, sub)),
    btns.length ? h('div.sep') : null, ...btns));
}

// ------------------------------------------------------------------ what the planned turn will do
// The server works the turn out from what the party can see (Game.forecast): one line per hero, so
// everyone knows who's walking into what, who gets pulled into a fight, and where enemies will step.
const LAND = { event: 'finds something curious', wreck: 'loots a wreck', shrine: 'gets a shrine’s blessing', town: 'reaches town', camp: 'reaches a camp', lair: 'reaches a lair' };
// An enemy's name, with its elite affix ("Hulking Crabfolk Brute").
export function foeName(k, aff) {
  const st = S.static;
  return (aff && st.elites?.[aff] ? st.elites[aff].name + ' ' : '') + (st.foes[k]?.name || k);
}
function fightLine(f) {
  const st = S.static, g = S.game;
  const counts = {};
  f.foes.forEach((k, i) => { const n = foeName(k, f.aff?.[i]); counts[n] = (counts[n] || 0) + 1; });
  const foes = Object.entries(counts).map(([n, c]) => n + (c > 1 ? ` ×${c}` : '')).join(', ');
  const where = f.kind === 'dungeon' ? `${st.dungeons[f.region]} (fight ${f.step + 1} of 3)` : f.kind === 'boss' ? 'the Drowned Crown' : f.kind === 'lair' ? `a lair: ${foes}` : foes;
  return { where, with: f.heroes.map(x => g.heroes[x].name) };
}
export function renderForecast() {
  const el = $('forecast');
  if (!el) return;
  const g = S.game, fc = g.forecast;
  if (!fc || g.phase !== 'plan' || combatOpen()) { el.replaceChildren(); return; }
  const lines = [];
  g.heroes.forEach((hero, x) => {
    if (!hero.alive) return;
    const p = g.plans[x] || {};
    const fight = fc.fights.find(f => f.heroes.includes(x));
    let text;
    if (fight) {
      const fl = fightLine(fight);
      const others = fl.with.filter(n => n !== hero.name);
      text = fight.by === x ? `walks into a fight: ${fl.where}` : fight.by == null ? `is caught by ${fl.where}` : `is pulled into the fight: ${fl.where}`;
      if (others.length) text += ` · with ${others.join(', ')}`;
    } else if (p.rest) text = 'rests';
    else if (fc.lands[x]) text = LAND[fc.lands[x]] || 'arrives';
    else if (p.path?.length) text = 'moves';
    else text = p.ready ? 'stays put' : 'hasn’t planned yet';
    lines.push(h('div.fc-line' + (fight ? '.fight' : ''), { style: { '--seat': seat(x) } },
      h('i.dot'), h('b', null, hero.name), h('span', null, ' ' + text), p.ready ? h('span.ok', null, ' ✓') : null));
  });
  const steps = fc.steps.length;
  if (steps) lines.push(h('div.fc-line.muted', null, icon('skull'), ` ${steps} enemy group${steps > 1 ? 's' : ''} will step toward you (red arrows).`));
  el.replaceChildren(h('div.forecast', { role: 'status', 'aria-live': 'polite' }, h('span.eyebrow', null, 'This turn'), ...lines,
    h('div.fc-foot', null, 'Hidden enemies can still ambush you.')));
}

function restText(h0) {
  const g = S.game, hero = g.heroes[h0];
  const p = g.places[hero.tile];
  const medic = g.heroes.some(x => x.alive && x.tile === hero.tile && cls(x.cls).map.key === 'field_medic');
  const camp = p && p.kind === 'camp';
  const frac = Math.min(1, (camp ? 0.5 : 0.2) + (medic ? 0.1 : 0));
  return `Spend the turn resting: heal ${Math.round(hero.maxhp * frac)} HP${medic ? ' (with the Field Medic)' : ''}${camp ? '' : ' (more at a camp)'}.`;
}

// ------------------------------------------------------------------ log
function renderLog() {
  const g = S.game;
  const el = $('log');
  if (!UI.log) { el.replaceChildren(); return; }
  const list = h('div.loglist', null, ...g.log.slice().reverse().map(l => h('div', null, h('span.t', null, `T${l.t}`), l.m)));
  el.replaceChildren(h('div.logpanel', null,
    h('header', null, h('span.eyebrow', null, 'Voyage log'), h('button.btn.icon.ghost.sm', { 'aria-label': 'Hide log', onclick: () => { UI.log = false; renderLog(); } }, icon('x'))),
    list));
}

// ------------------------------------------------------------------ menu
function renderMenu() {
  const el = $('menu');
  if (!UI.menu) { el.replaceChildren(); return; }
  const host = S.room.host === S.you;
  const close = () => { UI.menu = false; renderMenu(); };
  const speed = [[1, '1×'], [2, '2×'], [0, 'Instant']];
  el.replaceChildren(modal([
    h('h2', null, 'Menu'),
    h('div.field', null, 'Animation speed', h('div.seg', null, ...speed.map(([v, l]) => h('button', {
      'aria-pressed': String(S.settings.speed === v), onclick: () => { S.settings.speed = v; saved.settings = S.settings; persist(); renderMenu(); },
    }, l)))),
    h('label.field', null, `Sound effects`, h('input', {
      type: 'range', min: 0, max: 1, step: 0.05, value: S.settings.volume,
      oninput: e => { S.settings.volume = +e.target.value; sfx.setVolume(S.settings.volume); saved.settings = S.settings; persist(); },
    })),
    h('label.field', null, `Music`, h('input', {
      type: 'range', min: 0, max: 1, step: 0.05, value: S.settings.music ?? 0.5,
      oninput: e => { S.settings.music = +e.target.value; sfx.setMusicVolume(S.settings.music); saved.settings = S.settings; persist(); },
    })),
    h('p.muted', null, `Room ${S.code}. The voyage saves itself after every turn and every round of a fight.`),
    h('div.keys', null, h('b', null, 'Keys'),
      h('span', null, h('span.kbd', null, 'Space'), ' ready up'),
      h('span', null, h('span.kbd', null, '1'), '–', h('span.kbd', null, '9'), ' pick a die, or a choice in a dialog'),
      h('span', null, h('span.kbd', null, 'Q'), h('span.kbd', null, 'W'), h('span.kbd', null, 'E'), '… pick an action (a fight)'),
      h('span', null, h('span.kbd', null, 'Esc'), ' close or cancel')),
    h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap' } },
      host ? h('button.btn', { onclick: () => { if (confirm('Save and take everyone back to the lobby?')) { send({ t: 'quit' }); close(); } } }, 'Save and return to lobby') : null,
      h('button.btn.ghost', { onclick: () => { if (confirm('Leave this voyage? It’s saved, and you can rejoin with the room code.')) disconnect(); } }, 'Leave'),
      h('button.btn.primary', { style: { marginLeft: 'auto' }, onclick: close }, 'Close')),
  ], { onClose: close, enter: !!UI.menuFresh }));
  UI.menuFresh = false;
}

// ------------------------------------------------------------------ drawers
// `who`: the hero whose sheet to show (default the selected one); an ally's sheet is read-only.
function openDrawer(kind, tab, who) {
  UI.drawer = { kind, tab: tab || (kind === 'town' ? 'market' : 'gear'), enter: true, who };
  renderDrawer();
}
function closeDrawer() { UI.drawer = null; renderDrawer(); }

function renderDrawer() {
  drawDrawer();
  // the action bar slides left so the drawer doesn't cover Ready
  document.body.classList.toggle('drawer-open', $('drawer').childElementCount > 0);
}
function drawDrawer() {
  const el = $('drawer');
  const d = UI.drawer;
  if (!d || combatOpen()) { el.replaceChildren(); return; }
  const h0 = d.kind === 'hero' && d.who != null ? d.who : sel(), hero = S.game.heroes[h0];
  if (d.kind === 'hero' && !mine().includes(h0)) { el.replaceChildren(heroDrawer(h0, d, true)); return; }
  if (!mine().includes(h0) || !hero.alive) { el.replaceChildren(); return; }
  if (d.kind === 'town') {
    const town = inTown(h0);
    if (!town) { UI.drawer = null; el.replaceChildren(); return; }
    el.replaceChildren(townDrawer(h0, town, d));
  } else {
    el.replaceChildren(heroDrawer(h0, d));
  }
}

function tabs(d, list) {
  return h('div.tabs', { role: 'tablist' }, ...list.map(([k, label]) => h('button', {
    role: 'tab', 'aria-selected': String(d.tab === k), onclick: () => { d.tab = k; renderDrawer(); },
  }, label)));
}

function drawerShell(title, sub, tabList, d, body) {
  const enter = d.enter;
  d.enter = false;
  return h('div.drawer' + (enter ? '.enter' : ''), { role: 'dialog' },
    h('header', null, h('div', { style: { flex: 1 } }, h('div.eyebrow', null, sub), h('h2', null, title)),
      h('button.btn.icon.ghost', { 'aria-label': 'Close', onclick: closeDrawer }, icon('x'))),
    tabList ? tabs(d, tabList) : null,
    h('div.body', null, body));
}

const SLOT_ICON = { weapon: 'sword', armor: 'shield', trinket: 'star', trinket2: 'star', use: 'drop' };
const SLOTS = ['weapon', 'armor', 'trinket', 'trinket2'];
// The equipment slots an item of this kind can go in (two for trinkets), and the first empty one.
const slotsFor = slot => (slot === 'trinket' ? ['trinket', 'trinket2'] : [slot]);
const freeSlot = (hero, slot) => slotsFor(slot).find(s => !hero.equip[s]);
// The slot a new item would replace when all its slots are full: the lesser item, by rarity.
const RAR = ['common', 'uncommon', 'rare', 'legendary'];
function swapSlot(hero, slot) {
  return slotsFor(slot).reduce((a, b) => (RAR.indexOf(item(hero.equip[b]).rarity) < RAR.indexOf(item(hero.equip[a]).rarity) ? b : a));
}
// "Put it on" buttons: one, or for a trinket with both slots full, one per trinket it could replace.
function wearButtons(hero, key, send1, primary = true) {
  const it = item(key);
  if (it.slot !== 'trinket' || freeSlot(hero, 'trinket')) return [h('button.btn.sm' + (primary ? '.primary' : ''), { onclick: () => send1(undefined) }, 'Put it on')];
  return ['trinket', 'trinket2'].map((s, i) => h('button.btn.sm' + (primary && i === 0 ? '.primary' : ''), { onclick: () => send1(s), tip: `Wear it instead of the ${item(hero.equip[s]).name} (that goes in your bag)` }, `Swap for ${item(hero.equip[s]).name}`));
}
// What the hero would get for selling an item in a town (40% of its price, 60% with Haggler).
function sellValue(key, h0 = sel()) {
  return Math.floor(S.static.prices[key] * (S.game.heroes[h0]?.sellrate ?? 40) / 100);
}
function sellChip(key, h0) {
  return h('span.sells', { tip: 'What a town pays for it' }, icon('coin'), `sells ${sellValue(key, h0)}`);
}
function itemRow(key, right, extra) {
  const it = item(key);
  const sub = [];
  if (it.slot !== 'use') sub.push(it.slot[0].toUpperCase() + it.slot.slice(1));
  // a long die (8+ faces) gets its own line rather than wrapping after a dangling separator
  const long = it.die && it.die.length > 6;
  if (it.die && !long) sub.push(faceRow(it));
  sub.push(sellChip(key));
  return h('div.item.r-' + it.rarity, { tip: itemTip(key) },
    h('div.ico', null, icon(SLOT_ICON[it.slot] || 'spark')),
    h('div', null, h('div.name.rar-' + it.rarity, null, it.name), h('div.sub', null, ...interleave(sub, ' · ')),
      long ? h('div.sub', null, faceRow(it)) : null,
      it.text && it.slot !== 'use' ? h('div.passive', null, it.text) : null, extra || null),
    h('div.acts', null, right));
}
// A die's faces as little tiles, with its kinds (Seer, Fate...) in front.
function faceRow(it) {
  const kinds = (it.dk || []).filter(k => !k.startsWith('link:') && k !== 'top');
  return h('span.faces', { tip: dieTip({ faces: it.die, dk: it.dk || [] }) },
    ...kinds.map(k => h('span.chip.brass', { style: { height: '20px' }, tip: `${k[0].toUpperCase() + k.slice(1)} die\n${KIND_TEXT[k] || ''}` }, k[0].toUpperCase() + k.slice(1))),
    ...(it.die.every((f, i) => f === i + 1) ? [h('span.face', null, 'd' + it.die.length)]
      : it.die.map(f => h('span.face' + (f === 'S' ? '.s' : ''), typeof f === 'string' ? { tip: faceTip(f) } : null, faceText(f)))));
}
// What a hero has in an item's slot now, to compare against: its die (with the change in average),
// its actions and its passive. Null for consumables.
function compareWith(h0, key, compact) {
  const it = item(key);
  if (it.slot === 'use') return null;
  const hero = S.game.heroes[h0];
  if (freeSlot(hero, it.slot)) return h('div.compare.empty', null, h('span.cmp-lbl', null, 'Now'), `${it.slot === 'trinket' ? 'A trinket slot is free' : `No ${it.slot}`}: this fills an empty slot.`);
  const curKey = hero.equip[swapSlot(hero, it.slot)];
  if (curKey === key) return h('div.compare.same', null, h('span.cmp-lbl', null, 'Now'), 'You already wear one of these.');
  const cur = item(curKey);
  const avg = x => (x.die ? expected({ faces: x.die, dk: x.dk || [] }) : 0);
  const diff = avg(it) - avg(cur);
  const acts = (cur.acts || []).map(a => S.static.actions[a].name);
  const lost = (cur.acts || []).filter(a => !(it.acts || []).includes(a)).map(a => S.static.actions[a].name);
  return h('div.compare', null,
    h('span.cmp-lbl', null, 'Now'),
    h('b.rar-' + cur.rarity, null, cur.name), cur.die ? faceRow(cur) : null,
    it.die && cur.die ? h('span.cmp-diff' + (diff > 0.05 ? '.up' : diff < -0.05 ? '.down' : ''), { tip: 'Change in the die’s average roll' },
      diff > 0.05 ? `▲ +${diff.toFixed(1)} avg` : diff < -0.05 ? `▼ ${diff.toFixed(1)} avg` : '= same avg') : null,
    !compact && acts.length ? h('span.cmp-acts', null, `Actions: ${acts.join(', ')}${lost.length ? ` (you'd lose ${lost.join(', ')})` : ''}`) : null,
    compact && lost.length ? h('span.cmp-acts', null, `You'd lose ${lost.join(', ')}`) : null,
    !compact && cur.text ? h('span.cmp-pass', null, cur.text) : null);
}
function interleave(arr, sep) { return arr.flatMap((x, i) => (i ? [sep, x] : [x])); }
function itemTip(key) {
  const it = item(key);
  const lines = [it.name, `${it.rarity[0].toUpperCase() + it.rarity.slice(1)} ${it.slot === 'use' ? 'consumable' : it.slot}`];
  if (it.die) lines.push(...dieTip({ faces: it.die, dk: it.dk || [] }).split('\n'));
  for (const a of it.acts || []) { const ad = S.static.actions[a]; lines.push(`${ad.name} (${reqText(ad.req)}): ${ad.text}`); }
  if (it.mods) lines.push(modsText(it.mods));
  if (it.text) lines.push(it.text);
  return lines.filter(Boolean).join('\n');
}
function modsText(m) {
  const out = [];
  for (const [k, v] of Object.entries(m)) {
    out.push({ max_hp: `+${v} max HP`, heal_bonus: `+${v} to heals`, thorns: `Attackers take ${v}`, start_armor: `Start fights with ${v} Armor`, bomb_bonus: `+${v} bomb damage`,
      reroll: `+${v} reroll per fight`, move: `+${v} move`, might: `+${v} damage on every hit`, regen: `Regenerate ${v} HP a round in fights` }[k] || '');
  }
  return out.filter(Boolean).join(', ');
}

function townDrawer(h0, town, d) {
  const g = S.game, hero = g.heroes[h0];
  const disabled = !canPlan(h0);
  let body;
  if (d.tab === 'market') {
    body = [
      h('div.section-title', null, h('h3', null, 'For sale'), h('span.chip.brass', null, icon('coin'), hero.gold)),
      ...(town.shop || []).map(k => {
        const price = Math.floor(S.static.prices[k] * (g.herald ? 0.8 : 1));
        return itemRow(k, h('button.btn.sm' + (hero.gold >= price ? '.primary' : ''), { disabled: disabled || hero.gold < price, onclick: () => send({ t: 'buy', h: h0, item: k }) }, icon('coin'), price), compareWith(h0, k, true));
      }),
      g.herald ? h('p.muted', null, 'The Herald’s silver tongue knocks 20% off.') : null,
      hero.bag.length ? h('h3', null, 'Sell') : null,
      ...hero.bag.map((k, i) => itemRow(k, h('button.btn.sm', { disabled, onclick: () => send({ t: 'sell', h: h0, bag: i }) }, `Sell · ${sellValue(k, h0)}`))),
    ];
  } else if (d.tab === 'inn') {
    body = [h('h3', null, 'The inn'), h('p.muted', null, 'A hot meal and a dry bed. Heals you to full straight away.'),
      h('div', null, `HP ${hero.hp} / ${hero.maxhp}`),
      hero.hp >= hero.maxhp ? h('div.chip.brass', null, icon('check'), 'You’re at full health: no need for a room')
        : h('button.btn.primary', { disabled: disabled || hero.gold < g.inn, onclick: () => send({ t: 'inn', h: h0 }) }, icon('bed'), `Take a room · ${g.inn} gold`),
      hero.hp < hero.maxhp && hero.gold < g.inn ? h('p.muted', null, `You need ${g.inn - hero.gold} more gold.`) : null];
  } else if (d.tab === 'docks') {
    body = town.docks ? [h('h3', null, 'The docks'), h('p.muted', null, 'A skiff lets you cross open water. Boarding or landing costs a move; on water every hex costs 1.'),
      hero.skiff ? h('div.chip.brass', null, icon('check'), 'You have a skiff')
        : h('button.btn.primary', { disabled: disabled || hero.gold < g.skiff_cost, onclick: () => send({ t: 'skiff', h: h0 }) }, icon('sail'), `Buy a skiff · ${g.skiff_cost} gold`)]
      : [h('p.muted', null, 'No docks here.')];
  } else {
    const q = town.quest;
    const qText = q => q.kind === 'lair' ? 'Clear the lair marked on your map.' : `Deliver a parcel to ${q.name}.`;
    body = [h('h3', null, 'Notice board'),
      q ? h('div.card', { style: { padding: '16px', display: 'grid', gap: '10px' } }, h('b', null, 'Work going'), h('p', null, qText(q)),
        h('p.muted', null, '25 gold for every hero, and a choice of loot for whoever finishes it.'),
        h('button.btn.primary', { disabled, onclick: () => send({ t: 'quest', h: h0 }) }, 'Take the job')) : h('p.muted', null, 'Nothing pinned up today.'),
      g.quests.length ? h('h3', null, 'Your jobs') : null,
      ...g.quests.map(q2 => h('div.item', null, h('div.ico', null, icon(q2.done ? 'check' : 'scroll')), h('div', null, h('div.name', null, qText(q2)), h('div.sub', null, `For ${q2.src}${q2.done ? ' · done' : ''}`)), h('span')))];
  }
  return drawerShell(town.name, 'Town', [['market', 'Market'], ['inn', 'Inn'], ['docks', 'Docks'], ['board', 'Notice board']], d, body);
}

function heroDrawer(h0, d, readonly = false) {
  const g = S.game, hero = g.heroes[h0], c = cls(hero.cls);
  const town = inTown(h0);
  const free = !(g.fight && g.fight.heroes.includes(h0));
  let body;
  if (d.tab === 'gear' && readonly) {
    // an ally's gear, to look at
    body = [
      h('h3', null, 'Equipped'),
      ...SLOTS.map(slot => hero.equip[slot] ? itemRow(hero.equip[slot])
        : h('div.item.empty', null, h('div.ico', null, icon(SLOT_ICON[slot])), h('div', null, slot === 'trinket2' ? 'No second trinket' : `No ${slot}`))),
      h('div.section-title', null, h('h3', null, `Bag · ${hero.bag.length} item${hero.bag.length === 1 ? '' : 's'}`), h('span.chip.brass', null, icon('coin'), hero.gold)),
      ...hero.bag.map(k => itemRow(k)),
      !hero.bag.length ? h('p.muted', null, 'Their bag is empty.') : null,
    ];
  } else if (d.tab === 'gear') {
    const mates = g.heroes.map((x, i) => i).filter(i => i !== h0 && g.heroes[i].alive && g.heroes[i].tile === hero.tile);
    body = [
      h('h3', null, 'Equipped'),
      ...SLOTS.map(slot => hero.equip[slot]
        ? itemRow(hero.equip[slot], slot !== 'weapon' ? h('button.btn.sm.ghost', { disabled: !free, onclick: () => send({ t: 'unequip', h: h0, slot }) }, 'Take off') : null)
        : h('div.item.empty', null, h('div.ico', null, icon(SLOT_ICON[slot])), h('div', null, slot === 'trinket2' ? 'No second trinket' : `No ${slot}`))),
      h('div.section-title', null, h('h3', null, `Bag · ${hero.bag.length} item${hero.bag.length === 1 ? '' : 's'}`), h('span.chip.brass', null, icon('coin'), hero.gold)),
      ...hero.bag.map((k, i) => {
        const it = item(k);
        // the bag's buttons go in one row under the item, not squeezed into the right-hand column
        return itemRow(k, null, h('div.bag-acts', null,
          ...(it.slot === 'trinket' && !freeSlot(hero, 'trinket')
            ? ['trinket', 'trinket2'].map(sl => h('button.btn.sm', { disabled: !free, onclick: () => send({ t: 'equip', h: h0, bag: i, into: sl }) }, `Swap for ${item(hero.equip[sl]).name}`))
            : [it.slot !== 'use' ? h('button.btn.sm', { disabled: !free, onclick: () => send({ t: 'equip', h: h0, bag: i }) }, 'Equip') : null]),
          it.slot === 'use' && !it.fight ? h('button.btn.sm', { onclick: () => send({ t: 'use', h: h0, bag: i }) }, 'Use') : null,
          mates.length ? h('select.input.give', { 'aria-label': `Give ${it.name} to`, onchange: e => { if (e.target.value !== '') send({ t: 'give', h: h0, to: +e.target.value, bag: i }); } },
            h('option', { value: '' }, 'Give to…'), ...mates.map(m => h('option', { value: m }, g.heroes[m].name))) : null,
          town ? h('button.btn.sm.ghost', { onclick: () => send({ t: 'sell', h: h0, bag: i }) }, 'Sell') : null,
          h('button.btn.sm.ghost', { 'aria-label': 'Drop', tip: 'Throw it away', onclick: () => { if (confirm(`Throw away ${it.name}?`)) send({ t: 'drop', h: h0, bag: i }); } }, icon('x'), 'Drop')));
      }),
      !hero.bag.length ? h('p.muted', null, 'Your bag is empty.') : null,
      mates.length && hero.gold > 0 ? h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' } }, h('span.muted', null, 'Give 10 gold to'),
        ...mates.map(m => h('button.btn.sm', { disabled: hero.gold < 10, onclick: () => send({ t: 'give', h: h0, to: m, gold: 10 }) }, g.heroes[m].name))) : null,
    ];
  } else if (d.tab === 'skills') {
    const acts = hero.actions.filter(k => !['block', 'shift', 'flee'].includes(k));
    const weapon = hero.equip.weapon ? item(hero.equip.weapon) : null;
    const passives = hero.skills.filter(k => S.static.passives[k.replace(/\+$/, '')]);
    body = [
      h('h3', null, 'Actions'),
      ...acts.map(k => skillCard(k, (weapon?.acts || []).includes(k.replace(/\+$/, '')) ? weapon.name : null)),
      h('h3', null, 'Passives'),
      passives.length ? passives.map(k => skillCard(k)) : h('p.muted', null, 'None yet: pick them as you level up.'),
      h('h3', null, 'Always available'),
      skillCard('block'), skillCard('flee'),
    ];
  } else {
    body = [
      h('div', { style: { display: 'flex', gap: '16px', alignItems: 'center' } },
        h('img.pix', { src: spriteURL(hero.cls), alt: '', style: { width: '96px', height: '96px', background: 'var(--bg-2)', borderRadius: '10px', border: '1px solid var(--border)' } }),
        h('div', null, h('h3', null, c.name), h('p.muted', null, `${c.role} · level ${g.level}`), h('p', null, `HP ${hero.hp} / ${hero.maxhp} · ${hero.moves} moves`))),
      h('div.card.skill', null, h('div.row', null, h('b', null, c.map.name), h('span.chip', null, 'Map ability')), h('p', null, c.map.text)),
      h('h3', null, 'Dice'),
      h('div', { style: { display: 'grid', gap: '6px' } }, ...hero.dice.map((d, i) => h('div', { tip: dieTip(d) }, faceRow({ die: d.faces, dk: d.dk }),
        h('span.muted', null, '  ' + (i < c.dice.length ? 'class die' : 'from gear'))))),
      h('p.muted', null, '◆ is a shield face: worth 0, but it blocks 3 damage when you use it.'),
      Object.keys(hero.buffs).length ? h('h3', null, 'Blessings and curses') : null,
      ...Object.entries(hero.buffs).map(([b, n]) => h('div.card.skill', null, h('div.row', null, h('b', null, S.static.buffs[b].name), h('span.chip', null, `${n} turns`)), h('p', null, S.static.buffs[b].text))),
    ];
  }
  return drawerShell(hero.name, `${c.name} · ${controllerName(h0)}${readonly ? ' · ally' : ''}`, [['gear', 'Gear'], ['skills', 'Skills'], ['about', 'About']], d, body);
}

// The same face a skill has in a fight: the requirement badge, then its effect and miss lines.
export function skillFace(k) {
  const a = S.static.actions[k.replace(/\+$/, '')];
  if (!a) return null;
  const bd = reqBadge(a.req);
  const [ico, eff, miss] = a.short || ['spark', a.text, null];
  return h('div.skill-face', null,
    h('div.rq' + (bd.risky ? '.risky' : ''), { tip: `Needs: ${reqText(a.req)}` }, h('b', null, bd.main), bd.sub ? h('small', null, bd.sub) : null),
    h('div.ab', null, h('div.eff', null, icon(ico), h('span', null, eff + (k.endsWith('+') ? ' (+2)' : ''))), miss ? h('div.miss', null, `miss: ${miss}`) : null));
}

export function skillCard(k, source = null) {
  const sk = skillDef(k);
  const up = k.endsWith('+');
  const isAct = !!S.static.actions[k.replace(/\+$/, '')];
  // how often it can be used, where it comes from, and whether it takes Guard dice
  const when = !isAct ? null : sk.cd ? `Cooldown: every ${sk.cd} rounds` : sk.once ? 'Once a fight' : sk.per_rest ? 'Once per rest' : 'Every round';
  return h('div.card.skill', null,
    h('div.row', null, h('b', null, sk.name + (up ? '+' : '')), isAct ? null : h('span.chip', null, sk.cap ? 'Capstone' : 'Passive')),
    isAct ? skillFace(k) : null,
    isAct ? h('div.sk-tags', { style: { justifyContent: 'flex-start' } },
      h('span.tag' + (when === 'Every round' ? '.free' : ''), null, sk.cd ? icon('clock') : null, when),
      source ? h('span.tag', { tip: `From your ${source}` }, source) : null,
      sk.def ? h('span.tag.def', { tip: 'Defensive: takes Guard dice.' }, icon('shield'), 'Guard dice') : null) : null,
    h('p', null, sk.text + (up ? ' Upgraded: +2 to its numbers.' : '')),
    sk.tags?.length ? h('div', { style: { display: 'flex', gap: '4px' } }, ...sk.tags.map(t => h('span.chip', null, t[0].toUpperCase() + t.slice(1)))) : null);
}

// ------------------------------------------------------------------ event checks
// Which die an event check rolls, and the odds, worked out the way the server rolls it.
const SLOT_NAME = { weapon: 'weapon', armor: 'armor', trinket: 'trinket' };
function eventDie(x, which) {
  const hero = S.game.heroes[x];
  const top = d => Math.max(...d.faces.map(f => (typeof f === 'number' ? f : parseInt(String(f).slice(1)) || 0)));
  if (SLOT_NAME[which]) return hero.dice.find(d => d.src === which) || { faces: [1, 2, 3, 4], dk: [], bare: true };
  return hero.dice.reduce((a, b) => (top(b) > top(a) ? b : a), hero.dice[0]);
}
function faceVal(f, faces) {
  if (typeof f === 'number') return f;
  if (f === 'W') return Math.max(...faces.map(x => (typeof x === 'number' ? x : parseInt(String(x).slice(1)) || 0)));
  return parseInt(String(f).slice(1)) || 0;
}
function eventOdds(x, spec) {
  if (typeof spec === 'number') spec = { n: spec };
  const g = S.game;
  let roller = x, which = spec.die || 'best';
  if (which === 'party') {
    const here = g.heroes.map((y, i) => i).filter(i => g.heroes[i].alive && g.heroes[i].tile === g.heroes[x].tile);
    const top = i => Math.max(...eventDie(i, 'best').faces.map(f => faceVal(f, eventDie(i, 'best').faces)));
    roller = here.reduce((a, b) => (top(b) > top(a) ? b : a), x);
    which = 'best';
  }
  const d = eventDie(roller, which);
  const bonus = g.heroes[roller].skills.includes('silver_voice') ? 1 : 0;
  const vals = d.faces.map(f => faceVal(f, d.faces) + bonus);
  const p = spec.vs ? vals.reduce((a, v) => a + Math.max(0, Math.min(v - 1, spec.vs)) / spec.vs, 0) / vals.length
    : vals.filter(v => v >= (spec.n ?? 4)).length / vals.length;
  const whose = roller === x ? 'your' : `${g.heroes[roller].name}’s`;
  const label = d.bare ? `a bare d4 (no ${which})` : `${whose} ${SLOT_NAME[which] || 'best'} die (${dieLabel(d)})`;
  const text = spec.vs ? ` Roll ${label}, beat a d${spec.vs}:` : ` Roll ${label}, ${spec.n ?? 4}+${(spec.die === 'party') ? ' · anyone on your hex can roll it' : ''}:`;
  return { p, text, need: spec.n ?? 4, vs: spec.vs, greatAt: spec.great };
}
function outcomeSummary(o) {
  if (!o) return '';
  const st = S.static, parts = [];
  if (o.fight) parts.push('a fight with ' + [...new Set(o.fight)].map(k => st.foes[k].name).join(' and '));
  if (o.item) parts.push(`${/^[aeiou]/.test(o.item) ? 'an' : 'a'} ${o.item} item`);
  if (o.gold) parts.push(`${o.gold > 0 ? '+' : '−'}${Math.abs(o.gold)} gold`);
  if (o.hp) parts.push(`${o.hp > 0 ? '+' : '−'}${Math.abs(o.hp)} HP`);
  if (o.xp) parts.push(`+${o.xp} XP`);
  if (o.potion) parts.push(`${o.potion} potion${o.potion > 1 ? 's' : ''}`);
  if (o.buff) parts.push(`${st.buffs[o.buff].name}${st.buffs[o.buff].curse ? ' (a curse)' : ''}`);
  if (o.revive) parts.push('+1 revive');
  if (o.skiff) parts.push('a skiff');
  if (!parts.length) return 'nothing much';
  return parts.join(', ') + (o.all ? ' (everyone on your hex)' : '');
}
function eventRollView(r) {
  const verdict = r.great ? 'Great!' : r.ok ? 'Success' : 'Failed';
  return h('div.ev-roll' + (r.ok ? '.ok' : '.bad'), null,
    h('div.big-die', null, h('span', null, r.v)),
    r.vs ? [h('span.vs', null, 'vs'), h('div.big-die.foe', null, h('span', null, r.opp))] : null,
    h('div.ev-need', null, r.vs ? `Beat a d${r.vs}` : `Needed ${r.need}+`, r.by != null && r.by !== undefined ? h('small', null, `${S.game.heroes[r.by].name} rolled ${dieLabel({ faces: r.faces, dk: [] })}`) : null),
    h('div.rt-verdict.' + (r.ok ? 'hit' : 'miss'), null, verdict));
}

// ------------------------------------------------------------------ dialogs
function renderDialogs() {
  const el = $('modal');
  const g = S.game;
  if (UI.outcomes.length) {
    const o = UI.outcomes[0];
    const key = 'o' + o.title + o.text;
    const enter = key !== UI.lastDialog; UI.lastDialog = key;
    el.replaceChildren(modal([
      h('div.eyebrow', null, o.hero),
      h('h2', null, o.title),
      o.roll ? eventRollView(o.roll) : null,
      h('div.outcome', null, o.text),
      o.bits.length ? h('div.gains', null, ...o.bits.map(b => h('span.chip.brass', null, b))) : null,
      h('button.btn.primary', { style: { justifySelf: 'end' }, onclick: () => { UI.outcomes.shift(); renderDialogs(); } }, 'Carry on'),
    ], { enter }));
    return;
  }
  if (g.phase === 'fork' && g.fork && !combatOpen() && !mine().some(x => g.pending[x]?.length)) {
    const fk = forkView(g.fork);
    if (fk) {
      const enter = UI.lastDialog !== 'fork' + g.fork.step; UI.lastDialog = 'fork' + g.fork.step;
      el.replaceChildren(modal(fk, { wide: true, enter, backdrop: 'dungeon' }));
      return;
    }
  }
  const h0 = mine().find(x => g.pending[x]?.length && (x === sel() || true));
  if (h0 === undefined || combatOpen()) { el.replaceChildren(); UI.lastDialog = null; return; }
  const d = g.pending[h0][0], hero = g.heroes[h0];
  // allies who could take loot from this hero: anyone alive within a hex (who'd have joined the fight)
  const mates = g.heroes.map((x, i) => i).filter(i => i !== h0 && g.heroes[i].alive && hexDist(g.heroes[i].tile, hero.tile) <= 1);
  let content;
  if (d.type === 'event') {
    const ev = S.static.events[d.key];
    content = [
      h('div.eyebrow', null, `${hero.name} · ${S.static.regions[S.world.reg[hero.tile]] || ''}`),
      h('h2', null, ev.title),
      h('p.lead', null, ev.text),
      h('div.choices', null, ...ev.choices.map((ch, i) => {
        const missing = ch.need && !g.heroes.some(x => x.alive && x.cls === ch.need);
        const broke = (ch.cost || 0) > hero.gold;
        const tags = [];
        if (ch.need) tags.push(`${cls(ch.need).name}${missing ? ' needed' : ''}`);
        if (ch.cost) tags.push(`${ch.cost} gold${broke ? ' (not enough)' : ''}`);
        const ck = ch.check ? eventOdds(h0, ch.check) : null;
        const stakes = ch.check
          ? [ch.great ? `${ck.greatAt}+: ${outcomeSummary(ch.great)}` : null, `${ck.vs ? 'Win' : ck.need + '+'}: ${outcomeSummary(ch.ok)}`, `${ck.vs ? 'Lose' : 'Else'}: ${outcomeSummary(ch.bad)}`].filter(Boolean).join(' · ')
          : outcomeSummary(ch.ok);
        return h('button.choice', { disabled: missing || broke, onclick: () => send({ t: 'choose', h: h0, n: i }) },
          h('span.n', null, i + 1),
          h('span.grow', null, h('span.label', null, ch.label),
            ck ? h('span.roll', null, icon('dice'), ck.text, h('b.odds' + (ck.p >= 0.6 ? '.good' : ck.p >= 0.35 ? '.mid' : '.bad'), null, ` ${Math.round(ck.p * 100)}%`)) : null,
            stakes ? h('span.stakes', null, stakes) : null),
          tags.length ? h('span.tag', null, tags.join(' · ')) : null);
      })),
    ];
  } else if (d.type === 'loot') {
    content = [
      h('div.eyebrow', null, hero.name),
      h('h2', null, 'Spoils'),
      h('p.lead', null, mates.length ? 'Take one, or hand it to an ally nearby. Put gear on now, or keep it in a bag for later.'
        : 'Take one. Put gear on now, or keep it in your bag for later.'),
      h('div.picks.loot', null, ...d.opts.map((k, i) => lootCard(h0, k, i, mates, extra => send({ t: 'choose', h: h0, n: i, ...extra })))),
      h('button.btn.ghost', { style: { justifySelf: 'end' }, onclick: () => send({ t: 'choose', h: h0, n: -1 }) }, 'Leave it'),
    ];
  } else if (d.type === 'pool') {
    // the fight's shared loot: four items, three claims going round the winners, first come first served
    const pool = g.pools[d.id];
    const still = pool.heroes.filter(x => x !== h0 && g.pending[x]?.some(p => p.type === 'pool' && p.id === d.id)).map(x => g.heroes[x].name);
    content = [
      h('div.eyebrow', null, `${hero.name} · ${pool.heroes.length > 1 ? 'shared spoils' : 'spoils'}`),
      h('h2', null, 'Spoils'),
      h('p.lead', null, `Four items, and ${3 - Object.keys(pool.taken).length} of three claims left. ` +
        (pool.heroes.length > 1 ? 'The claims go round the party; first claim wins an item, and you can hand yours to an ally.' : 'They’re all yours: claim up to three.')),
      h('div.picks.loot', null, ...pool.items.map((k, i) => lootCard(h0, k, i, mates, extra => send({ t: 'choose', h: h0, n: i, ...extra }), pool.taken[i]))),
      h('div', { style: { display: 'flex', gap: '12px', alignItems: 'center', justifyContent: 'flex-end' } },
        still.length ? h('span.muted', null, `Still choosing: ${still.join(', ')}`) : null,
        h('button.btn.ghost', { onclick: () => send({ t: 'choose', h: h0, n: -1 }) }, 'Pass')),
    ];
  } else if (d.type === 'level') {
    content = [
      h('div.eyebrow', null, `Level ${d.lvl}`),
      h('h2', null, `${hero.name} learns something new`),
      h('p.lead', null, `Choose one. ${d.lvl === 3 || d.lvl === 6 ? 'One of your class dice also grows a size. ' : ''}Max HP went up too.`),
      h('div.picks', null, ...d.opts.map((k, i) => {
        const sk = skillDef(k), up = k.endsWith('+');
        const isAct = !!S.static.actions[k.replace(/\+$/, '')];
        return h('button.pick', { style: { '--i': i }, onclick: () => send({ t: 'choose', h: h0, n: i }) }, h('span.kbd.pick-key', null, i + 1),
          h('span.kind', null, up ? 'Upgrade' : sk.cap ? 'Capstone' : isAct ? 'New action' : 'Passive'),
          h('h3', null, sk.name + (up ? '+' : '')),
          isAct ? skillFace(k) : null,
          isAct && sk.cd ? h('span.req', null, icon('clock'), `cooldown ${sk.cd}`) : null,
          h('p', null, up ? `${sk.text} Upgraded: +2 to its numbers.` : sk.text),
          sk.tags?.length ? h('div.tags', null, ...sk.tags.map(t => h('span.chip', null, t[0].toUpperCase() + t.slice(1)))) : null);
      })),
    ];
  }
  const key = JSON.stringify([h0, d]);
  const enter = key !== UI.lastDialog; UI.lastDialog = key;
  // between a dungeon's fights the party is still underground: no map behind the spoils
  const here = g.places[hero.tile];
  const deep = g.phase === 'reward' && here && ((here.kind === 'dungeon' && !g.cleared.includes(here.region)) || here.kind === 'peak');
  el.replaceChildren(modal(content, { wide: d.type !== 'event', enter, backdrop: deep ? 'dungeon' : null }));
  // good loot gets a fanfare as the cards are dealt
  if (enter && (d.type === 'loot' || d.type === 'pool')) {
    const best = Math.max(...(d.opts || g.pools[d.id].items).map(k => ['common', 'uncommon', 'rare', 'legendary'].indexOf(item(k).rarity)));
    if (best >= 2) setTimeout(() => sfx.play(best === 3 ? 'fanfare' : 'rare'), 250);
  }
}

// One loot card: the item, what it sells for, how it compares with what's worn, and buttons to put it
// on, bag it or hand it to an ally (`choose(extra)` sends the pick). `taken` ({by, to}) greys it out.
function lootCard(h0, k, i, mates, choose, taken) {
  const g = S.game, hero = g.heroes[h0];
  const it = item(k);
  const cur = it.slot !== 'use' && !freeSlot(hero, it.slot) ? item(hero.equip[swapSlot(hero, it.slot)]) : null;
  const head = [h('span.kbd.pick-key', null, i + 1),
    h('span.kind.rar-' + it.rarity, null, `${it.rarity[0].toUpperCase() + it.rarity.slice(1)} ${it.slot === 'use' ? 'consumable' : it.slot}`),
    h('h3.rar-' + it.rarity, null, it.name),
    it.die ? faceRow(it) : null,
    it.dk?.length ? h('p', null, it.dk.map(x => KIND_TEXT[x]).filter(Boolean).join(' ')) : null,
    ...(it.acts || []).map(a => h('p', null, h('b', null, S.static.actions[a].name + ': '), S.static.actions[a].text)),
    it.mods ? h('p', null, modsText(it.mods)) : null,
    it.text ? h('p.passive', null, it.text) : null,
    sellChip(k, h0)];
  if (taken) {
    const who = taken.by === taken.to ? g.heroes[taken.by].name : `${g.heroes[taken.by].name}, for ${g.heroes[taken.to].name}`;
    return h('div.pick.loot-card.taken.r-' + it.rarity, { style: { '--i': i } }, ...head, h('div.claimed', null, icon('check'), `Claimed by ${who}`));
  }
  const give = m => choose({ to: m, equip: it.slot !== 'use' && !!freeSlot(g.heroes[m], it.slot) });
  return h('div.pick.loot-card.r-' + it.rarity, { style: { '--i': i } }, ...head,
    compareWith(h0, k),
    h('div.pick-btns', null,
      it.slot === 'use' || !cur ? h('button.btn.primary.sm', { onclick: () => choose({ equip: true }) }, it.slot === 'use' ? 'Take' : 'Put it on')
        : [...wearButtons(hero, k, into => choose({ equip: true, into })), h('button.btn.sm.ghost', { onclick: () => choose({ equip: false }) }, 'Into the bag')],
      mates.length ? h('div.give-row', null, h('span.muted', null, 'Give to'),
        ...mates.map(m => {
          const mate = g.heroes[m];
          const now = it.slot !== 'use' && !freeSlot(mate, it.slot) ? item(mate.equip[swapSlot(mate, it.slot)]).name : null;
          return h('button.btn.sm.ghost', { onclick: () => give(m),
            tip: it.slot === 'use' ? `Into ${mate.name}'s bag.`
              : now ? `Into ${mate.name}'s bag (they wear the ${now}).` : `${mate.name} puts it on (their ${it.slot} slot is empty).` },
            mate.name);
        })) : null));
}

// ------------------------------------------------------------------ a fork in a dungeon
// After a dungeon fight the party picks one of two ways on. Everyone in the dungeon votes (one
// click votes for every hero you play); the most votes wins, a tie is a coin toss.
function forkView(fk) {
  const g = S.game, st = S.static;
  const mineIn = mine().filter(x => fk.heroes.includes(x) && g.heroes[x].alive);
  if (!mineIn.length) return null;
  const vote = n => mineIn.forEach(x => send({ t: 'fork', h: x, n }));
  const waiting = fk.heroes.filter(x => g.heroes[x].alive && fk.votes[x] === undefined).map(x => g.heroes[x].name);
  const lines = fk.opts.map((o, i) => {
    const p = st.paths[o.path];
    const voters = fk.heroes.filter(x => fk.votes[x] === i);
    const foes = o.foes.map(x => typeof x === 'string' ? { k: x } : x);
    const affs = [...new Set(foes.map(x => x.aff).filter(Boolean))];
    const big = foes.find(x => st.foes[x.k]?.big);
    const boss = foes.find(x => st.foes[x.k]?.boss);
    const kind = !foes.length ? 'No fight' : boss ? 'The boss' : big || affs.length ? 'Elite fight' : 'Fight';
    const mine_ = mineIn.every(x => fk.votes[x] === i);
    return h('button.pick.fork' + (mine_ ? '.chosen' : ''), { style: { '--i': i }, onclick: () => vote(i) },
      h('span.kbd.pick-key', null, i + 1),
      h('span.kind', null, kind),
      h('h3', null, p.name),
      h('p', null, p.text),
      foes.length ? h('div.fork-foes', null, ...foes.map(x => h('span.chip' + (x.aff || st.foes[x.k]?.big || st.foes[x.k]?.boss ? '.danger' : ''), null, foeName(x.k, x.aff)))) : null,
      ...affs.map(a => h('p.muted.small', null, `${st.elites[a].name}: ${st.elites[a].text}`)),
      big ? h('p.muted.small', null, `${st.foes[big.k].name}: a big threat. At half health it's bloodied: ${st.foes[big.k].bloodied.text}`) : null,
      h('div.gains', null, h('span.chip.brass', null, p.reward)),
      h('div.fork-votes', null, ...voters.map(x => h('span.vote', { style: { '--c': `var(--hero-${x})` } }, g.heroes[x].name))));
  });
  return [
    h('div.eyebrow', null, `${st.dungeons[fk.region]} · fight ${fk.step + 1} of 3 next`),
    h('h2', null, 'The way forks'),
    h('p.lead', null, fk.heroes.length > 1 ? 'Pick a path together. Most votes wins; a tie is a coin toss.' : 'Pick a path.'),
    h('div.picks', null, ...lines),
    waiting.length ? h('p.muted', null, `Waiting for ${waiting.join(', ')}.`) : null,
  ];
}

// ------------------------------------------------------------------ first-time hints
const HINTS = {
  plan: ['Planning together', 'Everyone plans at once. Click a lit hex to plot a route, then Ready. When the whole party is ready, everyone moves together. Walking into enemies starts a fight, and anyone within a hex joins in.'],
  fight: ['Fighting with dice', 'Click dice to pick them, then click an action they fit: it happens at once, dice and all. Whoever plays first goes first, so set-ups before attacks. Heroes working together score combos: hover Combos in the fight for the list. When everyone is ready, enemies do what their intents say.'],
  sea: ['The rising tide', 'Every few turns the tide rises and every enemy grows a little stronger, as the top bar shows. The sooner you clear the three objectives and reach the peak, the easier the fights.'],
};
function renderHint() {
  const el = $('hint');
  const g = S.game;
  let key = null;
  if (!S.seenHints.plan && g.phase === 'plan') key = 'plan';
  else if (!S.seenHints.sea && g.rises > 0) key = 'sea';
  const modalUp = UI.outcomes.length || mine().some(x => g.pending[x]?.length);
  if (!key || combatOpen() || modalUp) { el.replaceChildren(); return; }
  const [title, text] = HINTS[key];
  el.replaceChildren(h('div.hint-card.panel', null, h('b', null, title), h('p', null, text),
    h('button.btn.sm', { onclick: () => { S.seenHints[key] = 1; saved.hints = S.seenHints; persist(); renderHint(); } }, 'Got it')));
}
export function seenHint(key) { return !!S.seenHints[key]; }
export function markHint(key) { S.seenHints[key] = 1; saved.hints = S.seenHints; persist(); }

// ------------------------------------------------------------------ effects
export function handleFx(list, before) {
  const speed = S.settings.speed;
  let heroSteps = 0;
  for (const f of list) {
    switch (f.k) {
      case 'move':
        if (map && speed) {
          map.playMove('h' + f.h, f.path, speed);
          heroSteps = Math.max(heroSteps, f.path.length - 1);
          if (f.h === sel()) map.centerOn(f.path[f.path.length - 1]);
        }
        if (mine().includes(f.h)) sfx.play('step');
        break;
      case 'gmove': if (map && speed) map.playMove('g' + f.g, f.path, speed, heroSteps * map.stepTime(speed) + 120); break;
      case 'rise': {
        toast(`The tide rises: enemies +${S.game.surge}%`, 'big');
        sfx.play('rise');
        break;
      }
      case 'coins': if (mine().includes(f.h) && !combatOpen()) { toast(`${S.game.heroes[f.h].name}: +${f.n} gold`); sfx.play('coin'); } break;
      case 'tide': toast(f.tide === 'low' ? 'Low tide: the sandbars are out' : 'High tide: the shallows close'); break;
      case 'level': bigBanner(`Level ${f.lvl}`, 'The party grows stronger', 'gold'); sfx.play('level'); break;
      case 'cleared': bigBanner(`${S.static.dungeons[f.region]} cleared`, `${S.game.cleared.length} of 3 objectives`, 'gold', 2600); sfx.play('fanfare'); break;
      case 'buff': if (mine().includes(f.h)) toast(`${S.game.heroes[f.h].name}: ${S.static.buffs[f.b].name}`); break;
      case 'event':
        if (mine().includes(f.h)) {
          UI.outcomes.push({ hero: S.game.heroes[f.h].name, title: S.static.events[f.key].title, text: f.text, roll: f.roll, bits: f.bits });
          renderDialogs();
        }
        break;
    }
  }
  combatFx(list, before);
}

document.addEventListener('keydown', e => {
  if (!root || e.target.matches('input, select, textarea')) return;
  const g = S.game;
  if (!g || combatOpen()) return;
  if (e.key === 'Escape') { if (UI.drawer) closeDrawer(); else if (UI.menu) { UI.menu = false; renderMenu(); } }
  // dialogs: number keys pick an option (loot goes straight on), Enter carries on
  const scrim = document.querySelector('#modal .scrim');
  if (scrim) {
    const n = parseInt(e.key, 10);
    const opts = [...scrim.querySelectorAll('.choice, button.pick, .loot-card')];
    if (n >= 1 && n <= opts.length) {
      const o = opts[n - 1];
      (o.classList.contains('loot-card') ? o.querySelector('.pick-btns .btn.primary') : o)?.click();
      e.preventDefault();
    } else if (e.key === 'Enter' && !opts.length) scrim.querySelector('.btn.primary')?.click();
    return;
  }
  if (e.code === 'Space' && g.phase === 'plan') {
    const h0 = sel();
    if (mine().includes(h0) && g.plans[h0] && !g.pending[h0]?.length) { e.preventDefault(); send({ t: 'ready', h: h0, on: !g.plans[h0].ready }); }
  }
});
