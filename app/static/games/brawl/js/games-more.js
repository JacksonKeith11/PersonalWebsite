// More minigames' browser halves: Halloween takes on Mario Party favourites. Hex Heat and
// Spellbook Squirm are 3D (three.js, see view3d.js); the rest draw on the 2D stage like the others.

import { Game } from './base.js?v=6';
import { Arena, coarse } from './games-live.js?v=6';
import { View3D, loadThree } from './view3d.js?v=6';
import * as art from './art.js?v=6';
import * as sfx from './audio.js?v=6';

const now = () => performance.now() / 1000;

// ---------------------------------------------------------------- the 3D arena games

class Arena3D extends Arena {
  constructor(s) {
    super(s);
    this.transparent = true;
    this.v = null;
    this.blobs = new Map();
    this.fell = {};
    loadThree().then(T => {
      if (this.closed) return;
      this.v = new View3D(T, s);
      this.build(T);
    }).catch(err => { this.failed = err.message; });
  }
  build() {}
  end() { this.closed = true; if (this.v) this.v.dispose(); }
  draw(t, dt) {
    this.sendInput();
    if (!this.v) {
      this.c.fillStyle = '#140d22';
      this.c.fillRect(0, 0, this.W, this.H);
      this.text(this.failed ? 'Couldn’t load the 3D view.' : 'Loading…', this.W / 2, this.H / 2 + 140, 20, '#cbbfe0');
      return;
    }
    this.update(t, dt);
    const ds = this.discs();
    for (const d of ds.values()) {
      let b = this.blobs.get(d.id);
      if (!b) { b = this.v.blob(this.player(d.id).color); this.blobs.set(d.id, b); }
      if (!d.alive && this.fell[d.id] == null) { this.fell[d.id] = t; this.sound('fall'); }
      const drop = this.fell[d.id] != null ? (t - this.fell[d.id]) : 0;
      b.position.set(d.x - 50, 4.2 - drop * drop * 40, d.y - 50);
      b.visible = drop < 1.5;
      b.scale.setScalar(d.dash ? 1.15 : 1);
    }
    this.v.render();
    for (const d of ds.values()) {
      if (!d.alive) continue;
      const [x, y] = this.v.toStage(d.x - 50, 12, d.y - 50);
      this.text(this.player(d.id).name, x, y, 14, d.id === this.me ? '#ffe066' : '#fff');
    }
    this.overlay(t);
    this.drawControls();
  }
  update() {}
  overlay() {}
}

const HEX_COLORS = ['#ff8a2a', '#7cff6b', '#f2efff', '#b066ff'];
const HEX_NAMES = ['PUMPKIN', 'SLIME', 'GHOST', 'POTION'];

class HexHeat extends Arena3D {
  constructor(s) {
    super(s);
    this.hint = `${this.hint}. Stand on the colour called.`;
    this.tiles = null;
  }
  build(T) {
    this.T = T;
    this.mats = HEX_COLORS.map(c => new T.MeshStandardMaterial({ color: c, roughness: 0.6 }));
    const pit = new T.Mesh(new T.CircleGeometry(80, 48), new T.MeshBasicMaterial({ color: '#0b2a12' }));
    pit.rotation.x = -Math.PI / 2;
    pit.position.y = -40;
    this.v.scene.add(pit);
  }
  makeTiles(m) {
    const T = this.T;
    const geo = new T.CylinderGeometry(m.size * 0.95, m.size * 0.95, 3, 6);
    this.tiles = m.xy.map(([x, y]) => {
      const mesh = new T.Mesh(geo, this.mats[0]);
      mesh.position.set(x - 50, -1.5, y - 50);
      this.v.scene.add(mesh);
      return { mesh, y: -1.5 };
    });
  }
  update(t, dt) {
    const m = this.cur && this.cur.m;
    if (!m) return;
    if (!this.tiles) this.makeTiles(m);
    if (m.phase !== this.phase) {
      if (m.phase === 'drop') this.sound('fall');
      if (m.phase === 'call') this.sound('count');
      this.phase = m.phase;
    }
    m.tiles.forEach((c, i) => {
      const tile = this.tiles[i];
      tile.mesh.material = this.mats[c];
      const down = m.phase === 'drop' && c !== m.called;
      const goal = down ? -45 : -1.5;
      tile.y += (goal - tile.y) * Math.min(1, dt * (down ? 5 : 8));
      // in the last second of a call, the doomed tiles shake
      const shake = m.phase === 'call' && c !== m.called && m.left < 1 ? Math.sin(t * 60 + i) * 0.4 : 0;
      tile.mesh.position.y = tile.y + shake;
    });
  }
  overlay() {
    const m = this.cur && this.cur.m;
    if (!m) return;
    const c = this.c;
    if (m.phase === 'call') {
      c.fillStyle = 'rgba(0,0,0,0.45)';
      c.fillRect(this.W / 2 - 150, 50, 300, 60);
      this.title(HEX_NAMES[m.called], this.W / 2, 74, 34, HEX_COLORS[m.called]);
      c.fillStyle = HEX_COLORS[m.called];
      c.fillRect(this.W / 2 - 140, 100, 280 * Math.min(1, m.left / 4), 5);
    }
    const alive = m.d.filter(d => d[3]).length;
    this.text(`${alive} standing`, 14, 60, 15, '#cbbfe0', 'left');
  }
}

