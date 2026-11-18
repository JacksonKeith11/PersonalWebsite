// Scramble in the browser: the lobby, this player's own physics and controls, everyone else as the
// server reports them, items, and the drawing. The server (app/scramble/game.py) makes the course, runs
// the bots and keeps the clock and the scores.

import { CRUMBLE, CRUMBLE_H, DT, PH, PW, SPIKE_H, posX, posY, prepare, spawn, standing, step } from './physics.js?v=2';
import { person, startRoom } from '../../shared/lobby.js?v=1';

const $ = id => document.getElementById(id);
const show = screen => { for (const id of ['menu', 'lobby', 'game']) $(id).hidden = id !== screen; };

const S = {
  st: null,
  course: null,
  me: null,            // this browser's player (physics.js), while racing
  others: new Map(),   // id -> where the server last said they were, and where we draw them
  offset: null,        // race time minus this browser's clock
  downAt: 0,           // when this player was knocked out, to respawn a moment later
  cam: { x: 0, y: -448 },
  grabbed: new Set(),  // boxes this player has asked for an item from
  frozenUntil: 0,      // race times this player's freeze and boost wear off
  boostUntil: 0,
  effects: [],         // items going off, to draw for a moment: { k, by, to, blocked, at }
  note: null,          // a line under the HUD: { text, until }
  itemsSeen: 0,        // how many items have gone off this round (the smoke test counts them)
};

const KNOCKOUT = 1.2;   // seconds before a knocked-out racer is back at their flag (game.py too)
const FREEZE = 2.5, FREEZE_SPEED = 0.5, BOOST = 2.0, BOOST_SPEED = 1.5;
const ITEMS = {
  bolt: { icon: '⚡', name: 'Bolt', tip: 'zaps the racer just ahead', did: 'zapped', color: '#ffe14d' },
  freeze: { icon: '❄', name: 'Freeze', tip: 'slows everyone ahead', did: 'froze', color: '#9fe6ff' },
  trap: { icon: '▲', name: 'Spike trap', tip: 'drops spikes where you stand', did: 'trapped', color: '#e8452f' },
  swap: { icon: '⇄', name: 'Swap', tip: 'trade places with the racer ahead', did: 'swapped places with', color: '#c58cff' },
  shield: { icon: '◯', name: 'Shield', tip: 'blocks the next item used on you', did: 'shielded', color: '#7fd0ff' },
  boost: { icon: '»', name: 'Boost', tip: 'run faster for a moment', did: 'boosted', color: '#ffb347' },
};

const room = startRoom({ key: 'scramble', path: '/games/scramble', title: 'Scramble', show, onMessage: receive });
const local = () => performance.now() / 1000;
const raceTime = () => (S.offset == null ? -9 : local() + S.offset);
const player = id => S.st?.players.find(p => p.id === id);
const mine = () => player(room.you);
const racing = () => S.st?.phase === 'race' && S.course && mine()?.racing && mine().fin == null;

function receive(m) {
  if (m.t === 'state') {
    const had = mine()?.item;
    S.st = m;
    if (S.course) S.course.traps = (m.traps || []).map(([id, x, y, w, owner]) => ({ id, x, y, w, owner }));
    if (mine()?.item && mine().item !== had) sound('item');
    render();
  } else if (m.t === 'course') {
    S.course = prepare(m.course);
    S.offset = m.now - local();
    S.me = Object.assign(spawn(S.course), { id: room.you });
    S.others.clear();
    S.grabbed.clear();
    S.effects = [];
    S.itemsSeen = 0;
    S.note = null;
    S.frozenUntil = S.boostUntil = 0;
    S.cam.x = 0;
  } else if (m.t === 'fx') {
    itemUsed(m);
  } else if (m.t === 'pos') {
    // the clock: the message that took the least time to get here is nearest the truth
    const est = m.now - local();
    S.offset = S.offset == null || Math.abs(est - S.offset) > 0.5 ? est : Math.max(est, S.offset - 0.0005);
    for (const [id, x, y, face, air, dead, marks] of m.ps) {
      const o = S.others.get(id) || { x, y };
      S.others.set(id, Object.assign(o, { tx: x, ty: y, face, air, dead, marks }));
    }
  }
}

