// Frag Arena's client: input, your own movement (predicted here, reported to the server),
// firing, the server's events, the camera and the HUD.
import { Net } from './net.js?v=1';
import { View } from './render.js?v=1';
import { setWorld, move, rayWorld, rayBox, playerBox } from './physics.js?v=1';
import { initAudio, sfx, setListener, setVolume } from './audio.js?v=1';

const $ = id => document.getElementById(id);
const MG = 0, SG = 1, RL = 2, RG = 3;
const STEP = 1 / 125;
const KEY = 'frag-arena';
const WEAPON_SHORT = ['MG', 'SG', 'RL', 'RG'];

function loadSettings() {
  try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; }
}
const settings = Object.assign({ name: '', sens: 2.5, fov: 100, volume: 70, invert: false }, loadSettings());
function saveSettings() {
  try { localStorage.setItem(KEY, JSON.stringify(settings)); } catch { /* private mode */ }
}

const view = new View($('view'));
view.setFov(settings.fov);
setVolume(settings.volume / 100);
const canvas = view.renderer.domElement;

const S = {
  id: 0, ready: false, weapons: null, knock: 0.15, limit: 20, eye: 1.6,
  body: { pos: [0, 0, 0], vel: [0, 0, 0], ground: false }, prev: [0, 0, 0],
  yaw: 0, pitch: 0, alive: false, life: 0, hp: 0, armor: 0, ammo: [0, 0, 0, 0], weapon: MG,
  nextFire: 0, firedAt: -9, roster: new Map(), playing: false, wantPlay: false,
  diedAt: 0, killer: null, interUntil: 0, events: [], rockets: new Map(), nextLid: 1,
  sendAt: 0, acc: 0, bob: 0, stepSmooth: 0, landKick: 0, pain: 0, remote: new Map(),
};

// ------------------------------------------------------------------ network

const net = new Net({
  onStatus: text => { $('status').textContent = text; },
  onWelcome(m) {
    S.id = m.id;
    S.weapons = m.weapons;
    S.knock = m.knock;
    S.limit = m.limit;
    S.eye = m.phys.eye;
    setWorld(m.map, m.phys);
    if (!S.ready) view.buildMap(m.map);
    S.ready = true;
    S.alive = false;
    S.life = 0;
    S.events = [];
    for (const k of S.rockets.keys()) view.removeRocket('L' + k);
    S.rockets.clear();
    for (const id of [...view.players.keys()]) view.removePlayer(id);
    $('play').disabled = false;
    if (S.wantPlay) net.send({ t: 'spawn' });
  },
  onRoster(list) {
    S.roster = new Map(list.map(([id, name, color, score, deaths, bot, ping, playing]) =>
      [id, { id, name, color, score, deaths, bot: !!bot, ping, playing: !!playing }]));
    for (const id of [...view.players.keys()]) if (!S.roster.has(id)) view.removePlayer(id);
    drawRoster();
  },
  onSnap(m) {
    for (const e of m.pv) privateEvent(e);
    const [hp, armor, a0, a1, a2, a3, alive, life] = m.me;
    if (life === S.life) {
      S.hp = hp;
      S.armor = armor;
      const fresh = performance.now() / 1000 - S.firedAt < 0.3;
      S.ammo = [a0, a1, a2, a3].map((a, i) => (fresh && i === S.weapon ? Math.min(a, S.ammo[i]) : a));
      if (S.alive && !alive) died();
      S.alive = !!alive;
    }
    view.setPickups(m.pk);
    for (const e of m.ev) S.events.push([m.ts, e]);
  },
});

