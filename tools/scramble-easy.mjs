// Finds Scramble segments too easy to bother with: ones a player gets through by holding right, or
// by holding right and jumping on a steady beat, without looking.
//
//     node tools/scramble-easy.mjs [variants per segment, default 3] [segment name ...]
//
// Each segment is built several times at the hardest difficulty (and at the first obstacle's, with
// --first) and played by every lazy strategy: run only, then run while pressing jump for h steps every
// p steps (several holds, beats and starting points), each arriving at several different race times.
// A segment fails if more than a fifth of the arrivals get through any build by running alone, or
// more than a fifth of the beats do. Exits 1 if any segment fails.
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const tmp = mkdtempSync(join(tmpdir(), 'scramble-'));
copyFileSync(join(root, 'app/static/games/scramble/js/physics.js'), join(tmp, 'physics.mjs'));
const P = await import(pathToFileURL(join(tmp, 'physics.mjs')).href);

const args = process.argv.slice(2);
const variants = +args.find(a => /^\d+$/.test(a)) || 3;
const first = args.includes('--first');
const verbose = args.includes('-v');
const only = args.filter(a => !/^\d+$/.test(a) && !a.startsWith('-'));
const D = JSON.parse(execFileSync('python3', ['-c', 'from app.scramble import course; print([course.D_FIRST, course.D_LAST])'], { cwd: root }));
const d = first ? D[0] : D[1];
const courses = JSON.parse(execFileSync('python3', ['-c', `
import json, random
from app.scramble import course
only = ${JSON.stringify(only)}
out = []
for make in course.SEGMENTS:
    name = make(random.Random(0), 0.5).name
    if only and make.__name__[4:] not in only and name not in only:
        continue
    for seed in range(${variants}):
        c, legs, risks, alts = course.build(seed + 7, 1, [make], ${d})
        c["theme"] = "meadow"
        out.append(c)
print(json.dumps(out))`], { cwd: root, maxBuffer: 1 << 28 }));

const LIMIT = 30, MAX = 0.2;   // seconds to give up after; the share of lazy runs that may get through
const STARTS = [0, 0.37, 0.81, 1.29, 1.76, 2.43];   // race times to arrive at (moving pieces in another place each)
function play(c, jumpAt, t0) {
  const goal = c.segs[2] + 40;
  const p = P.spawn(c, 0);
  p.x = c.segs[1] - 60;
  for (let i = 0; i * P.DT < LIMIT; i++) {
    P.step(p, { dir: 1, jump: jumpAt(i) }, t0 + i * P.DT, c);
    if (p.dead) return false;
    if (p.ground && p.x >= goal) return true;
  }
  return false;
}
const beats = [];
for (const h of [4, 16, 40]) for (let per = h + 8; per <= 120; per += 8) for (let ph = 0; ph < per; ph += Math.max(4, per >> 2)) beats.push([h, per, ph]);

let bad = 0;
const by = {};
for (const raw of courses) {
  const name = raw.names[1], c = P.prepare(raw);
  const run = STARTS.filter(t0 => play(c, () => false, t0)).length / STARTS.length;
  let won = 0;
  for (const t0 of STARTS) won += beats.filter(([h, per, ph]) => play(c, i => (i + ph) % per < h, t0)).length;
  (by[name] ||= []).push({ run, share: won / beats.length / STARTS.length });
}
for (const [name, rs] of Object.entries(by)) {
  const worst = Math.max(...rs.map(r => r.share)), run = Math.max(...rs.map(r => r.run));
  const fail = run > MAX || worst > MAX;
  if (fail) bad++;
  if (fail || verbose) console.log(`${fail ? 'EASY ' : '     '} ${name.padEnd(18)} running up to ${(run * 100).toFixed(0)}%, beats up to ${(worst * 100).toFixed(0)}%`);
}
console.log(bad ? `${bad} of ${Object.keys(by).length} segments too easy (difficulty ${d})` : `ok: no segment beaten by lazy play (${courses.length} builds, difficulty ${d})`);
process.exit(bad ? 1 : 0);