class Squirm extends Arena3D {
  constructor(s) {
    super(s);
    this.hint = `${this.hint}. Get in the hole!`;
    this.page = null;
    this.pageN = -1;
  }
  build(T) {
    this.T = T;
    const floor = new T.Mesh(new T.PlaneGeometry(100, 100), new T.MeshStandardMaterial({ color: '#221a30', roughness: 0.9 }));
    floor.rotation.x = -Math.PI / 2;
    this.v.scene.add(floor);
    const grid = new T.GridHelper(100, 10, '#4a3a63', '#4a3a63');
    grid.position.y = 0.05;
    this.v.scene.add(grid);
    const edge = new T.LineSegments(new T.EdgesGeometry(new T.BoxGeometry(100, 2, 100)), new T.LineBasicMaterial({ color: '#ff9a3d' }));
    edge.position.y = 1;
    this.v.scene.add(edge);
  }
  makePage(p) {
    const T = this.T;
    if (this.page) { this.v.scene.remove(this.page.mesh, this.page.outline, this.page.spot); }
    const shape = new T.Shape();
    shape.moveTo(-60, -60); shape.lineTo(60, -60); shape.lineTo(60, 60); shape.lineTo(-60, 60); shape.lineTo(-60, -60);
    const hole = new T.Path();
    // shape coordinates: (x - 50, -(y - 50)), so that lying flat it lands at (x, y)
    const cx = p.x - 50, cy = -(p.y - 50);
    if (p.shape === 'circle') hole.absarc(cx, cy, p.r, 0, Math.PI * 2, true);
    else {
      hole.moveTo(cx - p.w / 2, cy - p.h / 2); hole.lineTo(cx - p.w / 2, cy + p.h / 2);
      hole.lineTo(cx + p.w / 2, cy + p.h / 2); hole.lineTo(cx + p.w / 2, cy - p.h / 2); hole.lineTo(cx - p.w / 2, cy - p.h / 2);
    }
    shape.holes.push(hole);
    const mesh = new T.Mesh(new T.ExtrudeGeometry(shape, { depth: 1.5, bevelEnabled: false }),
      // see-through, so you can see yourself under it as it falls
      new T.MeshStandardMaterial({ color: '#f4ead2', roughness: 0.8, transparent: true, opacity: 0.32, depthWrite: false }));
    mesh.rotation.x = -Math.PI / 2;
    this.v.scene.add(mesh);
    // where the hole will land, lit up on the floor
    const pts = hole.getPoints(48);
    const outline = new T.LineLoop(new T.BufferGeometry().setFromPoints(pts.map(q => new T.Vector3(q.x, 0.3, -q.y))),
      new T.LineBasicMaterial({ color: '#ffe066' }));
    const spot = new T.Mesh(new T.ShapeGeometry(new T.Shape(pts)), new T.MeshBasicMaterial({ color: '#ffd23f', transparent: true, opacity: 0.55, side: T.DoubleSide }));
    spot.rotation.x = -Math.PI / 2;
    spot.position.y = 0.2;
    this.v.scene.add(outline, spot);
    this.page = { mesh, outline, spot, fall: p.fall, left: p.left, at: now(), landed: null };
    this.pageN = p.n;
  }
  update(t) {
    const m = this.cur && this.cur.m;
    if (!m) return;
    if (m.page && m.page.n !== this.pageN) this.makePage(m.page);
    if (m.page && this.page) { this.page.left = m.page.left; this.page.at = this.cur.at; }
    if (!this.page) return;
    const left = Math.max(0, this.page.left - (now() - this.page.at));
    if (!m.page && this.page.landed == null) { this.page.landed = t; this.sound('hit'); }
    const h = this.page.landed != null ? 0 : 3 + 70 * Math.pow(left / this.page.fall, 1.4);
    this.page.mesh.position.y = h;
    if (this.page.landed != null && t - this.page.landed > 0.5) {
      this.v.scene.remove(this.page.mesh, this.page.outline, this.page.spot);
      this.page = null;
    }
  }
  overlay() {
    const m = this.cur && this.cur.m;
    if (!m) return;
    const alive = m.d.filter(d => d[3]).length;
    this.text(`${alive} standing`, 14, 60, 15, '#cbbfe0', 'left');
    if (m.page) this.text(`Page ${m.page.n + 1}`, this.W - 14, 60, 15, '#cbbfe0', 'right');
  }
}

// ---------------------------------------------------------------- Skeleton Says

const FLAG = ['#ff8a2a', '#f2efff'];

class SkeletonSays extends Game {
  constructor(s) {
    super(s);
    this.q = null;
    this.mine = {};
    this.hint = 'Left: pumpkin flag. Right: bone flag.';
  }
  snap(m) {
    if (this.q && !this.q.calling && m.calling) this.sound('tick');
    if (this.q && this.q.alive.includes(this.me) && !m.alive.includes(this.me)) this.sound('wrong');
    this.q = { ...m, at: now() };
  }
  flag(f) {
    const q = this.q;
    if (!q || !q.calling || this.mine[q.i] != null || !q.alive.includes(this.me)) return;
    this.mine[q.i] = f;
    this.send({ t: 'flag', i: q.i, f });
    this.sound('click');
  }
  key(e, down, live) {
    if (!down || !live) return;
    if (['KeyA', 'ArrowLeft'].includes(e.code)) this.flag(0);
    if (['KeyD', 'ArrowRight'].includes(e.code)) this.flag(1);
  }
  pointer(type, x, y, id, live) { if (type === 'pointerdown' && live && y > 50) this.flag(x < this.W / 2 ? 0 : 1); }
  draw(t) {
    const q = this.q;
    const c = this.c, W = this.W, H = this.H;
    // Top to bottom: the call, the skeleton (scaled to fit), everyone in a row, the flag buttons.
    const rowY = H - 150;
    const sc = Math.max(0.5, Math.min(1, (H - 330) / 260));
    c.save();
    c.translate(W / 2, 120 + 120 * sc);
    c.scale(sc, sc);
    const cx = 0, cy = 0;
    // the skeleton, waving its flags about while it calls
    const up = q && q.calling ? (Math.sin(t * 9) > 0 ? 0 : 1) : -1;
    c.strokeStyle = '#efe9dc';
    c.lineWidth = 8;
    c.lineCap = 'round';
    c.beginPath(); c.moveTo(cx, cy - 20); c.lineTo(cx, cy + 80); c.stroke();
    for (let i = 0; i < 3; i++) { c.beginPath(); c.moveTo(cx - 26, cy + 5 + i * 18); c.lineTo(cx + 26, cy + 5 + i * 18); c.stroke(); }
    c.beginPath(); c.moveTo(cx, cy + 80); c.lineTo(cx - 25, cy + 140); c.moveTo(cx, cy + 80); c.lineTo(cx + 25, cy + 140); c.stroke();
    for (const side of [0, 1]) {
      const dir = side ? 1 : -1;
      const raised = up === side;
      const hx = cx + dir * 70, hy = raised ? cy - 70 : cy + 50;
      c.strokeStyle = '#efe9dc';
      c.beginPath(); c.moveTo(cx, cy); c.lineTo(hx, hy); c.stroke();
      c.strokeStyle = '#7a5a2f';
      c.lineWidth = 4;
      c.beginPath(); c.moveTo(hx, hy + 10); c.lineTo(hx, hy - 50); c.stroke();
      c.fillStyle = FLAG[side];
      c.fillRect(hx - (side ? 0 : 40), hy - 50, 40, 28);
      c.lineWidth = 8;
    }
    art.skull(c, cx, cy - 50, 34, {});
    c.restore();
    if (!q) return;
    if (q.calling) {
      this.title(q.text, W / 2, 82, W < 600 ? 28 : 36, q.text.startsWith('Don') ? '#ff8b8b' : '#ffe066');
      c.fillStyle = '#ffe066';
      const left = Math.max(0, q.left - (now() - q.at));
      c.fillRect(W / 2 - 150, 108, 300 * (left / q.window), 5);
    } else if (q.last) {
      this.text(`It was the ${q.last.flag ? 'bone' : 'pumpkin'} flag`, W / 2, 82, 20, '#cbbfe0');
    }
    if (this.playing && q.alive.includes(this.me)) {
      const mine = this.mine[q.i];
      this.button({ x: 16, y: H - 110, w: W / 2 - 24, h: 90 }, '◀ Pumpkin', { color: mine === 0 ? '#9a4a10' : '#3a2a52', size: 22 });
      this.button({ x: W / 2 + 8, y: H - 110, w: W / 2 - 24, h: 90 }, 'Bone ▶', { color: mine === 1 ? '#77736a' : '#3a2a52', size: 22 });
    } else if (this.playing) {
      this.title('You’re out!', W / 2, H - 65, 30, '#ff8b8b');
    }
    // everyone, with what they raised last time
    const n = this.ids.length;
    this.ids.forEach((id, i) => {
      const x = (W / (n + 1)) * (i + 1), y = rowY;
      const p = this.player(id);
      const out = !q.alive.includes(id);
      art.token(c, x, y, 16, p.color, { label: p.name.slice(0, 1), dim: out, t: t + id });
      const pick = q.last && q.last.picks[id];
      if (!q.calling && pick != null) {
        c.fillStyle = FLAG[pick];
        c.fillRect(x - 8, y - 46, 18, 12);
        c.fillStyle = '#7a5a2f';
        c.fillRect(x - 10, y - 46, 3, 28);
      }
      if (q.calling && q.in.includes(id)) this.text('✓', x + 18, y - 18, 16, '#7dff9b');
      this.text(p.name, x, y + 28, 13, id === this.me ? '#ffe066' : out ? '#777' : '#fff');
    });
  }
}