// Someone used an item. If it hit this player, this browser does it to them.
function itemUsed(m) {
  const now = raceTime(), me = room.you, by = player(m.by)?.name || 'Someone', item = ITEMS[m.k];
  S.effects.push({ ...m, at: local() });
  S.itemsSeen++;
  const hitMe = m.to.includes(me), savedMe = m.blocked.includes(me);
  if (hitMe && S.me && racing()) {
    if (m.k === 'bolt') S.me.dead = true;
    else if (m.k === 'freeze') S.frozenUntil = now + FREEZE;
    else if (m.k === 'boost') S.boostUntil = now + BOOST;
    if (m.warp?.[me]) {
      const [x, y, cp] = m.warp[me];
      Object.assign(S.me, { x, y: y - 1, vx: 0, vy: 0, cp, stood: {}, dead: false, on: -1 });
    }
  }
  const named = m.to.filter(id => id !== m.by).map(id => player(id)?.name).filter(Boolean);
  let text = '';
  if (m.by === me) {
    if (m.blocked.length) text = `${m.blocked.map(id => player(id)?.name).join(', ')} blocked your ${item.name.toLowerCase()}`;
    else if (named.length) text = `You ${item.did} ${named.join(', ')}`;
    else if (m.k === 'bolt' || m.k === 'swap' || m.k === 'freeze') text = 'Nobody ahead to hit';
  } else if (hitMe) text = `${by} ${item.did} you!`;
  else if (savedMe) text = `Your shield blocked ${by}'s ${item.name.toLowerCase()}`;
  if (text) S.note = { text, until: local() + 2.5 };
  if (hitMe || m.by === me || savedMe) sound(savedMe ? 'blocked' : m.k);
}

// ---------------------------------------------------------------- the lobby, the HUD and the results

const ORDINAL = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th'];
const clock = secs => `${Math.floor(secs / 60)}:${(secs % 60).toFixed(1).padStart(4, '0')}`;

function render() {
  const st = S.st;
  document.body.classList.toggle('host', st.host === room.you);
  if (st.phase === 'lobby') {
    show('lobby');
    const n = st.players.length;
    $('room-code').textContent = room.code;
    $('count').textContent = `${n} of 8`;
    $('seats').replaceChildren(...st.players.map(p => person(p, room.you, p.bot ? 'Bot' : p.id === st.host ? 'Host' : '')));
    $('rounds').value = st.rounds;
    $('rounds').disabled = st.host !== room.you;
    $('bot-add').disabled = n >= 8;
    $('bot-remove').disabled = !st.players.some(p => p.bot);
    $('lobby-note').textContent = st.host === room.you
      ? (n === 1 ? 'You can race the clock alone, or add bots to race against.' : '')
      : `Waiting for ${player(st.host)?.name || 'the host'} to start.`;
    return;
  }
  show('game');
  resize();
  $('hud-round').textContent = `Round ${st.round} of ${st.rounds}`;
  const over = st.phase !== 'race';
  $('results').hidden = !over;
  if (!over) return;
  const final = st.phase === 'final';
  const rows = final ? [...st.players].filter(p => p.racing || p.pts).sort((a, b) => b.pts - a.pts)
    : st.order.map(player).filter(Boolean);
  $('res-kicker').textContent = final ? 'Final standings' : `Round ${st.round} of ${st.rounds}`;
  $('res-title').textContent = final ? `${rows[0]?.name || 'Nobody'} wins!` : `${rows[0]?.name || 'Nobody'} takes the round`;
  $('res-rows').replaceChildren(...rows.map((p, i) => {
    const tr = document.createElement('tr');
    if (p.id === room.you) tr.className = 'me';
    const cell = (text, cls) => { const td = document.createElement('td'); td.textContent = text; if (cls) td.className = cls; return td; };
    const name = cell(p.name);
    const dot = document.createElement('span');
    dot.className = 'dot';
    dot.style.setProperty('--c', p.color);
    name.prepend(dot);
    tr.append(cell(ORDINAL[i] || ''), name, cell(p.fin != null ? clock(p.fin) : 'Did not finish'), cell(p.gain ? `+${p.gain}` : '', 'gain'), cell(p.pts));
    return tr;
  }));
  $('res-note').textContent = final ? '' : 'The next course is being built…';
  $('again').hidden = $('res-leave').hidden = !final;
}

$('bot-add').addEventListener('click', () => room.send({ t: 'bot', op: 'add' }));
$('bot-remove').addEventListener('click', () => room.send({ t: 'bot', op: 'remove' }));
$('rounds').addEventListener('change', () => room.send({ t: 'rounds', v: +$('rounds').value }));
$('start').addEventListener('click', () => { sound('go'); room.send({ t: 'start' }); });
$('again').addEventListener('click', () => room.send({ t: 'again' }));

