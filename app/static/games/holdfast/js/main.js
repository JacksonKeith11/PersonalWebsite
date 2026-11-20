// Holdfast in the browser: the lobby, the board (drawn on a canvas from the server's snapshots), the
// tower bar, the items bar and the side panels. The server (app/holdfast/game.py) runs the fight;
// this only draws it and asks to build, upgrade, sell, give and use items.

import { person, startRoom } from '../../shared/lobby.js?v=1';

const $ = id => document.getElementById(id);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
};
const show = screen => { for (const id of ['menu', 'lobby', 'game']) $(id).hidden = id !== screen; };
const now = () => performance.now() / 1000;

const S = {
  cfg: null,           // the rules: towers, enemies, items, board size (from `welcome`)
  st: null,
  map: null,           // { paths, rocks, road: Set of "x,y" }
  enemies: new Map(),  // id -> { kind, x, y (drawn), fx, fy (from), tx, ty (to), at, hp, flags }
  shots: [],           // instant shots (auras, lightning): { kind, st, evolved, from, pts, at }
  flying: new Map(),   // projectiles: id -> { style, kind, evolved, x0, y0, vx, vy, at, life }
  booms: [],           // blasts: { x, y, r, look, at }
  traps: [],           // piles on the road: [id, kind code, x, y]
  sentries: [],        // [id, x, y, workshop id]
  bosses: [],          // boss events' bosses on the board: [id, kind index, health %, tier, shell %]
  dazed: {},           // tower id -> seconds a boss has knocked it out for
  gold: {},
  itemCd: {},          // item -> seconds until this player can use it again
  nextIn: null,
  picked: null,        // the kind of tower about to be built
  item: null,          // the item about to be used (aimed at the board)
  chosen: null,        // the id of the tower whose panel is open
  hover: null,         // the tile under the pointer
  cd: {},              // tower id -> seconds until its ability is ready
  undoUntil: {},       // tower id -> now() its undo runs out (for this player)
  glow: [0, 0, 0, 0],  // seconds left of Rally, Mark Them, Bounty Hunt and Unmake
  blasts: [],          // abilities, items and boss moves going off: { do, from, pts, at }
  floats: [],          // damage numbers: { x, y, n, at }
  preview: null,       // { x, y, r }: the reach a hovered upgrade would give
  saves: [],
};
let numbers = false;
try { numbers = localStorage.getItem('holdfast-numbers') === '1'; } catch { /* private mode */ }

const room = startRoom({ key: 'holdfast', path: '/games/holdfast', title: 'Holdfast', show, onMessage: receive });
const player = id => S.st?.players.find(p => p.id === id);
const me = () => player(room.you);
const tower = id => S.st?.towers?.find(t => t.id === id);

// Crosspathing: the main path is the one with more tiers (on a tie, the one bought first); the other
// path's tiers give only their `cross` bonus. The same sum as data.stats on the server.
const mainPath = (c, f) => (!c[0] && !c[1] ? null : c[0] !== c[1] ? (c[0] > c[1] ? 0 : 1) : (f === 0 || f === 1 ? f : 0));
function statsOf(kind, c = [0, 0], f = null) {
  const def = S.cfg.towers[kind], out = { ...def.base }, m = mainPath(c, f);
  if (m == null) return out;
  const mul = new Set(S.cfg.cross_mul), add = new Set(S.cfg.cross_add);
  for (const t of def.paths[m].tiers.slice(0, c[m])) Object.assign(out, t.set);
  for (const t of def.paths[1 - m].tiers.slice(0, c[1 - m])) {
    for (const [k, v] of Object.entries(t.cross)) {
      if (v === true) out[k] = true;
      else if (mul.has(k)) out[k] = (out[k] || 0) * v;
      else if (add.has(k)) out[k] = (out[k] || 0) + v;
      else out[k] = Math.max(out[k] || 0, v);
    }
  }
  return out;
}
const towerStats = t => statsOf(t.k, t.c, t.f);
const canBuy = (c, path) => c[path] + 1 <= EVOLUTION && (c[path] + 1 <= S.cfg.cross_max || c[1 - path] <= S.cfg.cross_max);
const EVOLUTION = 4;
// What to call a tower: its final evolution's name, or its kind.
const towerName = t => (t.n >= EVOLUTION ? S.cfg.towers[t.k].paths[t.p].tiers[EVOLUTION - 1].name : S.cfg.towers[t.k].name);
const myGold = () => S.gold[room.you] ?? me()?.gold ?? 0;
const itemCost = k => Math.round(S.cfg.items[k].cost * (1 + (S.st?.item_wave || 1) / 10));

function receive(m) {
  if (m.t === 'welcome') {
    S.cfg = m;
    buildPalette();
    buildItems();
    $('map').replaceChildren(...Object.entries(m.maps).map(([id, v]) => { const o = el('option', '', v.name); o.value = id; return o; }));
    $('bosses').replaceChildren(...Object.entries(m.bosses).map(([id, name]) => { const o = el('option', '', name); o.value = id; return o; }));
  } else if (m.t === 'map') {
    const road = new Set();
    for (const path of m.paths) {
      for (let i = 0; i + 1 < path.length; i++) {
        const [x0, y0] = path[i], [x1, y1] = path[i + 1];
        const n = Math.abs(x1 - x0) + Math.abs(y1 - y0);
        for (let k = 0; k <= n; k++) road.add(`${x0 + Math.sign(x1 - x0) * k},${y0 + Math.sign(y1 - y0) * k}`);
      }
    }
    S.map = { ...m, road, rocks: new Set(m.rocks.map(([x, y]) => `${x},${y}`)),
      build: m.build ? new Set(m.build.map(([x, y]) => `${x},${y}`)) : null };
    S.enemies.clear();
    S.flying.clear();
    S.shots = [];
    S.traps = [];
    S.sentries = [];
    S.picked = S.chosen = S.item = null;
  } else if (m.t === 'saves') {
    S.saves = m.list;
    if (S.st?.phase === 'lobby') renderLobbyLists();
  } else if (m.t === 'note') {
    $('saves-note').textContent = m.msg;
  } else if (m.t === 'state') {
    const was = S.st;
    S.st = m;
    S.undoUntil = {};
    for (const t of m.towers || []) if (t.un && t.un[0] === room.you) S.undoUntil[t.id] = now() + t.un[1];
    for (const p of m.players) S.gold[p.id] = p.gold;
    if (was && m.phase === 'play') {
      if (m.fighting && !was.fighting) sound('wave');
      if (m.lives < was.lives) sound('leak');
    }
    if (was && was.phase === 'play' && m.phase !== 'play' && m.phase !== 'lobby') sound(m.phase === 'won' ? 'win' : 'lose');
    render();
  } else if (m.t === 's') {
    snapshot(m);
  }
}

function snapshot(m) {
  const t = now(), seen = new Set();
  for (const [id, k, x, y, hp, flags, taken] of m.e) {
    seen.add(id);
    const e = S.enemies.get(id) || { x, y };
    S.enemies.set(id, Object.assign(e, { kind: S.cfg.kinds[k], fx: e.x, fy: e.y, tx: x, ty: y, at: t, hp,
      slow: flags & 1, burning: flags & 2, stunned: flags & 4, camo: flags & 8, shield: flags & 16, shell: flags & 32, charging: flags & 64 }));
    if (numbers && taken >= 1) S.floats.push({ x: x + 0.5 + (Math.random() - 0.5) * 0.3, y, n: taken, at: t });
  }
  if (S.floats.length > 120) S.floats.splice(0, S.floats.length - 120);
  for (const id of S.enemies.keys()) if (!seen.has(id)) S.enemies.delete(id);
  S.cd = m.a || {};
  S.dazed = m.dz || {};
  S.glow = m.gl || [0, 0, 0, 0];
  S.traps = m.tr || [];
  S.sentries = m.se || [];
  S.bosses = m.bo || [];
  S.itemCd = (m.ic || {})[room.you] || {};
  for (const [id, what, ...pts] of m.x || []) {
    const tw = tower(id);
    S.blasts.push({ do: what, from: tw ? [tw.x, tw.y] : null, pts, at: t });
    ability(what);
  }
  const heard = new Set();
  const listen = tw => { if (tw && !heard.has(tw.k)) { heard.add(tw.k); hit(tw.k, tw.n >= EVOLUTION); } };
  for (const [id, fx, fy, ...pts] of m.f) {
    const tw = tower(id);
    if (!tw) continue;
    S.shots.push({ kind: tw.k, st: towerStats(tw), evolved: tw.n >= EVOLUTION, from: [fx, fy], pts, at: t });
    listen(tw);
  }
  for (const [id, tid, style, x, y, vx, vy, life] of m.p || []) {
    const tw = tower(tid);
    S.flying.set(id, { style, kind: tw?.k, evolved: tw ? tw.n >= EVOLUTION : false, fire: tw ? towerStats(tw).dtype === 'fire' : false,
      x0: x, y0: y, vx, vy, at: t, life });
    listen(tw);
  }
  for (const id of m.pe || []) S.flying.delete(id);
  for (const [x, y, r, look] of m.bx || []) S.booms.push({ x, y, r, look, at: t });
  if (S.booms.length > 120) S.booms.splice(0, S.booms.length - 120);
  if ((m.bx || []).length) hit('boom');
  let killed = false;
  for (const [id, kills] of Object.entries(m.k || {})) {
    const tw = tower(+id);
    if (tw) { tw.kills = kills; killed = true; }
  }
  if (killed) { hit('pop'); if (S.chosen != null && $('kills')) $('kills').textContent = tower(S.chosen)?.kills ?? 0; }
  S.gold = m.g;
  S.nextIn = m.n;
  renderLive();
  renderAbilities();
  renderBoss();
}

// ---------------------------------------------------------------- sounds

let audio = null, noise = null, muted = false;
try { muted = localStorage.getItem('holdfast-muted') === '1'; } catch { /* private mode */ }
const lastHit = {};

