// The solo minigames: each browser plays its own copy against the content the server dealt,
// and reports progress (`prog`) and a final score (`done`). Others' progress arrives in `prog`.

import { Game } from './base.js?v=6';
import * as art from './art.js?v=6';

const ARROWS = ['ArrowUp', 'ArrowRight', 'ArrowDown', 'ArrowLeft'];
const WASD = ['KeyW', 'KeyD', 'KeyS', 'KeyA'];

function arrow(c, x, y, s, dir, color) {
  c.save();
  c.translate(x, y);
  c.rotate((dir * Math.PI) / 2);
  c.fillStyle = color;
  c.beginPath();
  c.moveTo(0, -s);
  c.lineTo(s * 0.85, 0);
  c.lineTo(s * 0.35, 0);
  c.lineTo(s * 0.35, s);
  c.lineTo(-s * 0.35, s);
  c.lineTo(-s * 0.35, 0);
  c.lineTo(-s * 0.85, 0);
  c.closePath();
  c.fill();
  c.restore();
}

// ---------------------------------------------------------------- Boo-lloon Pump

class Pump extends Game {
  constructor(s) {
    super(s);
    this.target = this.params.target;
    this.local = 0;
    this.server = {};
    this.last = 0;
    this.popped = {};
    this.side = null;  // the last key: a pump is left then right, or right then left
    this.hint = 'Alternate ← and → (or A and D) to pump';
  }
  snap(m) {
    this.server = m.prog || {};
    for (const id of this.ids) {
      if (this.count(id) >= this.target && !this.popped[id]) { this.popped[id] = this.t; this.sound('pop'); }
    }
  }
  count(id) {
    const v = this.server[id] || 0;
    return id === this.me ? Math.max(v, this.local) : v;
  }
  pump(side) {
    const t = performance.now();
    if (side === this.side) { this.stall = 1; return; }  // the same key twice does nothing
    this.side = side;
    if (this.local >= this.target || t - this.last < 50) return;
    this.last = t;
    this.local++;
    this.send({ t: 'pump' });
    this.sound('pump');
    this.squish = 1;
  }
  key(e, down, live) {
    if (!down || !live) return;
    if (e.code === 'ArrowLeft' || e.code === 'KeyA') this.pump('L');
    else if (e.code === 'ArrowRight' || e.code === 'KeyD') this.pump('R');
  }
  // on a touch screen: tap the left half, then the right
  pointer(type, x, y, id, live) { if (type === 'pointerdown' && live) this.pump(x < this.W / 2 ? 'L' : 'R'); }
  draw(t, dt) {
    const c = this.c, n = this.ids.length;
    this.squish = Math.max(0, (this.squish || 0) - dt * 6);
    this.stall = Math.max(0, (this.stall || 0) - dt * 3);
    if (this.playing && this.local < this.target) {
      // which key is next
      const next = this.side === 'L' ? '→' : this.side === 'R' ? '←' : '← →';
      this.title(next, this.W / 2, this.portrait ? 110 : 96, 46, this.stall > 0 ? '#ff6b6b' : '#ffe066');
    }
    this.ids.forEach((id, i) => {
      const p = this.player(id);
      const cx = (this.W / n) * (i + 0.5);
      const base = this.portrait ? this.H * 0.66 : this.H - 90;
      const k = Math.min(1, this.count(id) / this.target);
      const r = 18 + Math.min(70, (this.W / n) * 0.42 - 18) * k;
      const by = base - 80 - r;
      if (!this.popped[id]) {
        c.strokeStyle = '#ccc';
        c.lineWidth = 2;
        c.beginPath(); c.moveTo(cx, base - 50); c.lineTo(cx, by + r); c.stroke();
        const wob = Math.sin(t * 3 + i) * 0.06 + (k > 0.85 ? Math.sin(t * 40) * 0.05 : 0);
        art.ghost(c, cx, by, r, { color: p.color, t, tilt: wob, mouth: k > 0.7 ? 'o' : 'line' });
      } else {
        const a = Math.min(1, (t - this.popped[id]) * 2);
        c.globalAlpha = 1 - a;
        for (let j = 0; j < 10; j++) {
          const ang = (j / 10) * Math.PI * 2;
          c.fillStyle = p.color;
          c.beginPath(); c.arc(cx + Math.cos(ang) * (40 + a * 60), by + Math.sin(ang) * (40 + a * 60), 8, 0, Math.PI * 2); c.fill();
        }
        c.globalAlpha = 1;
        this.title('POP!', cx, by, 40, '#ffe066');
      }
      // the pump
      const press = id === this.me ? this.squish * 14 : 0;
      c.fillStyle = '#6b5a7e';
      c.fillRect(cx - 22, base - 50, 44, 50);
      c.fillStyle = '#a99bbd';
      c.fillRect(cx - 4, base - 70 + press, 8, 22);
      c.fillRect(cx - 24, base - 74 + press, 48, 8);
      this.text(p.name, cx, base + 22, 18, id === this.me ? '#ffe066' : '#fff');
      this.text(`${this.count(id)} / ${this.target}`, cx, base + 46, 16, '#cbbfe0');
    });
  }
}

