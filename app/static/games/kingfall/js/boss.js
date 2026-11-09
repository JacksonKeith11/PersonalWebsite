// The boss in the browser. Drawn at the server's present time: during a move its position, aim and
// pose come from the move's timeline (the same for every browser); between moves it's extrapolated
// from the snapshots. Also draws each move's danger: ground marks before area hits, slashes, thrusts,
// shockwave rings and projectiles, and checks every hit against this browser's heroes.
import { Rig, sample, runCycle, rigDefaults, atlas } from './rig.js?v=1';
import { LiveMove, placeHit, touches } from './moves.js?v=1';

const FIRE = 0xff7a1a, DANGER = 0xd0302a, STEEL = 0xe8ecf2;

export class Boss {
  constructor(scene, data, fight) {
    this.scene = scene;
    this.B = data.bosses[fight.boss];
    this.def = rigDefaults(this.B.rig);
    const f = {};
    for (const k of Object.keys(atlas().rigs[this.B.rig].parts)) f[k] = `${this.B.art}.${k}`;
    this.rig = new Rig(scene, this.B.rig, f);
    this.shadow = scene.add.ellipse(0, 0, 54, 16, 0x000000, 0.4).setDepth(1);
    this.marks = scene.add.graphics().setDepth(2);     // on the floor, under everyone
    this.fx = scene.add.graphics().setDepth(5000);     // swings and projectiles, over everyone
    this.x = fight.size[0] / 2; this.y = fight.size[1] * 0.36;
    this.snap = null; this.sx = this.x; this.sy = this.y;
    this.face = Math.PI / 2;
    this.moves = [];          // live and recent moves (projectiles outlive their move)
    this.hp = fight.mhp; this.mhp = fight.mhp; this.poise = fight.mpoise; this.mpoise = fight.mpoise;
    this.phase = 1; this.state = 'intro';
    this.walk = 0; this.flash = 0; this.staggerT = 0;
    this.r = this.B.radius;
    this.embers = null;
  }

  get alive() { return this.state !== 'dead' && this.hp > 0; }

  onSnap(st, b) {
    const [x, y, vx, vy, face, hp, mhp, po, mpo, ph, state] = b;
    if (state === 'stagger' && this.state !== 'stagger') this.staggerT = 0;
    this.snap = { st, x, y, vx, vy };
    Object.assign(this, { face, hp, mhp, poise: po, mpoise: mpo, phase: ph, state });
  }

  onMove(m) {
    const data = m.id === 'phase2' ? this.B.phase2_move : this.B.moves[m.id];
    if (!data) return;
    this.moves.push(new LiveMove(m, data));
    if (this.moves.length > 6) this.moves.shift();
  }
  onAim(m) { const mv = this.moves.find(v => v.seq === m.seq); if (mv) mv.reaim(m.lt, m.a, m.d); }
  onCancel(m) { const mv = this.moves.find(v => v.seq === m.seq); if (mv) mv.cancelAt = m.at; }

  current(now) {
    for (let i = this.moves.length - 1; i >= 0; i--) {
      const mv = this.moves[i];
      if (now < mv.end() + 0.02) return mv;
    }
    return null;
  }

