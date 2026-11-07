// The run's HTML over the map: top bar, party cards, the action bar, the log, the town and hero
// drawers, dialogs (events, loot, level-ups), first-time hints, and wiring the map's clicks.
import { S, send, mine, controllerName, isOnline, saved, persist } from './store.js?v=151';
import { $, h, icon, toast, modal, hideTip, bigBanner } from './ui.js?v=151';
import { spriteURL, placeURL } from './art.js?v=151';
import { itemURL } from './itemart.js?v=151';
import { reach, routeTo, terrain, seaMap, inSquall, TERRAIN_NAME, dieLabel, dieTip, faceText, faceTip, KIND_TEXT, reqText, visibleTiles, dist as hexDist, expected, face, topFace } from './rules.js?v=151';
import { MapView } from './hexmap.js?v=151';
import { renderCombat, combatFx, combatOpen, showFight, hpClass, reqBadge, afterCombat, holdCombat, CRIT_TIP } from './combat.js?v=151';
import { disconnect } from './main.js?v=151';
import * as sfx from './audio.js?v=151';

// the log starts closed and "This turn" open; each remembers how you left it
const UI = { drawer: null, log: saved.logOpen === true, fc: saved.fcOpen !== false, res: {}, hover: -1, preview: null, menu: false };
let root = null, map = null, mapWorld = null;

export function teardownGame() {
  if (map) { map.destroy(); map = null; }
  root = null; mapWorld = null;
  UI.drawer = null; UI.res = {};
}

const seat = h => `var(--hero-${h})`;
const cls = k => S.static.classes[k];
// an upgraded action (key+) is the action with its rider merged in (classes.py `_upgrade`)
export const upDef = (k, a = S.static.actions[k.replace(/\+$/, '')]) => (a && k.endsWith('+') && a.up ? { ...a, ...a.up } : a);
export const upText = (k, a) => (k.endsWith('+') ? ` Upgraded: +2 to its numbers${a?.up_text ? `, and ${a.up_text}` : ''}.` : '');
const actionDef = k => upDef(k);
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
      h('div#topbar'), h('div#party.party'), h('div#forecast'), h('div#partyev'), h('div#actionbar'), h('div#log'), h('div#hint'),
      h('div.zoom', null,
        h('button.btn.icon', { 'aria-label': 'Zoom in', tip: 'Zoom in\nOr use the mouse wheel', onclick: () => map?.zoomBy(1) }, icon('plus')),
        h('button.btn.icon', { 'aria-label': 'Zoom out', tip: 'Zoom out', onclick: () => map?.zoomBy(-1) }, h('span', { style: { fontSize: '20px', lineHeight: 1 } }, '−')),
        h('button.btn.icon', { 'aria-label': 'Find my hero', tip: 'Find my hero', onclick: () => map?.centerOn(selHero().tile) }, icon('target'))),
      h('div.minimap', { tip: 'The whole map\nClick to look there. Gold: objectives; red: raids.' }, h('canvas#minimap', { width: 220, height: 134, 'aria-label': 'Minimap' })),
      h('div#drawer'), h('div#modal'), h('div#combat'), h('div#hextip.hextip', { hidden: true }), h('div#menu'));
    $('app').replaceChildren(root);
    mapWorld = S.world;
    map = new MapView($('map'), S.world, { click: onTileClick, hover: onTileHover });
    map.centerOn(g.heroes[sel()]?.tile ?? S.world.start, false);
    map.attachMinimap($('minimap'));
  }
  updateMap();
  renderTopbar();
  renderParty();
  renderActionbar();
  renderForecast();
  renderPartyEvents();
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
  map.setState(g, { sel: h0, mine: mine(), reach: planning ? reach(S.world, g, S.static, h0) : null, preview: UI.preview,
    regions: S.static.regions, squallR: S.static.squall?.r });
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
    lines.push(h('b', null, placeTitle(p) || terrainName(t, ter)));
    if (p) lines.push(h('div', null, placeText(p)));
    lines.push(h('div.muted', null, `${terrainName(t, ter)}${S.world.reg[t] ? ' · ' + regions[S.world.reg[t]] : ''}`));
    for (const note of seaNotes(t, ter)) lines.push(h('div.sea-note', null, note));
    for (const note of biomeNotes(t, ter)) lines.push(h('div.sea-note', null, note));
    const storm = (g.squalls || []).find(q => hexDist(t, q.tile) <= S.static.squall.r);
    if (storm) { const K = S.static.biome.storms[storm.kind || 'squall']; lines.push(h('div.sea-note', null, `In a ${K.name}: whoever stands here sees only ${K.sight === 1 ? 'a hex' : `${K.sight} hexes`} around.`)); }
    const vis = visibleTiles(g);
    const gr = g.groups.find(x => x.tile === t);
    if (gr && (vis.has(t) || gr.lair || gr.raid)) lines.push(h('div', { style: { color: 'var(--danger)' } }, (gr.occupy ? 'Holding the town: ' : gr.raid ? 'Raiders: ' : gr.sea ? 'Sea beasts: ' : gr.lair ? (p?.kind === 'wreck' ? 'Guards: ' : 'Lair: ') : 'Enemies: ') + gr.foes.map((k, i) => foeName(k, gr.aff?.[i])).join(', ')));
    if (gr?.sea) lines.push(h('div.muted', null, `At high tide they hunt skiffs within ${S.static.sea.hunt} hexes, a hex a turn; at low tide they lie still. They can’t reach you on land.`));
    const raid = gr?.raid && (g.raids || []).find(r => r.g === gr.id);
    if (raid && !raid.occupy) lines.push(h('div.prize', null, `From ${S.static.dungeons[raid.reg]}, marching on ${g.places[raid.to]?.name || 'a town'}: ${raid.road.length} turn${raid.road.length === 1 ? '' : 's'} away. Beat them on the road for ${S.static.sea.raid_bounty} gold each, and ${S.static.dungeons[raid.reg]}’s garrison skips its next growth. If they get there with nobody in town, they take it.`));
    if (gr && vis.has(t) && !gr.sea) { const gt = groundLine(ter, t); if (gt) lines.push(h('div.ground-note', null, gt)); }
    if (gr?.prize) lines.push(h('div.prize', null, `Guards a prize: ${S.static.items[gr.prize].name} (rare ${S.static.items[gr.prize].slot}), in the loot when they’re beaten.`));
    if (p?.kind === 'dungeon' && !g.cleared?.includes(p.region) && g.dnext?.[p.region]) {
      const nx = g.dnext[p.region], step = (g.dungeon?.[p.region] || 0) + 1;
      lines.push(h('div', { style: { color: 'var(--danger)' } }, `Fight ${step} of 3 (${S.static.paths[nx.path]?.name || ''}): ` + nx.foes.map(x => typeof x === 'string' ? foeName(x) : foeName(x.k, x.aff)).join(', ')));
      lines.push(h('div', null, garrisonText(p.region)));
    }
    if (gr?.crew) lines.push(h('div.prize', null, `Wanted: ${gr.crew}. They run from you, a hex a turn.`));
    for (const q of (g.quests || []).filter(q => !q.done && !q.failed && q.goal === t))
      lines.push(h('div.prize', null, q.kind === 'trail' ? `Quest, ${questLine(q)}: ${jobText(q)}.` : `Job for ${q.src}: ${jobText(q)} (${q.left} turn${q.left === 1 ? '' : 's'} left).`));
    const mer = (g.merchants || []).find(m => m.tile === t);
    if (mer) lines.push(h('div.prize', null, `${cap(mer.name)}, a travelling merchant: ${merchantWhere(mer)}. Sells ${mer.stock.length} rare and legendary piece${mer.stock.length === 1 ? '' : 's'}; stop here to buy.`));
    const opp = (g.opps || []).find(o => o.tile === t);
    if (opp) lines.push(h('div.prize', null, `${S.static.opps[opp.kind].name}, for ${opp.left} more turn${opp.left === 1 ? '' : 's'}: ${S.static.opps[opp.kind].text}`));
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

// What the sea's extras mean for a skiff on this hex.
function seaNotes(t, ter) {
  const sea = seaMap(S.world), out = [];
  if (sea.cur.has(t)) out.push('A current: a skiff riding it downstream pays nothing a hex; against it, 2.');
  if (sea.reef.has(t)) out.push(S.game.tide === 'low' ? 'A reef, its rocks out at low tide: no skiff can cross until high tide.' : 'A reef under the high tide: a skiff can cross until the tide goes out.');
  if (sea.pool.has(t)) out.push('A whirlpool: no skiff can enter it.');
  else if (sea.swirl.has(t) && ter === 'deep') out.push('By a whirlpool: a skiff pays 1 more here.');
  return out;
}
// A hex's terrain name: the region's own (Black sand, Deep jungle...) where it has one.
function terrainName(t, ter) {
  if (ter === 'ice') return 'Frozen sea';
  const reg = worldRegions().includes(S.world.reg[t]) ? S.world.reg[t] : null;
  return (reg && S.static.biome.skins[reg]?.[ter]) || TERRAIN_NAME[ter] || ter;
}
// What the other regions' land does here (Game's biome rules).
function biomeNotes(t, ter) {
  const g = S.game, B = S.static.biome, out = [];
  const reg = worldRegions().includes(S.world.reg[t]) ? S.world.reg[t] : null;
  const sea = seaMap(S.world);
  if (g.lava?.[t] != null) out.push(`Lava: nobody can cross it. It cools in ${g.lava[t]} turn${g.lava[t] === 1 ? '' : 's'}.`);
  if (sea.sink.has(t)) out.push(`Quicksand: stepping in costs ${B.sink} moves (a whole turn's walk).`);
  if (ter === 'ice') out.push('The frozen sea: walk across it (2 moves a hex), but no skiff can pass.');
  if (reg === 'jungle' && ter === 'forest') out.push(g.trails?.[t] != null ? `A trail cut through the jungle: 1 move for anyone, for ${g.trails[t]} more turn${g.trails[t] === 1 ? '' : 's'}.`
    : `Deep jungle: ${B.jungle} moves to cross (a trail cut by walking through it costs 1 for everyone for ${B.trail_turns} turns). Inside it you see only ${B.jungle_sight} hexes.`);
  if (reg === 'frost' && (ter === 'hills' || ter === 'peak')) out.push('End a turn up here, away from a town or camp, and you get Frostbite (−5 max HP until you thaw by a fire).');
  if (reg === 'petrified') out.push('In the Stillwood your blessings and curses don’t run down.');
  if (reg === 'dream' && !g.places[t]) out.push('Rest here as if at a camp, and dream.');
  if (reg === 'heaven') out.push(`Resting here heals ${B.grace}% more; shrines bless everyone on their hex.`);
  if (reg === 'crystal') out.push(`You see ${B.prism_sight} hexes further here, but enemies notice you from further off too.`);
  return out;
}
// A battleground's rule for a fight on this terrain (Game.ground_of), for a hero walking in.
function groundLine(ter, t) {
  const G = S.static.grounds;
  const reg = t != null && worldRegions().includes(S.world.reg[t]) ? S.world.reg[t] : null;
  const own = { ash: ['grass', 'beach', 'embers'], dunes: ['grass', null, 'sinking'], petrified: ['forest', null, 'statues'], heaven: ['grass', null, 'hallowed'],
    crystal: ['forest', null, 'resonance'], dream: ['grass', null, 'lulled'], frost: ['grass', null, 'snowdrift'] }[reg];
  if (own && (ter === own[0] || ter === own[1])) return `${G[own[2]].name}: ${G[own[2]].text}`;
  if (ter === 'hills' || ter === 'peak') return `${G.high.name}: walk in and the enemies hold the slope (they start with Armor). Let them come to you and you hold it (6 Armor each).`;
  if (ter === 'forest') return `${G.woods.name}: walk in and they’re caught in the trees (Weak for a round). Let them come to you and you are.`;
  return null;
}
// A forecast fight's battleground, in words.
function groundSay(gr) {
  if (!gr) return '';
  const G = S.static.grounds[gr.k];
  if (gr.k !== 'high' && gr.k !== 'woods') {
    const who = gr.side === 'both' ? 'it hits both sides' : gr.k === 'statues' ? 'they start asleep' : gr.side === 'heroes' ? 'they walked into it' : 'you walk into it';
    return `${G.name}: ${who}`;
  }
  const who = gr.k === 'high' ? (gr.side === 'heroes' ? 'you hold the slope' : 'they hold the slope') : (gr.side === 'heroes' ? 'they’re caught in the trees' : 'you’re caught in the trees');
  return `${G.name}: ${who}`;
}

