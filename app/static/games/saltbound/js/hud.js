// The run's HTML over the map: top bar, party cards, the action bar, the log, the town and hero
// drawers, dialogs (events, loot, level-ups), first-time hints, and wiring the map's clicks.
import { S, send, mine, controllerName, isOnline, saved, persist } from './store.js?v=12';
import { $, h, icon, toast, modal, hideTip } from './ui.js?v=12';
import { spriteURL } from './art.js?v=12';
import { reach, routeTo, terrain, TERRAIN_NAME, dieLabel, dieTip, faceText, KIND_TEXT, reqText, visibleTiles } from './rules.js?v=12';
import { MapView } from './hexmap.js?v=12';
import { renderCombat, combatFx, combatOpen, showFight } from './combat.js?v=12';
import { disconnect } from './main.js?v=12';
import * as sfx from './audio.js?v=12';

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
      h('div#topbar'), h('div#party.party'), h('div#actionbar'), h('div#log'), h('div#hint'),
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
    if (gr && (vis.has(t) || gr.lair)) lines.push(h('div', { style: { color: 'var(--danger)' } }, (gr.lair ? 'Lair: ' : 'Enemies: ') + gr.foes.map(k => S.static.foes[k].name).join(', ')));
    if ((g.floods || []).includes(t)) lines.push(h('div', { style: { color: 'var(--info)' } }, 'Floods at the next rise.'));
    const heroesHere = g.heroes.filter(x => x.alive && x.tile === t).map(x => x.name);
    if (heroesHere.length) lines.push(h('div', null, heroesHere.join(', ')));
  }
  if (mine().includes(h0) && canPlan(h0) && !g.plans[h0].ready) {
    const r = reach(S.world, g, S.static, h0);
    const b = r.best.get(t);
    if (b && t !== g.heroes[h0].tile) {
      lines.push(h('div.cost', null, `${b.cost} of ${g.heroes[h0].moves} moves`));
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
    case 'dungeon': return g.cleared.includes(p.region) ? 'Cleared.' : `An objective: ${3 - (g.dungeon[p.region] || 0)} fights deep, no retreat.`;
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
  const left = g.loss_rise - g.rises;
  const xpPct = g.xp_next ? Math.round(100 * (g.xp - g.xp_this) / (g.xp_next - g.xp_this)) : 100;
  $('topbar').replaceChildren(h('div.topbar', null,
    h('div.logo', null, 'Salt', h('span', null, 'bound')),
    h('div.stats', null,
      h('div.stat', { tip: `Turn ${g.turn}\nEveryone plans, then everyone moves at once.` }, h('span.lbl', null, 'Turn'), h('b', null, g.turn)),
      h('div.stat.opt', { tip: `${g.tide === 'low' ? 'Low' : 'High'} tide\n${g.tide === 'low' ? 'Sandbars and shallows are walkable.' : 'Shallows are under water: skiffs only.'}\nTurns in ${g.next_tide} turn${g.next_tide === 1 ? '' : 's'}.` },
        icon('moon'), h('b', null, g.tide === 'low' ? 'Low tide' : 'High tide'), h('span.lbl', null, `· ${g.next_tide}`)),
      h('div.stat' + (left <= 3 ? '.warn' : ''), { tip: `The sea\nRises every ${g.rise_every} turns, next in ${g.next_rise}.\n${left} rises until the peak floods and the voyage is lost.${g.rises >= g.grow_from ? '\nThe Drowned Crown grows stronger with each rise.' : ''}` },
        icon('wave'), h('b', null, `${left} left`), h('span.lbl', null, `· next in ${g.next_rise}`)),
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
  if (g.pending[h0]?.length) return [{ event: 'Reading an event', loot: 'Picking loot', level: 'Levelling up' }[g.pending[h0][0].type], 'wait'];
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
      onclick: () => { if (my.includes(i)) { S.sel = i; UI.preview = null; renderGame(); } map.centerOn(hero.tile); },
    },
      h('div.hero-top', null,
        h('img.pix', { src: spriteURL(hero.cls), alt: '' }),
        h('div.who', null, h('b', null, hero.name), h('span', null, `${cls(hero.cls).name} · ${controllerName(i)}${my.includes(i) ? ' (you)' : ''}`)),
        h('span.hero-state.' + (stCls || 'x'), null, stTxt)),
      h('div.bar', null, h('i', { style: { width: pct + '%' } }), h('span', null, `${Math.max(0, hero.hp)} / ${hero.maxhp}`)),
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

function restText(h0) {
  const g = S.game, hero = g.heroes[h0];
  const p = g.places[hero.tile];
  const medic = g.heroes.some(x => x.alive && x.tile === hero.tile && cls(x.cls).map.key === 'field_medic');
  const frac = (p && p.kind === 'camp') || medic ? 0.5 : 0.2;
  return `Spend the turn resting: heal ${Math.round(hero.maxhp * frac)} HP${frac < 0.5 ? ' (half at a camp)' : ''}.`;
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
    h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap' } },
      host ? h('button.btn', { onclick: () => { if (confirm('Save and take everyone back to the lobby?')) { send({ t: 'quit' }); close(); } } }, 'Save and return to lobby') : null,
      h('button.btn.ghost', { onclick: () => { if (confirm('Leave this voyage? It’s saved, and you can rejoin with the room code.')) disconnect(); } }, 'Leave'),
      h('button.btn.primary', { style: { marginLeft: 'auto' }, onclick: close }, 'Close')),
  ], { onClose: close, enter: !!UI.menuFresh }));
  UI.menuFresh = false;
}

