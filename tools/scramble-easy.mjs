// Finds Scramble segments too easy to bother with: ones a player gets through by holding right, or
// by holding right and jumping on a steady beat, without looking.
//
//     node tools/scramble-easy.mjs [variants per segment, default 3] [--first] [-v] [segment name ...]
//
// Each segment is built several times at the hardest difficulty (and at the first obstacle's, with
// --first) and played by every lazy strategy: run only, then run while pressing jump for h steps every
// p steps (several holds, beats and starting points), some of them air-dashing a set time into every
// jump, each arriving at several different race times. A segment fails if more than 12% of the
// arrivals get through any build by running alone, or more than 12% of the beats do (15% at the
// first obstacle's difficulty). Exits 1 if any
// segment fails. The builds are shared out between worker threads, one per core.
//
// It also checks the server's copy of where the timed hazards are (app/scramble/hazards.py, which
// the bots look ahead with) against physics.js, at random places and times on every build.
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdtempSync } from 'node:fs';
import { availableParallelism, tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { Worker, isMainThread, parentPort, workerData } from 'node:worker_threads';

const LIMIT = 30;   // seconds to give up after
const MAX_LAST = 0.12, MAX_FIRST = 0.15;   // the share of lazy runs that may get through (the first obstacle is meant to be the easiest)
const STARTS = [0, 0.37, 0.81, 1.29, 1.76, 2.43];   // race times to arrive at (moving pieces in another place each)
const RUN_STARTS = Array.from({ length: 24 }, (_, i) => i * 0.29);   // more for running alone (one strategy: cheap)

// a beat: jump held h steps every per steps from step ph; and, with `dash`, the dash pressed that
// many steps into each jump (so every jump ends in an air dash)
const beats = [];
for (const dash of [0, 12, 30]) {
  for (const h of [4, 16, 40]) for (let per = h + 8; per <= 120; per += 8) for (let ph = 0; ph < per; ph += Math.max(4, per >> 2)) {
    if (!dash || per > dash + 6) beats.push([h, per, ph, dash]);
  }
}
const beat = ([h, per, ph, dash]) => i => {
  const u = (i + ph) % per;
  return { jump: u < h, dash: dash > 0 && u >= dash && u < dash + 4 };
};

function play(P, c, press, t0) {
  const goal = c.segs[2] + 40;
  const p = P.spawn(c, 0);
  p.x = c.segs[1] - 60;
  for (let i = 0; i * P.DT < LIMIT; i++) {
    P.step(p, { dir: 1, ...press(i) }, t0 + i * P.DT, c);
    if (p.dead) return false;
    if (p.ground && p.x >= goal) return true;
  }
  return false;
}

function judge(P, raw) {
  const c = P.prepare(raw);
  const run = RUN_STARTS.filter(t0 => play(P, c, () => ({ jump: false }), t0)).length / RUN_STARTS.length;
  let won = 0;
  for (const t0 of STARTS) won += beats.filter(b => play(P, c, beat(b), t0)).length;
  return { run, share: won / beats.length / STARTS.length };
}

// physics.js's killing checks for the timed hazards, for a racer standing with feet at x, y
function caught(P, c, x, y, t) {
  const HALF = P.PW / 2;
  const touches = (cx, cy, r) => {
    const nx = Math.max(x - HALF, Math.min(cx, x + HALF)), ny = Math.max(y - P.PH, Math.min(cy, y));
    return (cx - nx) ** 2 + (cy - ny) ** 2 < r * r;
  };
  const hits = (bx, by, w, h) => x + HALF > bx && x - HALF < bx + w && y > by && y - P.PH < by + h;
  return c.saws.some(s => touches(P.posX(s, t), P.posY(s, t), s.r - 3))
    || c.bars.some(b => P.barBalls(b, t).some(([bx, by]) => touches(bx, by, P.BAR_R - 2)))
    || c.cannons.some(cn => P.shots(cn, t).some(([bx, by]) => touches(bx, by, P.BULLET_R - 2)))
    || c.crushers.some(m => hits(P.posX(m, t) + 3, P.posY(m, t) + 3, m.w - 6, m.h - 6))
    || c.jets.some(j => P.jetOn(j, t) && hits(j.x + 4, j.y + 4, j.w - 8, j.h - 8));
}

if (!isMainThread) {
  const P = await import(workerData.physics);
  parentPort.on('message', ({ i, course }) => {
    const out = judge(P, course);
    const c = P.prepare(course);
    out.mismatch = course.samples.filter(([x, y, t, hit]) => caught(P, c, x, y, t) !== hit).length;
    parentPort.postMessage({ i, ...out });
  });
} else {
  const root = join(dirname(fileURLToPath(import.meta.url)), '..');
  const tmp = mkdtempSync(join(tmpdir(), 'scramble-'));
  copyFileSync(join(root, 'app/static/games/scramble/js/physics.js'), join(tmp, 'physics.mjs'));
  const physics = pathToFileURL(join(tmp, 'physics.mjs')).href;

  const args = process.argv.slice(2);
  const variants = +args.find(a => /^\d+$/.test(a)) || 3;
  const first = args.includes('--first');
  const MAX = first ? MAX_FIRST : MAX_LAST;
  const verbose = args.includes('-v');
  const only = args.filter(a => !/^\d+$/.test(a) && !a.startsWith('-'));
  // the builds, each with points (x, y, t) and whether hazards.py says a racer there then is caught
  const { d, courses } = JSON.parse(execFileSync('python3', ['-c', `
import json, random
from app.scramble import course
from app.scramble.hazards import Hazards
only = ${JSON.stringify(only)}
d = course.D_FIRST if ${first ? 'True' : 'False'} else course.D_LAST
out = []
for make in course.SEGMENTS:
    name = make(random.Random(0), 0.5).name
    if only and make.__name__[4:] not in only and name not in only:
        continue
    for seed in range(${variants}):
        c, legs, risks, alts = course.build(seed + 7, 1, [make], d)
        c["theme"] = "meadow"
        hz, r = Hazards(c), random.Random(seed)
        pts = [(r.uniform(c["segs"][1], c["segs"][2]), r.uniform(-300, 60), r.uniform(0, 20)) for _ in range(400)]
        c["samples"] = [[x, y, t, hz.hit(x, y, t)] for x, y, t in pts]
        out.append(c)
print(json.dumps({"d": d, "courses": out}))`], { cwd: root, maxBuffer: 1 << 28 }));

  const results = new Array(courses.length);
  let next = 0;
  await Promise.all(Array.from({ length: Math.min(availableParallelism(), courses.length) }, () => new Promise((res, rej) => {
    const w = new Worker(fileURLToPath(import.meta.url), { workerData: { physics } });
    const feed = () => {
      if (next >= courses.length) { w.terminate(); res(); return; }
      const i = next++;
      w.postMessage({ i, course: courses[i] });
    };
    w.on('message', ({ i, ...r }) => { results[i] = r; feed(); });
    w.on('error', rej);
    w.on('online', feed);
  })));

  let bad = 0, mismatch = 0;
  const by = {};
  courses.forEach((c, i) => {
    (by[c.names[1]] ||= []).push(results[i]);
    if (results[i].mismatch) {
      mismatch++;
      console.log(`DIFFER ${c.names[1]}: hazards.py and physics.js disagree at ${results[i].mismatch} of ${c.samples.length} points`);
    }
  });
  for (const [name, rs] of Object.entries(by)) {
    const worst = Math.max(...rs.map(r => r.share)), run = Math.max(...rs.map(r => r.run));
    const fail = run > MAX || worst > MAX;
    if (fail) bad++;
    if (fail || verbose) console.log(`${fail ? 'EASY ' : '     '} ${name.padEnd(18)} running up to ${(run * 100).toFixed(0)}%, beats up to ${(worst * 100).toFixed(0)}%`);
  }
  console.log(bad ? `${bad} of ${Object.keys(by).length} segments too easy (difficulty ${d})`
    : `ok: no segment beaten by lazy play (${courses.length} builds, difficulty ${d})`);
  if (mismatch) console.log(`${mismatch} builds where the bots' hazards differ from the physics`);
  process.exit(bad || mismatch ? 1 : 0);
}
