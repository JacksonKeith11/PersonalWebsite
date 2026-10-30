// Frag Arena's client: input, your own movement (predicted here, reported to the server),
// firing, the server's events, the camera and the HUD.
import { Net } from './net.js?v=5';
import { View, POWER_COLOR } from './render.js?v=5';
import { setWorld, setPhys, move, rayWorld, rayBox, playerBox } from './physics.js?v=5';
import { initAudio, sfx, setListener, setVolume } from './audio.js?v=5';

const $ = id => document.getElementById(id);
const MG = 0, RL = 2, KN = 8;
const STEP = 1 / 125;
const KEY = 'frag-arena';

function loadSettings() {
  try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; }
}
const settings = Object.assign({ name: '', sens: 2.5, fov: 100, volume: 70, invert: false }, loadSettings());
function saveSettings() {
  try { localStorage.setItem(KEY, JSON.stringify(settings)); } catch { /* private mode */ }
}
const randomId = () => Array.from(crypto.getRandomValues(new Uint8Array(12)), b => b.toString(16).padStart(2, '0')).join('');

// Who this browser is (kept), and which tab (kept through reloads of that tab), so leaving and
// coming back, or a reload, puts you back in as the same player.
if (!settings.token) { settings.token = randomId(); saveSettings(); }
let tab = '';
try {
  tab = sessionStorage.getItem(`${KEY}-tab`) || randomId();
  sessionStorage.setItem(`${KEY}-tab`, tab);
} catch { tab = randomId(); }

const view = new View($('view'));
view.setFov(settings.fov);
setVolume(settings.volume / 100);
const canvas = view.renderer.domElement;

const S = {
  id: 0, ready: false, weapons: null, knock: 0.15, limit: 20, eye: 1.6,
  body: { pos: [0, 0, 0], vel: [0, 0, 0], ground: false }, prev: [0, 0, 0],
  yaw: 0, pitch: 0, alive: false, life: 0, warp: 0, hp: 0, armor: 0, ammo: [], weapon: MG,
  nextFire: 0, firedAt: -9, roster: new Map(), playing: false, wantPlay: false,
  diedAt: 0, killer: null, interUntil: 0, events: [], rockets: new Map(), nextLid: 1,
  sendAt: 0, acc: 0, bob: 0, stepSmooth: 0, landKick: 0, pain: 0, remote: new Map(),
  // what the round's rules let you hold, in slot order, and which never run out (the server's kit)
  allow: [0, 1, 2], inf: new Set(), fast: 1, rules: null, modes: {}, mutators: {},
  maps: {}, map: null, phys: null,
};

// The menu's one-line explanation of each mode and mutator.
const MODE_BLURB = {
  dm: 'Everyone for themselves. First to 20 frags.',
  gun: 'Every two kills moves you to the next weapon, up to the knife; a knife kill wins. Get knifed and you drop back a kill.',
  infect: 'One player turns zombie: fast, knife only. Whoever they kill joins them. Survive three minutes to win.',
  jugg: 'The first kill makes you the Juggernaut: 300 health and a recharging power weapon. Only the Juggernaut scores; kill them to take over. First to 10.',
};
const MUT_BLURB = {
  lowgrav: 'Floaty jumps.', insta: 'Railguns only, one hit kills.', rockets: 'Rocket launchers only, endless ammo.',
  bigheads: 'Huge heads (hitboxes stay the same).', frenzy: 'Power weapons every few seconds.',
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
    S.modes = m.modes;
    S.mutators = m.mutators;
    S.maps = m.maps;
    S.phys = m.phys;
    loadMap(m.map);
    buildRulesMenu();
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
  onMap(map) {
    // someone picked another map, or the rotation moved on; a respawn follows
    loadMap(map);
    S.events = S.events.filter(([, e]) => ['kill', 'msg', 'win'].includes(e.k));
    for (const k of S.rockets.keys()) view.removeRocket('L' + k);
    S.rockets.clear();
  },
  onRules(m) {
    S.rules = m;
    S.limit = m.limit;
    S.knock = m.knock;
    S.phys = m.phys;
    setPhys(m.phys);
    drawRulesMenu();
    hudKey = '';
  },
  onRoster(list) {
    S.roster = new Map(list.map(([id, name, color, score, deaths, bot, ping, playing, role]) =>
      [id, { id, name, color, score, deaths, bot: !!bot, ping, playing: !!playing, role: role || '' }]));
    for (const id of [...view.players.keys()]) if (!S.roster.has(id)) view.removePlayer(id);
    drawRoster();
  },
  onSnap(m) {
    for (const e of m.pv) privateEvent(e);
    const n = S.weapons.length;
    const [hp, armor] = m.me, ammo = m.me.slice(2, 2 + n), [alive, life] = m.me.slice(2 + n);
    if (life === S.life) {
      S.hp = hp;
      S.armor = armor;
      const fresh = performance.now() / 1000 - S.firedAt < 0.3;
      S.ammo = ammo.map((a, i) => (fresh && i === S.weapon ? Math.min(a, S.ammo[i] ?? a) : a));
      if (!fresh && ((isPower(S.weapon) && S.ammo[S.weapon] <= 0) || !S.allow.includes(S.weapon))) pickWeapon(fallback());
      if (S.alive && !alive) died();
      S.alive = !!alive;
    }
    view.setPickups(m.pk);
    view.setPower(m.pw, w => S.weapons[w].key);
    for (const e of m.ev) S.events.push([m.ts, e]);
  },
});

