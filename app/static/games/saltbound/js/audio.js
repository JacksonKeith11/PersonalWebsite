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

// ------------------------------------------------------------------ music
// Two loops synthesized on the fly, scheduled a little ahead of time: a calm one for the map and
// menus (D dorian, slow pads, a lilting arpeggio, the sea breathing underneath) and a driving one
// for fights (kick, snare, pulsing bass, a minor-key lead). Browsers only allow sound after the
// first click or key press, so music waits for one.
let musicVol = 0.5, musicBus = null, mode = null, timer = null, nextAt = 0, step = 0, unlocked = false;
try { musicVol = JSON.parse(localStorage.getItem('saltbound'))?.settings?.music ?? 0.5; } catch { /* private mode */ }

const N = n => 440 * Math.pow(2, (n - 69) / 12); // midi note -> Hz
const SONGS = {
  map: {
    bpm: 76, steps: 128, // 8 bars of 16ths
    chords: [[50, 57, 62, 65], [46, 53, 58, 62], [53, 57, 60, 65], [48, 55, 60, 64]], // Dm Bb F C
    arp: [0, 2, 3, 1, 2, 3, 2, 1],
  },
  fight: {
    bpm: 128, steps: 64,
    chords: [[50, 57, 62, 65], [48, 55, 60, 64], [46, 53, 58, 62], [45, 52, 57, 61]], // Dm C Bb A
    arp: [0, 3, 2, 3, 1, 3, 2, 3],
  },
};

function bus() {
  const c = ac(); if (!c) return null;
  if (!musicBus) {
    musicBus = c.createGain();
    musicBus.gain.value = musicVol * 0.35;
    const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 5000;
    musicBus.connect(lp); lp.connect(c.destination);
  }
  return musicBus;
}
function mtone(freq, t, dur, { type = 'sine', gain = 0.2, attack = 0.01, release = 0.2, detune = 0 } = {}) {
  const c = ctx, o = c.createOscillator(), g = c.createGain();
  o.type = type; o.frequency.value = freq; o.detune.value = detune;
  g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(gain, t + attack);
  g.gain.setValueAtTime(gain, t + Math.max(attack, dur - release)); g.gain.linearRampToValueAtTime(0, t + dur);
  o.connect(g); g.connect(musicBus); o.start(t); o.stop(t + dur + 0.05);
}
function mnoise(t, dur, { gain = 0.1, freq = 800, type = 'bandpass', q = 1 } = {}) {
  const c = ctx, buf = c.createBuffer(1, Math.ceil(c.sampleRate * dur), c.sampleRate), d = buf.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  const src = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain();
  src.buffer = buf; f.type = type; f.frequency.value = freq; f.Q.value = q;
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(gain, t + Math.min(0.02, dur / 3)); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  src.connect(f); f.connect(g); g.connect(musicBus); src.start(t);
}

function playStep(song, i, t) {
  const sixteenth = 60 / song.bpm / 4;
  const bar = Math.floor(i / 16) % song.chords.length, chord = song.chords[bar], pos = i % 16;
  if (mode === 'map') {
    if (pos === 0) chord.forEach((n, k) => mtone(N(n), t, sixteenth * 16, { type: k ? 'triangle' : 'sine', gain: 0.05, attack: 0.6, release: 0.8, detune: k % 2 ? 6 : -6 }));
    if (pos % 2 === 0) mtone(N(chord[song.arp[(pos / 2) % 8]] + 12), t, sixteenth * 2.5, { type: 'triangle', gain: 0.045, attack: 0.005, release: 0.25 });
    if (pos === 0 && bar % 2 === 0) mnoise(t, sixteenth * 28, { gain: 0.035, freq: 400, type: 'lowpass' });
    if (pos === 8 && (i / 16) % 4 === 3) mtone(N(chord[3] + 24), t, sixteenth * 6, { gain: 0.03, attack: 0.05, release: 0.4 });
  } else {
    if (pos % 4 === 0) { mtone(110, t, 0.18, { gain: 0.25, attack: 0.002, release: 0.15 }); mtone(55, t, 0.2, { gain: 0.2, attack: 0.002, release: 0.18 }); }
    if (pos === 4 || pos === 12) mnoise(t, 0.16, { gain: 0.12, freq: 1800, q: 0.7 });
    if (pos % 2 === 1) mnoise(t, 0.04, { gain: 0.04, freq: 7000, type: 'highpass' });
    if (pos % 2 === 0) mtone(N(chord[0] - 12), t, sixteenth * 1.8, { type: 'sawtooth', gain: 0.05, attack: 0.005, release: 0.08 });
    if (pos === 0) chord.forEach(n => mtone(N(n), t, sixteenth * 15, { type: 'triangle', gain: 0.025, attack: 0.05, release: 0.3 }));
    if ([0, 3, 6, 8, 11, 14].includes(pos)) mtone(N(chord[song.arp[pos % 8]] + 12), t, sixteenth * 1.5, { type: 'square', gain: 0.025, attack: 0.003, release: 0.08 });
  }
}

function tick() {
  if (!ctx || !mode) return;
  const song = SONGS[mode], sixteenth = 60 / song.bpm / 4;
  while (nextAt < ctx.currentTime + 0.25) {
    playStep(song, step, nextAt);
    step = (step + 1) % song.steps;
    nextAt += sixteenth;
  }
}

export function music(want) {
  if (want === mode) return;
  mode = want;
  if (!unlocked || !want || musicVol <= 0) return;
  if (!bus()) return;
  step = 0;
  nextAt = ctx.currentTime + 0.1;
  if (!timer) timer = setInterval(tick, 80);
}
export function setMusicVolume(v) {
  musicVol = v;
  if (musicBus) musicBus.gain.value = v * 0.35;
  if (v > 0 && mode && unlocked && !timer) { const m = mode; mode = null; music(m); }
}
function unlock() {
  if (unlocked) return;
  unlocked = true;
  const m = mode; mode = null;
  if (m) music(m);
}
addEventListener('pointerdown', unlock, { once: true });
addEventListener('keydown', unlock, { once: true });
