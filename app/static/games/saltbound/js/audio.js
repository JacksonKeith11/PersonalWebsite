// Sound effects, synthesized with Web Audio when first needed: no audio files.
let ctx = null, master = null, volume = 0.6;
try { volume = JSON.parse(localStorage.getItem('saltbound'))?.settings?.volume ?? 0.6; } catch { /* private mode */ }

function ac() {
  if (!ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return null;
    ctx = new AC();
    master = ctx.createGain();
    master.gain.value = volume * 0.5;
    master.connect(ctx.destination);
  }
  if (ctx.state === 'suspended') ctx.resume();
  return ctx;
}
export function setVolume(v) { volume = v; if (master) master.gain.value = v * 0.5; }

function tone(freq, dur, { type = 'sine', gain = 0.3, slide = 0, delay = 0, attack = 0.005 } = {}) {
  const c = ac(); if (!c) return;
  const t = c.currentTime + delay;
  const o = c.createOscillator(), g = c.createGain();
  o.type = type; o.frequency.setValueAtTime(freq, t);
  if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, freq + slide), t + dur);
  g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(gain, t + attack); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g); g.connect(master); o.start(t); o.stop(t + dur + 0.02);
}
function noise(dur, { gain = 0.2, freq = 1200, q = 0.8, delay = 0, type = 'bandpass' } = {}) {
  const c = ac(); if (!c) return;
  const t = c.currentTime + delay;
  const buf = c.createBuffer(1, Math.ceil(c.sampleRate * dur), c.sampleRate);
  const d = buf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length);
  const src = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain();
  src.buffer = buf; f.type = type; f.frequency.value = freq; f.Q.value = q; g.gain.value = gain;
  src.connect(f); f.connect(g); g.connect(master); src.start(t);
}

const SOUNDS = {
  click: () => tone(880, 0.05, { type: 'triangle', gain: 0.08 }),
  place: () => { tone(520, 0.08, { type: 'triangle', gain: 0.12 }); tone(780, 0.1, { type: 'triangle', gain: 0.08, delay: 0.04 }); },
  dice: () => { for (let i = 0; i < 4; i++) noise(0.04, { gain: 0.15, freq: 2400 + i * 300, delay: i * 0.05 }); },
  swing: () => noise(0.14, { gain: 0.12, freq: 900, q: 0.6 }),
  hit: () => { noise(0.12, { gain: 0.25, freq: 400, q: 1 }); tone(140, 0.12, { type: 'square', gain: 0.06, slide: -60 }); },
  block: () => { tone(1200, 0.08, { type: 'square', gain: 0.05 }); noise(0.06, { gain: 0.1, freq: 3000 }); },
  heal: () => { tone(660, 0.18, { gain: 0.1 }); tone(990, 0.22, { gain: 0.08, delay: 0.06 }); },
  die: () => tone(220, 0.35, { type: 'sawtooth', gain: 0.07, slide: -150 }),
  step: () => noise(0.05, { gain: 0.06, freq: 600 }),
  fight: () => { tone(196, 0.25, { type: 'sawtooth', gain: 0.08 }); tone(147, 0.4, { type: 'sawtooth', gain: 0.08, delay: 0.15 }); },
  level: () => [523, 659, 784, 1047].forEach((f, i) => tone(f, 0.25, { type: 'triangle', gain: 0.1, delay: i * 0.08 })),
  rise: () => { noise(1.2, { gain: 0.12, freq: 300, q: 0.5, type: 'lowpass' }); tone(110, 1.0, { gain: 0.08, slide: -30 }); },
  win: () => [392, 523, 659, 784].forEach((f, i) => tone(f, 0.35, { type: 'triangle', gain: 0.1, delay: i * 0.1 })),
  lose: () => [392, 330, 262].forEach((f, i) => tone(f, 0.4, { type: 'triangle', gain: 0.1, delay: i * 0.15 })),
  error: () => tone(180, 0.12, { type: 'square', gain: 0.05 }),
};
export function play(name) {
  if (volume <= 0) return;
  try { SOUNDS[name]?.(); } catch { /* audio can fail before a user gesture */ }
}