function privateEvent(e) {
  if (e.k === 'spawn') {
    S.body = { pos: e.p.slice(), vel: [0, 0, 0], ground: false };
    S.prev = e.p.slice();
    S.yaw = e.yaw;
    S.pitch = 0;
    S.life = e.life;
    S.alive = true;
    S.hp = 100;
    S.killer = null;
    S.weapon = MG;
    view.setViewWeapon(MG);
    sfx('spawn');
    setCenter('', 0);
  } else if (e.k === 'knock') {
    const v = S.body.vel;
    v[0] += e.v[0]; v[1] += e.v[1]; v[2] += e.v[2];
    if (v[1] > 0.5) S.body.ground = false;
  } else if (e.k === 'hurt') {
    S.pain = Math.min(1, S.pain + e.d / 60);
    sfx('hurt', null, 0.8);
    showDamageFrom(e.from);
  } else if (e.k === 'hit') {
    sfx('hit', null, 1, e.d);
    const h = $('hitmark');
    h.classList.remove('on');
    void h.offsetWidth;
    h.classList.add('on');
  } else if (e.k === 'got') {
    sfx(e.kind);
    flashPickup(e.kind);
  }
}

function worldEvent(e) {
  const who = S.roster.get(e.by) || S.roster.get(e.id);
  const color = who ? who.color : '#ffffff';
  if (e.k === 'shot') {
    if (e.by === S.id) return;
    for (const end of e.e) {
      if (e.w === RG) view.rail(e.o, end, color);
      else view.tracer(e.o, end, e.w);
    }
    sfx(WEAPON_SHORT[e.w].toLowerCase(), e.o);
  } else if (e.k === 'rocket') {
    if (e.by === S.id) return;
    view.addRocket('S' + e.id, e.p, e.v, e.ts, color);
    sfx('rl', e.p);
  } else if (e.k === 'boom') {
    if (e.by === S.id) {
      // our own rocket: we drew it already, unless the server saw it hit someone we didn't
      if (S.rockets.has(e.lid)) explodeLocal(e.lid, e.p);
      return;
    }
    view.removeRocket('S' + e.id);
    view.explosion(e.p);
    sfx('boom', e.p);
  } else if (e.k === 'kill') {
    const victim = S.roster.get(e.to), killer = S.roster.get(e.by);
    addFeed(killer, victim, e.w);
    const s = e.to === S.id ? { x: S.body.pos[0], y: S.body.pos[1], z: S.body.pos[2] } : S.remote.get(e.to);
    if (s) {
      view.gibs([s.x, s.y, s.z], victim ? victim.color : '#888888');
      if (e.to !== S.id) sfx('die', [s.x, s.y, s.z], 0.7);
    }
    if (e.to === S.id) {
      S.killer = e.by && e.by !== S.id ? e.by : null;
      setCenter(S.killer ? `Fragged by ${killer ? killer.name : 'someone'}` : 'You fragged yourself', 0);
    } else if (e.by === S.id) {
      sfx('frag');
      setCenter(`You fragged ${victim ? victim.name : 'someone'}`, 2);
    }
  } else if (e.k === 'respawn') {
    if (e.id !== S.id) view.teleport(e.p, color);
  } else if (e.k === 'pickup') {
    if (e.by !== S.id) {
      const pk = view.pickups[e.i];
      if (pk) sfx(pk.kind, [pk.m.position.x, pk.m.position.y, pk.m.position.z], 0.6);
    }
  } else if (e.k === 'msg') {
    addMessage(e.text);
  } else if (e.k === 'win') {
    S.interUntil = net.serverNow() + e.until;
    const w = S.roster.get(e.id);
    setCenter(`${w ? w.name : 'Someone'} wins the round!`, e.until);
    sfx('mega');
  }
}

// ------------------------------------------------------------------ input

const keys = new Set();
let firing = false;

