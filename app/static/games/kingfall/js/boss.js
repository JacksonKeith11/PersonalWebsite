// The boss in the browser: one or more bodies, its adds, and every move's danger. Drawn at the server's
// present time: during a move a body's position, aim and pose come from the move's timeline (the same
// for every browser); between moves it's extrapolated from the snapshots. Draws ground marks before
// area hits, slashes, thrusts, rings, projectiles and lingering pools, and checks every hit against
// this browser's heroes.
import { Rig, sample, runCycle, rigDefaults, atlas } from './rig.js?v=13';
import { LiveMove, placeHit, touches } from './moves.js?v=13';
import { crescent, lance, burst, shockwave, orb, pool } from './fx.js?v=13';

const FIRE = 0xff7a1a, DANGER = 0xd0302a, STEEL = 0xe8ecf2;
const POOL = { poison: 0x6a8a2a, fire: 0xff6a1a, ice: 0x7fe3ff, void: 0x8a3ab0, blood: 0x8a1e2a };
const INTERP = 0.1;

const bodiesOf = B => B.bodies || [B];

// art name -> rig name (bosses whose phases change their look name both)
function rigFor(def, art) {
  if (art === def.art) return def.rig;
  return (def.phase_rig || {})[art] || def.rig;
}

function framesFor(rigName, art) {
  const f = {};
  for (const k of Object.keys(atlas().rigs[rigName].parts)) f[k] = `${art}.${k}`;
  return f;
}

class BodyView {
  constructor(scene, def, e, init) {
    this.scene = scene; this.def = def; this.e = e;
    this.art = init.art || def.art;
    this.makeRig();
    this.shadow = scene.add.ellipse(0, 0, def.radius * 2.8, def.radius * 0.8, 0x000000, 0.4).setDepth(1);
    this.coreG = scene.add.graphics().setDepth(4800);
    this.x = init.x; this.y = init.y; this.sx = this.x; this.sy = this.y;
    this.snap = null; this.face = Math.PI / 2;
    this.hp = init.mhp; this.mhp = init.mhp; this.poise = init.mpoise; this.mpoise = init.mpoise;
    this.phase = 1; this.state = 'intro'; this.cores = (def.cores || []).map(c => c.hp);
    this.walk = 0; this.flash = 0; this.staggerT = 0; this.z = 0;
    this.r = def.radius;
    this.trail = [];  // the wyrm's path: it starts coiled out behind it
    for (let i = 0; i < 160; i++) this.trail.push([this.x - Math.sin(i / 14) * 24, this.y - i * 1.2]);
  }

  makeRig() {
    if (this.rig) this.rig.destroy();
    this.rigName = rigFor(this.def, this.art);
    this.def_ = rigDefaults(this.rigName);
    if (this.def.render === 'wyrm') {
      this.rig = new Rig(this.scene, this.rigName, framesFor(this.rigName, this.art));
      this.segs = [];
      for (let i = 0; i < 11; i++) {
        const name = i === 10 ? `${this.art}.tail` : `${this.art}.seg`;
        const [, , w, h, px, py] = atlas().frames[name];
        this.segs.push(this.scene.add.image(0, 0, 'atlas', name).setOrigin(px / w, py / h));
      }
      this.mound = this.scene.add.ellipse(0, 0, 40, 14, 0x3a2e22, 0.9).setDepth(2).setVisible(false);
    } else {
      this.rig = new Rig(this.scene, this.rigName, framesFor(this.rigName, this.art));
    }
  }

  get alive() { return this.state !== 'dead' && this.hp > 0; }

  // a hit can't land: leaping, flying high, burrowed, or between phases
  untouchable(now, mv) {
    if (!mv || now < mv.start) return false;
    const t = now - mv.start, d = mv.data, w = k => d[k] && t >= d[k][0] && t <= d[k][1];
    return !!(d.invuln || w('air') || w('under'));
  }

  corePos(i) {
    const c = this.def.cores[i], side = Math.cos(this.face) < -0.05 ? -1 : 1;
    return [this.x + c.dx * side, this.y + c.dy];
  }
}