// ---------------------------------------------------------------- Pumpkin Lift

const FEATURES = ['leye', 'reye', 'nose', 'mouth'];

function drawFeature(c, f, x, y, R, color = '#2a1500') {
  c.fillStyle = color;
  c.beginPath();
  if (f === 'leye' || f === 'reye') {
    c.moveTo(x, y - R * 0.16); c.lineTo(x - R * 0.17, y + R * 0.12); c.lineTo(x + R * 0.17, y + R * 0.12);
  } else if (f === 'nose') {
    c.moveTo(x, y - R * 0.09); c.lineTo(x - R * 0.09, y + R * 0.08); c.lineTo(x + R * 0.09, y + R * 0.08);
  } else {
    c.moveTo(x - R * 0.42, y - R * 0.06);
    for (let i = 0; i <= 6; i++) c.lineTo(x - R * 0.42 + (i * R * 0.84) / 6, y + (i % 2 ? R * 0.06 : -R * 0.06));
    c.quadraticCurveTo(x, y + R * 0.4, x - R * 0.42, y - R * 0.06);
  }
  c.closePath();
  c.fill();
}

class PumpkinLift extends Game {
  constructor(s) {
    super(s);
    this.pos = JSON.parse(JSON.stringify(this.params.start));
    this.drag = null;
    this.sel = 0;
    this.result = null;
    this.others = {};
    this.hint = 'Drag the face to match';
  }
  snap(m) { this.others = m.prog || {}; }
  layout() {
    const a = this.area();
    const R = Math.min(a.w * 0.32, a.h * 0.32);
    if (this.portrait) return { tx: a.w / 2, ty: a.y + R * 0.55, tr: R * 0.45, mx: a.w / 2, my: a.y + a.h - R * 1.25, R };
    return { tx: a.x + R * 0.6, ty: a.y + R * 0.75, tr: R * 0.45, mx: a.x + a.w * 0.6, my: a.y + a.h / 2 + 10, R };
  }
  doneRect() { const l = this.layout(); return { x: l.mx - 70, y: l.my + l.R * 1.05, w: 140, h: 44 }; }
  finish() {
    if (this.result != null) return;
    let d = 0;
    for (const f of FEATURES) d += Math.hypot(this.pos[f][0] - this.params.target[f][0], this.pos[f][1] - this.params.target[f][1]);
    this.result = Math.round(d * 100);
    this.done([this.result]);
    this.sound('right');
  }
  pointer(type, x, y, id, live) {
    if (!live || this.result != null) return;
    const l = this.layout();
    if (type === 'pointerdown') {
      if (this.hit(this.doneRect(), x, y)) { this.finish(); return; }
      let best = null, bd = 1e9;
      for (const f of FEATURES) {
        const fx = l.mx + this.pos[f][0] * l.R, fy = l.my + this.pos[f][1] * l.R;
        const d = Math.hypot(fx - x, fy - y);
        if (d < bd && d < l.R * 0.3) { bd = d; best = f; }
      }
      if (best) this.drag = { f: best, id, dx: l.mx + this.pos[best][0] * l.R - x, dy: l.my + this.pos[best][1] * l.R - y };
    } else if (type === 'pointermove' && this.drag && this.drag.id === id) {
      const f = this.drag.f;
      this.pos[f] = [Math.max(-0.8, Math.min(0.8, (x + this.drag.dx - l.mx) / l.R)), Math.max(-0.75, Math.min(0.75, (y + this.drag.dy - l.my) / l.R))];
    } else if (type === 'pointerup' || type === 'pointercancel') {
      this.drag = null;
    }
  }
  key(e, down, live) {
    if (!down || !live || this.result != null) return;
    if (e.code === 'Tab' || /^Digit[1-4]$/.test(e.code)) { e.preventDefault(); this.sel = e.code === 'Tab' ? (this.sel + 1) % 4 : +e.code.slice(5) - 1; }
    const step = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1], KeyA: [-1, 0], KeyD: [1, 0], KeyW: [0, -1], KeyS: [0, 1] }[e.code];
    if (step) { const f = FEATURES[this.sel]; this.pos[f] = [this.pos[f][0] + step[0] * 0.04, this.pos[f][1] + step[1] * 0.04]; }
    if (e.code === 'Enter' || e.code === 'Space') this.finish();
  }
  draw(t) {
    if (this.playing && t > this.s.info.dur - 0.3) this.finish();
    if (this.playing) {
      const l = this.layout(), c = this.c;
      art.pumpkin(c, l.tx, l.ty, l.tr, { face: false });
      for (const f of FEATURES) drawFeature(c, f, l.tx + this.params.target[f][0] * l.tr, l.ty + this.params.target[f][1] * l.tr, l.tr);
      this.text('Make it look like this', l.tx, l.ty + l.tr + 18, 14, '#cbbfe0');
      art.pumpkin(c, l.mx, l.my, l.R, { face: false });
      if (this.result != null) {
        c.globalAlpha = 0.35;
        for (const f of FEATURES) drawFeature(c, f, l.mx + this.params.target[f][0] * l.R, l.my + this.params.target[f][1] * l.R, l.R, '#fff');
        c.globalAlpha = 1;
      }
      FEATURES.forEach((f, i) => {
        const x = l.mx + this.pos[f][0] * l.R, y = l.my + this.pos[f][1] * l.R;
        drawFeature(c, f, x, y, l.R, (this.drag && this.drag.f === f) || (!coarse && i === this.sel && this.result == null) ? '#5a2a00' : '#2a1500');
      });
      if (this.result == null) this.button(this.doneRect(), 'Done!', { on: true, size: 20 });
      else this.title(`${Math.max(0, 100 - Math.floor(this.result / 2))}% match`, l.mx, l.my + l.R * 1.05 + 22, 30, '#ffe066');
    }
    this.sideBoard('Finished', this.ids.map(id => ({ id, text: (id === this.me ? this.result != null : this.others[id]) ? '✓' : '…' })));
  }
}

