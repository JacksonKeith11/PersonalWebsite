// Checks Song Guesser's arrangements without a browser: every song parses and arranges, parts
// loop in whole bars and line up with the chords, every clip is a chorus (or refrain), and the
// guess list has no duplicates.
// Notes outside the key the chords imply are listed too; those are often typos, sometimes real.
// Usage: node tools/song-guesser-check.js
const path = require('path');
const { pathToFileURL } = require('url');

const dir = path.join(__dirname, '..', 'app', 'static', 'games', 'song-guesser', 'js');
const load = f => import(pathToFileURL(path.join(dir, f)).href);
const NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'];

(async () => {
  const { SONGS, EXTRA } = await load('songs.js');
  const { arrange, parseSeq, parseChord, midiOf, GROOVES, INSTRUMENTS } = await load('synth.js');
  const notesOf = n => n.split('+').map(midiOf);
  let errors = 0;
  const err = (song, msg) => { errors++; console.log(`ERROR ${song.title}: ${msg}`); };
  const warn = (song, msg) => console.log(`  warn ${song.title}: ${msg}`);
  const seen = new Set();

  for (const song of SONGS) {
    const key = `${song.title}|${song.artist}`.toLowerCase();
    if (seen.has(key)) err(song, 'listed twice');
    seen.add(key);
    for (const f of ['title', 'artist', 'year', 'genre', 'tier', 'section', 'bpm']) if (!song[f]) err(song, `missing ${f}`);
    // only transcribed songs have a vocal line; the hand-written ones were dropped as unreliable
    if (song.source === 'midi' && !song.melody) err(song, 'missing melody');
    if (song.source !== 'midi' && song.melody) err(song, 'hand-written melody (only MIDI songs carry one)');
    if (!['indie', 'alt', 'pop', 'other'].includes(song.tier)) err(song, `bad tier ${song.tier}`);
    // the clip is the chorus; songs without one use their refrain
    if (song.section && !['Chorus', 'Refrain'].includes(song.section)) err(song, `section is "${song.section}", not Chorus or Refrain`);
    if (typeof song.drums === 'string' && !GROOVES[song.drums]) err(song, `unknown groove ${song.drums}`);
    for (const p of ['guitar', 'riff', 'melody']) {
      const inst = song[p] && song[p].inst;
      if (inst && !INSTRUMENTS.includes(inst)) err(song, `unknown instrument ${inst}`);
    }
    let arr;
    try { arr = arrange(song); } catch (e) { err(song, e.message); continue; }
    if (arr.order.length < 3) err(song, `only ${arr.order.length} instruments`);

    const meter = song.meter || 4;
    const lens = {};
    const pcs = new Array(12).fill(0);
    const lines = {};
    try {
      if (song.chords) {
        const c = parseSeq(song.chords, parseChord);
        lens.chords = c.total;
        for (const e of c.events) for (const i of e.item.ivs) pcs[(e.item.root + i) % 12] += e.len;
      }
      for (const p of ['bass', 'riff', 'melody']) {
        const spec = song[p];
        if (!spec || (p === 'bass' && /^[a-z0-9]+$/.test(spec))) continue;
        const seq = parseSeq(typeof spec === 'string' ? spec : spec.notes, notesOf);
        lens[p] = seq.total;
        lines[p] = seq;
      }
      if (song.guitar && song.guitar.notes) lens.guitar = parseSeq(song.guitar.notes, notesOf).total;
    } catch (e) { err(song, e.message); continue; }
    for (const [p, len] of Object.entries(lens)) {
      if (Math.abs(len / meter - Math.round(len / meter)) > 1e-9) err(song, `${p} is ${len} beats, not whole bars of ${meter}`);
      if (lens.chords && p !== 'chords') {
        const a = Math.max(len, lens.chords), b = Math.min(len, lens.chords);
        if (Math.abs(a / b - Math.round(a / b)) > 1e-9) warn(song, `${p} (${len} beats) and chords (${lens.chords}) drift apart`);
      }
    }
    // The major scale holding most chord time stands in for the key.
    if (song.chords) {
      let best = 0, bestScore = -1;
      for (let k = 0; k < 12; k++) {
        const score = [0, 2, 4, 5, 7, 9, 11].reduce((s, i) => s + pcs[(k + i) % 12], 0);
        if (score > bestScore) { best = k; bestScore = score; }
      }
      const scale = new Set([0, 2, 4, 5, 7, 9, 11].map(i => (best + i) % 12));
      const chordPcs = new Set(pcs.map((v, i) => (v ? i : -1)).filter(i => i >= 0));
      for (const [p, seq] of Object.entries(lines)) {
        const odd = new Set();
        for (const e of seq.events) for (const m of e.item) if (!scale.has(m % 12) && !chordPcs.has(m % 12)) odd.add(NAMES[m % 12]);
        if (odd.size) warn(song, `${p} has ${[...odd].join(' ')}, outside ${NAMES[best]} major`);
      }
    }
    for (const n of arr.order) {
      const part = arr.parts[n];
      const count = part.drums ? part.hits.length : part.notes.length;
      if (!count) err(song, `${n} is silent in the clip`);
      for (const x of part.notes || []) for (const m of x.m) if (m < 28 || m > 96) err(song, `${n} note ${m} out of range`);
    }
  }

  for (const [artist, titles] of Object.entries(EXTRA)) {
    for (const title of titles) {
      const key = `${title}|${artist}`.toLowerCase();
      if (seen.has(key)) console.log(`ERROR guess list: ${title} by ${artist} is listed twice`), errors++;
      seen.add(key);
    }
  }

  const tiers = SONGS.reduce((t, s) => ({ ...t, [s.tier]: (t[s.tier] || 0) + 1 }), {});
  console.log(`${SONGS.length} songs (${Object.entries(tiers).map(([k, v]) => `${v} ${k}`).join(', ')}), ${seen.size} in the guess list`);
  if (errors) { console.log(`${errors} error(s)`); process.exit(1); }
  console.log('ok');
})();
