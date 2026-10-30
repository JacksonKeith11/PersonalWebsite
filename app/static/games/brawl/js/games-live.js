// The live minigames, run on the server: trivia, draw-and-guess, tug of war, and the arena games
// (bumper ring, candy grab, ghost tag, pumpkin drop), which send a stick and a dash 20 times a
// second and draw the server's snapshots, smoothed between arrivals.

import { Game, TEAM_COLORS } from './base.js?v=5';
import * as art from './art.js?v=5';

const now = () => performance.now() / 1000;
const coarse = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;

function wrap(c, text, width) {
  const words = text.split(' ');
  const lines = [];
  let line = '';
  for (const w of words) {
    const test = line ? `${line} ${w}` : w;
    if (c.measureText(test).width > width && line) { lines.push(line); line = w; } else line = test;
  }
  if (line) lines.push(line);
  return lines;
}

// ---------------------------------------------------------------- Trivia Night

class Trivia extends Game {
  constructor(s) {
    super(s);
    this.q = null;
    this.mine = {};
    this.got = 0;
    this.hint = 'Quick right answers score more';
  }
  snap(m) {
    if (m.q == null) return;
    if (this.q && !this.q.asking && m.asking && m.i !== this.q.i) this.sound('tick');
    if (this.q && this.q.asking && !m.asking) this.sound(this.mine[m.i] === m.a ? 'right' : 'wrong');
    this.q = { ...m, at: now() };
  }
  opts() {
    const portrait = this.portrait;
    const top = portrait ? this.H * 0.42 : 230;
    const w = portrait ? this.W - 60 : (this.W - 70) / 2;
    const h = portrait ? Math.min(90, (this.H - top - 40) / 4 - 12) : 80;
    return [0, 1, 2, 3].map(i => portrait
      ? { x: 30, y: top + i * (h + 12), w, h }
      : { x: 25 + (i % 2) * (w + 20), y: top + Math.floor(i / 2) * (h + 16), w, h });
  }
  pick(a) {
    const q = this.q;
    if (!q || !q.asking || this.mine[q.i] != null) return;
    this.mine[q.i] = a;
    this.send({ t: 'ans', q: q.i, a });
    this.sound('click');
  }
  key(e, down, live) {
    if (down && live && /^Digit[1-4]$/.test(e.code)) this.pick(+e.code.slice(5) - 1);
  }
  pointer(type, x, y, id, live) {
    if (type !== 'pointerdown' || !live) return;
    this.opts().forEach((r, i) => { if (this.hit(r, x, y)) this.pick(i); });
  }
  draw() {
    const q = this.q;
    if (!q) return;
    const c = this.c;
    this.text(`Question ${q.i + 1} of ${q.n}`, this.W / 2, 62, 16, '#cbbfe0');
    const left = Math.max(0, q.left - (now() - q.at));
    c.fillStyle = q.asking ? '#ffd23f' : '#666';
    c.fillRect(30, 76, (this.W - 60) * (q.asking ? left / 10 : 0), 6);
    c.font = '700 26px "Source Serif 4", Georgia, serif';
    const lines = wrap(c, q.q, this.W - 80);
    lines.forEach((l, i) => this.title(l, this.W / 2, 118 + i * 34, 26, '#fff'));
    this.opts().forEach((r, i) => {
      let color = '#3a2a52';
      if (!q.asking && i === q.a) color = '#2f8a4a';
      else if (!q.asking && this.mine[q.i] === i) color = '#9b2f2f';
      else if (this.mine[q.i] === i) color = '#6a4fa0';
      this.button(r, `${i + 1}.  ${q.opts[i]}`, { color, size: r.h > 70 ? 22 : 19 });
      if (!q.asking && q.picks) {
        Object.entries(q.picks).filter(([, a]) => a === i).forEach(([pid], k) => {
          c.fillStyle = this.player(+pid).color;
          c.beginPath(); c.arc(r.x + r.w - 16 - k * 18, r.y + 14, 7, 0, Math.PI * 2); c.fill();
        });
      }
    });
    const scores = this.ids.map(id => ({ id, v: (q.pts || {})[id] || 0 })).sort((a, b) => b.v - a.v);
    const answered = new Set(q.in || []);
    const y = this.H - 34;
    scores.forEach((s, i) => {
      const x = (this.W / scores.length) * (i + 0.5);
      const p = this.player(s.id);
      c.fillStyle = p.color;
      c.beginPath(); c.arc(x - 60, y, 8, 0, Math.PI * 2); c.fill();
      this.text(`${p.name} ${s.v}${q.asking && answered.has(s.id) ? ' ✓' : ''}`, x - 46, y, 15, '#fff', 'left');
    });
  }
}