function placeTitle(p) {
  if (!p) return null;
  const st = S.static;
  return {
    town: p.name + (p.spec ? ` · ${st.town_specs[p.spec].name}` : ''), dungeon: st.dungeons[p.region], peak: 'The Drowned Peak',
    shrine: p.dark ? 'Dark shrine' : 'Shrine', camp: 'Camp', event: p.title && !p.done ? p.title : 'Something curious',
    wreck: p.guard && !p.done ? 'Guarded wreck' : 'Wreck', lair: 'Lair', cache: 'Buried cache',
    cove: 'Smugglers’ cove', flotsam: 'Flotsam', lookout: 'Lookout', grotto: p.grotto === 'spring' ? 'Grotto spring' : 'Hidden grotto',
    oasis: 'Oasis', fossil: 'Fossil bed', geode: 'Geode', gate: 'Light-gate', quest: p.name, beacon: p.lit ? 'Lit beacon' : 'Beacon tower',
  }[p.kind] + (p.kind === 'shrine' && p.sea ? ' (drowned)' : '') + (p.occupied ? ' · occupied' : '');
}
const RISK = { safe: 'Nothing here can hurt you.', risky: 'A roll could go badly.', fight: 'It could turn into a fight.' };
const cap = s => s[0].toUpperCase() + s.slice(1);
// This run's three objective regions (drawn per world; a world from an older save has the first three).
// Beacons the party has lit, and where a travelling merchant is (in a town, or on its way to one).
const litBeacons = () => Object.entries(S.game.places).filter(([, p]) => p.kind === 'beacon' && p.lit).map(([t]) => +t);
function merchantWhere(m) {
  const g = S.game, here = g.places[m.tile], to = g.places[m.to];
  if (here?.kind === 'town') return `in ${here.name}${m.wait ? `, for ${m.wait} more turn${m.wait === 1 ? '' : 's'}` : ', leaving soon'}`;
  return to ? `on the road to ${to.name}` : 'on the road';
}
// Where a beacon is, in words a player knows: by its nearest town, and its region if this run drew it.
function beaconName(t) {
  const towns = Object.entries(S.game.places).filter(([, p]) => p.kind === 'town').map(([u, p]) => [+u, p.name]);
  const near = towns.sort((a, b) => hexDist(a[0], t) - hexDist(b[0], t))[0];
  const reg = S.world.reg[t], region = worldRegions().includes(reg) ? S.static.regions[reg] : t === S.world.peak || reg === 'peak' ? 'the central island' : null;
  return { title: near ? `Near ${near[1]}` : cap(region || 'a far island'), region };
}
const merchantHere = h0 => (S.game.merchants || []).find(m => m.tile === S.game.heroes[h0].tile);
const onLitBeacon = h0 => { const hero = S.game.heroes[h0], p = S.game.places[hero.tile]; return p?.kind === 'beacon' && p.lit && !hero.afloat; };
const worldRegions = () => S.world?.regions || ['coral', 'keys', 'storm'];
// A job in words: what to do, and what it pays.
function jobText(q) {
  const g = S.game;
  if (q.kind === 'trail') return S.static.quests[q.key].goals[Math.min(q.step, 2) - 1];
  if (q.kind === 'deliver') return `deliver a parcel to ${q.name}`;
  if (q.kind === 'lair') return 'clear the lair';
  if (q.kind === 'bounty') return `catch ${q.crew}`;
  if (q.stage === 'return') return `${g.heroes[q.carrier]?.name || 'someone'} brings the cargo back to ${q.src}`;
  return `fetch the cargo from a ${q.guarded ? 'guarded ' : ''}wreck`;
}
// A quest's place in the log: its name, the step it's on, what it ends with.
const questLine = q => `${S.static.quests[q.key].name}${q.done ? '' : ` (step ${q.step + 1} of 3)`}`;
const questTip = q => `Quest: ${S.static.quests[q.key].name}\nNext: ${jobText(q)}\nIt ends with ${S.static.quests[q.key].reward}. No time limit.`;
function rewardText(r) {
  if (!r) return '';
  const st = S.static;
  const extra = { loot: 'a pick of loot for whoever finishes it', item: `${st.items[r.item]?.name} (rare ${st.items[r.item]?.slot})`, revive: '+1 revive',
    trade: `a free go at the ${st.town_specs[r.spec]?.name.toLowerCase()}`, restock: 'the town restocks its shop with better wares' }[r.type];
  return `${r.gold} gold each, and ${extra}`;
}
// What an objective's growing garrison adds to its boss fight, and when it next grows.
function garrisonText(reg) {
  const g = S.game, gs = g.garrison?.[reg];
  if (!gs) return '';
  const now = gs.n ? `Garrison: ${gs.foes.map(k => foeName(k)).join(', ')} join the boss fight${gs.boss ? `, and the boss has ${gs.boss}% more health` : ''}.`
    : 'Garrison: none yet. Clear it before it grows to weaken the Drowned Crown.';
  return `${now} Grows in ${g.garrison_next} turn${g.garrison_next === 1 ? '' : 's'}${gs.n >= 6 ? ' (at its largest)' : ''}.`;
}
function placeText(p) {
  const g = S.game;
  switch (p.kind) {
    case 'beacon': return p.lit ? `Lit. Stand on it to travel to any other lit beacon (${litBeacons().length} lit) in one move.`
      : `Light it by ending a turn here: the land ${S.static.travel.beacon_sight} hexes round is revealed, and lit beacons carry the party between them.`;
    case 'quest': {
      const Q = S.static.quests[p.q], q = (g.quests || []).find(x => x.kind === 'trail' && x.key === p.q);
      return q?.done ? `${Q.name}: done.` : q ? `${Q.name}: under way (next, ${jobText(q)}).`
        : `Offers a quest, ${Q.name}: three steps across ${S.static.regions[p.q]}, ending with ${Q.reward}. Stop here to hear it.`;
    }
    case 'oasis': return 'Fresh water under the palms: full health and every curse lifted, once for each hero.';
    case 'fossil': return p.done ? 'Dug out.' : `Old bones in the stone, and older treasure: a pick of better loot and ${S.static.biome.fossil_xp} XP for whoever digs.`;
    case 'geode': return p.done ? 'Cracked open and emptied.' : 'A geode as big as a cart. Crack it for an enchant material.';
    case 'gate': return `End your move here and the light carries you to its twin across the sea${p.to != null && g.seen[p.to] === '1' ? '' : ' (somewhere you haven’t seen yet)'}.`;
    case 'town': return p.occupied ? 'Raiders hold it: its shop, inn, board and trade are shut. Walk in to fight them and free it '
      + `(${S.static.sea.free_gold} gold each, and a better-stocked shop).`
      : 'Shop, inn and notice board' + (p.docks ? ', with docks for skiffs.' : '.') + (p.spec ? ` ${S.static.town_specs[p.spec].text}` : '');
    case 'dungeon': return g.cleared.includes(p.region) ? 'Cleared.' : `An objective: ${3 - (g.dungeon[p.region] || 0)} fights deep, the way forking between them. No retreat.`;
    case 'peak': return g.cleared.length >= 3 ? 'The Drowned Crown waits at the top.' : `Sealed until all three objectives are cleared (${g.cleared.length} of 3).`;
    case 'shrine': return p.dark ? 'A stronger blessing than a shrine’s, at a price. Once for each hero.'
      : p.sea && p.buff ? `Out at sea, by skiff only. ${S.static.buffs[p.buff].name} (${S.static.buffs[p.buff].text.replace(/\.$/, '')}, ${S.static.buffs[p.buff].turns} turns), once for each hero.${p.mat_taken ? '' : ' The first to come also finds an enchant material.'}`
      : `${p.buff ? `${S.static.buffs[p.buff].name} (${S.static.buffs[p.buff].text.replace(/\.$/, '')}, ${S.static.buffs[p.buff].turns} turns)` : 'A blessing'}, once for each hero.`;
    case 'camp': return 'Rest here to heal half your HP.';
    case 'event': return p.done ? 'Already seen to.' : `${RISK[p.risk] || 'Step on it to find out.'}${p.needs?.length ? ` ${/^[AEIOU]/.test(S.static.classes[p.needs[0]].name) ? 'An' : 'A'} ${p.needs.map(k => S.static.classes[k].name).join(' or ')} would have another option.` : ''}`;
    case 'wreck': return p.done ? 'Picked clean.' : p.guard ? 'Enemies are camped on it. Beat them for a pool of rare loot and an enchant material.' : `${cap(p.rarity || 'some')} loot, for whoever gets there first.`;
    case 'cache': return p.done ? 'Dug up.' : 'The X from the torn chart: good loot and gold.';
    case 'lair': return p.done ? 'Cleared.' : 'A nest of tougher enemies, guarding good loot.';
    case 'cove': return p.done ? 'Emptied.' : `Out at sea, by skiff only: a smugglers’ stash (${S.static.sea.cove_gold} gold and a pick of uncommon or rare loot).`;
    case 'flotsam': return p.done ? 'Picked over.' : `Out at sea, by skiff only: ${S.static.sea.flotsam_gold} gold and a little loot.`;
    case 'lookout': return p.done ? 'Climbed: the land around is on your map.' : `Climb it to see everything ${S.static.lookout_sight} hexes around, hidden grottos too.`;
    case 'grotto': return p.done ? 'Already found and taken.' : p.grotto === 'spring' ? 'A clear spring: full health for whoever drinks, and a revive for the party.'
      : `An old hoard: ${S.static.sea.grotto_gold} gold, a pick of rare loot and an enchant material.`;
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
      h('div.stat' + (g.next_rise === 1 ? '.tide-soon' : g.rises >= g.grow_from ? '.warn' : ''), { tip: `The Great Tide\nRises every ${g.rise_every} turns, next in ${g.next_rise}. Each one makes every enemy stronger, brings two or three arrivals from the sea (wreckage and visitors early on, raiders, war-bands and worse later), and grows the garrisons of the objectives you haven’t cleared.${g.tides ? `\nRisen ${g.tides} time${g.tides === 1 ? '' : 's'}.` : ''}${(g.tidenews || []).length ? `\nLast time: ${g.tidenews.map(n => n.name).join('; ')}.` : ''}${g.rises >= g.grow_from ? '\nMore enemies come ashore now.' : ''}` },
        icon('wave'), h('b', null, g.next_rise === 1 ? 'Great Tide next turn!' : `Great Tide in ${g.next_rise}`)),
      h('div.stat', { tip: `Party level ${g.level}\n${g.xp_next ? `${g.xp} / ${g.xp_next} XP` : 'Max level'}\nXP is shared: everyone levels together.` },
        icon('star'), h('b', null, `Level ${g.level}`), h('div.xpbar', null, h('i', { style: { width: xpPct + '%' } }))),
      h('div.stat', { tip: 'Revives\nShared by the party. A knocked-down hero who’s still down at the end of a fight uses one.' },
        icon('feather'), h('b', null, g.revives)),
      goalStat(g, `Objectives\n${worldRegions().map(r => `${S.static.dungeons[r]} (${S.static.regions[r]}): ${g.cleared.includes(r) ? 'cleared' : `not yet${g.garrison?.[r]?.n ? `, garrison +${g.garrison[r].n}` : ''}`}${S.static.biome.rules[r] ? `\n  ${S.static.biome.rules[r]}` : ''}`).join('\n')}\nEach Great Tide (every ${g.rise_every} turns) the garrisons of those not yet cleared grow (next in ${g.garrison_next}).\nEach objective you clear makes the ones left harder: their enemies now have ${g.dungeon_step?.hp ?? 100}% health and deal ${g.dungeon_step?.dmg ?? 100}% damage.${g.crown_cut ? `\nThe Drowned Crown is ${g.crown_cut}% weaker for objectives cleared early.` : ''}`)),
    h('div.right', null,
      h('button.btn.icon.ghost', { 'aria-label': 'Log', tip: 'Log', onclick: () => { UI.log = !UI.log; saved.logOpen = UI.log; persist(); renderLog(); } }, icon('list')),
      h('button.btn.icon.ghost', { 'aria-label': 'Menu', tip: 'Menu', onclick: () => { UI.menu = !UI.menu; UI.menuFresh = true; renderMenu(); } }, icon('menu')))));
}

