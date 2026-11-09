// Music: a small sequencer that writes each boss's theme as it plays, with Web Audio (no files).
// A theme is a key and mode, a tempo, a bass line, a progression for the pad, a motif and a drum
// pattern. Intensity rises with the boss's phase: phase 2 adds the drums, phase 3 the fast arpeggio.
// The lobby and the Bonfire get a quiet pad of their own.
import { audioOut } from './audio.js?v=5';

const MODES = { minor: [0, 2, 3, 5, 7, 8, 10], phrygian: [0, 1, 3, 5, 7, 8, 10], dorian: [0, 2, 3, 5, 7, 9, 10], harmonic: [0, 2, 3, 5, 7, 8, 11], locrian: [0, 1, 3, 5, 6, 8, 10] };
// prog: scale degrees of each bar's chord root; motif: scale degrees per 8th (null rests); drums: per 16th (k kick, s snare, h hat)
const THEMES = {
  bonfire: { root: 45, mode: 'dorian', bpm: 64, prog: [0, 5, 3, 4], motif: [], drums: '', lead: 'sine', pad: 0.05 },
  corvin: { root: 38, mode: 'minor', bpm: 96, prog: [0, 5, 6, 4], motif: [4, null, 3, 2, 0, null, 2, null, 4, 5, 4, 3, 2, null, null, null], drums: 'k...s...k.k.s...', lead: 'sawtooth' },
  mire: { root: 36, mode: 'phrygian', bpm: 84, prog: [0, 1, 0, 6], motif: [0, null, 1, null, 0, null, null, null, 3, 1, 0, null, null, null, null, null], drums: 'k.....k.s.......', lead: 'triangle' },
  bellwarden: { root: 41, mode: 'locrian', bpm: 72, prog: [0, 1, 4, 0], motif: [7, null, null, null, 6, null, null, null, 4, null, 3, null, 1, null, null, null], drums: 'k.......s.......', lead: 'triangle', bell: true },
  headsmen: { root: 40, mode: 'harmonic', bpm: 112, prog: [0, 5, 4, 4], motif: [0, 0, 2, 3, 4, null, 3, 2, 3, null, 2, 1, 0, null, null, null], drums: 'k.k.s..kk.k.s...', lead: 'square' },
  wolf: { root: 39, mode: 'minor', bpm: 120, prog: [0, 6, 5, 6], motif: [4, null, 4, 5, 4, 3, 2, null, 0, null, 2, 3, 2, null, null, null], drums: 'k..k..s.k..k.ss.', lead: 'sawtooth' },
  alchemist: { root: 43, mode: 'dorian', bpm: 100, prog: [0, 3, 1, 4], motif: [0, 2, 4, 6, 4, 2, null, null, 1, 3, 5, 3, 1, null, null, null], drums: 'k...s.h.k.h.s.h.', lead: 'triangle' },
  wyrm: { root: 35, mode: 'phrygian', bpm: 92, prog: [0, 1, 6, 1], motif: [0, null, null, 1, 0, null, null, null, 4, null, 3, null, 1, null, null, null], drums: 'k..k....s..k....', lead: 'sawtooth' },
  mirror: { root: 44, mode: 'harmonic', bpm: 104, prog: [0, 4, 5, 4], motif: [4, 6, 7, 6, 4, null, 2, null, 3, 4, 3, 1, 0, null, null, null], drums: 'k...s...k...s.hh', lead: 'triangle' },
  bastion: { root: 33, mode: 'minor', bpm: 76, prog: [0, 0, 5, 6], motif: [0, null, null, null, 2, null, null, null, 3, null, null, 2, 0, null, null, null], drums: 'k.......k.k.s...', lead: 'square' },
  moth: { root: 46, mode: 'dorian', bpm: 80, prog: [0, 3, 6, 4], motif: [7, null, 6, null, 4, null, 2, null, 4, null, 3, null, 2, null, null, null], drums: 'k.......s.......', lead: 'sine', bell: true },
  king: { root: 38, mode: 'harmonic', bpm: 108, prog: [0, 5, 3, 4], motif: [0, 2, 3, 4, 7, null, 6, 4, 5, null, 4, 3, 2, 1, 0, null], drums: 'k..ks...k..ks.s.', lead: 'sawtooth', organ: true },
  drake: { root: 36, mode: 'phrygian', bpm: 116, prog: [0, 1, 5, 6], motif: [0, 1, 3, null, 1, 0, null, null, 4, 3, 1, null, 0, null, null, null], drums: 'k.k.s.k.k.k.s.ss', lead: 'sawtooth' },
};

const hz = m => 440 * Math.pow(2, (m - 69) / 12);

class Music {
  constructor() { this.theme = null; this.level = 1; this.step = 0; this.next = 0; this.timer = null; this.vol = 0.5; this.bus = null; }