// ---------------------------------------------------------------- Sketchy Spirits

class Sketch extends Game {
  constructor(s) {
    super(s);
    this.artist = this.params.artist;
    this.ops = [];  // from the server
    this.mineOps = [];  // the artist's own, drawn at once
    this.pending = [];
    this.feed = [];
    this.got = [];
    this.word = null;
    this.down = false;
    this.lastPt = null;
    this.sendAt = 0;
    this.hint = this.artist === this.me ? 'You draw! Don’t write letters.' : `${this.player(this.artist).name} draws. You guess.`;
    if (this.playing && this.me !== this.artist) {
      const box = s.input;
      box.hidden = false;
      box.value = '';
      box.placeholder = 'Type a guess and press Enter';
      box.onkeydown = e => {
        if (e.key !== 'Enter' || !box.value.trim()) return;
        this.send({ t: 'guess', text: box.value.trim() });
        box.value = '';
      };
      setTimeout(() => box.focus(), 100);
    }
  }
  pad() {
    // room above for the word, and below for the guesses and the guess box
    const h = this.H - 230, w = Math.min(this.W - 40, h * 1.4);
    return { x: (this.W - w) / 2, y: 100, w, h };
  }
  snap(m) {
    if (m.word) this.word = m.word;
    if (m.ops) {
      if (m.from === 0) this.ops = [];
      const skip = this.ops.length - m.from;
      this.ops.push(...m.ops.slice(Math.max(0, skip)));
    }
    if (m.feed) this.feed = m.feed;
    if (m.got) {
      for (const id of m.got) if (!this.got.includes(id)) { this.got.push(id); this.sound('right'); }
      if (this.got.includes(this.me)) this.s.input.hidden = true;
    }
  }
  clearRect() { const p = this.pad(); return { x: p.x + p.w - 90, y: p.y + p.h + 10, w: 90, h: 40 }; }
  pointer(type, x, y, id, live) {
    if (!live || this.me !== this.artist) return;
    const p = this.pad();
    if (type === 'pointerdown' && this.hit(this.clearRect(), x, y)) {
      this.add(['c']);
      return;
    }
    const ux = ((x - p.x) / p.w) * 100, uy = ((y - p.y) / p.h) * 100;
    const inside = ux >= 0 && ux <= 100 && uy >= 0 && uy <= 100;
    if (type === 'pointerdown' && inside) {
      this.down = true;
      this.add(['n', +ux.toFixed(1), +uy.toFixed(1)]);
      this.lastPt = [ux, uy];
    } else if (type === 'pointermove' && this.down) {
      if (Math.hypot(ux - this.lastPt[0], uy - this.lastPt[1]) < 0.6) return;
      this.add(['l', +Math.min(100, Math.max(0, ux)).toFixed(1), +Math.min(100, Math.max(0, uy)).toFixed(1)]);
      this.lastPt = [ux, uy];
    } else if (type === 'pointerup' || type === 'pointercancel') {
      this.down = false;
    }
  }
  add(op) {
    this.mineOps.push(op);
    this.pending.push(op);
  }
  ink(ops) {
    const c = this.c, p = this.pad();
    c.strokeStyle = '#1d1426';
    c.lineWidth = 4;
    c.lineCap = 'round';
    c.lineJoin = 'round';
    let start = 0;
    for (let i = ops.length - 1; i >= 0; i--) if (ops[i][0] === 'c') { start = i + 1; break; }
    c.beginPath();
    for (let i = start; i < ops.length; i++) {
      const [k, x, y] = ops[i];
      const px = p.x + (x / 100) * p.w, py = p.y + (y / 100) * p.h;
      if (k === 'n') { c.moveTo(px, py); c.lineTo(px + 0.1, py); } else c.lineTo(px, py);
    }
    c.stroke();
  }
  draw(t) {
    if (this.pending.length && now() - this.sendAt > 0.1) {
      this.send({ t: 'ink', ops: this.pending.splice(0, 200) });
      this.sendAt = now();
    }
    const c = this.c, p = this.pad();
    c.fillStyle = '#f6f0e2';
    c.fillRect(p.x, p.y, p.w, p.h);
    this.ink(this.me === this.artist ? this.mineOps : this.ops);
    const artist = this.player(this.artist);
    if (this.me === this.artist) {
      this.title(`Draw: ${(this.word || '').toUpperCase()}`, this.W / 2, 62, 26, '#ffe066');
      this.button(this.clearRect(), 'Clear', { size: 16 });
    } else {
      this.text(`${artist.name} is drawing`, this.W / 2, 52, 15, '#cbbfe0');
      this.title(this.params.hint.replace(/ {2}/g, '   '), this.W / 2, 80, 24, '#ffe066');
    }
    // the guesses
    const y0 = p.y + p.h + 22;
    const shown = this.feed.slice(-3);
    shown.forEach(([pid, text], i) => {
      const who = this.player(pid);
      this.text(`${who.name}: ${text == null ? 'got it! ✓' : text}`, p.x + 4, y0 + i * 20, 15, text == null ? '#7dff9b' : '#ddd', 'left', 600);
    });
    if (this.got.includes(this.me)) this.title('You got it!', this.W / 2, p.y + 30, 28, '#2f8a4a');
  }
  end() { this.s.input.hidden = true; }
}

