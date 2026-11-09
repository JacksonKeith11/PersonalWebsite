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
export function setVolume(v) { volume = v; if (master) master.gain.value = v; }
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
  const c = ac(); if (!c) return;
  const t = c.currentTime, s = noise(c), fl = c.createBiquadFilter(), g = c.createGain(), p = c.createStereoPanner();
  fl.type = type; fl.Q.value = q;
  fl.frequency.setValueAtTime(f0, t); fl.frequency.exponentialRampToValueAtTime(f1, t + dur);
  env(c, g, t, 0.01, peak, dur); p.pan.value = pan;
  s.connect(fl).connect(g).connect(p).connect(master);
  s.start(t, Math.random() * 0.5); s.stop(t + dur + 0.05);
}

function tone(type, f0, f1, dur, peak, delay = 0, pan = 0) {
  const c = ac(); if (!c) return;
  const t = c.currentTime + delay, o = c.createOscillator(), g = c.createGain(), p = c.createStereoPanner();
  o.type = type; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), t + dur);
  env(c, g, t, 0.005, peak, dur); p.pan.value = pan;
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
    else { tone('triangle', 260, 240, 0.08, 0.1, 0, pan); }
  },
  heal: () => { tone('sine', 520, 520, 0.4, 0.15); tone('sine', 780, 780, 0.5, 0.12, 0.08); tone('sine', 1040, 1040, 0.6, 0.08, 0.16); },
  down: () => { tone('sawtooth', 300, 60, 0.9, 0.3); },
  revive: () => { tone('sine', 400, 800, 0.5, 0.2); tone('sine', 600, 1200, 0.6, 0.12, 0.1); },
  stagger: (pan) => { tone('square', 200, 80, 0.4, 0.3, 0, pan); hiss(1000, 200, 0.6, 0.4, 0.4, 'bandpass', pan); },
  bossDown: () => { tone('sine', 110, 40, 2.5, 0.6); hiss(600, 60, 0.5, 2.5, 0.5, 'lowpass'); tone('triangle', 330, 330, 2, 0.12, 0.6); tone('triangle', 440, 440, 2, 0.1, 0.9); tone('triangle', 660, 660, 2, 0.08, 1.2); },
  wipe: () => { tone('sawtooth', 220, 55, 2.2, 0.35); tone('sawtooth', 233, 58, 2.2, 0.25); },
  ui: () => tone('triangle', 660, 660, 0.06, 0.08),
  uiBack: () => tone('triangle', 440, 440, 0.06, 0.08),
};
