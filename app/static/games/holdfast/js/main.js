// Holdfast in the browser: the lobby, the board (drawn on a canvas from the server's snapshots), the
// tower bar and the side panels. The server (app/holdfast/game.py) runs the fight; this only draws
// it and asks to build, upgrade, sell and give.

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
  cfg: null,           // the rules: towers, enemies, board size (from `welcome`)
  st: null,
  map: null,           // { paths, rocks, road: Set of "x,y" }
  enemies: new Map(),  // id -> { kind, x, y (drawn), fx, fy (from), tx, ty (to), at, hp, slow }
  shots: [],           // { kind, pts, at, r }
  gold: {},
  nextIn: null,
  picked: null,        // the kind of tower about to be built
  chosen: null,        // the id of the tower whose panel is open
  hover: null,         // the tile under the pointer
  cd: {},              // tower id -> seconds until its ability is ready
  undoUntil: {},       // tower id -> now() its undo runs out (for this player)
  glow: [0, 0, 0],     // seconds left of Rally, Mark Them and Bounty Hunt
  blasts: [],          // abilities going off: { do, from, pts, at }
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

// A tower's numbers with `tiers` bought on `path` (the same sum as data.stats on the server).
function statsOf(kind, path = null, tiers = 0) {
  const def = S.cfg.towers[kind], out = { ...def.base };
  if (path != null) for (const t of def.paths[path].tiers.slice(0, tiers)) Object.assign(out, t.set);
  return out;
}
const EVOLUTION = 4;
// What to call a tower: its final evolution's name, or its kind.
const towerName = t => (t.n >= EVOLUTION ? S.cfg.towers[t.k].paths[t.p].tiers[EVOLUTION - 1].name : S.cfg.towers[t.k].name);
const myGold = () => S.gold[room.you] ?? me()?.gold ?? 0;

