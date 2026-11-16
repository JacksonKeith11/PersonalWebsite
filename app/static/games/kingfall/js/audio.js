// Every sound, synthesized with Web Audio as it plays (no files), like the site's other games.
let ctx = null, master = null;
export let volume = 0.6;

function ac() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    master = ctx.createGain(); master.gain.value = volume; master.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}
export function setVolume(v) { volume = Number.isFinite(v) ? v : 0.6; if (master) master.gain.value = volume; }
export function audioOut() { return ac() ? { ctx, master } : null; }
export function unlock() { ac(); }

let noiseBuf = null;
function noise(c) {
  if (!noiseBuf) {
    noiseBuf = c.createBuffer(1, c.sampleRate, c.sampleRate);
    const d = noiseBuf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  }
  const s = c.createBufferSource(); s.buffer = noiseBuf; return s;
}

function env(c, g, t, a, peak, dur) {
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(peak, t + a);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
}

// filtered noise: whooshes, impacts, fire
function hiss(f0, f1, q, dur, peak, type = 'bandpass', pan = 0) {
  const c = ac(); if (!c || !(dur > 0) || ![f0, f1, peak].every(Number.isFinite)) return;
  const t = c.currentTime, s = noise(c), fl = c.createBiquadFilter(), g = c.createGain(), p = c.createStereoPanner();
  fl.type = type; fl.Q.value = q;
  fl.frequency.setValueAtTime(f0, t); fl.frequency.exponentialRampToValueAtTime(f1, t + dur);
  env(c, g, t, 0.01, peak, dur); p.pan.value = Number.isFinite(pan) ? Math.max(-1, Math.min(1, pan)) : 0;  // a place not known yet plays in the middle
  s.connect(fl).connect(g).connect(p).connect(master);
  s.start(t, Math.random() * 0.5); s.stop(t + dur + 0.05);
}

function tone(type, f0, f1, dur, peak, delay = 0, pan = 0) {
  const c = ac(); if (!c || !(dur > 0) || ![f0, f1, peak].every(Number.isFinite)) return;
  const t = c.currentTime + delay, o = c.createOscillator(), g = c.createGain(), p = c.createStereoPanner();
  o.type = type; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), t + dur);
  env(c, g, t, 0.005, peak, dur); p.pan.value = Number.isFinite(pan) ? Math.max(-1, Math.min(1, pan)) : 0;
  o.connect(g).connect(p).connect(master); o.start(t); o.stop(t + dur + 0.05);
}

