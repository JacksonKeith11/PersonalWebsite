// Song Guesser's synthesizer. Every song in songs.js is a short text arrangement; arrange() turns
// one into timed notes per instrument, and renderPart() plays a part into an AudioBuffer with
// OfflineAudioContext. Nothing is downloaded: every sound is built here, guitars and basses as
// plucked strings (Karplus-Strong), voices through vowel formants, drums from noise and oscillators.

export const SR = 44100; // older Safari can't render offline audio at lower rates
export const CLIP = 15; // seconds of each song the player hears
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
// z shaker, y crash. x is a hit, X an accent and g a ghost note; a bar's steps share it evenly.
// Grooves with a snare or clap also get a crash on the first beat and a snare fill every 4 bars.
export const GROOVES = {
  rock: { k: 'x.......x.x.....', s: '....x.......x...', h: 'X.x.X.x.X.x.X.x.' },
  drive: { k: 'x.......x.x.....', s: '....x.......x...', h: 'XxgxXxgxXxgxXxgx' },
  motorik: { k: 'x...x...x...x...', s: '....x.......x...', h: 'Xxxxxxxxxxxxxxxx' },
  disco: { k: 'x...x...x...x...', s: '....x.......x...', h: 'x...x...x...x...', o: '..x...x...x...x.' },
  four: { k: 'x...x...x...x...', s: '....g.......g...' },
  half: { k: 'x.......x.......', s: '........x.......', h: 'X.x.x.x.X.x.x.x.' },
  stomp: { k: 'x.....x.x.......', c: '....x.......x...', h: '..g...g...g...g.' },
  shaker: { k: 'x.......x.......', r: '....x.......x...', z: 'XxgxXxgxXxgxXxgx' },
  onedrop: { k: '........x.......', r: '........x.......', h: 'X.x.x.x.X.x.x.x.' },
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

// ks: a plucked string [seconds to die away, brightness 0..1]; osc: [type, detune cents, level];
// drive: distortion amount; hp/lp: highpass Hz and lowpass [from Hz, to Hz, over seconds], which
// after a drive act as the speaker cabinet; env: [attack, decay, sustain level, release];
// vib: [rate Hz, depth cents, delay]; vowels: sung through formant filters; double: a second
// string detuned by this ratio, as on a mandolin.
const INST = {
  bass: { ks: [2.5, 0.35], osc: [['sine', 0, 0.25]], lp: [1500, 900, 0.3], env: [0.002, 9, 1, 0.05] },
  guitar: { ks: [2.2, 0.6], hp: 90, lp: [6500, 6500, 1], env: [0.001, 9, 1, 0.08] },
  clean: { ks: [3, 0.5], hp: 100, lp: [4200, 4200, 1], env: [0.001, 9, 1, 0.1] },
  dist: { ks: [5, 0.85], drive: 30, hp: 110, lp: [3400, 3400, 1], env: [0.001, 9, 1, 0.05] },
  lead: { ks: [5, 0.85], drive: 12, hp: 150, lp: [4200, 4200, 1], env: [0.001, 9, 1, 0.08] },
  mandolin: { ks: [0.9, 0.85], double: 1.004, hp: 200, lp: [7000, 7000, 1], env: [0.001, 9, 1, 0.05] },
  piano: { osc: [['triangle', 0, 0.7], ['sine', 1200, 0.25], ['square', 0, 0.05]], lp: [4500, 1500, 0.6], env: [0.002, 0.9, 0, 0.25] },
  organ: { osc: [['sine', 0, 0.5], ['sine', 1200, 0.3], ['sine', 1902, 0.15], ['sine', 2400, 0.1]], env: [0.01, 1, 1, 0.05], vib: [6, 6, 0] },
  synth: { osc: [['sawtooth', 8, 0.3], ['sawtooth', -8, 0.3], ['sawtooth', 0, 0.2]], lp: [2600, 1400, 0.4], env: [0.01, 0.4, 0.6, 0.2] },
  square: { osc: [['square', 0, 0.35], ['square', 1200, 0.08]], lp: [5000, 3000, 0.3], env: [0.004, 0.25, 0.55, 0.05] },
  strings: { osc: [['sawtooth', 7, 0.2], ['sawtooth', -7, 0.2], ['sawtooth', 0, 0.2]], lp: [2400, 2400, 1], env: [0.08, 1, 0.9, 0.25], vib: [5, 8, 0.2] },
  horn: { osc: [['sawtooth', 0, 0.5], ['sawtooth', 7, 0.3]], lp: [700, 2200, 0.09], env: [0.04, 0.3, 0.85, 0.12], vib: [5, 10, 0.3] },
  saw: { osc: [['sine', 0, 0.8], ['triangle', 0, 0.2]], env: [0.15, 1, 1, 0.3], vib: [5.5, 30, 0.1] },
  voice: { osc: [['sawtooth', 0, 0.6], ['sawtooth', 9, 0.3]], vowels: true, env: [0.04, 0.4, 0.85, 0.12], vib: [5.2, 22, 0.25] },
  bell: { osc: [['sine', 0, 0.6], ['sine', 2786, 0.2]], env: [0.002, 0.7, 0, 0.4] },
  whistle: { osc: [['sine', 0, 0.8]], env: [0.03, 1, 0.9, 0.08], vib: [6, 15, 0.15] },
};
export const INSTRUMENTS = Object.keys(INST);
const STRUMMED = new Set(['guitar', 'dist', 'clean', 'mandolin']);
const CHORD_LABEL = { guitar: 'Guitar', dist: 'Guitar', clean: 'Guitar', piano: 'Piano', organ: 'Organ', synth: 'Synth', strings: 'Strings', mandolin: 'Mandolin' };
const LINE_LABEL = { lead: 'Lead guitar', dist: 'Guitar riff', guitar: 'Guitar line', clean: 'Guitar line', piano: 'Piano', synth: 'Synth lead', square: 'Synth lead', horn: 'Horns', saw: 'Singing saw', voice: 'Backing vocal', bell: 'Bells', whistle: 'Whistle', strings: 'Strings', organ: 'Organ', mandolin: 'Mandolin' };
const ORDER = ['drums', 'bass', 'chords', 'riff', 'melody'];

// Vowel formants (Hz) for a tenor-ish voice; a melody cycles through them like made-up words.
const VOWELS = [[650, 1080, 2650], [400, 800, 2600], [400, 1700, 2600], [650, 1080, 2650], [350, 600, 2700], [290, 1870, 2800]];
const FORMANT_GAIN = [1, 0.55, 0.3];

// Beats to seconds, with swing pushing each off-beat eighth later.
function timer(song) {
  const spb = 60 / song.bpm, sw = song.swing || 0.5;
  return b => {
    const i = Math.floor(b), f = b - i;
    return spb * (i + (f < 0.5 ? (f / 0.5) * sw : sw + ((f - 0.5) / 0.5) * (1 - sw)));
  };
}

// A small seeded random generator, so a song plays the same human-ish way every time.
function rng(text) {
  let a = 0;
  for (const ch of text) a = (Math.imul(a ^ ch.charCodeAt(0), 2654435761) >>> 0);
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
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
  const rand = rng(song.title);
  const jit = s => (rand() * 2 - 1) * s; // timing and loudness wobble, as a band plays
  const meter = song.meter || 4;
  const beats = (CLIP * song.bpm) / 60;
  const note = (at, len, m, v = 1, wobble = 0.004) => {
    const t = Math.max(0, time(at) + jit(wobble));
    return { t, d: time(at + len) - time(at), m, v: v * (1 + jit(0.08)) };
  };
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
    const band = groove.s || groove.c;
    const hit = (at, drum, v) => { if (at < beats) hits.push({ t: Math.max(0, time(at) + jit(0.005)), drum, v: v * (1 + jit(0.1)) }); };
    for (let bar = 0; bar * meter < beats; bar++) {
      const fill = band && song.fill !== false && bar % 4 === 3;
      for (const [drum, pat] of Object.entries(groove)) {
        const step = meter / pat.length;
        [...pat].forEach((c, i) => {
          const at = bar * meter + i * step;
          if (fill && at >= bar * meter + meter - 1 && drum !== 'k') return; // the fill owns the last beat
          if (c !== '.') hit(at, drum, c === 'X' ? 1.25 : c === 'g' ? 0.4 : 1);
        });
      }
      if (fill) for (let i = 0; i < 4; i++) hit(bar * meter + meter - 1 + i / 4, i < 2 ? 's' : 't', 0.55 + i * 0.15);
    }
    if (band && song.crash !== false) {
      for (let bar = 0; bar * meter < beats; bar += 8) hit(bar * meter, 'y', 1);
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
          notes.push(note(at, Math.min(tpl.step, c.at + c.len - at) * tpl.len, [tpl.note(m, i)], i ? 0.85 : 1));
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
        notes.push(note(at, step * 2.5, [m], i % 2 ? 0.75 : 0.9));
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
        const up = i % 2 === 1;
        if (up) v = [...v].reverse();
        cur = { chord: c, n: { ...note(at, step, v, up ? 0.75 : 1), up } };
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
// wide: the right channel is delayed this many seconds, like a double-tracked guitar.
const FX = {
  drums: { pan: 0, wet: 0.1, mix: 0.9 },
  bass: { pan: 0, wet: 0, mix: 0.8 },
  chords: { pan: -0.15, wet: 0.15, mix: 0.62, wide: 0.014 },
  riff: { pan: 0.3, wet: 0.18, mix: 0.62 },
  melody: { pan: 0, wet: 0.22, mix: 0.9 },
};

const curves = new Map();
function driveCurve(k) {
  if (!curves.has(k)) {
    const c = new Float32Array(2048);
    for (let i = 0; i < c.length; i++) {
      const x = (i / (c.length - 1)) * 2 - 1;
      c[i] = Math.tanh(k * x) / Math.tanh(k);
    }
    curves.set(k, c);
  }
  return curves.get(k);
}

// Karplus-Strong: a burst of noise circulating in a delay line one period long, softened a little
// each pass, sounds like a plucked string. Each string is made once per page and reused.
const strings = new Map();
function pluck(m, [life, bright]) {
  const key = `${m}:${life}:${bright}`;
  if (!strings.has(key)) {
    const period = SR / freq(m), n = Math.max(2, Math.floor(period));
    const len = Math.ceil(Math.min(life, 4) * SR);
    const out = new Float32Array(len), ring = new Float32Array(n);
    let y = 0;
    const soft = 0.15 + 0.85 * bright; // a darker pluck starts with smoother noise
    for (let i = 0; i < n; i++) { y += soft * (Math.random() * 2 - 1 - y); ring[i] = y; }
    const loss = Math.pow(10, -3 / (life * freq(m))); // reaches -60 dB after `life` seconds
    const s = 0.5 - 0.35 * bright; // less averaging keeps a bright string's overtones longer
    let peak = 0;
    for (let i = 0; i < len; i++) {
      const j = i % n, k = j + 1 === n ? 0 : j + 1;
      out[i] = ring[j];
      ring[j] = loss * ((1 - s) * ring[j] + s * ring[k]);
      peak = Math.max(peak, Math.abs(out[i]));
    }
    for (let i = 0; i < len; i++) out[i] /= peak || 1;
    strings.set(key, { data: out, rate: n / period }); // play slower by the period's fraction
  }
  return strings.get(key);
}

// Offline rendering keeps every node alive to the end, so filters and envelopes come from a
// small pool of chains reused once their last note has died away; only sources are per note.
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
  const buffers = new Map();
  const bufferOf = m => {
    if (!buffers.has(m)) {
      const s = pluck(m, inst.ks), b = ctx.createBuffer(1, s.data.length, SR);
      b.getChannelData(0).set(s.data);
      buffers.set(m, { b, rate: s.rate });
    }
    return buffers.get(m);
  };
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
    if (inst.hp) {
      const hp = ctx.createBiquadFilter();
      hp.type = 'highpass';
      hp.frequency.value = inst.hp;
      hp.connect(c.head);
      c.head = hp;
    }
    if (inst.drive) {
      const ws = ctx.createWaveShaper();
      ws.curve = driveCurve(inst.drive);
      ws.oversample = '2x';
      ws.connect(c.head);
      c.head = ws;
    }
    if (inst.vowels) {
      // a voice: the source runs through three resonances that shape it into a vowel
      const sum = ctx.createGain();
      sum.connect(c.head);
      c.formants = FORMANT_GAIN.map((level, i) => {
        const bp = ctx.createBiquadFilter(), g = ctx.createGain();
        bp.type = 'bandpass';
        bp.Q.value = 6 + i * 3;
        g.gain.value = level * (2 + i);
        bp.connect(g);
        g.connect(sum);
        return bp;
      });
      c.head = ctx.createGain();
      c.formants.forEach(bp => c.head.connect(bp));
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
  let last = null, count = 0; // the previous sung note, to slide from
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
      c.lg.gain.linearRampToValueAtTime(depth, t + delay + 0.3);
    }
    if (c.formants) {
      const vowel = VOWELS[count++ % VOWELS.length];
      c.formants.forEach((bp, i) => bp.frequency.setTargetAtTime(vowel[i], t, 0.02));
    }
    const slide = inst.vowels && last && t - last.end < 0.12 ? last.f : 0;
    ms.forEach((m, i) => {
      const at = t + i * spread;
      if (inst.ks) {
        const { b, rate } = bufferOf(m);
        for (const detune of inst.double ? [1, inst.double] : [1]) {
          const s = ctx.createBufferSource(), sg = ctx.createGain();
          s.buffer = b;
          s.playbackRate.value = rate * detune;
          sg.gain.value = 1 / Math.sqrt(ms.length);
          s.connect(sg);
          sg.connect(c.head);
          s.start(at);
          s.stop(Math.min(stop, at + b.duration));
        }
      }
      for (const [type, cents, level] of inst.osc || []) {
        const o = ctx.createOscillator(), og = ctx.createGain();
        o.type = type;
        if (slide) {
          o.frequency.setValueAtTime(slide, at);
          o.frequency.exponentialRampToValueAtTime(freq(m), at + 0.06);
        } else {
          o.frequency.value = freq(m);
        }
        o.detune.value = cents;
        og.gain.value = level / Math.sqrt(ms.length);
        if (c.lg) c.lg.connect(o.detune);
        o.connect(og);
        og.connect(c.head);
        o.start(at);
        o.stop(stop);
      }
    });
    last = { end, f: freq(ms[ms.length - 1]) };
  };
}

function drumKit(ctx, out) {
  const nb = ctx.createBuffer(1, SR * 2, SR);
  const nd = nb.getChannelData(0);
  for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;
  const chains = {};
  const chainOf = (id, make) => (chains[id] = chains[id] || pool(make));
  const hit = (t, dur, vol, type, f, q = 1, attack = 0.001) => {
    const c = chainOf(`${type}${f}${q}`, () => {
      const fl = ctx.createBiquadFilter(), g = ctx.createGain();
      fl.type = type;
      fl.frequency.value = f;
      fl.Q.value = q;
      g.gain.value = 0;
      fl.connect(g);
      g.connect(out);
      return { fl, g };
    })(t, t + dur + 0.03);
    c.g.gain.setValueAtTime(0.0001, t);
    c.g.gain.linearRampToValueAtTime(vol, t + attack);
    c.g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    c.g.gain.setValueAtTime(0, t + dur + 0.01);
    const s = ctx.createBufferSource();
    s.buffer = nb;
    s.connect(c.fl);
    s.start(t, Math.random() * 1.5);
    s.stop(t + dur + 0.02);
  };
  const tone = (t, type, f, f2, dur, vol, drop = 0.4) => {
    const c = chainOf(type, () => {
      const g = ctx.createGain();
      g.gain.value = 0;
      g.connect(out);
      return { g };
    })(t, t + dur + 0.03);
    const o = ctx.createOscillator();
    o.type = type;
    o.frequency.setValueAtTime(f, t);
    o.frequency.exponentialRampToValueAtTime(f2, t + dur * drop);
    c.g.gain.setValueAtTime(vol, t);
    c.g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    c.g.gain.setValueAtTime(0, t + dur + 0.01);
    o.connect(c.g);
    o.start(t);
    o.stop(t + dur + 0.02);
  };
  // cymbals: six square waves at clashing pitches, filtered high, as classic drum machines do
  const METAL = [205.3, 304.4, 369.6, 522.7, 540, 800].map(f => f * 1.8);
  const metal = (t, dur, vol) => {
    const c = chainOf('metal', () => {
      const bp = ctx.createBiquadFilter(), hp = ctx.createBiquadFilter(), g = ctx.createGain();
      bp.type = 'bandpass';
      bp.frequency.value = 10000;
      bp.Q.value = 0.8;
      hp.type = 'highpass';
      hp.frequency.value = 7000;
      g.gain.value = 0;
      bp.connect(hp);
      hp.connect(g);
      g.connect(out);
      return { bp, g };
    })(t, t + dur + 0.03);
    c.g.gain.setValueAtTime(vol, t);
    c.g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    c.g.gain.setValueAtTime(0, t + dur + 0.01);
    for (const f of METAL) {
      const o = ctx.createOscillator();
      o.type = 'square';
      o.frequency.value = f;
      o.connect(c.bp);
      o.start(t);
      o.stop(t + dur + 0.02);
    }
  };
  return {
    k: (t, v) => { tone(t, 'sine', 165, 48, 0.45, v * 1.1, 0.15); hit(t, 0.012, v * 0.35, 'lowpass', 5000); },
    s: (t, v) => {
      tone(t, 'triangle', 190, 170, 0.12, v * 0.5);
      tone(t, 'sine', 330, 300, 0.07, v * 0.25);
      hit(t, 0.22, v * 0.7, 'bandpass', 3500, 0.8);
      hit(t, 0.12, v * 0.3, 'highpass', 6000);
    },
    c: (t, v) => { for (const dt of [0, 0.011, 0.022]) hit(t + dt, 0.03, v * 0.5, 'bandpass', 1300, 1.5); hit(t + 0.03, 0.16, v * 0.5, 'bandpass', 1200, 1.2); },
    h: (t, v) => { metal(t, 0.05, v * 0.12); hit(t, 0.04, v * 0.12, 'highpass', 8000); },
    o: (t, v) => { metal(t, 0.3, v * 0.1); hit(t, 0.3, v * 0.12, 'highpass', 7000); },
    y: (t, v) => { metal(t, 1.2, v * 0.08); hit(t, 1.6, v * 0.35, 'highpass', 4500); },
    t: (t, v) => { tone(t, 'sine', 140, 85, 0.38, v * 0.85); hit(t, 0.05, v * 0.12, 'lowpass', 900); },
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
    for (const n of part.notes) play(n.m, n.t, n.d, n.v * 0.5, part.strum ? (n.up ? 0.008 : 0.013) : 0);
  }
  const buf = await ctx.startRendering();
  const d = buf.getChannelData(0);
  let sum = 0;
  for (let i = 0; i < d.length; i += 4) sum += d[i] * d[i];
  return { buf, rms: Math.sqrt(sum / (d.length / 4)) || 1 };
}

// Mixes rendered parts into one stereo buffer made on ctx: each part at an even loudness, its
// FX.mix level and pan, then gently saturated like a mastered record, with fades at both ends.
export function mix(ctx, rendered) {
  const len = Math.ceil((CLIP + TAIL) * SR);
  const buf = ctx.createBuffer(2, len, SR);
  for (const [name, r] of Object.entries(rendered)) {
    const fx = FX[name] || FX.riff, k = (fx.mix * 0.12) / r.rms;
    const angle = ((fx.pan + 1) * Math.PI) / 4, src = r.buf.getChannelData(0);
    const lag = Math.round((fx.wide || 0) * SR);
    [Math.cos(angle), Math.sin(angle)].forEach((g, ch) => {
      const dst = buf.getChannelData(ch), shift = ch ? lag : 0, gain = k * g * Math.SQRT2;
      for (let i = shift; i < len; i++) dst[i] += src[i - shift] * gain;
    });
  }
  let peak = 0;
  for (let ch = 0; ch < 2; ch++) for (const x of buf.getChannelData(ch)) peak = Math.max(peak, Math.abs(x));
  const drive = 1.6, k = peak > 0 ? drive / peak : 1, norm = 0.92 / Math.tanh(drive);
  const fadeIn = 0.01 * SR, fadeFrom = (CLIP - 0.4) * SR;
  for (let ch = 0; ch < 2; ch++) {
    const d = buf.getChannelData(ch);
    for (let i = 0; i < len; i++) {
      let g = 1;
      if (i < fadeIn) g *= i / fadeIn;
      if (i > fadeFrom) g *= Math.max(0, 1 - (i - fadeFrom) / (len - fadeFrom));
      d[i] = Math.tanh(d[i] * k) * norm * g;
    }
  }
  return buf;
}