// The run's goal in the top bar: the nearest objective not yet cleared (the Drowned Peak once all
// three are), by name; clicking it finds it on the map, and clicking again moves on to the next one.
// An objective not found yet points at the middle of its region instead.
let midOf = null;
function regionMiddle(r) {
  if (midOf?.world !== S.world) midOf = { world: S.world };
  if (!(r in midOf)) {
    const ts = [];
    S.world.reg.forEach((x, t) => { if (x === r) ts.push(t); });
    let best = ts[0], bestSum = Infinity;
    for (const t of ts) {
      let sum = 0;
      for (let i = 0; i < ts.length; i += 3) sum += hexDist(t, ts[i]);
      if (sum < bestSum) { bestSum = sum; best = t; }
    }
    midOf[r] = best;
  }
  return midOf[r];
}
function goalTargets(g) {
  const from = g.heroes[sel()]?.tile ?? g.heroes[0].tile;
  const all = Object.entries(g.places).map(([t, p]) => [+t, p]);
  const left = worldRegions().filter(r => !g.cleared.includes(r)).map(r => {
    const at = all.find(([, p]) => p.kind === 'dungeon' && p.region === r);
    const mark = (S.world.landmarks || []).find(m => m.region === r);
    return { t: at ? at[0] : mark ? mark.tile : regionMiddle(r), name: S.static.dungeons[r], found: !!(at || mark), where: S.static.regions[r] };
  }).filter(x => x.t != null);
  if (!left.length) {
    const peak = all.find(([, p]) => p.kind === 'peak');
    left.push({ t: peak ? peak[0] : S.world.peak, name: 'The Drowned Peak', found: true });
  }
  return left.map(x => ({ ...x, far: hexDist(from, x.t) })).sort((a, b) => b.found - a.found || a.far - b.far);
}
function goalStat(g, tip) {
  const goals = goalTargets(g);
  const first = goals[0];
  const pips = h('span.pips', null, ...[0, 1, 2].map(i => h('i' + (i < g.cleared.length ? '.on' : ''))));
  if (!first) return h('div.stat', { tip }, icon('flag'), pips);
  const next = goals.length > 1 ? `\nClick again for ${goals.slice(1).map(x => x.name).join(', then ')}.` : '';
  return h('button.stat.goal', {
    tip: `${tip}\n\nNext: ${first.name}, ${first.found ? `${first.far} hex${first.far === 1 ? '' : 'es'} from ${g.heroes[sel()]?.name ?? 'you'}.\nClick to find it on the map.` : `not found yet: it's somewhere in ${first.where}.\nClick to look that way.`}${next}`,
    onclick: () => {
      // clicking again moves on to the next one, until the turn or the selected hero changes
      const key = `${g.turn}:${sel()}`;
      UI.goalAt = UI.goalKey === key ? (UI.goalAt + 1) % goals.length : 0;
      UI.goalKey = key;
      map?.centerOn(goals[UI.goalAt].t);
    },
  }, icon('flag'), pips, h('span.lbl', null, 'Next'), h('b', null, first.name));
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

// A level-up pick flies from the dialog into its hero's card in the party column, which flashes
// gold as it lands.
function flyToHero(el, x) {
  const to = $('party')?.children[x];
  if (!el || !to || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const a = el.getBoundingClientRect(), b = to.getBoundingClientRect();
  const ghost = el.cloneNode(true);
  Object.assign(ghost.style, { position: 'fixed', left: a.left + 'px', top: a.top + 'px', width: a.width + 'px', height: a.height + 'px', margin: 0, zIndex: 60, pointerEvents: 'none' });
  ghost.classList.add('flying');
  document.body.append(ghost);
  const dx = b.left + b.width / 2 - (a.left + a.width / 2), dy = b.top + b.height / 2 - (a.top + a.height / 2);
  const s = Math.min(0.35, b.width / a.width);
  ghost.animate([{ transform: 'none', opacity: 1 }, { transform: `translate(${dx * 0.55}px, ${dy * 0.45 - 60}px) scale(0.6) rotate(-6deg)`, opacity: 1, offset: 0.55 },
    { transform: `translate(${dx}px, ${dy}px) scale(${s})`, opacity: 0.2 }], { duration: 720, easing: 'cubic-bezier(0.4, 0, 0.6, 1)' }).onfinish = () => {
    ghost.remove();
    $('party')?.children[x]?.animate([{ boxShadow: '0 0 0 2px #e0bb62, 0 0 26px rgba(224,187,98,0.8)' }, { boxShadow: 'none' }], { duration: 700 });
  };
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
        hero.cls === 'dragonborn' ? h('span', { tip: `Scales ${hero.scales || 0} / 5: 1 Armor each at the start of every fight round; Breath sheds them. They stay between fights.` }, icon('shield'), `${hero.scales || 0} Scales`) : null,
        Object.keys(hero.buffs).length ? h('span', { tip: Object.keys(hero.buffs).map(b => `${S.static.buffs[b].name}: ${S.static.buffs[b].text} (${S.static.buffs[b].perm ? 'for good' : `${hero.buffs[b]} turns`})`).join('\n') }, icon('spark'), Object.keys(hero.buffs).length) : null),
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
// A fallen hero can give their spirit die to someone fighting, once a round.
function giveBtns(x, btns) {
  const g = S.game, f = g.fight, sp = f?.spirit?.[x];
  if (g.phase !== 'fight' || !sp || sp.used) return false;
  for (const y of f.heroes.filter(y => f.hs[y] && !f.hs[y].down && !f.hs[y].fled)) {
    btns.push(h('button.btn.primary', { tip: `Give ${g.heroes[y].name} a die showing ${sp.v} for this round.`, onclick: () => send({ t: 'spirit', h: x, to: y }) },
      icon('dice'), `${sp.v} to ${g.heroes[y].name}`));
  }
  return true;
}
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
    giveBtns(h0, btns);
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
      const mer = merchantHere(h0);
      if (mer) btns.push(h('button.btn', { tip: `${cap(mer.name)}\nRare and legendary gear for sale`, onclick: () => openDrawer('merchant') }, icon('coin'), 'Merchant'));
      if (onLitBeacon(h0) && litBeacons().length > 1)
        btns.push(h('button.btn' + (p.warp != null ? '.primary' : ''), { tip: 'Travel to another lit beacon\nIt takes your whole move.', onclick: () => beaconPicker(h0) }, icon('flame'), p.warp != null ? 'Beacon set' : 'Beacon'));
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
const LAND = { event: 'finds something curious', wreck: 'loots a wreck', shrine: 'reaches a shrine', town: 'reaches town', camp: 'reaches a camp', lair: 'reaches a lair',
  cache: 'digs up the cache', cove: 'searches the cove', flotsam: 'hauls in the flotsam', lookout: 'climbs the lookout', grotto: 'enters the grotto', drift: 'hauls in the drifting cargo', healer: 'is seen to by the healer', job: 'finishes a job', cargo: 'picks up the salvage', quest: 'takes the quest on a step' };
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
  return { where: where + (f.job ? ' (a job)' : ''), with: f.heroes.map(x => g.heroes[x].name) };
}
// The last rise's arrivals still on the map: an unlooted wreck, a group not yet beaten (where it is now).
function tideNews(g) {
  const out = [];
  for (const n of g.tidenews || []) {
    let at = n.tile;
    if (n.g != null) {
      const gr = g.groups.find(x => x.id === n.g);
      if (!gr) continue;
      at = gr.tile;
    } else if (n.k === 'wreckage' && g.places[n.tile]?.done) continue;
    else if (n.k === 'boon' && !(g.opps || []).some(o => o.tile === n.tile)) continue;
    out.push({ ...n, at });
  }
  return out;
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
      if (fight.ground) text += ` · ${groundSay(fight.ground)}`;
      if (fight.raid) text += fight.raid === 'free' ? ' · freeing the town' : ' · stopping the raid';
    } else if (p.warp != null) text = `travels by beacon (${beaconName(p.warp).title.replace(/^Near /, 'near ')})`;
    else if (p.rest) text = 'rests';
    else if (fc.lands[x]) text = LAND[fc.lands[x]] || 'arrives';
    else if (p.path?.length) text = 'moves';
    else text = p.ready ? 'stays put' : 'hasn’t planned yet';
    lines.push(h('div.fc-line' + (fight ? '.fight' : ''), { style: { '--seat': seat(x) } },
      h('i.dot'), h('b', null, hero.name), h('span', null, ' ' + text), p.ready ? h('span.ok', null, ' ✓') : null));
  });
  // below the heroes' lines, the world's news, in a list of its own that scrolls when it's long
  const heroLines = lines.splice(0);
  const steps = fc.steps.length;
  if (steps) lines.push(h('div.fc-line.muted', null, icon('skull'), ` ${steps} enemy group${steps > 1 ? 's' : ''} will step toward you (red arrows).`));
  // what the last rise of the tide brought, while it's still there
  for (const n of tideNews(g)) {
    lines.push(h('div.fc-line.opp.tide', { tip: `${n.text}\nClick to find it on the map.`, onclick: () => map?.centerOn(n.at) },
      icon('wave'), h('b', null, ` ${n.name}`), h('span', null, n.where ? ` (${n.where})` : '')));
  }
  // raids on the road, and towns they hold
  for (const r of g.raids || []) {
    const town = g.places[r.to]?.name || 'a town';
    const text = r.occupy ? ` hold ${town}: free it to reopen the town` : ` march on ${town}: ${r.road.length} turn${r.road.length === 1 ? '' : 's'} away`;
    lines.push(h('div.fc-line.opp.raid', { tip: `Raiders from ${S.static.dungeons[r.reg]}.${r.occupy ? '' : ' Beat them on the road and its garrison skips its next growth; if they reach the town with nobody in it, they take it.'}\nClick to find them on the map.`, onclick: () => map?.centerOn(r.tile) },
      icon('flag'), h('b', null, ' Raiders'), h('span', null, text)));
  }
  for (const q of g.squalls || []) {
    const K = S.static.biome.storms[q.kind || 'squall'];
    lines.push(h('div.fc-line.opp.squall', { tip: `Inside a ${K.name} you see only ${K.sight === 1 ? 'a hex' : `${K.sight} hexes`} around you. It drifts a hex a turn (the dashed ring is where it goes next).\nClick to find it on the map.`, onclick: () => map?.centerOn(q.tile) },
      icon('wave'), h('b', null, ` ${cap(K.name)}`), h('span', null, ` over ${S.static.regions[S.world.reg[q.tile]] || 'the sea'}: ${q.left} turn${q.left === 1 ? '' : 's'} left`)));
  }
  if (g.erupt != null && g.erupt <= 1) {
    const crater = (S.world.landmarks || []).find(m => m.region === 'ash');
    lines.push(h('div.fc-line.opp.raid', { tip: `The volcano on Cinderreach erupts ${g.erupt <= 0 ? 'now' : 'next turn'}: lava runs down its slopes and blocks the hexes it covers for ${S.static.biome.lava_turns} turns. It never covers a hero, a town or a place.\nClick to find it on the map.`, onclick: () => crater && map?.centerOn(crater.tile) },
      icon('flame'), h('b', null, ' Eruption'), h('span', null, ' next turn on Cinderreach')));
  }
  for (const m of g.merchants || []) {
    lines.push(h('div.fc-line.opp', { tip: `A travelling merchant with rare and legendary gear, dear (×${S.static.travel.markup}). Stand on its hex to buy; it waits for you a turn or two.\nClick to find it on the map.`, onclick: () => map?.centerOn(m.tile) },
      icon('coin'), h('b', null, ` ${cap(m.name)}`), h('span', null, `: ${merchantWhere(m)}`)));
  }
  // chances that won't wait, and debts that will come
  for (const o of g.opps || []) {
    const where = o.kind === 'ship' ? ` at ${g.places[o.tile]?.name || 'a town'}` : '';
    lines.push(h('div.fc-line.opp', { tip: `${S.static.opps[o.kind].text}\nClick to find it on the map.`, onclick: () => map?.centerOn(o.tile) },
      icon('spark'), h('b', null, ` ${S.static.opps[o.kind].name}`), h('span', null, `${where}: ${o.left} turn${o.left === 1 ? '' : 's'} left`)));
  }
  for (const q of (g.quests || []).filter(q => !q.done && !q.failed)) {
    if (q.kind === 'trail') {
      lines.push(h('div.fc-line.opp.job', { tip: `${questTip(q)}\nClick to find it on the map.`, onclick: () => q.goal != null && map?.centerOn(q.goal) },
        icon('star'), h('b', null, ' Quest'), h('span', null, `: ${jobText(q)}`)));
      continue;
    }
    lines.push(h('div.fc-line.opp.job', { tip: `Job for ${q.src}: ${rewardText(q.reward)}\nClick to find it on the map.`, onclick: () => q.goal != null && map?.centerOn(q.goal) },
      icon('scroll'), h('b', null, ' Job'), h('span', null, `: ${jobText(q)}, ${q.left} turn${q.left === 1 ? '' : 's'} left`)));
  }
  for (const l of g.loans || []) {
    if (l.left <= 3) lines.push(h('div.fc-line.muted', null, icon('coin'), ` The moneylender comes for ${g.heroes[l.h].name}’s 60 gold in ${Math.max(0, l.left)} turn${l.left === 1 ? '' : 's'}.`));
  }
  const toggle = () => { UI.fc = !UI.fc; saved.fcOpen = UI.fc; persist(); renderForecast(); };
  const head = h('button.fc-head', { 'aria-expanded': String(UI.fc), tip: UI.fc ? 'Hide' : 'Show what this turn will do', onclick: toggle },
    h('span.eyebrow', null, 'This turn'), UI.fc ? null : h('span.fc-count', null, `${heroLines.length + lines.length} line${heroLines.length + lines.length === 1 ? '' : 's'}`), icon(UI.fc ? 'chevron-down' : 'chevron-up'));
  el.replaceChildren(h('div.forecast' + (UI.fc ? '' : '.closed'), { role: 'status', 'aria-live': 'polite' }, head,
    ...(UI.fc ? [...heroLines, lines.length ? h('div.fc-news', null, ...lines) : null, h('div.fc-foot', null, 'Hidden enemies can still ambush you.')] : [])));
}

