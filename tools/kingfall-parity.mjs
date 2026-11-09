// Checks that the browser's move maths (app/static/games/kingfall/js/moves.js) and the server's
// (app/kingfall/geom.py, content/moves.py) agree: Python places every boss's hits at many times and
// tests them against many points; this replays the same cases in JS and fails on any difference.
//     node tools/kingfall-parity.mjs
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const tmp = mkdtempSync(join(tmpdir(), 'kf-'));
copyFileSync(join(root, 'app/static/games/kingfall/js/moves.js'), join(tmp, 'moves.mjs'));
const { LiveMove, placeHit, touches } = await import(join(tmp, 'moves.mjs'));

const py = `
import json, math, random, sys
sys.path.insert(0, ${JSON.stringify(root)})
from app.kingfall import content as C
from app.kingfall.fight import Move
from app.kingfall.geom import place_hit, touches
from app.kingfall.content.moves import resolve
R = random.Random(3)
cases = []
for bid, B in C.BOSSES.items():
  for body in (B.get("bodies") or [B]):
    moves = dict(body["moves"])
    for ph, pm in body.get("phase_moves", {}).items(): moves[f"phase{ph}"] = pm
    for mid, m in moves.items():
        for _ in range(6):
            aim = R.uniform(-math.pi, math.pi)
            dists = resolve(m, 0.0, R.uniform(20, 250), [0.0] * len(m["motion"]))
            mv = Move(1, 0, mid, m, 10.0, (R.uniform(100, 700), R.uniform(100, 400)), aim, dists)
            for lt in m.get("locks", [])[1:]:
                mv.aims.append((lt, R.uniform(-math.pi, math.pi)))
                mv.dists = resolve(m, lt, R.uniform(20, 250), mv.dists)
            wire = {"seq": 1, "id": mid, "at": 10.0, "x": mv.origin[0], "y": mv.origin[1], "a": aim, "d": dists}
            for _ in range(25):
                t = R.uniform(0, m["dur"] + 1)
                real = [i for i, h in enumerate(m["hits"]) if h["k"] != "spawn"]
                hi = R.choice(real) if real else None
                px, py = mv.pos(10.0 + t)
                pt = (px + R.uniform(-120, 120), py + R.uniform(-120, 120))
                s = place_hit(mv, m["hits"][hi], t) if hi is not None else None
                cases.append({"boss": bid, "body": (B.get("bodies") or [B]).index(body), "move": mid, "wire": wire, "aims": mv.aims, "dists": mv.dists, "t": t, "hit": hi,
                              "pos": [px, py], "pt": pt, "touch": bool(s and touches(s, pt[0], pt[1], 8))})
print(json.dumps({"cases": cases, "data": C.client()}))
`;
const out = JSON.parse(execFileSync('python3', ['-c', py], { maxBuffer: 1 << 28 }).toString());
let bad = 0;
for (const c of out.cases) {
  const B = (out.data.bosses[c.boss].bodies || [out.data.bosses[c.boss]])[c.body];
  const data = c.move.startsWith('phase') ? B.phase_moves[c.move.slice(5)] : B.moves[c.move];
  const mv = new LiveMove(c.wire, data);
  mv.aims = c.aims; mv.dists = c.dists;
  const [x, y] = mv.pos(c.t);
  if (Math.abs(x - c.pos[0]) > 0.01 || Math.abs(y - c.pos[1]) > 0.01) { bad++; if (bad < 5) console.log('position differs', c.boss, c.move, c.t, [x, y], c.pos); }
  if (c.hit !== null) {
    const s = placeHit(mv, data.hits[c.hit], c.t);
    const touch = !!(s && touches(s, c.pt[0], c.pt[1], 8));
    if (touch !== c.touch) { bad++; if (bad < 5) console.log('hit differs', c.boss, c.move, c.hit, c.t); }
  }
}
console.log(`${out.cases.length} cases, ${bad} differ`);
process.exit(bad ? 1 : 0);