// ---------------------------------------------------------------- Hide and Go Boo!

class HideBoo extends Game {
  constructor(s) {
    super(s);
    this.q = null;
    this.mine = null;
    this.seeker = this.params.seeker;
    this.hint = this.me === this.seeker ? 'You’re the seeker' : 'Hide in a coffin!';
  }
  snap(m) {
    if (m.mine != null) this.mine = m.mine;
    if (this.q && m.opened.length > this.q.opened.length) {
      const last = m.opened[m.opened.length - 1];
      this.sound(last[1].length ? 'boo' : 'wrong');
    }
    this.q = { ...m, at: now() };
  }
  coffins() {
    const n = this.params.n, a = this.area(), W = this.W;
    const perRow = this.portrait ? Math.min(3, n) : n;
    const w = Math.min(120, (W - 40) / perRow - 16), h = w * 1.6;
    const top = this.portrait ? this.H * 0.28 : this.H * 0.36;
    return Array.from({ length: n }, (_, i) => {
      const r = Math.floor(i / perRow), k = i % perRow;
      const inRow = Math.min(perRow, n - r * perRow);
      const x0 = (W - inRow * (w + 16)) / 2 + 8;
      return { x: x0 + k * (w + 16), y: top + r * (h + 30), w, h };
    });
  }
  pointer(type, x, y, id, live) {
    if (type !== 'pointerdown' || !live || !this.q) return;
    this.coffins().forEach((r, i) => {
      if (!this.hit(r, x, y)) return;
      if (this.q.phase === 'hide' && this.me !== this.seeker) { this.mine = i; this.send({ t: 'pick', c: i }); this.sound('click'); }
      if (this.q.phase === 'seek' && this.me === this.seeker) { this.send({ t: 'pick', c: i }); this.sound('click'); }
    });
  }
  draw(t) {
    const q = this.q;
    if (!q) return;
    const c = this.c, seeker = this.me === this.seeker;
    const left = Math.max(0, Math.ceil(q.left - (now() - q.at)));
    const sk = this.player(this.seeker);
    let msg;
    if (q.phase === 'hide') msg = seeker ? `Close your eyes… they’re hiding (${left})` : `Pick a coffin to hide in (${left})`;
    else if (q.phase === 'seek') msg = seeker ? `Open a coffin! ${this.params.opens - q.opened.length} left (${left})` : `${sk.name} is choosing… (${left})`;
    else if (q.phase === 'show') msg = q.opened[q.opened.length - 1][1].length ? 'BOO! Found!' : 'Empty!';
    else msg = q.caught.length >= this.params.need ? `${sk.name} wins!` : 'The hiders win!';
    this.title(msg, this.W / 2, 72, this.W < 600 ? 22 : 30, '#ffe066');
    this.text(`Found ${q.caught.length}; the seeker needs ${this.params.need}`, this.W / 2, 104, 15, '#cbbfe0');
    const opened = new Map(q.opened.map(([i, found]) => [i, found]));
    this.coffins().forEach((r, i) => {
      const open = opened.has(i);
      c.save();
      c.translate(r.x + r.w / 2, r.y + r.h / 2);
      c.fillStyle = open ? '#140a08' : '#5b3a24';
      c.beginPath();
      c.moveTo(-r.w * 0.3, -r.h / 2); c.lineTo(r.w * 0.3, -r.h / 2); c.lineTo(r.w / 2, -r.h * 0.2);
      c.lineTo(r.w * 0.32, r.h / 2); c.lineTo(-r.w * 0.32, r.h / 2); c.lineTo(-r.w / 2, -r.h * 0.2); c.closePath();
      c.fill();
      c.strokeStyle = this.mine === i && !seeker ? '#ffe066' : '#2e1c10';
      c.lineWidth = this.mine === i && !seeker ? 4 : 3;
      c.stroke();
      if (!open) { c.strokeStyle = '#2e1c10'; c.lineWidth = 4; c.beginPath(); c.moveTo(0, -r.h * 0.3); c.lineTo(0, r.h * 0.15); c.moveTo(-r.w * 0.15, -r.h * 0.15); c.lineTo(r.w * 0.15, -r.h * 0.15); c.stroke(); }
      c.restore();
      const inside = open ? opened.get(i) : q.hide ? Object.entries(q.hide).filter(([, v]) => v === i).map(([k]) => +k) : [];
      inside.forEach((pid, k) => art.token(c, r.x + r.w / 2 + (k - (inside.length - 1) / 2) * 22, r.y + r.h / 2, 13, this.player(pid).color, { label: this.player(pid).name.slice(0, 1), t }));
      if (open && !inside.length) art.ghost(c, r.x + r.w / 2, r.y + r.h / 2, r.w * 0.2, { t, color: 'rgba(220,214,255,0.5)' });
      this.text(String(i + 1), r.x + r.w / 2, r.y + r.h + 14, 14, '#cbbfe0');
    });
    art.token(c, 40, this.H - 40, 18, sk.color, { label: sk.name.slice(0, 1), t });
    this.text(`Seeker: ${sk.name}`, 66, this.H - 40, 15, '#fff', 'left');
  }
}

