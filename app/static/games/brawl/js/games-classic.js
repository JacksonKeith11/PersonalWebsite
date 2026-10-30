// The minigames from the owner's friends' favourites thread, the browser's half. Only the board is
// Halloween, so these keep a plain look, close to the Mario Party games they're based on.
// They're made for a keyboard and mouse.

import { Game, TEAM_COLORS } from './base.js?v=7';
import { Arena } from './games-live.js?v=7';
import * as art from './art.js?v=7';

const now = () => performance.now() / 1000;
const ARROWS = ['ArrowUp', 'ArrowRight', 'ArrowDown', 'ArrowLeft'];
const WASD = ['KeyW', 'KeyD', 'KeyS', 'KeyA'];

function arrow(c, x, y, s, dir, color) {
  c.save();
  c.translate(x, y);
  c.rotate((dir * Math.PI) / 2);
  c.fillStyle = color;
  c.beginPath();
  c.moveTo(0, -s); c.lineTo(s * 0.85, 0); c.lineTo(s * 0.35, 0); c.lineTo(s * 0.35, s);
  c.lineTo(-s * 0.35, s); c.lineTo(-s * 0.35, 0); c.lineTo(-s * 0.85, 0);
  c.closePath();
  c.fill();
  c.restore();
}

// ---------------------------------------------------------------- Say Cheese!

class SayCheese extends Arena {
  constructor(s) {
    super(s);
    this.hint = 'Get in the picture!';
    this.nameColor = '#2b2620';
    this.meColor = '#b8860b';
    this.shot = -1;
    this.flash = 0;
    this.floats = [];
  }
  onSnap(m) {
    if (m.last && m.last.i !== this.shot) {
      this.shot = m.last.i;
      this.flash = now();
      this.sound('pop');
      const ds = new Map(m.d.map(d => [d[0], d]));
      for (const [pid, pts] of Object.entries(m.last.got)) {
        const d = ds.get(+pid);
        if (d) this.floats.push({ x: d[1], y: d[2], text: `+${pts}`, t: now() });
      }
    }
  }
  drawField() {
    const c = this.c, f = this.field();
    c.fillStyle = '#e9e4d8';
    c.fillRect(f.x, f.y, 100 * f.s, 100 * f.s);
    c.strokeStyle = '#b5ab96';
    c.lineWidth = 3;
    c.strokeRect(f.x, f.y, 100 * f.s, 100 * f.s);
    const m = this.cur && this.cur.m;
    if (!m || !m.frame) return;
    const fr = m.frame;
    const [x0, y0] = this.at(fr.x - fr.w / 2, fr.y - fr.h / 2);
    const w = fr.w * f.s, h = fr.h * f.s, k = Math.min(w, h) * 0.2;
    c.fillStyle = 'rgba(255, 230, 120, 0.25)';
    c.fillRect(x0, y0, w, h);
    c.strokeStyle = '#2b2620';
    c.lineWidth = 4;
    for (const [cx, cy, dx, dy] of [[x0, y0, 1, 1], [x0 + w, y0, -1, 1], [x0, y0 + h, 1, -1], [x0 + w, y0 + h, -1, -1]]) {
      c.beginPath(); c.moveTo(cx + dx * k, cy); c.lineTo(cx, cy); c.lineTo(cx, cy + dy * k); c.stroke();
    }
    const [mx, my] = this.at(fr.x, fr.y);
    c.strokeStyle = 'rgba(200, 40, 40, 0.6)';
    c.lineWidth = 2;
    c.beginPath(); c.arc(mx, my, Math.min(fr.w, fr.h) * 0.22 * f.s, 0, Math.PI * 2); c.stroke();
    const left = fr.in - (now() - this.cur.at);
    if (left < 3.2 && left > 0) this.title(String(Math.ceil(left)), mx, y0 - 22, 34, '#c0392b');
  }
  drawOver() {
    const c = this.c;
    const m = this.cur && this.cur.m;
    if (m) {
      const rows = this.ids.map(id => ({ id, v: m.pts[id] || 0 })).sort((a, b) => b.v - a.v);
      rows.forEach((r, i) => this.text(`${this.player(r.id).name} ${r.v}`, 14, 60 + i * 22, 16, this.player(r.id).color, 'left'));
    }
    this.floats = this.floats.filter(fl => now() - fl.t < 1.2);
    for (const fl of this.floats) {
      const [x, y] = this.at(fl.x, fl.y);
      this.title(fl.text, x, y - 30 - (now() - fl.t) * 30, 26, '#ffd23f');
    }
    const a = 1 - (now() - this.flash) * 3;
    if (a > 0) { c.fillStyle = `rgba(255,255,255,${a})`; c.fillRect(0, 0, this.W, this.H); }
  }
}

// ---------------------------------------------------------------- Tick Tock Hop