window.addEventListener('keydown', e => {
  if (!S.playing) return;
  keys.add(e.code);
  if (e.code.startsWith('Digit')) {
    const w = Number(e.code.slice(5)) - 1;
    if (w >= 0 && w < 4) selectWeapon(w);
  }
  if (e.code === 'KeyQ') cycleWeapon(-1);
  if (e.code === 'KeyE') cycleWeapon(1);
  if (['Tab', 'Space', 'ArrowUp', 'ArrowDown'].includes(e.code)) e.preventDefault();
});
window.addEventListener('keyup', e => keys.delete(e.code));
window.addEventListener('blur', () => { keys.clear(); firing = false; });
canvas.addEventListener('mousedown', e => {
  if (!S.playing) return;
  if (e.button === 0) firing = true;
  if (!S.alive && S.life > 0 && performance.now() / 1000 - S.diedAt > 1 && net.serverNow() >= S.interUntil) {
    net.send({ t: 'spawn' });
  }
});
window.addEventListener('mouseup', e => { if (e.button === 0) firing = false; });
window.addEventListener('wheel', e => { if (S.playing) cycleWeapon(e.deltaY > 0 ? 1 : -1); }, { passive: true });
document.addEventListener('mousemove', e => {
  if (!S.playing || !S.alive) return;
  const k = settings.sens * 0.0008;
  S.yaw -= e.movementX * k;
  S.pitch -= e.movementY * k * (settings.invert ? -1 : 1);
  S.pitch = Math.max(-1.55, Math.min(1.55, S.pitch));
});

document.addEventListener('pointerlockchange', () => {
  S.playing = document.pointerLockElement === canvas;
  $('menu').hidden = S.playing;
  if (!S.playing) { keys.clear(); firing = false; }
  $('play').textContent = S.alive ? 'Resume' : 'Play';
});

function play() {
  initAudio();
  const name = $('name').value.trim().slice(0, 16);
  if (name !== settings.name) {
    settings.name = name;
    saveSettings();
    if (name) net.send({ t: 'name', name });
  }
  S.wantPlay = true;
  const p = canvas.requestPointerLock();
  if (p && p.catch) p.catch(() => { $('status').textContent = 'Click Play again to grab the mouse.'; });
  if (!S.alive) net.send({ t: 'spawn' });
}

function selectWeapon(w) {
  if (w === S.weapon || !S.alive) return;
  if (S.ammo[w] <= 0) { sfx('empty'); return; }
  S.weapon = w;
  view.setViewWeapon(w);
  S.nextFire = Math.max(S.nextFire, performance.now() / 1000 + 0.2);
  sfx('switch', null, 0.6);
}

function cycleWeapon(dir) {
  for (let i = 1; i < 4; i++) {
    const w = (S.weapon + dir * i + 8) % 4;
    if (S.ammo[w] > 0) { selectWeapon(w); return; }
  }
}

// ------------------------------------------------------------------ firing

function dirOf(yaw, pitch) {
  const c = Math.cos(pitch);
  return [-Math.sin(yaw) * c, Math.sin(pitch), -Math.cos(yaw) * c];
}

function norm(v) {
  const n = Math.hypot(...v) || 1;
  return [v[0] / n, v[1] / n, v[2] / n];
}

function gauss() {
  return (Math.random() + Math.random() + Math.random() - 1.5) * 1.15;
}

// Where our own shots appear to leave the gun (they're aimed from the eye).
function muzzle() {
  const f = dirOf(S.yaw, S.pitch), o = eyePos();
  const rx = Math.cos(S.yaw), rz = -Math.sin(S.yaw);
  return [o[0] + f[0] * 0.7 + rx * 0.16, o[1] + f[1] * 0.7 - 0.14, o[2] + f[2] * 0.7 + rz * 0.16];
}

function eyePos() {
  return [S.body.pos[0], S.body.pos[1] + S.eye, S.body.pos[2]];
}

// Where a shot from o along d stops: the map, or another player as we see them now.
function trace(o, d) {
  let best = rayWorld(o, d, 300);
  for (const [id, s] of S.remote) {
    if (id === S.id || !s.alive) continue;
    const t = rayBox(o, d, playerBox(s.x, s.y, s.z, 0.08), best);
    if (t !== null && t < best) best = t;
  }
  return [o[0] + d[0] * best, o[1] + d[1] * best, o[2] + d[2] * best];
}