// ---------------------------------------------------------------- Quick Draw

class QuickDraw extends Game {
  constructor(s) {
    super(s);
    this.delays = this.params.delays;
    this.pause = this.params.pause;
    this.r = 0;
    this.phase = 'wait';
    this.at = 0;  // when the current phase started
    this.times = [];
    this.result = '';
    this.others = {};
    this.hint = 'Wait for the coffin to burst open';
  }
  snap(m) { this.others = m.prog || {}; }
  press() {
    if (this.phase === 'wait') {
      this.record(1000, 'Too soon! +1s');
      this.sound('wrong');
    } else if (this.phase === 'draw') {
      const ms = Math.max(80, Math.round((this.t - this.at) * 1000));
      this.record(ms, `${ms} ms`);
      this.sound('hit');
    }
  }
  record(ms, text) {
    this.times.push(ms);
    this.result = text;
    this.phase = 'result';
    this.at = this.t;
    this.prog(this.times);
    if (this.times.length === 3) this.done(this.times);
  }
  key(e, down, live) { if (down && live && ['Space', 'Enter'].includes(e.code)) this.press(); }
  pointer(type, x, y, id, live) { if (type === 'pointerdown' && live) this.press(); }
  draw(t) {
    if (t >= 0 && this.playing) {
      if (this.phase === 'wait' && t - this.at >= this.delays[this.r]) { this.phase = 'draw'; this.at = t; this.sound('go'); }
      else if (this.phase === 'draw' && t - this.at > 1) { this.record(1000, 'Too slow!'); }
      else if (this.phase === 'result' && t - this.at > this.pause && this.times.length < 3) { this.r++; this.phase = 'wait'; this.at = t; }
    }
    const c = this.c;
    const a = this.area(), cx = this.cx(), cy = a.y + a.h / 2 - 10;
    if (this.playing) {
      const open = this.phase === 'draw';
      c.fillStyle = open ? '#1d6b35' : this.phase === 'wait' ? '#3a1520' : '#2a2140';
      c.fillRect(a.x + 10, a.y, a.w - 20, a.h - 6);
      // the coffin
      c.save();
      c.translate(cx, cy);
      c.fillStyle = '#5b3a24';
      c.beginPath();
      c.moveTo(-50, -120); c.lineTo(50, -120); c.lineTo(80, -50); c.lineTo(50, 130); c.lineTo(-50, 130); c.lineTo(-80, -50);
      c.closePath(); c.fill();
      if (open) {
        c.fillStyle = '#120a0a';
        c.fill();
        art.skull(c, 0, -40, 40, {});
        c.restore();
        this.title('DRAW!', cx, a.y + a.h - 40, 56, '#7dff9b');
      } else {
        c.strokeStyle = '#2e1c10'; c.lineWidth = 6;
        c.beginPath(); c.moveTo(0, -90); c.lineTo(0, 30); c.moveTo(-30, -50); c.lineTo(30, -50); c.stroke();
        c.restore();
        if (this.phase === 'wait' && t >= 0) this.title('Wait…', cx, a.y + a.h - 40, 40, '#ffb3b3');
        if (this.phase === 'result') this.title(this.result, cx, a.y + a.h - 40, 40, '#ffe066');
      }
      this.text(`Round ${Math.min(3, this.r + 1)} of 3`, cx, 70, 18, '#ddd');
    }
    this.sideBoard('Times', this.ids.map(id => {
      const v = id === this.me ? this.times : this.others[id] || [];
      return { id, text: v.length ? v.map(ms => (ms >= 1000 ? '✗' : `${(ms / 1000).toFixed(2)}s`)).join(' · ') : '…' };
    }));
  }
}

