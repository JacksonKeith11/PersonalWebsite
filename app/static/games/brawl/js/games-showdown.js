// More one-against-the-rest minigames (showdown.py on the server): Candy Bash, Look Away, and
// Red Light, Green Light. In each, params.solo is the one.

import { Game } from './base.js?v=6';
import { Arena } from './games-live.js?v=6';
import * as art from './art.js?v=6';

const now = () => performance.now() / 1000;

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

// ---------------------------------------------------------------- Candy Bash

class CandyBash extends Arena {
  constructor(s) {
    super(s);
    this.solo = this.params.solo;
    this.hint = this.solo === this.me ? 'Keep your sack: run!' : 'Bump the sack! Dash to knock out more';
    this.bag = this.params.bag;
  }
  onSnap(m) {
    if (m.bag < this.bag) this.sound(this.solo === this.me ? 'lose' : 'coin');
    this.bag = m.bag;
  }
  drawField() {
    const c = this.c, f = this.field();
    c.fillStyle = '#2f6b3a';
    c.fillRect(f.x, f.y, 100 * f.s, 100 * f.s);
    c.fillStyle = 'rgba(255,255,255,0.05)';
    for (let i = 0; i < 10; i += 2) c.fillRect(f.x + i * 10 * f.s, f.y, 10 * f.s, 100 * f.s);
    c.strokeStyle = '#f2e3b3';
    c.lineWidth = 4;
    c.strokeRect(f.x, f.y, 100 * f.s, 100 * f.s);
    for (const [x, y] of (this.cur && this.cur.m.c) || []) {
      const [px, py] = this.at(x, y);
      art.coin(c, px, py, 2.4 * f.s, 1);
    }
  }
  drawDisc(d, t) {
    if (d.id === this.solo) {
      // the sack, on their back, shrinking as it empties
      const c = this.c, [x, y] = this.at(d.x, d.y), s = this.field().s;
      const k = 0.5 + 0.5 * this.bag / this.params.bag;
      c.fillStyle = '#b07a3c';
      c.strokeStyle = '#5a3a14';
      c.lineWidth = 2;
      c.beginPath(); c.arc(x + 3 * s, y + 2 * s, 5.5 * s * k, 0, Math.PI * 2); c.fill(); c.stroke();
      if (this.cur && this.cur.m.safe && Math.floor(t * 12) % 2) return;  // blink while safe
    }
    super.drawDisc(d, t);
  }
  drawOver() {
    const keep = this.params.keep;
    const color = this.bag >= keep ? '#7dff9b' : '#ff6b6b';
    this.text(`Sack: ${this.bag} / ${this.params.bag}`, 14, 70, 20, color, 'left');
    this.text(`${this.player(this.solo).name} needs ${keep}`, 14, 96, 15, '#cbbfe0', 'left');
  }
}

// ---------------------------------------------------------------- Look Away

const DIRS = ['ArrowUp', 'ArrowRight', 'ArrowDown', 'ArrowLeft'];
const WASD = ['KeyW', 'KeyD', 'KeyS', 'KeyA'];