function loadMap(map) {
  setWorld(map, S.phys);
  if (!S.map || S.map.key !== map.key) view.buildMap(map);
  S.map = map;
}

function privateEvent(e) {
  if (e.k === 'spawn') {
    S.body = { pos: e.p.slice(), vel: [0, 0, 0], ground: false, fast: S.fast };
    S.prev = e.p.slice();
    S.yaw = e.yaw;
    S.pitch = 0;
    S.life = e.life;
    S.warp = e.warp;
    S.alive = true;
    S.hp = 100;
    S.killer = null;
    S.weapon = e.w || MG;
    view.setViewWeapon(S.weapon);
    sfx('spawn');
    setCenter('', 0);
  } else if (e.k === 'tp') {
    // swapped places: the server moved us
    S.body = { pos: e.p.slice(), vel: [0, 0, 0], ground: false, fast: S.fast };
    S.prev = e.p.slice();
    S.warp = e.warp;
    sfx('swap');
  } else if (e.k === 'kit') {
    // what the rules let us hold changed: a new round, a Gun Game step, turning zombie or Juggernaut
    const was = S.allow;
    S.allow = e.a;
    S.inf = new Set(e.inf);
    S.fast = S.body.fast = e.fast;
    if (!S.allow.includes(S.weapon)) pickWeapon(fallback());
    const mode = S.rules && S.rules.mode;
    if (mode === 'gun' && was[0] !== e.a[0]) {
      sfx('rankup');
      setCenter(e.a[0] === KN ? 'Knife: one kill to win!' : `Now: ${S.weapons[e.a[0]].name}`, 2);
    } else if (mode === 'infect' && e.a.length === 1 && e.a[0] === KN && !(was.length === 1 && was[0] === KN)) {
      sfx('infect');
      setCenter("You're a zombie! Knife the living", 3);
    }
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
  } else if (e.k === 'got' && e.kind === 'power') {
    sfx('power');
    S.ammo[e.w] = S.weapons[e.w].charge;
    pickWeapon(e.w);
    setCenter(`${S.weapons[e.w].name}: ${S.weapons[e.w].blurb}`, 3.5);
  } else if (e.k === 'got') {
    sfx(e.kind);
    flashPickup(e.kind);
  }
}

const isPower = w => !!(S.weapons && S.weapons[w] && S.weapons[w].power);
// what to hold when the current weapon goes: the first one we may use that has ammo
const fallback = () => S.allow.find(w => S.ammo[w] > 0 || S.inf.has(w)) ?? S.allow[0];

// Draw a hitscan shot by weapon: rails, swap beams, yeet blasts, or plain tracers.
function drawShot(w, o, end, color) {
  const key = S.weapons[w].key;
  if (key === 'rg') view.rail(o, end, color);
  else if (key === 'sw') view.swapBeam(o, end);
  else if (key === 'yt') view.yeet(o, end);
  else if (key !== 'kn') view.tracer(o, end, w);
}