// ---------------------------------------------------------------- Tug of Doom

class Tug extends Game {
  constructor(s) {
    super(s);
    this.rope = 0;
    this.side = {};
    this.last = 0;
    this.yank = 0;
    this.hint = 'Mash Space, or tap!';
  }
  snap(m) { this.rope = m.rope; this.side = m.side || {}; }
  pull() {
    const t = performance.now();
    if (t - this.last < 50) return;
    this.last = t;
    this.yank = 1;
    this.send({ t: 'pump' });
    this.sound('pump');
  }
  key(e, down, live) { if (down && live && (e.code === 'Space' || e.code === 'Enter')) this.pull(); }
  pointer(type, x, y, id, live) { if (type === 'pointerdown' && live) this.pull(); }
  draw(t, dt) {
    const c = this.c, W = this.W, cy = this.H / 2 + 30;
    this.yank = Math.max(0, this.yank - dt * 5);
    const shift = this.rope * (W * 0.3);
    const pit = Math.min(70, W * 0.12);
    // the pit
    c.fillStyle = '#163d1d';
    c.fillRect(W / 2 - pit, cy + 20, pit * 2, this.H - cy - 20);
    for (let i = 0; i < 6; i++) {
      c.fillStyle = 'rgba(120, 255, 120, 0.5)';
      const bx = W / 2 - pit * 0.8 + ((i * 37 + t * 20) % (pit * 1.6)), by = cy + 40 + ((i * 53 + t * 40) % 60);
      c.beginPath(); c.arc(bx, by, 4 + (i % 3), 0, Math.PI * 2); c.fill();
    }
    c.fillStyle = '#3b2b1d';
    c.fillRect(0, cy + 20, W / 2 - pit, 20);
    c.fillRect(W / 2 + pit, cy + 20, W / 2 - pit, 20);
    // the rope and its marker
    c.strokeStyle = '#c9a36a';
    c.lineWidth = 8;
    c.beginPath(); c.moveTo(40 + shift, cy - 10); c.lineTo(W - 40 + shift, cy - 10); c.stroke();
    c.fillStyle = '#e8303a';
    c.fillRect(W / 2 + shift - 5, cy - 30, 10, 40);
    this.text('▼', W / 2, cy - 50, 22, '#fff');
    (this.teams || []).forEach((team, ti) => {
      team.forEach((id, k) => {
        const p = this.player(id);
        const dir = ti === 0 ? -1 : 1;
        const x = W / 2 + dir * (Math.min(130, W * 0.2) + k * Math.min(70, W * 0.13)) + shift + (id === this.me ? -dir * this.yank * 6 : 0);
        art.token(c, x, cy - 10, 22, p.color, { label: p.name.slice(0, 1), t, ring: TEAM_COLORS[ti] });
        this.text(p.name, x, cy + 60 + (W < 600 ? k * 20 : 0), 15, id === this.me ? '#ffe066' : '#fff');
      });
    });
    this.text('Pull them into the pit!', W / 2, W > 600 ? 70 : 90, 20, '#cbbfe0');
  }
}

// ---------------------------------------------------------------- the arena games

