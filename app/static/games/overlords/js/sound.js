// Overlords' sounds, all synthesized with Web Audio: nothing to download. `play(name)` makes one;
// hits are rate-limited so a big fight doesn't turn into noise. Muting is remembered.

let ctx = null;
let master = null;
let muted = false;
try { muted = localStorage.getItem('overlords-muted') === '1'; } catch { /* private mode */ }
const lastAt = {};

function audio() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = 0.5;
    master.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}

// browsers only start audio after a click or key
for (const ev of ['pointerdown', 'keydown']) addEventListener(ev, () => audio(), { once: true });

export const isMuted = () => muted;
export function setMuted(m) {
  muted = m;
  try { localStorage.setItem('overlords-muted', m ? '1' : '0'); } catch { /* private mode */ }
}

function tone(freq, start, dur, { type = 'sine', vol = 0.2, to = null, attack = 0.005 } = {}) {
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = type;
  o.frequency.setValueAtTime(freq, start);
  if (to) o.frequency.exponentialRampToValueAtTime(to, start + dur);
  g.gain.setValueAtTime(0.0001, start);
  g.gain.exponentialRampToValueAtTime(vol, start + attack);
  g.gain.exponentialRampToValueAtTime(0.0001, start + dur);
  o.connect(g).connect(master);
  o.start(start);
  o.stop(start + dur + 0.02);
}

let noiseBuf = null;
function noise(start, dur, { vol = 0.2, freq = 1200, q = 1, type = 'bandpass', to = null } = {}) {
  if (!noiseBuf) {
    noiseBuf = ctx.createBuffer(1, ctx.sampleRate * 0.5, ctx.sampleRate);
    const d = noiseBuf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  }
  const src = ctx.createBufferSource();
  src.buffer = noiseBuf;
  const f = ctx.createBiquadFilter();
  f.type = type;
  f.frequency.setValueAtTime(freq, start);
  if (to) f.frequency.exponentialRampToValueAtTime(to, start + dur);
  f.Q.value = q;
  const g = ctx.createGain();
  g.gain.setValueAtTime(vol, start);
  g.gain.exponentialRampToValueAtTime(0.0001, start + dur);
  src.connect(f).connect(g).connect(master);
  src.start(start);
  src.stop(start + dur + 0.02);
}

const SOUNDS = {
  buy: t => { tone(988, t, 0.07, { type: 'square', vol: 0.07 }); tone(1319, t + 0.06, 0.12, { type: 'square', vol: 0.07 }); },
  sell: t => { tone(880, t, 0.07, { type: 'square', vol: 0.06 }); tone(587, t + 0.06, 0.12, { type: 'square', vol: 0.06 }); },
  reroll: t => {
    noise(t, 0.12, { vol: 0.12, freq: 2500, q: 0.8 });
    [523, 659, 784].forEach((f, i) => tone(f, t + 0.04 + i * 0.04, 0.08, { type: 'triangle', vol: 0.08 }));
  },
  level: t => [392, 494, 587, 784].forEach((f, i) => tone(f, t + i * 0.07, 0.25, { type: 'triangle', vol: 0.12 })),
  star: t => {
    for (const [f, d] of [[1047, 0], [1568, 0.08], [2093, 0.16]]) {
      tone(f, t + d, 0.6, { vol: 0.1 });
      tone(f * 2.01, t + d, 0.3, { vol: 0.03 });
    }
  },
  plan: t => { tone(196, t, 0.5, { type: 'sawtooth', vol: 0.05, attack: 0.08 }); tone(294, t + 0.12, 0.5, { type: 'sawtooth', vol: 0.04, attack: 0.08 }); },
  fight: t => {
    for (const d of [0, 0.22]) {
      tone(140, t + d, 0.25, { to: 45, vol: 0.35 });
      noise(t + d, 0.08, { vol: 0.15, freq: 600, type: 'lowpass' });
    }
  },
  hit: t => noise(t, 0.05, { vol: 0.08, freq: 1800 + Math.random() * 1200, q: 2 }),
  shot: t => tone(1400 + Math.random() * 400, t, 0.06, { type: 'triangle', vol: 0.04, to: 700 }),
  crit: t => { noise(t, 0.09, { vol: 0.14, freq: 3200, q: 3 }); tone(220, t, 0.1, { type: 'square', vol: 0.05, to: 110 }); },
  cast: t => { tone(330, t, 0.35, { to: 990, vol: 0.08 }); tone(495, t + 0.05, 0.3, { to: 1485, vol: 0.04, type: 'triangle' }); },
  heal: t => [659, 880].forEach((f, i) => tone(f, t + i * 0.06, 0.25, { vol: 0.06 })),
  stun: t => tone(1200, t, 0.18, { type: 'square', vol: 0.04, to: 300 }),
  death: t => { tone(110, t, 0.3, { to: 40, vol: 0.25 }); noise(t, 0.2, { vol: 0.1, freq: 400, type: 'lowpass' }); },
  rise: t => tone(220, t, 0.5, { to: 660, vol: 0.08, type: 'triangle' }),
  won: t => { tone(523, t, 0.15, { type: 'triangle', vol: 0.12 }); tone(784, t + 0.13, 0.35, { type: 'triangle', vol: 0.12 }); },
  lost: t => { tone(392, t, 0.18, { type: 'triangle', vol: 0.12 }); tone(311, t + 0.16, 0.4, { type: 'triangle', vol: 0.12 }); },
  out: t => [392, 330, 262, 196].forEach((f, i) => tone(f, t + i * 0.16, 0.35, { type: 'sawtooth', vol: 0.06 })),
  victory: t => [523, 659, 784, 1047, 784, 1047].forEach((f, i) => tone(f, t + i * 0.12, i === 5 ? 0.8 : 0.18, { type: 'triangle', vol: 0.12 })),
  click: t => tone(660, t, 0.04, { type: 'square', vol: 0.04 }),
  deny: t => tone(150, t, 0.12, { type: 'square', vol: 0.06 }),
};
// at most this many of a sound a second
const LIMIT = { hit: 14, shot: 14, crit: 6, cast: 6, death: 6, heal: 4, stun: 4, rise: 3 };

export function play(name) {
  if (muted || !SOUNDS[name]) return;
  const c = audio();
  if (!c || c.state !== 'running') return;
  const now = c.currentTime;
  if (LIMIT[name] && now - (lastAt[name] || 0) < 1 / LIMIT[name]) return;
  lastAt[name] = now;
  SOUNDS[name](now + 0.005);
}
