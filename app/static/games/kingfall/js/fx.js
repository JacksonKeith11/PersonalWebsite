// Kingfall's drawn effects: every swing, thrust, burst, shockwave and projectile in the game is one of
// these, so heroes and bosses share one look. All are filled, tapered shapes meant for a Graphics with
// additive blending (they glow where they overlap): a coloured body and a white-hot core. Shapes are the
// placed hit shapes from moves.js ({cx, cy, a, ...}); `lift` raises a shape off the floor to blade height.

const D2R = Math.PI / 180;
const clamp = u => Math.min(1, Math.max(0, u));
const easeOut = u => 1 - (1 - clamp(u)) * (1 - clamp(u));

function fill(g, pts, col, alpha) {
  if (pts.length < 3 || alpha <= 0.01) return;
  g.fillStyle(col, Math.min(1, alpha));
  g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) g.lineTo(pts[i][0], pts[i][1]);
  g.closePath(); g.fillPath();
}

// One blade-shaped band of a crescent between angles t0..t1 (degrees off the aim): its outer edge on
// radius r, its inner edge thick in the middle and pointed at both ends (sharper at the leading end).
function band(g, s, lift, t0, t1, r, thick, col, alpha) {
  const span = t1 - t0;
  if (Math.abs(span) < 2) return;
  const n = Math.max(6, Math.ceil(Math.abs(span) / 5)), outer = [], inner = [];
  for (let i = 0; i <= n; i++) {
    const q = i / n, a = s.a + (t0 + span * q) * D2R;
    const taper = Math.pow(Math.min(1, q * 1.5), 0.7) * Math.min(1, (1 - q) * 5);
    const c = Math.cos(a), sn = Math.sin(a);
    outer.push([s.cx + c * r, s.cy - lift + sn * r]);
    inner.push([s.cx + c * (r - thick * taper), s.cy - lift + sn * (r - thick * taper)]);
  }
  fill(g, outer.concat(inner.reverse()), col, alpha);
}

// A swing. p runs 0..1 across the strike and on to 2 as its trail dies away. The blade's edge sweeps
// from one end of the arc to the other (rev: from a1 to a0) with the trail catching up behind it.
export function crescent(g, s, p, col, { lift = 12, rev = false, thick = 0.4 } = {}) {
  const head = easeOut(p * 1.15), tail = clamp((p - 0.45) / 1.4), fade = p < 1 ? 1 : clamp(2 - p);
  const from = rev ? s.a1 : s.a0, to = rev ? s.a0 : s.a1;
  const t0 = from + (to - from) * tail, t1 = from + (to - from) * head;
  const T = s.r * thick;
  band(g, s, lift, t0, t1, s.r, T, col, 0.5 * fade);
  band(g, s, lift, t0, t1, s.r * 0.985, T * 0.55, col, 0.5 * fade);
  band(g, s, lift, t0 + (t1 - t0) * 0.25, t1, s.r * 0.97, T * 0.22, 0xffffff, 0.95 * fade);
}

// A thrust or a downward slam along a line: a spearhead that shoots out to full length, then thins away.
export function lance(g, s, p, col, { lift = 12 } = {}) {
  const out = easeOut(p * 1.6), fade = p < 1 ? 1 : clamp(2 - p), thin = p < 1 ? 1 : clamp(2 - p);
  const L = s.x0 + (s.x1 - s.x0) * out, c = Math.cos(s.a), n = Math.sin(s.a);
  const P = (fx, fy) => [s.cx + c * fx - n * fy, s.cy - lift + n * fx + c * fy];
  const blade = (w, col2, alpha) => {
    const b = s.x0 + (L - s.x0) * 0.72;
    fill(g, [P(s.x0, 0), P(s.x0 + (b - s.x0) * 0.5, -w * 0.8), P(b, -w), P(L, 0), P(b, w), P(s.x0 + (b - s.x0) * 0.5, w * 0.8)], col2, alpha);
  };
  blade(s.w * thin, col, 0.45 * fade);
  blade(s.w * 0.6 * thin, col, 0.5 * fade);
  blade(s.w * 0.24 * thin, 0xffffff, 0.95 * fade);
}

// A burst on the floor (a slam, a shield bash, a stomp): a flash that fills the circle and a ring
// that snaps out to its edge.
export function burst(g, s, p, col) {
  const out = easeOut(p * 1.4), fade = p < 1 ? 1 - p * 0.3 : clamp(2 - p) * 0.7;
  g.fillStyle(col, 0.3 * fade * (1 - clamp(p) * 0.6)); g.fillCircle(s.cx, s.cy, s.r * out);
  g.fillStyle(0xffffff, 0.35 * clamp(1 - p * 2.5)); g.fillCircle(s.cx, s.cy, s.r * out * 0.7);
  g.lineStyle(1 + 4 * clamp(1 - p * 0.7), col, 0.85 * fade); g.strokeCircle(s.cx, s.cy, s.r * out);
  g.lineStyle(1, 0xffffff, 0.9 * fade); g.strokeCircle(s.cx, s.cy, s.r * out - 1);
}

