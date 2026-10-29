// Checks Frag Arena's two copies of the movement physics agree: app/arena/world.py (bots) and
// app/static/games/arena/js/physics.js (your own player, in the browser). Both walk, jump, strafe
// and ride a jump pad through the same inputs; their paths must match.
//
//     node tools/arena-parity.mjs
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';
import path from 'path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const { setWorld, move } = await import(path.join(root, 'app/static/games/arena/js/physics.js'));

// The same input script in both languages: a function of the step number.
const STEPS = 4000;
const pyScript = `
import json, math, sys
sys.path.insert(0, '.')
from app.arena import world
out = []
for start in ((20, 0, 26), (14, 0, 0), (0, 0, 13)):
    b = world.Body(*start)
    yaw = math.atan2(start[0], start[2] + 0.1)
    path = []
    for i in range(${STEPS}):
        if i % 90 == 0:
            yaw += 0.7 * math.sin(i)
        jump = (i // 60) % 3 == 0
        wx, wz = -math.sin(yaw), -math.cos(yaw)
        if (i // 200) % 2:
            wx, wz = wx + math.cos(yaw) * 0.7, wz - math.sin(yaw) * 0.7
        world.move(b, wx, wz, jump, 1 / 125)
        if i % 50 == 49:
            path.append(b.pos[:])
    out.append(path)
print(json.dumps({"paths": out, "map": world.map_payload(), "phys": world.PHYS}))
`;
const py = JSON.parse(execFileSync('python3', ['-c', pyScript], { cwd: root }).toString());
setWorld(py.map, py.phys);

let worst = 0, travelled = 0;
[[20, 0, 26], [14, 0, 0], [0, 0, 13]].forEach((start, k) => {
  const b = { pos: start.slice(), vel: [0, 0, 0], ground: false };
  let yaw = Math.atan2(start[0], start[2] + 0.1);
  let n = 0;
  for (let i = 0; i < STEPS; i++) {
    if (i % 90 === 0) yaw += 0.7 * Math.sin(i);
    const jump = Math.floor(i / 60) % 3 === 0;
    let wx = -Math.sin(yaw), wz = -Math.cos(yaw);
    if (Math.floor(i / 200) % 2) { wx += Math.cos(yaw) * 0.7; wz -= Math.sin(yaw) * 0.7; }
    move(b, wx, wz, jump, 1 / 125);
    if (i % 50 === 49) {
      const q = py.paths[k][n++];
      worst = Math.max(worst, Math.hypot(b.pos[0] - q[0], b.pos[1] - q[1], b.pos[2] - q[2]));
    }
  }
  travelled += Math.hypot(b.pos[0] - start[0], b.pos[2] - start[2]);
});
console.log(`largest gap between the two: ${worst.toExponential(1)} m (paths moved ${travelled.toFixed(0)} m)`);
if (worst > 1e-3 || travelled < 5) {
  console.log('FAILED: world.py and physics.js disagree');
  process.exit(1);
}
console.log('OK');
