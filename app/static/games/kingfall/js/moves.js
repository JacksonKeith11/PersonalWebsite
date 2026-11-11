// Boss moves in the browser: where the boss is during a move, where each hit's shape is, and
// whether it touches a hero. The server has the motion half of this in app/kingfall/content/moves.py.
// Shapes are in the aim's frame: x forward, y to the right. Angles: radians, except the shapes'
// a0/a1/a/gaps, which are degrees (as written in the content files).

const D2R = Math.PI / 180;

export const ease = u => { u = Math.min(1, Math.max(0, u)); return 1 - (1 - u) * (1 - u); };

export function aimAt(aims, t) {
  let a = aims[0][1];
  for (const [at, ang] of aims) if (at <= t) a = ang;
  return a;
}

// A move in progress: built from the server's 'mv' message, updated by 'aim' and 'cancel'.
export class LiveMove {
  constructor(m, data) {
    this.seq = m.seq; this.id = m.id; this.data = data;
    this.start = m.at; this.origin = [m.x, m.y];
    this.aims = [[0, m.a]];
    this.dists = m.d.slice();
    this.cancelAt = Infinity;
  }
  reaim(lt, a, d) {
    this.aims = this.aims.filter(([t]) => t < lt);
    this.aims.push([lt, a]);
    this.dists = d.slice();
  }
  end() { return Math.min(this.start + this.data.dur, this.cancelAt); }
  // the boss's position at move time t (seconds from the start)
  pos(t) {
    t = Math.min(t, this.cancelAt - this.start);
    let x = this.origin[0], y = this.origin[1];
    this.data.motion.forEach(([t0, t1], i) => {
      if (t <= t0) return;
      const a = aimAt(this.aims, t0), u = ease((t - t0) / Math.max(1e-6, t1 - t0));
      x += Math.cos(a) * this.dists[i] * u; y += Math.sin(a) * this.dists[i] * u;
    });
    return [x, y];
  }
  aim(t) { return aimAt(this.aims, t); }
}

// Where a hit's shape is at move time t: {k, cx, cy, a, ...} in world space, or null if it isn't live.
// lead: also return it this long before it starts (for ground marks).
export function placeHit(mv, h, t, lead = 0) {
  if (t < h.t0 - lead || t > h.t1 || mv.start + t > mv.cancelAt) return null;
  const k = h.k;
  if (k === 'spawn') return null;
  const rot = (h.rot || 0) * D2R;
  const fx = (h.x || 0) + (h.tx ? mv.dists[mv.data.motion.length] || 0 : 0);
  if (k === 'proj' || k === 'ring' || k === 'zone') {
    // anchored where the boss stood when it was fired
    const [bx, by] = mv.pos(h.t0), a = mv.aim(h.t0) + rot;
    const ox = bx + Math.cos(a) * fx - Math.sin(a) * (h.y || 0);
    const oy = by + Math.sin(a) * fx + Math.cos(a) * (h.y || 0);
    const dt = Math.max(0, t - h.t0);
    if (k === 'proj') {
      const pa = a + (h.a || 0) * D2R;
      return { k, cx: ox + Math.cos(pa) * h.v * dt, cy: oy + Math.sin(pa) * h.v * dt, a: pa, r: h.r, live: t >= h.t0 };
    }
    if (k === 'zone') return { k, cx: ox, cy: oy, a, r: h.r, live: t >= h.t0, pool: h.pool };
    return { k, cx: ox, cy: oy, a, r: h.r0 + h.v * dt, th: h.th, gaps: h.gaps, live: t >= h.t0 };
  }
  const tt = Math.max(t, h.t0);
  const [bx, by] = mv.pos(tt), a = mv.aim(tt) + rot;
  if (k === 'circle') {
    return { k, cx: bx + Math.cos(a) * fx - Math.sin(a) * h.y, cy: by + Math.sin(a) * fx + Math.cos(a) * h.y, a, r: h.r, live: t >= h.t0 };
  }
  return { ...h, k, cx: bx, cy: by, a, live: t >= h.t0 };
}

// Does placed shape s touch a circle at (px, py) of radius pr?
export function touches(s, px, py, pr) {
  const dx = px - s.cx, dy = py - s.cy;
  const d = Math.hypot(dx, dy);
  switch (s.k) {
    case 'circle': case 'proj': case 'zone': return d < s.r + pr;
    case 'arc': {
      if (d > s.r + pr) return false;
      if (d < pr + 6) return true;
      const rel = wrap(Math.atan2(dy, dx) - s.a) / D2R;
      const slack = Math.asin(Math.min(1, pr / d)) / D2R;
      return rel >= s.a0 - slack && rel <= s.a1 + slack;
    }
    case 'rect': {
      const fx = Math.cos(s.a) * dx + Math.sin(s.a) * dy, fy = -Math.sin(s.a) * dx + Math.cos(s.a) * dy;
      return fx >= s.x0 - pr && fx <= s.x1 + pr && Math.abs(fy) <= s.w + pr;
    }
    case 'ring': {
      if (Math.abs(d - s.r) > s.th / 2 + pr) return false;
      const rel = wrap(Math.atan2(dy, dx) - s.a) / D2R;
      return !(s.gaps || []).some(([g0, g1]) => rel >= g0 && rel <= g1);
    }
  }
  return false;
}

export const wrap = a => { while (a > Math.PI) a -= 2 * Math.PI; while (a < -Math.PI) a += 2 * Math.PI; return a; };

// A hero's attack shape placed at their feet, aimed at angle a.
export function placeAttack(shape, x, y, a) {
  if (shape.k === 'circle') return { k: 'circle', cx: x + Math.cos(a) * shape.x - Math.sin(a) * (shape.y || 0), cy: y + Math.sin(a) * shape.x + Math.cos(a) * (shape.y || 0), r: shape.r, a };
  return { ...shape, cx: x, cy: y, a };
}