class Arena extends Game {
  constructor(s) {
    super(s);
    this.prev = null;
    this.cur = null;
    this.keys = new Set();
    this.stick = null;  // {id, ox, oy, x, y} for a touch stick
    this.dashWanted = false;
    this.sentAt = 0;
    this.sent = '';
    this.gone = {};
    this.hint = coarse ? 'Drag to roll, tap DASH' : 'WASD or arrows, Space to dash';
  }
  snap(m) {
    if (!m.d) return;
    this.prev = this.cur;
    this.cur = { m, at: now() };
    this.onSnap(m);
  }
  onSnap() {}
  discs() {
    const out = new Map();
    if (!this.cur) return out;
    const a = this.prev ? Math.min(1, (now() - this.cur.at) / Math.max(0.03, this.cur.at - this.prev.at)) : 1;
    const before = new Map(this.prev ? this.prev.m.d.map(d => [d[0], d]) : []);
    for (const d of this.cur.m.d) {
      const b = before.get(d[0]) || d;
      out.set(d[0], { id: d[0], x: b[1] + (d[1] - b[1]) * a, y: b[2] + (d[2] - b[2]) * a, alive: !!d[3], dash: !!d[4], coins: d[5], lives: d[6] });
    }
    return out;
  }
  field() {
    const size = Math.min(this.W - 30, this.H - 60 - (coarse ? 0 : 0));
    return { x: (this.W - size) / 2, y: 46 + (this.H - 46 - size) / 2, s: size / 100 };
  }
  at(x, y) { const f = this.field(); return [f.x + x * f.s, f.y + y * f.s]; }
  dashRect() { return { x: this.W - 140, y: this.H - 130, w: 120, h: 110 }; }
  key(e, down) {
    if (down) this.keys.add(e.code); else this.keys.delete(e.code);
    if (down && e.code === 'Space') this.dashWanted = true;
  }
  pointer(type, x, y, id, live) {
    if (!live) return;
    if (type === 'pointerdown') {
      if (this.hit(this.dashRect(), x, y)) { this.dashWanted = true; return; }
      if (!this.stick) this.stick = { id, ox: x, oy: y, x, y };
    } else if (type === 'pointermove' && this.stick && this.stick.id === id) {
      this.stick.x = x; this.stick.y = y;
    } else if ((type === 'pointerup' || type === 'pointercancel') && this.stick && this.stick.id === id) {
      this.stick = null;
    }
  }
  input() {
    let x = 0, y = 0;
    const k = this.keys;
    if (k.has('KeyA') || k.has('ArrowLeft')) x -= 1;
    if (k.has('KeyD') || k.has('ArrowRight')) x += 1;
    if (k.has('KeyW') || k.has('ArrowUp')) y -= 1;
    if (k.has('KeyS') || k.has('ArrowDown')) y += 1;
    if (this.stick) {
      x = (this.stick.x - this.stick.ox) / 50;
      y = (this.stick.y - this.stick.oy) / 50;
    }
    const m = Math.hypot(x, y);
    if (m > 1) { x /= m; y /= m; }
    return [Math.round(x * 100) / 100, Math.round(y * 100) / 100];
  }
  sendInput() {
    if (!this.playing || this.t < 0 || this.s.ended) return;
    const [x, y] = this.input();
    const key = `${x},${y}`;
    const t = now();
    if (this.dashWanted || (key !== this.sent && t - this.sentAt > 0.045) || t - this.sentAt > 0.5) {
      this.send({ t: 'in', x, y, dash: this.dashWanted ? 1 : 0 });
      if (this.dashWanted) this.sound('pump');
      this.dashWanted = false;
      this.sent = key;
      this.sentAt = t;
    }
  }
  drawDisc(d, t) {
    const [x, y] = this.at(d.x, d.y);
    const p = this.player(d.id);
    const r = 4.2 * this.field().s;
    if (d.dash) {
      this.c.fillStyle = 'rgba(255,255,255,0.25)';
      this.c.beginPath(); this.c.arc(x, y, r * 1.5, 0, Math.PI * 2); this.c.fill();
    }
    art.token(this.c, x, y, r, p.color, { label: p.name.slice(0, 1), ring: d.id === this.me ? '#ffe066' : this.teamRing(d.id), t: t + d.id });
    // games on a light floor set nameColor (and a darker colour for you)
    this.text(p.name, x, y - r - 12, 14, d.id === this.me ? (this.meColor || '#ffe066') : (this.nameColor || '#fff'));
  }
  teamRing(id) {
    if (!this.teams || this.mode === 'ffa' || this.mode === 'duel') return '#fff';
    return this.teams[0].includes(id) ? TEAM_COLORS[0] : TEAM_COLORS[1];
  }
  drawControls() {
    if (!coarse || !this.playing) return;
    const r = this.dashRect();
    this.c.globalAlpha = 0.75;
    this.button(r, this.dashLabel || 'DASH', { color: '#7a2a2a', size: 22 });
    this.c.globalAlpha = 1;
    if (this.stick) {
      const c = this.c;
      c.strokeStyle = 'rgba(255,255,255,0.4)';
      c.lineWidth = 3;
      c.beginPath(); c.arc(this.stick.ox, this.stick.oy, 50, 0, Math.PI * 2); c.stroke();
      const [ix, iy] = this.input();
      c.fillStyle = 'rgba(255,255,255,0.5)';
      c.beginPath(); c.arc(this.stick.ox + ix * 50, this.stick.oy + iy * 50, 20, 0, Math.PI * 2); c.fill();
    }
  }
  draw(t) {
    this.sendInput();
    this.drawField(t);
    const ds = this.discs();
    for (const d of ds.values()) {
      if (d.alive) this.drawDisc(d, t);
      else this.drawGone(d, t);
    }
    this.drawOver(t, ds);
    this.drawControls();
  }
  drawField() {}
  drawOver() {}
  drawGone(d, t) {
    if (this.gone[d.id] == null) { this.gone[d.id] = t; this.sound('fall'); }
    const a = Math.max(0, 1 - (t - this.gone[d.id]) * 1.5);
    if (a <= 0) return;
    const [x, y] = this.at(d.x, d.y);
    this.c.globalAlpha = a;
    art.token(this.c, x, y, 4.2 * this.field().s * a, this.player(d.id).color, { t });
    this.c.globalAlpha = 1;
  }
}