class LookAway extends Game {
  constructor(s) {
    super(s);
    this.solo = this.params.solo;
    this.q = null;
    this.mine = null;
    this.hint = this.solo === this.me ? 'Point where you think they’ll look' : 'Don’t look where they point!';
  }
  snap(m) {
    if (m.mine != null) this.mine = m.mine;
    if (this.q && this.q.phase === 'pick' && m.phase === 'show') {
      const caught = Object.keys(m.out).length > Object.keys(this.q.out).length;
      this.sound(caught ? 'boo' : 'wrong');
    }
    if (this.q && this.q.phase !== 'pick' && m.phase === 'pick') this.mine = null;
    this.q = { ...m, at: now() };
  }
  canPick() {
    const q = this.q;
    return q && q.phase === 'pick' && this.playing && (this.me === this.solo || !(String(this.me) in q.out));
  }
  pick(d) {
    if (!this.canPick()) return;
    this.mine = d;
    this.send({ t: 'look', d });
    this.sound('click');
  }
  // wide screens: everyone on the left, the arrows on the right; tall ones: arrows underneath
  get wide() { return this.W > this.H * 1.2; }
  pads() {
    const s = Math.min(90, this.H * 0.14);
    const cx = this.wide ? this.W * 0.83 : this.W / 2, cy = this.wide ? this.H * 0.56 : this.H - s * 2.1;
    return [[0, -1], [1, 0], [0, 1], [-1, 0]].map(([dx, dy]) => ({ x: cx + dx * (s + 8) - s / 2, y: cy + dy * (s + 8) - s / 2, w: s, h: s }));
  }
  key(e, down, live) {
    if (!down || !live) return;
    const i = Math.max(DIRS.indexOf(e.code), WASD.indexOf(e.code));
    if (i >= 0) this.pick(i);
  }
  pointer(type, x, y, id, live) {
    if (type !== 'pointerdown' || !live) return;
    this.pads().forEach((r, i) => { if (this.hit(r, x, y)) this.pick(i); });
  }
  draw(t) {
    const q = this.q;
    if (!q) return;
    const c = this.c, W = this.wide ? this.W * 0.66 : this.W;
    const solo = this.player(this.solo);
    const left = Math.max(0, Math.ceil(q.left - (now() - q.at)));
    const iAmSolo = this.me === this.solo;
    let msg;
    if (q.phase === 'pick') msg = iAmSolo ? `Point a way! (${left})` : (String(this.me) in q.out || !this.playing) ? `They’re choosing… (${left})` : `Look a way! (${left})`;
    else if (q.phase === 'show') msg = 'Look!';
    else msg = Object.keys(q.out).length === this.ids.length - 1 ? `${solo.name} got everyone!` : 'The lookers win!';
    this.title(msg, W / 2, 70, 30, '#ffe066');
    this.text(`Round ${Math.min(q.round + 1, this.params.rounds)} of ${this.params.rounds}`, W / 2, 100, 15, '#cbbfe0');
    // the pointer, in the middle, with a big arrow once it's shown
    const py = this.wide ? this.H * 0.36 : this.H * 0.3;
    art.token(c, W / 2, py, 30, solo.color, { label: solo.name.slice(0, 1), ring: this.me === this.solo ? '#ffe066' : '#fff', t });
    this.text(solo.name, W / 2, py + 46, 16, this.me === this.solo ? '#ffe066' : '#fff');
    const last = q.last;
    if (last) arrow(c, W / 2 + [0, 70, 0, -70][last.solo], py + [-62, 0, 62, 0][last.solo], 26, last.solo, '#ff6b3d');
    else if (q.phase === 'pick' && iAmSolo && this.mine != null) arrow(c, W / 2 + [0, 70, 0, -70][this.mine], py + [-62, 0, 62, 0][this.mine], 22, this.mine, 'rgba(255,224,102,0.6)');
    // the lookers in a row
    const lookers = this.ids.filter(id => id !== this.solo);
    const ry = this.wide ? this.H * 0.72 : this.H * 0.52;
    lookers.forEach((id, k) => {
      const x = (W / (lookers.length + 1)) * (k + 1);
      const p = this.player(id), out = String(id) in q.out;
      const fresh = out && last && q.out[id] === q.round && q.phase !== 'pick';
      art.token(c, x, ry, 22, p.color, { label: p.name.slice(0, 1), ring: id === this.me ? '#ffe066' : '#fff', dim: out && !fresh, t });
      this.text(p.name, x, ry + 36, 15, id === this.me ? '#ffe066' : '#fff');
      let dir = last ? last.picks[id] : null;
      if (dir == null && q.phase === 'pick' && id === this.me) dir = this.mine;
      if (dir != null && (!out || fresh)) arrow(c, x + 44, ry, 14, dir, last ? (dir === last.solo ? '#ff6b3d' : '#7dff9b') : 'rgba(255,224,102,0.7)');
      if (q.phase === 'pick' && !out && (q.in || []).includes(id)) this.text('✓', x - 36, ry - 20, 16, '#7dff9b');
      if (out) this.text(fresh ? 'CAUGHT!' : 'out', x, ry - 34, fresh ? 18 : 14, '#ff6b6b');
    });
    if (this.canPick()) {
      this.pads().forEach((r, i) => {
        c.fillStyle = this.mine === i ? '#ffe066' : '#3a2a52';
        c.beginPath(); c.roundRect(r.x, r.y, r.w, r.h, 12); c.fill();
        arrow(c, r.x + r.w / 2, r.y + r.h / 2, r.w * 0.32, i, this.mine === i ? '#1a1020' : '#fff');
      });
    }
  }
}

// ---------------------------------------------------------------- Red Light, Green Light