// ------------------------------------------------------------------ drawers
function openDrawer(kind, tab) {
  UI.drawer = { kind, tab: tab || (kind === 'town' ? 'market' : 'gear'), enter: true };
  renderDrawer();
}
function closeDrawer() { UI.drawer = null; renderDrawer(); }

function renderDrawer() {
  const el = $('drawer');
  const d = UI.drawer;
  if (!d || combatOpen()) { el.replaceChildren(); return; }
  const h0 = sel(), hero = S.game.heroes[h0];
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

const SLOT_ICON = { weapon: 'sword', armor: 'shield', trinket: 'star', use: 'drop' };
function itemRow(key, right, extra) {
  const it = item(key);
  const sub = [];
  if (it.slot !== 'use') sub.push(it.slot[0].toUpperCase() + it.slot.slice(1));
  if (it.die) sub.push(faceRow(it));
  return h('div.item.r-' + it.rarity, { tip: itemTip(key) },
    h('div.ico', null, icon(SLOT_ICON[it.slot] || 'spark')),
    h('div', null, h('div.name.rar-' + it.rarity, null, it.name), h('div.sub', null, ...interleave(sub, ' · ')), extra || null),
    h('div.acts', null, right));
}
// A die's faces as little tiles, with its kinds (Seer, Fate...) in front.
function faceRow(it) {
  const kinds = (it.dk || []).filter(k => !k.startsWith('link:') && k !== 'top');
  return h('span.faces', null, ...kinds.map(k => h('span.chip.brass', { style: { height: '20px' } }, k[0].toUpperCase() + k.slice(1))),
    ...it.die.map(f => h('span.face' + (f === 'S' ? '.s' : ''), null, faceText(f))));
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
    out.push({ max_hp: `+${v} max HP`, heal_bonus: `+${v} to heals`, thorns: `Attackers take ${v}`, start_armor: `Start fights with ${v} Armor`,
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
        return itemRow(k, h('button.btn.sm' + (hero.gold >= price ? '.primary' : ''), { disabled: disabled || hero.gold < price, onclick: () => send({ t: 'buy', h: h0, item: k }) }, icon('coin'), price));
      }),
      g.herald ? h('p.muted', null, 'The Herald’s silver tongue knocks 20% off.') : null,
      hero.bag.length ? h('h3', null, 'Sell') : null,
      ...hero.bag.map((k, i) => itemRow(k, h('button.btn.sm', { disabled, onclick: () => send({ t: 'sell', h: h0, bag: i }) }, `Sell · ${Math.floor(S.static.prices[k] * 0.4)}`))),
    ];
  } else if (d.tab === 'inn') {
    body = [h('h3', null, 'The inn'), h('p.muted', null, 'A hot meal and a dry bed. Heals you to full straight away.'),
      h('div', null, `HP ${hero.hp} / ${hero.maxhp}`),
      h('button.btn.primary', { disabled: disabled || hero.hp >= hero.maxhp || hero.gold < g.inn, onclick: () => send({ t: 'inn', h: h0 }) }, icon('bed'), `Take a room · ${g.inn} gold`)];
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

function heroDrawer(h0, d) {
  const g = S.game, hero = g.heroes[h0], c = cls(hero.cls);
  const town = inTown(h0);
  const free = !(g.fight && g.fight.heroes.includes(h0));
  let body;
  if (d.tab === 'gear') {
    const mates = g.heroes.map((x, i) => i).filter(i => i !== h0 && g.heroes[i].alive && g.heroes[i].tile === hero.tile);
    body = [
      h('h3', null, 'Equipped'),
      ...['weapon', 'armor', 'trinket'].map(slot => hero.equip[slot]
        ? itemRow(hero.equip[slot], slot !== 'weapon' ? h('button.btn.sm.ghost', { disabled: !free, onclick: () => send({ t: 'unequip', h: h0, slot }) }, 'Take off') : null)
        : h('div.item.empty', null, h('div.ico', null, icon(SLOT_ICON[slot])), h('div', null, `No ${slot}`))),
      h('div.section-title', null, h('h3', null, `Bag · ${hero.bag.length} of ${hero.bagsize}`), h('span.chip.brass', null, icon('coin'), hero.gold)),
      ...hero.bag.map((k, i) => {
        const it = item(k);
        return itemRow(k, [
          it.slot !== 'use' ? h('button.btn.sm', { disabled: !free, onclick: () => send({ t: 'equip', h: h0, bag: i }) }, 'Equip') : null,
          it.slot === 'use' && !it.fight ? h('button.btn.sm', { onclick: () => send({ t: 'use', h: h0, bag: i }) }, 'Use') : null,
          ...mates.map(m => h('button.btn.sm.ghost', { tip: `Give to ${g.heroes[m].name}`, onclick: () => send({ t: 'give', h: h0, to: m, bag: i }) }, icon('hand'), g.heroes[m].name)),
          town ? h('button.btn.sm.ghost', { onclick: () => send({ t: 'sell', h: h0, bag: i }) }, 'Sell') : null,
          h('button.btn.sm.ghost', { 'aria-label': 'Drop', tip: 'Throw it away', onclick: () => { if (confirm(`Throw away ${it.name}?`)) send({ t: 'drop', h: h0, bag: i }); } }, icon('x')),
        ]);
      }),
      !hero.bag.length ? h('p.muted', null, 'Your bag is empty.') : null,
      mates.length && hero.gold > 0 ? h('div', { style: { display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' } }, h('span.muted', null, 'Give 10 gold to'),
        ...mates.map(m => h('button.btn.sm', { disabled: hero.gold < 10, onclick: () => send({ t: 'give', h: h0, to: m, gold: 10 }) }, g.heroes[m].name))) : null,
    ];
  } else if (d.tab === 'skills') {
    const acts = hero.actions.filter(k => !['shift', 'flee'].includes(k));
    const passives = hero.skills.filter(k => S.static.passives[k.replace(/\+$/, '')]);
    body = [
      h('h3', null, 'Actions'),
      ...acts.map(k => skillCard(k)),
      h('h3', null, 'Passives'),
      passives.length ? passives.map(k => skillCard(k)) : h('p.muted', null, 'None yet: pick them as you level up.'),
      h('h3', null, 'Always available'),
      skillCard('shift'), skillCard('flee'),
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
  return drawerShell(hero.name, `${c.name} · ${controllerName(h0)}`, [['gear', 'Gear'], ['skills', 'Skills'], ['about', 'About']], d, body);
}

export function skillCard(k) {
  const sk = skillDef(k);
  const up = k.endsWith('+');
  const isAct = !!S.static.actions[k.replace(/\+$/, '')];
  return h('div.card.skill', null,
    h('div.row', null, h('b', null, sk.name + (up ? '+' : '')), isAct ? h('span.req', null, icon('dice'), reqText(sk.req)) : h('span.chip', null, sk.cap ? 'Capstone' : 'Passive')),
    sk.cd ? h('span.chip', { style: { justifySelf: 'start' } }, icon('clock'), `Cooldown: every ${sk.cd} rounds`) : null,
    h('p', null, sk.text + (up ? ' Upgraded: +2 to its numbers.' : '')),
    sk.tags?.length ? h('div', { style: { display: 'flex', gap: '4px' } }, ...sk.tags.map(t => h('span.chip', null, t[0].toUpperCase() + t.slice(1)))) : null);
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
      o.roll != null ? h('p.muted', null, `You rolled ${o.roll === 'S' ? 'a shield' : o.roll}.`) : null,
      h('div.outcome', null, o.text),
      o.bits.length ? h('div.gains', null, ...o.bits.map(b => h('span.chip.brass', null, b))) : null,
      h('button.btn.primary', { style: { justifySelf: 'end' }, onclick: () => { UI.outcomes.shift(); renderDialogs(); } }, 'Carry on'),
    ], { enter }));
    return;
  }
  const h0 = mine().find(x => g.pending[x]?.length && (x === sel() || true));
  if (h0 === undefined || combatOpen()) { el.replaceChildren(); UI.lastDialog = null; return; }
  const d = g.pending[h0][0], hero = g.heroes[h0];
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
        if (ch.need) tags.push(`${cls(ch.need).name}`);
        if (ch.check) tags.push(`Roll ${ch.check}+ on your best die`);
        if (ch.cost) tags.push(`${ch.cost} gold`);
        return h('button.choice', { disabled: missing || broke, onclick: () => send({ t: 'choose', h: h0, n: i }) },
          h('span.n', null, i + 1), h('span.grow', null, ch.label), tags.length ? h('span.tag', null, tags.join(' · ')) : null);
      })),
    ];
  } else if (d.type === 'loot') {
    content = [
      h('div.eyebrow', null, hero.name),
      h('h2', null, 'Spoils'),
      h('p.lead', null, 'Take one. Gear goes straight on if the slot is empty; otherwise into your bag.'),
      h('div.picks', null, ...d.opts.map((k, i) => {
        const it = item(k);
        return h('button.pick.r-' + it.rarity, { onclick: () => send({ t: 'choose', h: h0, n: i }) },
          h('span.kind.rar-' + it.rarity, null, `${it.rarity[0].toUpperCase() + it.rarity.slice(1)} ${it.slot === 'use' ? 'consumable' : it.slot}`),
          h('h3.rar-' + it.rarity, null, it.name),
          it.die ? faceRow(it) : null,
          it.dk?.length ? h('p', null, it.dk.map(k => KIND_TEXT[k]).filter(Boolean).join(' ')) : null,
          ...(it.acts || []).map(a => h('p', null, h('b', null, S.static.actions[a].name + ': '), S.static.actions[a].text)),
          it.mods ? h('p', null, modsText(it.mods)) : null,
          it.text ? h('p', null, it.text) : null,
          hero.equip[it.slot] ? h('p.muted', null, `Now: ${item(hero.equip[it.slot]).name}`) : null);
      })),
      h('button.btn.ghost', { style: { justifySelf: 'end' }, onclick: () => send({ t: 'choose', h: h0, n: -1 }) }, 'Leave it'),
    ];
  } else if (d.type === 'level') {
    content = [
      h('div.eyebrow', null, `Level ${d.lvl}`),
      h('h2', null, `${hero.name} learns something new`),
      h('p.lead', null, `Choose one. ${d.lvl === 3 || d.lvl === 6 ? 'One of your class dice also grows a size. ' : ''}Max HP went up too.`),
      h('div.picks', null, ...d.opts.map((k, i) => {
        const sk = skillDef(k), up = k.endsWith('+');
        const isAct = !!S.static.actions[k.replace(/\+$/, '')];
        return h('button.pick', { onclick: () => send({ t: 'choose', h: h0, n: i }) },
          h('span.kind', null, up ? 'Upgrade' : sk.cap ? 'Capstone' : isAct ? 'New action' : 'Passive'),
          h('h3', null, sk.name + (up ? '+' : '')),
          isAct ? h('span.req', null, icon('dice'), reqText(sk.req), sk.cd ? ` · cooldown ${sk.cd}` : '') : null,
          h('p', null, up ? `${sk.text} Upgraded: +2 to its numbers.` : sk.text),
          sk.tags?.length ? h('div.tags', null, ...sk.tags.map(t => h('span.chip', null, t[0].toUpperCase() + t.slice(1)))) : null);
      })),
    ];
  }
  const key = JSON.stringify([h0, d]);
  const enter = key !== UI.lastDialog; UI.lastDialog = key;
  el.replaceChildren(modal(content, { wide: d.type !== 'event', enter }));
}