// ---------------------------------------------------------------- Stop the Needle

class Needle extends Game {
  constructor(s) {
    super(s);
    this.k = 0;
    this.at = 0;
    this.misses = [];
    this.stopped = null;
    this.others = {};
    this.hint = 'Stop the needle in the middle';
  }
  snap(m) { this.others = m.prog || {}; }
  pos(t) {
    const k = Math.min(2, this.k);
    return Math.sin(2 * Math.PI * (this.params.speeds[k] * (t - this.at) + this.params.phase[k]));
  }
  press() {
    if (this.stopped || this.misses.length >= 3) return;
    const p = this.pos(this.t);
    const miss = Math.round(Math.abs(p) * 100);
    this.misses.push(miss);
    this.stopped = { p, t: this.t, miss };
    this.sound(miss < 10 ? 'right' : 'hit');
    this.prog(this.misses);
    if (this.misses.length === 3) this.done(this.misses);
  }
  key(e, down, live) { if (down && live && ['Space', 'Enter'].includes(e.code)) this.press(); }
  pointer(type, x, y, id, live) { if (type === 'pointerdown' && live) this.press(); }
  draw(t) {
    if (this.playing && t >= 0) {
      if (this.stopped && t - this.stopped.t > 1 && this.misses.length < 3) { this.stopped = null; this.k++; this.at = t; }
      if (t > this.s.info.dur - 0.4 && this.misses.length < 3) {
        while (this.misses.length < 3) this.misses.push(100);
        this.done(this.misses);
      }
    }
    const c = this.c;
    const a = this.area(), cx = this.cx(), cy = a.y + a.h * 0.68, R = Math.min(220, a.w * 0.4, a.h * 0.5);
    // the dial
    c.lineWidth = 34;
    c.strokeStyle = '#3a2a52';
    c.beginPath(); c.arc(cx, cy, R, Math.PI, 0); c.stroke();
    c.strokeStyle = '#ffd23f';
    c.beginPath(); c.arc(cx, cy, R, -Math.PI / 2 - 0.25, -Math.PI / 2 + 0.25); c.stroke();
    c.strokeStyle = '#4ee07a';
    c.beginPath(); c.arc(cx, cy, R, -Math.PI / 2 - 0.07, -Math.PI / 2 + 0.07); c.stroke();
    if (this.playing) {
      const p = this.stopped ? this.stopped.p : t >= 0 ? this.pos(t) : this.pos(0);
      const a = -Math.PI / 2 + p * (Math.PI / 2);
      c.strokeStyle = '#fff';
      c.lineWidth = 6;
      c.lineCap = 'round';
      c.beginPath(); c.moveTo(cx, cy); c.lineTo(cx + Math.cos(a) * (R + 20), cy + Math.sin(a) * (R + 20)); c.stroke();
      c.fillStyle = '#9b4fd1';
      c.beginPath(); c.arc(cx, cy, 16, 0, Math.PI * 2); c.fill();
      if (this.stopped) this.title(this.stopped.miss === 0 ? 'Perfect!' : `${this.stopped.miss}% off centre`, cx, cy + 50, 34, '#ffe066');
      this.text(`Try ${Math.min(3, this.k + 1)} of 3`, cx, 70, 18, '#ddd');
    }
    this.sideBoard('Misses (lower is better)', this.ids.map(id => {
      const v = id === this.me ? this.misses : this.others[id] || [];
      return { id, text: v.length ? `${v.join(' + ')}${v.length === 3 ? ` = ${v.reduce((a, b) => a + b, 0)}` : ''}` : '…' };
    }));
  }
}

// ---------------------------------------------------------------- Copycat Spell