export class Boss {
  constructor(scene, data, fight) {
    this.scene = scene;
    this.B = data.bosses[fight.boss];
    this.defs = bodiesOf(this.B);
    this.bodies = this.defs.map((d, e) => new BodyView(scene, d, e, fight.bodies[e]));
    this.marks = scene.add.graphics().setDepth(2);     // on the floor, under everyone
    this.fx = scene.add.graphics().setDepth(5000);     // markers and glints, over everyone
    this.glow = scene.add.graphics().setDepth(4990).setBlendMode(Phaser.BlendModes.ADD);  // swings, projectiles, shockwaves
    this.moves = [];          // live and recent moves (projectiles and pools outlive their move)
    this.adds = {};           // id -> {view, buf, kind}
  }

  get alive() { return this.bodies.some(b => b.alive); }
  // the nearest live body to a point (aim assist, lock-on)
  nearest(x, y) {
    let best = null, d = Infinity;
    for (const b of this.bodies) if (b.alive) { const q = Math.hypot(b.x - x, b.y - y); if (q < d) { d = q; best = b; } }
    return best || this.bodies[0];
  }
  // compatibility: the first body's position
  get x() { return this.nearest(this.scene.camX, this.scene.camY).x; }
  get y() { return this.nearest(this.scene.camX, this.scene.camY).y; }

  onSnap(st, rows, adds) {
    rows.forEach((row, e) => {
      const b = this.bodies[e];
      if (!b) return;
      const [x, y, vx, vy, face, hp, mhp, po, mpo, ph, state, cores, meters, live] = row;
      if (state === 'stagger' && b.state !== 'stagger') b.staggerT = 0;
      b.snap = { st, x, y, vx, vy };
      Object.assign(b, { face, hp, mhp, poise: po, mpoise: mpo, phase: ph, state, cores, meters: meters || [], live: live || [] });
    });
    const seen = new Set();
    for (const [id, kind, x, y, hp, mhp] of adds || []) {
      seen.add(id);
      let a = this.adds[id];
      if (!a) { a = this.adds[id] = this.makeAdd(id, kind, x, y); a.seen = st; }
      a.buf.push([st, x, y]); if (a.buf.length > 20) a.buf.shift();
      a.hp = hp; a.mhp = mhp;
    }
    for (const id of Object.keys(this.adds)) if (!seen.has(+id)) this.dropAdd(+id);
  }

  makeAdd(id, kind, x, y) {
    const A = this.B.adds[kind], sc = this.scene;
    const name = A.art;
    const [, , w, h, px, py] = atlas().frames[name];
    const im = sc.add.image(x, y, 'atlas', name).setOrigin(px / w, py / h);
    if (A.tint) im.setTint(Phaser.Display.Color.HexStringToColor(A.tint).color);
    if (A.alpha) im.setAlpha(A.alpha);
    const shadow = sc.add.ellipse(x, y, A.radius * 2.2, A.radius * 0.7, 0x000000, 0.35).setDepth(1);
    return { id, kind, A, im, shadow, buf: [], x, y, r: A.radius, hp: 1, mhp: 1, flash: 0, bob: Math.random() * 6 };
  }

  dropAdd(id) {
    const a = this.adds[id];
    if (!a) return;
    this.scene.tweens.add({ targets: a.im, alpha: 0, scaleY: 0.2, duration: 220, onComplete: () => a.im.destroy() });
    a.shadow.destroy();
    delete this.adds[id];
  }

  body(m) { return this.bodies[m.e || 0]; }