// ---------------------------------------------------------------- Skull Bowling

class Bowling extends Arena {
  constructor(s) {
    super(s);
    this.bowler = this.params.bowler;
    this.dashLabel = this.me === this.bowler ? 'THROW' : null;
    this.hint = this.me === this.bowler ? 'Line up, throw, and steer the skull' : 'Dodge the skull!';
    this.q = null;
    this.trail = [];
  }
  snap(m) {
    if (this.q && m.r.some(([id, , a]) => !a && (this.q.r.find(r => r[0] === id) || [])[2])) this.sound('hit');
    if (m.ball && !(this.q && this.q.ball)) this.sound('roll');
    this.prevQ = this.q;
    this.q = { ...m, at: now() };
  }
  lane() {
    const a = { y: 50, h: this.H - 60 };
    const w = Math.min(this.W - 30, a.h * 0.8);
    return { x: (this.W - w) / 2, y: a.y, w, h: a.h };
  }
  at(x, y) { const l = this.lane(); return [l.x + (x / 100) * l.w, l.y + (y / 100) * l.h]; }
  lerp(cur, prev, f) {
    if (!prev) return cur;
    const a = Math.min(1, (now() - this.q.at) / 0.05);
    return prev + (cur - prev) * a;
  }
  drawControls() {
    if (this.me === this.bowler) return super.drawControls();
    if (!coarse || !this.playing) return;
    this.text('Drag left or right to dodge', this.W / 2, this.H - 24, 15, 'rgba(255,255,255,0.6)');
    if (this.stick) {
      this.c.strokeStyle = 'rgba(255,255,255,0.4)';
      this.c.beginPath(); this.c.arc(this.stick.ox, this.stick.oy, 50, 0, Math.PI * 2); this.c.stroke();
    }
  }
  draw(t) {
    this.sendInput();
    const q = this.q;
    const c = this.c, l = this.lane();
    c.fillStyle = '#3a2a1f';
    c.fillRect(l.x, l.y, l.w, l.h);
    c.strokeStyle = '#7a5a2f';
    c.lineWidth = 3;
    c.strokeRect(l.x, l.y, l.w, l.h);
    for (let i = 1; i < 6; i++) { c.strokeStyle = 'rgba(0,0,0,0.25)'; c.beginPath(); c.moveTo(l.x + (l.w * i) / 6, l.y); c.lineTo(l.x + (l.w * i) / 6, l.y + l.h); c.stroke(); }
    if (!q) return;
    const s = l.w / 100;
    q.r.forEach(([id, x, alive], k) => {
      const px = this.prevQ && this.prevQ.r.find(r => r[0] === id);
      const [sx, sy] = this.at(this.lerp(x, px && px[1]), this.params.row);
      const p = this.player(id);
      art.token(c, sx, sy, 4.2 * s, p.color, { label: p.name.slice(0, 1), dim: !alive, t: t + id, ring: id === this.me ? '#ffe066' : '#fff' });
      // names alternate above and below, so neighbours' don't run together
      if (alive) this.text(p.name, sx, sy + (k % 2 ? 4.2 * s + 12 : -4.2 * s - 10), 13, id === this.me ? '#ffe066' : '#fff');
    });
    const [bx, by] = this.at(this.lerp(q.bx, this.prevQ && this.prevQ.bx), this.params.bowl);
    const bp = this.player(this.bowler);
    art.token(c, bx, by + 6 * s, 4.5 * s, bp.color, { label: bp.name.slice(0, 1), t, ring: this.bowler === this.me ? '#ffe066' : '#fff' });
    if (q.ball) {
      const pb = this.prevQ && this.prevQ.ball;
      const [x, y] = this.at(this.lerp(q.ball[0], pb && pb[0]), this.lerp(q.ball[1], pb && pb[1]));
      c.save(); c.translate(x, y); c.rotate(t * 8); art.skull(c, 0, 0, 5 * s, {}); c.restore();
    } else if (q.left > 0) {
      const [ax, ay] = this.at(q.bx, this.params.bowl - 8);
      c.strokeStyle = 'rgba(255,224,102,0.5)'; c.setLineDash([6, 8]); c.lineWidth = 2;
      c.beginPath(); c.moveTo(ax, ay); c.lineTo(ax, l.y + 10); c.stroke(); c.setLineDash([]);
    }
    this.text(`Skulls left: ${q.left}`, l.x + 8, l.y + l.h - 14, 15, '#ffe9b8', 'left');
    this.drawControls();
  }
}

// ---------------------------------------------------------------- Grave Robbers

