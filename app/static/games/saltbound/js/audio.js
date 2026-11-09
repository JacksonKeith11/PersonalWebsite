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
  crit: () => { noise(0.2, { gain: 0.3, freq: 300, q: 0.8 }); tone(90, 0.3, { type: 'square', gain: 0.08, slide: -40 }); tone(1400, 0.08, { type: 'triangle', gain: 0.06, delay: 0.02 }); },
  kill: () => { tone(330, 0.12, { type: 'triangle', gain: 0.08 }); tone(220, 0.3, { type: 'sawtooth', gain: 0.06, slide: -120, delay: 0.06 }); noise(0.25, { gain: 0.12, freq: 1800, delay: 0.04 }); },
  stun: () => [1320, 1760, 1320].forEach((f, i) => tone(f, 0.08, { type: 'triangle', gain: 0.06, delay: i * 0.06 })),
  hitwin: () => { tone(784, 0.1, { type: 'triangle', gain: 0.08 }); tone(1175, 0.16, { type: 'triangle', gain: 0.08, delay: 0.07 }); },
  rare: () => [659, 988, 1319].forEach((f, i) => tone(f, 0.3, { type: 'triangle', gain: 0.08, delay: i * 0.09 })),
  fanfare: () => { [523, 659, 784, 1047, 1319].forEach((f, i) => tone(f, 0.4, { type: 'triangle', gain: 0.09, delay: i * 0.09 })); tone(2093, 0.6, { gain: 0.05, delay: 0.5 }); },
  phase: () => { tone(98, 0.9, { type: 'sawtooth', gain: 0.1, slide: -20 }); noise(0.9, { gain: 0.14, freq: 200, q: 0.5, type: 'lowpass' }); },
  coin: () => { tone(1568, 0.06, { type: 'square', gain: 0.04 }); tone(2093, 0.12, { type: 'square', gain: 0.04, delay: 0.05 }); },
  revive: () => [392, 523, 784].forEach((f, i) => tone(f, 0.3, { gain: 0.09, delay: i * 0.08 })),
};
export function play(name) {
  if (volume <= 0) return;
  try { SOUNDS[name]?.(); } catch { /* audio can fail before a user gesture */ }
}

// ------------------------------------------------------------------ music
// Loops synthesized on the fly, scheduled a little ahead of time. Each region has its own style
// (`STYLES`: chords, tempo, instruments, ambience), played two ways: calm on the map and menus (slow
// pads, an arpeggio, the region's ambience underneath) and driving in fights (kick, snare, pulsing
// bass, a lead). A dungeon's boss fight adds brass stabs, and each final boss has its own theme.
// `music(key)` takes 'map:<region>', 'fight:<region>', 'boss:<region>' or 'final:<boss key>'. A new
// region waits for the next bar, so walking along a border doesn't stutter; map to fight is at once.
// Browsers only allow sound after the first click or key press, so music waits for one.
let musicVol = 0.5, musicBus = null, mode = null, playing = null, timer = null, nextAt = 0, step = 0, unlocked = false;
try { musicVol = JSON.parse(localStorage.getItem('saltbound'))?.settings?.music ?? 0.5; } catch { /* private mode */ }