// A shockwave ring racing outward; gaps (degrees off the aim) are left dark.
export function shockwave(g, s, life, col) {
  const fade = 1 - clamp(life) * 0.55;
  const arcs = [];
  let from = -180;
  for (const [g0, g1] of (s.gaps || []).slice().sort((x, y) => x[0] - y[0])) { if (g0 > from) arcs.push([from, g0]); from = Math.max(from, g1); }
  if (from < 180) arcs.push([from, 180]);
  const draw = (w, c, alpha, r) => {
    g.lineStyle(w, c, alpha);
    for (const [a0, a1] of arcs) { g.beginPath(); g.arc(s.cx, s.cy, r, s.a + a0 * D2R, s.a + a1 * D2R); g.strokePath(); }
  };
  draw(s.th + 4, col, 0.22 * fade, s.r);
  draw(s.th * 0.7, col, 0.5 * fade, s.r);
  draw(1.5, 0xffffff, 0.9 * fade, s.r + s.th * 0.3);
}

// A glowing projectile: a tapered tail behind it, a soft halo, a coloured body and a white core.
// (x, y) is its place on the floor; it flies `lift` above that, and `floor` gets its shadow.
export function orb(g, floor, x, y, a, r, col, { lift = 10, tail = 3.2, core = 0xffffff } = {}) {
  const c = Math.cos(a), n = Math.sin(a), py = y - lift, L = r * tail + 8;
  if (floor) { floor.fillStyle(0x000000, 0.28); floor.fillEllipse(x, y + 1, r * 1.8, r * 0.6); }
  const T = (w, len) => [[x - n * w, py + c * w], [x - c * len, py - n * len], [x + n * w, py - c * w]];
  fill(g, T(r * 0.95, L), col, 0.3);
  fill(g, T(r * 0.6, L * 0.7), col, 0.45);
  fill(g, T(r * 0.3, L * 0.45), core, 0.6);
  g.fillStyle(col, 0.16); g.fillCircle(x, py, r * 1.9);
  g.fillStyle(col, 0.7); g.fillCircle(x, py, r);
  g.fillStyle(core, 0.95); g.fillCircle(x, py, r * 0.5);
}

// An arrow: a shaft and a head (drawn solid on `solid`) with a thin streak of light behind (on g).
export function arrow(g, solid, floor, x, y, a, { lift = 14 } = {}) {
  const c = Math.cos(a), n = Math.sin(a), py = y - lift;
  if (floor) { floor.fillStyle(0x000000, 0.22); floor.fillEllipse(x - c * 6, y + 1, 12, 2.5); }
  fill(g, [[x - n * 1.6, py + c * 1.6], [x - c * 44, py - n * 44], [x + n * 1.6, py - c * 1.6]], 0xfff0c0, 0.4);
  solid.lineStyle(1.5, 0x8a6a48, 1); solid.lineBetween(x - c * 13, py - n * 13, x, py);
  fill(solid, [[x + c * 4, py + n * 4], [x - c * 2 - n * 2.4, py - n * 2 + c * 2.4], [x - c * 2 + n * 2.4, py - n * 2 - c * 2.4]], 0xe8ecf2, 1);
  fill(solid, [[x - c * 13, py - n * 13], [x - c * 16 - n * 2, py - n * 16 + c * 2], [x - c * 16 + n * 2, py - n * 16 - c * 2]], 0xd8d0c0, 1);
}

// Where a hit landed: a four-point star (long across the blow, short along it) and a ring.
export function impact(g, x, y, a, p, big, col) {
  const k = 1 - clamp(p), L = (big ? 26 : 16) * (0.5 + easeOut(p) * 0.7), W = (big ? 5 : 3.2) * k;
  const star = (ang, len, w, c2, alpha) => {
    const c = Math.cos(ang), n = Math.sin(ang);
    fill(g, [[x - c * len, y - n * len], [x - n * w, y + c * w], [x + c * len, y + n * len], [x + n * w, y - c * w]], c2, alpha);
  };
  star(a, L, W, col, 0.7 * k); star(a, L * 0.8, W * 0.5, 0xffffff, k);
  star(a + Math.PI / 2, L * 0.45, W * 0.8, 0xffffff, 0.9 * k);
  g.fillStyle(0xffffff, 0.8 * k * k); g.fillCircle(x, y, (big ? 6 : 4) * k);
  g.lineStyle(1.5 * k + 0.5, col, 0.8 * k); g.strokeCircle(x, y, (big ? 8 : 5) + easeOut(p) * (big ? 16 : 10));
}

// A pool on the floor (poison, fire, void...): a soft body, a bright rim that breathes, drifting motes.
export function pool(floor, g, s, col, fade, now) {
  const breathe = 0.5 + 0.5 * Math.sin(now * 3 + s.cx * 0.1);
  floor.fillStyle(col, 0.26 * fade); floor.fillCircle(s.cx, s.cy, s.r);
  floor.fillStyle(col, 0.2 * fade); floor.fillCircle(s.cx, s.cy, s.r * 0.66);
  floor.lineStyle(1.5, col, (0.6 + 0.3 * breathe) * fade); floor.strokeCircle(s.cx, s.cy, s.r);
  g.fillStyle(col, 0.1 * fade * (0.6 + 0.4 * breathe)); g.fillCircle(s.cx, s.cy, s.r * 0.8);
  for (let k = 0; k < 4; k++) {
    const ph = (now * 0.5 + k * 0.25 + s.cy * 0.013) % 1, ang = k * 2.4 + s.cx * 0.07, rr = s.r * (0.25 + 0.5 * ((k * 0.37) % 1));
    g.fillStyle(col, 0.7 * fade * Math.sin(ph * Math.PI));
    g.fillCircle(s.cx + Math.cos(ang) * rr, s.cy + Math.sin(ang) * rr * 0.6 - ph * 12, 1.4);
  }
}