  onMove(m) {
    const b = this.body(m);
    if (!b) return;
    const def = b.def;
    const data = m.id.startsWith('phase') ? (def.phase_moves || {})[m.id.slice(5)] : def.moves[m.id];
    if (!data) return;
    if (m.art && m.art !== b.art) { b.art = m.art; b.makeRig(); }
    const mv = new LiveMove(m, data);
    mv.e = m.e || 0;
    mv.tg = m.tg;
    // the move's first strike (for the glint and the target marker)
    const strikes = data.hits.filter(h => h.k !== 'spawn' && h.k !== 'zone');
    mv.first = strikes.length ? Math.min(...strikes.map(h => h.t0)) : null;
    mv.unblock = data.hits.some(h => h.unblock);
    mv.last = mv.start + Math.max(data.dur, ...data.hits.map(h => h.t1));
    this.moves.push(mv);
    if (this.moves.length > 16) this.moves.shift();
  }
  onAim(m) { const mv = this.moves.find(v => v.seq === m.seq); if (mv) mv.reaim(m.lt, m.a, m.d); }
  onCancel(m) {
    const mv = this.moves.find(v => v.seq === m.seq);
    if (mv) { mv.cancelAt = m.at; mv.last = Math.min(mv.last, m.at); }
  }

  current(b, now) {
    for (let i = this.moves.length - 1; i >= 0; i--) {
      const mv = this.moves[i];
      if (mv.e === b.e && now < mv.end() + 0.02) return mv;
    }
    return null;
  }

  update(now, dt) {
    for (const b of this.bodies) this.updateBody(b, now, dt);
    this.updateAdds(now, dt);
    this.drawDanger(now);
  }

  updateBody(b, now, dt) {
    b.flash = Math.max(0, b.flash - dt);
    const mv = this.current(b, now);
    b.mv = mv;
    let pose, moving = false;
    if (mv) {
      const t = now - mv.start;
      const [x, y] = mv.pos(Math.max(0, t));
      b.x = x; b.y = y; b.sx = x; b.sy = y;
      b.face = mv.aim(Math.max(0, t));
      pose = sample(mv.data.anim, Math.max(0, Math.min(t, mv.cancelAt - mv.start)), b.def_);
      if (pose.run) { b.walk += dt * 14; pose = { ...runCycle(b.walk, 0.8), ...pose, ...legsOnly(runCycle(b.walk, 0.8)) }; }
    } else if (b.snap) {
      const s = b.snap, dts = Math.min(0.25, now - s.st);
      const tx = s.x + s.vx * dts, ty = s.y + s.vy * dts;
      b.sx += (tx - b.sx) * Math.min(1, dt * 12); b.sy += (ty - b.sy) * Math.min(1, dt * 12);
      b.x = b.sx; b.y = b.sy;
      moving = Math.hypot(s.vx, s.vy) > 5;
      if (moving) b.face = Math.atan2(s.vy, s.vx);
    }
    if (b.state === 'stagger' && !mv) {
      b.staggerT += dt;
      pose = { ...(b.def.stagger_pose || { torso: 22, head: 18, arm_f: 30, weapon: 120, arm_b: 30, shield: -30, dy: 4 }), dy: 4 + Math.sin(b.staggerT * 3) };
    } else if (b.state === 'dead') {
      pose = b.def.dead_pose || { torso: 30, head: 30, arm_f: 40, weapon: 150, arm_b: 40, dy: 6 };
    } else if (!pose) {
      if (moving) { b.walk += dt * 8; pose = runCycle(b.walk, 0.7); }
      else pose = { torso: Math.sin(now * 1.8) * 1.5, head: Math.sin(now * 1.8 + 0.6) * 1.5 };
      if (b.def.idle_pose) pose = { ...b.def.idle_pose, ...pose };
    }
    // height: leaps and flight lift the whole figure off its shadow
    const hover = b.def.hover ? b.def.hover + Math.sin(now * 2.4) * 2 : 0;
    b.z = (pose.z || 0) + hover;
    const left = Math.cos(b.face) < -0.05;
    const under = b.untouchable(now, mv) && mv && mv.data.under && now - mv.start >= mv.data.under[0] && now - mv.start <= mv.data.under[1];
    if (b.def.render === 'wyrm') this.drawWyrm(b, pose, left, under, dt);
    else {
      b.rig.pose(pose, left);
      b.rig.c.setPosition(Math.round(b.x), Math.round(b.y - b.z)).setDepth(b.y);
      b.rig.c.setVisible(!under);
    }
    const sh = Math.max(0.4, 1 - b.z / 120);
    b.shadow.setPosition(b.x, b.y + 1).setScale(sh).setVisible(!under);
    // a flash of white when struck; a flash of warning red in the instant before its strike lands
    const lead = mv && mv.first != null ? mv.first - (now - mv.start) : 9;
    b.rig.setTint(b.flash > 0 ? 0xffffff : lead > 0.02 && lead < 0.09 && now < mv.cancelAt ? (mv.unblock ? 0xff5030 : 0xffd0c0) : null);
    // staggered: stars wheel over its head and a ring counts the stagger down
    if (b.state === 'stagger' && !mv) {
      const f = this.fx, left = Math.max(0, 1 - b.staggerT / (b.staggerDur || 5)), hy = b.y - b.z - Math.max(46, b.r * 2.6);
      f.lineStyle(3, 0x120e16, 0.7); f.beginPath(); f.arc(b.x, hy, 9, 0, Math.PI * 2); f.strokePath();
      f.lineStyle(2, 0xffd23f, 1); f.beginPath(); f.arc(b.x, hy, 9, -Math.PI / 2, -Math.PI / 2 + left * Math.PI * 2); f.strokePath();
      for (let k = 0; k < 3; k++) {
        const a = now * 4 + k * 2.094, sx = b.x + Math.cos(a) * 16, sy = hy + 14 + Math.sin(a) * 5;
        f.fillStyle(0xffe680, 0.9); f.fillTriangle(sx - 3, sy, sx + 3, sy, sx, sy - 4); f.fillTriangle(sx - 3, sy - 1.5, sx + 3, sy - 1.5, sx, sy + 2.5);
      }
    }
    if (b.state === 'dead') { b.rig.c.alpha = Math.max(0, b.rig.c.alpha - dt * 0.35); b.shadow.alpha = b.rig.c.alpha * 0.4; if (b.segs) b.segs.forEach(s => s.alpha = b.rig.c.alpha); }
    // weak points glow until broken
    b.coreG.clear();
    (b.def.cores || []).forEach((c, i) => {
      if (!(b.cores[i] > 0) || b.state === 'dead') return;
      const [cx, cy] = b.corePos(i), p = 0.6 + Math.sin(now * 6 + i) * 0.25;
      b.coreG.lineStyle(2, 0xa0e0ff, p).strokeCircle(cx, cy - (c.h || 0), c.r * 0.8);
      b.coreG.lineStyle(1, 0xffffff, p * 0.6).strokeCircle(cx, cy, c.r);
    });
  }