  update(now, dt) {
    this.flash = Math.max(0, this.flash - dt);
    const mv = this.current(now);
    let pose, moving = false;
    if (mv) {
      const t = now - mv.start;
      const [x, y] = mv.pos(Math.max(0, t));
      this.x = x; this.y = y; this.sx = x; this.sy = y;
      this.face = mv.aim(Math.max(0, t));
      pose = sample(mv.data.anim, Math.max(0, Math.min(t, mv.cancelAt - mv.start)), this.def);
      if (pose.run) { this.walk += dt * 14; Object.assign(pose, runCycle(this.walk, 0.8), { torso: pose.torso, arm_b: pose.arm_b, shield: pose.shield }); }
    } else if (this.snap) {
      // extrapolate from the last snapshot, then ease toward it so corrections don't jump
      const s = this.snap, dts = Math.min(0.25, now - s.st);
      const tx = s.x + s.vx * dts, ty = s.y + s.vy * dts;
      this.sx += (tx - this.sx) * Math.min(1, dt * 12); this.sy += (ty - this.sy) * Math.min(1, dt * 12);
      this.x = this.sx; this.y = this.sy;
      moving = Math.hypot(s.vx, s.vy) > 5;
    }
    if (this.state === 'stagger' && !mv) {
      this.staggerT += dt;
      pose = { torso: 22, head: 18, arm_f: 30, weapon: 120, arm_b: 30, shield: -30, dy: 4 + Math.sin(this.staggerT * 3) };
    } else if (this.state === 'dead') {
      pose = { torso: 30, head: 30, arm_f: 40, weapon: 150, arm_b: 40, dy: 6 };
    } else if (!pose) {
      if (moving) { this.walk += dt * 8; pose = runCycle(this.walk, 0.7); }
      else pose = { torso: Math.sin(now * 1.8) * 1.5, head: Math.sin(now * 1.8 + 0.6) * 1.5 };
    }
    const left = Math.cos(this.face) < -0.05;
    this.rig.pose(pose, left);
    this.rig.c.setPosition(Math.round(this.x), Math.round(this.y)).setDepth(this.y);
    this.shadow.setPosition(this.x, this.y + 1);
    this.rig.setTint(this.flash > 0 ? 0xffffff : null);
    if (this.state === 'dead') this.rig.c.alpha = Math.max(0, this.rig.c.alpha - dt * 0.35);
    this.drawDanger(now, mv);
  }

  // ground marks, swing arcs, rings and projectiles
  drawDanger(now, cur) {
    const g = this.marks, f = this.fx;
    g.clear(); f.clear();
    for (const mv of this.moves) {
      const t = now - mv.start;
      if (t > mv.data.dur + 3) continue;
      mv.data.hits.forEach(h => {
        const s = placeHit(mv, h, t, h.mark ?? 0);
        if (!s) return;
        const fire = !!h.fire, col = fire ? FIRE : STEEL;
        if (!s.live) { // the warning before it lands
          const u = 1 - (h.t0 - t) / Math.max(0.05, h.mark);
          g.fillStyle(DANGER, 0.12 + 0.22 * u); shape(g, s, true);
          g.lineStyle(1, DANGER, 0.5 + 0.4 * u); shape(g, s, false);
          return;
        }
        const life = (t - h.t0) / Math.max(0.05, h.t1 - h.t0);
        if (s.k === 'proj') {
          f.fillStyle(fire ? 0xffd23f : 0xc0d0ff, 1); f.fillCircle(s.cx, s.cy - 4, s.r * 0.55);
          f.fillStyle(col, 0.55); f.fillCircle(s.cx, s.cy - 4, s.r);
          g.fillStyle(0x000000, 0.25); g.fillEllipse(s.cx, s.cy + 2, s.r * 2, s.r * 0.7);
        } else if (s.k === 'ring') {
          f.lineStyle(s.th, col, 0.65 * (1 - life * 0.6)); f.strokeEllipse(s.cx, s.cy, s.r * 2, s.r * 2);
          f.lineStyle(2, 0xfff0c0, 0.8 * (1 - life)); f.strokeEllipse(s.cx, s.cy, s.r * 2, s.r * 2);
        } else if (s.k === 'arc') {
          slash(f, s, life, col);
        } else if (s.k === 'rect') {
          thrust(f, s, life, col);
        } else if (s.k === 'circle') {
          f.fillStyle(col, 0.35 * (1 - life)); f.fillEllipse(s.cx, s.cy, s.r * 2, s.r * 2);
          f.lineStyle(2, col, 0.8 * (1 - life)); f.strokeEllipse(s.cx, s.cy, s.r * 2, s.r * 2);
        }
      });
    }
  }