class Memory extends Game {
  constructor(s) {
    super(s);
    this.seq = this.params.seq;
    this.n = this.params.start;
    this.phase = 'show';
    this.at = 0;
    this.i = 0;
    this.flash = null;
    this.others = {};
    this.hint = 'Watch the arrows, then repeat them';
  }
  snap(m) { this.others = m.prog || {}; }
  showTime() { return this.n * 0.55 + 0.3; }
  enter(d) {
    if (this.phase !== 'input') return;
    this.flash = { d, t: this.t, ok: d === this.seq[this.i] };
    if (d !== this.seq[this.i]) {
      this.sound('wrong');
      this.phase = 'out';
      this.done([this.n - 1, +this.t.toFixed(2)]);
      return;
    }
    this.sound('tick');
    this.i++;
    if (this.i === this.n) {
      this.sound('right');
      this.prog([this.n, +this.t.toFixed(2)]);
      if (this.n === this.params.max) { this.phase = 'won'; this.done([this.n, +this.t.toFixed(2)]); return; }
      this.phase = 'between';
      this.at = this.t;
    }
  }
  key(e, down, live) {
    if (!down || !live) return;
    const d = ARROWS.indexOf(e.code) >= 0 ? ARROWS.indexOf(e.code) : WASD.indexOf(e.code);
    if (d >= 0) this.enter(d);
  }
  pads() {
    const a = this.area(), s = Math.min(90, a.h * 0.16), cx = this.cx(), cy = a.y + a.h - s * 1.9;
    return [[cx, cy - s * 1.05], [cx + s * 1.1, cy], [cx, cy + s * 1.05 - 10], [cx - s * 1.1, cy]].map(([x, y]) => ({ x: x - s / 2, y: y - s / 2, w: s, h: s }));
  }
  pointer(type, x, y, id, live) {
    if (type !== 'pointerdown' || !live) return;
    this.pads().forEach((r, d) => { if (this.hit(r, x, y)) this.enter(d); });
  }
  draw(t) {
    if (this.playing && t >= 0) {
      if (this.phase === 'show' && t - this.at > this.showTime()) { this.phase = 'input'; this.i = 0; }
      if (this.phase === 'between' && t - this.at > 0.7) { this.n++; this.phase = 'show'; this.at = t; }
      if (t > this.s.info.dur - 0.3 && !this.sentDone) this.done([this.n - 1, +t.toFixed(2)]);
    }
    const cx = this.cx();
    if (this.playing) {
      const big = Math.min(110, this.area().h * 0.16);
      const cy = 60 + big * 1.3;
      if (this.phase === 'show' && t >= 0) {
        const k = (t - this.at) / 0.55;
        const i = Math.floor(k);
        if (i < this.n && k - i < 0.8) arrow(this.c, cx, cy, big, this.seq[i], '#ffd23f');
        this.text(`Watch: ${this.n} arrows`, cx, 66, 18, '#ddd');
      } else if (this.phase === 'input') {
        this.text(`Your turn: ${this.i} / ${this.n}`, cx, 66, 20, '#ffe066');
      } else if (this.phase === 'out') {
        this.title(`Out! You remembered ${this.n - 1}`, cx, cy, 32, '#ff8b8b');
      } else if (this.phase === 'won') {
        this.title('Perfect memory!', cx, cy, 34, '#7dff9b');
      } else if (this.phase === 'between') {
        this.title('Nice!', cx, cy, 40, '#7dff9b');
      }
      this.pads().forEach((r, d) => {
        const lit = this.flash && this.flash.d === d && t - this.flash.t < 0.25;
        this.c.fillStyle = lit ? (this.flash.ok ? '#4ee07a' : '#ff5a5a') : this.phase === 'input' ? '#4a3870' : '#2c2340';
        this.c.beginPath(); this.c.roundRect(r.x, r.y, r.w, r.h, 14); this.c.fill();
        arrow(this.c, r.x + r.w / 2, r.y + r.h / 2, r.w * 0.32, d, '#fff');
      });
    }
    this.sideBoard('Longest spell', this.ids.map(id => {
      const v = id === this.me ? (this.phase === 'out' ? [this.n - 1] : [this.n - (this.phase === 'won' ? 0 : 1)]) : this.others[id];
      return { id, text: v ? `${v[0]}` : '…', frac: v ? v[0] / this.params.max : 0 };
    }));
  }
}

// ---------------------------------------------------------------- Count the Creeps

const PLURAL = { bat: 'BATS', ghost: 'GHOSTS', pumpkin: 'PUMPKINS', spider: 'SPIDERS' };
const CRIT_COLOR = { ghost: '#f4f1ff', pumpkin: '#f07b1d', bat: '#7a5fa8', spider: '#a58fc4' };