// ---------------------------------------------------------------- controls

const keys = new Set();
let tapped = false;   // jump was pressed since the last physics step, however briefly
const touch = { left: false, right: false, jump: false };
const KEYMAP = { ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right', ArrowUp: 'jump', KeyW: 'jump', Space: 'jump' };
const USE_KEYS = new Set(['KeyE', 'ShiftLeft', 'ShiftRight', 'KeyF']);
const useItem = () => { if (racing() && mine()?.item && raceTime() > 0) room.send({ t: 'use' }); };
addEventListener('keydown', e => {
  if (USE_KEYS.has(e.code) && !$('game').hidden && !e.repeat) { useItem(); e.preventDefault(); return; }
  const k = KEYMAP[e.code];
  if (!k || $('game').hidden || e.target.tagName === 'INPUT') return;
  if (k === 'jump' && !keys.has(k)) tapped = true;
  keys.add(k);
  e.preventDefault();
});
addEventListener('keyup', e => keys.delete(KEYMAP[e.code]));
addEventListener('blur', () => keys.clear());
for (const [id, k] of [['t-left', 'left'], ['t-right', 'right'], ['t-jump', 'jump']]) {
  const b = $(id);
  const set = on => e => { e.preventDefault(); touch[k] = on; if (on && k === 'jump') tapped = true; b.classList.toggle('down', on); };
  b.addEventListener('pointerdown', set(true));
  for (const type of ['pointerup', 'pointercancel', 'pointerleave']) b.addEventListener(type, set(false));
  b.addEventListener('contextmenu', e => e.preventDefault());
}
$('t-use').addEventListener('pointerdown', e => { e.preventDefault(); useItem(); });
const coarse = matchMedia('(pointer: coarse)').matches;
$('touch').hidden = !coarse;
const input = () => ({
  dir: (keys.has('right') || touch.right ? 1 : 0) - (keys.has('left') || touch.left ? 1 : 0),
  jump: keys.has('jump') || touch.jump || tapped,
});

// ---------------------------------------------------------------- sounds

let audio = null;
function sound(kind) {
  try {
    audio ||= new AudioContext();
    const [f0, f1, secs, type] = { jump: [300, 620, 0.12, 'square'], spring: [240, 980, 0.22, 'square'], out: [260, 70, 0.3, 'sawtooth'],
      flag: [520, 780, 0.1, 'triangle'], item: [700, 1400, 0.15, 'triangle'], bolt: [1600, 200, 0.25, 'sawtooth'],
      freeze: [1200, 900, 0.4, 'sine'], trap: [300, 200, 0.12, 'square'], swap: [400, 1200, 0.3, 'sine'],
      shield: [500, 900, 0.25, 'sine'], boost: [300, 900, 0.3, 'square'], blocked: [900, 500, 0.15, 'triangle'], win: [660, 1320, 0.5, 'triangle'], go: [880, 880, 0.25, 'square'], tick: [440, 440, 0.1, 'square'] }[kind];
    const o = audio.createOscillator(), g = audio.createGain(), t = audio.currentTime;
    o.type = type;
    o.frequency.setValueAtTime(f0, t);
    o.frequency.exponentialRampToValueAtTime(f1, t + secs);
    g.gain.setValueAtTime(0.06, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + secs);
    o.connect(g).connect(audio.destination);
    o.start(t);
    o.stop(t + secs);
  } catch { /* no sound, then */ }
}

// ---------------------------------------------------------------- each frame: physics, then the picture

const canvas = $('view'), ctx = canvas.getContext('2d');
const VIEW_H = 640, VIEW_W = 560;   // the least of the world, in its units, that must fit on screen
function resize() {
  const dpr = Math.min(devicePixelRatio || 1, 2);
  const w = Math.round(canvas.clientWidth * dpr), h = Math.round(canvas.clientHeight * dpr);
  if (w && (canvas.width !== w || canvas.height !== h)) { canvas.width = w; canvas.height = h; }
}
addEventListener('resize', resize);

let lastFrame = local(), simTime = null, lastSent = 0, lastCount = null;

function simulate(now) {
  const p = S.me, c = S.course;
  if (simTime == null || now - simTime > 0.25) simTime = now;   // a tab that was asleep doesn't catch up
  const inp = input();
  while (simTime + DT <= now) {
    simTime += DT;
    if (simTime < 0) continue;   // still on the start line
    if (p.dead) {
      if (!S.downAt) { S.downAt = simTime; sound('out'); }
      if (simTime - S.downAt > KNOCKOUT) { S.me = Object.assign(p, spawn(c, p.cp)); S.downAt = 0; }
      continue;
    }
    const was = { ground: p.ground, cp: p.cp, sprung: p.sprung, vy: p.vy };
    p.speed = (simTime < S.frozenUntil ? FREEZE_SPEED : 1) * (simTime < S.boostUntil ? BOOST_SPEED : 1);
    step(p, inp, simTime, c);
    if (!p.dead && !mine()?.item) {
      c.boxes.forEach(([bx, by], i) => {
        if (!S.grabbed.has(i) && Math.abs(p.x - bx) < PW / 2 + 13 && p.y > by - 13 && p.y - PH < by + 13) {
          S.grabbed.add(i);
          room.send({ t: 'grab', i });
        }
      });
    }
    if (tapped) { tapped = false; inp.jump = keys.has('jump') || touch.jump; }
    if (p.sprung !== was.sprung) sound('spring');
    else if (was.ground && p.vy < -400) sound('jump');
    if (p.cp !== was.cp) sound('flag');
  }
  if (now - lastSent > 0.066) {
    lastSent = now;
    room.send({ t: 'p', v: [Math.round(p.x), Math.round(p.y), p.face, p.ground ? 0 : 1, p.dead ? 1 : 0] });
  }
}

function hud(now) {
  const st = S.st, me = mine(), banner = $('banner');
  const racers = [...S.others.entries()].map(([id, o]) => ({ id, x: id === room.you && S.me && racing() ? S.me.x : o.tx, fin: player(id)?.fin }));
  const ahead = racers.filter(r => r.id !== room.you && (r.fin != null || (me?.fin == null && r.x > (S.me?.x ?? 0)))).length;
  const place = me?.fin != null ? st.order.indexOf(room.you) : ahead;
  $('hud-place').textContent = me?.racing && racers.length > 1 ? ORDINAL[place] || '' : '';
  $('hud-time').textContent = clock(Math.max(0, me?.fin ?? now));
  let text = '', small = false;
  if (st.phase === 'race') {
    if (now < 0) {
      const n = Math.ceil(-now);
      text = n > 3 ? 'Get ready' : String(n);
      if (n !== lastCount && n <= 3) sound('tick');
      lastCount = n;
    } else if (now < 0.8) {
      text = 'Go!';
      if (lastCount !== 0) { lastCount = 0; sound('go'); }
    } else if (me?.fin != null) {
      text = `Finished ${ORDINAL[st.order.indexOf(room.you)] || ''}!`;
      small = now - me.fin > 2;
    } else if (!me?.racing) {
      text = "Watching: you'll race in the next round";
      small = true;
    } else if (st.ends != null) {
      text = `${Math.max(0, Math.ceil(st.ends - now))} s left`;
      small = true;
    }
  }
  if (!text && S.note && local() < S.note.until) { text = S.note.text; small = true; }
  banner.hidden = !text;
  banner.textContent = text;
  banner.classList.toggle('small', small);
  const item = racing() ? ITEMS[me?.item] : null;
  $('item').hidden = !item;
  $('t-use').classList.toggle('empty', !item);
  if (item) {
    $('item-icon').textContent = item.icon;
    $('item-icon').style.color = item.color;
    $('item-name').textContent = item.name;
    $('item-tip').textContent = `${item.tip}. ${coarse ? 'Tap Use' : 'E or Shift to use'}`;
  }
}

function frame() {
  requestAnimationFrame(frame);
  const t = local(), dt = Math.min(0.1, t - lastFrame);
  lastFrame = t;
  if (!S.st || S.st.phase === 'lobby' || !S.course || $('game').hidden) return;
  const now = raceTime();
  if (racing()) simulate(now); else simTime = null;
  for (const o of S.others.values()) {   // ease everyone else towards where they were last seen
    const k = 1 - Math.exp(-dt * 18);
    if (Math.abs(o.tx - o.x) > 400) { o.x = o.tx; o.y = o.ty; }
    o.x += (o.tx - o.x) * k;
    o.y += (o.ty - o.y) * k;
  }
  hud(now);
  draw(now, dt);
}

// Who the camera follows: this player, or (watching, or finished) whoever is still running in front.
function focus() {
  if (S.me && mine()?.racing && (racing() || S.st.phase !== 'race' || raceTime() - mine().fin < 2.5)) return S.me;
  const running = [...S.others.entries()].filter(([id]) => player(id)?.fin == null).map(([, o]) => o);
  return running.sort((a, b) => b.x - a.x)[0] || S.me || { x: 0, y: 0 };
}

function draw(now, dt) {
  const c = S.course, k = Math.min(canvas.height / VIEW_H, canvas.width / VIEW_W), vw = canvas.width / k, vh = canvas.height / k;
  const floor = -vh * 0.7;   // the camera's resting height: the ground 70% of the way down
  const f = focus(), cam = S.cam;
  const wantX = Math.max(0, Math.min(f.x - vw * 0.4, c.length - vw));
  const wantY = Math.min(floor, f.y - vh * 0.4);
  const ease = 1 - Math.exp(-dt * 8);
  cam.x += (wantX - cam.x) * (Math.abs(wantX - cam.x) > 900 ? 1 : ease);
  cam.y += (wantY - cam.y) * ease;
  const t = Math.max(0, now);

  ctx.setTransform(1, 0, 0, 1, 0, 0);
  const sky = ctx.createLinearGradient(0, 0, 0, canvas.height);
  sky.addColorStop(0, '#6fb1e0');
  sky.addColorStop(1, '#d6ecf5');
  ctx.fillStyle = sky;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  // far hills, drifting past slower than the course
  for (const [depth, color, h, wave] of [[0.15, '#a9d0c0', 150, 520], [0.35, '#8fbf9c', 100, 340]]) {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(0, canvas.height);
    for (let sx = 0; sx <= vw + 40; sx += 40) {
      const wx = sx + cam.x * depth;
      ctx.lineTo(sx * k, (vh * 0.72 - h * (0.5 + 0.5 * Math.sin(wx / wave) * Math.cos(wx / (wave * 2.7)))) * k);
    }
    ctx.lineTo(canvas.width, canvas.height);
    ctx.fill();
  }

  ctx.setTransform(k, 0, 0, k, -cam.x * k, -cam.y * k);
  const seen = (x, w) => x + w > cam.x - 50 && x < cam.x + vw + 50;

  // checkpoint flags and the finish
  c.segs.forEach((x, i) => {
    if (!i || i === c.segs.length - 1 || !seen(x, 80)) return;
    const up = S.me && S.me.cp >= i;
    ctx.fillStyle = '#5b4a3a';
    ctx.fillRect(x + 38, -64, 4, 64);
    ctx.fillStyle = up ? '#f2c230' : '#e9e4d8';
    ctx.beginPath();
    ctx.moveTo(x + 42, -64); ctx.lineTo(x + 70, -54); ctx.lineTo(x + 42, -44);
    ctx.fill();
  });
  if (seen(c.finish, 60)) {
    ctx.fillStyle = '#4a3b2c';
    ctx.fillRect(c.finish - 3, -170, 6, 170);
    for (let i = 0; i < 4; i++) for (let j = 0; j < 3; j++) {
      ctx.fillStyle = (i + j) % 2 ? '#1d1b19' : '#fff';
      ctx.fillRect(c.finish + 3 + i * 16, -170 + j * 16, 16, 16);
    }
  }

  for (const s of c.plats) {
    if (!seen(s.x, s.w)) continue;
    const thin = s.h <= 30;
    ctx.fillStyle = thin ? '#b07a45' : '#7a5433';
    ctx.fillRect(s.x, s.y, s.w, s.h);
    ctx.fillStyle = thin ? '#d19a5c' : '#5fae4e';
    ctx.fillRect(s.x, s.y, s.w, thin ? 6 : 12);
    if (!thin) { ctx.fillStyle = 'rgba(0,0,0,0.12)'; ctx.fillRect(s.x, s.y + 12, s.w, 5); }
  }
  for (const m of c.movers) {
    const x = posX(m, t), y = posY(m, t);
    if (!seen(x, m.w)) continue;
    ctx.fillStyle = '#56657a';
    ctx.fillRect(x, y, m.w, m.h);
    ctx.fillStyle = '#9fb0c6';
    ctx.fillRect(x, y, m.w, 6);
    ctx.fillStyle = '#2f3a48';
    for (const bx of [8, m.w - 12]) ctx.fillRect(x + bx, y + 11, 4, 4);
  }
  for (const s of c.pads) {
    if (!seen(s.x, s.w)) continue;
    const squash = S.me?.sprung != null && t - S.me.sprung < 0.15 && Math.abs(S.me.x - s.x - s.w / 2) < 120 ? 6 : 0;
    ctx.fillStyle = '#3b3f48';
    ctx.fillRect(s.x + 6, s.y - 8 + squash, s.w - 12, 8 - squash);
    ctx.fillStyle = '#e8452f';
    ctx.fillRect(s.x, s.y - 14 + squash, s.w, 6);
  }
  // crumbling blocks: as this player sees them (each racer crumbles their own)
  c.crumbles.forEach((s, i) => {
    if (!seen(s.x, s.w)) return;
    const since = S.me?.stood[i] != null ? t - S.me.stood[i] : null;
    let dx = 0, dy = 0, alpha = 1;
    if (since != null && since < CRUMBLE) dx = Math.sin(since * 80) * 2.5;
    else if (since != null) { dy = (since - CRUMBLE) ** 2 * 1400; alpha = Math.max(0, 1 - (since - CRUMBLE) * 1.5); }
    if (alpha <= 0) return;
    ctx.globalAlpha = alpha;
    ctx.fillStyle = '#9a7b5b';
    ctx.fillRect(s.x + dx, s.y + dy, s.w, CRUMBLE_H);
    ctx.fillStyle = '#6f553c';
    for (let cx = s.x + 14; cx < s.x + s.w - 8; cx += 22) ctx.fillRect(cx + dx, s.y + dy + 6, 3, CRUMBLE_H - 10);
    ctx.globalAlpha = 1;
  });
  // item boxes: faded once this player has had one
  ctx.font = '700 18px "Source Sans 3", sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  c.boxes.forEach(([bx, by], i) => {
    if (!seen(bx - 15, 30)) return;
    const bob = Math.sin(t * 3 + i) * 3;
    ctx.globalAlpha = S.grabbed.has(i) ? 0.3 : 1;
    ctx.fillStyle = '#f2c230';
    ctx.beginPath(); ctx.roundRect(bx - 13, by - 13 + bob, 26, 26, 5); ctx.fill();
    ctx.strokeStyle = '#9a6b0f'; ctx.lineWidth = 2; ctx.stroke();
    ctx.fillStyle = '#5a3d00';
    ctx.fillText('?', bx, by + 1 + bob);
    ctx.globalAlpha = 1;
  });
  ctx.textBaseline = 'alphabetic';
  for (const s of c.traps) {
    if (!seen(s.x, s.w)) continue;
    const n = 3, w = s.w / n;
    ctx.fillStyle = player(s.owner)?.color || '#e8452f';
    ctx.beginPath();
    for (let i = 0; i < n; i++) { ctx.moveTo(s.x + i * w, s.y); ctx.lineTo(s.x + (i + 0.5) * w, s.y - SPIKE_H); ctx.lineTo(s.x + (i + 1) * w, s.y); }
    ctx.fill();
    ctx.strokeStyle = '#1d1b19'; ctx.lineWidth = 1.5; ctx.stroke();
  }
  ctx.fillStyle = '#c9ced6';
  for (const s of c.spikes) {
    if (!seen(s.x, s.w)) continue;
    const n = Math.max(2, Math.round(s.w / 14)), w = s.w / n;
    ctx.beginPath();
    for (let i = 0; i < n; i++) { ctx.moveTo(s.x + i * w, s.y); ctx.lineTo(s.x + (i + 0.5) * w, s.y - SPIKE_H); ctx.lineTo(s.x + (i + 1) * w, s.y); }
    ctx.fill();
  }
  for (const s of c.saws) {
    const x = posX(s, t), y = posY(s, t);
    if (!seen(x - s.r, s.r * 2)) continue;
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(t * 9);
    ctx.fillStyle = '#d4d9e0';
    ctx.beginPath();
    for (let i = 0; i < 20; i++) { const a = i / 20 * Math.PI * 2, r = i % 2 ? s.r : s.r - 7; ctx.lineTo(Math.cos(a) * r, Math.sin(a) * r); }
    ctx.fill();
    ctx.fillStyle = '#7d8794';
    ctx.beginPath(); ctx.arc(0, 0, s.r * 0.35, 0, Math.PI * 2); ctx.fill();
    ctx.restore();
  }

  // everyone else, then this player on top
  ctx.font = '600 13px "Source Sans 3", sans-serif';
  ctx.textAlign = 'center';
  const meRacing = S.me && mine()?.racing;
  for (const [id, o] of S.others) {
    if (id === room.you && meRacing) continue;
    const p = player(id);
    if (!p || !seen(o.x - 20, 40)) continue;
    runner(o.x, o.y, p.color, o.face, o.air, o.dead, 0.85, o.marks || 0);
    ctx.fillStyle = 'rgba(20,40,60,0.75)';
    ctx.fillText(p.name, o.x, o.y - PH - 10);
  }
  if (meRacing) {
    const p = S.me;
    const marks = (mine().shield ? 1 : 0) | (t < S.frozenUntil ? 2 : 0) | (t < S.boostUntil ? 4 : 0);
    runner(p.x, p.y, mine().color, p.face, !p.ground, p.dead, 1, marks);
    ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.moveTo(p.x - 6, p.y - PH - 16); ctx.lineTo(p.x + 6, p.y - PH - 16); ctx.lineTo(p.x, p.y - PH - 8); ctx.fill();
  }
  drawEffects();
}

