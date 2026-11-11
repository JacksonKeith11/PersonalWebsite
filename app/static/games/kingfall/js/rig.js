// Cutout rigs: a character is a Phaser container of part images from the atlas, posed by rotating
// each part around its pivot. The rig tables come from atlas.json (tools/kingfall-art/rigs.py): each
// part has a parent and its pivot's rest position, relative to the feet. 'ground' parts stay put,
// 'body' parts move with the pose's lean/dy, and other parts are carried round by their parent.
// Everything is drawn facing right; facing left flips the container. Angles are degrees, clockwise.

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

const rot = (x, y, deg) => {
  const r = deg * Math.PI / 180, c = Math.cos(r), s = Math.sin(r);
  return [x * c - y * s, x * s + y * c];
};

// {part: [x, y, angle]} for a pose (part angles; lean, dy; <part>_x/_y nudges along the parent's frame)
export function solve(R, p) {
  const d = R.defaults, g = k => (p[k] ?? d[k] ?? 0), out = {};
  const place = k => {
    if (out[k]) return out[k];
    const [parent, x, y] = R.parts[k], nx = g(k + '_x'), ny = g(k + '_y');
    if (parent === 'ground') out[k] = [x + nx, y + ny, g(k)];
    else if (parent === 'body') out[k] = [x + Math.round(g('lean')) + nx, y + Math.round(g('dy')) + ny, g(k)];
    else {
      const [px, py, pa] = place(parent), [, ax, ay] = R.parts[parent];
      const [ox, oy] = rot(x - ax + nx, y - ay + ny, pa);
      out[k] = [px + ox, py + oy, pa + g(k)];
    }
    return out[k];
  };
  for (const k of Object.keys(R.parts)) place(k);
  return out;
}

export function drawOrder(R, p, has) {
  const o = R.order.slice();
  for (const [k, [back, front]] of Object.entries(R.front || {})) {
    const i = o.indexOf(k);
    if (i < 0) continue;
    o.splice(i, 1);
    const before = p.front ? front : back, j = o.indexOf(before);
    o.splice(j < 0 ? o.length : j, 0, k);
  }
  return o.filter(has);
}

export class Rig {
  // kind: a rig table's name; frames: {part: atlas frame name}
  constructor(scene, kind, frames, x = 0, y = 0) {
    this.R = ATLAS.rigs[kind];
    this.kind = kind;
    this.c = scene.add.container(x, y);
    this.parts = {};
    for (const key of this.R.order) {
      const name = frames[key];
      if (!name || !ATLAS.frames[name]) continue;
      const [, , w, h, px, py] = ATLAS.frames[name];
      const im = scene.add.image(0, 0, 'atlas', name).setOrigin(px / w, py / h);
      this.parts[key] = im;
      this.c.add(im);
    }
    this.orderKey = '';
  }

  get defaults() { return this.R.defaults; }

  setFrame(key, name) {
    const im = this.parts[key];
    if (!im || !ATLAS.frames[name]) return;
    const [, , w, h, px, py] = ATLAS.frames[name];
    im.setFrame(name).setOrigin(px / w, py / h);
  }

  // p: a pose; left: face left
  pose(p, left) {
    const at = solve(this.R, p);
    for (const [k, im] of Object.entries(this.parts)) {
      const [x, y, a] = at[k];
      im.x = Math.round(x); im.y = Math.round(y); im.angle = a;
      im.visible = !p[k + '_hide'];
    }
    const key = p.front ? 'f' : 'b';
    if (key !== this.orderKey) {
      this.orderKey = key;
      drawOrder(this.R, p, k => this.parts[k]).forEach((k, i) => this.c.moveTo(this.parts[k], i));
    }
    this.c.scaleX = left ? -1 : 1;
  }

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
      // a quick key (a strike) snaps out and settles; a slow one (a wind-up, a recovery) eases both ways
      const k = t1 - t0 < 0.2 ? 1 - (1 - u) * (1 - u) * (1 - u) : u * u * (3 - 2 * u);
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

export const rigDefaults = kind => (ATLAS.rigs[kind] || {}).defaults || {};

// Draws a rig into a 2D canvas (lobby portraits), posed as Rig.pose does.
export function paintRig(g, img, kind, frames, p, ox, oy) {
  const R = ATLAS.rigs[kind], at = solve(R, p);
  for (const key of drawOrder(R, p, k => frames[k] && ATLAS.frames[frames[k]])) {
    const [fx, fy, w, h, px, py] = ATLAS.frames[frames[key]];
    const [x, y, a] = at[key];
    g.save(); g.translate(ox + Math.round(x), oy + Math.round(y)); g.rotate(a * Math.PI / 180);
    g.drawImage(img, fx, fy, w, h, -px, -py, w, h);
    g.restore();
  }
}