class Bumper extends Arena {
  drawField(t) {
    const c = this.c, f = this.field();
    const r = (this.cur ? this.cur.m.r : 44) * f.s;
    const [cx, cy] = this.at(50, 50);
    // bubbling slime around the stone
    c.fillStyle = '#123a1a';
    c.fillRect(f.x, f.y, 100 * f.s, 100 * f.s);
    for (let i = 0; i < 14; i++) {
      c.fillStyle = 'rgba(110, 255, 120, 0.25)';
      const a = i * 0.9 + t * 0.2;
      c.beginPath(); c.arc(cx + Math.cos(a) * 48 * f.s, cy + Math.sin(a * 1.3) * 48 * f.s, (3 + (i % 4)) * f.s, 0, Math.PI * 2); c.fill();
    }
    const g = c.createRadialGradient(cx, cy, r * 0.2, cx, cy, r);
    g.addColorStop(0, '#77738a');
    g.addColorStop(1, '#4b475c');
    c.fillStyle = g;
    c.beginPath(); c.arc(cx, cy, r, 0, Math.PI * 2); c.fill();
    c.strokeStyle = '#ff6b3d';
    c.lineWidth = 3;
    c.stroke();
    c.strokeStyle = 'rgba(30,25,40,0.6)';
    c.lineWidth = 2;
    for (let i = 0; i < 5; i++) {
      const a = i * 1.3;
      c.beginPath(); c.moveTo(cx + Math.cos(a) * r * 0.3, cy + Math.sin(a) * r * 0.3); c.lineTo(cx + Math.cos(a + 0.2) * r * 0.95, cy + Math.sin(a + 0.2) * r * 0.95); c.stroke();
    }
  }
}

class CandyGrab extends Arena {
  drawField() {
    const c = this.c, f = this.field();
    c.fillStyle = '#2a1f3a';
    c.fillRect(f.x, f.y, 100 * f.s, 100 * f.s);
    c.strokeStyle = '#ff9a3d';
    c.lineWidth = 4;
    c.strokeRect(f.x, f.y, 100 * f.s, 100 * f.s);
    for (const [x, y, v] of (this.cur && this.cur.m.c) || []) {
      const [px, py] = this.at(x, y);
      art.coin(c, px, py, (v > 1 ? 3.2 : 2.4) * f.s, v);
    }
  }
  drawOver() {
    const ds = this.cur ? this.cur.m.d : [];
    const rows = [...ds].sort((a, b) => b[5] - a[5]);
    rows.forEach((d, i) => {
      const p = this.player(d[0]);
      this.text(`${p.name} ${d[5]}`, 14, 60 + i * 22, 16, p.color, 'left');
    });
    if (this.mode === 'team' && this.teams) {
      this.teams.forEach((team, ti) => {
        const sum = ds.filter(d => team.includes(d[0])).reduce((a, d) => a + d[5], 0);
        this.text(`Team ${ti + 1}: ${sum}`, 14, 60 + (rows.length + 0.5 + ti) * 22, 16, TEAM_COLORS[ti], 'left');
      });
    }
  }
}