const N = n => 440 * Math.pow(2, (n - 69) / 12); // midi note -> Hz
// chords: four bars of four midi notes (root first); fchords: the fight's, when different.
// pad / lead: oscillator types. amb: the ambience bed (noise) on the map. perc: extra fight drums.
// drone: a low root held under the map song. bells: high chimes on the map. sparse: arpeggio every
// 4th sixteenth instead of every 2nd. swing: how late the off-beat eighths land (fraction of a 16th).
// wobble: detune drift on the map's pad and arpeggio. short: plucked arpeggio (marimba-like).
const SEA = { gain: 0.035, freq: 400, type: 'lowpass', q: 1 };
const WIND = { gain: 0.03, freq: 1100, type: 'bandpass', q: 0.4 };
const STYLES = {
  coral: { // the Coral Shallows: the old sea song, D dorian
    bpm: 76, fbpm: 128, chords: [[50, 57, 62, 65], [46, 53, 58, 62], [53, 57, 60, 65], [48, 55, 60, 64]],
    fchords: [[50, 57, 62, 65], [48, 55, 60, 64], [46, 53, 58, 62], [45, 52, 57, 61]],
    arp: [0, 2, 3, 1, 2, 3, 2, 1], pad: 'triangle', lead: 'square', amb: SEA,
  },
  keys: { // Smugglers' Keys: a swung A-minor shanty with a squeezebox
    bpm: 92, fbpm: 136, chords: [[45, 52, 57, 60], [50, 57, 62, 65], [52, 56, 59, 64], [45, 52, 57, 60]],
    arp: [0, 3, 2, 3, 1, 3, 2, 3], pad: 'sawtooth', padGain: 0.034, lead: 'square', amb: SEA, swing: 0.35, perc: 'shaker',
  },
  storm: { // Stormcrag: E minor, wind and distant thunder
    bpm: 80, fbpm: 140, chords: [[52, 59, 64, 67], [48, 55, 60, 64], [50, 57, 62, 66], [47, 54, 59, 63]],
    arp: [0, 1, 2, 3, 2, 1, 2, 3], pad: 'triangle', lead: 'sawtooth', amb: WIND, perc: 'thunder',
  },
  ash: { // Cinderreach: E phrygian over a growling drone, embers crackling
    bpm: 70, fbpm: 132, chords: [[52, 59, 64, 67], [53, 57, 60, 65], [52, 59, 64, 67], [50, 57, 62, 65]],
    arp: [0, 1, 3, 1, 2, 1, 3, 2], pad: 'sawtooth', padGain: 0.034, lead: 'sawtooth', drone: 'sawtooth', amb: { gain: 0.02, freq: 3000, type: 'highpass', q: 0.7 }, crackle: true, perc: 'toms',
  },
  dunes: { // the Shifting Sands: E hijaz, hand drums
    bpm: 84, fbpm: 132, chords: [[52, 56, 59, 64], [53, 57, 60, 65], [52, 56, 59, 64], [50, 57, 62, 65]],
    arp: [0, 1, 2, 3, 2, 1, 0, 1], pad: 'triangle', lead: 'square', amb: { gain: 0.018, freq: 5000, type: 'highpass', q: 0.5 }, perc: 'hand',
  },
  petrified: { // the Stillwood: slow, sparse and hushed
    bpm: 60, fbpm: 120, chords: [[45, 52, 57, 60], [41, 48, 53, 57], [48, 52, 55, 60], [43, 50, 55, 59]],
    arp: [0, 2, 1, 3, 2, 0, 3, 1], pad: 'sine', lead: 'triangle', sparse: true, amb: { gain: 0.015, freq: 300, type: 'lowpass', q: 1 },
  },
  jungle: { // the Verdant Deep: G minor pentatonic marimba over toms
    bpm: 96, fbpm: 138, chords: [[43, 50, 55, 58], [51, 55, 58, 63], [53, 57, 60, 65], [43, 50, 55, 58]],
    arp: [0, 2, 1, 3, 2, 0, 3, 1], pad: 'triangle', lead: 'sine', short: true, perc: 'toms', amb: { gain: 0.02, freq: 2500, type: 'bandpass', q: 2 },
  },
  heaven: { // Aetherhold: bright F lydian with bells
    bpm: 70, fbpm: 130, chords: [[53, 57, 60, 65], [55, 59, 62, 67], [57, 60, 64, 69], [48, 55, 60, 64]],
    arp: [0, 1, 2, 3, 2, 3, 1, 2], pad: 'sine', lead: 'triangle', bells: true, amb: { gain: 0.015, freq: 6000, type: 'highpass', q: 0.5 },
  },
  crystal: { // the Prism Wood: E major, glassy chimes
    bpm: 72, fbpm: 132, chords: [[52, 59, 64, 66], [49, 56, 61, 64], [45, 52, 57, 61], [47, 54, 59, 63]],
    arp: [0, 3, 2, 3, 1, 3, 2, 3], pad: 'sine', lead: 'sine', bells: true, wobble: 8,
  },
  dream: { // the Drowsing Vale: slow major sevenths, drifting out of tune
    bpm: 56, fbpm: 118, chords: [[46, 53, 57, 62], [43, 50, 53, 58], [51, 55, 58, 62], [53, 57, 60, 65]],
    arp: [0, 2, 3, 1, 3, 2, 1, 3], pad: 'triangle', lead: 'triangle', wobble: 18,
  },
  frost: { // the Frostpeaks: B minor, wind and icy bells
    bpm: 66, fbpm: 128, chords: [[47, 54, 59, 62], [43, 50, 55, 59], [50, 54, 57, 62], [45, 52, 57, 61]],
    arp: [0, 2, 3, 2, 1, 2, 3, 2], pad: 'sine', lead: 'sine', bells: true, sparse: true, amb: WIND,
  },
  peak: { // the Peak: D minor, a choir-like drone, wind
    bpm: 64, fbpm: 136, chords: [[50, 57, 62, 65], [46, 53, 58, 62], [43, 50, 55, 58], [45, 52, 57, 61]],
    arp: [0, 3, 2, 1, 0, 3, 2, 1], pad: 'sawtooth', padGain: 0.034, lead: 'sawtooth', drone: 'triangle', amb: WIND,
  },
};
// The final bosses' themes: always the fight pattern, with brass stabs.
const FINALS = {
  drowned_crown: { fbpm: 142, fchords: [[50, 57, 62, 65], [46, 53, 58, 62], [43, 50, 55, 58], [45, 52, 57, 61]], arp: [0, 3, 2, 3, 1, 3, 2, 3], lead: 'square', perc: 'toms' },
  leviathan: { fbpm: 104, fchords: [[48, 55, 60, 63], [44, 51, 56, 60], [41, 48, 53, 56], [43, 50, 55, 59]], arp: [0, 1, 0, 2, 0, 1, 3, 2], lead: 'sawtooth', sub: true },
  storm_queen: { fbpm: 152, fchords: [[52, 59, 64, 67], [48, 55, 60, 64], [45, 52, 57, 60], [47, 54, 59, 63]], arp: [0, 3, 2, 3, 1, 3, 2, 3], lead: 'square', perc: 'thunder' },
};