function worldEvent(e) {
  const who = S.roster.get(e.by) || S.roster.get(e.id);
  const color = who ? who.color : '#ffffff';
  if (e.k === 'shot') {
    if (e.by === S.id) return;
    for (const end of e.e) drawShot(e.w, e.o, end, color);
    sfx(S.weapons[e.w].key, e.o);
  } else if (e.k === 'proj') {
    const key = S.weapons[e.w].key;
    if (e.by === S.id && key === 'rl') return;  // we're flying our own rockets
    view.addRocket('S' + e.id, e.p, e.v, e.ts, key);
    if (e.by !== S.id) sfx(key, e.p);
  } else if (e.k === 'boom') {
    const key = S.weapons[e.w].key;
    if (e.by === S.id && key === 'rl') {
      // our own rocket: we drew it already, unless the server saw it hit someone we didn't
      if (S.rockets.has(e.lid)) explodeLocal(e.lid, e.p);
      return;
    }
    view.removeRocket('S' + e.id);
    if (key === 'vx') return;  // it opens a black hole instead; see 'vortex'
    view.explosion(e.p, key === 'io' ? POWER_COLOR.io : 0xffa040, key === 'io' ? 1.4 : 1);
    sfx('boom', e.p);
  } else if (e.k === 'vortex') {
    view.vortex('S' + e.id, e.p, e.t);
    sfx('vortex', e.p);
  } else if (e.k === 'gone') {  // a new round: shots still flying just stop
    for (const id of e.ids) view.removeRocket('S' + id);
  } else if (e.k === 'vend') {
    view.vortexEnd('S' + e.id, e.p);
    sfx('boom', e.p);
  } else if (e.k === 'zap') {
    view.zap(e.a, e.b);
    sfx('zap', e.b, 0.6);
  } else if (e.k === 'swap') {
    view.swapped(e.a, e.b);
    if (e.by !== S.id) sfx('swap', e.a);
  } else if (e.k === 'power') {
    if (e.w !== null) sfx('powerup');
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
      const verb = S.rules && S.rules.mode === 'infect' && killer && killer.role === 'zombie' ? 'Infected' : 'Fragged';
      setCenter(S.killer ? `${verb} by ${killer ? killer.name : 'someone'}` : 'You fragged yourself', 0);
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
    setCenter(e.text || `${w ? w.name : 'Someone'} wins the round!`, e.until);
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
    const w = S.allow[Number(e.code.slice(5)) - 1];
    if (w !== undefined) selectWeapon(w);
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
  if (!(S.ammo[w] > 0)) { sfx('empty'); return; }
  pickWeapon(w);
  sfx('switch', null, 0.6);
}

function pickWeapon(w) {
  S.weapon = w;
  view.setViewWeapon(w);
  S.nextFire = Math.max(S.nextFire, performance.now() / 1000 + 0.2);
}

function cycleWeapon(dir) {
  const slots = S.allow;
  const at = Math.max(0, slots.indexOf(S.weapon));
  for (let i = 1; i < slots.length; i++) {
    const w = slots[(at + dir * i + slots.length * 2) % slots.length];
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
function trace(o, d, grow = 0.08, range = 300) {
  let best = rayWorld(o, d, range);
  for (const [id, s] of S.remote) {
    if (id === S.id || !s.alive) continue;
    const t = rayBox(o, d, playerBox(s.x, s.y, s.z, grow), best);
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
  if (!S.inf.has(w)) S.ammo[w]--;
  view.shoot(w, spec.key);
  sfx(spec.key);
  const o = eyePos();
  const base = dirOf(S.yaw, S.pitch);
  const at = net.renderTime();
  const me = S.roster.get(S.id);
  if (spec.power && S.ammo[w] <= 0) pickWeapon(fallback());  // that was its last charge
  if (spec.kind === 'rocket') {
    const lid = S.nextLid++;
    const v = base.map(c => c * spec.speed);
    S.rockets.set(lid, { p: o, v, t0: t, last: o.slice() });
    view.addRocket('L' + lid, o, v, t, 'rl');
    net.send({ t: 'fire', w, o, d: [base], at, lid });
    return;
  }
  if (spec.kind !== 'hitscan') {  // the server flies vortex shells and ion orbs
    net.send({ t: 'fire', w, o, d: [base], at });
    return;
  }
  const n = spec.pellets || 1;
  const dirs = [];
  for (let i = 0; i < n; i++) {
    dirs.push(spec.spread ? norm(base.map(c => c + gauss() * spec.spread)) : base);
  }
  const m = muzzle();
  for (const d of dirs) drawShot(w, m, trace(o, d, spec.grow, spec.range), me ? me.color : '#60ffb0');
  if (spec.recoil) {  // the yeet cannon kicks you backwards
    const v = S.body.vel;
    v[0] -= base[0] * spec.recoil; v[1] -= base[1] * spec.recoil; v[2] -= base[2] * spec.recoil;
    if (v[1] > 0.5) S.body.ground = false;
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
    view.ensurePlayer(id, r.color, r.name, { role: r.role, bigHeads: !!(S.rules && S.rules.muts.includes('bigheads')) });
    view.updatePlayer(id, s, dt);
  }
  for (const [key, r] of view.rockets) {
    if (key[0] !== 'S') continue;
    if (rt - r.t0 > 12) view.removeRocket(key);  // its end never reached us; nothing lives this long
    else view.moveRocket(key, rt);
  }

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
        pitch: Math.round(S.pitch * 1000) / 1000, w: S.weapon, life: S.life, warp: S.warp });
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
    const half = S.map ? S.map.half : [30, 30];
    const x = Math.cos(a) * half[0] * 0.8, z = Math.sin(a) * half[1] * 0.8;
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
  if (killer && killer !== victim) el.append(nameSpan(killer), ` ${S.weapons[w].short} `);
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
  const modeText = modeLine(ranked);
  const key = [S.hp, S.armor, S.ammo.join(), S.weapon, S.allow.join(), me && me.score, leader && leader.score, leader && leader.name, Math.round(net.rtt * 1000), modeText].join('|');
  if (key !== hudKey) {
    hudKey = key;
    const count = w => (S.inf.has(w) ? '∞' : S.ammo[w] ?? 0);
    $('hp').textContent = Math.max(0, S.hp);
    $('hp').parentElement.classList.toggle('low', S.hp <= 25);
    $('armor').textContent = S.armor;
    $('ammo').textContent = count(S.weapon);
    $('ammo-name').textContent = S.weapons ? S.weapons[S.weapon].name : '';
    const slots = $('weapons');
    while (slots.children.length < S.allow.length) {
      slots.append(Object.assign(document.createElement('div'), { innerHTML: '<i></i> <span></span> <b></b>' }));
    }
    while (slots.children.length > S.allow.length) slots.lastChild.remove();
    S.allow.forEach((w, i) => {
      const el = slots.children[i];
      el.classList.toggle('on', w === S.weapon);
      el.classList.toggle('empty', !(S.ammo[w] > 0));
      el.classList.toggle('power', isPower(w));
      el.style.color = isPower(w) ? `#${(POWER_COLOR[S.weapons[w].key] || 0xffffff).toString(16).padStart(6, '0')}` : '';
      el.querySelector('i').textContent = i + 1;
      el.querySelector('span').textContent = S.weapons[w].short;
      el.querySelector('b').textContent = count(w);
    });
    $('frags-name').textContent = scoreName();
    $('frags').textContent = me ? me.score : 0;
    $('limit').textContent = S.limit ? ` / ${S.limit}` : '';
    $('lead').textContent = leader ? `${leader.name} ${leader.score}` : '';
    $('ping').textContent = net.rtt ? `${Math.round(net.rtt * 1000)} ms` : '';
    $('mode').textContent = modeText;
  }
  const showScores = (S.playing && keys.has('Tab')) || net.serverNow() < S.interUntil;
  $('scores').hidden = !showScores;
  if (showScores) drawScores(ranked);
}

const scoreName = () => ({ gun: 'Kills', infect: 'Points', jugg: 'Points' }[S.rules && S.rules.mode] || 'Frags');

// The line under the scores saying how the round stands: the mode, timers, who's what.
function modeLine(ranked) {
  const r = S.rules;
  if (!r || !S.modes[r.mode]) return '';
  let text = `${S.map ? `${S.map.name} · ` : ''}${S.modes[r.mode]}`;
  const now = net.serverNow();
  if (r.mode === 'gun' && r.ladder) {
    const me = S.roster.get(S.id);
    const rung = Math.min(Math.floor((me ? me.score : 0) / r.per), r.ladder.length - 1);
    text += ` · ${S.weapons[r.ladder[rung]].name} (${rung + 1} of ${r.ladder.length})`;
  } else if (r.mode === 'infect') {
    if (r.alpha !== null) {
      const left = Math.ceil(r.alpha - now);
      text += left > 0 ? ` · first zombie in ${left} s` : ' · waiting for a second player';
    } else if (r.ends !== null) {
      const left = Math.max(0, Math.ceil(r.ends - now));
      const alive = ranked.filter(p => p.role !== 'zombie').length;
      text += ` · ${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')} · ${alive} survivor${alive === 1 ? '' : 's'}`;
    }
  } else if (r.mode === 'jugg') {
    const j = ranked.find(p => p.role === 'jugg');
    text += j ? ` · ${j.id === S.id ? 'you are' : `${j.name} is`} the Juggernaut` : ' · first kill becomes the Juggernaut';
  }
  const muts = Object.keys(S.mutators).filter(m => r.muts.includes(m)).map(m => S.mutators[m]);
  return muts.length ? `${text} · ${muts.join(', ')}` : text;
}

function drawScores(ranked) {
  $('scores-name').textContent = scoreName();
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
    if (p.role) li.append(p.role === 'zombie' ? ' · zombie' : ' · Juggernaut');
    list.append(li);
  }
  const bots = all.filter(p => p.bot).length;
  $('bot-count').textContent = bots ? `${bots} bot${bots > 1 ? 's' : ''}` : 'No bots';
  $('bot-remove').disabled = $('bot-clear').disabled = !bots;
  $('bot-add').disabled = all.length >= 12;
}

// ------------------------------------------------------------------ menu

// The mode and mutators: anyone can change them, which starts a new round for everyone.
function buildRulesMenu() {
  if ($('modes').children.length) return;
  for (const [key, [name]] of Object.entries(S.maps)) {
    const b = Object.assign(document.createElement('button'), { type: 'button', textContent: name });
    b.dataset.map = key;
    b.addEventListener('click', () => sendRules(S.rules.mode, S.rules.muts, key));
    $('maps').append(b);
  }
  $('rotate').addEventListener('change', () => sendRules(S.rules.mode, S.rules.muts, S.rules.map, $('rotate').checked));
  for (const [key, name] of Object.entries(S.modes)) {
    const b = Object.assign(document.createElement('button'), { type: 'button', textContent: name });
    b.dataset.mode = key;
    b.addEventListener('click', () => sendRules(key, S.rules.muts));
    $('modes').append(b);
  }
  for (const [key, name] of Object.entries(S.mutators)) {
    const label = document.createElement('label');
    const box = Object.assign(document.createElement('input'), { type: 'checkbox' });
    box.dataset.mut = key;
    box.addEventListener('change', () => {
      const muts = S.rules.muts.filter(m => m !== key);
      if (box.checked) muts.push(key);
      sendRules(S.rules.mode, muts);
    });
    label.title = MUT_BLURB[key] || '';
    label.append(box, ` ${name[0].toUpperCase()}${name.slice(1)}`);
    $('muts').append(label);
  }
  drawRulesMenu();
}

function sendRules(mode, muts, map = S.rules && S.rules.map, rotate = S.rules && S.rules.rotate) {
  if (!S.rules) return;
  net.send({ t: 'rules', mode, muts, map, rotate });
}

function drawRulesMenu() {
  const r = S.rules;
  if (!r) return;
  for (const b of $('modes').children) b.classList.toggle('on', b.dataset.mode === r.mode);
  for (const b of $('maps').children) b.classList.toggle('on', b.dataset.map === r.map);
  $('rotate').checked = r.rotate;
  $('map-blurb').textContent = (S.maps[r.map] || [])[1] || '';
  for (const box of $('muts').querySelectorAll('input')) box.checked = r.muts.includes(box.dataset.mut);
  const muts = r.muts.map(m => MUT_BLURB[m]).filter(Boolean).join(' ');
  $('mode-blurb').textContent = `${MODE_BLURB[r.mode] || ''} ${muts}`.trim();
}

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
net.connect(settings.name || '', { token: settings.token, tab });
requestAnimationFrame(frame);
