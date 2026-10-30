// Every sound is synthesized when it plays: noise bursts, filtered sweeps and a few chimes.
// Sounds placed in the world are panned and quietened by distance from the listener.

let ctx = null, master = null, noiseBuf = null;
const listener = { x: 0, y: 0, z: 0, yaw: 0 };
let volume = 0.7;

export function initAudio() {
  if (ctx) { if (ctx.state === 'suspended') ctx.resume(); return; }
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  ctx = new AC();
  master = ctx.createGain();
  master.gain.value = volume;
  const comp = ctx.createDynamicsCompressor();
  master.connect(comp).connect(ctx.destination);
  noiseBuf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
  const d = noiseBuf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
}

export function setVolume(v) {
  volume = v;
  if (master) master.gain.value = v;
}

export function setListener(x, y, z, yaw) {
  listener.x = x; listener.y = y; listener.z = z; listener.yaw = yaw;
}

function out(pos, gain = 1) {
  const g = ctx.createGain();
  if (!pos) {
    g.gain.value = gain;
    g.connect(master);
    return g;
  }
  const dx = pos[0] - listener.x, dy = pos[1] - listener.y, dz = pos[2] - listener.z;
  const dist = Math.hypot(dx, dy, dz);
  g.gain.value = gain / (1 + dist / 7);
  const pan = ctx.createStereoPanner();
  // right is (cos yaw, -sin yaw) when forward is (-sin yaw, -cos yaw)
  const right = (dx * Math.cos(listener.yaw) - dz * Math.sin(listener.yaw)) / Math.max(dist, 1);
  pan.pan.value = Math.max(-0.8, Math.min(0.8, right));
  g.connect(pan).connect(master);
  return g;
}

function noise(dest, t, dur, { type = 'lowpass', f0 = 2000, f1 = f0, q = 0.7, a = 0.002, peak = 1 } = {}) {
  const src = ctx.createBufferSource();
  src.buffer = noiseBuf;
  src.loop = true;
  const flt = ctx.createBiquadFilter();
  flt.type = type;
  flt.Q.value = q;
  flt.frequency.setValueAtTime(f0, t);
  flt.frequency.exponentialRampToValueAtTime(Math.max(f1, 20), t + dur);
  const env = ctx.createGain();
  env.gain.setValueAtTime(0.0001, t);
  env.gain.exponentialRampToValueAtTime(peak, t + a);
  env.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  src.connect(flt).connect(env).connect(dest);
  src.start(t, Math.random());
  src.stop(t + dur + 0.05);
}

function tone(dest, t, dur, { type = 'sine', f0 = 440, f1 = f0, a = 0.005, peak = 0.5 } = {}) {
  const o = ctx.createOscillator();
  o.type = type;
  o.frequency.setValueAtTime(f0, t);
  o.frequency.exponentialRampToValueAtTime(Math.max(f1, 20), t + dur);
  const env = ctx.createGain();
  env.gain.setValueAtTime(0.0001, t);
  env.gain.exponentialRampToValueAtTime(peak, t + a);
  env.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(env).connect(dest);
  o.start(t);
  o.stop(t + dur + 0.05);
}