class Count extends Game {
  constructor(s) {
    super(s);
    const P = this.params;
    this.span = P.show + P.ans + P.reveal;
    this.answers = P.rounds.map(r => r.items.filter(it => it[0] === r.target).length);
    this.r = 0;
    this.guess = 10;
    this.locked = false;
    this.miss = 0;
    this.took = 0;
    this.others = {};
    this.hint = 'Count the critters you’re asked for';
  }
  snap(m) { this.others = m.prog || {}; }
  // where we are: round, and phase ('show', 'ans' or 'reveal') with seconds into it
  phase() {
    const P = this.params;
    const r = Math.min(P.rounds.length - 1, Math.max(0, Math.floor(this.t / this.span)));
    const into = this.t - r * this.span;
    if (into < P.show) return { r, ph: 'show', into };
    if (into < P.show + P.ans) return { r, ph: 'ans', into: into - P.show };
    return { r, ph: 'reveal', into: into - P.show - P.ans };
  }
  submit(timeout) {
    if (this.locked || (!timeout && this.phase().ph !== 'ans')) return;
    const P = this.params, { r, into } = this.phase();
    this.locked = true;
    this.miss += Math.abs(this.guess - this.answers[r]);
    this.took += timeout ? P.ans : into;
    if (!timeout) this.sound('right');
    if (r === P.rounds.length - 1) this.done([this.miss, +this.took.toFixed(2)]);
    else this.prog([r + 1]);
  }
  bump(d) { if (!this.locked && this.phase().ph === 'ans') { this.guess = Math.max(0, Math.min(99, this.guess + d)); this.typed = false; this.sound('tick'); } }
  key(e, down, live) {
    if (!down || !live) return;
    if (e.code === 'ArrowUp' || e.code === 'ArrowRight' || e.code === 'KeyW') this.bump(1);
    else if (e.code === 'ArrowDown' || e.code === 'ArrowLeft' || e.code === 'KeyS') this.bump(-1);
    else if (e.code === 'Enter' || e.code === 'Space') this.submit();
    else if (/^Digit\d$/.test(e.code) && !this.locked && this.phase().ph === 'ans') {
      const d = +e.code.slice(5);
      this.guess = this.typed ? Math.min(99, this.guess * 10 + d) : d;
      this.typed = this.guess < 10;
    }
  }
  rects() {
    const cy = this.H / 2;
    return {
      minus: { x: this.W / 2 - 200, y: cy - 45, w: 90, h: 90 },
      plus: { x: this.W / 2 + 110, y: cy - 45, w: 90, h: 90 },
      ok: { x: this.W / 2 - 110, y: cy + 80, w: 220, h: 70 },
    };
  }
  pointer(type, x, y, id, live) {
    if (type !== 'pointerdown' || !live) return;
    const r = this.rects();
    if (this.hit(r.minus, x, y)) this.bump(-1);
    if (this.hit(r.plus, x, y)) this.bump(1);
    if (this.hit(r.ok, x, y)) this.submit();
  }
  draw(t) {
    const P = this.params;
    const { r, ph, into } = this.phase();
    const round = P.rounds[r];
    if (r !== this.r) { this.r = r; this.locked = false; this.guess = 10; this.typed = false; }
    if (ph === 'reveal' && this.playing && !this.locked) this.submit(true);  // out of time: lock in what's there
    this.text(`Round ${r + 1} of ${P.rounds.length}`, this.W / 2, 40, 15, '#cbbfe0');
    if (ph === 'show') {
      this.text(`Count the ${PLURAL[round.target]}`, this.W / 2, 64, 24, '#ffe066');
      if (t >= 0) {
        for (const [kind, x, y, at] of round.items) {
          const age = into - at;
          if (age < 0 || age > P.life) continue;
          const pop = Math.min(1, age * 8) * Math.min(1, (P.life - age) * 8);
          const px = 30 + (x / 100) * (this.W - 60), py = 90 + (y / 100) * (this.H - 120);
          art.CRITTERS[kind](this.c, px, py, 24 * pop, { t, color: CRIT_COLOR[kind] });
        }
      }
      return;
    }
    if (ph === 'reveal') {
      this.title(`It was ${this.answers[r]}`, this.W / 2, this.H / 2 - 20, 64, '#ffe066');
      if (this.playing) this.text(`You said ${this.guess} · off by ${this.miss} so far`, this.W / 2, this.H / 2 + 40, 20, '#fff');
      return;
    }
    if (this.playing) {
      const b = this.rects();
      this.text(`How many ${PLURAL[round.target]}?`, this.W / 2, 80, 26, '#ffe066');
      this.title(String(this.guess), this.W / 2, this.H / 2, 96, this.locked ? '#7dff9b' : '#fff');
      this.button(b.minus, '−', { size: 48 });
      this.button(b.plus, '+', { size: 48 });
      this.button(b.ok, this.locked ? 'Locked in' : 'Lock in', { on: !this.locked, size: 26 });
      this.text(`${Math.max(0, P.ans - into).toFixed(0)}s to lock in`, this.W / 2, this.H / 2 + 175, 15, '#cbbfe0');
    }
    const answered = this.ids.filter(id => (id === this.me ? this.locked : (this.others[id] || [0])[0] > r));
    this.text(`${answered.length} of ${this.ids.length} answered`, this.W / 2, this.H - 30, 16, '#cbbfe0');
  }
}