  // the Gravewyrm: its head on the rig, its vertebrae laid along the path the head has taken
  drawWyrm(b, pose, left, under, dt) {
    const tr = b.trail;
    if (!tr.length || Math.hypot(tr[0][0] - b.x, tr[0][1] - b.y) > 3) { tr.unshift([b.x, b.y]); if (tr.length > 160) tr.pop(); }
    b.rig.pose(pose, left);
    b.rig.c.setPosition(Math.round(b.x), Math.round(b.y - b.z)).setDepth(b.y + 1).setVisible(!under);
    b.mound.setPosition(b.x, b.y).setVisible(!!under);
    let dist = 0, j = 0;
    b.segs.forEach((s, i) => {
      const want = 16 + i * 13;
      while (j < tr.length - 1 && dist + Math.hypot(tr[j + 1][0] - tr[j][0], tr[j + 1][1] - tr[j][1]) < want) {
        dist += Math.hypot(tr[j + 1][0] - tr[j][0], tr[j + 1][1] - tr[j][1]); j++;
      }
      const p = tr[Math.min(j, tr.length - 1)] || [b.x, b.y];
      const q = tr[Math.min(j + 1, tr.length - 1)] || p;
      s.setPosition(Math.round(p[0]), Math.round(p[1] - 14 + Math.sin(i * 0.9 + b.walk) * 2)).setDepth(p[1]);
      s.setFlipX(q[0] > p[0]);
      s.setVisible(!under || i > 7);
      s.setTint(b.flash > 0 ? 0xffffff : 0xffffff);
      s.p = p;
    });
    b.walk += dt * 4;
  }