class GhostTag extends Arena {
  constructor(s) {
    super(s);
    this.solo = this.params.solo;
    this.hint = this.solo === this.me ? 'You’re the ghost: catch them all!' : 'Run from the ghost!';
  }
  drawField(t) {
    const c = this.c, f = this.field();
    c.fillStyle = '#1b2a24';
    c.fillRect(f.x, f.y, 100 * f.s, 100 * f.s);
    c.strokeStyle = '#6b5a7e';
    c.lineWidth = 4;
    c.strokeRect(f.x, f.y, 100 * f.s, 100 * f.s);
    for (let i = 0; i < 6; i++) art.tombstone(c, f.x + (12 + ((i * 37) % 80)) * f.s, f.y + (15 + ((i * 53) % 75)) * f.s, 2.6 * f.s, { tilt: (i % 3 - 1) * 0.15 });
  }
  drawDisc(d, t) {
    if (d.id !== this.solo) return super.drawDisc(d, t);
    const [x, y] = this.at(d.x, d.y);
    const s = 5.5 * this.field().s;
    art.ghost(this.c, x, y, s, { t, color: d.dash ? '#ffffff' : '#d9d2ff' });
    this.text(this.player(d.id).name, x, y - s - 14, 14, d.id === this.me ? '#ffe066' : '#fff');
  }
}

class PumpkinDrop extends Arena {
  constructor(s) {
    super(s);
    this.solo = this.params.solo;
    this.dashLabel = this.solo === this.me ? 'DROP' : 'DASH';
    this.hint = this.solo === this.me ? 'You’re the bat: Space or DROP to drop pumpkins' : 'Dodge the shadows!';
    this.seen = new Set();
  }
  onSnap(m) {
    for (const b of m.bm || []) {
      const k = b.join(',');
      if (!this.seen.has(k)) { this.seen.add(k); this.sound('splash'); }
    }
  }
  drawField() {
    const c = this.c, f = this.field();
    c.fillStyle = '#2b2416';
    c.fillRect(f.x, f.y, 100 * f.s, 100 * f.s);
    c.strokeStyle = '#7a5a2f';
    c.lineWidth = 4;
    c.strokeRect(f.x, f.y, 100 * f.s, 100 * f.s);
    const m = this.cur && this.cur.m;
    if (!m) return;
    const since = now() - this.cur.at;
    for (const [x, y, left] of m.pk || []) {
      const l = Math.max(0, left - since);
      const [px, py] = this.at(x, y);
      c.fillStyle = `rgba(0,0,0,${0.5 - l * 0.3})`;
      c.beginPath(); c.arc(px, py, 9 * f.s * (1 - l * 0.5), 0, Math.PI * 2); c.fill();
      art.pumpkin(c, px, py - l * 120, 3 * f.s, {});
    }
    for (const [x, y] of m.bm || []) {
      const [px, py] = this.at(x, y);
      c.fillStyle = 'rgba(255, 140, 30, 0.45)';
      c.beginPath(); c.arc(px, py, 9 * f.s, 0, Math.PI * 2); c.fill();
    }
  }
  drawDisc(d, t) {
    if (d.id === this.solo) return;
    super.drawDisc(d, t);
    const [x, y] = this.at(d.x, d.y);
    this.text('♥'.repeat(Math.max(0, d.lives)), x, y + 4.2 * this.field().s + 12, 14, '#ff6b6b');
  }
  drawOver(t, ds) {
    const bat = ds.get(this.solo);
    if (!bat) return;
    const [x, y] = this.at(bat.x, bat.y);
    art.bat(this.c, x, y, 5 * this.field().s, { t, color: this.player(this.solo).color });
    this.text(this.player(this.solo).name, x, y - 30, 14, this.solo === this.me ? '#ffe066' : '#fff');
  }
}

export { Arena, coarse };
export const LIVE = { trivia: Trivia, sketch: Sketch, tug: Tug, bumper: Bumper, candy: CandyGrab, tag: GhostTag, drop: PumpkinDrop };