// ---------------------------------------------------------------- Whack-a-Bat

const WHACK_KEYS = ['KeyQ', 'KeyW', 'KeyE', 'KeyA', 'KeyS', 'KeyD', 'KeyZ', 'KeyX', 'KeyC'];

class Whack extends Game {
  constructor(s) {
    super(s);
    this.pops = this.params.pops.map(([t, cell, kind]) => ({ t, cell, kind, hit: null }));
    this.score = 0;
    this.others = {};
    this.marks = [];
    this.hint = 'Whack bats, spare ghosts';
  }
  snap(m) { this.others = m.prog || {}; }
  cells() {
    const a = this.area();
    const size = Math.min(a.h - 20, a.w - 20);
    const x0 = this.cx() - size / 2, y0 = a.y + (a.h - size) / 2;
    const s = size / 3;
    return Array.from({ length: 9 }, (_, i) => ({ x: x0 + (i % 3) * s, y: y0 + Math.floor(i / 3) * s, w: s, h: s }));
  }
  whack(cell) {
    const t = this.t;
    const p = this.pops.find(q => q.cell === cell && !q.hit && t >= q.t && t < q.t + this.params.up);
    if (!p) return;
    p.hit = t;
    this.score += p.kind === 'bat' ? 1 : -2;
    this.sound(p.kind === 'bat' ? 'hit' : 'wrong');
    this.marks.push({ cell, t, text: p.kind === 'bat' ? '+1' : '−2' });
    this.prog([this.score]);
  }
  key(e, down, live) { if (down && live && WHACK_KEYS.includes(e.code)) this.whack(WHACK_KEYS.indexOf(e.code)); }
  pointer(type, x, y, id, live) {
    if (type !== 'pointerdown' || !live) return;
    this.cells().forEach((r, i) => { if (this.hit(r, x, y)) this.whack(i); });
  }
  draw(t) {
    const last = this.pops[this.pops.length - 1];
    if (this.playing && t > last.t + this.params.up + 0.3) this.done([this.score]);
    const c = this.c;
    if (this.playing) {
      this.cells().forEach((r, i) => {
        c.fillStyle = '#241b33';
        c.fillRect(r.x + 6, r.y + 6, r.w - 12, r.h - 12);
        const p = this.pops.find(q => q.cell === i && t >= q.t && t < q.t + this.params.up && !q.hit);
        const cx = r.x + r.w / 2, cy = r.y + r.h / 2;
        if (p) {
          const rise = Math.min(1, (t - p.t) * 7) * Math.min(1, (p.t + this.params.up - t) * 7);
          if (p.kind === 'bat') art.bat(c, cx, cy + 20 - rise * 20, r.w * 0.22, { t });
          else art.ghost(c, cx, cy + 20 - rise * 20, r.w * 0.25, { t });
        }
        art.tombstone(c, cx, r.y + r.h - 22, r.w * 0.16, {});
        this.text(WHACK_KEYS[i].slice(3), r.x + 18, r.y + 20, 13, 'rgba(255,255,255,0.3)');
        const m = this.marks.find(q => q.cell === i && t - q.t < 0.5);
        if (m) this.title(m.text, cx, cy - 20 - (t - m.t) * 40, 30, m.text === '+1' ? '#7dff9b' : '#ff6b6b');
      });
    }
    this.sideBoard('Points', this.ids.map(id => {
      const v = id === this.me ? this.score : (this.others[id] || [0])[0];
      return { id, text: String(v) };
    }));
  }
}

