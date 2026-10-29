// Every sound is synthesized when it plays: short tones, sweeps and noise bursts.

let ctx = null, master = null, noiseBuf = null;
let muted = false;
try { muted = localStorage.getItem('brawl-muted') === '1'; } catch { /* private mode */ }

export function unlock() {
  if (ctx) { if (ctx.state === 'suspended') ctx.resume(); return; }
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return;
  ctx = new AC();
  master = ctx.createGain();
  master.gain.value = muted ? 0 : 0.5;
  master.connect(ctx.destination);
  noiseBuf = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
  const d = noiseBuf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
}

export function isMuted() { return muted; }

export function setMuted(m) {
  muted = m;
  try { localStorage.setItem('brawl-muted', m ? '1' : '0'); } catch { /* private mode */ }
  if (master) master.gain.value = m ? 0 : 0.5;
}

function tone(f0, dur, { type = 'square', f1 = f0, vol = 0.2, at = 0, attack = 0.005 } = {}) {
  const t = ctx.currentTime + at;
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = type;
  o.frequency.setValueAtTime(f0, t);
  if (f1 !== f0) o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), t + dur);
  g.gain.setValueAtTime(0.0001, t);
  g.gain.exponentialRampToValueAtTime(vol, t + attack);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  o.connect(g).connect(master);
  o.start(t);
  o.stop(t + dur + 0.02);
}

function noise(dur, { f0 = 1200, f1 = f0, vol = 0.3, at = 0, type = 'lowpass' } = {}) {
  const t = ctx.currentTime + at;
  const src = ctx.createBufferSource();
  src.buffer = noiseBuf;
  const f = ctx.createBiquadFilter();
  f.type = type;
  f.frequency.setValueAtTime(f0, t);
  f.frequency.exponentialRampToValueAtTime(Math.max(30, f1), t + dur);
  const g = ctx.createGain();
  g.gain.setValueAtTime(vol, t);
  g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  src.connect(f).connect(g).connect(master);
  src.start(t);
  src.stop(t + dur + 0.02);
}

const SOUNDS = {
  click: () => tone(660, 0.05, { type: 'triangle', vol: 0.12 }),
  step: () => tone(300 + Math.random() * 60, 0.06, { type: 'triangle', vol: 0.12 }),
  roll: () => { for (let i = 0; i < 8; i++) noise(0.04, { f0: 3000, vol: 0.25, at: i * 0.09 + Math.random() * 0.03, type: 'bandpass' }); },
  dice: () => tone(520, 0.15, { type: 'square', f1: 780, vol: 0.12 }),
  coin: () => { tone(988, 0.07, { vol: 0.1 }); tone(1319, 0.18, { vol: 0.1, at: 0.07 }); },
  lose: () => { tone(330, 0.12, { type: 'sawtooth', vol: 0.1 }); tone(220, 0.25, { type: 'sawtooth', vol: 0.1, at: 0.1 }); },
  crown: () => [523, 659, 784, 1047, 1319].forEach((f, i) => tone(f, 0.25, { type: 'triangle', vol: 0.18, at: i * 0.09 })),
  boo: () => { tone(500, 0.7, { type: 'sine', f1: 160, vol: 0.25, attack: 0.08 }); noise(0.5, { f0: 600, f1: 200, vol: 0.15 }); },
  item: () => { tone(400, 0.2, { type: 'triangle', f1: 1200, vol: 0.15 }); },
  bomb: () => { noise(0.8, { f0: 1500, f1: 60, vol: 0.6 }); tone(90, 0.5, { type: 'sine', f1: 40, vol: 0.4 }); },
  portal: () => { tone(200, 0.6, { type: 'sine', f1: 1400, vol: 0.15 }); tone(300, 0.6, { type: 'sine', f1: 1800, vol: 0.08, at: 0.05 }); },
  web: () => noise(0.3, { f0: 4000, f1: 800, vol: 0.2, type: 'highpass' }),
  trap: () => { noise(0.08, { f0: 5000, vol: 0.4, type: 'highpass' }); tone(150, 0.2, { type: 'square', vol: 0.15 }); },
  gift: () => [784, 988, 1175].forEach((f, i) => tone(f, 0.15, { type: 'triangle', vol: 0.15, at: i * 0.07 })),
  ghost: () => tone(240, 1.2, { type: 'sine', f1: 330, vol: 0.12, attack: 0.3 }),
  duel: () => { tone(220, 0.15, { type: 'sawtooth', vol: 0.15 }); tone(330, 0.3, { type: 'sawtooth', vol: 0.15, at: 0.15 }); },
  turn: () => { tone(660, 0.1, { type: 'triangle', vol: 0.15 }); tone(880, 0.15, { type: 'triangle', vol: 0.15, at: 0.1 }); },
  count: () => tone(440, 0.12, { type: 'square', vol: 0.12 }),
  go: () => tone(880, 0.35, { type: 'square', vol: 0.15 }),
  end: () => [784, 659, 523].forEach((f, i) => tone(f, 0.2, { type: 'square', vol: 0.12, at: i * 0.12 })),
  win: () => [523, 659, 784, 1047].forEach((f, i) => tone(f, 0.3, { type: 'triangle', vol: 0.18, at: i * 0.12 })),
  pop: () => { noise(0.25, { f0: 3000, f1: 300, vol: 0.5 }); tone(200, 0.1, { type: 'square', vol: 0.15 }); },
  pump: () => noise(0.06, { f0: 900, f1: 400, vol: 0.18 }),
  hit: () => { noise(0.1, { f0: 2000, f1: 300, vol: 0.35 }); tone(180, 0.1, { type: 'square', vol: 0.12 }); },
  right: () => { tone(880, 0.08, { type: 'triangle', vol: 0.15 }); tone(1175, 0.15, { type: 'triangle', vol: 0.15, at: 0.08 }); },
  wrong: () => tone(160, 0.25, { type: 'sawtooth', vol: 0.15 }),
  tick: () => tone(1200, 0.03, { type: 'square', vol: 0.06 }),
  splash: () => noise(0.5, { f0: 800, f1: 100, vol: 0.4 }),
  fall: () => tone(600, 0.6, { type: 'sine', f1: 80, vol: 0.2 }),
  kick: () => tone(120, 0.18, { type: 'sine', f1: 45, vol: 0.35 }),
  snare: () => noise(0.12, { f0: 2500, f1: 1200, vol: 0.25, type: 'bandpass' }),
  hat: () => noise(0.04, { f0: 7000, vol: 0.12, type: 'highpass' }),
  note0: () => tone(220, 0.22, { type: 'triangle', vol: 0.18 }),
  note1: () => tone(261.6, 0.22, { type: 'triangle', vol: 0.18 }),
  note2: () => tone(329.6, 0.22, { type: 'triangle', vol: 0.18 }),
  note3: () => tone(392, 0.22, { type: 'triangle', vol: 0.18 }),
  witching: () => { tone(110, 2, { type: 'sawtooth', f1: 55, vol: 0.15, attack: 0.2 }); [0, 0.6, 1.2].forEach(at => tone(196, 0.5, { type: 'sine', vol: 0.15, at })); },
};

export function play(name) {
  if (!ctx || muted || !SOUNDS[name]) return;
  try { SOUNDS[name](); } catch { /* a sound is never worth a crash */ }
}
