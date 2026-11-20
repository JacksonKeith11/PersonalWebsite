// Proves Scramble's obstacle segments can be got through, by searching the game's own physics.
//
//     node tools/scramble-check.mjs [variants per segment, default 3] [segment name ...]
//
// Each segment is built several times over (they vary at random) between a start and a finish, and
// a breadth-first search over what a player could press (run, run and jump, wait, back up; never the
// air dash, so every segment can be done without it) must reach the far side alive. The themes that
// change what's underfoot (snow's ice, the dunes' sand) get a hard variant of every segment too. Prints the
// fastest time found for each. The searches are shared out between worker threads, one per core.
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdtempSync } from 'node:fs';
import { availableParallelism, tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';

const ACTIONS = [{ dir: 1, jump: false }, { dir: 1, jump: true }, { dir: 0, jump: false }, { dir: -1, jump: false }, { dir: 0, jump: true }];
const HOLD = 8;          // physics steps per decision (1/15 s)
const BEAM = 600, LIMIT = 24;   // states kept per level; seconds before giving up

function solve(P, raw) {
  const c = P.prepare(raw);
  const from = 1;
  const goal = c.segs[from + 1] + 40;
  const first = P.spawn(c, from - 1);
  first.x = c.segs[from] - 60;
  let level = [first];
  const times = o => Object.values(o).map(v => v.toFixed(1));
  for (let n = 0; n * HOLD * P.DT < LIMIT; n++) {
    const seen = new Map();
    for (const s of level) {
      for (const a of ACTIONS) {
        const p = { ...s };
        for (let i = 0; i < HOLD && !p.dead; i++) P.step(p, a, (n * HOLD + i) * P.DT, c);
        if (p.dead || p.x < c.segs[from] - 90) continue;
        if (p.ground && p.x >= goal) return (n + 1) * HOLD * P.DT;
        // (in a barrel, when you got in matters: one that fires by itself does so a set time after.
        // On ice, how fast you are going matters, as it takes a while to change; finer than this and
        // the search keeps too many ways of going the same speed and loses the way up the lava. Flung
        // from a barrel, nobody steers, so the speed matters then too.)
        const slow = c.theme === 'snow' || p.fling > 0 || c.zones.some(z => z.kind === 2);
        const vx = slow ? Math.round(p.vx / 100) : Math.sign(Math.round(p.vx / 100));
        const key = `${Math.round(p.x / 8)},${Math.round(p.y / 8)},${Math.round(p.vy / 150)},${vx},${p.held ? 1 : 0},${p.barrel},${p.barrel >= 0 ? Math.round(p.barrelT * 30) : ''},${times(p.lava)},${times(p.chase)}`;
        if (!seen.has(key)) seen.set(key, p);
      }
    }
    level = [...seen.values()];
    // keep the furthest along, counting a player with their feet on something as well ahead of one
    // in mid-air (who may be on the way down a pit); but only so many from each stretch of the
    // course, so those waiting further back for something to come round aren't crowded out by
    // those ahead (on a platform about to vanish, say)
    const rank = p => p.x + (p.ground ? 400 : 0);
    if (level.length > BEAM) {
      level.sort((a, b) => rank(b) - rank(a));
      const per = new Map(), kept = [], rest = [];
      for (const p of level) {
        const k = Math.floor(p.x / 64);
        if ((per.get(k) || 0) < BEAM / 12) { per.set(k, (per.get(k) || 0) + 1); kept.push(p); } else rest.push(p);
      }
      level = kept.length >= BEAM ? kept.slice(0, BEAM) : kept.concat(rest.slice(0, BEAM - kept.length));
    }
    if (!level.length) return null;
  }
  return null;
}

if (!isMainThread) {
  const P = await import(workerData.physics);
  parentPort.on('message', ({ i, course }) => parentPort.postMessage({ i, secs: solve(P, course) }));
} else {
  const root = join(dirname(fileURLToPath(import.meta.url)), '..');
  const tmp = mkdtempSync(join(tmpdir(), 'scramble-'));
  copyFileSync(join(root, 'app/static/games/scramble/js/physics.js'), join(tmp, 'physics.mjs'));
  const physics = pathToFileURL(join(tmp, 'physics.mjs')).href;

  const args = process.argv.slice(2);
  const variants = +args.find(a => /^\d+$/.test(a)) || 3;
  const only = args.filter(a => !/^\d+$/.test(a));
  const courses = JSON.parse(execFileSync('python3', ['-c', `
import json
from app.scramble import course
only = ${JSON.stringify(only)}
out = []
for make in course.SEGMENTS:
    if only and make.__name__[4:] not in only and make(__import__("random").Random(0), 0.5).name not in only:
        continue
    for theme, n in (("meadow", ${variants}), ("snow", 1), ("desert", 1)):
        for seed in range(n):
            for d in ((course.D_FIRST, course.D_LAST) if theme == "meadow" else (course.D_LAST,)):
                c, legs, risks, alts = course.build(seed + 100 * (theme != "meadow"), 1, [make], d)
                c["hard"], c["theme"] = d > course.D_FIRST, theme
                out.append(c)
print(json.dumps(out))`], { cwd: root, maxBuffer: 1 << 28 }));

  const label = c => c.names[1] + (c.theme === 'meadow' ? '' : `/${c.theme}`);
  const results = new Array(courses.length);
  let next = 0;
  await Promise.all(Array.from({ length: Math.min(availableParallelism(), courses.length) }, () => new Promise((res, rej) => {
    const w = new Worker(fileURLToPath(import.meta.url), { workerData: { physics } });
    const feed = () => {
      if (next >= courses.length) { w.terminate(); res(); return; }
      const i = next++;
      w.postMessage({ i, course: courses[i] });
    };
    w.on('message', ({ i, secs }) => { results[i] = secs; feed(); });
    w.on('error', rej);
    w.on('online', feed);
  })));

  let failed = 0;
  const best = {};
  courses.forEach((c, i) => {
    const name = label(c);
    if (results[i] == null) { failed++; console.log(`STUCK  ${name}: no way through variant ${i}${c.hard ? ' (hard)' : ''}`); return; }
    (best[name] ||= []).push(results[i]);
  });
  for (const [name, times] of Object.entries(best)) {
    console.log(`${name.padEnd(18)} ${times.length} variants, ${Math.min(...times).toFixed(1)}-${Math.max(...times).toFixed(1)} s`);
  }
  if (failed || Object.keys(best).length < new Set(courses.map(label)).size) { console.log('FAILED'); process.exit(1); }
  console.log(`ok: every segment can be finished (${courses.length} courses searched)`);
}