class GraveRobbers extends Game {
  constructor(s) {
    super(s);
    this.q = null;
    this.mine = {};
    this.hint = 'Same grave as someone else? Nobody gets it.';
  }
  snap(m) {
    if (this.q && this.q.picking && !m.picking) this.sound('boo');
    this.q = { ...m, at: now() };
  }
  graves() {
    const size = Math.min(this.W - 40, this.H - 230);
    const s = size / 3, x0 = (this.W - size) / 2, y0 = 120;
    return Array.from({ length: 9 }, (_, i) => ({ x: x0 + (i % 3) * s, y: y0 + Math.floor(i / 3) * s, w: s, h: s }));
  }
  pointer(type, x, y, id, live) {
    const q = this.q;
    if (type !== 'pointerdown' || !live || !q || !q.picking) return;
    this.graves().forEach((r, i) => {
      if (this.hit(r, x, y)) { this.mine[q.r] = i; this.send({ t: 'pick', r: q.r, g: i }); this.sound('click'); }
    });
  }
  key(e, down, live) {
    const q = this.q;
    if (!down || !live || !q || !q.picking || !/^Digit[1-9]$/.test(e.code)) return;
    const g = +e.code.slice(5) - 1;
    this.mine[q.r] = g;
    this.send({ t: 'pick', r: q.r, g });
  }
  draw(t) {
    const q = this.q;
    if (!q) return;
    const c = this.c;
    const left = Math.max(0, q.left - (now() - q.at));
    this.title(q.picking ? `Night ${q.r + 1} of ${q.n}: pick a grave` : 'Dig!', this.W / 2, 66, this.W < 600 ? 22 : 28, '#ffe066');
    c.fillStyle = q.picking ? '#ffe066' : '#666';
    c.fillRect(this.W / 2 - 150, 92, q.picking ? 300 * (left / 7) : 0, 5);
    this.graves().forEach((r, i) => {
      const v = q.values[i];
      const mine = this.mine[q.r] === i;
      c.fillStyle = mine ? '#3e3260' : '#241b33';
      c.fillRect(r.x + 4, r.y + 4, r.w - 8, r.h - 8);
      art.tombstone(c, r.x + r.w / 2, r.y + r.h * 0.5, r.w * 0.2, { cross: v < 0 });
      this.title(`${v}`, r.x + r.w / 2, r.y + r.h * 0.82, Math.min(26, r.w * 0.2), v < 0 ? '#ff6b6b' : v >= 10 ? '#ffd23f' : '#fff');
      if (q.picks) {
        const who = Object.entries(q.picks).filter(([, g]) => g === i).map(([k]) => +k);
        who.forEach((pid, k) => art.token(c, r.x + 20 + k * 22, r.y + 22, 10, this.player(pid).color, { label: this.player(pid).name.slice(0, 1), t }));
        if (who.length > 1) { c.strokeStyle = '#ff5a5a'; c.lineWidth = 4; c.beginPath(); c.moveTo(r.x + 10, r.y + 10); c.lineTo(r.x + r.w - 10, r.y + r.h - 10); c.stroke(); }
      }
      if (mine) { c.strokeStyle = '#ffe066'; c.lineWidth = 3; c.strokeRect(r.x + 4, r.y + 4, r.w - 8, r.h - 8); }
    });
    const scores = this.ids.map(id => ({ id, v: (q.pts || {})[id] || 0 })).sort((a, b) => b.v - a.v);
    scores.forEach((s, i) => {
      const x = (this.W / scores.length) * (i + 0.5);
      const p = this.player(s.id);
      c.fillStyle = p.color;
      c.beginPath(); c.arc(x - 50, this.H - 30, 8, 0, Math.PI * 2); c.fill();
      this.text(`${p.name} ${s.v}${q.picking && q.in.includes(s.id) ? ' ✓' : ''}`, x - 38, this.H - 30, 15, '#fff', 'left');
    });
  }
}

// ---------------------------------------------------------------- Hot Pumpkin

class HotPumpkin extends Game {
  constructor(s) {
    super(s);
    this.q = null;
    this.hint = 'Pass it on! A/← or D/→';
  }
  snap(m) {
    if (this.q && m.booms.length > this.q.booms.length) this.sound('bomb');
    if (this.q) {
      const had = this.q.b.some(b => b[0] === this.me && b[1] == null);
      const has = m.b.some(b => b[0] === this.me && b[1] == null);
      if (has && !had) this.sound('trap');
    }
    this.q = { ...m, at: now() };
  }
  pass(d) {
    if (!this.q || !this.q.b.some(b => b[0] === this.me && b[1] == null)) return;
    this.send({ t: 'pass', d });
    this.sound('pump');
  }
  key(e, down, live) {
    if (!down || !live) return;
    if (['KeyA', 'ArrowLeft'].includes(e.code)) this.pass(-1);
    if (['KeyD', 'ArrowRight'].includes(e.code)) this.pass(1);
  }
  btns() { return [{ x: 16, y: this.H - 100, w: this.W / 2 - 24, h: 84 }, { x: this.W / 2 + 8, y: this.H - 100, w: this.W / 2 - 24, h: 84 }]; }
  pointer(type, x, y, id, live) {
    if (type !== 'pointerdown' || !live) return;
    const [l, r] = this.btns();
    if (this.hit(l, x, y)) this.pass(-1);
    if (this.hit(r, x, y)) this.pass(1);
  }
  spot(i, n) {
    const R = Math.min(this.W * 0.36, (this.H - 220) * 0.42);
    const a = Math.PI / 2 + (i / n) * Math.PI * 2;
    return [this.W / 2 + Math.cos(a) * R, this.H * 0.45 + Math.sin(a) * R];
  }
  draw(t) {
    const q = this.q;
    if (!q) return;
    const c = this.c, n = q.order.length;
    const where = id => this.spot(q.order.indexOf(id), n);
    q.order.forEach((id, i) => {
      const [x, y] = this.spot(i, n);
      const p = this.player(id);
      const alive = q.alive.includes(id);
      art.token(c, x, y, 26, p.color, { label: p.name.slice(0, 1), dim: !alive, t: t + id, ring: id === this.me ? '#ffe066' : '#fff' });
      this.text(p.name, x, y + 42, 15, id === this.me ? '#ffe066' : alive ? '#fff' : '#777');
    });
    for (const [at, to, fly] of q.b) {
      let [x, y] = where(at);
      if (to != null) {
        const f = 1 - Math.max(0, fly - (now() - q.at)) / 0.35;
        const [x2, y2] = where(to);
        x += (x2 - x) * f;
        y += (y2 - y) * f - Math.sin(f * Math.PI) * 60;
      } else y -= 34;
      art.pumpkin(c, x, y, 16 + Math.sin(t * 20) * 1.5, {});
      c.fillStyle = `rgba(255, ${150 + Math.random() * 100}, 40, 0.9)`;
      c.beginPath(); c.arc(x + 4, y - 20 - Math.random() * 4, 3 + Math.random() * 3, 0, Math.PI * 2); c.fill();
    }
    for (const [pid] of q.booms) {
      const [x, y] = where(pid);
      c.fillStyle = 'rgba(255, 140, 30, 0.4)';
      c.beginPath(); c.arc(x, y, 50, 0, Math.PI * 2); c.fill();
      this.title('BOOM!', x, y, 30, '#ffb347');
    }
    if (this.playing && q.alive.includes(this.me)) {
      const has = q.b.some(b => b[0] === this.me && b[1] == null);
      const [l, r] = this.btns();
      this.button(l, '◀ Pass', { color: has ? '#9a4a10' : '#2c2340', size: 22 });
      this.button(r, 'Pass ▶', { color: has ? '#9a4a10' : '#2c2340', size: 22 });
    }
  }
}