function receive(m) {
  if (m.t === 'welcome') {
    S.cfg = m;
    buildPalette();
    $('map').replaceChildren(...Object.entries(m.maps).map(([id, v]) => { const o = el('option', '', v.name); o.value = id; return o; }));
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
    S.shots = [];
    S.picked = S.chosen = null;
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
    const t = now(), seen = new Set();
    for (const [id, k, x, y, hp, flags, taken] of m.e) {
      seen.add(id);
      const e = S.enemies.get(id) || { x, y };
      S.enemies.set(id, Object.assign(e, { kind: S.cfg.kinds[k], fx: e.x, fy: e.y, tx: x, ty: y, at: t, hp,
        slow: flags & 1, burning: flags & 2, stunned: flags & 4, camo: flags & 8 }));
      if (numbers && taken >= 1) S.floats.push({ x: x + 0.5 + (Math.random() - 0.5) * 0.3, y, n: taken, at: t });
    }
    if (S.floats.length > 120) S.floats.splice(0, S.floats.length - 120);
    S.cd = m.a || {};
    S.glow = m.gl || [0, 0, 0];
    for (const [id, what, ...pts] of m.x || []) {
      const tw = tower(id);
      S.blasts.push({ do: what, from: tw ? [tw.x, tw.y] : null, pts, at: t });
      ability(what);
    }
    for (const id of S.enemies.keys()) if (!seen.has(id)) S.enemies.delete(id);
    const heard = new Set();
    for (const [id, ...pts] of m.f) {
      const tw = tower(id);
      if (!tw) continue;
      S.shots.push({ kind: tw.k, st: statsOf(tw.k, tw.p, tw.n), evolved: tw.n >= EVOLUTION, from: [tw.x, tw.y], pts, at: t });
      if (!heard.has(tw.k)) { heard.add(tw.k); hit(tw.k, tw.n >= EVOLUTION); }
    }
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
  }
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

// An ability going off.
function ability(what) {
  if (what === 'strike') { hiss(150, 0.8, 0.8, 0.16, 'lowpass'); tone(200, 40, 0.7, 'sawtooth', 0.07); }
  else if (what === 'stun') { tone(2000, 3000, 0.4, 'sine', 0.05); tone(1500, 2400, 0.5, 'sine', 0.04, 0.08); }
  else if (what === 'gold' || what === 'bounty') { for (let i = 0; i < 5; i++) tone(1000 + i * 180, 1400 + i * 180, 0.12, 'triangle', 0.04, i * 0.07); }
  else { tone(300, 900, 0.5, 'square', 0.04); hiss(800, 1, 0.5, 0.05); }
}

// A weapon's hit, at most once every 70 ms per weapon so a big defence doesn't roar. Final
// evolutions sound bigger.
function hit(kind, big = false) {
  const t = performance.now();
  if (muted || t - (lastHit[kind] || 0) < 70) return;
  lastHit[kind] = t;
  const v = big ? 1.6 : 1;
  switch (kind) {
    case 'archer': hiss(3200, 6, 0.06, 0.035 * v); tone(900, 500, 0.05, 'triangle', 0.02 * v); break;
    case 'cannon': hiss(180, 1, 0.3, 0.12 * v, 'lowpass'); tone(110, 40, 0.25, 'sine', 0.08 * v); break;
    case 'frost': tone(1800, 2400, 0.18, 'sine', 0.025 * v); tone(2700, 3600, 0.12, 'sine', 0.015 * v, 0.03); break;
    case 'ballista': tone(260, 90, 0.12, 'square', 0.04 * v); hiss(900, 3, 0.08, 0.05 * v); break;
    case 'tesla': tone(1400, 300, 0.12, 'sawtooth', 0.03 * v); hiss(5000, 2, 0.1, 0.03 * v, 'highpass'); break;
    case 'brazier': hiss(700, 0.6, 0.35, 0.05 * v); break;
    case 'mortar': hiss(120, 1, 0.45, 0.13 * v, 'lowpass'); tone(80, 30, 0.4, 'sine', 0.09 * v); break;
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
    $('map').disabled = $('diff').disabled = !host;
    $('map-blurb').textContent = S.cfg.maps[st.map].blurb;
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

// What the next wave brings: each kind drawn as on the board, how many, what's special about it,
// and a warning when nothing built can deal with it (nothing that sees Ghosts, or hits flyers).
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : word.endsWith('s') ? 'es' : 's'}`;
function traits(e) {
  return [e.camo && 'camouflaged', e.air && 'flies', e.armor && 'armoured', e.heal && 'heals others',
    e.split && `splits in ${e.split}`, (e.lives || 1) > 1 && `costs ${e.lives} lives`, e.summon && 'calls up Grunts'].filter(Boolean);
}
function renderComing() {
  const st = S.st, box = $('coming'), foes = S.cfg.enemies;
  const counts = new Map();
  for (const [k, n] of st.coming) counts.set(k, (counts.get(k) || 0) + n);
  const kinds = [...counts.keys()];
  const sight = st.towers.some(t => t.cs), antiAir = st.towers.some(t => statsOf(t.k, t.p, t.n).air);
  const warn = [];
  if (kinds.some(k => foes[k].camo) && !sight) warn.push('Nothing built can see Ghosts. Longbow (Archer), Heavy Bolts (Ballista), a Frost or Brazier, or a tower beside a Spyglass (Beacon) can.');
  if (kinds.some(k => foes[k].air) && !antiAir) warn.push('Nothing built can hit flyers. Archers, Frost, Ballistas and Teslas can.');
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
    drawEnemyBody(c, k, 0.7, 0.7, 0.25 + r * 0.6, color, 0, true);   // big ones a little bigger
    const text = el('span');
    text.append(el('b', '', plural(counts.get(k), foes[k].name)));
    const tr = traits(foes[k]);
    if (tr.length) text.append(el('small', '', tr.join(', ')));
    li.append(icon, text);
    if (foes[k].camo || foes[k].lives > 1 || foes[k].air) li.classList.add('special');
    list.append(li);
  }
  box.replaceChildren(head, list, ...warn.map(w => el('p', 'warn', w)));
}

// The parts that change with every snapshot: gold, the countdown, what can be afforded.
function renderLive() {
  const st = S.st;
  if (!st || st.phase === 'lobby') return;
  const gold = myGold(), seated = me()?.seated;
  $('wave-title').textContent = st.fighting ? `Wave ${st.wave}` : st.wave >= S.cfg.waves ? 'All waves beaten'
    : `Wave ${st.wave + 1} in ${Math.ceil(S.nextIn ?? 0)} s`;
  const chips = ['Rally', 'Mark Them', 'Bounty Hunt'].map((label, i) => S.glow[i] > 0 ? `${label} ${Math.ceil(S.glow[i])} s` : null).filter(Boolean);
  let box = $('chips');
  if (!box) { box = el('div', 'chips'); box.id = 'chips'; $('coming').after(box); }
  box.replaceChildren(...chips.map(c => el('span', 'chip', c)));
  if (S.chosen != null) {
    const a = $('info').querySelector('.ability-btn'), left = S.cd[S.chosen] ?? 0;
    if (a) { a.disabled = left > 0 || !st.fighting; a.textContent = a.dataset.label + (left > 0 ? ` (${Math.ceil(left)} s)` : st.fighting ? '' : ' (when a wave is on)'); }
    const u = $('info').querySelector('.undo-btn'), until = S.undoUntil[S.chosen];
    if (u && (!until || until < now())) u.remove();
    else if (u) u.textContent = `Undo (${Math.ceil(until - now())} s, full refund)`;
  }
  $('ready').hidden = st.fighting || !seated || st.phase !== 'play';
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
  for (const up of $('info').querySelectorAll('[data-cost]')) up.disabled = up.dataset.locked === '1' || gold < +up.dataset.cost;
}

const pct = v => `${Math.round(v * 100)}%`;
const STAT = [['dmg', 'Damage'], ['shots', 'Targets'], ['rate', 'Every', v => `${v} s`], ['range', 'Reach'],
  ['splash', 'Blast'], ['cluster', 'Extra blasts'], ['chain', 'Jumps to'], ['slow', 'Slows by', pct],
  ['stun', 'Stuns for', v => `${v} s`], ['burn', 'Burns', v => `${v} a second`], ['shred', 'Strips armour', v => `${v} a hit`],
  ['brittle', 'Slowed take', v => `${pct(v)} more`], ['boss', 'Against Warlords', v => `×${v}`],
  ['pierce', 'Ignores armour', () => 'yes'], ['air', 'Hits flyers', v => (v ? 'yes' : 'no')],
  ['boost', 'Speeds up', pct], ['reach', 'Extends reach', pct], ['power', 'Adds damage', pct],
  ['income', 'Pays a wave', v => `${v} gold`], ['bounty', 'Kill bonus', pct]];

function statList(stats) {
  const dl = el('dl');
  for (const [key, label, fmt = v => v] of STAT) {
    if (stats[key] == null || (key === 'air' && stats.mode === 'income') || (key === 'air' && stats.mode === 'support')) continue;
    dl.append(el('dt', '', label), el('dd', '', fmt(stats[key])));
  }
  return dl;
}

function renderInfo() {
  const box = $('info'), T = S.cfg.towers;
  const tw = S.chosen != null ? tower(S.chosen) : null;
  const kind = tw ? tw.k : S.picked;
  if (!kind) { box.replaceChildren(); return; }
  const def = T[kind];
  if (!tw) {
    box.replaceChildren(el('h2', '', `${def.name} (${def.cost} gold)`), el('p', '', def.blurb), statList(def.base),
      el('p', '', 'Click or tap a free square to build it.'));
    return;
  }
  const evolved = tw.n >= EVOLUTION;
  const title = el('h2', evolved ? 'evolved' : '', towerName(tw));
  const sub = tw.p == null ? 'Not upgraded yet' : `${def.paths[tw.p].name}, tier ${tw.n}${evolved ? ': final evolution' : ''}`;
  const tally = el('p', 'tally');
  tally.append('Kills: ', el('b', '', ''), ` · damage ${Number(tw.dmg || 0).toLocaleString()} · built by ${player(tw.o)?.name || 'someone who left'}`);
  tally.querySelector('b').id = 'kills';
  tally.querySelector('b').textContent = tw.kills;
  const parts = [title, el('p', '', sub), tally];
  const ab = abilityOf(tw);
  if (ab && me()?.seated) {
    const b = el('button', 'ability-btn', '');
    b.type = 'button';
    b.dataset.label = `${ab.name}: ${ab.blurb}`;
    b.textContent = b.dataset.label;
    b.disabled = (S.cd[tw.id] ?? 0) > 0 || !S.st.fighting;
    b.addEventListener('click', () => useAbility(tw.id));
    parts.push(b);
  }
  if (S.undoUntil[tw.id] > now()) {
    const u = el('button', 'undo-btn', 'Undo');
    u.type = 'button';
    u.addEventListener('click', () => { sound('sell'); room.send({ t: 'undo', id: tw.id }); });
    parts.push(u);
  }
  const st0 = statsOf(kind, tw.p, tw.n);
  if (!['support', 'income'].includes(st0.mode)) {
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

  // the two upgrade paths: the next tier on each, or why not
  const paths = el('div', 'paths');
  def.paths.forEach((path, pi) => {
    const col = el('section', `path${tw.p === pi ? ' taken' : ''}`);
    const pips = el('span', 'pips');
    for (let i = 1; i <= EVOLUTION; i++) pips.append(el('i', tw.p === pi && tw.n >= i ? 'on' : i === EVOLUTION ? 'evo' : ''));
    col.append(el('h3', '', path.name), pips);
    const mine = tw.p == null || tw.p === pi, n = mine ? tw.n : 0, next = path.tiers[n];
    if (!mine) col.append(el('p', 'note', `Closed: this tower took ${def.paths[tw.p].name}.`));
    else if (!next) col.append(el('p', 'note', 'Fully evolved.'));
    else {
      const evo = n + 1 === EVOLUTION;
      const taken = evo && S.st.towers.some(o => o.id !== tw.id && o.k === kind && o.p === pi && o.n >= EVOLUTION);
      col.append(el('p', 'next', `${evo ? 'Final evolution: ' : ''}${next.name}`), el('p', 'note', next.blurb.replace(/^Final evolution: /, '')));
      if (me()?.seated) {
        const up = el('button', evo ? 'primary evo' : 'primary', `${evo ? 'Evolve' : 'Buy'}: ${next.cost} gold`);
        up.type = 'button';
        up.dataset.cost = next.cost;
        up.dataset.path = pi;
        up.dataset.locked = taken ? '1' : '0';
        up.disabled = taken || myGold() < next.cost;
        up.addEventListener('click', () => { sound(evo ? 'evolve' : 'up'); room.send({ t: 'up', id: tw.id, path: pi }); });
        const r = statsOf(kind, pi, n + 1).range;
        up.addEventListener('pointerenter', () => { S.preview = { x: tw.x, y: tw.y, r: Math.min(r, 12) }; });
        up.addEventListener('pointerleave', () => { S.preview = null; });
        col.append(up);
        if (taken) col.append(el('p', 'note', `There's already a ${next.name}: only one at a time.`));
      }
    }
    paths.append(col);
  });
  parts.push(paths);
  if (tw.o === room.you) {
    const sell = el('button', '', `Sell for ${Math.round(tw.s * S.cfg.sell)}`);
    sell.type = 'button';
    sell.className = 'sell';
    sell.addEventListener('click', () => { sound('sell'); room.send({ t: 'sell', id: tw.id }); S.chosen = null; });
    parts.push(sell);
  }
  box.replaceChildren(...parts);
  S.preview = null;
}