function tryFire(t) {
  if (!S.alive || !S.weapons || net.serverNow() < S.interUntil || t < S.nextFire) return;
  const w = S.weapon, spec = S.weapons[w];
  if (S.ammo[w] <= 0) {
    sfx('empty');
    S.nextFire = t + 0.4;
    cycleWeapon(1);
    return;
  }
  S.nextFire = t + spec.cool;
  S.firedAt = t;
  S.ammo[w]--;
  view.shoot(w);
  sfx(spec.key);
  const o = eyePos();
  const base = dirOf(S.yaw, S.pitch);
  const at = net.renderTime();
  const me = S.roster.get(S.id);
  if (w === RL) {
    const lid = S.nextLid++;
    const v = base.map(c => c * spec.speed);
    S.rockets.set(lid, { p: o, v, t0: t, last: o.slice() });
    view.addRocket('L' + lid, o, v, t, '#ffffff');
    net.send({ t: 'fire', w, o, d: [base], at, lid });
    return;
  }
  const n = spec.pellets || 1;
  const dirs = [];
  for (let i = 0; i < n; i++) {
    dirs.push(w === RG ? base : norm(base.map(c => c + gauss() * spec.spread)));
  }
  const m = muzzle();
  for (const d of dirs) {
    const end = trace(o, d);
    if (w === RG) view.rail(m, end, me ? me.color : '#60ffb0');
    else view.tracer(m, end, w);
  }
  net.send({ t: 'fire', w, o, d: dirs, at });
}

// Our own rockets fly here too, so rocket jumps push us the moment they land.
function stepRockets(t) {
  for (const [lid, r] of S.rockets) {
    const age = t - r.t0;
    const pos = [r.p[0] + r.v[0] * age, r.p[1] + r.v[1] * age, r.p[2] + r.v[2] * age];
    const seg = [pos[0] - r.last[0], pos[1] - r.last[1], pos[2] - r.last[2]];
    const len = Math.hypot(...seg);
    if (len > 0) {
      const d = seg.map(c => c / len);
      let hit = rayWorld(r.last, d, len);
      for (const [id, s] of S.remote) {
        if (id === S.id || !s.alive) continue;
        const h = rayBox(r.last, d, playerBox(s.x, s.y, s.z, 0.1), hit);
        if (h !== null && h < hit) hit = h;
      }
      if (hit < len) {
        const back = Math.max(hit - 0.05, 0);
        explodeLocal(lid, [r.last[0] + d[0] * back, r.last[1] + d[1] * back, r.last[2] + d[2] * back]);
        continue;
      }
    }
    r.last = pos;
    view.moveRocket('L' + lid, t);
    if (age > 10) { S.rockets.delete(lid); view.removeRocket('L' + lid); }
  }
}

function explodeLocal(lid, p) {
  S.rockets.delete(lid);
  view.removeRocket('L' + lid);
  view.explosion(p);
  sfx('boom', p);
  if (!S.alive) return;
  const spec = S.weapons[RL];
  const b = playerBox(...S.body.pos);
  const near = [0, 1, 2].map(i => Math.min(Math.max(p[i], b[i]), b[i + 3]));
  const dist = Math.hypot(p[0] - near[0], p[1] - near[1], p[2] - near[2]);
  if (dist >= spec.radius) return;
  const c = [S.body.pos[0], S.body.pos[1] + 0.9, S.body.pos[2]];
  const push = norm([c[0] - p[0], c[1] - p[1] + 0.25, c[2] - p[2]]);
  const k = Math.min(spec.splash * (1 - dist / spec.radius), 200) * S.knock;
  const v = S.body.vel;
  v[0] += push[0] * k; v[1] += push[1] * k; v[2] += push[2] * k;
  if (v[1] > 0.5) S.body.ground = false;
}

// ------------------------------------------------------------------ the loop