// ---------------------------------------------------------------- Slime Shooters

class SlimeShooters extends Arena {
  constructor(s) {
    super(s);
    this.dashLabel = 'FIRE';
    this.hint = coarse ? 'Drag to roll and aim, tap FIRE' : 'WASD to roll and aim, Space to fire';
    this.shotCount = 0;
  }
  onSnap(m) {
    const n = (m.s || []).length;
    if (n > this.shotCount) this.sound('pump');
    this.shotCount = n;
  }
  drawField() {
    const c = this.c, f = this.field();
    c.fillStyle = '#1d2a1f';
    c.fillRect(f.x, f.y, 100 * f.s, 100 * f.s);
    c.strokeStyle = '#7cff6b';
    c.lineWidth = 3;
    c.strokeRect(f.x, f.y, 100 * f.s, 100 * f.s);
    for (const [x, y, owner] of (this.cur && this.cur.m.s) || []) {
      const [px, py] = this.at(x, y);
      c.fillStyle = '#7cff6b';
      c.beginPath(); c.arc(px, py, 1.6 * f.s, 0, Math.PI * 2); c.fill();
      c.fillStyle = this.player(owner).color;
      c.beginPath(); c.arc(px, py, 0.8 * f.s, 0, Math.PI * 2); c.fill();
    }
  }
  drawDisc(d, t) {
    const a = this.cur && this.cur.m.f ? this.cur.m.f[d.id] : 0;
    const [x, y] = this.at(d.x, d.y);
    const r = 4.2 * this.field().s;
    const c = this.c;
    c.strokeStyle = '#2b4a2b';
    c.lineWidth = r * 0.55;
    c.lineCap = 'round';
    c.beginPath(); c.moveTo(x, y); c.lineTo(x + Math.cos(a) * r * 1.7, y + Math.sin(a) * r * 1.7); c.stroke();
    super.drawDisc(d, t);
    this.text('♥'.repeat(Math.max(0, d.lives)), x, y + r + 12, 13, '#ff6b6b');
  }
}

// ---------------------------------------------------------------- Skull Pong

const SIDE_ANGLE = { bottom: 0, top: Math.PI, left: -Math.PI / 2, right: Math.PI / 2 };

class SkullPong extends Arena {
  constructor(s) {
    super(s);
    this.side = this.params.side || {};
    this.th = SIDE_ANGLE[this.side[this.me]] || 0;
    this.q = null;
    this.hint = 'Your wall is at the bottom: guard it';
    this.dashLabel = null;
  }
  snap(m) {
    if (this.q) {
      for (const id of this.ids) if ((this.q.lives[id] || 0) > (m.lives[id] || 0)) this.sound(id === this.me ? 'lose' : 'hit');
    }
    this.prevQ = this.q;
    this.q = { ...m, at: now() };
  }
  input() {
    const [x, y] = super.input();
    // the screen's left and right, turned back into the field's directions
    const c = Math.cos(-this.th), s = Math.sin(-this.th);
    return [Math.round((x * c - y * s) * 100) / 100, Math.round((x * s + y * c) * 100) / 100];
  }
  toScreen(x, y) {
    const f = this.field();
    const dx = x - 50, dy = y - 50;
    const c = Math.cos(this.th), s = Math.sin(this.th);
    return [f.x + (50 + dx * c - dy * s) * f.s, f.y + (50 + dx * s + dy * c) * f.s];
  }
  lerp(cur, prev) {
    if (prev == null) return cur;
    return prev + (cur - prev) * Math.min(1, (now() - this.q.at) / 0.05);
  }
  drawControls() {
    if (!coarse || !this.playing || !this.stick) return;
    const c = this.c;
    c.strokeStyle = 'rgba(255,255,255,0.4)';
    c.beginPath(); c.arc(this.stick.ox, this.stick.oy, 50, 0, Math.PI * 2); c.stroke();
  }
  draw(t) {
    this.sendInput();
    const q = this.q;
    const c = this.c, f = this.field();
    c.fillStyle = '#1f1530';
    c.fillRect(f.x, f.y, 100 * f.s, 100 * f.s);
    if (!q) return;
    const walls = { bottom: [[0, 100], [100, 100]], top: [[0, 0], [100, 0]], left: [[0, 0], [0, 100]], right: [[100, 0], [100, 100]] };
    for (const [side, [a, b]] of Object.entries(walls)) {
      const owner = Object.keys(this.side).find(id => this.side[id] === side && q.alive.includes(+id));
      const [x1, y1] = this.toScreen(...a), [x2, y2] = this.toScreen(...b);
      c.strokeStyle = owner ? this.player(+owner).color : '#5b5470';
      c.globalAlpha = owner ? 0.5 : 1;
      c.lineWidth = owner ? 4 : 10;
      c.beginPath(); c.moveTo(x1, y1); c.lineTo(x2, y2); c.stroke();
      c.globalAlpha = 1;
    }
    for (const id of this.ids) {
      if (!q.alive.includes(id)) continue;
      const side = this.side[id];
      const p = this.lerp(q.pos[id], this.prevQ && this.prevQ.pos[id]);
      const horiz = side === 'bottom' || side === 'top';
      const fixed = { bottom: 98.5, top: 1.5, left: 1.5, right: 98.5 }[side];
      const a = horiz ? [p - 11, fixed] : [fixed, p - 11], b = horiz ? [p + 11, fixed] : [fixed, p + 11];
      const [x1, y1] = this.toScreen(...a), [x2, y2] = this.toScreen(...b);
      c.strokeStyle = this.player(id).color;
      c.lineWidth = 2.6 * f.s;
      c.lineCap = 'round';
      c.beginPath(); c.moveTo(x1, y1); c.lineTo(x2, y2); c.stroke();
      const [lx, ly] = this.toScreen(horiz ? 50 : fixed === 1.5 ? 8 : 92, horiz ? (fixed === 1.5 ? 8 : 92) : 50);
      c.globalAlpha = 0.8;
      this.text(`${this.player(id).name} ${'♥'.repeat(q.lives[id])}`, lx, ly, 14, id === this.me ? '#ffe066' : '#fff');
      c.globalAlpha = 1;
    }
    q.balls.forEach(([x, y], i) => {
      const pb = this.prevQ && this.prevQ.balls[i];
      const [sx, sy] = this.toScreen(this.lerp(x, pb && pb[0]), this.lerp(y, pb && pb[1]));
      art.skull(c, sx, sy, 2.8 * f.s, {});
    });
    this.drawControls();
  }
}