// Where a racer is drawn: this player from their own physics, anyone else as last reported.
function at(id) {
  if (id === room.you && S.me && mine()?.racing) return S.me;
  return S.others.get(id);
}

// Items going off: a bolt's lightning, a freeze's frost, a swap's swirl, a blocked hit's pop.
function drawEffects() {
  const t = local();
  S.effects = S.effects.filter(e => t - e.at < 0.6);
  for (const e of S.effects) {
    const age = (t - e.at) / 0.6, from = at(e.by);
    ctx.globalAlpha = 1 - age;
    ctx.strokeStyle = ITEMS[e.k].color;
    ctx.lineWidth = 4;
    for (const id of [...e.to, ...e.blocked]) {
      const to = at(id);
      if (!to) continue;
      if (e.k === 'bolt' && from) {
        ctx.beginPath();
        ctx.moveTo(from.x, from.y - PH / 2);
        for (let i = 1; i <= 8; i++) {
          const u = i / 8;
          ctx.lineTo(from.x + (to.x - from.x) * u + (i < 8 ? Math.sin(i * 12.9 + e.at * 50) * 14 : 0),
            from.y - PH / 2 + (to.y - from.y) * u - Math.sin(u * Math.PI) * 60);
        }
        ctx.stroke();
      }
      if (e.k !== 'boost') {
        ctx.beginPath();
        ctx.arc(to.x, to.y - PH / 2, 20 + age * 40, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }
}

function runner(x, y, color, face, air, dead, alpha, marks = 0) {
  ctx.save();
  ctx.translate(x, y);
  ctx.globalAlpha = dead ? 0.35 : alpha;
  const w = air ? PW - 4 : PW, h = air ? PH + 4 : PH;
  if (marks & 4) {   // boosted: speed lines behind
    ctx.strokeStyle = '#ffb347';
    ctx.lineWidth = 3;
    for (const ly of [-h * 0.3, -h * 0.55, -h * 0.8]) { ctx.beginPath(); ctx.moveTo(-face * 18, ly); ctx.lineTo(-face * 40, ly); ctx.stroke(); }
  }
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.roundRect(-w / 2, -h, w, h, 7);
  ctx.fill();
  ctx.fillStyle = '#fff';
  ctx.fillRect(face > 0 ? 1 : -9, -h + 9, 8, 9);
  ctx.fillStyle = '#1d1b19';
  ctx.fillRect(face > 0 ? 5 : -9, -h + 12, 4, 5);
  if (marks & 2) {   // frozen: a crust of ice
    ctx.fillStyle = 'rgba(170, 230, 255, 0.55)';
    ctx.beginPath(); ctx.roundRect(-w / 2 - 3, -h - 3, w + 6, h + 3, 8); ctx.fill();
  }
  if (marks & 1) {   // shielded: a bubble
    ctx.strokeStyle = 'rgba(127, 208, 255, 0.9)';
    ctx.fillStyle = 'rgba(127, 208, 255, 0.15)';
    ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(0, -h / 2, h * 0.8, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
  }
  ctx.restore();
}

requestAnimationFrame(frame);
if (room.debug) window.scramble = { S, room, keys, raceTime };
