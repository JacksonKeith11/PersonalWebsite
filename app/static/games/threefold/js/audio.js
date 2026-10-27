// Chiptune audio, synthesized at startup with OfflineAudioContext and handed to Phaser's sound manager.
// Nothing is downloaded: every effect and music loop is built from oscillators and noise here.

const SR = 44100; // older Safari can't render offline audio at lower rates
const A = { game: null, ready: false, music: true, sfx: true, wanted: null, playing: null, playingKey: null };
try {
  const s = JSON.parse(localStorage.getItem('threefold-audio') || '{}');
  if (s.music === false) A.music = false;
  if (s.sfx === false) A.sfx = false;
} catch (e) { /* storage unavailable */ }

const midi = n => 440 * Math.pow(2, (n - 69) / 12);

function kit(ctx, out) {
  const nb = ctx.createBuffer(1, SR, SR);
  const d = nb.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  const env = (g, t, dur, vol, attack = 0.005) => {
    g.gain.setValueAtTime(0.0001, t);
    g.gain.linearRampToValueAtTime(vol, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
  };
  return {
    tone({ type = 'square', f, f2, t = 0, dur = 0.1, vol = 0.2, attack, vib }) {
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.type = type;
      o.frequency.setValueAtTime(f, t);
      if (f2) o.frequency.exponentialRampToValueAtTime(f2, t + dur);
      if (vib) {
        const l = ctx.createOscillator(), lg = ctx.createGain();
        l.frequency.value = vib; lg.gain.value = f * 0.03;
        l.connect(lg); lg.connect(o.frequency); l.start(t); l.stop(t + dur);
      }
      env(g, t, dur, vol, attack);
      o.connect(g); g.connect(out);
      o.start(t); o.stop(t + dur + 0.02);
    },
    noise({ t = 0, dur = 0.1, vol = 0.2, type = 'lowpass', f = 2000, f2, q = 1 }) {
      const s = ctx.createBufferSource(), fl = ctx.createBiquadFilter(), g = ctx.createGain();
      s.buffer = nb;
      fl.type = type; fl.Q.value = q;
      fl.frequency.setValueAtTime(f, t);
      if (f2) fl.frequency.exponentialRampToValueAtTime(f2, t + dur);
      env(g, t, dur, vol);
      s.connect(fl); fl.connect(g); g.connect(out);
      s.start(t, Math.random() * 0.5); s.stop(t + dur + 0.02);
    },
  };
}

async function render(seconds, build, target = 0.85) {
  const ctx = new OfflineAudioContext(1, Math.ceil(seconds * SR), SR);
  const out = ctx.createGain();
  out.gain.value = 0.9;
  out.connect(ctx.destination);
  build(kit(ctx, out));
  const buf = await ctx.startRendering();
  // normalize so every sound sits at a healthy level whatever its synth settings
  const d = buf.getChannelData(0);
  let peak = 0;
  for (let i = 0; i < d.length; i++) peak = Math.max(peak, Math.abs(d[i]));
  if (peak > 0) { const k = target / peak; for (let i = 0; i < d.length; i++) d[i] *= k; }
  return buf;
}

const SFX = {
  hit: [0.2, k => { k.noise({ dur: 0.09, vol: 0.5, f: 1800, f2: 300 }); k.tone({ f: 170, f2: 60, dur: 0.09, vol: 0.25 }); }],
  crit: [0.3, k => { k.noise({ dur: 0.14, vol: 0.6, f: 3000, f2: 300 }); k.tone({ f: 140, f2: 40, dur: 0.14, vol: 0.3 }); k.tone({ f: 990, f2: 1480, dur: 0.12, vol: 0.12, t: 0.03 }); }],
  slash: [0.2, k => { k.noise({ dur: 0.13, vol: 0.8, type: 'bandpass', f: 1500, f2: 6000, q: 2 }); k.noise({ dur: 0.06, vol: 0.3, f: 2500, f2: 600 }); }],
  magic: [0.35, k => { [880, 1108, 1318, 1760].forEach((f, i) => k.tone({ type: 'sine', f, t: i * 0.045, dur: 0.12, vol: 0.18 })); k.tone({ type: 'triangle', f: 440, f2: 880, dur: 0.3, vol: 0.08 }); }],
  fire: [0.5, k => { k.noise({ dur: 0.45, vol: 0.55, f: 500, f2: 2600 }); k.noise({ t: 0.1, dur: 0.35, vol: 0.3, f: 1200, f2: 200 }); k.tone({ type: 'sawtooth', f: 90, f2: 50, dur: 0.4, vol: 0.12 }); }],
  ice: [0.4, k => { [1760, 2349, 2093, 2637].forEach((f, i) => k.tone({ type: 'triangle', f, t: i * 0.05, dur: 0.18, vol: 0.12 })); k.noise({ dur: 0.25, vol: 0.15, type: 'highpass', f: 5000 }); }],
  heal: [0.45, k => { [523, 659, 784, 1046].forEach((f, i) => k.tone({ type: 'triangle', f, t: i * 0.06, dur: 0.22, vol: 0.2 })); }],
  shield: [0.6, k => { k.tone({ type: 'sine', f: 520, dur: 0.55, vol: 0.2, attack: 0.01 }); k.tone({ type: 'sine', f: 780, dur: 0.5, vol: 0.14, attack: 0.01 }); k.tone({ type: 'triangle', f: 1560, dur: 0.3, vol: 0.06 }); }],
  step: [0.05, k => { k.noise({ dur: 0.035, vol: 0.12, f: 900 }); }],
  click: [0.06, k => { k.tone({ f: 660, dur: 0.035, vol: 0.12 }); }],
  select: [0.08, k => { k.tone({ f: 523, dur: 0.035, vol: 0.12 }); k.tone({ f: 784, t: 0.035, dur: 0.04, vol: 0.12 }); }],
  coin: [0.25, k => { k.tone({ f: 988, dur: 0.06, vol: 0.16 }); k.tone({ f: 1319, t: 0.06, dur: 0.18, vol: 0.16 }); }],
  death: [0.5, k => { k.tone({ f: 420, f2: 70, dur: 0.45, vol: 0.22 }); k.noise({ dur: 0.3, vol: 0.2, f: 800, f2: 100 }); }],
  stun: [0.4, k => { [900, 700, 900, 700].forEach((f, i) => k.tone({ type: 'triangle', f, t: i * 0.08, dur: 0.08, vol: 0.14 })); }],
  buff: [0.35, k => { k.tone({ f: 330, f2: 660, dur: 0.18, vol: 0.12 }); k.tone({ f: 440, f2: 880, t: 0.1, dur: 0.2, vol: 0.12 }); }],
  lava: [0.5, k => { for (let i = 0; i < 5; i++) k.tone({ type: 'sine', f: 120 + i * 30, f2: 60, t: i * 0.08, dur: 0.1, vol: 0.2 }); k.noise({ dur: 0.45, vol: 0.2, f: 400 }); }],
  blink: [0.35, k => { k.tone({ type: 'sine', f: 300, f2: 1400, dur: 0.15, vol: 0.18 }); k.tone({ type: 'sine', f: 1400, f2: 300, t: 0.15, dur: 0.15, vol: 0.15 }); }],
  bee: [0.3, k => { k.tone({ type: 'sawtooth', f: 420, dur: 0.25, vol: 0.13, vib: 30 }); }],
  miss: [0.2, k => { k.tone({ type: 'sine', f: 700, f2: 300, dur: 0.16, vol: 0.14 }); }],
  summon: [0.7, k => { k.tone({ type: 'sawtooth', f: 55, f2: 110, dur: 0.6, vol: 0.18 }); k.noise({ dur: 0.6, vol: 0.25, f: 300, f2: 900 }); }],
  roar: [0.9, k => { k.tone({ type: 'sawtooth', f: 110, f2: 55, dur: 0.85, vol: 0.25, vib: 12 }); k.noise({ dur: 0.85, vol: 0.35, f: 700, f2: 200 }); }],
  victory: [1.3, k => { [523, 659, 784, 1046].forEach((f, i) => k.tone({ f, t: i * 0.11, dur: 0.14, vol: 0.14 })); [523, 659, 784].forEach(f => k.tone({ f, t: 0.5, dur: 0.7, vol: 0.09 })); k.tone({ type: 'triangle', f: 131, t: 0.5, dur: 0.7, vol: 0.25 }); }],
  defeat: [1.6, k => { [392, 311, 262, 196].forEach((f, i) => k.tone({ type: 'triangle', f, t: i * 0.3, dur: 0.4, vol: 0.22 })); }],
  promote: [1.6, k => { [262, 330, 392, 523, 659, 784, 1046].forEach((f, i) => k.tone({ f, t: i * 0.08, dur: 0.18, vol: 0.12 })); [1046, 1318, 1568].forEach(f => k.tone({ type: 'triangle', f, t: 0.6, dur: 0.9, vol: 0.1 })); for (let i = 0; i < 6; i++) k.tone({ type: 'sine', f: 2000 + i * 300, t: 0.6 + i * 0.07, dur: 0.1, vol: 0.05 }); }],
};

// Music: chord loops with a bass line, arpeggio, a seeded melody and optional drums.
function seeded(seed) {
  return () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
}
const TRACKS = {
  m_map: { bpm: 84, chords: [[57, 'm'], [53, ''], [48, ''], [55, '']], seed: 7, lead: 'triangle', drums: 0 },
  m_wood: { bpm: 120, chords: [[48, ''], [57, 'm'], [53, ''], [55, '']], seed: 11, lead: 'square', drums: 1 },
  m_crypt: { bpm: 100, chords: [[50, 'm'], [46, ''], [43, 'm'], [45, '']], seed: 23, lead: 'triangle', drums: 1 },
  m_ember: { bpm: 136, chords: [[52, 'm'], [48, ''], [50, ''], [47, '']], seed: 31, lead: 'square', drums: 2 },
  m_boss: { bpm: 150, chords: [[57, 'm'], [55, ''], [53, ''], [52, '']], seed: 41, lead: 'sawtooth', drums: 2 },
};
function track(def) {
  const beat = 60 / def.bpm, bars = 8, len = bars * 4 * beat;
  return [len, k => {
    const r = seeded(def.seed);
    for (let bar = 0; bar < bars; bar++) {
      const [root, q] = def.chords[bar % def.chords.length];
      const tones = [0, q === 'm' ? 3 : 4, 7];
      const t0 = bar * 4 * beat;
      for (let i = 0; i < 8; i++) {
        const n = root - 12 + (i === 3 || i === 7 ? 7 : 0);
        k.tone({ type: 'triangle', f: midi(n), t: t0 + i * beat / 2, dur: beat / 2 * 0.9, vol: 0.2 });
      }
      for (let i = 0; i < 16; i++) {
        const n = root + 12 + tones[i % 3] + (i % 6 === 5 ? 12 : 0);
        k.tone({ type: 'square', f: midi(n), t: t0 + i * beat / 4, dur: beat / 4 * 0.6, vol: 0.025 });
      }
      let step = 0;
      while (step < 8) {
        const long = r() < 0.25 ? 2 : 1;
        if (r() > 0.22) {
          const deg = tones[Math.floor(r() * 3)] + (r() < 0.3 ? 2 : 0);
          const n = root + 12 + deg + (r() < 0.25 ? 12 : 0);
          k.tone({ type: def.lead, f: midi(n), t: t0 + step * beat / 2, dur: beat / 2 * long * 0.85, vol: def.lead === 'triangle' ? 0.13 : 0.06, vib: long > 1 ? 6 : 0 });
        }
        step += long;
      }
      if (def.drums) {
        for (let b = 0; b < 4; b++) {
          const t = t0 + b * beat;
          if (b % 2 === 0 || def.drums > 1) k.tone({ type: 'sine', f: 120, f2: 40, t, dur: 0.12, vol: b % 2 === 0 ? 0.35 : 0.2 });
          if (b % 2 === 1) k.noise({ t, dur: 0.1, vol: 0.18, type: 'bandpass', f: 1800, q: 0.8 });
          k.noise({ t: t + beat / 2, dur: 0.03, vol: 0.06, type: 'highpass', f: 7000 });
          if (def.drums > 1) k.noise({ t, dur: 0.03, vol: 0.05, type: 'highpass', f: 7000 });
        }
      } else if (bar % 2 === 0) {
        tones.forEach(tn => k.tone({ type: 'sine', f: midi(root + tn), t: t0, dur: 8 * beat * 0.95, vol: 0.05, attack: 0.4 }));
      }
    }
  }];
}

function saveSettings() {
  try { localStorage.setItem('threefold-audio', JSON.stringify({ music: A.music, sfx: A.sfx })); } catch (e) { /* storage unavailable */ }
}

export async function initAudio(game) {
  A.game = game;
  if (!game.sound || !game.sound.context || typeof OfflineAudioContext === 'undefined') return;
  // iPhones mute web audio with the silent switch unless the page asks for playback audio
  try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch (e) { /* unsupported */ }
  // This module alone pauses and resumes audio. Phaser's own pause-on-blur suspends the context on
  // window blur and resumes only on a matching focus event, which browsers (Safari especially) don't
  // reliably deliver, so audio could stay suspended after a tab switch. Instead: suspend while the tab
  // is hidden; on return, focus, any tap, and every second while visible, resume if needed; and once
  // running again, restart the music, since Safari can leave a looping track silent.
  game.sound.pauseOnBlur = false;
  const ctx = game.sound.context;
  const wake = () => {
    if (document.hidden || ctx.state === 'closed') return;
    const restart = () => { if (A.stale && ctx.state === 'running') { A.stale = false; restartMusic(); } };
    if (ctx.state !== 'running') ctx.resume().then(restart).catch(() => {});
    else restart();
  };
  for (const ev of ['pointerdown', 'touchend', 'keydown', 'click']) document.addEventListener(ev, wake, { capture: true, passive: true });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { A.stale = true; if (ctx.state === 'running') ctx.suspend().catch(() => {}); }
    else wake();
  });
  window.addEventListener('pagehide', () => { A.stale = true; });
  window.addEventListener('pageshow', wake);
  window.addEventListener('focus', wake);
  setInterval(() => { if (A.ready && (ctx.state !== 'running' || A.stale)) wake(); }, 1000);
  const jobs = [];
  for (const [key, [len, build]] of Object.entries(SFX)) jobs.push(render(len, build, key === 'step' || key === 'click' ? 0.45 : 0.85).then(b => game.cache.audio.add(key, b)));
  await Promise.all(jobs);
  A.ready = true;
  if (A.wanted) { const w = A.wanted; A.wanted = null; music(w); }
  for (const [key, def] of Object.entries(TRACKS)) {
    const [len, build] = track(def);
    game.cache.audio.add(key, await render(len, build, 0.8));
    if (A.wanted === key && !A.playing) { A.wanted = null; music(key); }
  }
}