// ------------------------------------------------------------------ first-time hints
const HINTS = {
  plan: ['Planning together', 'Everyone plans at once. Click a lit hex to plot a route, then Ready. When the whole party is ready, everyone moves together. Walking into enemies starts a fight, and anyone within a hex joins in.'],
  fight: ['Fighting with dice', 'Click dice to pick them, then click an action they fit. Actions resolve in the order the party places them, then enemies do what their intents say. Ready up when you’re done.'],
  sea: ['The rising sea', 'Every few turns the sea rises and the lowest land floods. Hexes about to go under glow blue. Clear the three objectives and reach the peak before the water does.'],
};
function renderHint() {
  const el = $('hint');
  const g = S.game;
  let key = null;
  if (!S.seenHints.plan && g.phase === 'plan') key = 'plan';
  else if (!S.seenHints.sea && (g.floods || []).length) key = 'sea';
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
      case 'rise': toast('The sea rises', 'big'); sfx.play('rise'); break;
      case 'tide': toast(f.tide === 'low' ? 'Low tide: the sandbars are out' : 'High tide: the shallows close'); break;
      case 'level': toast(`The party reaches level ${f.lvl}`, 'big'); sfx.play('level'); break;
      case 'cleared': toast(`${S.static.dungeons[f.region]} is cleared`, 'big'); sfx.play('level'); break;
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
  if (e.code === 'Space' && g.phase === 'plan') {
    const h0 = sel();
    if (mine().includes(h0) && g.plans[h0] && !g.pending[h0]?.length) { e.preventDefault(); send({ t: 'ready', h: h0, on: !g.plans[h0].ready }); }
  }
});