export const sfx = {
  swing: (pan) => hiss(900, 2600, 1.2, 0.16, 0.25, 'bandpass', pan),
  heavySwing: (pan) => { hiss(400, 1600, 1, 0.3, 0.35, 'bandpass', pan); },
  hit: (pan) => { hiss(2400, 500, 0.8, 0.12, 0.5, 'bandpass', pan); tone('square', 160, 60, 0.12, 0.25, 0, pan); },
  crit: (pan) => { hiss(3000, 400, 0.7, 0.25, 0.7, 'bandpass', pan); tone('sawtooth', 220, 50, 0.3, 0.35, 0, pan); tone('sine', 880, 440, 0.4, 0.15, 0.02, pan); },
  clang: (pan) => { tone('triangle', 1400, 1300, 0.35, 0.28, 0, pan); tone('triangle', 2150, 2000, 0.3, 0.16, 0, pan); hiss(5000, 3000, 2, 0.08, 0.25, 'highpass', pan); },
  parry: (pan) => { tone('triangle', 1800, 1750, 0.6, 0.35, 0, pan); tone('sine', 2700, 2600, 0.7, 0.2, 0.01, pan); tone('sine', 900, 880, 0.5, 0.15, 0, pan); },
  guarded: (pan) => { tone('square', 300, 200, 0.12, 0.2, 0, pan); hiss(3000, 1500, 2, 0.08, 0.3, 'bandpass', pan); },
  roll: (pan) => hiss(300, 700, 0.8, 0.22, 0.22, 'lowpass', pan),
  hurt: (pan) => { tone('sawtooth', 220, 90, 0.18, 0.3, 0, pan); hiss(1500, 300, 1, 0.15, 0.4, 'bandpass', pan); },
  slam: (pan) => { tone('sine', 90, 30, 0.5, 0.7, 0, pan); hiss(800, 80, 0.7, 0.45, 0.6, 'lowpass', pan); },
  bossSwing: (pan) => hiss(500, 1800, 0.9, 0.3, 0.4, 'bandpass', pan),
  fire: (pan) => hiss(1200, 300, 0.5, 0.6, 0.35, 'bandpass', pan),
  // each telegraph has its own sound, so you can learn moves by ear
  tell: (kind, pan) => {
    if (kind === 'charge') { tone('sawtooth', 70, 110, 0.5, 0.25, 0, pan); hiss(200, 900, 1, 0.5, 0.2, 'bandpass', pan); }
    else if (kind === 'delayed') { tone('sine', 300, 600, 0.9, 0.12, 0, pan); hiss(2000, 6000, 3, 0.9, 0.06, 'bandpass', pan); }
    else if (kind === 'guard') { tone('square', 120, 110, 0.15, 0.2, 0, pan); }
    else if (kind === 'embers' || kind === 'phase2') { hiss(300, 2000, 0.6, 0.7, 0.3, 'bandpass', pan); tone('sawtooth', 55, 110, 0.7, 0.2, 0, pan); }
  },
  // A boss's attacks, one sound per kind of hit (boss.js plays them as each hit starts), sized by the
  // hit: a bigger swing whooshes lower, a bigger slam thumps deeper. `fire` adds a roar of flame,
  // `heavy` (it can't be blocked) a low growl under it.
  boss: {
    // the wind-up: a breath drawn in that rises until the strike (dur = how long that is)
    windup: (pan, dur, heavy) => { hiss(180, heavy ? 700 : 1100, 1.4, dur, heavy ? 0.16 : 0.1, 'bandpass', pan); if (heavy) tone('sawtooth', 48, 82, dur, 0.14, 0, pan); },
    // the glint just before the first strike: a bright ping, or a sour low one if it can't be blocked
    glint: (pan, heavy) => heavy ? (tone('square', 196, 185, 0.22, 0.16, 0, pan), tone('square', 277, 262, 0.22, 0.12, 0, pan))
      : (tone('triangle', 1560, 1500, 0.16, 0.14, 0, pan), tone('sine', 2340, 2300, 0.12, 0.07, 0, pan)),
    arc: (pan, size, o) => { const k = Math.max(0.5, Math.min(1.6, 60 / size)); hiss(380 * k, 1900 * k, 0.9, 0.26, 0.5, 'bandpass', pan); tone('sine', 130 * k, 60, 0.2, 0.22, 0.02, pan); sfx.boss.extra(pan, o); },
    rect: (pan, size, o) => { hiss(1400, 3600, 1.6, 0.14, 0.42, 'bandpass', pan); hiss(300, 900, 0.8, 0.22, 0.3, 'bandpass', pan); tone('triangle', 240, 90, 0.16, 0.2, 0, pan); sfx.boss.extra(pan, o); },
    circle: (pan, size, o) => { const k = Math.max(0.6, Math.min(1.5, 40 / size)); tone('sine', 105 * k, 32, 0.45, 0.75, 0, pan); hiss(900, 70, 0.7, 0.4, 0.55, 'lowpass', pan); hiss(2600, 900, 1.5, 0.08, 0.25, 'bandpass', pan); sfx.boss.extra(pan, o); },
    ring: (pan, size, o) => { tone('sine', 70, 34, 0.7, 0.6, 0, pan); hiss(240, 2200, 0.6, 0.75, 0.38, 'bandpass', pan); tone('triangle', 196, 185, 0.6, 0.12, 0, pan); sfx.boss.extra(pan, o); },
    proj: (pan, size, o) => { const k = Math.max(0.6, Math.min(1.6, 7 / size)); tone('sawtooth', 620 * k, 170 * k, 0.2, 0.16, 0, pan); hiss(2600 * k, 700, 1.2, 0.2, 0.3, 'bandpass', pan); sfx.boss.extra(pan, o); },
    zone: (pan, size, o) => { hiss(500, 1600, 2.5, 0.5, 0.28, 'bandpass', pan); tone('sine', 150, 260, 0.12, 0.14, 0.05, pan); tone('sine', 210, 330, 0.1, 0.12, 0.2, pan); tone('sine', 170, 300, 0.1, 0.1, 0.33, pan); sfx.boss.extra(pan, o); },
    spawn: (pan) => { tone('sine', 300, 620, 0.3, 0.16, 0, pan); tone('sine', 450, 930, 0.3, 0.1, 0.08, pan); hiss(800, 2400, 2, 0.3, 0.12, 'bandpass', pan); },
    // a called-down area landing on its mark (a pillar, a lobbed flask, a falling bell)
    land: (pan, size, o) => { tone('sine', 150, 40, 0.35, 0.6, 0, pan); hiss(3200, 400, 0.8, 0.3, 0.5, 'bandpass', pan); sfx.boss.extra(pan, o); },
    extra: (pan, o) => {
      if (!o) return;
      if (o.fire) hiss(1400, 260, 0.5, 0.55, 0.3, 'bandpass', pan);
      if (o.heavy) tone('sawtooth', 62, 40, 0.4, 0.22, 0, pan);
    },
  },
  // A hero's hit landing, by weapon, so each feels different in the hand: the sword's ring, the
  // greatsword's thud, the daggers' quick ticks, the halberd's crack, an arrow's thunk, the catalyst's
  // crackle. `big`: a heavy or a special.
  hitBy: (weapon, pan, big) => {
    switch (weapon) {
      case 'greatsword': tone('sine', big ? 95 : 120, 36, big ? 0.34 : 0.22, big ? 0.6 : 0.42, 0, pan); hiss(1400, 180, 0.7, big ? 0.3 : 0.2, 0.5, 'lowpass', pan); tone('square', 150, 70, 0.1, 0.16, 0, pan); break;
      case 'daggers': hiss(5200, 2400, 2.2, 0.05, 0.4, 'bandpass', pan); tone('triangle', 1900 + Math.random() * 500, 900, 0.05, 0.14, 0, pan); if (big) hiss(3000, 900, 1.2, 0.14, 0.4, 'bandpass', pan); break;
      case 'halberd': hiss(2000, 600, 1, 0.14, 0.5, 'bandpass', pan); tone('triangle', 520, 240, 0.12, 0.2, 0, pan); tone('square', 130, 60, big ? 0.2 : 0.1, 0.22, 0, pan); break;
      case 'bow': tone('sine', 210, 90, 0.09, 0.4, 0, pan); hiss(1800, 500, 1.4, 0.07, 0.35, 'bandpass', pan); if (big) tone('triangle', 420, 160, 0.16, 0.18, 0, pan); break;
      case 'catalyst': tone('sawtooth', 1300, 320, 0.14, 0.12, 0, pan); tone('sine', 660, 990, 0.16, 0.14, 0.02, pan); hiss(4200, 1600, 3, 0.12, 0.2, 'bandpass', pan); if (big) tone('sine', 110, 50, 0.3, 0.4, 0, pan); break;
      default: hiss(2600, 600, 0.9, 0.11, 0.48, 'bandpass', pan); tone('square', 170, 70, 0.1, 0.2, 0, pan); tone('triangle', 1250, 1150, big ? 0.22 : 0.12, 0.1, 0, pan);
    }
  },
  // a footfall, by floor: stone taps, mud squelches, grass and dirt scuff, glass ticks. `vol` 0..1 (others' are quieter)
  step: (floor, pan, vol = 1) => {
    const j = 0.85 + Math.random() * 0.3;
    if (floor === 'mud') { hiss(500 * j, 160, 1.2, 0.09, 0.11 * vol, 'lowpass', pan); tone('sine', 150 * j, 90, 0.06, 0.05 * vol, 0, pan); }
    else if (floor === 'grass') hiss(2600 * j, 1200, 0.8, 0.07, 0.07 * vol, 'bandpass', pan);
    else if (floor === 'dirt') hiss(900 * j, 400, 0.8, 0.06, 0.09 * vol, 'bandpass', pan);
    else if (floor === 'glass') { tone('triangle', 2300 * j, 2000, 0.05, 0.035 * vol, 0, pan); hiss(4200, 2600, 2, 0.03, 0.05 * vol, 'bandpass', pan); }
    else { hiss(1500 * j, 600, 1.4, 0.045, 0.1 * vol, 'bandpass', pan); tone('sine', 120 * j, 70, 0.04, 0.05 * vol, 0, pan); }
  },
  // a heartbeat while this browser's hero is close to falling
  heart: () => { tone('sine', 62, 40, 0.14, 0.4); tone('sine', 56, 38, 0.16, 0.3, 0.16); },
  // a hit rolled clean through: a quick bright whisper
  perfect: (pan) => { tone('sine', 1560, 2100, 0.16, 0.1, 0, pan); tone('sine', 2340, 3100, 0.14, 0.05, 0.03, pan); hiss(3000, 7000, 2, 0.16, 0.1, 'bandpass', pan); },
  // a boss's body coming to rest
  collapse: (pan, big) => { tone('sine', big ? 70 : 95, 30, 0.5, 0.6, 0, pan); hiss(700, 70, 0.7, 0.5, 0.5, 'lowpass', pan); hiss(2200, 500, 1, 0.12, 0.2, 'bandpass', pan); },
  shatter: (pan) => { for (let i = 0; i < 6; i++) tone('triangle', 1800 + Math.random() * 2600, 1400, 0.25, 0.08, i * 0.035, pan); hiss(6000, 2500, 1.5, 0.3, 0.3, 'highpass', pan); },
  heal: () => { tone('sine', 520, 520, 0.4, 0.15); tone('sine', 780, 780, 0.5, 0.12, 0.08); tone('sine', 1040, 1040, 0.6, 0.08, 0.16); },
  down: () => { tone('sawtooth', 300, 60, 0.9, 0.3); },
  revive: () => { tone('sine', 400, 800, 0.5, 0.2); tone('sine', 600, 1200, 0.6, 0.12, 0.1); },
  stagger: (pan) => { tone('square', 200, 80, 0.4, 0.3, 0, pan); hiss(1000, 200, 0.6, 0.4, 0.4, 'bandpass', pan); },
  bossDown: () => { tone('sine', 110, 40, 2.5, 0.6); hiss(600, 60, 0.5, 2.5, 0.5, 'lowpass'); tone('triangle', 330, 330, 2, 0.12, 0.6); tone('triangle', 440, 440, 2, 0.1, 0.9); tone('triangle', 660, 660, 2, 0.08, 1.2); },
  // the big moments: a deep bell under a boss's name card, a rising roar as it changes phase, a bright sting for a parry
  gong: () => { tone('sine', 82, 78, 3.2, 0.5); tone('triangle', 164, 160, 2.6, 0.18, 0.01); tone('sine', 247, 244, 2.2, 0.1, 0.02); tone('sine', 415, 410, 1.6, 0.05, 0.03); hiss(300, 80, 0.6, 1.2, 0.25, 'lowpass'); },
  roar: () => { hiss(120, 900, 0.7, 0.9, 0.55, 'lowpass'); tone('sawtooth', 55, 90, 0.9, 0.3); tone('sawtooth', 58, 95, 0.9, 0.22, 0.02); hiss(900, 200, 1, 1.4, 0.3, 'bandpass'); },
  sting: (pan) => { tone('sine', 1320, 1300, 0.5, 0.18, 0, pan); tone('sine', 1980, 1960, 0.45, 0.1, 0.02, pan); },
  wipe: () => { tone('sawtooth', 220, 55, 2.2, 0.35); tone('sawtooth', 233, 58, 2.2, 0.25); },
  ui: () => tone('triangle', 660, 660, 0.06, 0.08),
  uiBack: () => tone('triangle', 440, 440, 0.06, 0.08),
};

