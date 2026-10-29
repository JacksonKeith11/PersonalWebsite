// Movement and ray tests. A copy of app/arena/world.py's physics: keep the two in step.
// The server sends the constants (PHYS) and the map in its welcome message.

export const W = { boxes: [], pads: [], P: null };
const EPS = 1e-5;

export function setWorld(map, phys) {
  W.boxes = map.boxes.map(b => b.slice(0, 6));
  W.pads = map.pads.map(([x, y, z, r, vx, vy, vz]) => ({ x, y, z, r, v: [vx, vy, vz] }));
  W.P = phys;
}

export function playerHits(boxes, x, y, z) {
  const { radius: R, height: H } = W.P;
  const out = [];
  for (const b of boxes) {
    if (b[0] < x + R - EPS && b[3] > x - R + EPS && b[1] < y + H - EPS && b[4] > y + EPS &&
        b[2] < z + R - EPS && b[5] > z - R + EPS) out.push(b);
  }
  return out;
}

export function insideSolid(x, y, z) { return playerHits(W.boxes, x, y, z).length > 0; }

// Distance along a ray (unit direction) to box b, or null if it misses within tmax.
export function rayBox(o, d, b, tmax) {
  let t0 = 0, t1 = tmax;
  for (let i = 0; i < 3; i++) {
    const lo = b[i], hi = b[i + 3];
    if (Math.abs(d[i]) < 1e-9) {
      if (o[i] < lo || o[i] > hi) return null;
      continue;
    }
    let a = (lo - o[i]) / d[i], c = (hi - o[i]) / d[i];
    if (a > c) [a, c] = [c, a];
    if (a > t0) t0 = a;
    if (c < t1) t1 = c;
    if (t0 > t1) return null;
  }
  return t0;
}

export function rayWorld(o, d, tmax) {
  let best = tmax;
  for (const b of W.boxes) {
    const t = rayBox(o, d, b, best);
    if (t !== null && t < best) best = t;
  }
  return best;
}

export function playerBox(x, y, z, grow = 0) {
  const { radius: R, height: H } = W.P;
  return [x - R - grow, y - grow, z - R - grow, x + R + grow, y + H + grow, z + R + grow];
}

function moveAxis(cands, pos, axis, d) {
  if (d === 0) return false;
  const { radius: R, height: H } = W.P;
  pos[axis] += d;
  const hits = playerHits(cands, pos[0], pos[1], pos[2]);
  if (!hits.length) return false;
  if (axis === 1) {
    pos[1] = d < 0 ? Math.max(...hits.map(b => b[4])) : Math.min(...hits.map(b => b[1])) - H;
  } else if (d > 0) {
    pos[axis] = Math.min(...hits.map(b => b[axis])) - R;
  } else {
    pos[axis] = Math.max(...hits.map(b => b[axis + 3])) + R;
  }
  return true;
}

function moveFlat(cands, pos, dx, dz, ground) {
  const start = pos.slice();
  const bx = moveAxis(cands, pos, 0, dx);
  const bz = moveAxis(cands, pos, 2, dz);
  if (!(bx || bz) || !ground) return [bx, bz, 0];
  // Blocked on the ground: try again a step higher, then settle back down.
  const up = [start[0], start[1] + W.P.step, start[2]];
  if (playerHits(cands, up[0], up[1], up[2]).length) return [bx, bz, 0];
  const ux = moveAxis(cands, up, 0, dx);
  const uz = moveAxis(cands, up, 2, dz);
  moveAxis(cands, up, 1, -W.P.step);
  if (Math.hypot(up[0] - start[0], up[2] - start[2]) > Math.hypot(pos[0] - start[0], pos[2] - start[2]) + 1e-4) {
    const rise = up[1] - pos[1];
    pos[0] = up[0]; pos[1] = up[1]; pos[2] = up[2];
    return [ux, uz, rise];
  }
  return [bx, bz, 0];
}

function accelerate(v, wx, wz, wishspeed, accel, dt) {
  const add = wishspeed - (v[0] * wx + v[2] * wz);
  if (add <= 0) return;
  const a = Math.min(accel * dt * wishspeed, add);
  v[0] += a * wx;
  v[2] += a * wz;
}

// One physics step for body {pos, vel, ground}. (wx, wz) is the wished direction, length 0..1.
// Returns what happened worth a sound or a camera nudge.
export function move(body, wx, wz, jump, dt) {
  const P = W.P, p = body.pos, v = body.vel;
  const out = { jumped: false, landed: 0, pad: false, stepped: 0 };
  const wish = Math.hypot(wx, wz);
  if (wish > 1e-6) { wx /= wish; wz /= wish; }
  const wishspeed = P.speed * Math.min(wish, 1);

  if (body.ground && jump) {
    v[1] = P.jump;
    body.ground = false;
    out.jumped = true;
  }
  if (body.ground) {
    const speed = Math.hypot(v[0], v[2]);
    if (speed > 0) {
      const drop = Math.max(speed, P.stop_speed) * P.friction * dt;
      const scale = Math.max(speed - drop, 0) / speed;
      v[0] *= scale;
      v[2] *= scale;
    }
    accelerate(v, wx, wz, wishspeed, P.accel, dt);
  } else {
    accelerate(v, wx, wz, wishspeed, P.air_accel, dt);
    v[1] -= P.gravity * dt;
  }

  const dx = v[0] * dt, dy = v[1] * dt, dz = v[2] * dt;
  const R = P.radius, reach = Math.abs(dx) + Math.abs(dz) + P.step + 0.1;
  const loY = p[1] - P.step - Math.abs(dy) - 0.1, hiY = p[1] + P.height + P.step + Math.abs(dy) + 0.1;
  const cands = W.boxes.filter(b => b[0] < p[0] + R + reach && b[3] > p[0] - R - reach &&
    b[2] < p[2] + R + reach && b[5] > p[2] - R - reach && b[1] < hiY && b[4] > loY);

  const [bx, bz, rise] = moveFlat(cands, p, dx, dz, body.ground);
  if (bx) v[0] = 0;
  if (bz) v[2] = 0;
  out.stepped = rise;

  if (body.ground) {
    // Stay glued to the floor walking down steps; walking off an edge starts a fall.
    const probe = p.slice();
    if (moveAxis(cands, probe, 1, -P.step)) {
      out.stepped -= p[1] - probe[1];
      p[1] = probe[1];
      v[1] = 0;
    } else {
      body.ground = false;
    }
  } else {
    const fall = v[1];
    if (moveAxis(cands, p, 1, dy)) {
      if (v[1] < 0) { body.ground = true; out.landed = -fall; }
      v[1] = 0;
    }
  }

  if (body.ground) {
    for (const pad of W.pads) {
      if (Math.abs(p[1] - pad.y) < 0.05 && Math.hypot(p[0] - pad.x, p[2] - pad.z) < pad.r) {
        v[0] = pad.v[0]; v[1] = pad.v[1]; v[2] = pad.v[2];
        body.ground = false;
        out.pad = true;
        break;
      }
    }
  }
  return out;
}
