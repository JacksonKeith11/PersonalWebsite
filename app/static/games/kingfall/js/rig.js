// Cutout rigs: a character is a Phaser container of part images from the atlas, posed by rotating
// each part around its pivot. The rig tables (where each pivot sits, the drawing order, where the
// hand grips) come from atlas.json, written by tools/kingfall-art/build.py. Everything is drawn
// facing right; facing left flips the container. Angles are degrees, clockwise.
//
// Hierarchy: legs and torso hang off the body (which leans and bobs); head, arms and cape off the
// torso; the weapon off the front hand, the shield off the back hand.

let ATLAS = null;
export function setAtlas(a) { ATLAS = a; }
export const atlas = () => ATLAS;

// Adds every frame in the atlas to the loaded 'atlas' texture.
export function addFrames(scene) {
  const tex = scene.textures.get('atlas');
  for (const [name, [x, y, w, h]] of Object.entries(ATLAS.frames)) {
    if (!tex.has(name)) tex.add(name, 0, x, y, w, h);
  }
}

const DEFAULTS = {
  hero: { weapon: 40, arm_b: 8, shield: -8 },
  knight: { weapon: 35, arm_b: 10, shield: -10 },
};

const rot = (x, y, deg) => {
  const r = deg * Math.PI / 180, c = Math.cos(r), s = Math.sin(r);
  return [x * c - y * s, x * s + y * c];
};

export class Rig {
  // kind: 'hero' or 'knight' (the rig table); frames: {part: atlas frame name}
  constructor(scene, kind, frames, x = 0, y = 0) {
    const R = ATLAS.rigs[kind];
    this.kind = kind;
    this.at = R.at; this.hand = R.hand; this.order = R.order.filter(k => frames[k]);
    this.defaults = DEFAULTS[kind] || {};
    this.c = scene.add.container(x, y);
    this.parts = {};
    for (const key of this.order) {
      const name = frames[key];
      const [, , w, h, px, py] = ATLAS.frames[name];
      const im = scene.add.image(0, 0, 'atlas', name).setOrigin(px / w, py / h);
      this.parts[key] = im;
      this.c.add(im);
    }
    this.front = false;
    this.flash = 0;
  }

  setFrame(key, name) {
    const im = this.parts[key];
    if (!im || !ATLAS.frames[name]) return;
    const [, , w, h, px, py] = ATLAS.frames[name];
    im.setFrame(name).setOrigin(px / w, py / h);
  }

  // p: a pose (part angles, lean, dy, front); left: face left
  pose(p, left) {
    const d = this.defaults, g = k => (p[k] ?? d[k] ?? 0);
    const at = this.at, P = this.parts;
    const bx = Math.round(g('lean')), by = Math.round(g('dy'));
    const torsoA = g('torso');
    const tp = [at.torso[0] + bx, at.torso[1] + by];
    const place = (key, x, y, a) => { const im = P[key]; if (im) { im.x = Math.round(x); im.y = Math.round(y); im.angle = a; } };
    place('leg_b', at.leg_b[0], at.leg_b[1], g('leg_b'));
    place('leg_f', at.leg_f[0], at.leg_f[1], g('leg_f'));
    place('torso', tp[0], tp[1], torsoA);
    const off = key => { const [ox, oy] = rot(at[key][0] - at.torso[0], at[key][1] - at.torso[1], torsoA); return [tp[0] + ox, tp[1] + oy]; };
    const head = off('head'); place('head', head[0], head[1] + (p.headDy || 0), torsoA + g('head'));
    const cape = off('cape'); place('cape', cape[0], cape[1], torsoA + g('cape'));
    const af = off('arm_f'), afA = torsoA + g('arm_f');
    const ab = off('arm_b'), abA = torsoA + g('arm_b');
    place('arm_f', af[0], af[1], afA);
    place('arm_b', ab[0], ab[1], abA);
    const [hx, hy] = rot(this.hand[0], this.hand[1], afA);
    place('weapon', af[0] + hx, af[1] + hy, afA + g('weapon'));
    const [sx, sy] = rot(this.hand[0], this.hand[1], abA);
    place('shield', ab[0] + sx, ab[1] + sy, abA + g('shield'));
    if (P.shield && !!p.front !== this.front) {
      this.front = !!p.front;
      this.c.remove(P.shield);
      const before = this.front ? 'weapon' : 'arm_b';
      const idx = P[before] ? this.c.getIndex(P[before]) : this.c.length;
      this.c.addAt(P.shield, Math.max(0, idx));
    }
    this.c.scaleX = left ? -1 : 1;
  }

