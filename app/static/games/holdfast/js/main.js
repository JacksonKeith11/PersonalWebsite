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
};

const room = startRoom({ key: 'holdfast', path: '/games/holdfast', title: 'Holdfast', show, onMessage: receive });
const player = id => S.st?.players.find(p => p.id === id);
const me = () => player(room.you);
const tower = id => S.st?.towers?.find(t => t[0] === id);
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
    S.map = { ...m, road, rocks: new Set(m.rocks.map(([x, y]) => `${x},${y}`)) };
    S.enemies.clear();
    S.shots = [];
    S.picked = S.chosen = null;
  } else if (m.t === 'state') {
    const was = S.st;
    S.st = m;
    for (const p of m.players) S.gold[p.id] = p.gold;
    if (was && m.phase === 'play') {
      if (m.fighting && !was.fighting) sound('wave');
      if (m.lives < was.lives) sound('leak');
    }
    if (was && was.phase === 'play' && m.phase !== 'play' && m.phase !== 'lobby') sound(m.phase === 'won' ? 'win' : 'lose');
    render();
  } else if (m.t === 's') {
    const t = now(), seen = new Set();
    for (const [id, k, x, y, hp, slow] of m.e) {
      seen.add(id);
      const e = S.enemies.get(id) || { x, y };
      S.enemies.set(id, Object.assign(e, { kind: S.cfg.kinds[k], fx: e.x, fy: e.y, tx: x, ty: y, at: t, hp, slow }));
    }
    for (const id of S.enemies.keys()) if (!seen.has(id)) S.enemies.delete(id);
    for (const [id, ...pts] of m.f) {
      const tw = tower(id);
      if (tw) S.shots.push({ kind: tw[1], level: tw[2], from: [tw[3], tw[4]], pts, at: t });
    }
    S.gold = m.g;
    S.nextIn = m.n;
    renderLive();
  }
}

// ---------------------------------------------------------------- sounds

let audio = null;
function sound(kind) {
  try {
    audio ||= new AudioContext();
    const [f0, f1, secs, type] = { build: [420, 640, 0.09, 'triangle'], up: [520, 1040, 0.16, 'triangle'], sell: [500, 250, 0.12, 'triangle'],
      wave: [196, 294, 0.5, 'sawtooth'], leak: [140, 60, 0.35, 'square'], win: [523, 1047, 0.8, 'triangle'], lose: [220, 55, 0.9, 'sawtooth'] }[kind];
    const o = audio.createOscillator(), g = audio.createGain(), t = audio.currentTime;
    o.type = type;
    o.frequency.setValueAtTime(f0, t);
    o.frequency.exponentialRampToValueAtTime(f1, t + secs);
    g.gain.setValueAtTime(0.05, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + secs);
    o.connect(g).connect(audio.destination);
    o.start(t);
    o.stop(t + secs);
  } catch { /* no sound, then */ }
}

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
    return;
  }
  show('game');
  $('game-code').textContent = room.code;
  $('hud-wave').textContent = `Wave ${Math.max(1, st.wave)} of ${S.cfg.waves}`;
  $('hud-lives').textContent = `♥ ${st.lives}`;
  $('hud-lives').classList.toggle('low', st.lives <= 5);
  $('speed').textContent = `Speed ×${st.speed}`;
  if (S.chosen != null && !tower(S.chosen)) S.chosen = null;
  renderLive();
  renderInfo();

  const over = st.phase !== 'play';
  $('end').hidden = !over;
  if (over) {
    $('end-kicker').textContent = st.phase === 'won' ? 'Victory' : `Fell on wave ${st.wave}`;
    $('end-title').textContent = st.phase === 'won' ? 'The keep holds!' : 'The keep has fallen';
    $('end-rows').replaceChildren(...st.players.filter(p => p.seated).map(p => {
      const tr = el('tr'), name = el('td', '', p.name), dot = el('span', 'dot');
      dot.style.setProperty('--c', p.color);
      name.prepend(dot);
      tr.append(name, el('td', '', p.kills), el('td', '', p.dmg.toLocaleString()), el('td', '', p.spent.toLocaleString()));
      return tr;
    }));
  }
}

