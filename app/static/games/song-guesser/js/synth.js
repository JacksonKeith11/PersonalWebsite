// Song Guesser's synthesizer. Every song in songs.js is a short text arrangement; arrange() turns
// one into timed notes per instrument, and renderPart() plays a part into an AudioBuffer with
// OfflineAudioContext. Nothing is downloaded: every sound is built from oscillators and noise here.

export const SR = 44100; // older Safari can't render offline audio at lower rates
export const CLIP = 10; // seconds of each song the player hears
const TAIL = 0.6; // after the clip, for releases and reverb; faded out in mix()

const LETTER = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
const acc = s => (s === '#' ? 1 : s === 'b' ? -1 : 0);
const freq = m => 440 * Math.pow(2, (m - 69) / 12);

export function midiOf(name) {
  const m = /^([A-G])([#b]?)(\d)$/.exec(name);
  if (!m) throw new Error(`bad note "${name}"`);
  return 12 * (+m[3] + 1) + LETTER[m[1]] + acc(m[2]);
}

const QUALITY = {
  '': [0, 4, 7], m: [0, 3, 7], 5: [0, 7, 12], 6: [0, 4, 7, 9], m6: [0, 3, 7, 9], 7: [0, 4, 7, 10],
  maj7: [0, 4, 7, 11], m7: [0, 3, 7, 10], sus2: [0, 2, 7], sus4: [0, 5, 7], '7sus4': [0, 5, 7, 10],
  add9: [0, 4, 7, 14], madd9: [0, 3, 7, 14], dim: [0, 3, 6], aug: [0, 4, 8],
};

// "G#m/F#" -> { root: 8, bass: 6, ivs: [0, 3, 7], power }
export function parseChord(sym) {
  const m = /^([A-G])([#b]?)([^/]*)(?:\/([A-G])([#b]?))?$/.exec(sym);
  if (!m || !(m[3] in QUALITY)) throw new Error(`bad chord "${sym}"`);
  const root = (LETTER[m[1]] + acc(m[2]) + 12) % 12;
  const bass = m[4] ? (LETTER[m[4]] + acc(m[5]) + 12) % 12 : root;
  return { root, bass, ivs: QUALITY[m[3]], power: m[3] === '5' };
}

// "E4:1 G4:.5 - B3+E4:2" -> { events: [{ at, len, item }], total } in beats. A token without
// ":len" keeps the previous length, "-" is a rest and "|" (a bar line, for reading) is skipped.
export function parseSeq(text, item) {
  const events = [];
  let at = 0, len = 1;
  for (const tok of text.trim().split(/\s+/)) {
    if (tok === '|') continue;
    const [name, l] = tok.split(':');
    if (l !== undefined) {
      len = +l;
      if (!(len > 0)) throw new Error(`bad length in "${tok}"`);
    }
    if (name !== '-') events.push({ at, len, item: item(name) });
    at += len;
  }
  return { events, total: at };
}
const notesOf = name => name.split('+').map(midiOf);

// One bar of drums per string: k kick, s snare, c clap, h closed hat, o open hat, t tom, r rim,
// z shaker. x is a hit, X an accent and g a ghost note; a bar's steps share it evenly.
export const GROOVES = {
  rock: { k: 'x.......x.x.....', s: '....x.......x...', h: 'x.x.x.x.x.x.x.x.' },
  drive: { k: 'x.......x.x.....', s: '....x.......x...', h: 'XxxxXxxxXxxxXxxx' },
  motorik: { k: 'x...x...x...x...', s: '....x.......x...', h: 'xxxxxxxxxxxxxxxx' },
  disco: { k: 'x...x...x...x...', s: '....x.......x...', h: 'x...x...x...x...', o: '..x...x...x...x.' },
  four: { k: 'x...x...x...x...', s: '....g.......g...' },
  half: { k: 'x.......x.......', s: '........x.......', h: 'x.x.x.x.x.x.x.x.' },
  stomp: { k: 'x.....x.x.......', c: '....x.......x...', h: '..g...g...g...g.' },
  shaker: { k: 'x.......x.......', r: '....x.......x...', z: 'XxgxXxgxXxgxXxgx' },
  onedrop: { k: '........x.......', r: '........x.......', h: 'x.x.x.x.x.x.x.x.' },
  six8: { k: 'x...........', r: '......x.....', z: 'x.g.g.x.g.g.' },
};

// How a derived bass line plays each chord's root: step in beats, note length as a share of it.
const BASS = {
  eighths: { step: 0.5, len: 0.9, note: m => m },
  quarters: { step: 1, len: 0.9, note: m => m },
  halves: { step: 2, len: 0.95, note: m => m },
  octaves: { step: 0.5, len: 0.8, note: (m, i) => (i % 2 ? m + 12 : m) },
  root5: { step: 1, len: 0.9, note: (m, i) => (i % 2 ? m + 7 : m) },
};

// Chord rhythms, looping from the clip's start: x strikes, - holds, . is silent.
const RHYTHM = {
  strum: ['x--x--x-', 0.5],
  eighths: ['x', 0.5],
  sixteenths: ['x', 0.25],
  quarters: ['x-', 0.5],
  pulse: ['x.', 0.5],
  whole: ['x-------', 0.5],
  offbeat: ['.x', 0.5],
  stabs: ['x..x..x.', 0.5],
};
const ARP = [0, 1, 2, 3, 2, 1, 2, 1];

// osc: [type, detune in cents, level]; lp: lowpass [from Hz, to Hz, over seconds];
// env: [attack, decay, sustain level, release]; vib: [rate Hz, depth cents, delay].
const INST = {
  bass: { osc: [['sawtooth', 0, 0.45], ['sine', 0, 0.9]], lp: [1200, 380, 0.25], q: 2, env: [0.005, 0.35, 0.6, 0.06] },
  guitar: { osc: [['sawtooth', 6, 0.35], ['square', -6, 0.18]], lp: [3400, 1100, 0.35], env: [0.003, 0.5, 0.3, 0.1] },
  dist: { osc: [['sawtooth', 9, 0.4], ['sawtooth', -9, 0.4]], drive: 8, lp: [2600, 1700, 0.3], env: [0.003, 0.3, 0.75, 0.06] },
  lead: { osc: [['sawtooth', 5, 0.4], ['square', -5, 0.2]], drive: 4, lp: [3200, 2200, 0.3], env: [0.004, 0.3, 0.8, 0.08], vib: [5.5, 14, 0.25] },
  clean: { osc: [['triangle', 0, 0.6], ['sawtooth', 4, 0.2]], lp: [4200, 1400, 0.3], env: [0.002, 0.5, 0.15, 0.15] },
  piano: { osc: [['triangle', 0, 0.7], ['sine', 1200, 0.25], ['square', 0, 0.05]], lp: [4500, 1500, 0.6], env: [0.002, 0.9, 0, 0.25] },
  organ: { osc: [['sine', 0, 0.5], ['sine', 1200, 0.3], ['sine', 1902, 0.15], ['sine', 2400, 0.1]], env: [0.01, 1, 1, 0.05] },
  synth: { osc: [['sawtooth', 8, 0.3], ['sawtooth', -8, 0.3]], lp: [2600, 1400, 0.4], env: [0.01, 0.4, 0.6, 0.2] },
  square: { osc: [['square', 0, 0.35], ['square', 1200, 0.08]], lp: [5000, 3000, 0.3], env: [0.004, 0.25, 0.55, 0.05] },
  strings: { osc: [['sawtooth', 5, 0.25], ['sawtooth', -5, 0.25]], lp: [2400, 2400, 1], env: [0.08, 1, 0.9, 0.25], vib: [5, 8, 0.2] },
  mandolin: { osc: [['triangle', 0, 0.5], ['sawtooth', 4, 0.2]], lp: [5200, 1700, 0.15], env: [0.002, 0.18, 0.05, 0.08] },
  horn: { osc: [['sawtooth', 0, 0.5], ['sawtooth', 7, 0.3]], lp: [700, 2200, 0.09], env: [0.04, 0.3, 0.85, 0.12], vib: [5, 10, 0.3] },
  saw: { osc: [['sine', 0, 0.8], ['triangle', 0, 0.2]], env: [0.15, 1, 1, 0.3], vib: [5.5, 30, 0.1] },
  voice: { osc: [['triangle', 0, 0.7], ['sawtooth', 0, 0.12]], lp: [1900, 1900, 1], env: [0.035, 0.3, 0.85, 0.12], vib: [5, 16, 0.22] },
  bell: { osc: [['sine', 0, 0.6], ['sine', 2786, 0.2]], env: [0.002, 0.7, 0, 0.4] },
  whistle: { osc: [['sine', 0, 0.8]], env: [0.03, 1, 0.9, 0.08], vib: [6, 15, 0.15] },
};
export const INSTRUMENTS = Object.keys(INST);
const STRUMMED = new Set(['guitar', 'dist', 'clean', 'mandolin']);
const CHORD_LABEL = { guitar: 'Guitar', dist: 'Guitar', clean: 'Guitar', piano: 'Piano', organ: 'Organ', synth: 'Synth', strings: 'Strings', mandolin: 'Mandolin' };
const LINE_LABEL = { lead: 'Lead guitar', dist: 'Guitar riff', guitar: 'Guitar line', clean: 'Guitar line', piano: 'Piano', synth: 'Synth lead', square: 'Synth lead', horn: 'Horns', saw: 'Singing saw', voice: 'Backing vocal', bell: 'Bells', whistle: 'Whistle', strings: 'Strings', organ: 'Organ', mandolin: 'Mandolin' };
const ORDER = ['drums', 'bass', 'chords', 'riff', 'melody'];

// Beats to seconds, with swing pushing each off-beat eighth later.
function timer(song) {
  const spb = 60 / song.bpm, sw = song.swing || 0.5;
  return b => {
    const i = Math.floor(b), f = b - i;
    return spb * (i + (f < 0.5 ? (f / 0.5) * sw : sw + ((f - 0.5) / 0.5) * (1 - sw)));
  };
}

function* looped(seq, beats) {
  for (let k = 0; k * seq.total < beats; k++) {
    for (const e of seq.events) {
      const at = e.at + k * seq.total;
      if (at < beats) yield { ...e, at };
    }
  }
}

// Pitch class -> MIDI note inside [lo, lo + 11].
const place = (pc, lo) => lo + ((pc - lo) % 12 + 12) % 12;

// Turns a song into its parts: { order, parts: { name: { label, inst, notes | hits } } }.
export function arrange(song) {
  const time = timer(song);
  const meter = song.meter || 4;
  const beats = (CLIP * song.bpm) / 60;
  const note = (at, len, m, v = 1) => ({ t: time(at), d: time(at + len) - time(at), m, v });
  const chords = song.chords ? parseSeq(song.chords, parseChord) : null;
  const chordAt = b => {
    if (!chords) return null;
    const x = b % chords.total;
    return chords.events.find(e => x >= e.at - 1e-9 && x < e.at + e.len - 1e-9) || null;
  };
  const parts = {};

  if (song.drums) {
    const groove = typeof song.drums === 'string' ? GROOVES[song.drums] : song.drums;
    if (!groove) throw new Error(`unknown groove "${song.drums}"`);
    const hits = [];
    for (const [drum, pat] of Object.entries(groove)) {
      const step = meter / pat.length;
      for (let bar = 0; bar * meter < beats; bar++) {
        [...pat].forEach((c, i) => {
          const at = bar * meter + i * step;
          if (c !== '.' && at < beats) hits.push({ t: time(at), drum, v: c === 'X' ? 1.25 : c === 'g' ? 0.4 : 1 });
        });
      }
    }
    parts.drums = { label: 'Drums', drums: true, hits };
  }

  if (song.bass) {
    const notes = [];
    const tpl = BASS[song.bass];
    if (tpl) {
      if (!chords) throw new Error('a derived bass line needs chords');
      for (const c of looped(chords, beats)) {
        const m = place(c.item.bass, 31);
        for (let i = 0, at = c.at; at < c.at + c.len - 1e-9 && at < beats; i++, at += tpl.step) {
          notes.push(note(at, Math.min(tpl.step, c.at + c.len - at) * tpl.len, [tpl.note(m, i)]));
        }
      }
    } else {
      for (const e of looped(parseSeq(song.bass, notesOf), beats)) notes.push(note(e.at, e.len * 0.92, e.item));
    }
    parts.bass = { label: 'Bass', inst: 'bass', notes };
  }

  if (chords && song.guitar !== null) {
    const spec = { inst: 'guitar', style: 'strum', ...song.guitar };
    const power = spec.inst === 'dist' && !spec.full;
    const voicing = c => {
      if (power || c.power) {
        const r = place(c.root, 40);
        return [r, r + 7, r + 12];
      }
      const r = place(c.root, 52);
      return c.ivs.map(i => r + i);
    };
    const notes = [];
    if (spec.style === 'arp') {
      const step = spec.step || 0.5;
      for (let i = 0, at = 0; at < beats; i++, at += step) {
        const c = chordAt(at);
        if (!c) continue;
        const v = voicing(c.item);
        const tones = spec.arp ? spec.arp.map(x => v[0] + x) : [...v.slice(0, 3), v[0] + 12];
        const m = spec.arp ? tones[i % tones.length] : tones[ARP[i % ARP.length] % tones.length];
        notes.push(note(at, step * 2, [m], 0.8));
      }
    } else {
      const [pat, step] = spec.rhythm ? [spec.rhythm, spec.step || 0.5] : RHYTHM[spec.style] || [];
      if (!pat) throw new Error(`unknown chord style "${spec.style}"`);
      let cur = null;
      for (let i = 0, at = 0; at < beats; i++, at += step) {
        const ch = pat[i % pat.length], c = chordAt(at);
        if (ch === '.' || !c) { cur = null; continue; }
        if (ch === '-' && cur && cur.chord === c) { cur.n.d = time(at + step) - cur.n.t; continue; }
        let v = voicing(c.item);
        if (i % 2) v = [...v].reverse(); // upstrokes
        cur = { chord: c, n: note(at, step, v, i % 2 ? 0.8 : 1) };
        notes.push(cur.n);
      }
    }
    parts.chords = { label: spec.label || CHORD_LABEL[spec.inst] || 'Chords', inst: spec.inst, strum: STRUMMED.has(spec.inst), notes };
  }

  for (const [name, inst] of [['riff', 'lead'], ['melody', 'voice']]) {
    if (!song[name]) continue;
    const spec = typeof song[name] === 'string' ? { notes: song[name] } : song[name];
    const notes = [];
    for (const e of looped(parseSeq(spec.notes, notesOf), beats)) notes.push(note(e.at, e.len * 0.95, e.item));
    const i = spec.inst || inst;
    parts[name] = { label: spec.label || (name === 'melody' ? 'Vocal melody' : LINE_LABEL[i]), inst: i, strum: STRUMMED.has(i), notes };
  }

  const order = (song.order || ORDER).filter(n => parts[n]);
  for (const n of Object.keys(parts)) if (!order.includes(n)) order.push(n);
  return { order, parts };
}

// Where each part sits in the stereo field, how much reverb it gets, and its level in the mix.
const FX = {
  drums: { pan: 0, wet: 0.08, mix: 0.9 },
  bass: { pan: 0, wet: 0, mix: 0.85 },
  chords: { pan: -0.3, wet: 0.18, mix: 0.6 },
  riff: { pan: 0.3, wet: 0.2, mix: 0.65 },
  melody: { pan: 0, wet: 0.22, mix: 0.85 },
};

const curves = new Map();
function driveCurve(k) {
  if (!curves.has(k)) {
    const c = new Float32Array(1024);
    for (let i = 0; i < c.length; i++) {
      const x = (i / (c.length - 1)) * 2 - 1;
      c[i] = Math.tanh(k * x) / Math.tanh(k);
    }
    curves.set(k, c);
  }
  return curves.get(k);
}

// Offline rendering keeps every node alive to the end, so filters and envelopes come from a
// small pool of chains reused once their last note has died away; only oscillators are per note.
function pool(make) {
  const chains = [];
  return (t, until) => {
    let c = chains.find(x => x.free <= t);
    if (!c) chains.push((c = make()));
    c.free = until;
    return c;
  };
}

// Plays an instrument. Every pitch of one strike (a chord, strummed `spread` seconds a string)
// shares one drive, filter and envelope, as strings through one amp would.
function player(ctx, out, inst) {
  const [a, dec, sus, rel] = inst.env;
  const chain = pool(() => {
    const c = { g: ctx.createGain() };
    c.g.gain.value = 0;
    c.g.connect(out);
    c.head = c.g;
    if (inst.lp) {
      c.fl = ctx.createBiquadFilter();
      c.fl.type = 'lowpass';
      c.fl.Q.value = inst.q || 0.7;
      c.fl.connect(c.head);
      c.head = c.fl;
    }
    if (inst.drive) {
      const ws = ctx.createWaveShaper();
      ws.curve = driveCurve(inst.drive);
      ws.connect(c.head);
      c.head = ws;
    }
    if (inst.vib) {
      const lfo = ctx.createOscillator();
      c.lg = ctx.createGain();
      c.lg.gain.value = 0;
      lfo.frequency.value = inst.vib[0];
      lfo.connect(c.lg);
      lfo.start(0);
    }
    return c;
  });
  return (ms, t, d, v, spread = 0) => {
    const end = t + Math.max(d, a + 0.01), stop = end + rel + 0.05;
    const c = chain(t, stop + 0.01);
    c.g.gain.setValueAtTime(0, t);
    c.g.gain.linearRampToValueAtTime(v, t + a);
    c.g.gain.setTargetAtTime(Math.max(v * sus, 0.0001), t + a, dec / 3);
    c.g.gain.setTargetAtTime(0, end, rel / 3);
    if (c.fl) {
      c.fl.frequency.setValueAtTime(inst.lp[0], t);
      c.fl.frequency.exponentialRampToValueAtTime(inst.lp[1], t + inst.lp[2]);
    }
    if (c.lg) {
      const [, depth, delay] = inst.vib;
      c.lg.gain.setValueAtTime(0, t);
      c.lg.gain.setValueAtTime(0, t + delay);
      c.lg.gain.linearRampToValueAtTime(depth, t + delay + 0.25);
    }
    ms.forEach((m, i) => {
      for (const [type, cents, level] of inst.osc) {
        const o = ctx.createOscillator(), og = ctx.createGain();
        o.type = type;
        o.frequency.value = freq(m);
        o.detune.value = cents;
        og.gain.value = level / Math.sqrt(ms.length);
        if (c.lg) c.lg.connect(o.detune);
        o.connect(og);
        og.connect(c.head);
        o.start(t + i * spread);
        o.stop(stop);
      }
    });
  };
}

function drumKit(ctx, out) {
  const nb = ctx.createBuffer(1, SR, SR);
  const nd = nb.getChannelData(0);
  for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;
  const chains = {};
  const hit = (t, dur, vol, type, f, q = 1, attack = 0.001) => {
    const id = `${type}${f}${q}`;
    chains[id] = chains[id] || pool(() => {
      const fl = ctx.createBiquadFilter(), g = ctx.createGain();
      fl.type = type;
      fl.frequency.value = f;
      fl.Q.value = q;
      g.gain.value = 0;
      fl.connect(g);
      g.connect(out);
      return { fl, g };
    });
    const c = chains[id](t, t + dur + 0.03);
    c.g.gain.setValueAtTime(0.0001, t);
    c.g.gain.linearRampToValueAtTime(vol, t + attack);
    c.g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    c.g.gain.setValueAtTime(0, t + dur + 0.01);
    const s = ctx.createBufferSource();
    s.buffer = nb;
    s.connect(c.fl);
    s.start(t, Math.random() * 0.8);
    s.stop(t + dur + 0.02);
  };
  const tone = (t, type, f, f2, dur, vol) => {
    const c = (chains[type] = chains[type] || pool(() => {
      const g = ctx.createGain();
      g.gain.value = 0;
      g.connect(out);
      return { g };
    }))(t, t + dur + 0.03);
    const o = ctx.createOscillator();
    o.type = type;
    o.frequency.setValueAtTime(f, t);
    o.frequency.exponentialRampToValueAtTime(f2, t + dur * 0.4);
    c.g.gain.setValueAtTime(vol, t);
    c.g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    c.g.gain.setValueAtTime(0, t + dur + 0.01);
    o.connect(c.g);
    o.start(t);
    o.stop(t + dur + 0.02);
  };
  return {
    k: (t, v) => { tone(t, 'sine', 150, 46, 0.32, v); hit(t, 0.02, v * 0.25, 'lowpass', 3000); },
    s: (t, v) => { hit(t, 0.18, v * 0.6, 'highpass', 1400); tone(t, 'triangle', 200, 165, 0.09, v * 0.45); },
    c: (t, v) => { for (const dt of [0, 0.011, 0.022]) hit(t + dt, 0.03, v * 0.5, 'bandpass', 1300, 1.5); hit(t + 0.03, 0.16, v * 0.5, 'bandpass', 1200, 1.2); },
    h: (t, v) => hit(t, 0.045, v * 0.3, 'highpass', 7500),
    o: (t, v) => hit(t, 0.28, v * 0.25, 'highpass', 6500),
    t: (t, v) => { tone(t, 'sine', 125, 82, 0.38, v * 0.85); hit(t, 0.05, v * 0.12, 'lowpass', 900); },
    r: (t, v) => { tone(t, 'triangle', 850, 820, 0.035, v * 0.35); hit(t, 0.03, v * 0.35, 'bandpass', 2600, 3); },
    z: (t, v) => hit(t, 0.07, v * 0.22, 'highpass', 5500, 1, 0.018),
  };
}

function reverb(ctx, seconds = 1.6) {
  const ir = ctx.createBuffer(1, Math.ceil(seconds * SR), SR);
  const d = ir.getChannelData(0);
  for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / d.length, 3);
  const cv = ctx.createConvolver();
  cv.normalize = true;
  cv.buffer = ir;
  return cv;
}

// Renders one part to a mono AudioBuffer (mix() pans it); returns { buf, rms }.
export async function renderPart(name, part) {
  const ctx = new OfflineAudioContext(1, Math.ceil((CLIP + TAIL) * SR), SR);
  const fx = FX[name] || FX.riff;
  const bus = ctx.createGain(), out = ctx.destination;
  bus.connect(out);
  if (fx.wet) {
    const send = ctx.createGain(), cv = reverb(ctx);
    send.gain.value = fx.wet;
    bus.connect(send);
    send.connect(cv);
    cv.connect(out);
  }
  if (part.drums) {
    const kit = drumKit(ctx, bus);
    for (const h of part.hits) kit[h.drum](h.t, h.v);
  } else {
    const inst = INST[part.inst];
    if (!inst) throw new Error(`unknown instrument "${part.inst}"`);
    const play = player(ctx, bus, inst);
    for (const n of part.notes) play(n.m, n.t, n.d, n.v * 0.5, part.strum ? 0.012 : 0);
  }
  const buf = await ctx.startRendering();
  const d = buf.getChannelData(0);
  let sum = 0;
  for (let i = 0; i < d.length; i += 4) sum += d[i] * d[i];
  return { buf, rms: Math.sqrt(sum / (d.length / 4)) || 1 };
}

// Mixes rendered parts into one stereo buffer made on ctx: each part at an even loudness, its
// FX.mix level and pan, peak-normalized, with a short fade in and a fade out at the end.
export function mix(ctx, rendered) {
  const len = Math.ceil((CLIP + TAIL) * SR);
  const buf = ctx.createBuffer(2, len, SR);
  for (const [name, r] of Object.entries(rendered)) {
    const fx = FX[name] || FX.riff, k = (fx.mix * 0.12) / r.rms;
    const angle = ((fx.pan + 1) * Math.PI) / 4, src = r.buf.getChannelData(0);
    [Math.cos(angle), Math.sin(angle)].forEach((g, ch) => {
      const dst = buf.getChannelData(ch);
      for (let i = 0; i < len; i++) dst[i] += src[i] * k * g * Math.SQRT2;
    });
  }
  let peak = 0;
  for (let ch = 0; ch < 2; ch++) for (const x of buf.getChannelData(ch)) peak = Math.max(peak, Math.abs(x));
  const k = peak > 0 ? 0.9 / peak : 1;
  const fadeIn = 0.01 * SR, fadeFrom = (CLIP - 0.4) * SR;
  for (let ch = 0; ch < 2; ch++) {
    const d = buf.getChannelData(ch);
    for (let i = 0; i < len; i++) {
      let g = k;
      if (i < fadeIn) g *= i / fadeIn;
      if (i > fadeFrom) g *= Math.max(0, 1 - (i - fadeFrom) / (len - fadeFrom));
      d[i] *= g;
    }
  }
  return buf;
}