class TickTockHop extends Game {
  constructor(s) {
    super(s);
    this.q = null;
    this.myAir = 0;
    this.hint = 'Space or click to jump the hands';
  }
  snap(m) {
    if (this.q && this.q.alive.includes(this.me) && !m.alive.includes(this.me)) this.sound('hit');
    else if (this.q && m.alive.length < this.q.alive.length) this.sound('fall');
    this.q = { ...m, at: now() };
  }
  jump() {
    if (!this.q || !this.q.alive.includes(this.me) || now() < this.myAir + 0.05) return;
    this.myAir = now() + 0.55;
    this.send({ t: 'jump' });
    this.sound('pump');
  }
  key(e, down, live) { if (down && live && (e.code === 'Space' || e.code === 'Enter' || e.code === 'ArrowUp')) this.jump(); }
  pointer(type, x, y, id, live) { if (type === 'pointerdown' && live) this.jump(); }
  draw(t) {
    const q = this.q;
    const c = this.c;
    const cx = this.W / 2, cy = 50 + (this.H - 50) / 2, R = Math.min(this.W, this.H - 70) * 0.44;
    c.fillStyle = '#7a5a2f';
    c.beginPath(); c.arc(cx, cy, R + 12, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#f6efdc';
    c.beginPath(); c.arc(cx, cy, R, 0, Math.PI * 2); c.fill();
    for (let i = 1; i <= 12; i++) {
      const a = (i / 12) * Math.PI * 2 - Math.PI / 2;
      this.text(String(i), cx + Math.cos(a) * R * 0.88, cy + Math.sin(a) * R * 0.88, 20, '#4a3a28', 'center', 600);
    }
    if (!q) return;
    const since = now() - q.at;
    for (const [a, w, on] of q.hands) {
      if (!on) continue;
      const ang = a + w * since;
      c.save();
      c.translate(cx, cy);
      c.rotate(ang);
      c.fillStyle = '#2b2620';
      c.beginPath(); c.roundRect(-8, -7, R * 0.98, 14, 7); c.fill();
      c.restore();
    }
    c.fillStyle = '#c0392b';
    c.beginPath(); c.arc(cx, cy, 12, 0, Math.PI * 2); c.fill();
    for (const id of this.ids) {
      const a = this.params.angle[id];
      const alive = q.alive.includes(id);
      let air = Math.max(0, (q.air[id] || 0) - since);
      if (id === this.me) air = Math.max(air, this.myAir - now());
      const lift = Math.sin(Math.min(1, air / 0.55) * Math.PI) * 26;
      const x = cx + Math.cos(a) * R * 0.66, y = cy + Math.sin(a) * R * 0.66;
      c.fillStyle = 'rgba(0,0,0,0.25)';
      c.beginPath(); c.ellipse(x, y + 14, 14, 5, 0, 0, Math.PI * 2); c.fill();
      const p = this.player(id);
      art.token(c, x, y - lift, 18, p.color, { label: p.name.slice(0, 1), dim: !alive, t: t + id, ring: id === this.me ? '#ffe066' : '#fff' });
      this.text(p.name, x, y + 30, 14, id === this.me ? '#b8860b' : '#2b2620');
    }
  }
}

// ---------------------------------------------------------------- Cookie Cutter

function shapePoints(kind) {
  const pts = [];
  const N = 240;
  for (let i = 0; i < N; i++) {
    const th = (i / N) * Math.PI * 2;
    if (kind === 'circle') pts.push([Math.cos(th), Math.sin(th)]);
    else if (kind === 'heart') {
      const x = 16 * Math.sin(th) ** 3, y = -(13 * Math.cos(th) - 5 * Math.cos(2 * th) - 2 * Math.cos(3 * th) - Math.cos(4 * th));
      pts.push([x / 17, y / 17 + 0.1]);
    } else if (kind === 'cloud') {
      const r = 0.85 + 0.15 * Math.abs(Math.sin(th * 3.5));
      pts.push([Math.cos(th) * r * 1.15, Math.sin(th) * r * 0.8]);
    }
  }
  if (pts.length) return pts;
  let poly;
  if (kind === 'star') poly = Array.from({ length: 10 }, (_, i) => { const a = (i / 10) * Math.PI * 2 - Math.PI / 2, r = i % 2 ? 0.42 : 1; return [Math.cos(a) * r, Math.sin(a) * r]; });
  else if (kind === 'bolt') poly = [[-0.2, -1], [0.45, -1], [0.1, -0.2], [0.55, -0.2], [-0.35, 1], [-0.05, 0.15], [-0.5, 0.15]];
  else poly = [[0, -1], [0.9, -0.2], [0.65, -0.2], [0.65, 0.9], [-0.65, 0.9], [-0.65, -0.2], [-0.9, -0.2]];  // a house
  // walk round the polygon at an even spacing
  const segs = poly.map((p, i) => [p, poly[(i + 1) % poly.length]]);
  const total = segs.reduce((s, [a, b]) => s + Math.hypot(b[0] - a[0], b[1] - a[1]), 0);
  for (let i = 0; i < N; i++) {
    let d = (i / N) * total;
    for (const [a, b] of segs) {
      const l = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (d <= l) { pts.push([a[0] + ((b[0] - a[0]) * d) / l, a[1] + ((b[1] - a[1]) * d) / l]); break; }
      d -= l;
    }
  }
  return pts;
}

class CookieCutter extends Game {
  constructor(s) {
    super(s);
    this.outline = shapePoints(this.params.shape);
    this.covered = new Array(this.outline.length).fill(false);
    this.path = [];  // strokes of [x, y] in shape units
    this.err = [];
    this.down = false;
    this.result = null;
    this.others = {};
    this.hint = 'Hold the mouse button and trace the outline';
  }
  snap(m) { this.others = m.prog || {}; }
  frame() { const a = this.area(); return { cx: a.x + a.w / 2, cy: a.y + a.h / 2 + 10, S: Math.min(a.w, a.h) * 0.32 }; }
  doneRect() { const a = this.area(); return { x: a.x + a.w / 2 - 70, y: a.y + a.h - 50, w: 140, h: 40 }; }
  add(x, y) {
    const f = this.frame();
    const u = (x - f.cx) / f.S, v = (y - f.cy) / f.S;
    this.path[this.path.length - 1].push([u, v]);
    let best = 9;
    this.outline.forEach(([ox, oy], i) => {
      const d = Math.hypot(ox - u, oy - v);
      if (d < best) best = d;
      if (d < 0.07) this.covered[i] = true;
    });
    this.err.push(best);
  }
  coverage() { return this.covered.filter(Boolean).length / this.covered.length; }
  finish() {
    if (this.result != null) return;
    const cov = this.coverage();
    const err = this.err.length ? this.err.reduce((a, b) => a + b, 0) / this.err.length : 1;
    const quick = cov > 0.9 ? Math.max(0, this.s.info.dur - this.t) * 1.5 : 0;
    this.result = Math.max(0, Math.min(200, Math.round(cov * 100 - Math.max(0, err - 0.02) * 250 + quick)));
    this.done([this.result]);
    this.sound('right');
  }
  pointer(type, x, y, id, live) {
    if (!live || this.result != null) return;
    if (type === 'pointerdown') {
      if (this.hit(this.doneRect(), x, y)) { this.finish(); return; }
      this.down = true;
      this.path.push([]);
      this.add(x, y);
    } else if (type === 'pointermove' && this.down) {
      this.add(x, y);
    } else if (type === 'pointerup' || type === 'pointercancel') {
      this.down = false;
    }
  }
  key(e, down, live) { if (down && live && e.code === 'Enter') this.finish(); }
  draw(t) {
    if (this.playing && t > this.s.info.dur - 0.3) this.finish();
    const c = this.c;
    if (this.playing) {
      const f = this.frame();
      c.fillStyle = '#f3e3c3';
      c.beginPath(); c.arc(f.cx, f.cy, f.S * 1.25, 0, Math.PI * 2); c.fill();
      c.setLineDash([8, 6]);
      c.strokeStyle = '#8a6a3a';
      c.lineWidth = 4;
      c.beginPath();
      this.outline.forEach(([u, v], i) => (i ? c.lineTo(f.cx + u * f.S, f.cy + v * f.S) : c.moveTo(f.cx + u * f.S, f.cy + v * f.S)));
      c.closePath();
      c.stroke();
      c.setLineDash([]);
      c.strokeStyle = '#c0392b';
      c.lineWidth = 3;
      c.lineCap = 'round';
      c.lineJoin = 'round';
      for (const stroke of this.path) {
        c.beginPath();
        stroke.forEach(([u, v], i) => (i ? c.lineTo(f.cx + u * f.S, f.cy + v * f.S) : c.moveTo(f.cx + u * f.S, f.cy + v * f.S)));
        c.stroke();
      }
      this.text(`Traced ${Math.round(this.coverage() * 100)}%`, f.cx, this.area().y + 16, 18, '#ffe9b8');
      if (this.result == null) this.button(this.doneRect(), 'Done', { on: true, size: 18 });
      else this.title(`${this.result} points`, f.cx, this.area().y + this.area().h - 30, 30, '#ffe066');
    }
    this.sideBoard('Finished', this.ids.map(id => ({ id, text: (id === this.me ? this.result != null : this.others[id]) ? '✓' : '…' })));
  }
}

// ---------------------------------------------------------------- Hotel Hustle

class HotelHustle extends Game {
  constructor(s) {
    super(s);
    this.floor = 0;
    this.tried = new Set();
    this.stunned = 0;
    this.others = {};
    this.hint = 'Pick the door that goes up';
  }
  snap(m) { this.others = m.prog || {}; }
  doors() {
    const a = this.area();
    const n = this.floor < this.params.floors.length ? this.params.floors[this.floor][0] : 3;
    const w = Math.min(110, (a.w - 60) / n - 20), h = w * 1.7;
    const x0 = a.x + (a.w - n * (w + 20)) / 2 + 10;
    return Array.from({ length: n }, (_, i) => ({ x: x0 + i * (w + 20), y: a.y + a.h / 2 - h / 2 + 20, w, h }));
  }
  pick(i) {
    const F = this.params.floors;
    if (this.floor >= F.length || this.t < this.stunned || this.tried.has(i) || i >= F[this.floor][0]) return;
    if (i === F[this.floor][1]) {
      this.floor++;
      this.tried = new Set();
      this.sound('right');
      this.prog([this.floor, +this.t.toFixed(2)]);
      if (this.floor === F.length) this.done([this.floor, +this.t.toFixed(2)]);
    } else {
      this.tried.add(i);
      this.stunned = this.t + this.params.stun;
      this.sound('wrong');
    }
  }
  key(e, down, live) { if (down && live && /^Digit[1-4]$/.test(e.code)) this.pick(+e.code.slice(5) - 1); }
  pointer(type, x, y, id, live) {
    if (type !== 'pointerdown' || !live) return;
    this.doors().forEach((r, i) => { if (this.hit(r, x, y)) this.pick(i); });
  }
  draw(t) {
    const c = this.c, F = this.params.floors;
    if (this.playing && t > this.s.info.dur - 0.3 && !this.sentDone) this.done([this.floor, +t.toFixed(2)]);
    if (this.playing) {
      const a = this.area();
      c.fillStyle = '#c9b49a';
      c.fillRect(a.x + 10, a.y + 30, a.w - 20, a.h - 40);
      c.fillStyle = '#8c2f2f';
      c.fillRect(a.x + 10, a.y + a.h - 40, a.w - 20, 30);
      if (this.floor < F.length) {
        this.title(`Floor ${this.floor + 1} of ${F.length}`, a.x + a.w / 2, a.y + 10, 26, '#ffe9b8');
        this.doors().forEach((r, i) => {
          const bad = this.tried.has(i);
          c.fillStyle = bad ? '#5a4a3a' : '#6b3e1f';
          c.fillRect(r.x, r.y, r.w, r.h);
          c.strokeStyle = '#3a2210';
          c.lineWidth = 4;
          c.strokeRect(r.x, r.y, r.w, r.h);
          c.fillStyle = '#e8c35a';
          c.beginPath(); c.arc(r.x + r.w * 0.8, r.y + r.h * 0.55, 5, 0, Math.PI * 2); c.fill();
          this.text(String(i + 1), r.x + r.w / 2, r.y + 22, 20, '#f3e3c3');
          if (bad) this.title('✗', r.x + r.w / 2, r.y + r.h / 2, 50, '#c0392b');
        });
        if (t < this.stunned) this.title('Bonk! Wrong door', a.x + a.w / 2, a.y + a.h - 70, 28, '#c0392b');
      } else {
        this.title('You made it to the roof!', a.x + a.w / 2, a.y + a.h / 2, 30, '#ffe066');
      }
    }
    // everyone's progress up the hotel
    const s = this.side();
    const top = s.y + 30, bottom = Math.min(this.H - 30, s.y + 30 + 320);
    const n = this.ids.length;
    this.text('Floors', s.x + s.w / 2, s.y + 10, 15, '#cbbfe0');
    this.ids.forEach((id, i) => {
      const x = s.x + (s.w / (n + 1)) * (i + 1);
      const fl = id === this.me ? this.floor : (this.others[id] || [0])[0];
      c.fillStyle = 'rgba(255,255,255,0.1)';
      c.fillRect(x - 6, top, 12, bottom - top);
      const y = bottom - ((bottom - top) * fl) / F.length;
      const p = this.player(id);
      art.token(c, x, y, 11, p.color, { label: p.name.slice(0, 1), t: t + id, ring: id === this.me ? '#ffe066' : '#fff' });
      this.text(p.name.slice(0, 8), x, bottom + 16 + (i % 2) * 16, 13, id === this.me ? '#ffe066' : '#cbbfe0');
    });
  }
}

// ---------------------------------------------------------------- Shooting Gallery

class ShootingGallery extends Game {
  constructor(s) {
    super(s);
    this.targets = this.params.targets.map(([t, y, dir, speed, kind]) => ({ t, y, dir, speed, kind, hit: null }));
    this.score = 0;
    this.mouse = null;
    this.pops = [];
    this.others = {};
    this.hint = 'Click the ducks and stars; leave the bombs';
  }
  snap(m) { this.others = m.prog || {}; }
  box() { const a = this.area(); return { x: a.x + 10, y: a.y + 10, w: a.w - 20, h: a.h - 30 }; }
  pos(tg, t) {
    const x = (tg.dir > 0 ? -6 : 106) + tg.dir * tg.speed * (t - tg.t);
    return x;
  }
  pointer(type, x, y, id, live) {
    this.mouse = [x, y];
    if (type !== 'pointerdown' || !live) return;
    const b = this.box();
    const u = ((x - b.x) / b.w) * 100, v = ((y - b.y) / b.h) * 100;
    for (const tg of this.targets) {
      if (tg.hit || this.t < tg.t) continue;
      const tx = this.pos(tg, this.t);
      if (Math.hypot((tx - u) * b.w / 100, (tg.y - v) * b.h / 100) < 26) {
        tg.hit = this.t;
        const pts = tg.kind === 'gold' ? 3 : tg.kind === 'bomb' ? -3 : 1;
        this.score += pts;
        this.pops.push({ x, y, text: pts > 0 ? `+${pts}` : `${pts}`, t: this.t });
        this.sound(pts > 0 ? 'hit' : 'bomb');
        this.prog([this.score]);
        return;
      }
    }
    this.sound('tick');
  }
  draw(t) {
    const last = this.targets[this.targets.length - 1];
    if (this.playing && last && t > last.t + 5.5) this.done([this.score]);
    const c = this.c;
    if (this.playing) {
      const b = this.box();
      c.fillStyle = '#2f5d8a';
      c.fillRect(b.x, b.y, b.w, b.h);
      for (let i = 0; i < 3; i++) { c.fillStyle = i % 2 ? '#3b6d9c' : '#284f75'; c.fillRect(b.x, b.y + b.h * (0.3 + i * 0.25), b.w, 8); }
      c.save();
      c.beginPath(); c.rect(b.x, b.y, b.w, b.h); c.clip();
      for (const tg of this.targets) {
        if (tg.hit || t < tg.t) continue;
        const x = b.x + (this.pos(tg, t) / 100) * b.w, y = b.y + (tg.y / 100) * b.h;
        if (x < b.x - 40 || x > b.x + b.w + 40) continue;
        if (tg.kind === 'duck') {
          c.fillStyle = '#f4d03f';
          c.beginPath(); c.ellipse(x, y, 22, 16, 0, 0, Math.PI * 2); c.fill();
          c.beginPath(); c.arc(x + tg.dir * 14, y - 14, 10, 0, Math.PI * 2); c.fill();
          c.fillStyle = '#e67e22';
          c.beginPath(); c.moveTo(x + tg.dir * 22, y - 16); c.lineTo(x + tg.dir * 32, y - 12); c.lineTo(x + tg.dir * 22, y - 9); c.fill();
          c.fillStyle = '#222';
          c.beginPath(); c.arc(x + tg.dir * 16, y - 17, 2.5, 0, Math.PI * 2); c.fill();
        } else if (tg.kind === 'gold') {
          c.fillStyle = '#ffd23f';
          c.beginPath();
          for (let i = 0; i < 10; i++) { const a = (i / 10) * Math.PI * 2 - Math.PI / 2 + t * 3, r = i % 2 ? 9 : 22; c.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r); }
          c.closePath(); c.fill();
        } else {
          c.fillStyle = '#222';
          c.beginPath(); c.arc(x, y, 17, 0, Math.PI * 2); c.fill();
          c.strokeStyle = '#a0522d'; c.lineWidth = 3;
          c.beginPath(); c.moveTo(x + 8, y - 14); c.quadraticCurveTo(x + 14, y - 26, x + 20, y - 22); c.stroke();
          c.fillStyle = '#ff8c1a';
          c.beginPath(); c.arc(x + 20, y - 22, 3 + Math.random() * 2, 0, Math.PI * 2); c.fill();
        }
      }
      c.restore();
      c.fillStyle = '#7a1f1f';
      c.fillRect(b.x, b.y - 8, b.w, 12);
      this.pops = this.pops.filter(p => t - p.t < 0.8);
      for (const p of this.pops) this.title(p.text, p.x, p.y - 20 - (t - p.t) * 40, 26, p.text.startsWith('+') ? '#7dff9b' : '#ff6b6b');
      if (this.mouse) {
        const [mx, my] = this.mouse;
        c.strokeStyle = '#fff'; c.lineWidth = 2;
        c.beginPath(); c.arc(mx, my, 14, 0, Math.PI * 2); c.moveTo(mx - 22, my); c.lineTo(mx + 22, my); c.moveTo(mx, my - 22); c.lineTo(mx, my + 22); c.stroke();
      }
    }
    this.sideBoard('Points', this.ids.map(id => ({ id, text: String(id === this.me ? this.score : (this.others[id] || [0])[0]) })));
  }
}