class RedLight extends Game {
  constructor(s) {
    super(s);
    this.solo = this.params.solo;
    this.q = null;
    this.on = false;  // holding run
    this.seen = new Set();
    this.hint = this.solo === this.me ? 'Space or click to turn round' : 'Hold ↑ to run; let go when they turn!';
  }
  snap(m) {
    if (this.q && this.q.state === 'away' && m.state === 'turning') this.sound('turn');
    for (const [id, at] of m.flash || []) {
      const k = `${id},${at}`;
      if (!this.seen.has(k)) { this.seen.add(k); this.sound(id === this.me ? 'lose' : 'boo'); }
    }
    this.q = { ...m, at: now() };
  }
  run(on) {
    if (this.me === this.solo || !this.playing || on === this.on) return;
    this.on = on;
    this.send({ t: 'run', on: on ? 1 : 0 });
  }
  key(e, down, live) {
    if (!live) return;
    if (this.me === this.solo) {
      if (down && (e.code === 'Space' || e.code === 'Enter')) this.send({ t: 'turn' });
      return;
    }
    if (['ArrowUp', 'KeyW', 'Space'].includes(e.code)) this.run(down);
  }
  pointer(type, x, y, id, live) {
    if (!live) return;
    if (this.me === this.solo) { if (type === 'pointerdown') this.send({ t: 'turn' }); return; }
    if (type === 'pointerdown') this.run(true);
    else if (type === 'pointerup' || type === 'pointercancel') this.run(false);
  }
  end() { this.run(false); }
  draw(t) {
    const q = this.q;
    if (!q) return;
    const c = this.c, W = this.W, H = this.H;
    const runners = this.ids.filter(id => id !== this.solo);
    const top = 120, bottom = H - 50, laneW = Math.min(140, (W - 80) / runners.length);
    const x0 = (W - laneW * runners.length) / 2;
    // the field, lanes and the finish line
    c.fillStyle = '#3b7a3f';
    c.fillRect(x0 - 20, top - 20, laneW * runners.length + 40, bottom - top + 40);
    for (let i = 1; i < runners.length; i++) {
      c.fillStyle = 'rgba(255,255,255,0.35)';
      c.fillRect(x0 + i * laneW - 1, top, 2, bottom - top);
    }
    for (let i = 0; i < 12; i++) {
      c.fillStyle = i % 2 ? '#fff' : '#222';
      c.fillRect(x0 + (laneW * runners.length / 12) * i, top - 6, laneW * runners.length / 12, 8);
    }
    // the watcher, past the finish
    const solo = this.player(this.solo);
    const looking = q.state === 'looking', turning = q.state === 'turning';
    const wx = W / 2, wy = 66;
    if (looking || turning) {
      art.token(c, wx, wy, 26, solo.color, { label: solo.name.slice(0, 1), ring: looking ? '#ff3b3b' : '#ffe066', t });
    } else {
      // back turned: no face
      c.fillStyle = solo.color;
      c.beginPath(); c.arc(wx, wy, 26, 0, Math.PI * 2); c.fill();
      c.strokeStyle = '#fff'; c.lineWidth = 3; c.stroke();
    }
    this.text(solo.name, wx + 40, wy, 15, this.me === this.solo ? '#ffe066' : '#fff', 'left');
    const banner = looking ? ['RED LIGHT!', '#ff4b4b'] : turning ? ['Turning…', '#ffe066'] : q.state === 'rest' ? ['', ''] : ['GREEN LIGHT', '#7dff9b'];
    if (banner[0]) this.title(banner[0], W / 2 - 170, wy, 26, banner[1]);
    if (looking) { c.fillStyle = 'rgba(255,40,40,0.08)'; c.fillRect(0, 0, W, H); }
    // the runners
    const moving = new Set(q.mv || []);
    const flashed = new Set((q.flash || []).map(f => f[0]));
    runners.forEach((id, k) => {
      const p = this.player(id);
      const frac = (q.pos[id] || 0) / 100;
      const x = x0 + laneW * (k + 0.5), y = bottom - frac * (bottom - top);
      const bob = moving.has(id) ? Math.sin(t * 18) * 3 : 0;
      art.token(c, x, y + bob, 17, p.color, { label: p.name.slice(0, 1), ring: id === this.me ? '#ffe066' : '#fff', t });
      this.text(p.name, x, Math.min(bottom + 26, y + 30), 14, id === this.me ? '#ffe066' : '#fff');
      if (flashed.has(id)) this.title('Caught!', x, bottom - 40, 20, '#ff6b6b');
      if ((q.home || []).includes(id)) this.text('Home!', x, top + 26, 16, '#ffe066');
    });
    this.text(`The runners need ${this.params.need} home`, W - 16, H - 16, 14, '#cbbfe0', 'right');
  }
}

export const SHOWDOWN = { bash: CandyBash, look: LookAway, redlight: RedLight };