function pick(kind) {
  S.picked = S.picked === kind ? null : kind;
  S.chosen = null;
  for (const b of $('palette').children) b.setAttribute('aria-pressed', String(b.dataset.kind === S.picked));
  renderInfo();
}

function buildPalette() {
  $('palette').replaceChildren(...Object.entries(S.cfg.towers).map(([kind, def], i) => {
    const b = el('button');
    b.type = 'button';
    b.dataset.kind = kind;
    b.setAttribute('aria-pressed', 'false');
    b.title = `${def.blurb} (key ${i + 1})`;
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

$('map').addEventListener('change', () => room.send({ t: 'set', map: $('map').value }));
$('diff').addEventListener('change', () => room.send({ t: 'set', diff: $('diff').value }));
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

// Keys: 1-9 pick a tower to build; with a tower chosen, Z and X buy on its paths, Q sets off its
// ability, T changes what it aims at, U undoes; Space sends the next wave; Esc puts things away.
addEventListener('keydown', e => {
  if ($('game').hidden || e.target.tagName === 'INPUT' || e.ctrlKey || e.metaKey || e.altKey) return;
  const kinds = Object.keys(S.cfg.towers), tw = S.chosen != null ? tower(S.chosen) : null, k = e.key.toLowerCase();
  if (e.key === 'Escape') { S.chosen = null; if (S.picked) pick(S.picked); else renderInfo(); }
  else if (kinds[+e.key - 1]) pick(kinds[+e.key - 1]);
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
const free = (x, y) => x >= 0 && y >= 0 && x < S.cfg.cols && y < S.cfg.rows
  && !S.map.road.has(`${x},${y}`) && !S.map.rocks.has(`${x},${y}`) && (!S.map.build || S.map.build.has(`${x},${y}`))
  && !towerAt(x, y);

canvas.addEventListener('pointermove', e => { S.hover = tileAt(e); });
canvas.addEventListener('pointerleave', () => { S.hover = null; });
canvas.addEventListener('click', e => {
  if (!S.map || S.st.phase !== 'play') return;
  const [x, y] = tileAt(e), there = towerAt(x, y);
  if (there) {
    if (S.picked) pick(S.picked);
    S.chosen = S.chosen === there.id ? null : there.id;
    renderInfo();
  } else if (S.picked && me()?.seated) {
    if (free(x, y) && myGold() >= S.cfg.towers[S.picked].cost) { sound('build'); room.send({ t: 'build', k: S.picked, x, y }); }
  } else {
    S.chosen = null;
    renderInfo();
  }
  if (e.pointerType === 'touch') S.hover = S.picked ? [x, y] : null;
});
canvas.addEventListener('contextmenu', e => { e.preventDefault(); if (S.picked) pick(S.picked); });

const TOWER_COLOR = { archer: '#7fb069', cannon: '#8a96a3', frost: '#7fd0e8', ballista: '#b08a5a', tesla: '#c9a0f0', beacon: '#f2c230',
  brazier: '#ff7a2f', mortar: '#a3a9b3', mint: '#f2d14a' };
const PATH_COLOR = ['#f2c230', '#6fd0ff'];
const ENEMY = {   // colour and radius, in tiles
  grunt: ['#d9534a', 0.27], runner: ['#f09a3e', 0.2], swarm: ['#b06fd6', 0.14], brute: ['#8f2d2d', 0.4],
  shield: ['#4f7fc9', 0.3], flyer: ['#f3f0e6', 0.24], boss: ['#3a2440', 0.55],
  ghost: ['#e8f0ff', 0.25], healer: ['#5cc46a', 0.28], splitter: ['#c78a3a', 0.3], gargoyle: ['#6b6f78', 0.3],
};
const FLYING = new Set(['flyer', 'gargoyle']);

// A tower, drawn in a 1 x 1 box centred on the origin: its tiers as pips in its path's colour, and
// a final evolution bigger, gold-rimmed and glowing.
function drawTower(c, kind, path, tier, ring) {
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
  else { c.arc(0, 0, 0.2, 0, 7); c.stroke(); c.beginPath(); c.arc(0, 0, 0.07, 0, 7); c.fill(); }
  c.restore();
  if (evo) {   // a crown
    c.fillStyle = '#ffd75a';
    c.beginPath(); c.moveTo(-0.16, -0.4); c.lineTo(-0.16, -0.54); c.lineTo(-0.08, -0.46); c.lineTo(0, -0.58); c.lineTo(0.08, -0.46); c.lineTo(0.16, -0.54); c.lineTo(0.16, -0.4); c.closePath(); c.fill();
  } else if (tier > 0) {
    c.fillStyle = PATH_COLOR[path];
    for (let i = 0; i < tier; i++) { c.beginPath(); c.arc(-0.07 * (tier - 1) + i * 0.14, 0.34, 0.05, 0, 7); c.fill(); }
  }
}

// An enemy's body at (x, y), radius r; `flap` moves a Gargoyle's wings; an `icon` (the wave
// preview) leaves out the Mender's ring.
function drawEnemyBody(ctx, kind, x, y, r, color, flap, icon = false) {
  ctx.fillStyle = color;
  ctx.beginPath();
  if (kind === 'brute') ctx.roundRect(x - r, y - r, r * 2, r * 2, 0.1);
  else if (FLYING.has(kind)) {
    const f = kind === 'gargoyle' ? Math.sin(flap) * 0.08 : 0;
    ctx.moveTo(x, y - r); ctx.lineTo(x + r * 1.4, y + f); ctx.lineTo(x, y + r * 0.6); ctx.lineTo(x - r * 1.4, y + f);
  } else if (kind === 'ghost') { ctx.arc(x, y - r * 0.2, r, Math.PI, 0); ctx.lineTo(x + r, y + r); for (let i = 3; i >= 0; i--) ctx.lineTo(x - r + i * r * 2 / 3, y + r - (i % 2) * 0.1); }
  else if (kind === 'splitter') { ctx.arc(x - r * 0.4, y, r * 0.6, 0, 7); ctx.arc(x + r * 0.4, y, r * 0.6, 0, 7); ctx.arc(x, y - r * 0.4, r * 0.6, 0, 7); }
  else ctx.arc(x, y, r, 0, 7);
  ctx.fill();
  if (kind === 'healer') {   // a white cross, and the ring it mends within
    const a = ctx.globalAlpha;
    ctx.globalAlpha = 1;
    ctx.fillStyle = '#fff';
    ctx.fillRect(x - r * 0.15, y - r * 0.55, r * 0.3, r * 1.1);
    ctx.fillRect(x - r * 0.55, y - r * 0.15, r * 1.1, r * 0.3);
    if (!icon) { ctx.strokeStyle = 'rgba(92, 196, 106, 0.35)'; ctx.lineWidth = 0.03; ctx.beginPath(); ctx.arc(x, y, 1.5, 0, 7); ctx.stroke(); }
    ctx.globalAlpha = a;
  }
  if (kind === 'gargoyle') { ctx.strokeStyle = '#3a3d44'; ctx.lineWidth = 0.05; ctx.stroke(); }
  if (kind === 'shield' || kind === 'boss') { ctx.strokeStyle = kind === 'boss' ? '#f2c230' : '#cfe0ff'; ctx.lineWidth = 0.07; ctx.stroke(); }
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

  // where a tower would go, and how far it would reach
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
  if (chosen) reach(chosen.x, chosen.y, Math.min(statsOf(chosen.k, chosen.p, chosen.n).range, 12), true);
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
    drawTower(ctx, tw.k, tw.p, tw.n, tw.id === S.chosen ? '#fff' : player(tw.o)?.color || '#8a8580');
    ctx.restore();
  }

  // enemies, eased between snapshots; flyers last, so they pass over the rest
  const list = [...S.enemies.values()].sort((a, b) => FLYING.has(a.kind) - FLYING.has(b.kind));
  for (const e of list) {
    const u = Math.min(1, (t - e.at) / 0.1);
    e.x = e.fx + (e.tx - e.fx) * u;
    e.y = e.fy + (e.ty - e.fy) * u;
    const [color, r] = ENEMY[e.kind], x = e.x + 0.5, y = e.y + 0.5 - (FLYING.has(e.kind) ? 0.25 : 0);
    if (FLYING.has(e.kind)) { ctx.fillStyle = 'rgba(0,0,0,0.25)'; ctx.beginPath(); ctx.ellipse(x, y + 0.4, r * 0.8, r * 0.4, 0, 0, 7); ctx.fill(); }
    if (e.camo) ctx.globalAlpha = 0.35 + 0.15 * Math.sin(t * 4 + e.tx);   // a Ghost: hard to make out
    drawEnemyBody(ctx, e.kind, x, y, r, color, t * 10 + e.tx);
    ctx.globalAlpha = 1;
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

  // shots, each fading over a moment
  S.shots = S.shots.filter(s => t - s.at < 0.35);
  ctx.lineCap = 'round';
  for (const s of S.shots) {
    const age = (t - s.at) / 0.35, fx = s.from[0] + 0.5, fy = s.from[1] + 0.5, big = s.evolved ? 1.6 : 1;
    ctx.globalAlpha = 1 - age;
    ctx.strokeStyle = ctx.fillStyle = s.evolved ? '#ffd75a' : TOWER_COLOR[s.kind];
    if (s.st.mode === 'aura') {   // a pulse from the tower
      ctx.lineWidth = 0.06 * big;
      if (s.kind === 'brazier') { ctx.fillStyle = `rgba(255, 110, 30, ${0.25 * (1 - age)})`; ctx.beginPath(); ctx.arc(fx, fy, s.st.range * (0.3 + 0.7 * age), 0, 7); ctx.fill(); }
      ctx.beginPath(); ctx.arc(fx, fy, s.st.range * age, 0, 7); ctx.stroke();
    } else if (s.st.mode === 'chain') {
      ctx.lineWidth = 0.07 * big;
      ctx.beginPath(); ctx.moveTo(fx, fy);
      for (let i = 0; i < s.pts.length; i += 2) ctx.lineTo(s.pts[i] + 0.5 + Math.sin(i * 7 + s.at * 90) * 0.08, s.pts[i + 1] + 0.5 + Math.cos(i * 5 + s.at * 70) * 0.08);
      ctx.stroke();
    } else if (s.st.mode === 'splash') {   // the shell's flight, then a blast at each point
      const tx = s.pts[0] + 0.5, ty = s.pts[1] + 0.5;
      ctx.lineWidth = 0.05;
      ctx.beginPath(); ctx.moveTo(fx, fy);
      if (s.kind === 'mortar') ctx.quadraticCurveTo((fx + tx) / 2, Math.min(fy, ty) - 2, tx, ty); else ctx.lineTo(tx, ty);
      ctx.stroke();
      for (let i = 0; i < s.pts.length; i += 2) {
        ctx.fillStyle = i ? 'rgba(255, 179, 71, 0.7)' : s.st.burn ? '#ff6a2f' : '#ffb347';
        ctx.beginPath(); ctx.arc(s.pts[i] + 0.5, s.pts[i + 1] + 0.5, s.st.splash * (i ? 0.6 : 1) * (0.4 + 0.6 * age), 0, 7); ctx.fill();
      }
    } else {
      const tx = s.pts[0] + 0.5, ty = s.pts[1] + 0.5;
      ctx.lineWidth = (s.kind === 'ballista' ? 0.1 : 0.05) * big;
      ctx.beginPath(); ctx.moveTo(fx, fy); ctx.lineTo(tx, ty); ctx.stroke();
    }
  }
  ctx.globalAlpha = 1;

  // abilities: a flash over the board and a burst on everything struck
  S.blasts = S.blasts.filter(bl => t - bl.at < 0.9);
  for (const bl of S.blasts) {
    const age = (t - bl.at) / 0.9;
    const color = { strike: '255, 215, 90', stun: '200, 240, 255', slow: '120, 90, 40', burn: '255, 110, 30', gold: '255, 215, 90', bounty: '255, 215, 90' }[bl.do] || '255, 255, 255';
    ctx.fillStyle = `rgba(${color}, ${0.18 * (1 - age)})`;
    ctx.fillRect(0, 0, cols, rows);
    ctx.fillStyle = `rgba(${color}, ${0.8 * (1 - age)})`;
    for (let i = 0; i < bl.pts.length; i += 2) { ctx.beginPath(); ctx.arc(bl.pts[i] + 0.5, bl.pts[i + 1] + 0.5, 0.2 + age * 0.9, 0, 7); ctx.fill(); }
    if (bl.from && (bl.do === 'overdrive' || bl.do === 'rally' || bl.do === 'mark')) {
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