// ---------------------------------------------------------------- Ten Seconds Flat

class TenSeconds extends Game {
  constructor(s) {
    super(s);
    this.r = 0;
    this.phase = 'ready';
    this.at = 0;
    this.misses = [];
    this.result = null;
    this.others = {};
    this.hint = 'Count in your head';
  }
  snap(m) { this.others = m.prog || {}; }
  stop() {
    if (this.phase !== 'run') return;
    this.record(this.t - this.at);
  }
  record(elapsed) {
    const target = this.params.targets[this.r];
    const miss = Math.round(Math.abs(elapsed - target) * 1000);
    this.misses.push(miss);
    this.result = elapsed;
    this.phase = 'result';
    this.at = this.t;
    this.sound(miss < 150 ? 'right' : 'hit');
    this.prog(this.misses);
    if (this.misses.length === this.params.targets.length) this.done(this.misses);
  }
  key(e, down, live) { if (down && live && ['Space', 'Enter'].includes(e.code)) this.stop(); }
  pointer(type, x, y, id, live) { if (type === 'pointerdown' && live) this.stop(); }
  draw(t) {
    const T = this.params.targets;
    if (this.playing && t >= 0) {
      if (this.phase === 'ready' && t - this.at > 1.2) { this.phase = 'run'; this.at = t; this.sound('go'); }
      else if (this.phase === 'run' && t - this.at > T[this.r] + 5) this.record(t - this.at);
      else if (this.phase === 'result' && t - this.at > 2 && this.r < T.length - 1) { this.r++; this.phase = 'ready'; this.at = t; }
    }
    const c = this.c;
    if (this.playing) {
      const a = this.area(), cx = a.x + a.w / 2, cy = a.y + a.h / 2;
      this.title(`Stop at ${T[Math.min(this.r, T.length - 1)].toFixed(2)}s`, cx, a.y + 20, 30, '#ffe066');
      c.fillStyle = '#ddd';
      c.beginPath(); c.arc(cx, cy + 20, 120, 0, Math.PI * 2); c.fill();
      c.fillStyle = '#fff';
      c.beginPath(); c.arc(cx, cy + 20, 108, 0, Math.PI * 2); c.fill();
      c.fillStyle = '#999';
      c.fillRect(cx - 12, cy - 120, 24, 22);
      let shown = '';
      if (this.phase === 'ready') shown = 'Ready…';
      else if (this.phase === 'run') shown = t - this.at < this.params.hide ? (t - this.at).toFixed(2) : '?.??';
      else shown = this.result.toFixed(2);
      this.title(shown, cx, cy + 20, 46, '#2b2620');
      if (this.phase === 'result') {
        const miss = this.misses[this.misses.length - 1];
        this.title(miss < 50 ? 'Spot on!' : `Off by ${(miss / 1000).toFixed(2)}s`, cx, cy + 170, 28, miss < 150 ? '#7dff9b' : '#ffe9b8');
      }
      this.text(`Round ${this.r + 1} of ${T.length}`, cx, a.y + a.h - 10, 16, '#cbbfe0');
    }
    this.sideBoard('Off by', this.ids.map(id => {
      const v = id === this.me ? this.misses : this.others[id] || [];
      return { id, text: v.length ? v.map(ms => (ms / 1000).toFixed(2)).join(' + ') : '…' };
    }));
  }
}