  // segment positions, for hits on the wyrm's body
  segments(b) { return b.segs ? b.segs.filter(s => s.visible && s.p).map(s => s.p) : []; }

  updateAdds(now, dt) {
    const rt = now - INTERP;
    for (const a of Object.values(this.adds)) {
      a.flash = Math.max(0, a.flash - dt);
      const buf = a.buf;
      if (!buf.length) continue;
      let i = buf.findIndex(r => r[0] > rt), x, y;
      if (i <= 0) [, x, y] = i === 0 ? buf[0] : buf[buf.length - 1];
      else {
        const p = buf[i - 1], q = buf[i], u = (rt - p[0]) / Math.max(1e-6, q[0] - p[0]);
        x = p[1] + (q[1] - p[1]) * u; y = p[2] + (q[2] - p[2]) * u;
        if (Math.abs(q[1] - p[1]) > 0.3) a.im.setFlipX(q[1] < p[1]);
      }
      a.x = x; a.y = y;
      const bob = a.A.float ? Math.sin(now * 3 + a.bob) * 3 + a.A.float : Math.abs(Math.sin(now * 8 + a.bob)) * 1.5;
      a.im.setPosition(Math.round(x), Math.round(y - bob)).setDepth(y);
      a.shadow.setPosition(x, y);
      if (a.flash > 0) a.im.setTintFill(0xffffff); else if (a.A.tint) a.im.setTint(Phaser.Display.Color.HexStringToColor(a.A.tint).color); else a.im.clearTint();
    }
  }

  // ground marks, swing arcs, rings, projectiles and pools
  drawDanger(now) {
    const g = this.marks, f = this.fx, gl = this.glow;
    g.clear(); f.clear(); gl.clear();
    for (const mv of this.moves) {
      const t = now - mv.start;
      if (now > mv.last + 0.2) continue;
      this.drawTell(mv, t, now);
      mv.data.hits.forEach(h => {
        if (h.mark == null && t < h.t0) { this.drawWindup(mv, h, t); return; }
        const fire = !!h.fire, col = fire ? FIRE : h.col ? Phaser.Display.Color.HexStringToColor(h.col).color : STEEL;
        // a swing's trail lingers a moment after it can no longer hurt
        const AFTER = 0.2, melee = h.k === 'arc' || h.k === 'rect' || h.k === 'circle';
        if (melee && t > h.t1 && t < h.t1 + AFTER && mv.start + h.t1 <= mv.cancelAt) {
          const s = placeHit(mv, h, h.t1);
          if (s) this.drawStrike(gl, s, 1 + (t - h.t1) / AFTER, col);
          return;
        }
        const s = placeHit(mv, h, t, h.mark ?? 0);
        if (!s) return;
        if (!s.live) { // the warning before it lands: it fills from the middle as the moment comes
          const u = 1 - (h.t0 - t) / Math.max(0.05, h.mark);
          g.fillStyle(DANGER, 0.1 + 0.12 * u); shape(g, s, true);
          if (s.k === 'circle') { g.fillStyle(DANGER, 0.22); g.fillCircle(s.cx, s.cy, s.r * Math.max(0, u)); }
          g.lineStyle(1.5, DANGER, 0.55 + 0.4 * u); shape(g, s, false);
          return;
        }
        const life = (t - h.t0) / Math.max(0.05, h.t1 - h.t0);
        if (s.k === 'zone') {
          pool(g, gl, s, POOL[s.pool] || 0x6a8a2a, Math.min(1, (h.t1 - t) * 2, (t - h.t0) * 4), now);
        } else if (s.k === 'proj') {
          orb(gl, g, s.cx, s.cy, s.a, s.r, col, { lift: 8, core: fire ? 0xffe9a0 : 0xffffff });
        } else if (s.k === 'ring') {
          shockwave(gl, s, life, col);
        } else this.drawStrike(gl, s, life, col);
      });
    }
  }