  play(key, level = 1) {
    const out = audioOut();
    if (!out) return;
    const T = THEMES[key] || THEMES.bonfire;
    this.level = level;
    if (this.theme === T) return;
    this.stop();
    this.theme = T; this.key = key; this.step = 0;
    const { ctx, master } = out;
    this.ctx = ctx;
    this.bus = ctx.createGain(); this.bus.gain.value = 0.0001; this.bus.connect(master);
    this.bus.gain.exponentialRampToValueAtTime(this.vol * 0.55, ctx.currentTime + 2);
    this.next = ctx.currentTime + 0.1;
    this.timer = setInterval(() => this.schedule(), 50);
  }

  setLevel(level) { this.level = level; }
  setVolume(v) { this.vol = v; if (this.bus) this.bus.gain.setTargetAtTime(v * 0.55, this.ctx.currentTime, 0.2); }

  stop() {
    if (!this.bus) return;
    clearInterval(this.timer);
    const bus = this.bus, t = this.ctx.currentTime;
    bus.gain.setTargetAtTime(0.0001, t, 0.4);
    setTimeout(() => bus.disconnect(), 2000);
    this.bus = null; this.theme = null;
  }

  // schedule every 16th note that falls in the next 0.2 s
  schedule() {
    const T = this.theme, ctx = this.ctx;
    if (!T) return;
    const s16 = 60 / T.bpm / 4;
    while (this.next < ctx.currentTime + 0.2) {
      this.note16(T, this.step, this.next, s16);
      this.next += s16; this.step++;
    }
  }

  deg(T, d, oct = 0) {
    const sc = MODES[T.mode], n = sc.length;
    return T.root + 12 * (oct + Math.floor(d / n)) + sc[((d % n) + n) % n];
  }

  note16(T, step, t, s16) {
    const bar = Math.floor(step / 16) % T.prog.length, i = step % 16, chord = T.prog[bar];
    // the pad: the bar's chord, held
    if (i === 0) for (const d of [0, 2, 4]) this.voice('sine', hz(this.deg(T, chord + d, 1)), t, s16 * 16, T.pad || 0.035, 0.6, T.organ);
    // the bass: root on the beat, fifth between
    if (T.key !== 'bonfire' && i % 4 === 0) this.voice('triangle', hz(this.deg(T, chord + (i === 8 ? 4 : 0), -1)), t, s16 * 3, 0.16, 0.01);
    // the motif, every 8th
    if (i % 2 === 0 && T.motif.length) {
      const d = T.motif[(i / 2 + (bar % 2) * 8) % T.motif.length];
      if (d != null) this.voice(T.lead, hz(this.deg(T, chord + d, 1)), t, s16 * 1.8, 0.05, 0.01);
    }
    if (T.bell && i === 0 && bar % 2 === 0) this.voice('sine', hz(this.deg(T, chord, 2)), t, s16 * 12, 0.06, 0.002, false, 2.76);
    // phase 2+: drums
    if (this.level >= 2 && T.drums) {
      const c = T.drums[i];
      if (c === 'k') this.kick(t);
      else if (c === 's') this.snare(t);
      else if (c === 'h') this.hat(t);
    }
    // phase 3: a fast arpeggio over everything
    if (this.level >= 3 && T.motif.length) this.voice('square', hz(this.deg(T, chord + [0, 2, 4, 7][i % 4], 2)), t, s16 * 0.9, 0.025, 0.005);
  }

  voice(type, f, t, dur, peak, attack, organ, ratio) {
    const ctx = this.ctx, o = ctx.createOscillator(), g = ctx.createGain(), fl = ctx.createBiquadFilter();
    o.type = type; o.frequency.value = f;
    fl.type = 'lowpass'; fl.frequency.value = type === 'sawtooth' || type === 'square' ? 1400 : 3000;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(peak, t + attack + 0.005);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(fl).connect(g).connect(this.bus);
    o.start(t); o.stop(t + dur + 0.05);
    if (organ || ratio) {  // an organ's fifth above, or a bell's inharmonic partial
      const o2 = ctx.createOscillator(); o2.type = 'sine'; o2.frequency.value = f * (ratio || 1.5);
      o2.connect(g); o2.start(t); o2.stop(t + dur + 0.05);
    }
  }

  kick(t) {
    const ctx = this.ctx, o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.setValueAtTime(110, t); o.frequency.exponentialRampToValueAtTime(40, t + 0.12);
    g.gain.setValueAtTime(0.35, t); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.25);
    o.connect(g).connect(this.bus); o.start(t); o.stop(t + 0.3);
  }

  noise(t, dur, f, peak) {
    const ctx = this.ctx, len = Math.floor(ctx.sampleRate * dur), buf = ctx.createBuffer(1, len, ctx.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    const s = ctx.createBufferSource(), fl = ctx.createBiquadFilter(), g = ctx.createGain();
    s.buffer = buf; fl.type = 'highpass'; fl.frequency.value = f;
    g.gain.setValueAtTime(peak, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(fl).connect(g).connect(this.bus); s.start(t);
  }
  snare(t) { this.noise(t, 0.16, 1200, 0.16); }
  hat(t) { this.noise(t, 0.04, 7000, 0.06); }
}

export const music = new Music();