// ---------------------------------------------------------------- Beanstalk

class Beanstalk extends Game {
  constructor(s) {
    super(s);
    this.h = 0;
    this.stunned = 0;
    this.others = {};
    this.hint = 'Press the arrow shown';
  }
  snap(m) { this.others = m.prog || {}; }
  height(id) { return id === this.me ? this.h : (this.others[id] || [0])[0]; }
  key(e, down, live) {
    if (!down || !live || this.h >= this.params.goal || this.t < this.stunned) return;
    const d = ARROWS.indexOf(e.code) >= 0 ? ARROWS.indexOf(e.code) : WASD.indexOf(e.code);
    if (d < 0) return;
    if (d === this.params.seq[this.h]) {
      this.h++;
      this.sound('tick');
      this.prog([this.h, +this.t.toFixed(2)]);
      if (this.h === this.params.goal) { this.done([this.h, +this.t.toFixed(2)]); this.sound('win'); }
    } else {
      this.stunned = this.t + this.params.stun;
      this.sound('wrong');
    }
  }
  draw(t) {
    if (this.playing && t > this.s.info.dur - 0.3 && !this.sentDone) this.done([this.h, +t.toFixed(2)]);
    const c = this.c, goal = this.params.goal;
    const g = c.createLinearGradient(0, 40, 0, this.H);
    g.addColorStop(0, '#8ec5ff');
    g.addColorStop(1, '#d8f0ff');
    c.fillStyle = g;
    c.fillRect(0, 40, this.W, this.H - 40);
    c.fillStyle = '#6b4a2b';
    c.fillRect(0, this.H - 40, this.W, 40);
    const n = this.ids.length;
    const top = 120, bottom = this.H - 40;
    c.strokeStyle = '#fff';
    c.setLineDash([10, 8]);
    c.lineWidth = 3;
    c.beginPath(); c.moveTo(0, top); c.lineTo(this.W, top); c.stroke();
    c.setLineDash([]);
    this.ids.forEach((id, i) => {
      const x = (this.W / (n + 1)) * (i + 1);
      const h = this.height(id);
      const y = bottom - ((bottom - top) * h) / goal;
      c.strokeStyle = '#2e8b3a';
      c.lineWidth = 8;
      c.beginPath(); c.moveTo(x, bottom);
      for (let yy = bottom; yy >= y; yy -= 6) c.lineTo(x + Math.sin(yy / 18) * 8, yy);
      c.stroke();
      for (let k = 0; k < h; k++) {
        const ly = bottom - ((bottom - top) * (k + 0.5)) / goal;
        c.fillStyle = '#4caf50';
        c.beginPath(); c.ellipse(x + (k % 2 ? 12 : -12), ly, 10, 5, k % 2 ? 0.5 : -0.5, 0, Math.PI * 2); c.fill();
      }
      const p = this.player(id);
      art.token(c, x, y - 18, 16, p.color, { label: p.name.slice(0, 1), t: t + id, ring: id === this.me ? '#ffe066' : '#fff' });
      this.text(`${p.name} ${h}`, x, bottom + 20, 15, id === this.me ? '#ffe066' : '#fff');
    });
    if (this.playing && this.h < goal) {
      const i = this.ids.indexOf(this.me);
      const x = (this.W / (n + 1)) * (i + 1);
      const y = bottom - ((bottom - top) * this.h) / goal - 70;
      c.fillStyle = 'rgba(0,0,0,0.55)';
      c.beginPath(); c.roundRect(x - 36, y - 36, 72, 72, 12); c.fill();
      arrow(c, x, y, 26, this.params.seq[this.h], t < this.stunned ? '#ff6b6b' : '#ffe066');
    }
  }
}