const SOUNDS = {
  mg(d, t) {
    noise(d, t, 0.09, { type: 'bandpass', f0: 2600, f1: 900, q: 0.9, peak: 0.9 });
    tone(d, t, 0.05, { type: 'square', f0: 180, f1: 60, peak: 0.25 });
  },
  sg(d, t) {
    noise(d, t, 0.45, { f0: 5000, f1: 200, peak: 1.2 });
    tone(d, t, 0.18, { type: 'triangle', f0: 120, f1: 40, peak: 0.7 });
    noise(d, t + 0.32, 0.06, { type: 'highpass', f0: 3000, peak: 0.25 });  // the pump
  },
  rl(d, t) {
    noise(d, t, 0.5, { type: 'bandpass', f0: 600, f1: 2400, q: 1.2, a: 0.02, peak: 0.8 });
    tone(d, t, 0.25, { type: 'sawtooth', f0: 110, f1: 55, peak: 0.25 });
  },
  rg(d, t) {
    tone(d, t, 0.6, { type: 'sawtooth', f0: 2400, f1: 300, peak: 0.35 });
    tone(d, t, 0.9, { type: 'sine', f0: 880, f1: 870, peak: 0.25 });
    noise(d, t, 0.25, { type: 'highpass', f0: 4000, f1: 1500, peak: 0.4 });
  },
  boom(d, t) {
    noise(d, t, 1.1, { f0: 3000, f1: 80, a: 0.004, peak: 1.6 });
    tone(d, t, 0.6, { type: 'sine', f0: 90, f1: 30, peak: 1.0 });
  },
  jump(d, t) { tone(d, t, 0.12, { type: 'triangle', f0: 220, f1: 330, peak: 0.15 }); },
  land(d, t) { noise(d, t, 0.12, { f0: 400, f1: 100, peak: 0.4 }); },
  pad(d, t) {
    tone(d, t, 0.5, { type: 'sawtooth', f0: 150, f1: 900, a: 0.02, peak: 0.25 });
    noise(d, t, 0.4, { type: 'bandpass', f0: 500, f1: 3000, q: 2, peak: 0.4 });
  },
  health(d, t) {
    tone(d, t, 0.25, { f0: 660, peak: 0.3 });
    tone(d, t + 0.08, 0.3, { f0: 990, peak: 0.3 });
  },
  mega(d, t) {
    for (const [i, f] of [523, 659, 784, 1047].entries()) tone(d, t + i * 0.06, 0.6, { type: 'triangle', f0: f, peak: 0.25 });
  },
  armor(d, t) {
    noise(d, t, 0.3, { type: 'bandpass', f0: 1800, q: 6, peak: 0.6 });
    tone(d, t, 0.4, { type: 'square', f0: 330, f1: 320, peak: 0.12 });
  },
  ammo(d, t) {
    noise(d, t, 0.05, { type: 'highpass', f0: 2500, peak: 0.5 });
    noise(d, t + 0.09, 0.05, { type: 'highpass', f0: 2000, peak: 0.5 });
  },
  hit(d, t, amount = 20) {
    tone(d, t, 0.08, { type: 'square', f0: 1400 - Math.min(amount, 100) * 6, peak: 0.18 });
  },
  frag(d, t) {
    tone(d, t, 0.15, { type: 'triangle', f0: 880, peak: 0.3 });
    tone(d, t + 0.1, 0.35, { type: 'triangle', f0: 1320, peak: 0.3 });
  },
  hurt(d, t) {
    tone(d, t, 0.18, { type: 'sawtooth', f0: 160, f1: 90, peak: 0.3 });
    noise(d, t, 0.12, { f0: 900, f1: 200, peak: 0.4 });
  },
  die(d, t) { tone(d, t, 0.8, { type: 'sawtooth', f0: 300, f1: 40, peak: 0.35 }); },
  spawn(d, t) {
    tone(d, t, 0.5, { type: 'sine', f0: 300, f1: 1200, a: 0.05, peak: 0.25 });
    noise(d, t, 0.5, { type: 'bandpass', f0: 4000, f1: 8000, q: 3, a: 0.05, peak: 0.25 });
  },
  empty(d, t) { noise(d, t, 0.03, { type: 'highpass', f0: 3000, peak: 0.3 }); },
  switch(d, t) {
    noise(d, t, 0.04, { type: 'bandpass', f0: 1500, q: 3, peak: 0.3 });
    noise(d, t + 0.07, 0.04, { type: 'bandpass', f0: 1100, q: 3, peak: 0.3 });
  },
  msg(d, t) { tone(d, t, 0.1, { type: 'sine', f0: 700, peak: 0.12 }); },

  // power weapons
  vx(d, t) {
    tone(d, t, 0.5, { type: 'sawtooth', f0: 90, f1: 400, peak: 0.3 });
    tone(d, t, 0.5, { type: 'sine', f0: 300, f1: 60, peak: 0.4 });
  },
  vortex(d, t) {
    // a low wobbling drone, as long as the black hole lasts
    const o = ctx.createOscillator(), lfo = ctx.createOscillator(), depth = ctx.createGain(), env = ctx.createGain();
    o.type = 'sawtooth';
    o.frequency.value = 55;
    lfo.frequency.value = 7;
    depth.gain.value = 25;
    lfo.connect(depth).connect(o.frequency);
    const flt = ctx.createBiquadFilter();
    flt.type = 'lowpass';
    flt.frequency.value = 500;
    env.gain.setValueAtTime(0.0001, t);
    env.gain.exponentialRampToValueAtTime(0.5, t + 0.3);
    env.gain.setValueAtTime(0.5, t + 2.3);
    env.gain.exponentialRampToValueAtTime(0.0001, t + 2.7);
    o.connect(flt).connect(env).connect(d);
    o.start(t); lfo.start(t); o.stop(t + 2.8); lfo.stop(t + 2.8);
  },
  io(d, t) {
    tone(d, t, 0.6, { type: 'square', f0: 200, f1: 900, a: 0.05, peak: 0.15 });
    noise(d, t, 0.5, { type: 'bandpass', f0: 3000, f1: 6000, q: 4, peak: 0.4 });
  },
  zap(d, t) {
    for (let i = 0; i < 4; i++) noise(d, t + i * 0.02, 0.03, { type: 'highpass', f0: 2000 + Math.random() * 3000, peak: 0.5 });
  },
  sw(d, t) {
    tone(d, t, 0.35, { type: 'sine', f0: 400, f1: 2400, peak: 0.3 });
    tone(d, t + 0.05, 0.35, { type: 'triangle', f0: 2400, f1: 400, peak: 0.2 });
  },
  swap(d, t) {
    noise(d, t, 0.4, { type: 'bandpass', f0: 6000, f1: 800, q: 3, peak: 0.5 });
    tone(d, t, 0.4, { type: 'sine', f0: 1500, f1: 200, peak: 0.3 });
  },
  yt(d, t) {
    tone(d, t, 0.35, { type: 'sine', f0: 140, f1: 35, peak: 1.0 });
    noise(d, t, 0.3, { f0: 1500, f1: 100, peak: 1.0 });
    tone(d, t + 0.05, 0.4, { type: 'square', f0: 900, f1: 1800, peak: 0.08 });  // the "yeet"
  },
  kn(d, t) {  // a knife swish
    noise(d, t, 0.14, { type: 'bandpass', f0: 1200, f1: 5000, q: 1.5, peak: 0.6 });
  },
  infect(d, t) {  // a growl
    tone(d, t, 0.6, { type: 'sawtooth', f0: 90, f1: 55, peak: 0.35 });
    noise(d, t, 0.5, { type: 'lowpass', f0: 500, f1: 200, peak: 0.4 });
  },
  rankup(d, t) {  // Gun Game: on to the next weapon
    for (const [i, f] of [523, 659, 784].entries()) tone(d, t + i * 0.06, 0.25, { type: 'triangle', f0: f, peak: 0.18 });
  },
  powerup(d, t) {
    for (const [i, f] of [392, 523, 659, 784, 1047].entries()) tone(d, t + i * 0.07, 0.4, { type: 'square', f0: f, peak: 0.1 });
  },
  power(d, t) {
    for (const [i, f] of [523, 784, 1047, 1568].entries()) tone(d, t + i * 0.05, 0.7, { type: 'sawtooth', f0: f, peak: 0.12 });
    noise(d, t, 0.6, { type: 'bandpass', f0: 2000, f1: 8000, q: 2, peak: 0.3 });
  },
};

// Play a sound; `pos` places it in the world, otherwise it plays in your head.
export function sfx(name, pos = null, gain = 1, arg) {
  if (!ctx || ctx.state !== 'running' || !SOUNDS[name]) return;
  const dest = out(pos, gain);
  SOUNDS[name](dest, ctx.currentTime + 0.005, arg);
}
