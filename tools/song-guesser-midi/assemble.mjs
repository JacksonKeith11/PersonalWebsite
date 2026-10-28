// Merges choruses pulled out by extract.py into songs.js, replacing each song's arrangement
// fields and keeping its title, year, genre, tier and section.
// usage: node assemble.mjs DONE.json, where DONE.json maps song titles to extract.py outputs. A song
// not in songs.js yet is added at the end of SONGS (and dropped from EXTRA): map its title to
// { out, artist, year, genre, tier, section } instead of a path.
import fs from 'fs';
const file = new URL('../../app/static/games/song-guesser/js/songs.js', import.meta.url).pathname;
const { SONGS } = await import('file://' + file + '?t=' + Date.now());
const done = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B'];
const L = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
const midi = n => { const m = /^([A-G])([#b]?)(\d)$/.exec(n); return 12 * (+m[3] + 1) + L[m[1]] + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0); };
const name = m => NAMES[m % 12] + (Math.floor(m / 12) - 1);
// move a line by whole octaves so its middle sits in [lo, hi]
function center(text, lo, hi, floor = 0, ceil = 127) {
  const ps = text.split(/\s+/).flatMap(t => { const n = t.split(':')[0]; return n === '-' ? [] : n.split('+').map(midi); }).sort((a, b) => a - b);
  if (!ps.length) return text;
  const med = ps[ps.length >> 1];
  let k = 0;
  while (med + k > hi) k -= 12;
  while (med + k < lo) k += 12;
  const fold = m => { while (m < floor) m += 12; while (m > ceil) m -= 12; return m; };
  return text.split(/\s+/).map(t => { const [n, l] = t.split(':'); if (n === '-') return t; return n.split('+').map(x => name(fold(midi(x) + k))).join('+') + (l !== undefined ? ':' + l : ''); }).join(' ');
}
const q = v => JSON.stringify(v).replace(/"([a-zA-Z]+)":/g, '$1: ').replace(/"/g, "'").replace(/,(?=[a-zA-Z{'])/g, ', ');
const str = s => (s.includes("'") ? JSON.stringify(s) : `'${s}'`);
let text = fs.readFileSync(file, 'utf8');
let n = 0;
const added = [];
for (const [title, entry] of Object.entries(done)) {
  const out = typeof entry === 'string' ? entry : entry.out;
  const old = SONGS.find(s => s.title === title) || { title, section: 'Chorus', ...entry };
  const { song: m } = JSON.parse(fs.readFileSync(out, 'utf8'));
  const lines = [];
  lines.push(`    title: ${str(old.title)}, artist: ${str(old.artist)}, year: ${old.year}, genre: ${str(old.genre)}, tier: '${old.tier}', section: '${old.section}', source: 'midi',`);
  const head = [`bpm: ${m.bpm}`];
  if (m.meter) head.push(`meter: ${m.meter}`);
  if (m.drums) head.push('fill: false', 'crash: false');
  lines.push(`    ${head.join(', ')},`);
  lines.push(`    drums: ${m.drums ? q(m.drums) : str(typeof old.drums === 'string' ? old.drums : 'rock')},`);
  if (!m.bass && !m.guitar && old.chords) lines.push(`    chords: ${str(old.chords)},`);
  if (m.bass) lines.push(`    bass: '${center(m.bass, 33, 45, 28, 55)}',`);
  else if (old.bass) lines.push(`    bass: ${str(old.bass)},`);
  lines.push(`    guitar: ${m.guitar ? `{ inst: '${m.guitar.inst}', notes: '${m.guitar.notes}' }` : 'null'},`);
  if (m.riff) lines.push(`    riff: { inst: '${m.riff.inst}', notes: '${m.riff.notes}' },`);
  const mel = m.melody;
  const extra = [mel.inst && `inst: '${mel.inst}'`, mel.label && `label: ${str(mel.label)}`].filter(Boolean).join(', ');
  lines.push(`    melody: { ${extra ? extra + ', ' : ''}notes: '${center(mel.notes, 55, 69, 45, 84)}' },`);
  const block = `  {\n${lines.join('\n')}\n  },\n`;
  const key = `  {\n    title: ${str(old.title)}`;
  const a = text.indexOf(key);
  if (a < 0) {
    if (typeof entry === 'string') { console.log('not found', title); continue; }
    added.push(block);
    // a title that only padded the guess list is a real song now
    text = text.split('\n').map(line => {
      const m2 = /^(  (['"])(.*?)\2: )(\[.*\]),$/.exec(line);
      if (!m2 || m2[3] !== old.artist) return line;
      const titles = Function(`return ${m2[4]}`)().filter(t => t !== title);
      return `${m2[1]}[${titles.map(str).join(', ')}],`;
    }).join('\n');
    n++;
    continue;
  }
  const b = text.indexOf('\n  },\n', a) + '\n  },\n'.length;
  text = text.slice(0, a) + block + text.slice(b);
  n++;
}
if (added.length) {
  const end = text.indexOf('\n];\n');
  text = text.slice(0, end + 1) + '\n  // Added from MIDI transcriptions, chosen for a clear vocal track and a record to check against\n' + added.join('') + text.slice(end + 1);
}
fs.writeFileSync(file, text);
console.log(`replaced or added ${n} (${added.length} new)`);