// ---------------------------------------------------------------- Messy Memory

function thing(c, kind, x, y, s) {
  c.save();
  c.translate(x, y);
  if (kind === 'apple') {
    c.fillStyle = '#d63a2f'; c.beginPath(); c.arc(-s * 0.2, 0, s * 0.45, 0, Math.PI * 2); c.arc(s * 0.2, 0, s * 0.45, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#5b3a1a'; c.fillRect(-s * 0.05, -s * 0.65, s * 0.1, s * 0.25);
    c.fillStyle = '#4caf50'; c.beginPath(); c.ellipse(s * 0.18, -s * 0.55, s * 0.2, s * 0.09, -0.5, 0, Math.PI * 2); c.fill();
  } else if (kind === 'book') {
    ['#2f6db5', '#c0392b', '#27ae60'].forEach((col, i) => { c.fillStyle = col; c.fillRect(-s * 0.55 + i * s * 0.37, -s * 0.6, s * 0.33, s * 1.2); });
  } else if (kind === 'cup') {
    c.fillStyle = '#f2f2f2'; c.fillRect(-s * 0.4, -s * 0.4, s * 0.7, s * 0.85);
    c.strokeStyle = '#f2f2f2'; c.lineWidth = s * 0.12; c.beginPath(); c.arc(s * 0.32, 0, s * 0.2, -1.4, 1.4); c.stroke();
    c.fillStyle = '#6b3e1f'; c.fillRect(-s * 0.35, -s * 0.38, s * 0.6, s * 0.1);
  } else if (kind === 'lamp') {
    c.fillStyle = '#f4d03f'; c.beginPath(); c.moveTo(-s * 0.25, -s * 0.6); c.lineTo(s * 0.25, -s * 0.6); c.lineTo(s * 0.45, -s * 0.1); c.lineTo(-s * 0.45, -s * 0.1); c.fill();
    c.fillStyle = '#555'; c.fillRect(-s * 0.05, -s * 0.1, s * 0.1, s * 0.55); c.fillRect(-s * 0.3, s * 0.45, s * 0.6, s * 0.1);
  } else if (kind === 'clock') {
    c.fillStyle = '#e67e22'; c.beginPath(); c.arc(0, 0, s * 0.55, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#fff'; c.beginPath(); c.arc(0, 0, s * 0.42, 0, Math.PI * 2); c.fill();
    c.strokeStyle = '#222'; c.lineWidth = 3; c.beginPath(); c.moveTo(0, 0); c.lineTo(0, -s * 0.3); c.moveTo(0, 0); c.lineTo(s * 0.22, 0); c.stroke();
  } else if (kind === 'plant') {
    c.fillStyle = '#b5651d'; c.fillRect(-s * 0.3, s * 0.05, s * 0.6, s * 0.5);
    c.fillStyle = '#2e8b3a';
    for (const a of [-0.8, -0.3, 0.3, 0.8]) { c.beginPath(); c.ellipse(Math.sin(a) * s * 0.3, -s * 0.25, s * 0.12, s * 0.35, a, 0, Math.PI * 2); c.fill(); }
  } else {
    c.fillStyle = '#9b59b6'; c.beginPath(); c.arc(0, 0, s * 0.5, 0, Math.PI * 2); c.fill();
    c.strokeStyle = '#fff'; c.lineWidth = s * 0.1; c.beginPath(); c.arc(0, 0, s * 0.5, -0.6, 0.6); c.stroke();
    c.beginPath(); c.arc(0, 0, s * 0.5, Math.PI - 0.6, Math.PI + 0.6); c.stroke();
  }
  c.restore();
}

class MessyMemory extends Game {
  constructor(s) {
    super(s);
    this.pos = this.params.moved.slice();
    this.drag = null;
    this.result = null;
    this.others = {};
    this.hint = 'Remember where everything goes';
  }
  snap(m) { this.others = m.prog || {}; }
  slots() {
    const a = this.area();
    const cols = 4, rows = 3;
    const w = Math.min((a.w - 40) / cols, (a.h - 100) / rows);
    const x0 = a.x + (a.w - cols * w) / 2, y0 = a.y + 30;
    return Array.from({ length: this.params.slots }, (_, i) => ({ x: x0 + (i % cols) * w, y: y0 + Math.floor(i / cols) * w, w, h: w }));
  }
  doneRect() { const a = this.area(); return { x: a.x + a.w / 2 - 70, y: a.y + a.h - 50, w: 140, h: 40 }; }
  sorting() { return this.t >= this.params.show && this.result == null; }
  finish() {
    if (this.result != null || !this.sorting()) return;
    this.result = this.pos.filter((p, k) => p === this.params.home[k]).length;
    this.done([this.result, +(this.t - this.params.show).toFixed(2)]);
    this.sound('right');
  }
  pointer(type, x, y, id, live) {
    if (!live || !this.sorting()) return;
    const S = this.slots();
    const at = S.findIndex(r => this.hit(r, x, y));
    if (type === 'pointerdown') {
      if (this.hit(this.doneRect(), x, y)) { this.finish(); return; }
      const k = this.pos.indexOf(at);
      if (at >= 0 && k >= 0) this.drag = { k, x, y };
    } else if (type === 'pointermove' && this.drag) {
      this.drag.x = x; this.drag.y = y;
    } else if (type === 'pointerup' && this.drag) {
      if (at >= 0) {
        const other = this.pos.indexOf(at);
        if (other >= 0) this.pos[other] = this.pos[this.drag.k];
        this.pos[this.drag.k] = at;
        this.sound('tick');
      }
      this.drag = null;
    }
  }
  key(e, down, live) { if (down && live && e.code === 'Enter') this.finish(); }
  draw(t) {
    if (this.playing && t > this.s.info.dur - 0.3) this.finish();
    const c = this.c, P = this.params;
    if (this.playing) {
      const S = this.slots();
      const showing = t < P.show;
      S.forEach(r => {
        c.fillStyle = '#c9a36a';
        c.fillRect(r.x + 4, r.y + r.h - 12, r.w - 8, 10);
        c.fillStyle = 'rgba(255,255,255,0.05)';
        c.fillRect(r.x + 4, r.y + 4, r.w - 8, r.h - 16);
      });
      const where = showing ? P.home : this.pos;
      P.kinds.forEach((kind, k) => {
        if (this.drag && this.drag.k === k) return;
        const r = S[where[k]];
        thing(c, kind, r.x + r.w / 2, r.y + r.h / 2 - 6, r.w * 0.4);
        if (this.result != null && this.pos[k] !== P.home[k]) this.title('✗', r.x + r.w - 16, r.y + 16, 22, '#ff6b6b');
      });
      if (this.drag) thing(c, P.kinds[this.drag.k], this.drag.x, this.drag.y, S[0].w * 0.45);
      const a = this.area();
      if (showing) this.title(t >= 0 ? `Remember this! ${Math.ceil(P.show - t)}` : 'Remember where everything is', a.x + a.w / 2, a.y + 10, 24, '#ffe066');
      else if (this.result == null) { this.title('Put it all back', a.x + a.w / 2, a.y + 10, 24, '#ffe066'); this.button(this.doneRect(), 'Done', { on: true, size: 18 }); }
      else this.title(`${this.result} of ${P.kinds.length} right`, a.x + a.w / 2, a.y + a.h - 30, 28, '#ffe066');
    }
    this.sideBoard('Finished', this.ids.map(id => ({ id, text: (id === this.me ? this.result != null : this.others[id]) ? '✓' : '…' })));
  }
}

// ---------------------------------------------------------------- Snowball Summit

class SnowballSummit extends Arena {
  constructor(s) {
    super(s);
    this.nameColor = '#2b2620';
    this.meColor = '#b8860b';
  }
  drawField() {
    const c = this.c, f = this.field();
    const g = c.createLinearGradient(0, f.y, 0, f.y + 100 * f.s);
    g.addColorStop(0, '#dfe9f5');
    g.addColorStop(1, '#ffffff');
    c.fillStyle = g;
    c.fillRect(f.x, f.y, 100 * f.s, 100 * f.s);
    c.fillStyle = '#2e6b3a';
    for (const [x, y] of [[4, 20], [96, 40], [5, 65], [95, 85]]) {
      const [px, py] = this.at(x, y);
      c.beginPath(); c.moveTo(px, py - 5 * f.s); c.lineTo(px - 3 * f.s, py + 3 * f.s); c.lineTo(px + 3 * f.s, py + 3 * f.s); c.fill();
    }
    for (const [x, y, r] of (this.cur && this.cur.m.b) || []) {
      const [px, py] = this.at(x, y);
      c.fillStyle = 'rgba(0,0,40,0.15)';
      c.beginPath(); c.ellipse(px, py + r * f.s * 0.8, r * f.s, r * f.s * 0.3, 0, 0, Math.PI * 2); c.fill();
      const sg = c.createRadialGradient(px - r * f.s * 0.3, py - r * f.s * 0.3, 1, px, py, r * f.s);
      sg.addColorStop(0, '#ffffff');
      sg.addColorStop(1, '#b9cde0');
      c.fillStyle = sg;
      c.beginPath(); c.arc(px, py, r * f.s, 0, Math.PI * 2); c.fill();
    }
  }
}

// ---------------------------------------------------------------- Speed Hockey

class SpeedHockey extends Arena {
  constructor(s) {
    super(s);
    this.side = this.params.side || {};
    this.goals = [0, 0];
    this.hint = 'Score in the other side’s goal';
    this.nameColor = '#2b2620';
    this.meColor = '#b8860b';
  }
  onSnap(m) {
    if (m.goals && (m.goals[0] !== this.goals[0] || m.goals[1] !== this.goals[1])) this.sound('crown');
    this.goals = m.goals || this.goals;
  }
  teamRing(id) { return TEAM_COLORS[this.side[id] || 0]; }
  drawField() {
    const c = this.c, f = this.field();
    c.fillStyle = '#eaf6ff';
    c.fillRect(f.x, f.y, 100 * f.s, 100 * f.s);
    c.strokeStyle = '#9cc7e8';
    c.lineWidth = 4;
    c.strokeRect(f.x, f.y, 100 * f.s, 100 * f.s);
    const [mx, my] = this.at(50, 0), [, mb] = this.at(50, 100);
    c.strokeStyle = '#d64541';
    c.beginPath(); c.moveTo(mx, my); c.lineTo(mx, mb); c.stroke();
    c.beginPath(); c.arc(...this.at(50, 50), 12 * f.s, 0, Math.PI * 2); c.stroke();
    for (const [x, side] of [[0, 0], [100, 1]]) {
      const [gx, gy] = this.at(x, this.params.lo), [, gy2] = this.at(x, this.params.hi);
      c.strokeStyle = TEAM_COLORS[side];
      c.lineWidth = 10;
      c.beginPath(); c.moveTo(gx, gy); c.lineTo(gx, gy2); c.stroke();
    }
    const m = this.cur && this.cur.m;
    if (m && m.puck) {
      const pm = this.prev && this.prev.m.puck;
      const a = pm ? Math.min(1, (now() - this.cur.at) / 0.05) : 1;
      const x = pm ? pm[0] + (m.puck[0] - pm[0]) * a : m.puck[0], y = pm ? pm[1] + (m.puck[1] - pm[1]) * a : m.puck[1];
      const [px, py] = this.at(x, y);
      c.fillStyle = '#1d1d24';
      c.beginPath(); c.arc(px, py, 2.8 * f.s, 0, Math.PI * 2); c.fill();
    }
  }
  drawOver() {
    this.title(`${this.goals[0]} – ${this.goals[1]}`, this.W / 2, 64, 30, '#fff');
    this.c.fillStyle = TEAM_COLORS[0];
    this.c.fillRect(this.W / 2 - 70, 58, 12, 12);
    this.c.fillStyle = TEAM_COLORS[1];
    this.c.fillRect(this.W / 2 + 58, 58, 12, 12);
  }
}

export const CLASSIC = {
  cheese: SayCheese, ticktock: TickTockHop, cutter: CookieCutter, hotel: HotelHustle, gallery: ShootingGallery,
  clock: TenSeconds, beanstalk: Beanstalk, messy: MessyMemory, snowball: SnowballSummit, hockey: SpeedHockey,
};