// An ally's event, live on everyone else's screen: what it is, each choice with its odds and what's at
// stake for the party (a fight pulls in anyone within a hex; a shared outcome reaches everyone on the
// hex; a party check takes your die too, if you chip in), and a button to suggest a choice. Opens by
// itself when the ally asks the party; otherwise it's a one-line strip that opens on a click.
function renderPartyEvents() {
  const el = $('partyev');
  if (!el) return;
  const g = S.game, me = mine();
  const cards = [];
  g.heroes.forEach((hero, x) => {
    const d = (g.pending[x] || [])[0];
    if (me.includes(x) || !hero.alive || !d || d.type !== 'event' || combatOpen()) return;
    const ev = S.static.events[d.key];
    const myHero = me.find(y => g.heroes[y].alive);
    const near = myHero != null && hexDist(g.heroes[myHero].tile, hero.tile) <= 1;
    const here = myHero != null && g.heroes[myHero].tile === hero.tile;
    const okey = `${x}:${d.key}:${g.turn}`, open = UI.evOpen?.[okey] ?? !!d.asked;
    const mySugg = myHero != null ? d.sugg?.[myHero] : undefined;
    const flags = new Set();
    for (const ch of ev.choices) for (const o of [ch.ok, ch.bad, ch.great]) {
      if (o?.fight) flags.add('fight');
      if (o?.all) flags.add('all');
    }
    if (ev.choices.some(ch => ch.check?.die === 'party')) flags.add('party');
    const flagText = { fight: near ? 'Could start a fight: you’re within a hex, so you’d be pulled in.' : 'Could start a fight (anyone within a hex is pulled in).',
      all: here ? 'Good outcomes reach you too: you’re on the hex.' : 'Good outcomes reach everyone on the hex.',
      party: here ? 'Has a party check: you can chip in your die.' : 'Has a party check (allies on the hex can chip in).' };
    const head = h('button.pe-head', { onclick: () => { (UI.evOpen ||= {})[okey] = !open; renderPartyEvents(); }, 'aria-expanded': String(open) },
      h('i.dot', { style: { '--seat': seat(x) } }), h('b', null, hero.name), h('span', null, d.huddle ? ' is rolling a party check: ' : d.asked ? ' asks the party: ' : ' is at: '),
      h('span.pe-title', null, ev.title), icon(open ? 'chevron-up' : 'chevron-down'));
    const body = !open ? null : [
      h('p.pe-text', null, ev.text),
      flags.size ? h('div.pe-flags', null, ...[...flags].map(f => h('span.chip' + (f === 'fight' && near ? '.warn' : ''), null, flagText[f]))) : null,
      h('div.pe-choices', null, ...ev.choices.map((ch, n) => {
        const ck = ch.check ? eventOdds(x, ch.check) : null;
        const fans = Object.entries(d.sugg || {}).filter(([, v]) => v === n).map(([y]) => g.heroes[y].name);
        const missing = ch.need && !g.heroes.some(y => y.alive && y.cls === ch.need);
        return h('div.pe-choice' + (mySugg === n ? '.mine' : '') + (missing ? '.off' : ''), null,
          h('div.pe-label', null, h('b', null, ch.label), ck ? h('span.pe-odds', null, ` ${Math.round(ck.p * 100)}%${ck.pAll != null ? ` (${Math.round(ck.pAll * 100)}% with help)` : ''}`) : null,
            ch.need ? h('span.muted', null, ` · ${cls(ch.need).name}${missing ? ' needed' : ''}`) : null, ch.cost ? h('span.muted', null, ` · ${ch.cost} gold`) : null),
          h('div.pe-stakes', null, ch.check ? `${ck.vs ? 'Win' : ck.need + '+'}: ${outcomeSummary(ch.ok)} · Else: ${outcomeSummary(ch.bad)}` : outcomeSummary(ch.ok)),
          fans.length ? h('div.pe-fans', null, icon('chat'), `${fans.join(' and ')} suggest${fans.length === 1 ? 's' : ''} this`) : null,
          myHero != null && !d.huddle && !missing ? h('button.btn.sm' + (mySugg === n ? '.primary' : '.ghost'), {
            onclick: () => send({ t: 'suggest', h: myHero, to: x, n: mySugg === n ? null : n }),
          }, mySugg === n ? 'Suggested' : 'Suggest') : null);
      })),
    ];
    cards.push(h('div.pe-card' + (open ? '.open' : '') + (d.asked ? '.asked' : ''), { style: { '--seat': seat(x) } }, head, ...(body || [])));
  });
  el.replaceChildren(...cards);
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
    h('div.field', null, h('span', { tip: 'Ready up automatically\nIn a fight, once a hero has spent every die, they ready up by themselves (unready to take it back).' }, 'Ready when my dice are spent'),
      h('div.seg', null, ...[[false, 'Off'], [true, 'On']].map(([v, l]) => h('button', {
        'aria-pressed': String(!!S.settings.autoReady === v), onclick: () => { S.settings.autoReady = v; saved.settings = S.settings; persist(); renderMenu(); },
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
  if (d.kind === 'merchant') {
    const mer = merchantHere(h0);
    if (!mer) { UI.drawer = null; el.replaceChildren(); return; }
    el.replaceChildren(merchantDrawer(h0, mer, d));
    return;
  }
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
const SLOTS = ['weapon', 'armor', 'trinket'];
// The equipment slots an item of this kind can go in (one each), and the first empty one.
const slotsFor = slot => [slot];
const freeSlot = (hero, slot) => slotsFor(slot).find(s => !hero.equip[s]);
// The slot a new item would replace when its slot is full.
function swapSlot(hero, slot) { return slotsFor(slot)[0]; }
// The "Put it on" button.
function wearButtons(hero, key, send1, primary = true) {
  return [h('button.btn.sm' + (primary ? '.primary' : ''), { onclick: () => send1(undefined) }, 'Put it on')];
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
  else if (it.enchant) sub.push(h('span.mat-kind', { tip: KIND_TEXT[it.enchant] }, `Enchant material · ${cap(it.enchant)}`));
  else if (it.forge) sub.push(h('span.mat-kind', { tip: it.text }, `Forge material · ${it.forge === 'hone' ? 'Hone' : 'Mark'}`));
  if (it.die && it.slot !== 'use') sub.push(workPips(it));
  // an armor's own action, which takes Block's place
  if (it.guard) { const ad = S.static.actions[it.guard]; sub.push(h('span.guard-act', { tip: `${ad.name}, in place of Block\n${ad.text}` }, ad.name)); }
  // a long die (8+ faces) gets its own line rather than wrapping after a dangling separator
  const long = it.die && it.die.length > 6;
  if (it.die && !long) sub.push(faceRow(it));
  sub.push(sellChip(key));
  return h('div.item.r-' + it.rarity, { tip: itemTip(key) },
    h('div.ico', null, h('img.pix', { src: itemURL(key, it.slot), alt: '' })),
    h('div', null, h('div.name.rar-' + it.rarity, null, it.name), h('div.sub', null, ...interleave(sub, ' · ')),
      long ? h('div.sub', null, faceRow(it)) : null,
      it.text && it.slot !== 'use' ? h('div.passive', null, it.text) : null, extra || null),
    h('div.acts', null, right));
}
// What a guard die gives on Block, on average: a shield face is 3 Armor there, not the 0 it is on an
// attack, so an armor's plain average would undersell its shields (and oversell them against numbers).
const SHIELD_ARMOR = 3;
const blockAvg = faces => faces.reduce((a, f) => a + (f === 'S' ? SHIELD_ARMOR : f === 'X' ? 0 : f === 'W' ? topFace(faces) : face(f)[0]), 0) / faces.length;
const isGuard = it => (it.dk || []).includes('guard');
// A die's faces as little tiles, with its kinds (Seer, Fate...) in front, and a guard die's Block average.
function faceRow(it) {
  const kinds = (it.dk || []).filter(k => !k.startsWith('link:') && k !== 'top');
  return h('span.faces', { tip: dieTip({ faces: it.die, dk: it.dk || [] }) },
    ...kinds.map(k => h('span.chip.brass', { style: { height: '20px' }, tip: `${k[0].toUpperCase() + k.slice(1)} die\n${KIND_TEXT[k] || ''}` }, k[0].toUpperCase() + k.slice(1))),
    ...(it.die.every((f, i) => f === i + 1) ? [h('span.face', null, 'd' + it.die.length)]
      : it.die.map(f => h('span.face' + (f === 'S' ? '.s' : ''), typeof f === 'string' ? { tip: faceTip(f) } : null, faceText(f)))),
    isGuard(it) ? h('span.block-avg', { tip: `Block ${blockAvg(it.die).toFixed(1)} on average\nArmor dice go on Block, healing and other defensive actions. A shield face gives ${SHIELD_ARMOR} Armor there.` }, `Block ${blockAvg(it.die).toFixed(1)}`) : null);
}
// What a hero has in an item's slot now, to compare against: its die (with the change in average),
// its actions and its passive. Null for consumables.
function compareWith(h0, key, compact) {
  const it = item(key);
  if (it.slot === 'use') return null;
  const hero = S.game.heroes[h0];
  if (freeSlot(hero, it.slot)) return h('div.compare.empty', null, h('span.cmp-lbl', null, 'Now'), `No ${it.slot}: this fills an empty slot.`);
  const curKey = hero.equip[swapSlot(hero, it.slot)];
  if (curKey === key) return h('div.compare.same', null, h('span.cmp-lbl', null, 'Now'), 'You already wear one of these.');
  const cur = item(curKey);
  // armor compares what it gives on Block; other gear the die's average roll
  const guard = isGuard(it) && isGuard(cur);
  const avg = x => (!x.die ? 0 : guard ? blockAvg(x.die) : expected({ faces: x.die, dk: x.dk || [] }));
  const diff = avg(it) - avg(cur);
  const acts = (cur.acts || []).map(a => S.static.actions[a].name);
  const lost = (cur.acts || []).filter(a => !(it.acts || []).includes(a)).map(a => S.static.actions[a].name);
  return h('div.compare', null,
    h('span.cmp-lbl', null, 'Now'),
    h('b.rar-' + cur.rarity, null, cur.name), cur.die ? faceRow(cur) : null,
    it.die && cur.die ? h('span.cmp-diff' + (diff > 0.05 ? '.up' : diff < -0.05 ? '.down' : ''), { tip: guard ? 'Change in the die’s average on Block' : 'Change in the die’s average roll' },
      diff > 0.05 ? `▲ +${diff.toFixed(1)} ${guard ? 'Block' : 'avg'}` : diff < -0.05 ? `▼ ${diff.toFixed(1)} ${guard ? 'Block' : 'avg'}` : `= same ${guard ? 'Block' : 'avg'}`) : null,
    !compact && acts.length ? h('span.cmp-acts', null, `Actions: ${acts.join(', ')}${lost.length ? ` (you'd lose ${lost.join(', ')})` : ''}`) : null,
    compact && lost.length ? h('span.cmp-acts', null, `You'd lose ${lost.join(', ')}`) : null,
    !compact && cur.text ? h('span.cmp-pass', null, cur.text) : null);
}
// How much work (tempering, enchanting) a piece of gear has taken, out of the most it can: a pip each.
function workPips(it) {
  const most = S.static.work.cap, all = it.work || [], n = all.filter(w => !w.startsWith('star:')).length, star = all.length - n;
  const names = { hone: 'Honed', mark: 'Marked', exploding: 'Enchanted: Exploding', steady: 'Enchanted: Steady', seer: 'Enchanted: Seer', fate: 'Enchanted: Fate',
    'star:hone': 'Starmetal: honed (free of the limit)', 'star:mark': 'Wyrm’s Ember: marked (free of the limit)' };
  return h('span.pips.work', { tip: `Work ${n} of ${most}${all.length ? `\n${all.map(w => names[w] || w).join('\n')}` : '\nA smithy can temper it, and enchant materials can go into it.'}` },
    ...Array.from({ length: most }, (_, i) => h('i' + (i < n ? '.on' : ''))), ...Array.from({ length: star }, () => h('i.on.star')));
}
function interleave(arr, sep) { return arr.flatMap((x, i) => (i ? [sep, x] : [x])); }
function itemTip(key) {
  const it = item(key);
  const lines = [it.name, `${it.rarity[0].toUpperCase() + it.rarity.slice(1)} ${it.enchant || it.forge ? 'material' : it.slot === 'use' ? 'consumable' : it.slot}`];
  if (it.die) lines.push(...dieTip({ faces: it.die, dk: it.dk || [] }).split('\n'));
  for (const a of it.acts || []) { const ad = S.static.actions[a]; lines.push(`${ad.name} (${reqText(ad.req)}): ${ad.text}`); }
  if (it.guard) { const ad = S.static.actions[it.guard]; lines.push(`In place of Block, ${ad.name}: ${ad.text}`); }
  if (it.mods) lines.push(modsText(it.mods));
  if (it.text) lines.push(it.text);
  if (it.work?.length) lines.push(`Work: ${it.work.join(', ')} (${it.work.length} of ${S.static.work.cap})`);
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

// The smith's tempering for one piece of gear: Hone (the lowest number rises) and Mark (it becomes a
// special face), each showing the die it would make, and the item's work so far.
function temperRow(h0, slot, k, disabled) {
  const g = S.game, hero = g.heroes[h0], it = item(k), opts = g.temper?.[k] || {};
  const most = S.static.work.cap, n = (it.work || []).length;
  if (!it.die) return null;
  if (n >= most) return h('div.temper', null, h('span.muted', null, `Fully worked (${most} of ${most}): it can’t take any more.`));
  const what = { hone: ['Hone', `The lowest number rises by ${S.static.work.hone} (no higher than the top face)`], mark: ['Mark', 'The lowest number becomes a special face in the die’s own style'] };
  return h('div.temper', null,
    h('span.temper-lbl', null, `Temper · work ${n + 1} of ${most}`),
    ...Object.entries(what).map(([w, [name, text]]) => {
      const o = opts[w];
      if (!o) return null;
      const [die, cost] = o;
      return h('div.temper-opt', null,
        h('button.btn.sm' + (hero.gold >= cost ? '.primary' : ''), { disabled: disabled || hero.gold < cost, tip: text, onclick: () => send({ t: 'temper', h: h0, slot, what: w }) }, `${name} · ${cost}`),
        h('span.temper-arrow', null, '→'), faceRow({ ...it, die }));
    }));
}

function townDrawer(h0, town, d) {
  const g = S.game, hero = g.heroes[h0], st = S.static;
  const disabled = !canPlan(h0);
  const buyRow = k => {
    const price = Math.floor(st.prices[k] * (g.herald ? 0.8 : 1));
    return itemRow(k, h('button.btn.sm' + (hero.gold >= price ? '.primary' : ''), { disabled: disabled || hero.gold < price, onclick: () => send({ t: 'buy', h: h0, item: k }) }, icon('coin'), price), compareWith(h0, k, true));
  };
  const spec = town.spec && town.spec !== 'fence' ? st.town_specs[town.spec] : null;
  let body;
  if (d.tab === 'trade' && spec) {
    body = [h('div.section-title', null, h('h3', null, spec.name), h('span.chip.brass', null, icon('coin'), hero.gold)), h('p.muted', null, spec.text),
      town.voucher ? h('p.chip.brass', null, icon('check'), `A finished job earned ${town.voucher > 1 ? `${town.voucher} free goes` : 'a free go'} here`) : null];
    if (town.spec === 'smith') {
      for (const slot of ['weapon', 'armor', 'trinket']) {
        const k = hero.equip[slot];
        if (!k) continue;
        const cost = g.reforge?.[k] && town.voucher ? 0 : g.reforge?.[k];
        const nxt = g.reforge?.[k] ? ['common', 'uncommon', 'rare', 'legendary'][['common', 'uncommon', 'rare', 'legendary'].indexOf(st.items[k].rarity) + 1] : null;
        const worked = (st.items[k].work || []).length;
        // the reforge and temper options go under the item, so its die and theirs get the card's full width
        const reforge = cost != null ? h('div.temper-opt', null, h('button.btn.sm' + (hero.gold >= cost ? '.primary' : ''), { disabled: disabled || hero.gold < cost, tip: `Becomes a random ${nxt} ${st.items[k].slot}${worked ? '\nIts tempering and enchantments are lost with it.' : ''}`, onclick: () => send({ t: 'reforge', h: h0, slot }) }, cost ? `Reforge · ${cost}` : 'Reforge · free'),
          h('span.muted', null, `→ a random ${nxt} ${st.items[k].slot}${worked ? ' (the work is lost)' : ''}`))
          : h('span.muted', null, 'Can’t be reforged: it’s as rare as gear gets');
        body.push(itemRow(k, null, h('div', null, temperRow(h0, slot, k, disabled), h('div.temper', null, h('span.temper-lbl', null, 'Reforge'), reforge))));
      }
    } else if (town.spec === 'temple') {
      const curses = Object.keys(hero.buffs).filter(b => st.buffs[b]?.curse);
      body.push(h('div', { style: { display: 'grid', gap: '10px', justifyItems: 'start' } },
        h('button.btn', { disabled: disabled || !curses.length, onclick: () => send({ t: 'temple', h: h0, what: 'cleanse' }) }, curses.length ? `Lift ${curses.map(b => st.buffs[b].name).join(', ')} · free` : 'You aren’t cursed'),
        town.revive_sold ? h('span.muted', null, 'The temple’s revive has been given.')
          : h('button.btn.primary', { disabled: disabled || (!town.voucher && hero.gold < st.temple_revive), onclick: () => send({ t: 'temple', h: h0, what: 'revive' }) }, `+1 revive for the party · ${town.voucher ? 'free' : st.temple_revive}`),
        h('span.muted', null, `The party has ${g.revives} revive${g.revives === 1 ? '' : 's'}.`)));
    } else if (town.spec === 'cartographer') {
      for (const reg of [...worldRegions(), 'peak']) {
        body.push(h('div.item', null, h('div.ico', null, icon('eye')), h('div', null, h('div.name', null, st.regions[reg]), h('div.sub', null, reg === 'peak' ? 'The central island' : `Home of ${st.dungeons[reg]}`)),
          h('button.btn.sm', { disabled: disabled || (!town.voucher && hero.gold < st.chart_cost), onclick: () => send({ t: 'chart', h: h0, region: reg }) }, `Chart · ${town.voucher ? 'free' : st.chart_cost}`)));
      }
    }
  } else if (d.tab === 'market' || d.tab === 'trade') {
    body = [
      h('div.section-title', null, h('h3', null, 'For sale'), h('span.chip.brass', null, icon('coin'), hero.gold)),
      ...(town.shop || []).map(k => buyRow(k)),
      town.ship?.length ? h('div.section-title', null, h('h3', null, 'The merchant ship'), h('span.chip.brass', null, `sails in ${(g.opps.find(o => o.tile === hero.tile) || {}).left} turns`)) : null,
      ...(town.ship || []).map(k => buyRow(k)),
      g.herald ? h('p.muted', null, 'The Herald’s silver tongue knocks 20% off.') : null,
      hero.bag.length ? h('h3', null, 'Sell' + (town.spec === 'fence' ? ' (the fence pays half again as much)' : '')) : null,
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
    const jobs = town.jobs || [];
    const mineJobs = g.quests.filter(q2 => !q2.done && !q2.failed);
    body = [h('h3', null, 'Notice board'),
      jobs.length ? h('p.muted', null, 'Take one of these. The other comes down when you do.') : h('p.muted', null, town.quest_taken ? 'You’ve taken this town’s job.' : 'Nothing pinned up today.'),
      ...jobs.map((j, n) => h('div.card.job', null,
        h('div.job-head', null, h('span.kind', null, st.job_kinds[j.kind].name), h('span.chip', { tip: 'Turns to finish it, counting this one' }, icon('clock'), `${j.turns} turns`)),
        h('b', null, cap(jobText(j))), h('p.muted', null, st.job_kinds[j.kind].text),
        h('div.gains', null, h('span.chip.brass', null, cap(rewardText(j.reward)))),
        h('div', { style: { display: 'flex', gap: '8px' } },
          h('button.btn.primary', { disabled, onclick: () => send({ t: 'quest', h: h0, n }) }, 'Take this job'),
          h('button.btn.ghost', { onclick: () => map?.centerOn(j.tile) }, icon('target'), 'Show on map')))),
      g.quests.length ? h('h3', null, 'Your jobs') : null,
      ...g.quests.slice().reverse().map(q2 => q2.kind === 'trail' ? h('div.item', { tip: q2.done ? null : `${questTip(q2)}\nClick to find it on the map`, onclick: () => !q2.done && q2.goal != null && map?.centerOn(q2.goal) },
        h('div.ico', null, icon(q2.done ? 'check' : 'star')),
        h('div', null, h('div.name', null, questLine(q2)), h('div.sub', null, q2.done ? 'Quest complete' : `Quest · next: ${jobText(q2)}`)), h('span'))
        : h('div.item', { tip: q2.done || q2.failed ? null : 'Click to find it on the map', onclick: () => q2.goal != null && map?.centerOn(q2.goal) },
        h('div.ico', null, icon(q2.done ? 'check' : q2.failed ? 'x' : 'scroll')),
        h('div', null, h('div.name', null, cap(jobText(q2))),
          h('div.sub', null, `For ${q2.src} · ${q2.done ? 'done' : q2.failed ? 'failed' : `${q2.left} turn${q2.left === 1 ? '' : 's'} left · ${rewardText(q2.reward)}`}`)), h('span')))];
  }
  return drawerShell(town.name, town.spec ? `Town · ${st.town_specs[town.spec].name}` : 'Town',
    [['market', 'Market'], ...(spec ? [['trade', spec.name]] : []), ['inn', 'Inn'], ['docks', 'Docks'], ['board', 'Notice board']], d, body);
}

// A travelling merchant's wares: rare and legendary gear, marked up (Game.merchant_price).
function merchantDrawer(h0, m, d) {
  const g = S.game, hero = g.heroes[h0], disabled = g.fight?.heroes.includes(h0) && g.phase === 'fight';
  const body = [h('div.section-title', null, h('h3', null, 'For sale'), h('span.chip.brass', null, icon('coin'), hero.gold)),
    h('p.muted', null, `Rare and legendary gear from all over the islands, at ${S.static.travel.markup}× the usual price. The stock changes in every town it reaches.`),
    m.stock.length ? null : h('p.muted', null, 'Sold out until the next town.'),
    ...m.stock.map(k => {
      const price = Math.floor(m.prices[k] * (g.herald ? 0.8 : 1));
      return itemRow(k, h('button.btn.sm' + (hero.gold >= price ? '.primary' : ''), { disabled: disabled || hero.gold < price, onclick: () => send({ t: 'mbuy', h: h0, item: k }) }, icon('coin'), price), compareWith(h0, k, true));
    }),
    g.herald ? h('p.muted', null, 'The Herald’s silver tongue knocks 20% off.') : null];
  return drawerShell(cap(m.name), `Travelling merchant · ${merchantWhere(m)}`, null, d, body);
}

// Where a lit beacon can take a hero: every other lit one, with where it is and how far.
function beaconPicker(h0) {
  const g = S.game, hero = g.heroes[h0], p = g.plans[h0];
  const close = () => box.remove();
  const go = to => { send({ t: 'beacon', h: h0, to }); close(); };
  const opts = litBeacons().filter(t => t !== hero.tile).sort((a, b) => hexDist(hero.tile, a) - hexDist(hero.tile, b));
  const box = modal([
    h('h2', null, 'Travel by beacon'),
    h('p.lead', null, 'The lit beacons answer each other across the islands. Pick one to travel to: it takes your whole move, and you arrive before anyone else walks.'),
    h('div.choices', null, ...opts.map(t => {
      const near = g.heroes.filter((x, i) => i !== h0 && x.alive && hexDist(x.tile, t) <= 3).map(x => x.name);
      return h('button.choice' + (p?.warp === t ? '.on' : ''), { onclick: () => go(t), onmouseenter: () => map?.centerOn(t) },
        h('img.pix', { src: placeURL('beacon_lit'), alt: '', style: { width: '28px' } }),
        h('span.grow', null, h('b', null, beaconName(t).title),
          h('small', null, [beaconName(t).region && cap(beaconName(t).region), `${hexDist(hero.tile, t)} hexes away`, near.length && `${near.join(' and ')} nearby`].filter(Boolean).join(' · '))));
    })),
    h('div', { style: { display: 'flex', gap: '8px', justifyContent: 'flex-end' } },
      p?.warp != null ? h('button.btn', { onclick: () => go(null) }, 'Stay here instead') : null,
      h('button.btn.ghost', { onclick: close }, 'Cancel')),
  ], { onClose: close });
  document.body.append(box);
}

// What a material would do to a worn piece of gear: its die after, or why it can't (mirrors Game.enchant).
function materialResult(h0, mat, slot) {
  const hero = S.game.heroes[h0], key = hero.equip[slot], it = item(key), most = S.static.work.cap;
  const done = (it.work || []).filter(w => !w.startsWith('star:')).length, die = it.die || [];
  const nums = die.map((f, i) => [f, i]).filter(([f]) => typeof f === 'number');
  if (mat.forge) {
    if (!nums.length) return { why: 'Its die has no numbers to work' };
    const top = Math.max(...nums.map(([f]) => f)), low = nums.reduce((a, b) => (b[0] < a[0] ? b : a));
    const after = die.slice();
    if (mat.forge === 'hone') {
      if (low[0] >= top) return { why: 'Its die is already as high as it goes' };
      after[low[1]] = Math.min(top, low[0] + S.static.work.hone);
      const sorted = nums.map(([, i]) => after[i]).sort((a, b) => a - b);
      nums.forEach(([, i], j) => { after[i] = sorted[j]; });
    } else {
      if (nums.length < 2) return { why: 'Its die has no number to spare' };
      const tagged = die.filter(f => typeof f === 'string' && 'FIP'.includes(f[0]) && /^\d+$/.test(f.slice(1)));
      after[low[1]] = it.slot === 'armor' ? 'S' : tagged.length ? tagged.reduce((a, b) => (+b.slice(1) > +a.slice(1) ? b : a)) : 'W';
    }
    return { die: after, dk: it.dk || [], note: 'Free of the work limit' };
  }
  if ((it.dk || []).includes(mat.enchant)) return { why: `Its die is already ${cap(mat.enchant)}` };
  if (done >= most) return { why: `It has had all the work it can take (${most} of ${most})` };
  return { die, dk: [...(it.dk || []), mat.enchant], note: `Work ${done + 1} of ${most}` };
}

// A material's one button: a popup of every worn piece, what the material would make of it, and why not.
function materialPicker(h0, i, mat) {
  const hero = S.game.heroes[h0];
  const close = () => box.remove();
  const rows = SLOTS.filter(slot => hero.equip[slot]).map(slot => {
    const k = hero.equip[slot], it = item(k), r = materialResult(h0, mat, slot);
    const before = { faces: it.die || [], dk: it.dk || [] };
    return h('button.choice.mat-opt' + (r.why ? '.off' : ''), { disabled: !!r.why, onclick: () => { send({ t: 'use', h: h0, bag: i, slot }); close(); } },
      h('img.pix', { src: itemURL(k, it.slot), alt: '', style: { width: '32px' } }),
      h('span.grow', null,
        h('span', null, h('b', null, it.name), h('small', null, ` · ${cap(slot)}`)),
        h('div.mat-dice', null, dieLabel(before), r.why ? null : [h('span.arrow', null, ' → '), h('b', null, dieLabel({ faces: r.die, dk: r.dk }))]),
        h('div.mat-faces', null, faceRowOf(before.faces), r.why ? null : [h('span.arrow', null, '→'), faceRowOf(r.die, before.faces)]),
        h('small.muted', null, r.why || r.note)));
  });
  const box = modal([
    h('h2', null, `Use the ${mat.name}`),
    h('p.lead', null, mat.text),
    rows.length ? h('div.choices', null, ...rows) : h('p.muted', null, 'Wear some gear first.'),
    h('div', { style: { display: 'flex', justifyContent: 'flex-end' } }, h('button.btn.ghost', { onclick: close }, 'Cancel')),
  ], { onClose: close });
  document.body.append(box);
}
// A die's faces as small chips, the ones that changed (against `was`) picked out.
// (A face is new if the old die didn't have it, counting repeats: honing re-sorts the numbers.)
function faceRowOf(faces, was) {
  const left = {};
  for (const f of was || []) left[f] = (left[f] || 0) + 1;
  return h('span.faces', null, ...faces.map(f => {
    const fresh = was && !(left[f] > 0);
    if (was && !fresh) left[f]--;
    return h('span.face' + (fresh ? '.changed' : ''), { tip: faceTip(f) || null }, faceText(f));
  }));
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
        : h('div.item.empty', null, h('div.ico', null, icon(SLOT_ICON[slot])), h('div', null, `No ${slot}`))),
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
        : h('div.item.empty', null, h('div.ico', null, icon(SLOT_ICON[slot])), h('div', null, `No ${slot}`))),
      h('div.section-title', null, h('h3', null, `Bag · ${hero.bag.length} item${hero.bag.length === 1 ? '' : 's'}`), h('span.chip.brass', null, icon('coin'), hero.gold)),
      ...hero.bag.map((k, i) => {
        const it = item(k);
        // the bag's buttons go in one row under the item, not squeezed into the right-hand column
        return itemRow(k, null, h('div.bag-acts', null,
          it.slot !== 'use' ? h('button.btn.sm', { disabled: !free, onclick: () => send({ t: 'equip', h: h0, bag: i }) }, 'Equip') : null,
          it.slot === 'use' && !it.fight && !it.enchant && !it.forge ? h('button.btn.sm', { onclick: () => send({ t: 'use', h: h0, bag: i }) }, 'Use') : null,
          it.enchant || it.forge ? h('button.btn.sm.primary', { disabled: !free, tip: free ? 'See what it would do to each piece you wear' : 'Not in the middle of a fight', onclick: () => materialPicker(h0, i, it) }, icon('spark'), 'Use on gear…') : null,
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
      ...acts.map(k => skillCard(k, (weapon?.acts || []).includes(k.replace(/\+$/, '')) ? weapon.name
        : hero.equip.armor && item(hero.equip.armor).guard === k ? `${item(hero.equip.armor).name}, in place of Block` : null)),
      h('h3', null, 'Passives'),
      passives.length ? passives.map(k => skillCard(k)) : h('p.muted', null, 'None yet: pick them as you level up.'),
      h('h3', null, 'Always available'),
      ...(hero.actions.includes('block') ? [skillCard('block')] : []), skillCard('flee'),
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
      ...Object.entries(hero.buffs).map(([b, n]) => h('div.card.skill', null, h('div.row', null, h('b', null, S.static.buffs[b].name), h('span.chip' + (S.static.buffs[b].perm ? '.brass' : ''), null, S.static.buffs[b].perm ? 'Boon, for good' : `${n} turns`)), h('p', null, S.static.buffs[b].text))),
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
    h('div.ab', null, h('div.eff', null, icon(ico), h('span', null, eff + (k.endsWith('+') ? ' (+2)' : ''))), miss ? h('div.miss', null, `miss: ${miss}`) : null,
      a.crit_short ? h('div.crit', { tip: CRIT_TIP }, `crit: ${a.crit_short}`) : null));
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
    h('p', null, sk.text + upText(k, sk)),
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
  const party = spec.die === 'party', which = party ? 'best' : spec.die || 'best';
  // the chance one hero's die makes it
  const pOf = y => {
    const d = eventDie(y, which), bonus = g.heroes[y].skills.includes('silver_voice') ? 1 : 0;
    const vals = d.faces.map(f => faceVal(f, d.faces) + bonus);
    return spec.vs ? vals.reduce((a, v) => a + Math.max(0, Math.min(v - 1, spec.vs)) / spec.vs, 0) / vals.length
      : vals.filter(v => v >= (spec.n ?? 4)).length / vals.length;
  };
  const d = eventDie(x, which);
  // a party check: allies on the hex can chip in their best die too; the best roll counts
  const mates = party ? g.heroes.map((y, i) => i).filter(i => i !== x && g.heroes[i].alive && g.heroes[i].tile === g.heroes[x].tile) : [];
  const p = pOf(x), pAll = 1 - mates.reduce((a, y) => a * (1 - pOf(y)), 1 - p);
  const label = d.bare ? `a bare d4 (no ${which})` : `your ${SLOT_NAME[which] || 'best'} die (${dieLabel(d)})`;
  const text = spec.vs ? ` Roll ${label}, beat a d${spec.vs}:` : ` Roll ${label}, ${spec.n ?? 4}+:`;
  return { p, pAll: mates.length ? pAll : null, mates, party, pOf, text, need: spec.n ?? 4, vs: spec.vs, greatAt: spec.great };
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
  for (const b of [].concat(o.buff || [])) parts.push(`${st.buffs[b].name}${st.buffs[b].curse ? ' (a curse)' : st.buffs[b].perm ? ' (a boon, for good)' : ''}`);
  if (o.give) parts.push(`${st.items[o.give].name} (${st.items[o.give].rarity} ${st.items[o.give].slot === 'use' ? 'material' : st.items[o.give].slot})`);
  if (o.mat) parts.push(o.mat === 'random' ? 'an enchant material' : st.items[o.mat].name);
  if (o.quest === 'start') parts.push('a quest');
  else if (o.quest === 'next' && !o.win) parts.push('the quest moves on');
  if (o.win) parts.push('if you win: ' + outcomeSummary({ ...o.win, all: false }));
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
    h('div.ev-need', null, r.vs ? `Beat a d${r.vs}` : `Needed ${r.need}+`,
      r.rolls ? h('small', null, r.rolls.map(x => `${S.game.heroes[x.by].name} ${x.v}`).join(' · ') + ` (best counts)`)
        : r.by != null ? h('small', null, `${S.game.heroes[r.by].name} rolled ${dieLabel({ faces: r.faces, dk: [] })}`) : null),
    h('div.rt-verdict.' + (r.ok ? 'hit' : 'miss'), null, verdict));
}

// ------------------------------------------------------------------ dialogs
// ------------------------------------------------------------------ the results screen
// One screen per hero per turn: what happened to them (event outcomes, gold, blessings, jobs) and
// every choice it left them (an event's options, spoils, level-ups), all together, with one Continue.
// What happened stays on it (through any fight an event starts) until Continue clears it.
function resOf(x) { return (UI.res[x] ||= { outcomes: [], notes: [] }); }
function hasResults(x) {
  const r = UI.res[x];
  return !!(S.game.pending[x]?.length || (r && (r.outcomes.length || r.notes.length)));
}
// a line for the hero's results screen if one is (or is about to be) up, else a toast
function resultNote(x, text, fallback) {
  if (S.game.pending[x]?.length || UI.res[x]?.outcomes.length) { resOf(x).notes.push(text); renderDialogs(); }
  else fallback();
}

function renderDialogs() {
  const el = $('modal');
  const g = S.game;
  if (combatOpen()) { el.replaceChildren(); UI.lastDialog = null; return; }
  const h0 = mine().find(x => g.pending[x]?.length || UI.res[x]?.outcomes.length) ?? mine().find(hasResults);
  if (h0 === undefined && g.phase === 'fork' && g.fork) {
    const fk = forkView(g.fork);
    if (fk) {
      const enter = UI.lastDialog !== 'fork' + g.fork.step; UI.lastDialog = 'fork' + g.fork.step;
      el.replaceChildren(modal(fk, { wide: true, enter, backdrop: 'dungeon' }));
      return;
    }
  }
  if (h0 === undefined) { el.replaceChildren(); UI.lastDialog = null; return; }
  const hero = g.heroes[h0], r = resOf(h0), q = g.pending[h0] || [];
  r.turn ??= g.turn; // the last pick can end the turn; the screen keeps the turn it's about
  // allies who could take loot from this hero: anyone alive within a hex (who'd have joined the fight)
  const mates = g.heroes.map((x, i) => i).filter(i => i !== h0 && g.heroes[i].alive && hexDist(g.heroes[i].tile, hero.tile) <= 1);
  // each pick also goes on the screen's list of what happened, so it reads as a record of the turn
  const choose = (i, n, extra, note) => { send({ t: 'choose', h: h0, i, n, ...extra }); if (note) r.notes.push(note); };
  const took = (k, extra) => (extra?.to != null && extra.to !== h0 ? `${item(k).name} for ${g.heroes[extra.to].name}` : `Took ${item(k).name}`);
  const sections = [];

  for (const o of r.outcomes) {
    sections.push(h('section.res-sec', null,
      h('h3', null, o.title),
      o.roll ? eventRollView(o.roll) : null,
      h('div.outcome', null, o.text),
      o.bits.length ? h('div.gains', null, ...o.bits.map(b => h('span.chip.brass', null, b))) : null));
  }
  if (r.notes.length) sections.push(h('div.gains.res-notes', null, ...r.notes.map(t => h('span.chip.brass', null, t))));

  // the choices, in order; an event's choice comes first (what it leads to can change the rest)
  const blocked = q[0]?.type === 'event';
  const seenPools = new Set();
  let first = true, wide = false, lootKey = null;
  // a level-up's one pick comes before the spoils (the new skill can change what gear you want)
  const RANK = { event: 0, help: 0, level: 1, loot: 2, pool: 2 };
  const order = q.map((d, i) => i).sort((a, b) => RANK[q[a].type] - RANK[q[b].type] || a - b);
  order.forEach(i => {
    const d = q[i];
    if (blocked && i > 0) return;
    let sec = null;
    if (d.type === 'event' && d.huddle) {
      // a party check waiting on allies: who's chipped in so far, roll now, or take it back
      const ev = S.static.events[d.key], ch = ev.choices[d.huddle.n];
      const ck = eventOdds(h0, ch.check);
      const inNow = d.huddle.helpers.filter(y => d.huddle.offers[y]);
      const pNow = 1 - inNow.reduce((a, y) => a * (1 - ck.pOf(y)), 1 - ck.p);
      sec = [
        h('h3', null, ev.title),
        h('p.lead', null, `${ch.label}: a party check. Everyone on your hex who chips in rolls their best die too, and the best roll counts. If it fails, they share the bad outcome.`),
        h('div.huddle', null, ...d.huddle.helpers.map(y => {
          const st = d.huddle.offers[y];
          return h('div.hud-row' + (st === true ? '.in' : st === false ? '.out' : '.wait'), { style: { '--seat': seat(y) } },
            h('i.dot'), h('b', null, g.heroes[y].name),
            h('span', null, st === true ? ` chips in (${dieLabel(eventDie(y, 'best'))})` : st === false ? ' stays out' : ' deciding…'));
        })),
        h('p.muted', null, `Chance now: ${Math.round(pNow * 100)}%${ck.pAll != null ? ` (${Math.round(ck.pAll * 100)}% if everyone chips in)` : ''}.`),
        h('div.huddle-btns', null,
          h('button.btn.primary', { onclick: () => choose(i) }, icon('dice'), inNow.length ? `Roll now with ${inNow.map(y => g.heroes[y].name).join(' and ')}` : 'Roll now, alone'),
          h('button.btn.ghost', { onclick: () => choose(i, null, { cancel: true }) }, 'Choose something else')),
      ];
    } else if (d.type === 'help') {
      // an ally's party check: chip in or not
      const ev = S.static.events[d.key], ch = ev.choices[d.n], who = g.heroes[d.h];
      const ck = eventOdds(d.h, ch.check);
      const mine1 = eventDie(h0, 'best');
      const pWith = 1 - (1 - ck.p) * (1 - ck.pOf(h0));
      sec = [
        h('h3', null, `${who.name} asks you to chip in`),
        h('p.lead', null, `${ev.title}: ${ch.label}. They need ${ck.vs ? `to beat a d${ck.vs}` : `${ck.need}+`}. Chip in and you roll your best die (${dieLabel(mine1)}) too: the best roll counts.`),
        h('div.stakes-box', null,
          h('div', null, h('b', null, 'If it works: '), outcomeSummary(ch.ok)),
          h('div', null, h('b', null, 'If it fails: '), outcomeSummary(ch.bad), ' — and you share it if you chipped in.')),
        h('p.muted', null, `Their chance alone: ${Math.round(ck.p * 100)}%. With you: ${Math.round(pWith * 100)}%.`),
        h('div.huddle-btns', null,
          h('button.btn.primary', { onclick: () => choose(i, 1) }, icon('dice'), 'Chip in'),
          h('button.btn.ghost', { onclick: () => choose(i, 0) }, 'Not this time')),
      ];
    } else if (d.type === 'event') {
      const ev = S.static.events[d.key];
      const others = g.heroes.map((y, j) => j).filter(j => j !== h0 && g.heroes[j].alive && !mine().includes(j));
      const sugg = d.sugg || {};
      sec = [
        h('h3', null, ev.title),
        h('p.lead', null, ev.text),
        others.length ? h('div.ask-row', null,
          h('button.btn.sm' + (d.asked ? '.ghost' : ''), { onclick: () => send({ t: 'ask', h: h0 }), tip: 'Show this event on everyone’s screen and ask what they’d do. Their suggestions appear on the choices.' },
            icon('chat'), d.asked ? 'Asked the party' : 'Ask the party'),
          Object.keys(sugg).length ? h('span.muted', null, `${Object.keys(sugg).length} suggestion${Object.keys(sugg).length === 1 ? '' : 's'}`) : null) : null,
        h('div.choices', null, ...ev.choices.map((ch, n) => {
          const missing = ch.need && !g.heroes.some(x => x.alive && x.cls === ch.need);
          const broke = (ch.cost || 0) > hero.gold;
          const tags = [];
          if (ch.need) tags.push(`${cls(ch.need).name}${missing ? ' needed' : ''}`);
          if (ch.cost) tags.push(`${ch.cost} gold${broke ? ' (not enough)' : ''}`);
          const ck = ch.check ? eventOdds(h0, ch.check) : null;
          const stakes = ch.check
            ? [ch.great ? `${ck.greatAt}+: ${outcomeSummary(ch.great)}` : null, `${ck.vs ? 'Win' : ck.need + '+'}: ${outcomeSummary(ch.ok)}`, `${ck.vs ? 'Lose' : 'Else'}: ${outcomeSummary(ch.bad)}`].filter(Boolean).join(' · ')
            : outcomeSummary(ch.ok);
          const fans = Object.entries(sugg).filter(([, v]) => v === n).map(([y]) => g.heroes[y].name);
          return h('button.choice' + (fans.length ? '.suggested' : ''), { disabled: missing || broke, onclick: () => choose(i, n) },
            h('span.n', null, n + 1),
            h('span.grow', null, h('span.label', null, ch.label),
              ck ? h('span.roll', null, icon('dice'), ck.text, h('b.odds' + (ck.p >= 0.6 ? '.good' : ck.p >= 0.35 ? '.mid' : '.bad'), null, ` ${Math.round(ck.p * 100)}%`),
                ck.pAll != null ? h('span.party-odds', null, ` · ${Math.round(ck.pAll * 100)}% if ${ck.mates.map(y => g.heroes[y].name).join(' and ')} chip in`) : null) : null,
              stakes ? h('span.stakes', null, stakes) : null,
              fans.length ? h('span.sugg', null, icon('chat'), `${fans.join(' and ')} suggest${fans.length === 1 ? 's' : ''} this`) : null),
            tags.length ? h('span.tag', null, tags.join(' · ')) : null);
        })),
      ];
    } else if (d.type === 'loot') {
      wide = true; lootKey ??= JSON.stringify(d.opts);
      sec = [
        h('h3', null, 'A find'),
        h('p.lead', null, mates.length ? 'Take one, or hand it to an ally nearby. Put gear on now, or keep it in a bag for later.'
          : 'Take one. Put gear on now, or keep it in your bag for later.'),
        h('div.picks.loot', null, ...d.opts.map((k, n) => lootCard(h0, k, n, mates, extra => choose(i, n, extra, took(k, extra))))),
        h('button.btn.ghost', { style: { justifySelf: 'end' }, onclick: () => choose(i, -1) }, 'Leave it'),
      ];
    } else if (d.type === 'pool') {
      if (seenPools.has(d.id)) return;
      seenPools.add(d.id);
      wide = true;
      const pool = g.pools[d.id];
      lootKey ??= JSON.stringify(pool.items);
      const mine1 = q.filter(x => x.type === 'pool' && x.id === d.id).length;
      const still = pool.heroes.filter(x => x !== h0 && g.pending[x]?.some(p => p.type === 'pool' && p.id === d.id)).map(x => g.heroes[x].name);
      const left = 3 - Object.keys(pool.taken).length;
      sec = [
        h('h3', null, pool.heroes.length > 1 ? 'Shared spoils' : 'Spoils'),
        h('p.lead', null, `Four items, ${left} of three claims left, ${mine1} of them yours. ` +
          (pool.heroes.length > 1 ? 'The claims go round the party; first claim wins an item, and you can hand yours to an ally.' : 'Put gear on now, or keep it in your bag for later.')),
        h('div.picks.loot', null, ...pool.items.map((k, n) => lootCard(h0, k, n, mates, extra => choose(i, n, extra, took(k, extra)), pool.taken[n]))),
        h('div', { style: { display: 'flex', gap: '12px', alignItems: 'center', justifyContent: 'flex-end' } },
          still.length ? h('span.muted', null, `Still choosing: ${still.join(', ')}`) : null,
          h('button.btn.ghost', { onclick: () => choose(i, -1, { all: true }) }, mine1 > 1 ? 'Leave the rest' : 'Pass')),
      ];
    } else if (d.type === 'level') {
      wide = true;
      sec = [
        h('div.lvl-head', null, h('img.pix', { src: spriteURL(hero.cls), alt: '' }),
          h('div', null, h('span.lvl-badge', null, `Level ${d.lvl}`), h('h3', null, `${hero.name} learns something new`))),
        h('p.lead', null, `Choose one. ${d.lvl === 3 || d.lvl === 6 ? 'One of your class dice also grows a size. ' : ''}Max HP went up too.`),
        h('div.picks', null, ...d.opts.map((k, n) => {
          const sk = skillDef(k), up = k.endsWith('+');
          const isAct = !!S.static.actions[k.replace(/\+$/, '')];
          return h('button.pick', { style: { '--i': n }, onclick: e => { flyToHero(e.currentTarget, h0); choose(i, n, null, `Learned ${sk.name}${up ? '+' : ''}`); } }, h('span.kbd.pick-key', null, n + 1),
            h('span.kind', null, up ? 'Upgrade' : sk.cap ? 'Capstone' : isAct ? 'New action' : 'Passive'),
            h('h3', null, sk.name + (up ? '+' : '')),
            isAct ? skillFace(k) : null,
            isAct && sk.cd ? h('span.req', null, icon('clock'), `cooldown ${sk.cd}`) : null,
            h('p', null, sk.text + upText(k, sk)),
            sk.tags?.length ? h('div.tags', null, ...sk.tags.map(t => h('span.chip', null, t[0].toUpperCase() + t.slice(1)))) : null);
        })),
      ];
    }
    if (!sec) return;
    // number keys answer the first open choice
    sections.push(h('section.res-sec.choice-sec' + (first ? '.res-now' : ''), null, ...sec));
    first = false;
  });

  const open = q.length > 0;
  const content = [
    h('div.eyebrow', null, `${hero.name} · ${S.static.regions[S.world.reg[hero.tile]] || ''} · turn ${r.turn}`),
    ...sections,
    h('div.res-foot', null,
      open ? h('span.muted', null, blocked ? 'Choose to carry on.' : 'Choose above, then carry on.')
        : h('button.btn.primary.res-continue', { onclick: () => { delete UI.res[h0]; renderDialogs(); renderHint(); } }, 'Continue', h('span.kbd', null, 'Enter'))),
  ];
  const key = 'res' + h0;
  const enter = key !== UI.lastDialog; UI.lastDialog = key;
  // between a dungeon's fights the party is still underground: no map behind the spoils
  const here = g.places[hero.tile];
  const deep = g.phase === 'reward' && here && ((here.kind === 'dungeon' && !g.cleared.includes(here.region)) || here.kind === 'peak');
  el.replaceChildren(modal(content, { wide, enter, backdrop: deep ? 'dungeon' : null }));
  // good loot gets a fanfare as the cards are dealt
  if (lootKey && lootKey !== UI.lastLoot) {
    UI.lastLoot = lootKey;
    const best = Math.max(...JSON.parse(lootKey).map(k => ['common', 'uncommon', 'rare', 'legendary'].indexOf(item(k).rarity)));
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
    h('span.kind.rar-' + it.rarity, null, `${it.rarity[0].toUpperCase() + it.rarity.slice(1)} ${it.enchant || it.forge ? 'material' : it.slot === 'use' ? 'consumable' : it.slot}`),
    h('div.loot-title', null, h('img.pix', { src: itemURL(k, it.slot), alt: '' }), h('h3.rar-' + it.rarity, null, it.name)),
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
    // what waits down this path, drawn: the enemies facing you, or the shrine where nothing does
    const stage = h('div.fork-stage' + (foes.length ? '' : '.calm'), null, ...(foes.length
      ? foes.slice(0, 6).map(x => h('img.pix.fork-foe' + (st.foes[x.k]?.boss || st.foes[x.k]?.big ? '.big' : x.aff ? '.elite' : ''), { src: spriteURL(x.k), alt: '', tip: foeName(x.k, x.aff) }))
      : [h('img.pix.fork-place', { src: placeURL(o.path === 'shrine' ? 'shrine' : 'camp'), alt: '' })]));
    return h('button.pick.fork' + (mine_ ? '.chosen' : ''), { style: { '--i': i }, onclick: () => vote(i) },
      stage,
      h('span.kbd.pick-key', null, i + 1),
      h('span.kind', null, kind),
      h('h3', null, p.name),
      h('p', null, p.text),
      foes.length ? h('div.fork-foes', null, ...foes.map(x => h('span.chip' + (x.aff || st.foes[x.k]?.big || st.foes[x.k]?.boss ? '.danger' : ''), null, foeName(x.k, x.aff))),
        ...(boss ? fk.garrison?.foes || [] : []).map(k => h('span.chip', { tip: 'From the garrison, which grew while the objective waited' }, `${foeName(k)} (garrison)`))) : null,
      ...affs.map(a => h('p.muted.small', null, `${st.elites[a].name}: ${st.elites[a].text}`)),
      big ? h('p.muted.small', null, `${st.foes[big.k].name}: a big threat. At half health it's bloodied: ${st.foes[big.k].bloodied.text}`) : null,
      h('div.gains', null, h('span.chip.brass', null, p.reward)),
      h('div.fork-votes', null, ...voters.map(x => h('span.vote', { style: { '--c': `var(--hero-${x})` } }, g.heroes[x].name))));
  });
  return [
    h('div.eyebrow', null, `${st.dungeons[fk.region]} · fight ${fk.step + 1} of 3 next`),
    h('h2', null, 'The way forks'),
    h('p.lead', null, fk.heroes.length > 1 ? 'Pick a path together. Most votes wins; a tie is a coin toss.' : 'Pick a path.'),
    fk.garrison?.foes.length ? h('p.muted', null, `The garrison joins either way: ${fk.garrison.foes.map(k => foeName(k)).join(', ')}${fk.garrison.boss ? `, and the boss has ${fk.garrison.boss}% more health` : ''}.`) : null,
    h('div.picks', null, ...lines),
    waiting.length ? h('p.muted', null, `Waiting for ${waiting.join(', ')}.`) : null,
  ];
}

// ------------------------------------------------------------------ first-time hints
const HINTS = {
  plan: ['Planning together', 'Everyone plans at once. Click a lit hex to plot a route, then Ready. When the whole party is ready, everyone moves together. Walking into enemies starts a fight, and anyone within a hex joins in.'],
  fight: ['Fighting with dice', 'Click dice to pick them, then click an action they fit: it happens at once, dice and all. Whoever plays first goes first, so set-ups before attacks. Heroes working together score combos: hover Combos in the fight for the list. When everyone is ready, enemies do what their intents say.'],
  sea: ['Time and tide', 'Every nine turns the Great Tide rises: every enemy grows stronger, and the sea brings things ashore: wreckage and visitors at first, raiders and worse as the run goes on. They show on the map at once and under “This turn”. When the Great Tide rises the garrisons of objectives you haven’t cleared grow too, and an objective cleared before its garrison grows weakens the final boss. Gold-ringed places on the map are chances that won’t wait.'],
};
function renderHint() {
  const el = $('hint');
  const g = S.game;
  let key = null;
  if (!S.seenHints.plan && g.phase === 'plan') key = 'plan';
  else if (!S.seenHints.sea && g.rises > 0) key = 'sea';
  const modalUp = mine().some(hasResults);
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
  // what the map says after a fight (level-ups, gold, the tide...) waits until the fight has played out
  const later = [], coins = {};
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
      case 'fight': if (map && speed) { const at = heroSteps * map.stepTime(speed); setTimeout(() => map?.clash(f.tile), at); } break;
      case 'rise': later.push(() => {
        // the Great Tide: a wave over the whole screen, a banner with what it changed, the arrivals coming
        // in where they land and the garrisons that grew pulsing on their objectives
        const news = f.news || [], grown = f.garrisons || [];
        const what = [f.up ? `Enemies +${f.up}% stronger` : null, grown.length ? `Garrisons grow: ${grown.map(x => x.name).join(', ')}` : null].filter(Boolean);
        bigBanner('The Great Tide', what.join(' · ') || 'The sea rises', 'tide.great', 3600);
        document.body.classList.remove('great-tide'); void document.body.offsetWidth; document.body.classList.add('great-tide');
        setTimeout(() => document.body.classList.remove('great-tide'), 2600);
        for (const n of news) toast(`${n.name}: ${n.text}`);
        if (grown.length) toast(`Garrisons grow at ${grown.map(x => `${x.name} (+${x.n})`).join(', ')}: their bosses are harder to reach`, 'big');
        if (news.length && mine().length) map?.centerOn(news[0].tile);
        const mapEl = $('map');
        if (mapEl && speed) { mapEl.classList.remove('tide-wave'); void mapEl.offsetWidth; mapEl.classList.add('tide-wave'); setTimeout(() => mapEl.classList.remove('tide-wave'), 1700); }
        news.forEach((n, j) => setTimeout(() => map?.arrive(n.tile, n.k), 700 + j * 450));
        grown.forEach((x, j) => x.tile != null && setTimeout(() => map?.arrive(x.tile, 'garrison'), 900 + (news.length + j) * 450));
        sfx.play('rise');
      }); break;
      case 'coins': if (mine().includes(f.h)) coins[f.h] = (coins[f.h] || 0) + f.n; break;
      case 'tide': later.push(() => toast(f.tide === 'low' ? 'Low tide: the sandbars are out' : 'High tide: the shallows close')); break;
      case 'level': later.push(() => { bigBanner(`Level ${f.lvl}`, 'The party grows stronger', 'gold'); sfx.play('level'); }); break;
      case 'cleared': later.push(() => { bigBanner(`${S.static.dungeons[f.region]} cleared`, `${S.game.cleared.length} of 3 objectives`, 'gold', 2600); sfx.play('fanfare'); }); break;
      case 'buff': if (mine().includes(f.h)) later.push(() => resultNote(f.h, S.static.buffs[f.b].name, () => toast(`${S.game.heroes[f.h].name}: ${S.static.buffs[f.b].name}`))); break;
      case 'quest': later.push(() => { const Q = S.static.quests[f.key], t = f.done ? `Quest complete: ${Q.name}!` : `${Q.name}: the next step is marked on your map.`;
        mine().includes(f.h) ? resultNote(f.h, t, () => toast(t, 'big')) : toast(t, f.done ? 'big' : undefined); if (f.done) sfx.play('coin'); }); break;
      case 'job': later.push(() => { const t = `Job done for ${f.src}: +${f.gold} gold each${f.extra}`; mine().includes(f.h) ? resultNote(f.h, t, () => toast(t, 'big')) : toast(t, 'big'); sfx.play('coin'); }); break;
      case 'opp': if (list.some(r => r.k === 'rise' && (r.news || []).some(n => n.tile === f.tile))) break; later.push(() => toast(`${S.static.opps[f.kind].name} sighted, for ${S.static.opps[f.kind].turns} turns`)); break;
      case 'garrison': if (list.some(r => r.k === 'rise')) break; later.push(() => toast('The garrisons grow: their bosses are harder to reach', 'big')); break;
      case 'raid': later.push(() => { bigBanner('Raiders march', `From ${S.static.dungeons[f.reg]} on ${S.game.places[f.to]?.name || 'a town'}, ${f.eta} turns away`, 'tide', 2600); if (mine().length) map?.centerOn(f.tile); sfx.play('rise'); }); break;
      case 'occupied': later.push(() => toast(`Raiders take ${S.game.places[f.tile]?.name || 'a town'}: it’s shut until you drive them out`, 'big')); break;
      case 'freed': later.push(() => { toast(`${S.game.places[f.tile]?.name || 'The town'} is free: +${f.gold} gold each`, 'big'); sfx.play('coin'); }); break;
      case 'raidstop': later.push(() => toast(`Raid broken: +${f.gold} gold each, and ${S.static.dungeons[f.reg]}’s garrison skips its next growth`, 'big')); break;
      case 'temper': later.push(() => { const it = item(S.game.heroes[f.h].equip[f.slot]); toast(`${S.game.heroes[f.h].name}’s ${it?.name || 'gear'}: ${f.what === 'hone' ? 'honed' : f.what === 'mark' ? 'marked' : `${cap(f.what)} now`}`); sfx.play('rare'); }); break;
      case 'found': later.push(() => { toast(`${S.game.heroes[f.h].name} finds a hidden grotto`); sfx.play('coin'); }); break;
      case 'lookout': later.push(() => toast(`${S.game.heroes[f.h].name} climbs the lookout: ${f.r} hexes of land on the map`)); break;
      case 'squall': later.push(() => toast({ squall: 'A squall gathers over Stormcrag’s waters', sandstorm: 'A sandstorm rises over the Shifting Sands', blizzard: 'A blizzard blows in over the Frostpeaks' }[f.kind || 'squall'])); break;
      case 'rumble': later.push(() => { toast('The volcano rumbles: it erupts next turn', 'big'); sfx.play('rise'); }); break;
      case 'erupt': later.push(() => { bigBanner('The volcano erupts', `Lava blocks ${f.tiles.length} hexes for ${S.static.biome.lava_turns} turns`, 'tide', 2400); if (mine().length) map?.centerOn(f.tile); sfx.play('rise'); }); break;
      case 'beacon': later.push(() => { toast(`${S.game.heroes[f.h].name} lights a beacon`); sfx.play('rare'); }); break;
      case 'gate': later.push(() => { toast(f.how === 'beacon' ? `${S.game.heroes[f.h].name} travels by beacon` : `${S.game.heroes[f.h].name} steps through the light-gate`); sfx.play('rare'); if (mine().includes(f.h)) map?.centerOn(f.to); }); break;
      case 'ask': if (!mine().includes(f.h)) { (UI.evOpen ||= {})[`${f.h}:${f.key}:${S.game.turn}`] = true; later.push(() => { toast(`${S.game.heroes[f.h].name} asks the party: ${S.static.events[f.key].title}`, 'big'); sfx.play('rare'); }); } break;
      case 'huddle': if (f.helpers.some(y => mine().includes(y))) later.push(() => sfx.play('rare')); break;
      case 'event':
        if (!mine().includes(f.h)) {
          later.push(() => toast(`${S.game.heroes[f.h].name} — ${S.static.events[f.key].title}: ${f.text}${f.bits?.length ? ` (${f.bits.join(', ')})` : ''}${f.roll ? ` · rolled ${f.roll.v}` : ''}`));
        }
        if (mine().includes(f.h)) {
          later.push(() => {
            resOf(f.h).outcomes.push({ title: S.static.events[f.key].title, text: f.text, roll: f.roll, bits: f.bits });
            renderDialogs();
          });
        }
        break;
    }
  }
  // gold comes as one line per hero, however many kills paid it
  for (const [x, n] of Object.entries(coins)) later.push(() => { const t = `${n > 0 ? '+' : ''}${n} gold`; n > 0 ? resultNote(+x, t, () => toast(`${S.game.heroes[x].name}: ${t}`)) : toast(`${S.game.heroes[x].name}: ${t}`); sfx.play('coin'); });
  // walking into a fight: the walk plays out on the map before the fight covers it
  // walking into a fight: the walk plays out on the map, then the clash, before the fight covers it
  if (map && speed && list.some(f => f.k === 'fight')) holdCombat(heroSteps * map.stepTime(speed) + 480);
  combatFx(list, before);
  for (const fn of later) afterCombat(fn);
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
    // on the results screen, number keys answer its first open choice
    const scope = scrim.querySelector('.res-now') || scrim;
    const opts = [...scope.querySelectorAll('.choice, button.pick, .loot-card:not(.taken)')];
    if (n >= 1 && n <= opts.length) {
      const o = opts[n - 1];
      (o.classList.contains('loot-card') ? o.querySelector('.pick-btns .btn.primary') : o)?.click();
      e.preventDefault();
    } else if (e.key === 'Enter') (scrim.querySelector('.res-continue') || (!opts.length && scrim.querySelector('.btn.primary')))?.click();
    return;
  }
  if (e.code === 'Space' && g.phase === 'plan') {
    const h0 = sel();
    if (mine().includes(h0) && g.plans[h0] && !g.pending[h0]?.length) { e.preventDefault(); send({ t: 'ready', h: h0, on: !g.plans[h0].ready }); }
  }
});