function ctxAudio() {
  if (muted) return null;
  try {
    audio ||= new AudioContext();
    if (!noise) {
      noise = audio.createBuffer(1, audio.sampleRate * 0.5, audio.sampleRate);
      const d = noise.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    return audio;
  } catch { return null; }
}

// A pitched blip: from f0 to f1 over `secs`.
function tone(f0, f1, secs, type, vol = 0.05, delay = 0) {
  const a = ctxAudio();
  if (!a) return;
  const o = a.createOscillator(), g = a.createGain(), t = a.currentTime + delay;
  o.type = type;
  o.frequency.setValueAtTime(f0, t);
  o.frequency.exponentialRampToValueAtTime(f1, t + secs);
  g.gain.setValueAtTime(vol, t);
  g.gain.exponentialRampToValueAtTime(0.0005, t + secs);
  o.connect(g).connect(a.destination);
  o.start(t);
  o.stop(t + secs);
}

// A burst of filtered noise: thuds, whooshes and cracks.
function hiss(freq, q, secs, vol = 0.06, kind = 'bandpass') {
  const a = ctxAudio();
  if (!a) return;
  const src = a.createBufferSource(), f = a.createBiquadFilter(), g = a.createGain(), t = a.currentTime;
  src.buffer = noise;
  f.type = kind;
  f.frequency.value = freq;
  f.Q.value = q;
  g.gain.setValueAtTime(vol, t);
  g.gain.exponentialRampToValueAtTime(0.0005, t + secs);
  src.connect(f).connect(g).connect(a.destination);
  src.start(t);
  src.stop(t + secs);
}

function sound(kind) {
  if (kind === 'evolve') { tone(392, 784, 0.25, 'triangle', 0.06); tone(523, 1047, 0.3, 'triangle', 0.06, 0.12); tone(659, 1319, 0.5, 'triangle', 0.06, 0.24); return; }
  const [f0, f1, secs, type] = { build: [420, 640, 0.09, 'triangle'], up: [520, 1040, 0.16, 'triangle'], sell: [500, 250, 0.12, 'triangle'],
    wave: [196, 294, 0.5, 'sawtooth'], leak: [140, 60, 0.35, 'square'], win: [523, 1047, 0.8, 'triangle'], lose: [220, 55, 0.9, 'sawtooth'] }[kind];
  tone(f0, f1, secs, type);
}

// An ability, an item or a boss's move going off.
function ability(what) {
  if (what === 'strike' || what === 'item:keg') { hiss(150, 0.8, 0.8, 0.16, 'lowpass'); tone(200, 40, 0.7, 'sawtooth', 0.07); }
  else if (what === 'stun' || what === 'item:flask') { tone(2000, 3000, 0.4, 'sine', 0.05); tone(1500, 2400, 0.5, 'sine', 0.04, 0.08); }
  else if (what === 'gold' || what === 'bounty') { for (let i = 0; i < 5; i++) tone(1000 + i * 180, 1400 + i * 180, 0.12, 'triangle', 0.04, i * 0.07); }
  else if (what === 'zap') { tone(1800, 200, 0.3, 'sawtooth', 0.05); hiss(6000, 1, 0.2, 0.05, 'highpass'); }
  else if (what === 'skull') { tone(110, 55, 0.9, 'sawtooth', 0.08); tone(165, 82, 0.9, 'square', 0.04, 0.05); }
  else if (what === 'item:horn') { tone(220, 330, 0.6, 'sawtooth', 0.06); tone(330, 440, 0.5, 'sawtooth', 0.04, 0.3); }
  else if (what.startsWith('item:')) { tone(500, 700, 0.12, 'triangle', 0.05); }
  else { tone(300, 900, 0.5, 'square', 0.04); hiss(800, 1, 0.5, 0.05); }
}

// A weapon firing, at most once every 70 ms per weapon so a big defence doesn't roar. Final
// evolutions sound bigger.
function hit(kind, big = false) {
  const t = performance.now();
  if (muted || t - (lastHit[kind] || 0) < 70) return;
  lastHit[kind] = t;
  const v = big ? 1.6 : 1;
  switch (kind) {
    case 'archer': hiss(3200, 6, 0.06, 0.035 * v); tone(900, 500, 0.05, 'triangle', 0.02 * v); break;
    case 'cannon': hiss(180, 1, 0.3, 0.1 * v, 'lowpass'); tone(110, 40, 0.25, 'sine', 0.07 * v); break;
    case 'frost': tone(1800, 2400, 0.18, 'sine', 0.025 * v); tone(2700, 3600, 0.12, 'sine', 0.015 * v, 0.03); break;
    case 'ballista': tone(260, 90, 0.12, 'square', 0.04 * v); hiss(900, 3, 0.08, 0.05 * v); break;
    case 'tesla': tone(1400, 300, 0.12, 'sawtooth', 0.03 * v); hiss(5000, 2, 0.1, 0.03 * v, 'highpass'); break;
    case 'brazier': hiss(700, 0.6, 0.35, 0.05 * v); break;
    case 'mortar': hiss(120, 1, 0.45, 0.1 * v, 'lowpass'); tone(80, 30, 0.4, 'sine', 0.08 * v); break;
    case 'bladewheel': hiss(4200, 4, 0.08, 0.03 * v); tone(1200, 1600, 0.06, 'triangle', 0.015 * v); break;
    case 'workshop': tone(700, 400, 0.05, 'square', 0.02 * v); break;
    case 'arcanist': tone(600, 1300, 0.15, 'sine', 0.03 * v); tone(900, 1800, 0.1, 'sine', 0.015 * v, 0.04); break;
    case 'skyhook': tone(420, 120, 0.12, 'square', 0.035 * v); hiss(2000, 2, 0.1, 0.04 * v); break;
    case 'alchemist': hiss(1500, 3, 0.18, 0.04 * v); tone(300, 500, 0.1, 'sine', 0.02 * v); break;
    case 'boom': hiss(200, 1, 0.25, 0.06, 'lowpass'); break;
    case 'pop': tone(700, 1200, 0.05, 'triangle', 0.02); break;
  }
}

$('mute').addEventListener('click', () => {
  muted = !muted;
  try { localStorage.setItem('holdfast-muted', muted ? '1' : '0'); } catch { /* private mode */ }
  $('mute').textContent = muted ? '🔇' : '🔊';
  $('mute').setAttribute('aria-pressed', String(muted));
});
$('mute').textContent = muted ? '🔇' : '🔊';

// ---------------------------------------------------------------- the lobby and the panels

function render() {
  const st = S.st;
  document.body.classList.toggle('host', st.host === room.you);
  if (st.phase === 'lobby') {
    show('lobby');
    const host = st.host === room.you, seated = st.players.filter(p => p.seated).length;
    $('room-code').textContent = room.code;
    $('count').textContent = `${seated} of ${S.cfg.max}`;
    $('seats').replaceChildren(...st.players.map(p => person(p, room.you, !p.seated ? 'Watching' : p.id === st.host ? 'Host' : '')));
    $('map').value = st.map;
    $('diff').value = st.diff;
    $('bosses').value = st.bosses;
    $('map').disabled = $('diff').disabled = $('bosses').disabled = !host;
    $('map-blurb').textContent = S.cfg.maps[st.map].blurb;
    $('boss-blurb').textContent = st.bosses === 'warlord' ? 'Every tenth wave: Warlords, one more each time.'
      : st.bosses === 'random' ? 'Every tenth wave: one of the three bosses, picked at random, a tier tougher each time.'
        : `Every tenth wave, a tier tougher each time. ${S.cfg.enemies[st.bosses].blurb}`;
    $('lobby-note').textContent = host ? '' : `Waiting for ${player(st.host)?.name || 'the host'} to start.`;
    renderLobbyLists();
    return;
  }
  show('game');
  $('game-code').textContent = room.code;
  $('hud-wave').textContent = st.endless ? `Wave ${Math.max(1, st.wave)} (endless)` : `Wave ${Math.max(1, st.wave)} of ${S.cfg.waves}`;
  $('hud-lives').textContent = `♥ ${st.lives}`;
  $('hud-lives').classList.toggle('low', st.lives <= 5);
  $('speed').textContent = `Speed ×${st.speed}`;
  if (S.chosen != null && !tower(S.chosen)) S.chosen = null;
  renderLive();
  renderComing();
  renderInfo();

  const over = st.phase !== 'play';
  $('end').hidden = !over;
  if (over) renderEnd();
}

// The end of a game: the result, any record, the MVP tower, each player's best, and where lives went.
function renderEnd() {
  const st = S.st, sum = st.summary || {};
  $('end-kicker').textContent = st.phase === 'won' ? 'Victory' : sum.endless ? `Endless: fell on wave ${st.wave}` : `Fell on wave ${st.wave}`;
  $('end-title').textContent = st.phase === 'won' ? 'The keep holds!' : 'The keep has fallen';
  $('end-record').hidden = !st.record_new;
  $('end-record').textContent = 'A new record for this map and difficulty!';
  $('end-mvp').textContent = sum.mvp ? `Tower of the game: ${sum.mvp.name}, built by ${player(sum.mvp.owner)?.name || 'someone who left'}, with ${sum.mvp.kills} kills.` : '';
  $('end-rows').replaceChildren(...st.players.filter(p => p.seated).map(p => {
    const tr = el('tr'), name = el('td', '', p.name), dot = el('span', 'dot'), best = (sum.best || {})[p.id];
    dot.style.setProperty('--c', p.color);
    name.prepend(dot);
    tr.append(name, el('td', '', p.kills), el('td', '', p.dmg.toLocaleString()), el('td', '', best ? `${best.name} (${best.kills})` : '—'));
    return tr;
  }));
  const leaks = sum.leaks || [];
  $('end-leaks').textContent = leaks.length ? `Lives lost: ${leaks.map(([w, n]) => `wave ${w} (${n})`).join(', ')}.` : 'Not a single life lost.';
  $('endless').hidden = st.phase !== 'won' || st.endless;
}

function renderLobbyLists() {
  const st = S.st, host = st.host === room.you;
  $('saves').replaceChildren(...S.saves.map(g => {
    const li = el('li'), when = new Date(g.when * 1000);
    li.append(el('span', '', `${g.summary} (${when.toLocaleDateString()} ${when.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`));
    if (host) {
      const go = el('button', 'primary', 'Resume');
      go.type = 'button';
      go.addEventListener('click', () => room.send({ t: 'resume', id: g.id }));
      li.append(go);
    }
    const del = el('button', '', 'Delete');
    del.type = 'button';
    del.addEventListener('click', () => room.send({ t: 'forget', id: g.id }));
    li.append(del);
    return li;
  }));
  if (!S.saves.length) $('saves-note').textContent = 'Games save between waves; your unfinished ones show up here.';
  else if (!host) $('saves-note').textContent = 'The host can resume a game you were in.';
  else $('saves-note').textContent = '';
  $('records-for').textContent = `${S.cfg.maps[st.map].name}, ${st.diff}`;
  const recs = st.records || [];
  $('records').replaceChildren(...(recs.length ? recs.map(r => {
    const li = el('li');
    li.append(el('b', '', r.won ? '30 ✓' : `${r.wave}`), el('span', '', `${r.names.join(', ')} (${new Date(r.at * 1000).toLocaleDateString()})`));
    return li;
  }) : [el('li', '', 'No games on this map and difficulty yet.')]));
}

// The bar of final evolutions' abilities, with how long until each is ready.
function renderAbilities() {
  const st = S.st, bar = $('abilities');
  const evolved = (st?.towers || []).filter(t => t.n >= EVOLUTION);
  bar.hidden = !evolved.length || st.phase !== 'play';
  if (bar.hidden) return;
  const want = evolved.map(t => t.id).join(',');
  if (bar.dataset.ids !== want) {
    bar.dataset.ids = want;
    bar.replaceChildren(...evolved.map(t => {
      const a = abilityOf(t), b = el('button');
      b.type = 'button';
      b.dataset.id = t.id;
      b.append(el('b', '', a.name), el('small', '', towerName(t)), el('i', 'fill'));
      b.title = a.blurb;
      b.addEventListener('click', () => useAbility(t.id));
      return b;
    }));
  }
  for (const b of bar.children) {
    const t = tower(+b.dataset.id), left = S.cd[b.dataset.id] ?? 0, a = abilityOf(t);
    b.classList.toggle('ready', left <= 0 && st.fighting);
    b.disabled = left > 0 || !st.fighting || !me()?.seated;
    b.querySelector('.fill').style.width = `${100 * (1 - left / a.cd)}%`;
    b.querySelector('small').textContent = left > 0 ? `ready in ${Math.ceil(left)} s` : st.fighting ? 'ready' : 'ready when a wave is on';
  }
}

const abilityOf = t => t && t.n >= EVOLUTION ? S.cfg.towers[t.k].paths[t.p].tiers[EVOLUTION - 1].ability : null;
function useAbility(id) {
  const t = tower(id);
  if (t && abilityOf(t) && (S.cd[id] ?? 0) <= 0 && S.st.fighting) room.send({ t: 'ability', id });
}

// A boss event's boss: its name, tier, health with the skulls marked, and any shell.
function renderBoss() {
  const box = $('bossbar'), b = S.bosses[0];
  box.hidden = !b || S.st?.phase !== 'play';
  if (box.hidden) return;
  const [id, k, hp, tier, shell] = b, kind = S.cfg.kinds[k], def = S.cfg.enemies[kind];
  if (box.dataset.id !== String(id)) {
    box.dataset.id = id;
    box.replaceChildren(el('b', '', `${def.name}, tier ${tier}`), el('div', 'bar'));
    const bar = box.querySelector('.bar');
    bar.append(el('i', 'hp'), el('i', 'shell'));
    for (const s of def.skulls || []) { const sk = el('span', 'skull', '☠'); sk.style.left = `${s * 100}%`; bar.append(sk); }
  }
  box.querySelector('.hp').style.width = `${hp}%`;
  box.querySelector('.shell').style.width = `${Math.min(100, shell)}%`;
  box.classList.toggle('shielded', !!S.enemies.get(id)?.shield);
}

// What the next wave brings: each kind drawn as on the board, how many, what's special about it,
// and a warning when nothing built can deal with it (nothing that sees Ghosts, hits flyers, or can
// hurt an enemy that's immune to what's built).
const plural = (n, word) => (word.startsWith('The ') ? word : `${n} ${word}${n === 1 ? '' : word.endsWith('s') ? 'es' : 's'}`);
const listed = a => (a.length < 2 ? a.join('') : `${a.slice(0, -1).join(', ')} and ${a[a.length - 1]}`);
function traits(e) {
  const kids = (e.children || []).map(([k, n]) => plural(n, S.cfg.enemies[k].name));
  return [e.event && 'boss event', e.camo && 'camouflaged', e.air && 'flies', e.armor && 'armoured',
    e.immune && `immune to ${listed(e.immune.map(d => DTYPE[d]))}`, e.heal && 'heals others', kids.length && `bursts into ${listed(kids)}`,
    (e.lives || 1) > 1 && `costs ${e.lives} lives`, e.summon && 'calls up Grunts'].filter(Boolean);
}
// The damage type a tower deals, and whether it can hit flyers.
const dealt = t => { const s = towerStats(t), w = s.mode === 'sentry' ? s.sentry : s; return { dtype: w.dtype || 'normal', air: !!w.air, any: !!t.ul, attacks: !['support', 'income'].includes(s.mode) }; };
function renderComing() {
  const st = S.st, box = $('coming'), foes = S.cfg.enemies;
  const counts = new Map();
  for (const [k, n] of st.coming) counts.set(k, (counts.get(k) || 0) + n);
  const kinds = [...counts.keys()];
  const sight = st.towers.some(t => t.cs), arms = st.towers.map(dealt).filter(d => d.attacks), antiAir = arms.some(d => d.air);
  const warn = [];
  if (kinds.some(k => foes[k].camo) && !sight) warn.push('Nothing built can see Ghosts. Longbow (Archer), Heavy Bolts (Ballista), Seer\'s Eye (Arcanist), a Frost or Brazier, or a tower beside a Spyglass (Beacon) can.');
  if (kinds.some(k => foes[k].air) && !antiAir) warn.push('Nothing built can hit flyers. Archers, Frost, Ballistas, Teslas, Bladewheels, Arcanists and Skyhooks can.');
  for (const k of kinds) {
    const imm = foes[k].immune;
    if (imm && arms.length && !arms.some(d => d.any || !imm.includes(d.dtype))) warn.push(`Nothing built can hurt ${foes[k].name.replace(/^The /, 'the ')}: it's immune to ${listed(imm.map(d => DTYPE[d]))}. Some upgrades hurt anything, and so does a tower beside a Solvent Draught (Alchemist).`);
  }
  const key = JSON.stringify([st.wave, st.fighting, [...counts], warn]);
  if (box.dataset.key === key) return;
  box.dataset.key = key;
  if (!kinds.length) { box.replaceChildren(el('p', '', st.fighting ? 'The last wave: hold them off.' : '')); return; }
  const head = el('p', 'next-head', st.fighting ? `Next, wave ${st.wave + 1}:` : 'Coming:');
  const list = el('ul', 'foes');
  for (const k of kinds) {
    const li = el('li'), icon = document.createElement('canvas');
    icon.width = icon.height = 56;
    icon.setAttribute('aria-hidden', 'true');
    const c = icon.getContext('2d');
    c.scale(56 / 1.4, 56 / 1.4);
    const [color, r] = ENEMY[k] || ['#ccc', 0.27];
    if (foes[k].camo) c.globalAlpha = 0.6;
    drawEnemyBody(c, k, 0.7, 0.7, Math.min(0.6, 0.25 + r * 0.6), color, 0, true);   // big ones a little bigger
    const text = el('span');
    text.append(el('b', '', plural(counts.get(k), foes[k].name)));
    const tr = traits(foes[k]);
    if (tr.length) text.append(el('small', '', tr.join(', ')));
    li.append(icon, text);
    if (foes[k].camo || foes[k].lives > 1 || foes[k].air || foes[k].immune) li.classList.add('special');
    list.append(li);
  }
  box.replaceChildren(head, list, ...warn.map(w => el('p', 'warn', w)));
}

// The parts that change with every snapshot: gold, the countdown, what can be afforded.
function renderLive() {
  const st = S.st;
  if (!st || st.phase === 'lobby') return;
  const gold = myGold(), seated = me()?.seated;
  $('wave-title').textContent = st.fighting ? `Wave ${st.wave}` : st.wave >= S.cfg.waves && !st.endless ? 'All waves beaten'
    : `Wave ${st.wave + 1} in ${Math.ceil(S.nextIn ?? 0)} s`;
  const chips = ['Rally', 'Mark Them', 'Bounty Hunt', 'Unmake'].map((label, i) => S.glow[i] > 0 ? `${label} ${Math.ceil(S.glow[i])} s` : null).filter(Boolean);
  let box = $('chips');
  if (!box) { box = el('div', 'chips'); box.id = 'chips'; $('coming').after(box); }
  box.replaceChildren(...chips.map(c => el('span', 'chip', c)));
  if (S.chosen != null) {
    const a = $('info').querySelector('.ability-btn'), left = S.cd[S.chosen] ?? 0;
    if (a) { a.disabled = left > 0 || !st.fighting; a.textContent = a.dataset.label + (left > 0 ? ` (${Math.ceil(left)} s)` : st.fighting ? ': ready' : ' (when a wave is on)'); }
    const u = $('info').querySelector('.undo-btn'), until = S.undoUntil[S.chosen];
    if (u) {   // stays in place, greyed out, so nothing below it moves
      const live = until && until > now();
      u.disabled = !live;
      u.textContent = live ? `Undo (${Math.ceil(until - now())} s)` : 'Undo';
    }
  }
  // hidden but keeping its space, so the panels under it don't jump
  $('ready').style.visibility = st.fighting || !seated || st.phase !== 'play' ? 'hidden' : 'visible';
  $('ready').disabled = !!me()?.ready;
  $('ready').textContent = me()?.ready ? 'Waiting for the others…' : 'Ready: send it now';
  $('purses').replaceChildren(...st.players.filter(p => p.seated).map(p => {
    const li = person(p, room.you, String(S.gold[p.id] ?? p.gold));
    if (p.id !== room.you && seated && st.phase === 'play') {
      const give = el('button', '', `Give ${S.cfg.gift}`);
      give.type = 'button';
      give.disabled = gold < S.cfg.gift;
      give.addEventListener('click', () => room.send({ t: 'give', to: p.id }));
      li.append(give);
    }
    return li;
  }));
  for (const b of $('palette').children) b.classList.toggle('poor', gold < S.cfg.towers[b.dataset.kind].cost);
  for (const b of $('items').children) {
    const k = b.dataset.kind, it = S.cfg.items[k], cost = itemCost(k), left = S.itemCd[k] || 0;
    b.querySelector('.cost').textContent = left > 0 ? `${Math.ceil(left)} s` : cost;
    b.disabled = !seated || left > 0 || gold < cost || (it.fight && !st.fighting);
    b.setAttribute('aria-pressed', String(S.item === k));
  }
  if (S.item && $(`items`).querySelector(`[data-kind="${S.item}"]`)?.disabled) S.item = null;
  for (const up of $('info').querySelectorAll('[data-cost]')) up.disabled = up.dataset.locked === '1' || gold < +up.dataset.cost;
}

const pct = v => `${Math.round(v * 100)}%`;
const num = v => (typeof v === 'number' ? String(Math.round(v * 100) / 100) : v);
const DTYPE = { sharp: 'sharp', blast: 'blast', cold: 'cold', energy: 'lightning', fire: 'fire', arcane: 'arcane', normal: 'normal (hurts anything)' };
const STAT = [['dtype', 'Damage', v => DTYPE[v] || v], ['dmg', 'Damage a hit'], ['shots', 'Shots'], ['rate', 'Every', v => `${num(v)} s`], ['range', 'Reach'],
  ['pierce', 'Goes through', v => `${num(v)} enemies`], ['splash', 'Blast'], ['cluster', 'Extra blasts'], ['chain', 'Jumps to'],
  ['slow', 'Slows by', pct], ['stun', 'Stuns for', v => `${num(v)} s`], ['burn', 'Burns', v => `${num(v)} a second`], ['shred', 'Strips armour', v => `${num(v)} a hit`],
  ['brittle', 'Slowed take', v => `${pct(v)} more`], ['boss', 'Against bosses and blimps', v => `×${num(v)}`],
  ['ap', 'Ignores armour', () => 'yes'], ['air', 'Hits flyers', v => (v ? 'yes' : 'no')], ['ground', 'Hits the ground', v => (v ? 'yes' : 'no')],
  ['detect', 'Sees Ghosts', () => 'yes'], ['lob', 'Lobbed', () => 'yes, moving targets can dodge'],
  ['hits', 'Each pile hurts', v => `${num(v)} enemies`], ['max', 'At a time', num], ['life', 'Each lasts', v => `${num(v)} s`],
  ['boost', 'Speeds up', pct], ['reach', 'Extends reach', pct], ['power', 'Adds damage', pct], ['reveal', 'Reveals Ghosts', () => 'yes'],
  ['unlock', 'Towers near it hurt', () => 'every type'],
  ['income', 'Pays a wave', v => `${num(v)} gold`], ['bounty', 'Kill bonus', pct]];

function statList(stats) {
  const dl = el('dl'), quiet = ['support', 'income', 'sentry'].includes(stats.mode);
  for (const [key, label, fmt = num] of STAT) {
    if (stats[key] == null || ((key === 'air' || key === 'ground') && quiet) || (key === 'ground' && stats.ground !== false)) continue;
    if (key === 'dtype' && quiet) continue;
    if (key === 'boost' && !quiet && stats.mode !== 'support') continue;
    dl.append(el('dt', '', label), el('dd', '', fmt(stats[key])));
  }
  if (stats.sentry) {
    const s = stats.sentry;
    dl.append(el('dt', '', 'Sentries'), el('dd', '', `${num(s.dmg)} ${DTYPE[s.dtype] === DTYPE.normal ? '' : DTYPE[s.dtype] + ' '}damage every ${num(s.rate)} s, reach ${num(s.range)}${s.chain ? `, jumps to ${s.chain}` : ''}${s.splash ? ', blasts' : ''}${s.pierce > 1 ? `, through ${s.pierce}` : ''}${s.detect ? ', sees Ghosts' : ''}`));
  }
  return dl;
}

// What a tier gives a tower whose main path is the other one, in words.
const CROSS_WORD = { dmg: 'damage', range: 'reach', splash: 'blast', burn: 'burning', income: 'income', life: 'life', speed: 'projectile speed',
  pierce: 'pierce', chain: 'jumps', cluster: 'extra blast', hits: 'hits a pile', max: 'at a time', shred: 'armour stripped a hit', shots: 'shot a volley',
  slow: 'slows by at least', stun: 'stuns for at least', boost: 'speeds towers beside it by at least', reach: 'extends reach beside it by at least',
  power: 'adds damage beside it of at least', bounty: 'kill bonus of at least', hold: 'holds for at least', burn_for: 'burns for at least' };
const CROSS_ON = { detect: 'sees Ghosts', ap: 'ignores armour', reveal: 'reveals Ghosts to towers beside it', ground: 'hits the ground too', unlock: 'towers beside it hurt every type', air: 'hits flyers' };
function crossText(cross) {
  const parts = Object.entries(cross).map(([k, v]) => {
    if (v === true) return CROSS_ON[k] || k;
    if (k === 'rate') return `${Math.round((1 / v - 1) * 100)}% faster`;
    if (S.cfg.cross_mul.includes(k)) return `${Math.round((v - 1) * 100)}% ${v >= 1 ? 'more' : 'less'} ${CROSS_WORD[k]}`;
    if (S.cfg.cross_add.includes(k)) return `+${v} ${CROSS_WORD[k]}`;
    const shown = ['slow', 'boost', 'reach', 'power', 'bounty'].includes(k) ? pct(v) : ['stun', 'hold', 'burn_for'].includes(k) ? `${v} s` : v;
    return `${CROSS_WORD[k] || k} ${shown}`;
  });
  const s = parts.join(', ');
  return s ? s[0].toUpperCase() + s.slice(1) : 'Nothing extra';
}

function renderInfo() {
  const box = $('info'), T = S.cfg.towers;
  const tw = S.chosen != null ? tower(S.chosen) : null;
  if (S.item && !tw) {
    const it = S.cfg.items[S.item];
    const where = { road: 'Click or tap a square of road.', free: 'Click or tap a free square off the road.', any: 'Click or tap anywhere on the board.' }[it.place];
    box.replaceChildren(el('h2', '', `${it.name} (${itemCost(S.item)} gold)`), el('p', '', it.blurb), el('p', '', where));
    return;
  }
  const kind = tw ? tw.k : S.picked;
  if (!kind) { box.replaceChildren(); return; }
  const def = T[kind];
  if (!tw) {
    box.replaceChildren(el('h2', '', `${def.name} (${def.cost} gold)`), el('p', '', def.blurb), statList(def.base),
      el('p', '', 'Click or tap a free square to build it.'));
    return;
  }
  const evolved = tw.n >= EVOLUTION, c = tw.c, m = tw.p;
  const title = el('h2', evolved ? 'evolved' : '', towerName(tw));
  const sub = m == null ? 'Not upgraded yet' : `${def.paths[m].name}, ${c[0]}-${c[1]}${evolved ? ': final evolution' : ''}`;
  const tally = el('p', 'tally');
  tally.append('Kills: ', el('b', '', ''), ` · damage ${Number(tw.dmg || 0).toLocaleString()} · built by ${player(tw.o)?.name || 'someone who left'}`);
  tally.querySelector('b').id = 'kills';
  tally.querySelector('b').textContent = tw.kills;
  if (S.dazed[tw.id] > 0) tally.append(el('b', 'dazed', ` · knocked out ${Math.ceil(S.dazed[tw.id])} s`));
  const parts = [title, el('p', '', sub), tally];
  // Undo and Sell sit in one row of fixed height at the top, away from the upgrade buttons, and are
  // always there (greyed out when they can't be used), so nothing in the panel moves under the pointer.
  if (me()?.seated) {
    const row = el('div', 'actions');
    const u = el('button', 'undo-btn', 'Undo');
    u.type = 'button';
    u.disabled = !(S.undoUntil[tw.id] > now());
    u.title = 'Take back the latest build or upgrade for a full refund (only for a few seconds, and only who paid)';
    u.addEventListener('click', () => { sound('sell'); room.send({ t: 'undo', id: tw.id }); });
    row.append(u);
    if (tw.o === room.you) {
      const sell = el('button', 'sell', `Sell for ${Math.round(tw.s * S.cfg.sell)}`);
      sell.type = 'button';
      sell.addEventListener('click', () => { sound('sell'); room.send({ t: 'sell', id: tw.id }); S.chosen = null; });
      row.append(sell);
    } else row.append(el('span', 'note', 'Only its builder can sell it.'));
    parts.push(row);
  }
  const ab = abilityOf(tw);
  if (ab && me()?.seated) {
    const b = el('button', 'ability-btn', '');
    b.type = 'button';
    b.dataset.label = ab.name;
    b.title = ab.blurb;
    const left = S.cd[tw.id] ?? 0;
    b.textContent = ab.name + (left > 0 ? ` (${Math.ceil(left)} s)` : S.st.fighting ? ': ready' : ' (when a wave is on)');
    b.disabled = left > 0 || !S.st.fighting;
    b.addEventListener('click', () => useAbility(tw.id));
    parts.push(b, el('p', 'note ability-blurb', ab.blurb));
  }
  const st0 = towerStats(tw);
  if (!['support', 'income', 'trap', 'sentry'].includes(st0.mode)) {
    const row = el('div', 'targets');
    for (const v of S.cfg.targets) {
      const b = el('button', '', v[0].toUpperCase() + v.slice(1));
      b.type = 'button';
      b.setAttribute('aria-pressed', String(tw.tg === v));
      b.title = { first: 'The one nearest the keep', last: 'The one furthest back', strong: 'The one with the most health', close: 'The one nearest this tower' }[v];
      b.addEventListener('click', () => room.send({ t: 'target', id: tw.id, v }));
      row.append(b);
    }
    parts.push(row);
  }
  parts.push(statList(st0));
  if (tw.ul) parts.push(el('p', 'note', 'A Solvent Draught beside it: it hurts every type.'));

  // the two upgrade paths: the next tier on each (in full, or what it gives on the side), or why not
  const paths = el('div', 'paths');
  def.paths.forEach((path, pi) => {
    const col = el('section', `path${m === pi ? ' taken' : ''}`);
    const side = m != null && m !== pi && c[m] > S.cfg.cross_max;
    const pips = el('span', 'pips');
    for (let i = 1; i <= EVOLUTION; i++) pips.append(el('i', c[pi] >= i ? 'on' : side && i > S.cfg.cross_max ? 'shut' : i === EVOLUTION ? 'evo' : ''));
    col.append(el('h3', '', path.name), pips);
    const next = path.tiers[c[pi]];
    if (!next) col.append(el('p', 'note', 'Fully evolved.'));
    else if (!canBuy(c, pi)) col.append(el('p', 'note', `Closed past tier ${S.cfg.cross_max}: ${def.paths[1 - pi].name} went further.`));
    else {
      const after = [...c];
      after[pi] += 1;
      const full = mainPath(after, tw.f ?? pi) === pi, evo = full && after[pi] === EVOLUTION;
      const taken = evo && S.st.towers.some(o => o.id !== tw.id && o.k === kind && o.p === pi && o.n >= EVOLUTION);
      col.append(el('p', 'next', `${evo ? 'Final evolution: ' : ''}${next.name}`),
        el('p', 'note', full ? next.blurb.replace(/^Final evolution: /, '') : `On the side: ${crossText(next.cross)}.`));
      if (me()?.seated) {
        const up = el('button', evo ? 'primary evo' : 'primary', `${evo ? 'Evolve' : 'Buy'}: ${next.cost} gold`);
        up.type = 'button';
        up.dataset.cost = next.cost;
        up.dataset.path = pi;
        up.dataset.locked = taken ? '1' : '0';
        up.disabled = taken || myGold() < next.cost;
        up.addEventListener('click', () => { sound(evo ? 'evolve' : 'up'); room.send({ t: 'up', id: tw.id, path: pi }); });
        const r = statsOf(kind, after, tw.f ?? pi).range;
        up.addEventListener('pointerenter', () => { S.preview = { x: tw.x, y: tw.y, r: Math.min(r, 12) }; });
        up.addEventListener('pointerleave', () => { S.preview = null; });
        col.append(up);
        if (taken) col.append(el('p', 'note', `There's already a ${next.name}: only one at a time.`));
      }
    }
    paths.append(col);
  });
  parts.push(paths);
  box.replaceChildren(...parts);
  S.preview = null;
}

function pick(kind) {
  S.picked = S.picked === kind ? null : kind;
  S.chosen = null;
  S.item = null;
  for (const b of $('palette').children) b.setAttribute('aria-pressed', String(b.dataset.kind === S.picked));
  renderInfo();
  renderLive();
}

function pickItem(kind) {
  const it = S.cfg.items[kind];
  if (it.place === 'none') { room.send({ t: 'item', k: kind }); return; }
  S.item = S.item === kind ? null : kind;
  S.picked = S.chosen = null;
  for (const b of $('palette').children) b.setAttribute('aria-pressed', 'false');
  renderInfo();
  renderLive();
}

const keyName = i => (i < 9 ? String(i + 1) : i === 9 ? '0' : `Shift+${i - 9}`);
function buildPalette() {
  $('palette').replaceChildren(...Object.entries(S.cfg.towers).map(([kind, def], i) => {
    const b = el('button');
    b.type = 'button';
    b.dataset.kind = kind;
    b.setAttribute('aria-pressed', 'false');
    b.title = `${def.blurb} (key ${keyName(i)})`;
    const icon = document.createElement('canvas');
    icon.width = icon.height = 68;
    const c = icon.getContext('2d');
    c.setTransform(60, 0, 0, 60, 34, 34);
    drawTower(c, kind, null, 0, '#c9d3dd');
    b.append(icon, el('span', '', def.name), el('span', 'cost', def.cost));
    b.addEventListener('click', () => pick(kind));
    return b;
  }));
}

function buildItems() {
  $('items').replaceChildren(...Object.entries(S.cfg.items).map(([kind, it]) => {
    const b = el('button');
    b.type = 'button';
    b.dataset.kind = kind;
    b.title = it.blurb;
    b.append(el('span', '', it.name), el('span', 'cost', it.cost));
    b.addEventListener('click', () => pickItem(kind));
    return b;
  }));
}

$('map').addEventListener('change', () => room.send({ t: 'set', map: $('map').value }));
$('diff').addEventListener('change', () => room.send({ t: 'set', diff: $('diff').value }));
$('bosses').addEventListener('change', () => room.send({ t: 'set', bosses: $('bosses').value }));
$('start').addEventListener('click', () => room.send({ t: 'start' }));
$('again').addEventListener('click', () => room.send({ t: 'again' }));
$('ready').addEventListener('click', () => room.send({ t: 'ready' }));
$('speed').addEventListener('click', () => room.send({ t: 'speed', v: S.st.speed % 3 + 1 }));
$('endless').addEventListener('click', () => room.send({ t: 'endless' }));
$('numbers').addEventListener('click', () => {
  numbers = !numbers;
  try { localStorage.setItem('holdfast-numbers', numbers ? '1' : '0'); } catch { /* private mode */ }
  $('numbers').setAttribute('aria-pressed', String(numbers));
  S.floats = [];
});
$('numbers').setAttribute('aria-pressed', String(numbers));

// Keys: 1-9 and 0 pick a tower to build, Shift+1-5 the rest; with a tower chosen, Z and X buy on
// its paths, Q sets off its ability, T changes what it aims at, U undoes; Space sends the next wave;
// Esc puts things away.
addEventListener('keydown', e => {
  if ($('game').hidden || e.target.tagName === 'INPUT' || e.ctrlKey || e.metaKey || e.altKey) return;
  const kinds = Object.keys(S.cfg.towers), tw = S.chosen != null ? tower(S.chosen) : null, k = e.key.toLowerCase();
  const digit = /^Digit(\d)$/.exec(e.code), d = digit ? (+digit[1] + 9) % 10 : -1;   // Digit1 -> 0 ... Digit0 -> 9
  if (e.key === 'Escape') { S.chosen = null; S.item = null; if (S.picked) pick(S.picked); else { renderInfo(); renderLive(); } }
  else if (d >= 0 && kinds[e.shiftKey ? d + 10 : d] && (!e.shiftKey || d < 5)) pick(kinds[e.shiftKey ? d + 10 : d]);
  else if (e.key === ' ' && !S.st.fighting && me()?.seated) { e.preventDefault(); room.send({ t: 'ready' }); }
  else if (tw && (k === 'z' || k === 'x')) {
    const b = $('info').querySelector(`button[data-path="${k === 'z' ? 0 : 1}"]`);
    if (b && !b.disabled) b.click();
  } else if (tw && k === 'q') useAbility(tw.id);
  else if (tw && k === 't') room.send({ t: 'target', id: tw.id, v: S.cfg.targets[(S.cfg.targets.indexOf(tw.tg) + 1) % S.cfg.targets.length] });
  else if (tw && k === 'u' && S.undoUntil[tw.id] > now()) room.send({ t: 'undo', id: tw.id });
});

// ---------------------------------------------------------------- the board

const canvas = $('board'), ctx = canvas.getContext('2d');
const tileAt = e => {
  const r = canvas.getBoundingClientRect();
  return [Math.floor((e.clientX - r.left) / r.width * S.cfg.cols), Math.floor((e.clientY - r.top) / r.height * S.cfg.rows)];
};
const towerAt = (x, y) => S.st.towers.find(t => t.x === x && t.y === y);
const onBoard = (x, y) => x >= 0 && y >= 0 && x < S.cfg.cols && y < S.cfg.rows;
const free = (x, y) => onBoard(x, y) && !S.map.road.has(`${x},${y}`) && !S.map.rocks.has(`${x},${y}`)
  && (!S.map.build || S.map.build.has(`${x},${y}`)) && !towerAt(x, y);
// Whether the item being aimed can go on this square.
const itemFits = (kind, x, y) => {
  const place = S.cfg.items[kind].place;
  return place === 'road' ? S.map.road.has(`${x},${y}`) : place === 'free' ? free(x, y) : onBoard(x, y);
};

canvas.addEventListener('pointermove', e => { S.hover = tileAt(e); });
canvas.addEventListener('pointerleave', () => { S.hover = null; });
canvas.addEventListener('click', e => {
  if (!S.map || S.st.phase !== 'play') return;
  const [x, y] = tileAt(e), there = towerAt(x, y);
  if (S.item && me()?.seated) {
    if (itemFits(S.item, x, y)) { room.send({ t: 'item', k: S.item, x, y }); S.item = null; renderInfo(); renderLive(); }
  } else if (there) {
    if (S.picked) pick(S.picked);
    S.chosen = S.chosen === there.id ? null : there.id;
    renderInfo();
  } else if (S.picked && me()?.seated) {
    if (free(x, y) && myGold() >= S.cfg.towers[S.picked].cost) { sound('build'); room.send({ t: 'build', k: S.picked, x, y }); }
  } else {
    S.chosen = null;
    renderInfo();
  }
  if (e.pointerType === 'touch') S.hover = S.picked || S.item ? [x, y] : null;
});
canvas.addEventListener('contextmenu', e => { e.preventDefault(); if (S.picked) pick(S.picked); else if (S.item) pickItem(S.item); });

const TOWER_COLOR = { archer: '#7fb069', cannon: '#8a96a3', frost: '#7fd0e8', ballista: '#b08a5a', tesla: '#c9a0f0', beacon: '#f2c230',
  brazier: '#ff7a2f', mortar: '#a3a9b3', mint: '#f2d14a', bladewheel: '#c8d0d8', trapper: '#b58a55', workshop: '#e0954a',
  arcanist: '#9b7bff', skyhook: '#5fd0c8', alchemist: '#86d455' };
const PATH_COLOR = ['#f2c230', '#6fd0ff'];
const ENEMY = {   // colour and radius, in tiles
  grunt: ['#d9534a', 0.27], runner: ['#f09a3e', 0.2], swarm: ['#b06fd6', 0.14], brute: ['#8f2d2d', 0.4],
  shield: ['#4f7fc9', 0.3], flyer: ['#f3f0e6', 0.24], boss: ['#3a2440', 0.55],
  ghost: ['#e8f0ff', 0.25], healer: ['#5cc46a', 0.28], splitter: ['#c78a3a', 0.3], gargoyle: ['#6b6f78', 0.3],
  ironclad: ['#8d949c', 0.32], cinder: ['#2b2420', 0.22], frostborn: ['#bfe8ff', 0.25], warded: ['#8b5cf6', 0.27],
  juggernaut: ['#45603f', 0.6], colossus: ['#6a2f2f', 0.75],
  gravewarden: ['#d8d0b8', 0.62], stormhulk: ['#2f4f8f', 0.64], ironmaw: ['#5b5f66', 0.62],
};
const FLYING = new Set(['flyer', 'gargoyle']);

// A tower, drawn in a 1 x 1 box centred on the origin: its tiers as pips in its path's colour (the
// main path's above, the side path's below), and a final evolution bigger, gold-rimmed and glowing.
function drawTower(c, kind, path, tier, ring, side = 0) {
  const evo = tier >= EVOLUTION, t = performance.now() / 1000;
  if (evo) {
    c.fillStyle = `rgba(255, 215, 90, ${0.25 + 0.12 * Math.sin(t * 3)})`;
    c.beginPath(); c.arc(0, 0, 0.62, 0, 7); c.fill();
  }
  c.fillStyle = evo ? '#3a2f1a' : '#2a3542';
  c.strokeStyle = evo ? '#ffd75a' : ring;
  c.lineWidth = evo ? 0.1 : 0.07;
  c.beginPath();
  c.roundRect(-0.42, -0.42, 0.84, 0.84, 0.14);
  c.fill();
  c.stroke();
  if (evo) { c.strokeStyle = ring; c.lineWidth = 0.05; c.beginPath(); c.roundRect(-0.32, -0.32, 0.64, 0.64, 0.1); c.stroke(); }
  c.save();
  if (evo) c.scale(1.15, 1.15);
  c.fillStyle = c.strokeStyle = TOWER_COLOR[kind];
  c.lineWidth = 0.09;
  c.lineCap = 'round';
  c.beginPath();
  if (kind === 'archer') { c.moveTo(0, -0.26); c.lineTo(0.22, 0.2); c.lineTo(-0.22, 0.2); c.closePath(); c.fill(); }
  else if (kind === 'cannon') { c.arc(0, 0.04, 0.2, 0, 7); c.fill(); c.fillRect(-0.08, -0.3, 0.16, 0.3); }
  else if (kind === 'frost') { for (let i = 0; i < 3; i++) { const a = i * Math.PI / 3; c.moveTo(-Math.cos(a) * 0.26, -Math.sin(a) * 0.26); c.lineTo(Math.cos(a) * 0.26, Math.sin(a) * 0.26); } c.stroke(); }
  else if (kind === 'ballista') { c.moveTo(0, 0.26); c.lineTo(0, -0.28); c.moveTo(-0.24, -0.02); c.quadraticCurveTo(0, -0.3, 0.24, -0.02); c.stroke(); }
  else if (kind === 'tesla') { c.moveTo(0.06, -0.28); c.lineTo(-0.14, 0.04); c.lineTo(0.02, 0.04); c.lineTo(-0.06, 0.28); c.lineTo(0.16, -0.06); c.lineTo(0, -0.06); c.closePath(); c.fill(); }
  else if (kind === 'brazier') {
    c.moveTo(0, -0.28); c.quadraticCurveTo(0.24, -0.02, 0.14, 0.16); c.quadraticCurveTo(0, 0.26, -0.14, 0.16); c.quadraticCurveTo(-0.24, -0.02, 0, -0.28); c.fill();
    c.fillStyle = '#ffd36b'; c.beginPath(); c.arc(0, 0.08, 0.08, 0, 7); c.fill();
  } else if (kind === 'mortar') { c.fillRect(-0.14, -0.18, 0.28, 0.36); c.fillStyle = '#2a3542'; c.beginPath(); c.ellipse(0, -0.18, 0.14, 0.06, 0, 0, 7); c.fill(); c.fillStyle = TOWER_COLOR[kind]; c.fillRect(-0.24, 0.14, 0.48, 0.08); }
  else if (kind === 'mint') { c.arc(0, 0, 0.22, 0, 7); c.fill(); c.fillStyle = '#8a6a10'; c.font = 'bold 0.3px sans-serif'; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText('$', 0, 0.02); }
  else if (kind === 'bladewheel') {   // a ring of blades
    const spin = t * 2;
    for (let i = 0; i < 6; i++) { const a = spin + i * Math.PI / 3; c.moveTo(Math.cos(a) * 0.08, Math.sin(a) * 0.08); c.lineTo(Math.cos(a + 0.35) * 0.28, Math.sin(a + 0.35) * 0.28); c.lineTo(Math.cos(a - 0.1) * 0.24, Math.sin(a - 0.1) * 0.24); c.closePath(); }
    c.fill(); c.fillStyle = '#2a3542'; c.beginPath(); c.arc(0, 0, 0.07, 0, 7); c.fill();
  } else if (kind === 'trapper') {   // a caltrop
    c.lineWidth = 0.07;
    for (let i = 0; i < 3; i++) { const a = -Math.PI / 2 + i * Math.PI * 2 / 3; c.moveTo(0, 0); c.lineTo(Math.cos(a) * 0.26, Math.sin(a) * 0.26); }
    c.stroke(); c.beginPath(); c.arc(0, 0, 0.08, 0, 7); c.fill();
  } else if (kind === 'workshop') {   // a cog
    for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4; c.rect(Math.cos(a) * 0.2 - 0.05, Math.sin(a) * 0.2 - 0.05, 0.1, 0.1); }
    c.fill(); c.beginPath(); c.arc(0, 0, 0.18, 0, 7); c.fill(); c.fillStyle = '#2a3542'; c.beginPath(); c.arc(0, 0, 0.07, 0, 7); c.fill();
  } else if (kind === 'arcanist') {   // a star
    for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + i * Math.PI / 5, r = i % 2 ? 0.11 : 0.27; c.lineTo(Math.cos(a) * r, Math.sin(a) * r); }
    c.closePath(); c.fill();
  } else if (kind === 'skyhook') {   // a harpoon pointing up
    c.moveTo(0, 0.26); c.lineTo(0, -0.2); c.stroke(); c.beginPath(); c.moveTo(0, -0.3); c.lineTo(0.12, -0.12); c.lineTo(-0.12, -0.12); c.closePath(); c.fill();
    c.beginPath(); c.arc(0, 0.12, 0.16, 0.2, Math.PI - 0.2); c.stroke();
  } else if (kind === 'alchemist') {   // a flask
    c.moveTo(-0.06, -0.28); c.lineTo(0.06, -0.28); c.lineTo(0.06, -0.08); c.lineTo(0.22, 0.2); c.lineTo(-0.22, 0.2); c.lineTo(-0.06, -0.08); c.closePath(); c.fill();
    c.fillStyle = '#2a3542'; c.beginPath(); c.arc(0.05, 0.08, 0.04, 0, 7); c.arc(-0.06, 0.13, 0.03, 0, 7); c.fill();
  } else { c.arc(0, 0, 0.2, 0, 7); c.stroke(); c.beginPath(); c.arc(0, 0, 0.07, 0, 7); c.fill(); }
  c.restore();
  if (evo) {   // a crown
    c.fillStyle = '#ffd75a';
    c.beginPath(); c.moveTo(-0.16, -0.4); c.lineTo(-0.16, -0.54); c.lineTo(-0.08, -0.46); c.lineTo(0, -0.58); c.lineTo(0.08, -0.46); c.lineTo(0.16, -0.54); c.lineTo(0.16, -0.4); c.closePath(); c.fill();
  } else if (tier > 0) {
    c.fillStyle = PATH_COLOR[path];
    for (let i = 0; i < tier; i++) { c.beginPath(); c.arc(-0.07 * (tier - 1) + i * 0.14, 0.34, 0.05, 0, 7); c.fill(); }
  }
  if (side > 0) {   // the side path's tiers, small, at the top
    c.fillStyle = PATH_COLOR[1 - path];
    for (let i = 0; i < side; i++) { c.beginPath(); c.arc(-0.05 * (side - 1) + i * 0.1, evo ? -0.62 : -0.33, 0.035, 0, 7); c.fill(); }
  }
}

