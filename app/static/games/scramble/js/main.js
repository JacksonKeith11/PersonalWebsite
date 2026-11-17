// Scramble in the browser: the lobby, this player's own physics and controls, everyone else as the
// server reports them, and the drawing. The server (app/scramble/game.py) makes the course, runs
// the bots and keeps the clock and the scores.

import { DT, PH, PW, SPIKE_H, posX, posY, prepare, spawn, step } from './physics.js?v=1';
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
};

const room = startRoom({ key: 'scramble', path: '/games/scramble', title: 'Scramble', show, onMessage: receive });
const local = () => performance.now() / 1000;
const raceTime = () => (S.offset == null ? -9 : local() + S.offset);
const player = id => S.st?.players.find(p => p.id === id);
const mine = () => player(room.you);
const racing = () => S.st?.phase === 'race' && S.course && mine()?.racing && mine().fin == null;

function receive(m) {
  if (m.t === 'state') {
    S.st = m;
    render();
  } else if (m.t === 'course') {
    S.course = prepare(m.course);
    S.offset = m.now - local();
    S.me = spawn(S.course);
    S.others.clear();
    S.cam.x = 0;
  } else if (m.t === 'pos') {
    // the clock: the message that took the least time to get here is nearest the truth
    const est = m.now - local();
    S.offset = S.offset == null || Math.abs(est - S.offset) > 0.5 ? est : Math.max(est, S.offset - 0.0005);
    for (const [id, x, y, face, air, dead] of m.ps) {
      const o = S.others.get(id) || { x, y };
      S.others.set(id, Object.assign(o, { tx: x, ty: y, face, air, dead }));
    }
  }
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
addEventListener('keydown', e => {
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
$('touch').hidden = !matchMedia('(pointer: coarse)').matches;
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
      flag: [520, 780, 0.1, 'triangle'], win: [660, 1320, 0.5, 'triangle'], go: [880, 880, 0.25, 'square'], tick: [440, 440, 0.1, 'square'] }[kind];
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
      if (simTime - S.downAt > 0.7) { S.me = Object.assign(p, spawn(c, p.cp)); S.downAt = 0; }
      continue;
    }
    const was = { ground: p.ground, cp: p.cp, sprung: p.sprung, vy: p.vy };
    step(p, inp, simTime, c);
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
  banner.hidden = !text;
  banner.textContent = text;
  banner.classList.toggle('small', small);
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
    runner(o.x, o.y, p.color, o.face, o.air, o.dead, 0.85);
    ctx.fillStyle = 'rgba(20,40,60,0.75)';
    ctx.fillText(p.name, o.x, o.y - PH - 10);
  }
  if (meRacing) {
    const p = S.me;
    runner(p.x, p.y, mine().color, p.face, !p.ground, p.dead, 1);
    ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.moveTo(p.x - 6, p.y - PH - 16); ctx.lineTo(p.x + 6, p.y - PH - 16); ctx.lineTo(p.x, p.y - PH - 8); ctx.fill();
  }
}

function runner(x, y, color, face, air, dead, alpha) {
  ctx.save();
  ctx.translate(x, y);
  ctx.globalAlpha = dead ? 0.35 : alpha;
  const w = air ? PW - 4 : PW, h = air ? PH + 4 : PH;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.roundRect(-w / 2, -h, w, h, 7);
  ctx.fill();
  ctx.fillStyle = '#fff';
  ctx.fillRect(face > 0 ? 1 : -9, -h + 9, 8, 9);
  ctx.fillStyle = '#1d1b19';
  ctx.fillRect(face > 0 ? 5 : -9, -h + 12, 4, 5);
  ctx.restore();
}

requestAnimationFrame(frame);
if (room.debug) window.scramble = { S, room, keys, raceTime };
