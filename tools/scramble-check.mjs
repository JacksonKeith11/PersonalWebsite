// Proves Scramble's obstacle segments can be got through, by searching the game's own physics.
//
//     node tools/scramble-check.mjs [variants per segment, default 3]
//
// Each segment is built several times over (they vary at random) between a start and a finish, and
// a breadth-first search over what a player could press (run, run and jump, wait, back up) must
// reach the far side alive. Prints the fastest time found for each. About 45 seconds.
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const tmp = mkdtempSync(join(tmpdir(), 'scramble-'));
copyFileSync(join(root, 'app/static/games/scramble/js/physics.js'), join(tmp, 'physics.mjs'));
const P = await import(pathToFileURL(join(tmp, 'physics.mjs')));

const variants = +process.argv[2] || 3;
const courses = JSON.parse(execFileSync('python3', ['-c', `
import json
from app.scramble import course
out = []
for make in course.SEGMENTS:
    for seed in range(${variants}):
        for d in (0.35, 1.0):
            c, legs, risks = course.build(seed, 1, [make], d)
            c["hard"] = d > 0.5
            out.append(c)
print(json.dumps(out))`], { cwd: root, maxBuffer: 1 << 28 }));

const ACTIONS = [{ dir: 1, jump: false }, { dir: 1, jump: true }, { dir: 0, jump: false }, { dir: -1, jump: false }, { dir: 0, jump: true }];
const HOLD = 8;          // physics steps per decision (1/15 s)
const BEAM = 600, LIMIT = 20;   // states kept per level; seconds before giving up

function solve(raw) {
  const c = P.prepare(raw);
  const from = 1;
  const goal = c.segs[from + 1] + 40;
  const first = P.spawn(c, from - 1);
  first.x = c.segs[from] - 60;
  let level = [first];
  for (let n = 0; n * HOLD * P.DT < LIMIT; n++) {
    const seen = new Map();
    for (const s of level) {
      for (const a of ACTIONS) {
        const p = { ...s };
        for (let i = 0; i < HOLD && !p.dead; i++) P.step(p, a, (n * HOLD + i) * P.DT, c);
        if (p.dead || p.x < c.segs[from] - 90) continue;
        if (p.ground && p.x >= goal) return (n + 1) * HOLD * P.DT;
        const key = `${Math.round(p.x / 8)},${Math.round(p.y / 8)},${Math.round(p.vy / 150)},${Math.sign(Math.round(p.vx / 100))},${p.held ? 1 : 0}`;
        if (!seen.has(key)) seen.set(key, p);
      }
    }
    level = [...seen.values()];
    // keep the furthest along, counting a player with their feet on something as well ahead of one
    // in mid-air (who may be on the way down a pit)
    const rank = p => p.x + (p.ground ? 400 : 0);
    if (level.length > BEAM) level = level.sort((a, b) => rank(b) - rank(a)).slice(0, BEAM);
    if (!level.length) return null;
  }
  return null;
}

let failed = 0;
const best = {};
for (const c of courses) {
  const name = c.names[1];
  const secs = solve(c);
  if (secs == null) { failed++; console.log(`STUCK  ${name}: no way through a variant${c.hard ? ' (hard)' : ''}`); continue; }
  (best[name] ||= []).push(secs);
}
for (const [name, times] of Object.entries(best)) {
  console.log(`${name.padEnd(8)} ${times.length} variants, ${Math.min(...times).toFixed(1)}-${Math.max(...times).toFixed(1)} s`);
}
if (failed || Object.keys(best).length < 16) { console.log('FAILED'); process.exit(1); }
console.log(`ok: every segment can be finished (${courses.length} courses searched)`);
