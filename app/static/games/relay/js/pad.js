// Sketch Relay's drawings: what a drawing is, painting one, and the pad a player draws on.
//
// A drawing is a list of strokes on a W x H sheet: { c, w, p: [x, y, x, y, ...] }, where `c` indexes
// PALETTE and `w` indexes WIDTHS (the server checks both, and the sizes: app/relay/game.py).

export const W = 800, H = 600;
export const PALETTE = ['#1d1b19', '#8a8580', '#7a4a21', '#d6342a', '#ee8a1e', '#f2cf2b',
  '#3d9f45', '#2aa5a5', '#2f6fd6', '#7d45c4', '#ee6fa8', '#ffffff'];
export const ERASER = PALETTE.length - 1;   // the sheet is white, so rubbing out is white paint
export const WIDTHS = [3, 7, 16, 36];

function stroke(ctx, s, upTo = s.p.length) {
  const p = s.p;
  ctx.strokeStyle = ctx.fillStyle = PALETTE[s.c];
  ctx.lineWidth = WIDTHS[s.w];
  if (upTo <= 2) {
    ctx.beginPath();
    ctx.arc(p[0], p[1], WIDTHS[s.w] / 2, 0, Math.PI * 2);
    ctx.fill();
    return;
  }
  // through the midpoints, so corners between samples come out rounded
  ctx.beginPath();
  ctx.moveTo(p[0], p[1]);
  for (let i = 2; i < upTo - 2; i += 2) {
    ctx.quadraticCurveTo(p[i], p[i + 1], (p[i] + p[i + 2]) / 2, (p[i + 1] + p[i + 3]) / 2);
  }
  ctx.lineTo(p[upTo - 2], p[upTo - 1]);
  ctx.stroke();
}

// Paint `strokes` over the whole of `canvas`. With `points`, only that many points of ink (for
// replaying a drawing as it was made).
export function paint(canvas, strokes, points = Infinity) {
  const ctx = canvas.getContext('2d');
  ctx.setTransform(canvas.width / W, 0, 0, canvas.height / H, 0, 0);
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, W, H);
  ctx.lineCap = ctx.lineJoin = 'round';
  for (const s of strokes) {
    if (points <= 0) break;
    const n = Math.min(s.p.length / 2, Math.ceil(points));
    stroke(ctx, s, n * 2);
    points -= n;
  }
}

export const inkUsed = strokes => strokes.reduce((n, s) => n + s.p.length / 2, 0);

// Give `canvas` as many pixels as it takes up on screen. True if that changed.
export function fit(canvas) {
  const w = Math.round(canvas.clientWidth * Math.min(window.devicePixelRatio || 1, 2));
  if (!w || canvas.width === w) return false;
  canvas.width = w;
  canvas.height = Math.round(w * H / W);
  return true;
}

// Show a finished drawing in `canvas`, drawn again stroke by stroke over `secs` seconds if asked.
// Returns a function that stops the replay.
export function show(canvas, strokes, secs = 0) {
  fit(canvas);
  const total = inkUsed(strokes);
  if (!secs || !total || matchMedia('(prefers-reduced-motion: reduce)').matches) {
    paint(canvas, strokes);
    return () => {};
  }
  let raf = 0;
  const t0 = performance.now();
  const frame = () => {
    const f = Math.min(1, (performance.now() - t0) / (secs * 1000));
    fit(canvas);
    paint(canvas, strokes, f * total);
    if (f < 1) raf = requestAnimationFrame(frame);
  };
  frame();
  return () => cancelAnimationFrame(raf);
}