// Each arena's own quiet sound under the music: a bed of filtered noise that swells and falls (wind, a
// hall's hush, a fire's roar) and small sounds at random (drips, crackles, bubbles, chimes, rustles).
// `floor` is what footsteps sound like there.
export const PLACE = {
  chapel:   { floor: 'stone', bed: [260, 0.6, 0.035, 'lowpass'], bits: ['crackle'], every: 1.6 },
  bog:      { floor: 'mud',   bed: [420, 0.7, 0.03, 'lowpass'], bits: ['bubble', 'drip'], every: 1.3 },
  belfry:   { floor: 'stone', bed: [700, 1.6, 0.05, 'bandpass'], bits: ['creak'], every: 5 },
  yard:     { floor: 'dirt',  bed: [520, 1.0, 0.04, 'bandpass'], bits: ['rustle'], every: 4 },
  forest:   { floor: 'grass', bed: [1500, 0.7, 0.035, 'bandpass'], bits: ['rustle', 'creak'], every: 2.2 },
  lab:      { floor: 'stone', bed: [300, 0.6, 0.03, 'lowpass'], bits: ['bubble', 'bubble', 'drip'], every: 0.9 },
  boneyard: { floor: 'dirt',  bed: [380, 2.4, 0.05, 'bandpass'], bits: ['rustle'], every: 5 },
  glass:    { floor: 'glass', bed: [2400, 2.0, 0.02, 'bandpass'], bits: ['chime'], every: 1.8 },
  wall:     { floor: 'stone', bed: [600, 0.8, 0.05, 'bandpass'], bits: ['crackle', 'crackle'], every: 0.7 },
  sanctum:  { floor: 'stone', bed: [240, 0.6, 0.03, 'lowpass'], bits: ['crackle', 'chime'], every: 2.2 },
  throne:   { floor: 'stone', bed: [180, 0.8, 0.045, 'lowpass'], bits: ['drip', 'creak'], every: 4 },
  bridge:   { floor: 'stone', bed: [480, 0.9, 0.06, 'bandpass'], bits: ['crackle', 'crackle'], every: 0.5 },
};
const BITS = {
  drip: pan => { tone('sine', 1100 + Math.random() * 500, 520, 0.07, 0.05, 0, pan); tone('sine', 700, 1300, 0.05, 0.03, 0.08, pan); },
  crackle: pan => { hiss(3200 + Math.random() * 2500, 1500, 3, 0.025, 0.07, 'bandpass', pan); if (Math.random() < 0.4) hiss(2400, 1200, 2, 0.02, 0.05, 'bandpass', pan); },
  bubble: pan => { const f = 160 + Math.random() * 240; tone('sine', f, f * 2.1, 0.08, 0.05, 0, pan); },
  chime: pan => { const f = [1568, 1760, 2093, 2349, 2637][Math.floor(Math.random() * 5)]; tone('sine', f, f * 0.995, 0.9, 0.022, 0, pan); },
  rustle: pan => hiss(1800 + Math.random() * 1200, 3600, 0.8, 0.5 + Math.random() * 0.5, 0.03, 'bandpass', pan),
  creak: pan => { const f = 90 + Math.random() * 60; tone('sawtooth', f, f * 1.25, 0.5, 0.018, 0, pan); },
};
export const ambience = {
  P: null, src: null, gain: null, next: 0, swell: 0,
  start(arena) {
    this.stop();
    const c = ac(), P = PLACE[arena];
    if (!c || !P) return;
    const [f, q, vol, type] = P.bed;
    const s = noise(c), fl = c.createBiquadFilter(), g = c.createGain();
    s.loop = true; fl.type = type; fl.frequency.value = f; fl.Q.value = q; g.gain.value = 0.0001;
    s.connect(fl).connect(g).connect(master); s.start();
    g.gain.setTargetAtTime(vol, c.currentTime, 1.2);
    this.P = P; this.src = s; this.gain = g; this.next = 1 + Math.random() * P.every; this.swell = 2;
  },
  // once a frame: the bed swells and falls, and now and then a small sound somewhere in the room
  tick(dt) {
    const P = this.P;
    if (!P || !ctx) return;
    this.swell -= dt;
    if (this.swell <= 0) { this.swell = 2 + Math.random() * 3; this.gain.gain.setTargetAtTime(P.bed[2] * (0.5 + Math.random()), ctx.currentTime, 1.5); }
    this.next -= dt;
    if (this.next <= 0) { this.next = P.every * (0.4 + Math.random() * 1.2); BITS[P.bits[Math.floor(Math.random() * P.bits.length)]](Math.random() * 1.6 - 0.8); }
  },
  stop() {
    if (this.src) {
      const s = this.src, g = this.gain;
      try { g.gain.setTargetAtTime(0.0001, ctx.currentTime, 0.3); s.stop(ctx.currentTime + 1.2); } catch (e) { /* already stopped */ }
    }
    this.P = this.src = this.gain = null;
  },
};