// An enemy's body at (x, y), radius r; `flap` moves a Gargoyle's wings; an `icon` (the wave
// preview) leaves out the Mender's ring.
function drawEnemyBody(ctx, kind, x, y, r, color, flap, icon = false) {
  ctx.fillStyle = color;
  ctx.beginPath();
  if (kind === 'brute') ctx.roundRect(x - r, y - r, r * 2, r * 2, 0.1);
  else if (kind === 'ironclad') ctx.roundRect(x - r, y - r, r * 2, r * 2, 0.05);
  else if (kind === 'frostborn') { for (let i = 0; i < 6; i++) { const a = i * Math.PI / 3; ctx.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r); } ctx.closePath(); }
  else if (kind === 'juggernaut' || kind === 'colossus') ctx.ellipse(x, y, r * 1.25, r * 0.8, 0, 0, 7);
  else if (FLYING.has(kind)) {
    const f = kind === 'gargoyle' ? Math.sin(flap) * 0.08 : 0;
    ctx.moveTo(x, y - r); ctx.lineTo(x + r * 1.4, y + f); ctx.lineTo(x, y + r * 0.6); ctx.lineTo(x - r * 1.4, y + f);
  } else if (kind === 'ghost') { ctx.arc(x, y - r * 0.2, r, Math.PI, 0); ctx.lineTo(x + r, y + r); for (let i = 3; i >= 0; i--) ctx.lineTo(x - r + i * r * 2 / 3, y + r - (i % 2) * 0.1); }
  else if (kind === 'splitter') { ctx.arc(x - r * 0.4, y, r * 0.6, 0, 7); ctx.arc(x + r * 0.4, y, r * 0.6, 0, 7); ctx.arc(x, y - r * 0.4, r * 0.6, 0, 7); }
  else ctx.arc(x, y, r, 0, 7);
  ctx.fill();
  const lw = Math.max(0.04, r * 0.12);
  if (kind === 'healer') {   // a white cross, and the ring it mends within
    const a = ctx.globalAlpha;
    ctx.globalAlpha = 1;
    ctx.fillStyle = '#fff';
    ctx.fillRect(x - r * 0.15, y - r * 0.55, r * 0.3, r * 1.1);
    ctx.fillRect(x - r * 0.55, y - r * 0.15, r * 1.1, r * 0.3);
    if (!icon) { ctx.strokeStyle = 'rgba(92, 196, 106, 0.35)'; ctx.lineWidth = 0.03; ctx.beginPath(); ctx.arc(x, y, 1.5, 0, 7); ctx.stroke(); }
    ctx.globalAlpha = a;
  } else if (kind === 'ironclad') {   // rivets
    ctx.fillStyle = '#c7ccd2';
    for (const [dx, dy] of [[-0.6, -0.6], [0.6, -0.6], [-0.6, 0.6], [0.6, 0.6]]) { ctx.beginPath(); ctx.arc(x + dx * r, y + dy * r, r * 0.13, 0, 7); ctx.fill(); }
  } else if (kind === 'cinder') { ctx.strokeStyle = '#ff7a2f'; ctx.lineWidth = lw; ctx.stroke(); }
  else if (kind === 'frostborn') { ctx.strokeStyle = '#ffffff'; ctx.lineWidth = lw * 0.7; ctx.stroke(); }
  else if (kind === 'warded') { ctx.strokeStyle = '#e2d4ff'; ctx.lineWidth = lw * 0.7; ctx.beginPath(); ctx.arc(x, y, r * 0.65, 0, 7); ctx.stroke(); }
  else if (kind === 'juggernaut' || kind === 'colossus') {   // plates and a band
    ctx.strokeStyle = kind === 'colossus' ? '#f2c230' : '#a8c49c'; ctx.lineWidth = lw * 0.6;
    ctx.beginPath(); ctx.ellipse(x, y, r * 1.25, r * 0.8, 0, 0, 7); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(x - r * 0.4, y - r * 0.75); ctx.lineTo(x - r * 0.4, y + r * 0.75); ctx.moveTo(x + r * 0.4, y - r * 0.75); ctx.lineTo(x + r * 0.4, y + r * 0.75); ctx.stroke();
  } else if (kind === 'gravewarden') {   // a skull's eyes
    ctx.fillStyle = '#2a2220';
    ctx.beginPath(); ctx.arc(x - r * 0.35, y - r * 0.1, r * 0.2, 0, 7); ctx.arc(x + r * 0.35, y - r * 0.1, r * 0.2, 0, 7); ctx.fill();
    ctx.fillRect(x - r * 0.3, y + r * 0.35, r * 0.6, r * 0.12);
  } else if (kind === 'stormhulk') {   // a bolt
    ctx.fillStyle = '#ffe14d';
    ctx.beginPath(); ctx.moveTo(x + r * 0.1, y - r * 0.6); ctx.lineTo(x - r * 0.3, y + r * 0.05); ctx.lineTo(x, y + r * 0.05); ctx.lineTo(x - r * 0.15, y + r * 0.6); ctx.lineTo(x + r * 0.3, y - r * 0.1); ctx.lineTo(x, y - r * 0.1); ctx.closePath(); ctx.fill();
  } else if (kind === 'ironmaw') {   // a jaw of teeth
    ctx.fillStyle = '#e8e2d0';
    for (let i = 0; i < 5; i++) { const tx = x - r * 0.5 + i * r * 0.25; ctx.beginPath(); ctx.moveTo(tx, y + r * 0.1); ctx.lineTo(tx + r * 0.12, y + r * 0.4); ctx.lineTo(tx + r * 0.24, y + r * 0.1); ctx.fill(); }
    ctx.strokeStyle = '#2a2d33'; ctx.lineWidth = lw * 0.6; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.stroke();
  }
  if (kind === 'gargoyle') { ctx.strokeStyle = '#3a3d44'; ctx.lineWidth = 0.05; ctx.stroke(); }
  if (kind === 'shield' || kind === 'boss') { ctx.strokeStyle = kind === 'boss' ? '#f2c230' : '#cfe0ff'; ctx.lineWidth = 0.07; ctx.stroke(); }
}