// Drop the points of a stroke that sit within `tol` of the line through their neighbours
// (Ramer-Douglas-Peucker), so a slow, wobbly line doesn't use up the ink.
function simplify(p, tol) {
  const n = p.length / 2;
  if (n < 3) return p;
  const keep = new Uint8Array(n);
  keep[0] = keep[n - 1] = 1;
  const todo = [[0, n - 1]];
  while (todo.length) {
    const [a, b] = todo.pop();
    const ax = p[a * 2], ay = p[a * 2 + 1], dx = p[b * 2] - ax, dy = p[b * 2 + 1] - ay;
    const len = Math.hypot(dx, dy) || 1;
    let far = -1, most = tol;
    for (let i = a + 1; i < b; i++) {
      const px = p[i * 2] - ax, py = p[i * 2 + 1] - ay;
      const d = len === 1 && !dx && !dy ? Math.hypot(px, py) : Math.abs(px * dy - py * dx) / len;
      if (d > most) { most = d; far = i; }
    }
    if (far > 0) { keep[far] = 1; todo.push([a, far], [far, b]); }
  }
  const out = [];
  for (let i = 0; i < n; i++) if (keep[i]) out.push(p[i * 2], p[i * 2 + 1]);
  return out;
}

// The sheet a player draws on. `ink` is how many points a drawing may hold; `onChange` is called
// whenever the drawing changes.
export class Pad {
  constructor(canvas, { ink, onChange = () => {} }) {
    Object.assign(this, { canvas, ink, onChange });
    this.strokes = [];
    this.color = 0;
    this.width = 1;
    this.live = null;     // the stroke under the pointer
    this.pointer = null;
    canvas.addEventListener('pointerdown', e => this.down(e));
    canvas.addEventListener('pointermove', e => this.move(e));
    for (const type of ['pointerup', 'pointercancel']) canvas.addEventListener(type, e => this.up(e));
    new ResizeObserver(() => { if (fit(canvas)) this.redraw(); }).observe(canvas);
  }

  reset() {
    this.strokes = [];
    this.cleared = null;  // the drawing before Clear, so Undo can bring it back
    this.live = null;
    this.redraw();
    this.onChange();
  }

  // The drawing so far, including a stroke still under the pointer (the clock can run out mid-line).
  drawing() {
    return this.live ? [...this.strokes, this.live] : this.strokes;
  }

  left() { return Math.max(0, this.ink - inkUsed(this.drawing())); }

  redraw() {
    fit(this.canvas);
    paint(this.canvas, this.drawing());
  }

  at(e) {
    const r = this.canvas.getBoundingClientRect();
    return [
      Math.round(Math.min(Math.max((e.clientX - r.left) / r.width, 0), 1) * W),
      Math.round(Math.min(Math.max((e.clientY - r.top) / r.height, 0), 1) * H),
    ];
  }

  down(e) {
    if (this.live || (e.pointerType === 'mouse' && e.button !== 0) || this.left() < 1) return;
    e.preventDefault();
    this.pointer = e.pointerId;
    try { this.canvas.setPointerCapture(e.pointerId); } catch { /* a pointer that's already gone */ }
    this.live = { c: this.color, w: this.width, p: this.at(e) };
    this.redraw();
    this.onChange();
  }

  move(e) {
    const s = this.live;
    if (!s || e.pointerId !== this.pointer) return;
    e.preventDefault();
    let added = false;
    for (const ev of e.getCoalescedEvents?.().length ? e.getCoalescedEvents() : [e]) {
      const [x, y] = this.at(ev);
      const n = s.p.length;
      if (Math.hypot(x - s.p[n - 2], y - s.p[n - 1]) < 2 || this.left() < 1) continue;
      s.p.push(x, y);
      added = true;
    }
    if (added) { this.redraw(); this.onChange(); }
  }

  up(e) {
    if (!this.live || e.pointerId !== this.pointer) return;
    this.live.p = simplify(this.live.p, 0.8);
    this.strokes.push(this.live);
    this.cleared = null;
    this.live = null;
    this.redraw();
    this.onChange();
  }

  undo() {
    if (this.live) this.live = null;
    else if (!this.strokes.length && this.cleared) this.strokes = this.cleared;
    else this.strokes.pop();
    this.cleared = null;
    this.redraw();
    this.onChange();
  }

  clear() {
    if (!this.drawing().length) return;
    this.cleared = this.drawing();
    this.strokes = [];
    this.live = null;
    this.redraw();
    this.onChange();
  }
}