export function sfx(name, vol = 1) {
  if (!A.ready || !A.sfx || !A.game.cache.audio.exists(name)) return;
  try { A.game.sound.play(name, { volume: 0.7 * vol, detune: Math.round((Math.random() - 0.5) * 120) }); } catch (e) { /* sound unavailable */ }
}

function restartMusic() {
  const k = A.playingKey || A.wanted;
  if (A.playing) { A.playing.stop(); A.playing.destroy(); A.playing = null; A.playingKey = null; }
  if (k) music(k);
}
export function music(key) {
  const ctx = A.game && A.game.sound && A.game.sound.context;
  // keep a track that's really playing; restart one that only thinks it is
  if (A.playingKey === key && A.playing && A.playing.isPlaying && !A.stale && (!ctx || ctx.state === 'running')) return;
  if (A.playing) { A.playing.stop(); A.playing.destroy(); A.playing = null; A.playingKey = null; }
  A.wanted = key;
  if (!A.ready || !A.music || !key || !A.game.cache.audio.exists(key)) return;
  try {
    A.playing = A.game.sound.add(key, { loop: true, volume: 0.45 });
    A.playing.play();
    A.playingKey = key;
    A.wanted = null;
    if (ctx && ctx.state === 'running') A.stale = false;
  } catch (e) { A.playing = null; }
}

export function audioState() { return { music: A.music, sfx: A.sfx }; }
export function toggleMusic() {
  A.music = !A.music;
  saveSettings();
  const k = A.playingKey || A.wanted;
  if (!A.music && A.playing) { A.playing.stop(); A.playing.destroy(); A.playing = null; A.playingKey = null; A.wanted = k; }
  else if (A.music && k) music(k);
}
export function toggleSfx() { A.sfx = !A.sfx; saveSettings(); }
export const audioDebug = () => ({ ready: A.ready, playing: A.playingKey, isPlaying: !!(A.playing && A.playing.isPlaying), paused: !!(A.playing && A.playing.isPaused), wanted: A.wanted, state: A.game && A.game.sound.context && A.game.sound.context.state });