// A projectile in flight, drawn by its style.
function drawShot(s, t) {
  const age = t - s.at;
  if (age > s.life + 0.05) return false;
  const u = Math.min(age, s.life), x = s.x0 + s.vx * u + 0.5, y = s.y0 + s.vy * u + 0.5;
  const sp = Math.hypot(s.vx, s.vy) || 1, dx = s.vx / sp, dy = s.vy / sp;
  const color = s.evolved ? '#ffd75a' : TOWER_COLOR[s.kind] || '#e8edf2';
  ctx.strokeStyle = ctx.fillStyle = color;
  switch (s.style) {
    case 'l': {   // lobbed: an arc, with its shadow on the ground
      const k = u / s.life, h = Math.sin(Math.PI * k) * 1.4;
      ctx.fillStyle = 'rgba(0,0,0,0.3)'; ctx.beginPath(); ctx.ellipse(x, y, 0.1, 0.05, 0, 0, 7); ctx.fill();
      ctx.fillStyle = s.fire ? '#ff6a2f' : '#3a3f47'; ctx.beginPath(); ctx.arc(x, y - h, 0.12, 0, 7); ctx.fill();
      break;
    }
    case 's': ctx.fillStyle = '#2b2f36'; ctx.beginPath(); ctx.arc(x, y, 0.1, 0, 7); ctx.fill(); ctx.strokeStyle = color; ctx.lineWidth = 0.03; ctx.stroke(); break;
    case 'w': {   // a spinning blade
      const a = t * 20;
      ctx.lineWidth = 0.05;
      ctx.beginPath(); ctx.moveTo(x + Math.cos(a) * 0.12, y + Math.sin(a) * 0.12); ctx.lineTo(x - Math.cos(a) * 0.12, y - Math.sin(a) * 0.12);
      ctx.moveTo(x + Math.cos(a + 1.57) * 0.12, y + Math.sin(a + 1.57) * 0.12); ctx.lineTo(x - Math.cos(a + 1.57) * 0.12, y - Math.sin(a + 1.57) * 0.12); ctx.stroke();
      break;
    }
    case 'o': ctx.fillStyle = s.fire ? '#ff8a3a' : color; ctx.globalAlpha = 0.35; ctx.beginPath(); ctx.arc(x, y, 0.2, 0, 7); ctx.fill(); ctx.globalAlpha = 1; ctx.beginPath(); ctx.arc(x, y, 0.1, 0, 7); ctx.fill(); break;
    case 'f': ctx.fillStyle = '#86d455'; ctx.beginPath(); ctx.arc(x, y, 0.09, 0, 7); ctx.fill(); break;
    default: {   // arrows, bolts, harpoons, sentry bolts: a streak along the way it flies
      const len = { b: 0.45, h: 0.5, c: 0.22 }[s.style] || 0.3;
      ctx.lineWidth = { b: 0.09, h: 0.07, c: 0.05 }[s.style] || 0.05;
      ctx.beginPath(); ctx.moveTo(x - dx * len, y - dy * len); ctx.lineTo(x, y); ctx.stroke();
    }
  }
  return true;
}