  // test every live hit against a hero; calls back once per hit id that touches it
  checkHero(now, hero, cb) {
    for (const mv of this.moves) {
      const t = now - mv.start;
      if (t > mv.data.dur + 3 || t < 0) continue;
      mv.data.hits.forEach((h, i) => {
        const id = `${mv.seq}:${i}`;
        if (hero.taken.has(id)) return;
        const s = placeHit(mv, h, t);
        if (!s || !s.live) return;
        if (touches(s, hero.x, hero.y, hero.HERO.radius)) {
          const [bx, by] = mv.pos(Math.min(t, h.t0));
          const r = cb(h, id, s.k === 'proj' || s.k === 'ring' ? s.cx : bx, s.k === 'proj' || s.k === 'ring' ? s.cy : by);
          if (r) hero.taken.add(id);
        }
      });
    }
  }
}

// draw a placed shape onto a graphics (filled or outlined), squashed for the 3/4 view
function shape(g, s, fill) {
  const Y = 1;
  if (s.k === 'circle' || s.k === 'proj') {
    fill ? g.fillEllipse(s.cx, s.cy, s.r * 2, s.r * 2 * Y) : g.strokeEllipse(s.cx, s.cy, s.r * 2, s.r * 2 * Y);
  } else if (s.k === 'ring') {
    g.strokeEllipse(s.cx, s.cy, s.r * 2, s.r * 2 * Y);
  } else if (s.k === 'arc') {
    const pts = [[s.cx, s.cy]];
    for (let d = s.a0; d <= s.a1 + 0.1; d += 8) {
      const a = s.a + d * Math.PI / 180;
      pts.push([s.cx + Math.cos(a) * s.r, s.cy + Math.sin(a) * s.r * Y]);
    }
    poly(g, pts, fill);
  } else if (s.k === 'rect') {
    const c = Math.cos(s.a), n = Math.sin(s.a);
    const P = (fx, fy) => [s.cx + c * fx - n * fy, s.cy + (n * fx + c * fy) * Y];
    poly(g, [P(s.x0, -s.w), P(s.x1, -s.w), P(s.x1, s.w), P(s.x0, s.w)], fill);
  }
}

function poly(g, pts, fill) {
  g.beginPath(); g.moveTo(pts[0][0], pts[0][1]);
  for (const p of pts.slice(1)) g.lineTo(p[0], p[1]);
  g.closePath();
  fill ? g.fillPath() : g.strokePath();
}

// a crescent sweeping across the arc as the hit plays
export function slash(f, s, life, col, Y = 1) {
  const sweep = Math.min(1, life * 1.6), fade = 1 - Math.max(0, life - 0.4) / 0.6;
  const a0 = s.a0, a1 = s.a0 + (s.a1 - s.a0) * sweep;
  for (let k = 0; k < 3; k++) {
    const rr = s.r * (0.72 + k * 0.13);
    f.lineStyle(3 - k, k === 2 ? 0xffffff : col, (0.35 + k * 0.25) * fade);
    f.beginPath();
    for (let d = a0; d <= a1; d += 6) {
      const a = s.a + d * Math.PI / 180, x = s.cx + Math.cos(a) * rr, y = s.cy - 12 + Math.sin(a) * rr * Y;
      d === a0 ? f.moveTo(x, y) : f.lineTo(x, y);
    }
    f.strokePath();
  }
}

export function thrust(f, s, life, col, Y = 1) {
  const c = Math.cos(s.a), n = Math.sin(s.a), fade = 1 - life;
  const L = s.x0 + (s.x1 - s.x0) * Math.min(1, life * 2);
  for (let k = 0; k < 3; k++) {
    const w = s.w * (1 - k * 0.35);
    f.fillStyle(k === 2 ? 0xffffff : col, (0.2 + k * 0.2) * fade);
    const P = (fx, fy) => [s.cx + c * fx - n * fy, s.cy - 12 + (n * fx + c * fy) * Y];
    const pts = [P(s.x0, -w * 0.3), P(L * 0.8, -w), P(L, 0), P(L * 0.8, w), P(s.x0, w * 0.3)];
    f.beginPath(); f.moveTo(...pts[0]); for (const p of pts.slice(1)) f.lineTo(...p); f.closePath(); f.fillPath();
  }
}
