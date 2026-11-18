// Scramble's physics: one player against a course. No DOM here, so tools/scramble-check.mjs can
// run it in Node to prove the courses can be finished. The course data is described in
// app/scramble/course.py; RUN must match the number there (the bots run at it).
//
// A player is a PW x PH box; (x, y) is the middle of its feet. y points down.

export const RUN = 300, GRAV = 2000, JUMP = 760, PAD_V = 1150, MAX_FALL = 1200;
export const PW = 28, PH = 40, DT = 1 / 120;
export const SPIKE_H = 18, PIT = 520;   // fall below PIT and you're out
export const CRUMBLE = 0.5, CRUMBLE_H = 26;   // seconds a crumbling block holds once stood on
const HALF = PW / 2;

// Turn the server's arrays into objects.
export function prepare(c) {
  const swing = ([x, y, a, b, dx, dy, period, phase]) => ({ x, y, a, b, dx, dy, period, phase });
  return {
    ...c,
    plats: c.plats.map(([x, y, w, h]) => ({ x, y, w, h })),
    movers: c.movers.map(v => { const m = swing(v); return { ...m, w: m.a, h: m.b }; }),
    saws: c.saws.map(([x, y, r, dx, dy, period, phase]) => ({ x, y, r, dx, dy, period, phase })),
    spikes: c.spikes.map(([x, y, w]) => ({ x, y, w })),
    pads: c.pads.map(([x, y, w]) => ({ x, y, w })),
    crumbles: (c.crumbles || []).map(([x, y, w]) => ({ x, y, w })),
    traps: [],   // dropped by players: { id, x, y, w, owner }, kept up to date by main.js
  };
}

// Where a mover or saw is at time t: it swings dx, dy either side of its home.
const sway = (o, t) => Math.sin(2 * Math.PI * t / o.period + o.phase);
export const posX = (o, t) => o.x + o.dx * sway(o, t);
export const posY = (o, t) => o.y + o.dy * sway(o, t);

// A fresh player at a flag. `stood` is when they first stood on each crumbling block (by index); it's
// replaced rather than changed, so copies of a player (the checker's search) don't share it.
// `speed` scales running (freeze and boost: main.js sets it).
export function spawn(c, cp = 0) {
  return { x: c.segs[cp] + 60, y: -1, vx: 0, vy: 0, ground: false, on: -1, coyote: 0, buffer: 0,
    held: false, jumping: false, dead: false, cp, face: 1, stood: {}, speed: 1 };
}

// Is crumbling block i still there for this player at time t?
export const standing = (p, i, t) => p.stood[i] == null || t - p.stood[i] < CRUMBLE;

const hits = (p, x, y, w, h) => p.x + HALF > x && p.x - HALF < x + w && p.y > y && p.y - PH < y + h;

// The same, sideways: feet resting on (or a hair into) a surface don't count as running into it.
const blocks = (p, x, y, w, h) => p.x + HALF > x && p.x - HALF < x + w && p.y - 3 > y && p.y - PH < y + h;

function pushX(p, x, w) {
  p.x = p.x < x + w / 2 ? x - HALF : x + w + HALF;
  p.vx = 0;
}

function pushY(p, y, h, mover) {
  if (p.y - PH / 2 < y + h / 2) {   // landed on top
    p.y = y;
    if (p.vy > 0) p.vy = 0;
    p.ground = true;
    p.on = mover;
  } else {                          // bumped its underside
    p.y = y + h + PH;
    if (p.vy < 0) p.vy = 0;
  }
}

// Advance `p` by DT at course time `t`. `inp` is { dir: -1 | 0 | 1, jump: held? }.
export function step(p, inp, t, c) {
  if (p.dead) return;
  const dt = DT;
  if (p.on >= 0) {   // ride the platform underfoot
    const m = c.movers[p.on];
    p.x += posX(m, t) - posX(m, t - dt);
    p.y += posY(m, t) - posY(m, t - dt);
  }
  const acc = (p.ground ? 3000 : 1800) * dt, want = inp.dir * RUN * (p.speed ?? 1) - p.vx;
  p.vx += Math.max(-acc, Math.min(acc, want));
  if (inp.dir) p.face = inp.dir;

  // a jump pressed a moment early, or a moment after running off an edge, still counts
  p.buffer = inp.jump && !p.held ? 0.12 : Math.max(0, p.buffer - dt);
  p.held = inp.jump;
  p.coyote = p.ground ? 0.09 : Math.max(0, p.coyote - dt);
  if (p.buffer > 0 && p.coyote > 0) {
    p.vy = -JUMP;
    p.buffer = p.coyote = 0;
    p.jumping = true;
  }
  if (p.jumping && !inp.jump && p.vy < -260) p.vy = -260;   // let go early for a short hop
  if (p.vy >= 0) p.jumping = false;
  p.vy = Math.min(p.vy + GRAV * dt, MAX_FALL);

  p.x += p.vx * dt;
  for (const s of c.plats) if (blocks(p, s.x, s.y, s.w, s.h)) pushX(p, s.x, s.w);
  c.crumbles.forEach((s, i) => { if (standing(p, i, t) && blocks(p, s.x, s.y, s.w, CRUMBLE_H)) pushX(p, s.x, s.w); });
  for (const m of c.movers) { const x = posX(m, t), y = posY(m, t); if (blocks(p, x, y, m.w, m.h)) pushX(p, x, m.w); }
  p.x = Math.max(HALF, p.x);

  p.y += p.vy * dt;
  p.ground = false;
  p.on = -1;
  for (const s of c.plats) if (hits(p, s.x, s.y, s.w, s.h)) pushY(p, s.y, s.h, -1);
  c.crumbles.forEach((s, i) => {
    if (!standing(p, i, t) || !hits(p, s.x, s.y, s.w, CRUMBLE_H)) return;
    pushY(p, s.y, CRUMBLE_H, -1);
    if (p.ground && p.y === s.y && p.stood[i] == null) p.stood = { ...p.stood, [i]: t };
  });
  for (let i = 0; i < c.movers.length; i++) {
    const m = c.movers[i], x = posX(m, t), y = posY(m, t);
    if (hits(p, x, y, m.w, m.h)) pushY(p, y, m.h, i);
  }

  for (const s of c.pads) {
    if (p.vy >= 0 && p.x > s.x - 4 && p.x < s.x + s.w + 4 && p.y >= s.y - 8 && p.y <= s.y + 6) {
      p.vy = -PAD_V;
      p.jumping = false;
      p.ground = false;
      p.on = -1;
      p.sprung = t;
    }
  }
  for (const s of c.spikes) if (hits(p, s.x + 5, s.y - SPIKE_H + 5, s.w - 10, SPIKE_H)) p.dead = true;
  for (const s of c.traps) if (s.owner !== p.id && hits(p, s.x + 5, s.y - SPIKE_H + 5, s.w - 10, SPIKE_H)) p.dead = true;
  for (const s of c.saws) {
    const sx = posX(s, t), sy = posY(s, t);
    const nx = Math.max(p.x - HALF, Math.min(sx, p.x + HALF)), ny = Math.max(p.y - PH, Math.min(sy, p.y));
    if ((sx - nx) ** 2 + (sy - ny) ** 2 < (s.r - 3) ** 2) p.dead = true;
  }
  if (p.y > PIT) p.dead = true;
  if (p.ground) while (p.cp + 1 < c.segs.length && p.x >= c.segs[p.cp + 1] + 30) p.cp++;
}