// ---------------------------------------------------------------- Monster Mash

const LANE_KEYS = [['KeyD', 'ArrowLeft'], ['KeyF', 'ArrowDown'], ['KeyJ', 'ArrowUp'], ['KeyK', 'ArrowRight']];
const LANE_COLORS = ['#ff8a2a', '#7cff6b', '#b066ff', '#5fb0ff'];

class MonsterMash extends Game {
  constructor(s) {
    super(s);
    this.notes = this.params.notes.map(([t, lane]) => ({ t, lane, hit: null }));
    this.score = 0;
    this.beat = 60 / this.params.bpm;
    this.lastBeat = -1;
    this.flash = [0, 0, 0, 0];
    this.judge = null;
    this.others = {};
    this.progAt = 0;
    this.hint = coarse ? 'Tap the pads as the notes hit the line' : 'D F J K (or arrows) as the notes hit the line';
  }
  snap(m) { this.others = m.prog || {}; }
  lanes() {
    const a = this.area();
    const w = Math.min(a.w - 20, 420);
    const x0 = a.x + (a.w - w) / 2;
    return { x0, w: w / 4, top: a.y + 10, line: a.y + a.h - 90, bottom: a.y + a.h - 10 };
  }
  hitLane(lane) {
    if (this.t < 0) return;
    this.flash[lane] = this.t;
    let best = null;
    for (const n of this.notes) {
      if (n.lane !== lane || n.hit) continue;
      const d = Math.abs(n.t - this.t);
      if (d < 0.16 && (!best || d < Math.abs(best.t - this.t))) best = n;
    }
    if (!best) return;
    const d = Math.abs(best.t - this.t);
    best.hit = d < 0.065 ? 2 : 1;
    this.score += best.hit;
    this.judge = { text: best.hit === 2 ? 'Perfect!' : 'Good', t: this.t, lane };
    sfx.play(`note${lane}`);
  }
  key(e, down, live) {
    if (!down || !live) return;
    LANE_KEYS.forEach((ks, i) => { if (ks.includes(e.code)) this.hitLane(i); });
  }
  pointer(type, x, y, id, live) {
    if (type !== 'pointerdown' || !live) return;
    const l = this.lanes();
    if (y < l.line - 60) return;
    const i = Math.floor((x - l.x0) / l.w);
    if (i >= 0 && i < 4) this.hitLane(i);
  }
  draw(t) {
    const P = this.params;
    if (t >= 0 && t < P.lead + P.len + 0.5) {
      const b = Math.floor(t / this.beat);
      if (b > this.lastBeat) { this.lastBeat = b; sfx.play(b % 2 ? 'hat' : b % 4 === 0 ? 'kick' : 'snare'); }
    }
    if (this.playing && t > P.lead + P.len + 0.6) this.done([this.score]);
    if (this.playing && t - this.progAt > 1.5) { this.progAt = t; this.prog([this.score]); }
    const c = this.c;
    if (this.playing) {
      const l = this.lanes();
      const speed = (l.line - l.top) / 1.6;
      for (let i = 0; i < 4; i++) {
        c.fillStyle = i % 2 ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.07)';
        c.fillRect(l.x0 + i * l.w, l.top, l.w, l.bottom - l.top);
        const lit = t - this.flash[i] < 0.12;
        c.fillStyle = lit ? LANE_COLORS[i] : 'rgba(255,255,255,0.12)';
        c.beginPath(); c.roundRect(l.x0 + i * l.w + 6, l.line + 14, l.w - 12, l.bottom - l.line - 20, 10); c.fill();
        this.text(coarse ? '' : LANE_KEYS[i][0].slice(3), l.x0 + i * l.w + l.w / 2, l.line + (l.bottom - l.line) / 2 + 6, 18, lit ? '#1a1020' : '#cbbfe0');
      }
      c.strokeStyle = '#ffe066';
      c.lineWidth = 3;
      c.beginPath(); c.moveTo(l.x0, l.line); c.lineTo(l.x0 + 4 * l.w, l.line); c.stroke();
      for (const n of this.notes) {
        if (n.hit) continue;
        const y = l.line - (n.t - t) * speed;
        if (y < l.top - 20 || y > l.line + 30) continue;
        const x = l.x0 + n.lane * l.w + l.w / 2;
        if (n.lane === 0) art.pumpkin(c, x, y, l.w * 0.22, {});
        else if (n.lane === 1) art.ghost(c, x, y, l.w * 0.22, { t, color: '#c8ffc0' });
        else if (n.lane === 2) art.bat(c, x, y, l.w * 0.16, { t, color: '#b066ff' });
        else art.skull(c, x, y, l.w * 0.2, { color: '#cfe6ff' });
      }
      if (this.judge && t - this.judge.t < 0.4) this.title(this.judge.text, l.x0 + this.judge.lane * l.w + l.w / 2, l.line - 30, 20, this.judge.text === 'Good' ? '#cbbfe0' : '#7dff9b');
      this.text(`${this.score}`, l.x0 + 2 * l.w, l.top + 20, 26, '#ffe066');
    }
    this.sideBoard('Points', this.ids.map(id => ({ id, text: String(id === this.me ? this.score : (this.others[id] || [0])[0]) })));
  }
}

export const MORE = {
  hexheat: HexHeat, squirm: Squirm, says: SkeletonSays, lift: PumpkinLift, hide: HideBoo, bowl: Bowling,
  graves: GraveRobbers, potato: HotPumpkin, shoot: SlimeShooters, pong: SkullPong, band: MonsterMash,
};