// ---------------------------------------------------------------- Odd Ghost Out

const BASE = { ghost: '#f4f1ff', pumpkin: '#f07b1d', bat: '#3d2f52', skull: '#efe9dc' };
const SHADE = { ghost: '#d9d0ff', pumpkin: '#f9a548', bat: '#5a4478', skull: '#d8ccb0' };

class OddOne extends Game {
  constructor(s) {
    super(s);
    this.rounds = this.params.rounds;
    this.r = 0;
    this.penalty = 0;
    this.wrong = null;
    this.others = {};
    this.hint = 'Find the one that’s different';
  }
  snap(m) { this.others = m.prog || {}; }
  grid() {
    const R = this.rounds[this.r];
    const a = this.area(), areaW = a.w - 20, areaH = a.h - 34;
    const s = Math.min(areaW / R.cols, areaH / R.rows);
    const x0 = a.x + 10 + (areaW - s * R.cols) / 2, y0 = a.y + 26 + (areaH - s * R.rows) / 2;
    return Array.from({ length: R.cols * R.rows }, (_, i) => ({ x: x0 + (i % R.cols) * s, y: y0 + Math.floor(i / R.cols) * s, w: s, h: s }));
  }
  pick(i) {
    if (this.r >= this.rounds.length) return;
    if (i === this.rounds[this.r].odd) {
      this.sound('right');
      this.r++;
      const total = +(this.t + this.penalty).toFixed(2);
      this.prog([this.r, total]);
      if (this.r === this.rounds.length) this.done([this.r, total]);
    } else {
      this.sound('wrong');
      this.penalty += 2;
      this.wrong = { i, t: this.t };
    }
  }
  pointer(type, x, y, id, live) {
    if (type !== 'pointerdown' || !live || this.r >= this.rounds.length) return;
    this.grid().forEach((r, i) => { if (this.hit(r, x, y)) this.pick(i); });
  }
  draw(t) {
    if (this.playing && t > this.s.info.dur - 0.3 && !this.sentDone) this.done([this.r, +(t + this.penalty).toFixed(2)]);
    if (this.playing && t >= 0) {
      if (this.r < this.rounds.length) {
        const R = this.rounds[this.r];
        this.grid().forEach((cell, i) => {
          const odd = i === R.odd;
          const o = { t, color: BASE[R.kind] };
          let size = cell.w * 0.34;
          if (odd) {
            if (R.diff === 'eye') o.eyes = 1;
            if (R.diff === 'mouth') { o.mouth = R.kind === 'pumpkin' ? 'o' : R.kind === 'ghost' ? 'line' : 'flat'; o.eyeColor = '#ff5a5a'; }
            if (R.diff === 'tilt') o.tilt = 0.4;
            if (R.diff === 'shade') o.color = SHADE[R.kind];
            if (R.diff === 'small') size *= 0.82;
          }
          if (R.kind === 'bat') o.t = 0.1;  // bats hold still, or a flap would give it away
          if (R.kind === 'ghost') o.t = 0;
          art.CRITTERS[R.kind](this.c, cell.x + cell.w / 2, cell.y + cell.h / 2, size, o);
          if (this.wrong && this.wrong.i === i && t - this.wrong.t < 0.5) {
            this.c.strokeStyle = '#ff5a5a';
            this.c.lineWidth = 4;
            this.c.strokeRect(cell.x + 4, cell.y + 4, cell.w - 8, cell.h - 8);
          }
        });
        this.text(`Crowd ${this.r + 1} of ${this.rounds.length}${this.penalty ? `  (+${this.penalty}s)` : ''}`, this.cx(), 60, 16, '#cbbfe0');
      } else {
        this.title('All found!', this.cx(), this.H / 2, 44, '#7dff9b');
      }
    }
    this.sideBoard('Found', this.ids.map(id => {
      const v = id === this.me ? this.r : (this.others[id] || [0])[0];
      return { id, text: `${v} / ${this.rounds.length}`, frac: v / this.rounds.length };
    }));
  }
}

export const SOLO = { pump: Pump, draw: QuickDraw, needle: Needle, memory: Memory, count: Count, whack: Whack, odd: OddOne };