  // a boss's swing, thrust or slam: p 0..1 while it can hurt, on to 2 as it fades
  drawStrike(gl, s, p, col) {
    if (s.k === 'arc') crescent(gl, s, p, col, { lift: 14, thick: 0.34 });
    else if (s.k === 'rect') lance(gl, s, p, col, { lift: 14 });
    else if (s.k === 'circle') burst(gl, s, p, col);
  }

  // Before an unmarked hit lands, its shape is outlined on the floor: from the moment its aim is final
  // (its last lock has arrived) or 0.6 s before, whichever is later, brightening as it comes. Thrusts
  // and swings get a thin outline, projectiles a dashed line along their path, rings a faint circle.
  drawWindup(mv, h, t) {
    if (h.k === 'spawn' || h.k === 'zone' || mv.start + h.t0 > mv.cancelAt) return;
    const locks = (mv.data.locks || [0]).filter(l => l <= h.t0);
    const L = locks.length ? Math.max(...locks) : 0;
    if (L > 0 && !mv.aims.some(([at]) => Math.abs(at - L) < 1e-6)) return;  // its aim isn't known yet
    const lead = Math.min(0.6, h.t0 - L);
    if (t < h.t0 - lead || lead <= 0.02) return;
    const s = placeHit(mv, h, h.t0);
    if (!s) return;
    const u = 1 - (h.t0 - t) / lead, g = this.marks;
    const col = h.unblock ? 0xff3a20 : DANGER;
    if (s.k === 'proj') {
      const L2 = Math.min(140, h.v * 0.5), c = Math.cos(s.a), n = Math.sin(s.a);
      g.lineStyle(1, col, 0.25 + 0.5 * u);
      for (let d = 0; d < L2; d += 10) g.lineBetween(s.cx + c * d, s.cy + n * d, s.cx + c * (d + 5), s.cy + n * (d + 5));
      return;
    }
    if (s.k === 'ring') { g.lineStyle(1, col, 0.2 + 0.4 * u); g.strokeCircle(s.cx, s.cy, h.r0 + 10); return; }
    g.fillStyle(col, 0.1 + 0.2 * u * u); shape(g, s, true);
    g.lineStyle(u > 0.7 ? 2 : 1, col, 0.45 + 0.5 * u); shape(g, s, false);
  }

  // the tell: a glint on the boss just before its first strike (red if it can't be blocked), and a
  // marker over the hero the move is aimed at
  drawTell(mv, t, now) {
    if (mv.first == null || t > mv.first || now > mv.cancelAt) return;
    const b = this.bodies[mv.e], f = this.fx;
    if (!b || !b.alive) return;
    const hero = mv.tg != null && this.scene.byId && this.scene.byId[mv.tg];
    if (hero && t > -0.1 && !hero.down) {
      const hx = hero.x, hy = hero.y - 56 + Math.sin(now * 10) * 1.5;
      f.fillStyle(0xe03a2a, 0.95); f.fillTriangle(hx - 6, hy - 7, hx + 6, hy - 7, hx, hy + 2);
      f.lineStyle(1, 0x000000, 0.7); f.strokeTriangle(hx - 6, hy - 7, hx + 6, hy - 7, hx, hy + 2);
      this.marks.lineStyle(1, 0xe03a2a, 0.8); this.marks.strokeEllipse(hero.x, hero.y, 30, 12);
    }
    const lead = mv.first - t;
    if (lead > 0.32 || lead < 0) return;
    const u = 1 - lead / 0.32, k = Math.sin(u * Math.PI);
    const x = b.x + Math.cos(b.face) * (b.r * 0.9), y = b.y - b.z - Math.max(30, b.r * 1.6);
    const col = mv.unblock ? 0xff4020 : 0xfff6d0, L = 4 + 9 * k;
    f.fillStyle(col, 0.35 * k); f.fillCircle(x, y, 3 + 5 * k);
    f.lineStyle(2, col, 0.95 * k);
    f.lineBetween(x - L, y, x + L, y); f.lineBetween(x, y - L, x, y + L);
    f.lineStyle(1, col, 0.7 * k);
    f.lineBetween(x - L * 0.45, y - L * 0.45, x + L * 0.45, y + L * 0.45); f.lineBetween(x - L * 0.45, y + L * 0.45, x + L * 0.45, y - L * 0.45);
  }