  // world position of the weapon's tip (for trails), given the container's state
  setTint(colour) {
    for (const im of Object.values(this.parts)) colour == null ? im.clearTint() : im.setTintFill(colour);
  }

  destroy() { this.c.destroy(); }
}

// Interpolate a keyframe list [[t, pose], ...] at time t. Missing angles use the rig's defaults.
export function sample(keys, t, defaults = {}) {
  if (!keys || !keys.length) return {};
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, p1] = keys[i];
    if (t <= t1) {
      const [t0, p0] = keys[i - 1];
      const u = (t - t0) / Math.max(1e-6, t1 - t0);
      const k = u * u * (3 - 2 * u);
      const out = {};
      for (const key of new Set([...Object.keys(p0), ...Object.keys(p1)])) {
        if (key === 'front' || key === 'run') { out[key] = u < 0.5 ? p0[key] : p1[key]; continue; }
        const a = p0[key] ?? defaults[key] ?? 0, b = p1[key] ?? defaults[key] ?? 0;
        out[key] = a + (b - a) * k;
      }
      return out;
    }
  }
  return keys[keys.length - 1][1];
}

export function runCycle(phase, amp = 1) {
  const s = Math.sin(phase);
  return { leg_f: 32 * s * amp, leg_b: -32 * s * amp, arm_b: -22 * s * amp, dy: -Math.abs(Math.cos(phase)) * 1.5 * amp, cape: 14 * amp + 6 * s * amp, torso: 4 * amp };
}

export const rigDefaults = kind => DEFAULTS[kind] || {};

// Draws a rig into a 2D canvas (lobby portraits), with the same hierarchy as Rig.pose.
export function paintRig(g, img, kind, frames, p, ox, oy) {
  const R = ATLAS.rigs[kind], at = R.at, d = DEFAULTS[kind] || {}, val = k => (p[k] ?? d[k] ?? 0);
  const tA = val('torso'), tp = [at.torso[0], at.torso[1]];
  const off = k => { const [x, y] = rot(at[k][0] - at.torso[0], at[k][1] - at.torso[1], tA); return [tp[0] + x, tp[1] + y]; };
  const af = off('arm_f'), afA = tA + val('arm_f'), ab = off('arm_b'), abA = tA + val('arm_b');
  const [hx, hy] = rot(R.hand[0], R.hand[1], afA), [sx, sy] = rot(R.hand[0], R.hand[1], abA);
  const place = {
    leg_b: [at.leg_b, val('leg_b')], leg_f: [at.leg_f, val('leg_f')], torso: [tp, tA], head: [off('head'), tA + val('head')],
    cape: [off('cape'), tA + val('cape')], arm_f: [af, afA], arm_b: [ab, abA],
    weapon: [[af[0] + hx, af[1] + hy], afA + val('weapon')], shield: [[ab[0] + sx, ab[1] + sy], abA + val('shield')],
  };
  for (const key of R.order) {
    const name = frames[key];
    if (!name || !ATLAS.frames[name]) continue;
    const [fx, fy, w, h, px, py] = ATLAS.frames[name];
    const [[x, y], a] = place[key];
    g.save(); g.translate(ox + Math.round(x), oy + Math.round(y)); g.rotate(a * Math.PI / 180);
    g.drawImage(img, fx, fy, w, h, -px, -py, w, h);
    g.restore();
  }
}