function frame() {
  requestAnimationFrame(frame);
  if (!S.st || S.st.phase === 'lobby' || !S.map || $('game').hidden) return;
  const { cols, rows, towers: T } = S.cfg;
  const w = Math.round(canvas.clientWidth * Math.min(devicePixelRatio || 1, 2));
  if (w && canvas.width !== w) { canvas.width = w; canvas.height = Math.round(w * rows / cols); }
  const k = canvas.width / cols, t = now();
  ctx.setTransform(k, 0, 0, k, 0, 0);

  // ground: grass, the road, rocks, the keep
  for (let x = 0; x < cols; x++) for (let y = 0; y < rows; y++) {
    const key = `${x},${y}`;
    const rubble = S.map.build && !S.map.road.has(key) && !S.map.build.has(key);
    ctx.fillStyle = S.map.road.has(key) ? '#c9b48a' : rubble ? ((x + y) % 2 ? '#6b665c' : '#716b60') : (x + y) % 2 ? '#4a7a3f' : '#4f8244';
    ctx.fillRect(x, y, 1.02, 1.02);
    if (rubble) {   // broken stone: nothing can be built here
      ctx.fillStyle = '#8a8478';
      for (const [dx, dy, rr] of [[0.25, 0.3, 0.12], [0.65, 0.55, 0.16], [0.35, 0.75, 0.09]]) {
        ctx.beginPath(); ctx.arc(x + dx, y + dy, rr, 0, 7); ctx.fill();
      }
    }
    if (S.map.rocks.has(key)) {
      ctx.fillStyle = '#7d8590';
      ctx.beginPath(); ctx.ellipse(x + 0.5, y + 0.58, 0.36, 0.28, 0, 0, 7); ctx.fill();
      ctx.fillStyle = '#9aa2ad';
      ctx.beginPath(); ctx.ellipse(x + 0.44, y + 0.5, 0.2, 0.14, 0, 0, 7); ctx.fill();
    }
  }
  for (const path of S.map.paths) {
    const [sx, sy] = path[0], [nx, ny] = path[1];   // an arrow where they come in
    const ax = Math.max(0, sx) + 0.5, ay = Math.max(0, sy) + 0.5, dx = Math.sign(nx - sx), dy = Math.sign(ny - sy);
    ctx.fillStyle = 'rgba(120,60,30,0.55)';
    ctx.beginPath();
    ctx.moveTo(ax + dx * 0.3, ay + dy * 0.3); ctx.lineTo(ax - dx * 0.2 - dy * 0.25, ay - dy * 0.2 - dx * 0.25); ctx.lineTo(ax - dx * 0.2 + dy * 0.25, ay - dy * 0.2 + dx * 0.25);
    ctx.fill();
  }
  const [kx, ky] = S.map.paths[0][S.map.paths[0].length - 1];
  ctx.fillStyle = '#6b7684';
  ctx.fillRect(kx + 0.1, ky + 0.25, 0.8, 0.65);
  for (const bx of [0.1, 0.4, 0.7]) ctx.fillRect(kx + bx, ky + 0.08, 0.2, 0.2);
  ctx.fillStyle = '#2a3542';
  ctx.fillRect(kx + 0.38, ky + 0.55, 0.24, 0.35);

  // piles on the road: tar under everything, spikes and mines
  for (const [, code, x, y] of S.traps) {
    const cx = x + 0.5, cy = y + 0.5;
    if (code === 2) {
      ctx.fillStyle = 'rgba(40, 28, 16, 0.55)';
      ctx.beginPath(); ctx.arc(cx, cy, S.cfg.items.tar.radius, 0, 7); ctx.fill();
    } else if (code === 1) {
      ctx.fillStyle = '#2b2f36'; ctx.beginPath(); ctx.arc(cx, cy, 0.13, 0, 7); ctx.fill();
      ctx.fillStyle = Math.sin(t * 6 + x * 3) > 0 ? '#ff4a3a' : '#7a2a22'; ctx.beginPath(); ctx.arc(cx, cy, 0.05, 0, 7); ctx.fill();
    } else {
      ctx.strokeStyle = '#5a5f66'; ctx.lineWidth = 0.035;
      ctx.beginPath();
      for (const [ox, oy] of [[-0.08, -0.04], [0.08, 0.02], [-0.01, 0.08]]) {
        for (let i = 0; i < 3; i++) { const a = i * 2.1 + ox * 20; ctx.moveTo(cx + ox, cy + oy); ctx.lineTo(cx + ox + Math.cos(a) * 0.07, cy + oy + Math.sin(a) * 0.07); }
      }
      ctx.stroke();
    }
  }

  // where a tower (or an item) would go, and how far it would reach
  const hover = S.hover, chosen = S.chosen != null ? tower(S.chosen) : null;
  const reach = (x, y, r, ok) => {
    ctx.fillStyle = ok ? 'rgba(255,255,255,0.12)' : 'rgba(255,80,60,0.15)';
    ctx.strokeStyle = ok ? 'rgba(255,255,255,0.6)' : 'rgba(255,80,60,0.7)';
    ctx.lineWidth = 0.04;
    ctx.beginPath(); ctx.arc(x + 0.5, y + 0.5, r, 0, 7); ctx.fill(); ctx.stroke();
  };
  if (S.picked && hover && S.st.phase === 'play') {
    const ok = free(...hover);
    reach(hover[0], hover[1], Math.min(T[S.picked].base.range, 12), ok);
    ctx.globalAlpha = 0.6;
    ctx.save(); ctx.translate(hover[0] + 0.5, hover[1] + 0.5); drawTower(ctx, S.picked, null, 0, ok ? '#fff' : '#ff5a4a'); ctx.restore();
    ctx.globalAlpha = 1;
  }
  if (S.item && hover && S.st.phase === 'play') {
    const it = S.cfg.items[S.item];
    reach(hover[0], hover[1], it.radius || it.splash || it.sentry?.range || 0.45, itemFits(S.item, ...hover));
  }
  if (chosen) reach(chosen.x, chosen.y, Math.min(towerStats(chosen).range, 12), true);
  if (S.preview) {   // the reach an upgrade being pointed at would give
    ctx.setLineDash([0.15, 0.1]);
    ctx.strokeStyle = '#ffd75a';
    ctx.lineWidth = 0.05;
    ctx.beginPath(); ctx.arc(S.preview.x + 0.5, S.preview.y + 0.5, S.preview.r, 0, 7); ctx.stroke();
    ctx.setLineDash([]);
  }

  for (const tw of S.st.towers) {
    ctx.save();
    ctx.translate(tw.x + 0.5, tw.y + 0.5);
    const side = tw.p == null ? 0 : tw.c[1 - tw.p];
    drawTower(ctx, tw.k, tw.p, tw.n, tw.id === S.chosen ? '#fff' : player(tw.o)?.color || '#8a8580', side);
    if (S.dazed[tw.id] > 0) {   // knocked out by a boss: dark, with sparks
      ctx.fillStyle = 'rgba(10, 15, 30, 0.55)'; ctx.beginPath(); ctx.roundRect(-0.45, -0.45, 0.9, 0.9, 0.14); ctx.fill();
      ctx.strokeStyle = '#9fd0ff'; ctx.lineWidth = 0.04; ctx.beginPath();
      const j = Math.sin(t * 30) * 0.08;
      ctx.moveTo(-0.25, -0.3 + j); ctx.lineTo(0, -0.05); ctx.lineTo(-0.1, 0.05); ctx.lineTo(0.25, 0.3 - j); ctx.stroke();
    }
    ctx.restore();
  }
  for (const [, x, y, pid] of S.sentries) {   // sentries: little turrets in their workshop's colour
    const owner = player(tower(pid)?.o);
    ctx.save();
    ctx.translate(x + 0.5, y + 0.5);
    ctx.fillStyle = '#2a3542'; ctx.strokeStyle = owner?.color || '#c9d3dd'; ctx.lineWidth = 0.04;
    ctx.beginPath(); ctx.arc(0, 0, 0.17, 0, 7); ctx.fill(); ctx.stroke();
    ctx.fillStyle = TOWER_COLOR.workshop; ctx.fillRect(-0.04, -0.2, 0.08, 0.16);
    ctx.restore();
  }

  // enemies, eased between snapshots; flyers last, so they pass over the rest
  const list = [...S.enemies.values()].sort((a, b) => FLYING.has(a.kind) - FLYING.has(b.kind));
  for (const e of list) {
    const u = Math.min(1, (t - e.at) / 0.1);
    e.x = e.fx + (e.tx - e.fx) * u;
    e.y = e.fy + (e.ty - e.fy) * u;
    const [color, r] = ENEMY[e.kind] || ['#ccc', 0.3], x = e.x + 0.5, y = e.y + 0.5 - (FLYING.has(e.kind) ? 0.25 : 0);
    if (FLYING.has(e.kind)) { ctx.fillStyle = 'rgba(0,0,0,0.25)'; ctx.beginPath(); ctx.ellipse(x, y + 0.4, r * 0.8, r * 0.4, 0, 0, 7); ctx.fill(); }
    if (e.charging) {   // charging: speed lines behind it
      ctx.strokeStyle = 'rgba(255,255,255,0.5)'; ctx.lineWidth = 0.04;
      const ang = Math.atan2(e.ty - e.fy, e.tx - e.fx);
      for (let i = -1; i <= 1; i++) { ctx.beginPath(); ctx.moveTo(x - Math.cos(ang) * r * 1.2 + i * 0.1, y - Math.sin(ang) * r * 1.2); ctx.lineTo(x - Math.cos(ang) * r * 2 + i * 0.1, y - Math.sin(ang) * r * 2); ctx.stroke(); }
    }
    if (e.camo) ctx.globalAlpha = 0.35 + 0.15 * Math.sin(t * 4 + e.tx);   // a Ghost: hard to make out
    drawEnemyBody(ctx, e.kind, x, y, r, color, t * 10 + e.tx);
    ctx.globalAlpha = 1;
    if (e.shell) { ctx.strokeStyle = '#d9b26a'; ctx.lineWidth = 0.09; ctx.beginPath(); ctx.arc(x, y, r + 0.1, 0, 7); ctx.stroke(); }
    if (e.shield) { ctx.fillStyle = `rgba(220, 235, 255, ${0.25 + 0.1 * Math.sin(t * 8)})`; ctx.beginPath(); ctx.arc(x, y, r + 0.18, 0, 7); ctx.fill(); }
    if (e.slow) { ctx.strokeStyle = '#9fe6ff'; ctx.lineWidth = 0.05; ctx.beginPath(); ctx.arc(x, y, r + 0.07, 0, 7); ctx.stroke(); }
    if (e.burning) {   // flickering flames
      ctx.fillStyle = `rgba(255, ${120 + 60 * Math.sin(t * 20 + e.tx * 9)}, 40, 0.75)`;
      for (let i = 0; i < 3; i++) { const a = t * 6 + i * 2.1; ctx.beginPath(); ctx.arc(x + Math.cos(a) * r * 0.7, y - r * 0.4 + Math.sin(a) * r * 0.3, r * 0.3, 0, 7); ctx.fill(); }
    }
    if (e.stunned) {   // stars overhead
      ctx.fillStyle = '#ffe14d';
      for (let i = 0; i < 3; i++) { const a = t * 5 + i * 2.1; ctx.beginPath(); ctx.arc(x + Math.cos(a) * r, y - r - 0.12 + Math.sin(a) * 0.05, 0.05, 0, 7); ctx.fill(); }
    }
    if (e.hp < 100) {
      const bw = Math.max(0.5, r * 2);
      ctx.fillStyle = 'rgba(0,0,0,0.55)';
      ctx.fillRect(x - bw / 2, y - r - 0.2, bw, 0.09);
      ctx.fillStyle = e.hp > 50 ? '#7dff9b' : e.hp > 25 ? '#f2c230' : '#ff6b5a';
      ctx.fillRect(x - bw / 2, y - r - 0.2, bw * e.hp / 100, 0.09);
    }
  }

  // projectiles in flight
  ctx.lineCap = 'round';
  for (const [id, s] of S.flying) if (!drawShot(s, t)) S.flying.delete(id);

  // instant shots (auras and lightning), each fading over a moment
  S.shots = S.shots.filter(s => t - s.at < 0.35);
  for (const s of S.shots) {
    const age = (t - s.at) / 0.35, fx = s.from[0] + 0.5, fy = s.from[1] + 0.5, big = s.evolved ? 1.6 : 1;
    ctx.globalAlpha = 1 - age;
    ctx.strokeStyle = ctx.fillStyle = s.evolved ? '#ffd75a' : TOWER_COLOR[s.kind];
    if (s.pts.length) {   // lightning
      ctx.lineWidth = 0.07 * big;
      ctx.beginPath(); ctx.moveTo(fx, fy);
      for (let i = 0; i < s.pts.length; i += 2) ctx.lineTo(s.pts[i] + 0.5 + Math.sin(i * 7 + s.at * 90) * 0.08, s.pts[i + 1] + 0.5 + Math.cos(i * 5 + s.at * 70) * 0.08);
      ctx.stroke();
    } else {   // a pulse from the tower
      ctx.lineWidth = 0.06 * big;
      if (s.st.burn || s.st.dtype === 'fire') { ctx.fillStyle = `rgba(255, 110, 30, ${0.25 * (1 - age)})`; ctx.beginPath(); ctx.arc(fx, fy, s.st.range * (0.3 + 0.7 * age), 0, 7); ctx.fill(); }
      ctx.beginPath(); ctx.arc(fx, fy, s.st.range * age, 0, 7); ctx.stroke();
    }
  }
  ctx.globalAlpha = 1;

  // blasts
  S.booms = S.booms.filter(b => t - b.at < 0.35);
  for (const b of S.booms) {
    const age = (t - b.at) / 0.35;
    const c = { fire: '255, 106, 47', acid: '134, 212, 85', blast: '255, 179, 71' }[b.look] || '255, 179, 71';
    ctx.fillStyle = `rgba(${c}, ${0.7 * (1 - age)})`;
    ctx.beginPath(); ctx.arc(b.x + 0.5, b.y + 0.5, b.r * (0.4 + 0.6 * age), 0, 7); ctx.fill();
  }

  // abilities, items and boss moves: a flash over the board and a burst on everything struck
  S.blasts = S.blasts.filter(bl => t - bl.at < 0.9);
  for (const bl of S.blasts) {
    const age = (t - bl.at) / 0.9, what = bl.do.startsWith('item:') ? bl.do.slice(5) : bl.do;
    const color = { strike: '255, 215, 90', stun: '200, 240, 255', flask: '200, 240, 255', slow: '120, 90, 40', burn: '255, 110, 30', gold: '255, 215, 90',
      bounty: '255, 215, 90', zap: '150, 200, 255', skull: '255, 60, 60', keg: '255, 179, 71', unmake: '200, 160, 255', horn: '255, 215, 90' }[what] || '255, 255, 255';
    if (what !== 'zap') { ctx.fillStyle = `rgba(${color}, ${(what === 'skull' ? 0.25 : 0.18) * (1 - age)})`; ctx.fillRect(0, 0, cols, rows); }
    ctx.fillStyle = `rgba(${color}, ${0.8 * (1 - age)})`;
    const rad = what === 'keg' ? S.cfg.items.keg.splash : 0.2 + age * 0.9;
    if (what !== 'zap') for (let i = 0; i < bl.pts.length; i += 2) { ctx.beginPath(); ctx.arc(bl.pts[i] + 0.5, bl.pts[i + 1] + 0.5, rad, 0, 7); ctx.fill(); }
    if (what === 'zap' && bl.from && bl.pts.length) {   // a bolt from the boss to the tower it knocks out
      ctx.strokeStyle = `rgba(${color}, ${1 - age})`; ctx.lineWidth = 0.08;
      ctx.beginPath(); ctx.moveTo(bl.pts[0] + 0.5, bl.pts[1] + 0.5);
      const [tx, ty] = bl.from;
      for (let i = 1; i <= 4; i++) ctx.lineTo(bl.pts[0] + (tx - bl.pts[0]) * i / 4 + 0.5 + (i < 4 ? Math.sin(i * 9 + bl.at * 50) * 0.25 : 0), bl.pts[1] + (ty - bl.pts[1]) * i / 4 + 0.5);
      ctx.stroke();
    }
    if (bl.from && (what === 'overdrive' || what === 'rally' || what === 'mark' || what === 'unmake')) {
      ctx.strokeStyle = `rgba(${color}, ${1 - age})`; ctx.lineWidth = 0.1;
      ctx.beginPath(); ctx.arc(bl.from[0] + 0.5, bl.from[1] + 0.5, 0.5 + age * 3, 0, 7); ctx.stroke();
    }
  }

  // damage numbers, drifting up
  if (numbers) {
    S.floats = S.floats.filter(f => t - f.at < 0.8);
    ctx.font = 'bold 0.32px sans-serif';
    ctx.textAlign = 'center';
    for (const f of S.floats) {
      const age = (t - f.at) / 0.8;
      ctx.globalAlpha = 1 - age;
      ctx.fillStyle = f.n >= 500 ? '#ffd75a' : '#fff';
      ctx.fillText(f.n >= 10000 ? `${Math.round(f.n / 1000)}k` : String(f.n), f.x, f.y + 0.2 - age * 0.6);
    }
    ctx.globalAlpha = 1;
  }
}

requestAnimationFrame(frame);
if (room.debug) window.holdfast = { S, room, renderComing };   // for the checks