function songOf(key) {
  const [kind, name] = String(key).split(':');
  if (kind === 'final') {
    const fb = FINALS[name] || FINALS.drowned_crown;
    return { kind: 'fight', boss: true, steps: 64, ...fb, bpm: fb.fbpm, chords: fb.fchords };
  }
  const st = STYLES[name] || STYLES.coral;
  if (kind === 'map') return { kind: 'map', steps: 128, ...st };
  return { kind: 'fight', boss: kind === 'boss', steps: 64, ...st, bpm: st.fbpm + (kind === 'boss' ? 10 : 0), chords: st.fchords || st.chords };
}

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

function playMap(s, i, t, x) {
  const bar = Math.floor(i / 16), chord = s.chords[bar % s.chords.length], pos = i % 16;
  const sw = pos % 4 === 2 ? (s.swing || 0) * x : 0, wob = () => (s.wobble ? (Math.random() * 2 - 1) * s.wobble : 0);
  if (pos === 0) chord.forEach((n, k) => mtone(N(n), t, x * 16, { type: k ? s.pad : 'sine', gain: s.padGain ?? 0.05, attack: 0.6, release: 0.8, detune: (k % 2 ? 6 : -6) + wob() }));
  if (pos === 0 && s.drone) mtone(N(chord[0] - 12), t, x * 16, { type: s.drone, gain: 0.03, attack: 0.8, release: 0.8 });
  if (pos % (s.sparse ? 4 : 2) === 0) {
    const n = chord[s.arp[(pos / 2) % 8]] + 12;
    mtone(N(n), t + sw, x * (s.short ? 1.2 : 2.5), { type: s.lead === 'square' || s.lead === 'sawtooth' ? 'triangle' : s.lead, gain: 0.045, attack: 0.005, release: s.short ? 0.12 : 0.25, detune: wob() });
  }
  if (s.amb && pos === 0 && bar % 2 === 0) mnoise(t, x * 28, s.amb);
  if (s.crackle && Math.random() < 0.18) mnoise(t + Math.random() * x, 0.03, { gain: 0.04, freq: 4000, type: 'highpass' });
  if (s.bells && (pos === 6 || (pos === 14 && bar % 2))) mtone(N(chord[1 + (bar + pos) % 3] + 24), t, x * 8, { gain: 0.022, attack: 0.003, release: x * 7 });
  else if (pos === 8 && bar % 4 === 3) mtone(N(chord[3] + 24), t, x * 6, { gain: 0.03, attack: 0.05, release: 0.4 });
  if (s.perc === 'hand' && [0, 6, 10].includes(pos)) mtone(pos ? 220 : 110, t, 0.12, { gain: pos ? 0.05 : 0.08, attack: 0.002, release: 0.1 });
  if (s.perc === 'toms' && s.short && [0, 3, 8, 11, 14].includes(pos)) mtone([98, 0, 0, 131, 0, 0, 0, 0, 98, 0, 0, 147, 0, 0, 165][pos], t, 0.15, { gain: 0.06, attack: 0.002, release: 0.12 });
  if (s.perc === 'thunder' && pos === 0 && bar % 4 === 2) mnoise(t, x * 20, { gain: 0.06, freq: 120, type: 'lowpass', q: 0.5 });
}