function died() {
  S.diedAt = performance.now() / 1000;
  firing = false;
  sfx('die');
  for (const lid of S.rockets.keys()) view.removeRocket('L' + lid);
  S.rockets.clear();
}

let last = performance.now() / 1000;

function frame() {
  requestAnimationFrame(frame);
  const t = performance.now() / 1000;
  const dt = Math.min(0.1, t - last);
  last = t;
  if (!S.ready) {
    view.frame(dt, { x: 0, y: 20, z: 40, yaw: 0, pitch: -0.4 }, { showGun: false });
    return;
  }
  const rt = net.renderTime();
  S.remote = net.sample(rt);

  // world events, in step with the players we draw; after time in a background tab, only the news
  while (S.events.length && S.events[0][0] <= rt) {
    const [ts, e] = S.events.shift();
    e.ts = ts;
    if (ts > rt - 1 || ['kill', 'msg', 'win'].includes(e.k)) worldEvent(e);
  }

  for (const [id, s] of S.remote) {
    if (id === S.id) continue;
    const r = S.roster.get(id);
    if (!r) continue;
    view.ensurePlayer(id, r.color, r.name);
    view.updatePlayer(id, s, dt);
  }
  for (const key of view.rockets.keys()) if (key[0] === 'S') view.moveRocket(key, rt);

  let speed = 0;
  if (S.alive) {
    let f = 0, s = 0;
    if (S.playing) {
      if (keys.has('KeyW') || keys.has('ArrowUp')) f += 1;
      if (keys.has('KeyS') || keys.has('ArrowDown')) f -= 1;
      if (keys.has('KeyD') || keys.has('ArrowRight')) s += 1;
      if (keys.has('KeyA') || keys.has('ArrowLeft')) s -= 1;
    }
    const sy = Math.sin(S.yaw), cy = Math.cos(S.yaw);
    const wx = -sy * f + cy * s, wz = -cy * f - sy * s;
    const jump = S.playing && keys.has('Space');
    S.acc += dt;
    while (S.acc >= STEP) {
      S.acc -= STEP;
      S.prev = S.body.pos.slice();
      const out = move(S.body, wx, wz, jump, STEP);
      if (out.jumped) sfx('jump', null, 0.5);
      if (out.pad) sfx('pad');
      if (out.landed > 9) { sfx('land', null, Math.min(1, out.landed / 20)); S.landKick = Math.min(0.25, out.landed / 80); }
      if (out.stepped) S.stepSmooth = Math.max(-0.6, Math.min(0.6, S.stepSmooth + out.stepped));
    }
    speed = Math.hypot(S.body.vel[0], S.body.vel[2]);
    if (S.body.ground) S.bob += dt * speed * 1.1;
    if (S.playing && firing) tryFire(t);
    if (t >= S.sendAt) {
      S.sendAt = t + 1 / 30;
      const r3 = v => v.map(c => Math.round(c * 1000) / 1000);
      net.send({ t: 'st', p: r3(S.body.pos), v: r3(S.body.vel), yaw: Math.round(S.yaw * 1000) / 1000,
        pitch: Math.round(S.pitch * 1000) / 1000, w: S.weapon, life: S.life });
    }
  }
  if (S.weapons) stepRockets(t);

  S.stepSmooth *= Math.pow(0.0001, dt);
  S.landKick *= Math.pow(0.002, dt);
  S.pain = Math.max(0, S.pain - dt * 1.2);

  // camera
  let cam;
  if (S.alive) {
    const f = S.acc / STEP;
    const p = S.prev.map((c, i) => c + (S.body.pos[i] - c) * f);
    const bobY = S.body.ground ? Math.abs(Math.sin(S.bob)) * 0.05 * Math.min(speed / 10, 1) : 0;
    cam = { x: p[0], y: p[1] + S.eye - S.stepSmooth - S.landKick + bobY, z: p[2], yaw: S.yaw, pitch: S.pitch };
    view.setViewWeapon(S.weapon);
  } else if (S.life > 0) {
    // death cam: on the floor, turning to whoever did it
    const k = S.killer && S.remote.get(S.killer);
    if (k) {
      const want = Math.atan2(S.body.pos[0] - k.x, S.body.pos[2] - k.z);
      let d = want - S.yaw;
      d = ((d + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
      S.yaw += d * Math.min(1, dt * 3);
    }
    const sink = Math.min(1, (t - S.diedAt) * 3);
    cam = { x: S.body.pos[0], y: S.body.pos[1] + S.eye - sink * 1.2, z: S.body.pos[2], yaw: S.yaw, pitch: S.pitch * (1 - sink), roll: sink * 0.4 };
  } else {
    const a = t * 0.05;
    const x = Math.cos(a) * 24, z = Math.sin(a) * 24;
    cam = { x, y: 13, z, yaw: Math.atan2(x, z), pitch: -0.45 };
  }
  setListener(cam.x, cam.y, cam.z, cam.yaw);
  view.frame(dt, cam, { bob: S.bob, speed, showGun: S.alive });
  drawHud(t);
}

// ------------------------------------------------------------------ HUD

let centerUntil = 0;
function setCenter(text, secs) {
  $('center').textContent = text;
  centerUntil = secs ? performance.now() / 1000 + secs : Infinity;
}

function addMessage(text) {
  const el = document.createElement('div');
  el.textContent = text;
  $('msgs').appendChild(el);
  while ($('msgs').children.length > 5) $('msgs').firstChild.remove();
  setTimeout(() => el.remove(), 6000);
}

function nameSpan(p) {
  const s = document.createElement('span');
  s.textContent = p ? p.name : '?';
  s.style.color = p ? p.color : '#ccc';
  return s;
}

function addFeed(killer, victim, w) {
  const el = document.createElement('div');
  if (killer && killer !== victim) el.append(nameSpan(killer), ` ${WEAPON_SHORT[w]} `);
  el.append(nameSpan(victim));
  if (!killer || killer === victim) el.append(' fragged themself');
  $('feed').appendChild(el);
  while ($('feed').children.length > 5) $('feed').firstChild.remove();
  setTimeout(() => el.remove(), 6000);
}

function showDamageFrom(from) {
  const dx = from[0] - S.body.pos[0], dz = from[1] - S.body.pos[2];
  if (Math.hypot(dx, dz) < 0.5) return;
  // angle of the attacker relative to where we look; 0 = straight ahead
  const a = Math.atan2(-dx, -dz) - S.yaw;
  const el = $('dmgdir');
  el.style.transform = `translate(-50%, -50%) rotate(${-a}rad)`;
  el.classList.remove('on');
  void el.offsetWidth;
  el.classList.add('on');
}

function flashPickup(kind) {
  const el = $('pickflash');
  el.dataset.kind = kind;
  el.classList.remove('on');
  void el.offsetWidth;
  el.classList.add('on');
}

let hudKey = '';
function drawHud(t) {
  if (t > centerUntil) setCenter('', 0);
  if (!S.alive && S.life > 0 && net.serverNow() >= S.interUntil && t - S.diedAt > 1) {
    $('respawn').hidden = false;
  } else {
    $('respawn').hidden = true;
  }
  $('pain').style.opacity = S.pain.toFixed(2);
  const inGame = S.alive || S.life > 0;
  $('hud').classList.toggle('dead', !S.alive);
  $('hud').classList.toggle('watching', !inGame);
  const ranked = [...S.roster.values()].filter(p => p.playing || p.bot).sort((a, b) => b.score - a.score);
  const me = S.roster.get(S.id);
  const leader = ranked.find(p => p.id !== S.id);
  const key = [S.hp, S.armor, S.ammo.join(), S.weapon, me && me.score, leader && leader.score, leader && leader.name, Math.round(net.rtt * 1000)].join('|');
  if (key !== hudKey) {
    hudKey = key;
    $('hp').textContent = Math.max(0, S.hp);
    $('hp').parentElement.classList.toggle('low', S.hp <= 25);
    $('armor').textContent = S.armor;
    $('ammo').textContent = S.ammo[S.weapon];
    $('ammo-name').textContent = S.weapons ? S.weapons[S.weapon].name : '';
    [...$('weapons').children].forEach((el, i) => {
      el.classList.toggle('on', i === S.weapon);
      el.classList.toggle('empty', S.ammo[i] <= 0);
      el.querySelector('b').textContent = S.ammo[i];
    });
    $('frags').textContent = me ? me.score : 0;
    $('limit').textContent = S.limit;
    $('lead').textContent = leader ? `${leader.name} ${leader.score}` : '';
    $('ping').textContent = net.rtt ? `${Math.round(net.rtt * 1000)} ms` : '';
  }
  const showScores = (S.playing && keys.has('Tab')) || net.serverNow() < S.interUntil;
  $('scores').hidden = !showScores;
  if (showScores) drawScores(ranked);
}

function drawScores(ranked) {
  const body = $('scores-body');
  body.textContent = '';
  for (const p of ranked) {
    const tr = document.createElement('tr');
    if (p.id === S.id) tr.className = 'me';
    const name = document.createElement('td');
    name.append(nameSpan(p));
    if (p.bot) name.append(' ', Object.assign(document.createElement('small'), { textContent: 'bot' }));
    tr.append(name);
    for (const v of [p.score, p.deaths, p.bot ? '' : `${p.ping}`]) {
      const td = document.createElement('td');
      td.textContent = v;
      tr.append(td);
    }
    body.append(tr);
  }
}

function drawRoster() {
  const list = $('who');
  list.textContent = '';
  const all = [...S.roster.values()];
  for (const p of all) {
    const li = document.createElement('li');
    li.append(nameSpan(p));
    if (p.id === S.id) li.append(' (you)');
    else if (p.bot) li.append(' · bot');
    else if (!p.playing) li.append(' · watching');
    list.append(li);
  }
  const bots = all.filter(p => p.bot).length;
  $('bot-count').textContent = bots ? `${bots} bot${bots > 1 ? 's' : ''}` : 'No bots';
  $('bot-remove').disabled = $('bot-clear').disabled = !bots;
  $('bot-add').disabled = all.length >= 12;
}

// ------------------------------------------------------------------ menu

$('name').value = settings.name;
$('play').addEventListener('click', play);
$('name').addEventListener('keydown', e => { if (e.key === 'Enter') play(); });
$('bot-add').addEventListener('click', () => net.send({ t: 'bot', op: 'add' }));
$('bot-remove').addEventListener('click', () => net.send({ t: 'bot', op: 'remove' }));
$('bot-clear').addEventListener('click', () => net.send({ t: 'bot', op: 'clear' }));

for (const [id, key, fmt] of [['sens', 'sens', v => v.toFixed(1)], ['fov', 'fov', v => `${v}°`], ['volume', 'volume', v => `${v}%`]]) {
  const input = $(id);
  input.value = settings[key];
  $(`${id}-val`).textContent = fmt(Number(settings[key]));
  input.addEventListener('input', () => {
    settings[key] = Number(input.value);
    $(`${id}-val`).textContent = fmt(settings[key]);
    if (key === 'fov') view.setFov(settings.fov);
    if (key === 'volume') setVolume(settings.volume / 100);
    saveSettings();
  });
}
$('invert').checked = settings.invert;
$('invert').addEventListener('change', () => { settings.invert = $('invert').checked; saveSettings(); });

if (matchMedia('(pointer: coarse)').matches && !matchMedia('(pointer: fine)').matches) {
  $('touch-note').hidden = false;
}

// for tools/arena-smoke.js
if (new URLSearchParams(location.search).has('debug')) window.arena = { S, net, view, keys };

$('play').disabled = true;
net.connect(settings.name || '');
requestAnimationFrame(frame);