  // test every live hit (and every add) against a hero; calls back once per hit id that touches it
  checkHero(now, hero, cb) {
    for (const mv of this.moves) {
      const t = now - mv.start;
      if (t < 0 || now > mv.last + 0.2) continue;
      mv.data.hits.forEach((h, i) => {
        if (h.k === 'spawn') return;
        const id = `${mv.seq}:${i}` + (h.tick ? ':' + Math.floor((t - h.t0) / h.tick) : '');
        if (hero.taken.has(id)) return;
        const s = placeHit(mv, h, t);
        if (!s || !s.live) return;
        if (touches(s, hero.x, hero.y, hero.HERO.radius)) {
          const [bx, by] = mv.pos(Math.min(t, h.t0));
          const far = s.k === 'proj' || s.k === 'ring' || s.k === 'zone';
          if (cb(h, id, far ? s.cx : bx, far ? s.cy : by)) hero.taken.add(id);
        }
      });
    }
    for (const a of Object.values(this.adds)) {
      if (now - a.seen < 1.0 || Math.hypot(a.x - hero.x, a.y - hero.y) > a.r + hero.HERO.radius) continue;  // a moment's grace when it appears
      const id = `a${a.id}:${Math.floor(now / 2)}`;  // an add bites at most every 2 s
      if (hero.taken.has(id)) continue;
      if (cb({ dmg: a.A.dmg, kb: 30 }, id, a.x, a.y)) hero.taken.add(id);
    }
  }

  // what a hero's swing can strike: bodies (or their weak points), the wyrm's vertebrae, adds
  targets(now) {
    const out = [];
    for (const b of this.bodies) {
      if (!b.alive || b.state === 'intro' || b.untouchable(now, b.mv)) continue;
      (b.def.cores || []).forEach((c, i) => { if (b.cores[i] > 0) { const [x, y] = b.corePos(i); out.push({ kind: 'core', e: b.e, i, x, y, r: c.r, b }); } });
      out.push({ kind: 'body', e: b.e, x: b.x, y: b.y, r: b.r, b });
      for (const [x, y] of this.segments(b)) out.push({ kind: 'body', e: b.e, x, y, r: 9, b, seg: true });
    }
    for (const a of Object.values(this.adds)) out.push({ kind: 'add', a: a.id, x: a.x, y: a.y, r: a.r, add: a });
    return out;
  }
}

const legsOnly = p => ({ leg_f: p.leg_f, leg_b: p.leg_b, leg_ff: p.leg_f, leg_bb: p.leg_b, leg_fb: -p.leg_f, leg_bf: -p.leg_b });

// draw a placed shape onto a graphics (filled or outlined)
function shape(g, s, fill) {
  if (s.k === 'circle' || s.k === 'proj' || s.k === 'zone') {
    fill ? g.fillCircle(s.cx, s.cy, s.r) : g.strokeCircle(s.cx, s.cy, s.r);
  } else if (s.k === 'ring') {
    g.strokeCircle(s.cx, s.cy, s.r);
  } else if (s.k === 'arc') {
    const pts = [[s.cx, s.cy]];
    for (let d = s.a0; d <= s.a1 + 0.1; d += 8) {
      const a = s.a + d * Math.PI / 180;
      pts.push([s.cx + Math.cos(a) * s.r, s.cy + Math.sin(a) * s.r]);
    }
    poly(g, pts, fill);
  } else if (s.k === 'rect') {
    const c = Math.cos(s.a), n = Math.sin(s.a);
    const P = (fx, fy) => [s.cx + c * fx - n * fy, s.cy + (n * fx + c * fy)];
    poly(g, [P(s.x0, -s.w), P(s.x1, -s.w), P(s.x1, s.w), P(s.x0, s.w)], fill);
  }
}

function poly(g, pts, fill) {
  g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
  for (const p of pts.slice(1)) g.lineTo(p[0], p[1]);
  g.closePath();
  fill ? g.fillPath() : g.strokePath();
}