// The parts that change with every snapshot: gold, the countdown, what can be afforded.
function renderLive() {
  const st = S.st;
  if (!st || st.phase === 'lobby') return;
  const names = S.cfg.enemies, gold = myGold(), seated = me()?.seated;
  $('wave-title').textContent = st.fighting ? `Wave ${st.wave}` : st.wave >= S.cfg.waves ? 'All waves beaten'
    : `Wave ${st.wave + 1} in ${Math.ceil(S.nextIn ?? 0)} s`;
  $('coming').textContent = st.fighting ? 'Hold them off.'
    : st.coming.map(([k, n]) => `${n} ${names[k].name}${n > 1 ? 's' : ''}`).join(', ');
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
  for (const b of $('palette').children) b.classList.toggle('poor', gold < S.cfg.towers[b.dataset.kind].cost[0]);
  const up = $('info').querySelector('[data-cost]');
  if (up) up.disabled = gold < +up.dataset.cost;
}

const STAT = [['dmg', 'Damage'], ['rate', 'Every', v => `${v} s`], ['range', 'Reach'], ['splash', 'Blast'],
  ['slow', 'Slows by', v => `${Math.round(v * 100)}%`], ['chain', 'Jumps to'], ['boost', 'Speeds up', v => `${Math.round(v * 100)}%`]];

