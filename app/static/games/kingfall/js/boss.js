// The boss in the browser: one or more bodies, its adds, and every move's danger. Drawn at the server's
// present time: during a move a body's position, aim and pose come from the move's timeline (the same
// for every browser); between moves it's extrapolated from the snapshots. Draws ground marks before
// area hits, slashes, thrusts, rings, projectiles and lingering pools, and checks every hit against
// this browser's heroes.
import { Rig, sample, runCycle, rigDefaults, atlas } from './rig.js?v=47';
import { LiveMove, placeHit, touches, active, spared } from './moves.js?v=47';
import { crescent, lance, burst, shockwave, orb, pool } from './fx.js?v=47';
import { sfx } from './audio.js?v=47';

const FIRE = 0xff7a1a, DANGER = 0xd0302a, STEEL = 0xe8ecf2;
const POOL = { poison: 0x6a8a2a, fire: 0xff6a1a, ice: 0x7fe3ff, void: 0x8a3ab0, blood: 0x8a1e2a };
const INTERP = 0.1;
const GOLD = 0xffd23f, UNBLOCK = 0xff3a20;
const hex = c => Phaser.Display.Color.HexStringToColor(c).color;

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
      const [x, y, vx, vy, face, hp, mhp, po, mpo, ph, state, cores, meters, live, brk] = row;
      if (state === 'stagger' && b.state !== 'stagger') b.staggerT = 0;
      if (ph > (b.phase || 1) && b.state !== 'dead' && this.scene.onPhase) this.scene.onPhase(b, ph);
      b.snap = { st, x, y, vx, vy };
      Object.assign(b, { face, hp, mhp, poise: po, mpoise: mpo, phase: ph, state, cores, meters: meters || [], live: live || [], brk: brk || 0 });
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
    let im;
    if (A.draw) im = sc.add.image(x, y, propTexture(sc, A.draw)).setOrigin(0.5, 0.92);
    else {
      const [, , w, h, px, py] = atlas().frames[A.art];
      im = sc.add.image(x, y, 'atlas', A.art).setOrigin(px / w, py / h);
    }
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
    const strikes = data.hits.filter((h, i) => h.k !== 'spawn' && h.k !== 'zone' && active(mv, h, i));
    mv.first = strikes.length ? Math.min(...strikes.map(h => h.t0)) : null;
    mv.unblock = strikes.some(h => h.unblock);
    mv.last = mv.start + Math.max(data.dur, ...data.hits.map(h => h.t1));
    this.moves.push(mv);
    if (this.moves.length > 16) this.dropProps(this.moves.shift());
    if (data.name && this.scene.onSig) this.scene.onSig(b, data);
  }
  onSpot(m) { const mv = this.moves.find(v => v.seq === m.seq); if (mv && mv.c.spots && mv.c.spots[m.i]) mv.c.spots[m.i][4] = 1; }
  onReflect(m) { const mv = this.moves.find(v => v.seq === m.seq); if (mv) mv.gone.add(m.i); return mv; }
  // the boss's projectiles in flight within r of (x, y): [{seq, i, mv, x, y}] (a nova, a frost burst shatters them)
  shotsIn(now, x, y, r) {
    const out = [];
    for (const mv of this.moves) {
      const t = now - mv.start;
      mv.data.hits.forEach((h, i) => {
        if (h.k !== 'proj' || !active(mv, h, i)) return;
        const s = placeHit(mv, h, t);
        if (s && s.live && Math.hypot(s.cx - x, s.cy - y) <= r + s.r) out.push({ seq: mv.seq, i, mv, x: s.cx, y: s.cy });
      });
    }
    return out;
  }
  // a move's props (bells, stones, a word in the air): made as it needs them, dropped when it's over
  dropProps(mv) {
    if (!mv || !mv.props) return;
    for (const o of mv.props) o.destroy();
    mv.props = null;
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
    this.marks.clear(); this.fx.clear(); this.glow.clear();   // before the bodies draw their rings and bars on them
    for (const b of this.bodies) this.updateBody(b, now, dt);
    this.updateAdds(now, dt);
    this.drawDanger(now);
    this.sounds(now);
  }

  // Every attack is heard: a breath drawn in through the wind-up, a ping with the glint, and each hit's
  // own sound as it starts (audio.js, sfx.boss), panned to where it is. Hits of one kind starting within
  // 60 ms of each other (a fan of knives, a cross of brands) sound once; a cancelled move falls silent.
  sounds(now) {
    for (const mv of this.moves) {
      const t = now - mv.start, S = mv.snd ||= { hits: new Set(), last: {} };
      if (t < 0 || now > mv.last + 0.2 || now > mv.cancelAt) continue;
      const b = this.bodies[mv.e], pan = this.scene.pan(b ? b.x : mv.origin[0]);
      if (mv.first != null) {
        if (!S.windup && mv.first > 0.3) { S.windup = true; if (t < 0.15) sfx.boss.windup(pan, Math.min(1.4, mv.first - t), mv.unblock); }
        if (!S.glint && t >= mv.first - 0.3) { S.glint = true; if (t < mv.first) sfx.boss.glint(pan, mv.unblock); }
      }
      mv.data.hits.forEach((h, i) => {
        if (S.hits.has(i) || t < h.t0 || !active(mv, h, i)) return;
        S.hits.add(i);
        if (t > h.t0 + 0.25 || mv.start + h.t0 > mv.cancelAt) return;   // long past (we joined late), or never happened
        const kind = h.k === 'spawn' ? 'spawn' : h.k === 'circle' && (h.tx || h.mark != null) ? 'land' : h.k;
        const s = h.k === 'spawn' ? null : placeHit(mv, h, h.t0);
        this.leaveMark(h, s);
        if (S.last[kind] != null && h.t0 - S.last[kind] < 0.06) return;
        S.last[kind] = h.t0;
        const size = h.k === 'rect' ? h.x1 - h.x0 : h.k === 'ring' ? h.th : h.r || 40;
        sfx.boss[kind](s ? this.scene.pan(s.cx) : pan, size, { fire: !!h.fire || h.pool === 'fire', heavy: !!h.unblock });
      });
    }
  }

  // What a hit leaves on the floor (atmos.js, mark): a slam cracks it, fire scorches it, a pool stains it.
  leaveMark(h, s) {
    const A = this.scene.atmos, fire = !!h.fire || h.pool === 'fire';
    if (!A || !s) return;
    if (s.k === 'zone') fire ? A.mark('scorch', s.cx, s.cy, s.r * 0.8, 0, h.t1 - h.t0) : A.mark('stain', s.cx, s.cy, s.r * 0.85, POOL[s.pool] || 0x6a8a2a, h.t1 - h.t0);
    else if (s.k === 'circle') A.mark(fire ? 'scorch' : 'crack', s.cx, s.cy, fire ? s.r * 0.75 : Math.min(60, s.r * 0.9));
    else if (fire && s.k === 'arc') A.mark('scorch', s.cx + Math.cos(s.a) * s.r * 0.6, s.cy + Math.sin(s.a) * s.r * 0.6, s.r * 0.4);
    else if (fire && s.k === 'rect') A.mark('scorch', s.cx + Math.cos(s.a) * (s.x0 + s.x1) / 2, s.cy + Math.sin(s.a) * (s.x0 + s.x1) / 2, Math.min(40, (s.x1 - s.x0) * 0.3));
  }

  // How a body falls, by what it is: a knight reels and topples (`kneel`), a beast slumps (`slump`), a
  // thing of stone or bronze shakes itself apart and settles (`crumble`), the mirror knight breaks into
  // shards (`shatter`), a flyer drops out of the air (`fall`), the wyrm goes still from the tail up (`coil`).
  deathStyle(b) {
    if (b.def.render === 'wyrm') return 'coil';
    if (b.def.hover) return 'fall';
    if (b.rigName === 'mirror') return 'shatter';
    if (b.rigName === 'golem' || b.rigName === 'bellwarden') return 'crumble';
    return b.rig.parts.torso ? 'kneel' : 'slump';
  }

  // The pose of a dying body at `T` seconds after the blow, and what the fall does around it (dust, a
  // thud as it comes to rest, shards). It reels from the pose it was struck in, then goes down.
  dying(b, dt) {
    const first = b.deadT == null, sc = this.scene, style = b.deathStyle ||= this.deathStyle(b);
    if (first) { b.deadT = 0; b.fromPose = b.lastPose || {}; b.landed = false; b.puffT = 0; b.rig.setTint(null); }
    const T0 = b.deadT; b.deadT += dt;
    const T = b.deadT, dead = b.def.dead_pose || { torso: 30, head: 30, arm_f: 40, weapon: 150, arm_b: 40, dy: 6 };
    const mix = (p0, p1, u) => { const o = {}; for (const k of new Set([...Object.keys(p0), ...Object.keys(p1)])) { const a = p0[k] ?? b.def_[k] ?? 0, c = p1[k] ?? b.def_[k] ?? 0; o[k] = typeof a === 'number' && typeof c === 'number' ? a + (c - a) * u : u < 0.5 ? a : c; } return o; };
    const cl = u => Math.max(0, Math.min(1, u)), drop = style === 'crumble' ? 1.2 : style === 'slump' ? 0.8 : 1.0, reelEnd = style === 'slump' ? 0.3 : 0.45;
    const reel = style === 'kneel' || style === 'shatter' ? { ...dead, torso: -14, head: -20, arm_f: -30, arm_b: -24, dy: 0 } : { ...dead, dy: 0, z: b.fromPose.z || 0 };
    let pose;
    if (T < reelEnd) pose = mix(b.fromPose, reel, 1 - (1 - cl(T / reelEnd)) ** 2);
    else { const u = cl((T - reelEnd) / (drop - reelEnd)); pose = mix(reel, dead, u * u); }   // it falls faster as it goes
    delete pose.run;
    const c = b.rig.c, dir = c.scaleX < 0 ? -1 : 1, fallU = cl((T - reelEnd) / (drop - reelEnd));
    b.shake = T < drop ? (style === 'crumble' ? 2.2 : 1.2) * (style === 'crumble' ? 0.4 + T / drop : 1 - T / drop) : 0;
    if (style === 'kneel') c.angle = dir * 76 * fallU * fallU;          // flat on its face
    else if (style === 'slump' || style === 'fall') c.angle = dir * 10 * fallU * fallU;
    else if (style === 'crumble') c.scaleY = 1 - 0.14 * fallU;
    if (style === 'crumble' && T < drop) {   // pieces coming off it all the way down
      b.puffT -= dt;
      if (b.puffT <= 0) { b.puffT = 0.14; sc.atmos.dust(b.x + (Math.random() - 0.5) * b.r * 2, b.y, 3, true); sc.burst(b.x + (Math.random() - 0.5) * b.r * 2, b.y - 20 - Math.random() * 40, 0xc8b8a0, 4); }
    }
    if (style === 'shatter') {
      b.rig.setTint(T < 0.55 && Math.floor(T * 22) % 2 ? 0xffffff : null);
      if (T0 < 0.55 && T >= 0.55) {
        sfx.shatter(sc.pan(b.x)); sc.burst(b.x, b.y - 30, 0xe0f8ff, 60); sc.burst(b.x, b.y - 46, 0xffffff, 24);
        sc.atmos.embers(b.x, b.y, 30, 0xc8f0ff); sc.atmos.mark('crack', b.x, b.y, 40); sc.cameras.main.shake(180, 0.008);
        b.landed = true;
      }
      if (T >= 0.55) c.alpha = Math.max(0, c.alpha - dt * 7);
    } else if (!b.landed && T >= drop) {   // it comes to rest
      b.landed = true;
      const big = b.r >= 20;
      sfx.collapse(sc.pan(b.x), big); sc.atmos.dust(b.x + dir * (style === 'kneel' ? 24 : 0), b.y, big ? 16 : 10, true);
      sc.cameras.main.shake(big ? 260 : 160, big ? 0.009 : 0.005);
      if (big || style === 'crumble') sc.atmos.mark('crack', b.x + dir * (style === 'kneel' ? 18 : 0), b.y, Math.min(56, b.r * 1.8));
    }
    if (style === 'coil' && b.segs) {   // the vertebrae go dark from the tail to the head
      b.segs.forEach((s, i) => {
        const at = 0.15 + (b.segs.length - 1 - i) * 0.12, was = s.alpha;
        s.alpha = Math.max(0.0, 1 - cl((T - at) / 0.5));
        if (was > 0.5 && s.alpha <= 0.5 && s.p) sc.atmos.dust(s.p[0], s.p[1], 4, true);
      });
    }
    // the body lies a while, then fades
    const fadeAt = style === 'coil' ? 0.15 + b.segs.length * 0.12 + 0.3 : 1.7;
    if (style !== 'shatter' && T > fadeAt) c.alpha = Math.max(0, c.alpha - dt * 0.5);
    b.shadow.alpha = c.alpha * 0.4;
    return pose;
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
    } else if (b.state === 'tired' && !mv) {   // winded after a string: slumped and heaving, the opening
      const sp = b.def.stagger_pose || { torso: 22, head: 18, arm_f: 30, weapon: 120, arm_b: 30, shield: -30, dy: 4 };
      pose = {};
      for (const k in sp) pose[k] = sp[k] * 0.6;
      pose.dy = (sp.dy || 4) * 0.6 + Math.sin(now * 9) * 1.2;
    } else if (b.state === 'dead') {
      pose = this.dying(b, dt);
    } else if (!pose) {
      if (moving) { b.walk += dt * 8; pose = runCycle(b.walk, 0.7); }
      else pose = { torso: Math.sin(now * 1.8) * 1.5, head: Math.sin(now * 1.8 + 0.6) * 1.5 };
      if (b.def.idle_pose) pose = { ...b.def.idle_pose, ...pose };
    }
    // height: leaps and flight lift the whole figure off its shadow
    if (b.state !== 'dead') b.lastPose = pose;
    const hover = b.def.hover ? b.def.hover + (b.state === 'dead' ? 0 : Math.sin(now * 2.4) * 2) : 0;
    b.z = (pose.z || 0) + hover;
    const jx = b.state === 'dead' && b.shake ? (Math.random() - 0.5) * 2 * b.shake : 0;
    const left = Math.cos(b.face) < -0.05;
    const under = b.untouchable(now, mv) && mv && mv.data.under && now - mv.start >= mv.data.under[0] && now - mv.start <= mv.data.under[1];
    if (b.def.render === 'wyrm') this.drawWyrm(b, pose, left, under, dt);
    else {
      b.rig.pose(pose, left);
      b.rig.c.setPosition(Math.round(b.x + jx), Math.round(b.y - b.z)).setDepth(b.y);
      b.rig.c.setVisible(!under);
    }
    const sh = Math.max(0.4, 1 - b.z / 120);
    b.shadow.setPosition(b.x, b.y + 1).setScale(sh).setVisible(!under);
    // a flash of white when struck; a flash of warning red in the instant before its strike lands
    const lead = mv && mv.first != null ? mv.first - (now - mv.start) : 9;
    if (b.state !== 'dead') b.rig.setTint(b.flash > 0 ? 0xffffff : lead > 0.02 && lead < 0.09 && now < mv.cancelAt ? (mv.unblock ? 0xff5030 : 0xffd0c0) : null);
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
    if (b.state === 'tired' && !mv) {   // breath puffing off it
      const f = this.fx, hy = b.y - b.z - Math.max(40, b.r * 2.2);
      for (let k = 0; k < 3; k++) {
        const u = (now * 1.1 + k / 3) % 1, side = Math.cos(b.face) < 0 ? -1 : 1;
        f.fillStyle(0xe8e0d0, 0.5 * (1 - u)); f.fillCircle(b.x + side * (b.r * 0.7 + u * 14), hy - u * 12, 2 + u * 3);
      }
    }
    // its break bar: gold, over its head, while a move that can be broken off is under way
    if (b.brk > 0 && b.alive) {
      const at = mv && mv.data.spot_kind === 'image' && mv.c.spots ? mv.c.spots.map(q => [q[0], q[1]]) : [[b.x, b.y]];   // the trinity: over all three
      const top = this.scene.cameras.main.worldView.y + 40;
      for (const [x, y] of at) this.breakBar(x, Math.max(top, y - b.z - Math.max(52, b.r * 2.9)), b.brk / 100, now);
    }
    // weak points glow until broken
    b.coreG.clear();
    // the scythe's mark: a pale crescent hanging over it until it is reaped or fades
    if ((b.reapUntil || 0) > now && b.state !== 'dead') {
      const hy = b.y - b.z - Math.max(60, b.r * 3.2), k = 0.7 + 0.3 * Math.sin(now * 6);
      b.coreG.lineStyle(2.5, 0xb8f0c0, k).beginPath().arc(b.x, hy, 7, Math.PI * 0.9, Math.PI * 2.1).strokePath();
      b.coreG.lineStyle(1.5, 0xffffff, k).lineBetween(b.x + 6, hy + 1, b.x + 6, hy + 10);
    }
    // the catalyst's sigils: violet marks turning over its head until the orb or the Nova spends them
    if (b.sigils > 0 && now - (b.sigilAt || 0) < 8 && b.state !== 'dead') {
      const hy = b.y - b.z - Math.max(52, b.r * 2.9);
      for (let i = 0; i < b.sigils; i++) {
        const a = now * 2 + i * Math.PI * 2 / b.sigils, sx = b.x + Math.cos(a) * 13, sy = hy + Math.sin(a) * 4;
        b.coreG.fillStyle(0xc080ff, 0.95).fillTriangle(sx - 3, sy, sx, sy - 4.5, sx + 3, sy).fillTriangle(sx - 3, sy, sx, sy + 4.5, sx + 3, sy);
        b.coreG.fillStyle(0xffffff, 0.9).fillCircle(sx, sy, 1);
      }
    }
    (b.def.cores || []).forEach((c, i) => {
      if (!(b.cores[i] > 0) || b.state === 'dead') return;
      const [cx, cy] = b.corePos(i), p = 0.6 + Math.sin(now * 6 + i) * 0.25;
      b.coreG.lineStyle(2, 0xa0e0ff, p).strokeCircle(cx, cy - (c.h || 0), c.r * 0.8);
      b.coreG.lineStyle(1, 0xffffff, p * 0.6).strokeCircle(cx, cy, c.r);
    });
  }

  breakBar(x, y, u, now) {
    const f = this.fx, w = 44, p = 0.75 + Math.sin(now * 12) * 0.25;
    f.fillStyle(0x120e16, 0.85); f.fillRect(x - w / 2 - 2, y - 4, w + 4, 8);
    f.fillStyle(GOLD, p); f.fillRect(x - w / 2, y - 2, w * u, 4);
    f.lineStyle(1, GOLD, 0.9); f.strokeRect(x - w / 2 - 2, y - 4, w + 4, 8);
    f.fillStyle(GOLD, p); f.fillTriangle(x - 4, y - 7, x + 4, y - 7, x, y - 3);
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
    for (const mv of this.moves) {
      const t = now - mv.start;
      if (now > mv.last + 0.2 || now > mv.cancelAt + 0.2) { this.dropProps(mv); continue; }
      this.drawTell(mv, t, now);
      this.drawCast(mv, t, now);
      mv.data.hits.forEach((h, i) => {
        if (!active(mv, h, i)) return;
        if (h.room) { this.drawRoom(mv, h, t, now); return; }
        if (h.mark == null && t < h.t0) { this.drawWindup(mv, h, t); return; }
        const fire = !!h.fire, col = fire ? FIRE : h.col ? Phaser.Display.Color.HexStringToColor(h.col).color : STEEL;
        // a swing's trail lingers a moment after it can no longer hurt
        const AFTER = 0.2, melee = h.k === 'arc' || h.k === 'rect' || h.k === 'circle';
        if (melee && h.grp == null && t > h.t1 && t < h.t1 + AFTER && mv.start + h.t1 <= mv.cancelAt) {
          const s = placeHit(mv, h, h.t1);
          if (s) this.drawStrike(gl, s, 1 + (t - h.t1) / AFTER, col);
          return;
        }
        const s = placeHit(mv, h, t, h.mark ?? 0);
        if (!s) return;
        if (!s.live) { // the warning before it lands: it fills from the middle, reaching the edge as it strikes
          const u = 1 - (h.t0 - t) / Math.max(0.05, h.mark);
          warn(g, s, u, h.unblock ? UNBLOCK : DANGER, !!h.unblock);
          return;
        }
        const life = (t - h.t0) / Math.max(0.05, h.t1 - h.t0);
        if (h.abs) {   // a strip of the arena: the whole of it burns (or is torn through) at once
          gl.fillStyle(col, 0.5 * (1 - life * 0.5)); shape(gl, s, true);
          gl.fillStyle(0xffffff, 0.25 * (1 - life)); shape(gl, { ...s, w: s.w * 0.35 }, true);
          return;
        }
        if (s.k === 'zone') {
          pool(g, gl, s, POOL[s.pool] || 0x6a8a2a, Math.min(1, (h.t1 - t) * 2, (t - h.t0) * 4), now, DANGER);
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
    if (h.grp != null) {   // a turning beam: one thin line a little ahead of it, showing which way it turns
      if (h.t0 - t > 0.3 && h.t0 - t <= 0.46) { this.marks.lineStyle(1.5, UNBLOCK, 0.7); shape(this.marks, s, false); }
      return;
    }
    const u = 1 - (h.t0 - t) / lead, g = this.marks;
    const col = h.unblock ? UNBLOCK : DANGER;
    if (s.k === 'proj') {
      const L2 = Math.min(140, h.v * 0.5), c = Math.cos(s.a), n = Math.sin(s.a);
      g.lineStyle(1, col, 0.25 + 0.5 * u);
      for (let d = 0; d < L2; d += 10) g.lineBetween(s.cx + c * d, s.cy + n * d, s.cx + c * (d + 5), s.cy + n * (d + 5));
      return;
    }
    if (s.k === 'ring') { g.lineStyle(1, col, 0.2 + 0.4 * u); g.strokeCircle(s.cx, s.cy, h.r0 + 10); return; }
    warn(g, s, u, col, !!h.unblock);
  }

  // A blast across the whole arena: the floor floods with its colour as it comes, and what will save
  // you is drawn in gold: safe ground as a ring that fills, cover as the shadow behind it.
  drawRoom(mv, h, t, now) {
    const g = this.marks, lead = h.mark ?? 1.5, col = h.col ? hex(h.col) : DANGER;
    if (t < h.t0 - lead || t > h.t1 + 0.25 || mv.start + Math.min(t, h.t0) > mv.cancelAt) return;
    const u = Math.max(0, Math.min(1, 1 - (h.t0 - t) / lead)), live = t >= h.t0;
    const fade = live ? Math.max(0, 1 - (t - h.t1) / 0.25) : 1;
    g.fillStyle(col, (live ? 0.55 : 0.1 + 0.26 * u * u + 0.04 * Math.sin(now * (6 + 10 * u))) * fade);
    g.fillRect(-300, -300, 1500, 1200);
    if (live) return;
    const [ox, oy] = mv.pos(h.t0);
    if (h.near != null) this.safeRing(ox, oy, h.near, u, now);
    if (h.still) {   // stand still: a gold ring at the feet of every hero on this screen
      for (const hero of this.scene.local || []) if (!hero.down) { g.lineStyle(2, GOLD, 0.5 + 0.4 * u); g.strokeEllipse(hero.x, hero.y, 26 - 8 * u, 11 - 3 * u); }
    }
    for (const sp of mv.c.spots || []) {
      const [x, y, r, tag, on] = sp;
      if (h.safe != null) {
        if (mv.data.spot_kind === 'flask') continue;   // the circles are drawn in their own colours; which is safe is the puzzle
        if (h.safe === tag && on) this.safeRing(x, y, r, u, now);
        else if (h.safe === tag) { g.lineStyle(1, GOLD, 0.35); g.strokeCircle(x, y, r); }
      }
      if (h.cover === tag && on) this.shadow(ox, oy, x, y, r, u);
    }
  }

  // the shadow a piece of cover casts, away from the boss at (ox, oy): gold, the safe ground behind it
  shadow(ox, oy, x, y, r, u) {
    const g = this.marks, a = Math.atan2(y - oy, x - ox), d = Math.hypot(x - ox, y - oy), w = Math.asin(Math.min(1, (r + 6) / Math.max(d, r + 7)));
    const P = (ang, dist) => [ox + Math.cos(ang) * dist, oy + Math.sin(ang) * dist];
    g.fillStyle(GOLD, 0.14 + 0.1 * u);
    poly(g, [P(a - w, d), P(a - w, d + 900), P(a + w, d + 900), P(a + w, d)], true);
    g.lineStyle(1.5, GOLD, 0.5 + 0.4 * u);
    g.lineBetween(...P(a - w, d), ...P(a - w, d + 900)); g.lineBetween(...P(a + w, d), ...P(a + w, d + 900));
  }

  safeRing(x, y, r, u, now) {
    const g = this.marks;
    g.fillStyle(GOLD, 0.12 + 0.08 * u); g.fillCircle(x, y, r);
    g.lineStyle(2, GOLD, 0.6 + 0.35 * u); g.strokeCircle(x, y, r);
    g.lineStyle(3, 0xfff0c0, 0.9); g.beginPath(); g.arc(x, y, r + 4, -Math.PI / 2, -Math.PI / 2 + u * Math.PI * 2); g.strokePath();   // counts down to the blast
    for (let k = 0; k < 4; k++) { const a = now * 0.8 + k * Math.PI / 2; g.lineBetween(x + Math.cos(a) * (r - 6), y + Math.sin(a) * (r - 6), x + Math.cos(a) * (r + 2), y + Math.sin(a) * (r + 2)); }
  }

  // what a cast sets out: its props (stones, bells, chalk circles, candles, rubble, a planted fist,
  // false knights), eyes in the treeline, a word in the air, the flask it holds up, cracks in the ground
  drawCast(mv, t, now) {
    const d = mv.data, b = this.bodies[mv.e], sc = this.scene, f = this.fx, g = this.marks;
    if (now > mv.cancelAt) { this.dropProps(mv); return; }
    const spots = mv.c.spots || [];
    const top = sc.cameras.main.worldView.y + 46;   // nothing it holds up may hide behind its own health bar
    // cover from a turning beam (not a blast: drawRoom draws those): its shadow, for as long as the beam turns
    const beam = d.hits.filter(h => h.cover != null && !h.room);
    if (beam.length && t > 0.4 && t < beam[beam.length - 1].t1) {
      const [ox, oy] = mv.pos(beam[0].t0);
      for (const [x, y, r, tag, on] of spots) if (on && tag === beam[0].cover) this.shadow(ox, oy, x, y, r, Math.min(1, t / beam[0].t0));
    }
    if (spots.length && d.spot_kind && t > 0.2) {
      mv.props ||= [];
      spots.forEach((sp, i) => {
        const [x, y, r, tag, on] = sp;
        if (d.spot_kind === 'image') {   // false knights: the boss's own figure, in its own pose, but no shadow under them
          if (tag === 0 || !b) return;
          let rig = mv['rig' + i];
          if (!rig) { rig = mv['rig' + i] = new Rig(sc, b.rigName, framesFor(b.rigName, b.art)); mv.props.push({ destroy: () => rig.c.destroy() }); }
          rig.pose(sample(d.anim, Math.max(0, t), b.def_), Math.cos(b.face) < -0.05);
          rig.c.setPosition(Math.round(x), Math.round(y)).setDepth(y);
          return;
        }
        if (d.spot_kind === 'flask') {
          const col = hex(d.spot_cols[tag]);
          g.fillStyle(col, 0.16); g.fillCircle(x, y, r);
          g.lineStyle(2.5, col, 0.9); g.strokeCircle(x, y, r);
          g.lineStyle(1, col, 0.6); g.strokeCircle(x, y, r - 6);
          return;
        }
        if (d.spot_kind === 'light') {   // rings of light, one after another: each shows only for its own blast
          const at = d.seq_spots[tag], h = d.hits[tag];
          if (t < at || t > h.t1) return;
          f.fillStyle(0xfff0c0, 0.05 + 0.03 * Math.sin(now * 5)); f.fillCircle(x, y, r);
          return;
        }
        const kind = d.spot_kind === 'candle' ? (on ? 'candle_lit' : null) : d.spot_kind;
        if (d.spot_kind === 'candle' && on) { f.fillStyle(0xffc860, 0.1 + 0.03 * Math.sin(now * 7 + i)); f.fillCircle(x, y, r); }
        if (!kind) return;
        let im = mv['im' + i];
        if (!im) {
          im = mv['im' + i] = sc.add.image(x, y - 140, propTexture(sc, kind)).setOrigin(0.5, 0.9).setDepth(y);
          mv.props.push(im);
          sc.tweens.add({ targets: im, y, duration: kind === 'candle_lit' ? 1 : 260, ease: 'Quad.easeIn', onComplete: () => { if (kind !== 'candle_lit' && sc.thud) sc.thud(x, y); } });
        }
      });
    }
    // the flask it holds up: stand in the circle of this colour
    if (d.spot_kind === 'flask' && b && t >= d.show && t < d.hits[0].t1) {
      const col = hex(d.spot_cols[mv.c.v]), x = b.x, y = Math.max(top, b.y - b.z - Math.max(60, b.r * 3.4)), p = 0.8 + 0.2 * Math.sin(now * 10);
      f.fillStyle(col, 0.3 * p); f.fillCircle(x, y, 13);
      f.fillStyle(col, 1); f.fillCircle(x, y, 7);
      f.lineStyle(2, 0xffffff, 0.9); f.strokeCircle(x, y, 7);
    }
    // a word in the air
    if (d.words && b && t >= d.show && t < d.hits[0].t1) {
      if (!mv.word) {
        mv.word = sc.add.text(b.x, b.y - 96, d.words[mv.c.v], { fontFamily: 'Cinzel, Georgia, serif', fontSize: '20px', fontStyle: 'bold', color: '#fff0c0',
          stroke: '#120e16', strokeThickness: 5, resolution: sc.cfg.zoom() }).setOrigin(0.5).setDepth(7000);
        (mv.props ||= []).push(mv.word);
      }
      mv.word.setPosition(b.x, Math.max(top + 8, b.y - b.z - 96)).setScale(1 + 0.05 * Math.sin(now * 8));
    }
    // eyes in the treeline: the three places it will come from; each brightens before its charge
    if (d.lanes && d.seqs) {
      d.seqs[mv.c.v].forEach((L, k) => {
        const at = d.at[k];
        if (t < 0.8 || t > at + 0.1) return;
        const [x, y, deg] = d.lanes[L], a = deg * Math.PI / 180, bright = t > at - 1.0;
        const ex = x + Math.cos(a) * 6, ey = y + Math.sin(a) * 6 - 14, nx = -Math.sin(a) * 5, ny = Math.cos(a) * 5;
        const p = bright ? 0.75 + 0.25 * Math.sin(now * 16) : 0.4;
        for (const sgn of [-1, 1]) {
          f.fillStyle(bright ? 0xff5030 : 0xd8c040, 0.3 * p); f.fillCircle(ex + nx * sgn, ey + ny * sgn, bright ? 6 : 4);
          f.fillStyle(bright ? 0xffe0a0 : 0xd8c040, p); f.fillCircle(ex + nx * sgn, ey + ny * sgn, bright ? 2.4 : 1.8);
        }
      });
    }
    // the wyrm under the ground: cracks run ahead of it to where it will come up
    if (b && b.def.render === 'wyrm' && d.under && t >= d.under[0] && t <= d.under[1]) {
      const [x0, y0] = mv.pos(d.under[0]), [x1, y1] = mv.pos(d.under[1]), L = Math.hypot(x1 - x0, y1 - y0);
      const u = (t - d.under[0]) / Math.max(0.01, d.under[1] - d.under[0]);
      g.lineStyle(2, 0x1a1410, 0.75);
      for (let q = 0; q < L * Math.min(1, u * 1.6); q += 12) {
        const px = x0 + (x1 - x0) * q / L, py = y0 + (y1 - y0) * q / L, j = Math.sin(q * 1.7) * 5;
        g.lineBetween(px - j * (y1 - y0) / L, py + j * (x1 - x0) / L, px + (x1 - x0) / L * 9 + j * (y1 - y0) / L, py + (y1 - y0) / L * 9 - j * (x1 - x0) / L);
      }
    }
    // something held taut between it and whoever it has caught (a tongue, a chain)
    for (const [hid, H] of Object.entries(sc.holds || {})) {
      if (H.seq !== mv.seq || now > H.until || !b) continue;
      const hero = sc.byId[hid];
      if (!hero) continue;
      const col = d.hits[0].col ? hex(d.hits[0].col) : 0xa8b0bc;
      f.lineStyle(4, 0x120e16, 0.6); f.lineBetween(b.x, b.y - b.z - b.r, hero.x, hero.y - 16);
      f.lineStyle(2, col, 1); f.lineBetween(b.x, b.y - b.z - b.r, hero.x, hero.y - 16);
      f.lineStyle(2, GOLD, 0.6 + 0.3 * Math.sin(now * 14)); f.strokeEllipse(hero.x, hero.y, 26, 11);
    }
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
        if (h.k === 'spawn' || !active(mv, h, i)) return;
        const id = `${mv.seq}:${i}` + (h.tick ? ':' + Math.floor((t - h.t0) / h.tick) : '');
        if (hero.taken.has(id)) return;
        const s = placeHit(mv, h, t);
        if (!s || !s.live) return;
        // one sweep of a turning beam (its steps share a `grp`) hurts once a while, not at every step
        const grp = h.grp != null ? `${mv.seq}:${h.grp}` : null, G = hero.grpHit ||= {};
        if (grp && now - (G[grp] ?? -9) < 0.9) return;
        if (touches(s, hero.x, hero.y, hero.HERO.radius) && !spared(mv, h, hero.x, hero.y, hero.moving)) {
          if (grp && !hero.invulnerable()) G[grp] = now;
          const [bx, by] = mv.pos(Math.min(t, h.t0));
          const far = s.k === 'proj' || s.k === 'ring' || s.k === 'zone';
          if (cb(h, id, far ? s.cx : bx, far ? s.cy : by)) hero.taken.add(id);
        }
      });
    }
    for (const a of Object.values(this.adds)) {
      if (!a.A.dmg || now - a.seen < 1.0 || Math.hypot(a.x - hero.x, a.y - hero.y) > a.r + hero.HERO.radius) continue;  // a moment's grace when it appears
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
      // ...and its body as drawn, which stands (or hovers: the Moth Saint) well above its feet. Without
      // this a blow or a shot aimed at the boss you see passes over the circle on the floor.
      out.push({ kind: 'body', e: b.e, x: b.x, y: b.y - b.z - b.r * 1.5, r: b.r, b, up: true });
      for (const [x, y] of this.segments(b)) out.push({ kind: 'body', e: b.e, x, y, r: 9, b, seg: true });
    }
    for (const a of Object.values(this.adds)) out.push({ kind: 'add', a: a.id, x: a.x, y: a.y, r: a.r, add: a });
    for (const mv of this.moves) {   // its projectiles that can be struck back at it
      const t = now - mv.start;
      mv.data.hits.forEach((h, i) => {
        if (!h.ret || !active(mv, h, i)) return;
        const s = placeHit(mv, h, t);
        if (s && s.live) out.push({ kind: 'shot', seq: mv.seq, i, mv, x: s.cx, y: s.cy - 8, r: s.r + 10 });
      });
    }
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


// The warning for a hit before it lands: a faint fill and an outline in the whole shape, and a
// stronger fill that grows from the boss's side (or the middle) and reaches the far edge at the
// instant of the strike. Hits that can't be blocked are orange-red with a doubled outline.
function warn(g, s, u, col, heavy) {
  u = Math.max(0, Math.min(1, u));
  g.fillStyle(col, 0.08 + 0.08 * u); shape(g, s, true);
  const inner = s.k === 'rect' ? (s.abs ? { ...s, w: s.w * u } : { ...s, x1: s.x0 + (s.x1 - s.x0) * u }) : s.k === 'arc' || s.k === 'circle' ? { ...s, r: s.r * u } : null;
  if (inner && u > 0.02) { g.fillStyle(col, 0.2); shape(g, inner, true); }
  g.lineStyle(u > 0.7 ? 2 : 1.5, col, 0.5 + 0.45 * u); shape(g, s, false);
  if (heavy) {
    const out = s.k === 'rect' ? { ...s, x0: s.x0 - 3, x1: s.x1 + 3, w: s.w + 3 } : { ...s, r: s.r + 3 };
    g.lineStyle(1, 0xffd0a0, 0.5 + 0.4 * u); shape(g, out, false);
  }
}

// Props drawn here rather than in the atlas: small canvases made once a scene and used as textures.
function propTexture(sc, kind) {
  const key = 'kfprop-' + kind;
  if (sc.textures.exists(key)) return key;
  const cv = document.createElement('canvas'); cv.width = 48; cv.height = 64;
  const c = cv.getContext('2d'), R = (col, x, y, w, h) => { c.fillStyle = col; c.fillRect(x, y, w, h); };
  c.fillStyle = 'rgba(0,0,0,0.35)'; c.beginPath(); c.ellipse(24, 57, 17, 5, 0, 0, 7); c.fill();
  if (kind === 'bell') {
    c.fillStyle = '#3a3048'; c.beginPath(); c.moveTo(11, 56); c.quadraticCurveTo(12, 22, 24, 18); c.quadraticCurveTo(36, 22, 37, 56); c.closePath(); c.fill();
    c.fillStyle = '#6a5a88'; c.beginPath(); c.moveTo(15, 54); c.quadraticCurveTo(16, 26, 24, 22); c.quadraticCurveTo(26, 30, 22, 54); c.closePath(); c.fill();
    R('#c8a8ff', 9, 53, 30, 3); R('#2a2236', 21, 12, 6, 7); R('#120e16', 22, 36, 2, 14);
  } else if (kind === 'stone') {
    c.fillStyle = '#4a5a44'; c.beginPath(); c.ellipse(24, 52, 20, 8, 0, 0, 7); c.fill();
    c.fillStyle = '#7a8a70'; c.beginPath(); c.ellipse(24, 49, 19, 7, 0, 0, 7); c.fill();
    c.fillStyle = '#98a88c'; c.beginPath(); c.ellipse(21, 47, 11, 3.5, 0, 0, 7); c.fill();
  } else if (kind === 'rubble' || kind === 'fist') {
    const dark = kind === 'fist' ? '#5a5462' : '#3c3644', mid = kind === 'fist' ? '#8a8494' : '#6a6474', lit = kind === 'fist' ? '#b8b0c0' : '#948ca0';
    c.fillStyle = dark; c.beginPath(); c.moveTo(8, 57); c.lineTo(11, 30); c.lineTo(22, 20); c.lineTo(35, 24); c.lineTo(40, 57); c.closePath(); c.fill();
    c.fillStyle = mid; c.beginPath(); c.moveTo(12, 55); c.lineTo(14, 32); c.lineTo(22, 24); c.lineTo(27, 30); c.lineTo(25, 55); c.closePath(); c.fill();
    c.fillStyle = lit; c.fillRect(15, 32, 6, 3);
    if (kind === 'fist') { R(dark, 13, 38, 24, 2); R(dark, 13, 45, 24, 2); R('#ffb040', 20, 26, 8, 3); }
  } else {   // a candle, lit or not
    R('#d8ccb0', 20, 30, 8, 26); R('#f0e8d0', 20, 30, 3, 26); R('#2a2236', 23, 25, 2, 6); R('#8a7a5a', 16, 54, 16, 4);
    if (kind === 'candle_lit') {
      c.fillStyle = 'rgba(255,200,96,0.35)'; c.beginPath(); c.arc(24, 20, 11, 0, 7); c.fill();
      c.fillStyle = '#ffb040'; c.beginPath(); c.ellipse(24, 20, 4, 7, 0, 0, 7); c.fill();
      c.fillStyle = '#fff0c0'; c.beginPath(); c.ellipse(24, 22, 2, 4, 0, 0, 7); c.fill();
    }
  }
  sc.textures.addCanvas(key, cv);
  return key;
}