function playFight(s, i, t, x) {
  const bar = Math.floor(i / 16), chord = s.chords[bar % s.chords.length], pos = i % 16;
  const sw = pos % 4 === 2 ? (s.swing || 0) * x : 0;
  if (pos % 4 === 0) { mtone(110, t, 0.18, { gain: s.boss ? 0.3 : 0.25, attack: 0.002, release: 0.15 }); mtone(55, t, 0.2, { gain: 0.2, attack: 0.002, release: 0.18 }); }
  if (pos === 4 || pos === 12) mnoise(t, 0.16, { gain: 0.12, freq: 1800, q: 0.7 });
  if (pos % 2 === 1) mnoise(t + sw, 0.04, { gain: s.perc === 'shaker' ? 0.06 : 0.04, freq: 7000, type: 'highpass' });
  if (pos % 2 === 0) mtone(N(chord[0] - (s.sub ? 24 : 12)), t + sw, x * 1.8, { type: 'sawtooth', gain: 0.05, attack: 0.005, release: 0.08 });
  if (pos === 0) chord.forEach(n => mtone(N(n), t, x * 15, { type: 'triangle', gain: 0.025, attack: 0.05, release: 0.3 }));
  if ([0, 3, 6, 8, 11, 14].includes(pos)) mtone(N(chord[s.arp[pos % 8]] + 12), t + sw, x * 1.5, { type: s.lead, gain: s.lead === 'sine' ? 0.04 : 0.025, attack: 0.003, release: 0.08 });
  if (s.perc === 'hand' && [2, 7, 10].includes(pos)) mtone(pos === 10 ? 165 : 247, t, 0.1, { gain: 0.05, attack: 0.002, release: 0.08 });
  if (s.perc === 'toms' && pos === 14 && bar % 2) [147, 131, 110].forEach((f, k) => mtone(f, t + k * x * 0.66, 0.14, { gain: 0.08, attack: 0.002, release: 0.12 }));
  if (s.perc === 'thunder' && pos === 0 && bar % 4 === 0) mnoise(t, x * 12, { gain: 0.08, freq: 140, type: 'lowpass', q: 0.5 });
  if (s.bells && pos === 8) mtone(N(chord[2] + 24), t, x * 4, { gain: 0.02, attack: 0.003, release: x * 3 });
  if (s.boss && (pos === 0 || pos === 10)) chord.forEach(n => mtone(N(n - 12), t, x * 2, { type: 'sawtooth', gain: 0.03, attack: 0.01, release: 0.1 }));
  if (s.sub && pos === 0 && bar % 2 === 0) mtone(N(chord[0] - 24), t, x * 16, { gain: 0.12, attack: 0.05, release: 0.6 });
}

function tick() {
  if (!ctx || !playing) return;
  while (nextAt < ctx.currentTime + 0.25) {
    if (step % 16 === 0 && mode && mode !== playing.key) { playing = { key: mode, ...songOf(mode) }; step = 0; }
    const x = 60 / playing.bpm / 4;
    (playing.kind === 'map' ? playMap : playFight)(playing, step, nextAt, x);
    step = (step + 1) % playing.steps;
    nextAt += x;
  }
}

export function music(want) {
  if (want === mode) return;
  const kindChanged = !mode || !want || String(mode).split(':')[0] !== String(want).split(':')[0];
  mode = want;
  if (!want) { playing = null; return; }
  if (!unlocked || musicVol <= 0) return;
  if (!bus()) return;
  if (!playing || kindChanged) { // start at once; a new region of the same kind waits for the bar (in `tick`)
    playing = { key: want, ...songOf(want) };
    step = 0;
    nextAt = ctx.currentTime + 0.1;
  }
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