function renderInfo() {
  const box = $('info'), T = S.cfg.towers;
  const tw = S.chosen != null ? tower(S.chosen) : null;
  const kind = tw ? tw[1] : S.picked;
  if (!kind) { box.replaceChildren(); return; }
  const def = T[kind], level = tw ? tw[2] : 0, stats = def.levels[level], next = tw && def.levels[level + 1];
  const dl = el('dl');
  for (const [key, label, fmt = v => v] of STAT) {
    if (stats[key] == null) continue;
    dl.append(el('dt', '', label), el('dd', '', fmt(stats[key]) + (next && next[key] !== stats[key] ? ` → ${fmt(next[key])}` : '')));
  }
  const parts = [el('h2', '', tw ? `${def.name}, level ${level + 1}` : `${def.name} (${def.cost[0]} gold)`), el('p', '', def.blurb), dl];
  if (tw) {
    parts.splice(1, 0, el('p', '', `Built by ${player(tw[5])?.name || 'someone who left'}.`));
    const row = el('div', 'row');
    if (next && me()?.seated) {
      const up = el('button', 'primary', `Upgrade: ${def.cost[level + 1]} gold`);
      up.type = 'button';
      up.dataset.cost = def.cost[level + 1];
      up.disabled = myGold() < def.cost[level + 1];
      up.addEventListener('click', () => { sound('up'); room.send({ t: 'up', id: tw[0] }); });
      row.append(up);
    }
    if (tw[5] === room.you) {
      const sell = el('button', '', `Sell for ${Math.round(tw[6] * S.cfg.sell)}`);
      sell.type = 'button';
      sell.addEventListener('click', () => { sound('sell'); room.send({ t: 'sell', id: tw[0] }); S.chosen = null; });
      row.append(sell);
    }
    parts.push(row);
  } else {
    parts.push(el('p', '', 'Click or tap a free square to build it.'));
  }
  box.replaceChildren(...parts);
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
    drawTower(c, kind, 0, '#c9d3dd');
    b.append(icon, el('span', '', def.name), el('span', 'cost', def.cost[0]));
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
addEventListener('keydown', e => {
  if ($('game').hidden || e.target.tagName === 'INPUT') return;
  const kinds = Object.keys(S.cfg.towers);
  if (e.key === 'Escape') { S.chosen = null; if (S.picked) pick(S.picked); else renderInfo(); }
  else if (kinds[+e.key - 1]) pick(kinds[+e.key - 1]);
});

// ---------------------------------------------------------------- the board

const canvas = $('board'), ctx = canvas.getContext('2d');
const tileAt = e => {
  const r = canvas.getBoundingClientRect();
  return [Math.floor((e.clientX - r.left) / r.width * S.cfg.cols), Math.floor((e.clientY - r.top) / r.height * S.cfg.rows)];
};
const towerAt = (x, y) => S.st.towers.find(t => t[3] === x && t[4] === y);
const free = (x, y) => x >= 0 && y >= 0 && x < S.cfg.cols && y < S.cfg.rows
  && !S.map.road.has(`${x},${y}`) && !S.map.rocks.has(`${x},${y}`) && !towerAt(x, y);

canvas.addEventListener('pointermove', e => { S.hover = tileAt(e); });
canvas.addEventListener('pointerleave', () => { S.hover = null; });
canvas.addEventListener('click', e => {
  if (!S.map || S.st.phase !== 'play') return;
  const [x, y] = tileAt(e), there = towerAt(x, y);
  if (there) {
    if (S.picked) pick(S.picked);
    S.chosen = S.chosen === there[0] ? null : there[0];
    renderInfo();
  } else if (S.picked && me()?.seated) {
    if (free(x, y) && myGold() >= S.cfg.towers[S.picked].cost[0]) { sound('build'); room.send({ t: 'build', k: S.picked, x, y }); }
  } else {
    S.chosen = null;
    renderInfo();
  }
  if (e.pointerType === 'touch') S.hover = S.picked ? [x, y] : null;
});
canvas.addEventListener('contextmenu', e => { e.preventDefault(); if (S.picked) pick(S.picked); });

const TOWER_COLOR = { archer: '#7fb069', cannon: '#5a6672', frost: '#7fd0e8', ballista: '#b08a5a', tesla: '#c9a0f0', beacon: '#f2c230' };
const ENEMY = {   // colour and radius, in tiles
  grunt: ['#d9534a', 0.27], runner: ['#f09a3e', 0.2], swarm: ['#b06fd6', 0.14], brute: ['#8f2d2d', 0.4],
  shield: ['#4f7fc9', 0.3], flyer: ['#f3f0e6', 0.24], boss: ['#3a2440', 0.55],
};

// A tower, drawn in a 1 x 1 box centred on the origin.
function drawTower(c, kind, level, ring) {
  c.fillStyle = '#2a3542';
  c.strokeStyle = ring;
  c.lineWidth = 0.07;
  c.beginPath();
  c.roundRect(-0.4, -0.4, 0.8, 0.8, 0.14);
  c.fill();
  c.stroke();
  c.fillStyle = c.strokeStyle = TOWER_COLOR[kind];
  c.lineWidth = 0.09;
  c.lineCap = 'round';
  c.beginPath();
  if (kind === 'archer') { c.moveTo(0, -0.26); c.lineTo(0.22, 0.2); c.lineTo(-0.22, 0.2); c.closePath(); c.fill(); }
  else if (kind === 'cannon') { c.arc(0, 0.04, 0.2, 0, 7); c.fill(); c.fillRect(-0.08, -0.3, 0.16, 0.3); }
  else if (kind === 'frost') { for (let i = 0; i < 3; i++) { const a = i * Math.PI / 3; c.moveTo(-Math.cos(a) * 0.26, -Math.sin(a) * 0.26); c.lineTo(Math.cos(a) * 0.26, Math.sin(a) * 0.26); } c.stroke(); }
  else if (kind === 'ballista') { c.moveTo(0, 0.26); c.lineTo(0, -0.28); c.moveTo(-0.24, -0.02); c.quadraticCurveTo(0, -0.3, 0.24, -0.02); c.stroke(); }
  else if (kind === 'tesla') { c.moveTo(0.06, -0.28); c.lineTo(-0.14, 0.04); c.lineTo(0.02, 0.04); c.lineTo(-0.06, 0.28); c.lineTo(0.16, -0.06); c.lineTo(0, -0.06); c.closePath(); c.fill(); }
  else { c.arc(0, 0, 0.2, 0, 7); c.stroke(); c.beginPath(); c.arc(0, 0, 0.07, 0, 7); c.fill(); }
  c.fillStyle = '#fff';
  for (let i = 0; i < level; i++) { c.beginPath(); c.arc(-0.06 * (level - 1) + i * 0.12, 0.33, 0.04, 0, 7); c.fill(); }
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
    ctx.fillStyle = S.map.road.has(key) ? '#c9b48a' : (x + y) % 2 ? '#4a7a3f' : '#4f8244';
    ctx.fillRect(x, y, 1.02, 1.02);
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
    reach(hover[0], hover[1], T[S.picked].levels[0].range, ok);
    ctx.globalAlpha = 0.6;
    ctx.save(); ctx.translate(hover[0] + 0.5, hover[1] + 0.5); drawTower(ctx, S.picked, 0, ok ? '#fff' : '#ff5a4a'); ctx.restore();
    ctx.globalAlpha = 1;
  }
  if (chosen) reach(chosen[3], chosen[4], T[chosen[1]].levels[chosen[2]].range, true);

  for (const [id, kind, level, x, y, owner] of S.st.towers) {
    ctx.save();
    ctx.translate(x + 0.5, y + 0.5);
    drawTower(ctx, kind, level, id === S.chosen ? '#fff' : player(owner)?.color || '#8a8580');
    ctx.restore();
  }

  // enemies, eased between snapshots; flyers last, so they pass over the rest
  const list = [...S.enemies.values()].sort((a, b) => (a.kind === 'flyer') - (b.kind === 'flyer'));
  for (const e of list) {
    const u = Math.min(1, (t - e.at) / 0.1);
    e.x = e.fx + (e.tx - e.fx) * u;
    e.y = e.fy + (e.ty - e.fy) * u;
    const [color, r] = ENEMY[e.kind], x = e.x + 0.5, y = e.y + 0.5 - (e.kind === 'flyer' ? 0.25 : 0);
    if (e.kind === 'flyer') { ctx.fillStyle = 'rgba(0,0,0,0.25)'; ctx.beginPath(); ctx.ellipse(x, y + 0.4, r * 0.8, r * 0.4, 0, 0, 7); ctx.fill(); }
    ctx.fillStyle = color;
    ctx.beginPath();
    if (e.kind === 'brute') ctx.roundRect(x - r, y - r, r * 2, r * 2, 0.1);
    else if (e.kind === 'flyer') { ctx.moveTo(x, y - r); ctx.lineTo(x + r * 1.4, y); ctx.lineTo(x, y + r * 0.6); ctx.lineTo(x - r * 1.4, y); }
    else ctx.arc(x, y, r, 0, 7);
    ctx.fill();
    if (e.kind === 'shield' || e.kind === 'boss') { ctx.strokeStyle = e.kind === 'boss' ? '#f2c230' : '#cfe0ff'; ctx.lineWidth = 0.07; ctx.stroke(); }
    if (e.slow) { ctx.strokeStyle = '#9fe6ff'; ctx.lineWidth = 0.05; ctx.beginPath(); ctx.arc(x, y, r + 0.07, 0, 7); ctx.stroke(); }
    if (e.hp < 100) {
      const bw = Math.max(0.5, r * 2);
      ctx.fillStyle = 'rgba(0,0,0,0.55)';
      ctx.fillRect(x - bw / 2, y - r - 0.2, bw, 0.09);
      ctx.fillStyle = e.hp > 50 ? '#7dff9b' : e.hp > 25 ? '#f2c230' : '#ff6b5a';
      ctx.fillRect(x - bw / 2, y - r - 0.2, bw * e.hp / 100, 0.09);
    }
  }

  // shots, each fading over a moment
  S.shots = S.shots.filter(s => t - s.at < 0.3);
  ctx.lineCap = 'round';
  for (const s of S.shots) {
    const age = (t - s.at) / 0.3, fx = s.from[0] + 0.5, fy = s.from[1] + 0.5;
    ctx.globalAlpha = 1 - age;
    ctx.strokeStyle = ctx.fillStyle = TOWER_COLOR[s.kind];
    if (s.kind === 'frost') {
      ctx.lineWidth = 0.06;
      ctx.beginPath(); ctx.arc(fx, fy, T.frost.levels[s.level].range * age, 0, 7); ctx.stroke();
    } else if (s.kind === 'tesla') {
      ctx.lineWidth = 0.07;
      ctx.beginPath(); ctx.moveTo(fx, fy);
      for (let i = 0; i < s.pts.length; i += 2) ctx.lineTo(s.pts[i] + 0.5 + Math.sin(i * 7 + s.at * 90) * 0.08, s.pts[i + 1] + 0.5 + Math.cos(i * 5 + s.at * 70) * 0.08);
      ctx.stroke();
    } else {
      const tx = s.pts[0] + 0.5, ty = s.pts[1] + 0.5;
      ctx.lineWidth = s.kind === 'ballista' ? 0.1 : 0.05;
      ctx.beginPath(); ctx.moveTo(fx, fy); ctx.lineTo(tx, ty); ctx.stroke();
      if (s.kind === 'cannon') {
        ctx.fillStyle = '#ffb347';
        ctx.beginPath(); ctx.arc(tx, ty, T.cannon.levels[s.level].splash * (0.4 + 0.6 * age), 0, 7); ctx.fill();
      }
    }
  }
  ctx.globalAlpha = 1;
}

requestAnimationFrame(frame);
if (room.debug) window.holdfast = { S, room };
