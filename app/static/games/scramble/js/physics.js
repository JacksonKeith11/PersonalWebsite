// Scramble's physics: one player against a course. No DOM here, so tools/scramble-check.mjs can
// run it in Node to prove the courses can be finished. The course data is described in
// app/scramble/course.py; RUN must match the number there (the bots run at it).
//
// A player is a PW x PH box; (x, y) is the middle of its feet. y points down.

export const RUN = 300, GRAV = 2000, JUMP = 760, PAD_V = 1150, MAX_FALL = 1200;
export const PW = 28, PH = 40, DT = 1 / 120;
export const SPIKE_H = 18, PIT = 520;   // fall below PIT and you're out
export const CRUMBLE = 0.5, CRUMBLE_H = 26;   // seconds a crumbling block holds once stood on
export const BELT_H = 24, BLINK_H = 22;
export const DASH_V = 560, DASH_T = 0.16;   // the air dash: this fast, for this long, once per jump
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
    belts: (c.belts || []).map(([x, y, w, v]) => ({ x, y, w, v })),
    blinks: (c.blinks || []).map(([x, y, w, period, phase]) => ({ x, y, w, period, phase })),
    winds: (c.winds || []).map(([x, y, w, h, v, period, phase]) => ({ x, y, w, h, v, period, phase })),
    lavas: (c.lavas || []).map(([x0, x1, trigger, base, rate, cap]) => ({ x0, x1, trigger, base, rate, cap })),
    traps: [],   // dropped by players: { id, x, y, w, owner }, kept up to date by main.js
  };
}

// Where a mover or saw is at time t: it swings dx, dy either side of its home.
const sway = (o, t) => Math.sin(2 * Math.PI * t / o.period + o.phase);
export const posX = (o, t) => o.x + o.dx * sway(o, t);
export const posY = (o, t) => o.y + o.dy * sway(o, t);
// A blinking platform is there for the first half of each period.
export const blinkOn = (b, t) => ((t / b.period + b.phase) % 1 + 1) % 1 < 0.5;
// A gust blows while its sway is positive (a period of 0: always).
export const gusting = (w, t) => !w.period || Math.sin(2 * Math.PI * t / w.period + w.phase) > 0;
// Rising lava's surface for this player: it starts rising when they pass its trigger.
export const lavaTop = (p, l, i, t) => (p.lava[i] == null ? l.base : Math.max(l.cap, l.base - l.rate * (t - p.lava[i])));

// A fresh player at a flag. `stood` is when they first stood on each crumbling block (by index), and
// `lava` when they set each rising lava going; they're replaced rather than changed, so copies of a
// player (the checker's search) don't share them. `speed` scales running (freeze and boost: main.js
// sets it). `dashT` is how long the current dash has left; `canDash` comes back on landing.
export function spawn(c, cp = 0) {
  return { x: c.segs[cp] + 60, y: -1, vx: 0, vy: 0, ground: false, on: -1, belt: 0, coyote: 0, buffer: 0,
    held: false, jumping: false, dead: false, cp, face: 1, stood: {}, lava: {}, speed: 1,
    dashT: 0, canDash: true, dashHeld: false };
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

// Advance `p` by DT at course time `t`. `inp` is { dir: -1 | 0 | 1, jump: held?, dash: held? }.
export function step(p, inp, t, c) {
  if (p.dead) return;
  const dt = DT;
  if (p.on >= 0) {   // ride the platform underfoot
    const m = c.movers[p.on];
    p.x += posX(m, t) - posX(m, t - dt);
    p.y += posY(m, t) - posY(m, t - dt);
  }
  if (p.belt) p.x += p.belt * dt;   // and the belt
  for (const w of c.winds) {   // and the wind
    if (gusting(w, t) && p.x + HALF > w.x && p.x - HALF < w.x + w.w && p.y > w.y && p.y - PH < w.y + w.h) p.x += w.v * dt;
  }
  const acc = (p.ground ? 3000 : 1800) * dt, want = inp.dir * RUN * (p.speed ?? 1) - p.vx;
  if (inp.dir) p.face = inp.dir;

  // the air dash: a press in the air sends you level and fast for a moment, once until you land
  if (inp.dash && !p.dashHeld && !p.ground && p.canDash && !p.dashT) {
    p.dashT = DASH_T;
    p.canDash = false;
    p.vx = p.face * DASH_V * Math.max(1, p.speed ?? 1);
    p.jumping = false;
  }
  p.dashHeld = !!inp.dash;
  if (p.dashT) {
    p.dashT = Math.max(0, p.dashT - dt);
    p.vy = 0;
  } else {
    p.vx += Math.max(-acc, Math.min(acc, want));
  }

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
  if (!p.dashT) p.vy = Math.min(p.vy + GRAV * dt, MAX_FALL);

  p.x += p.vx * dt;
  for (const s of c.plats) if (blocks(p, s.x, s.y, s.w, s.h)) pushX(p, s.x, s.w);
  for (const s of c.belts) if (blocks(p, s.x, s.y, s.w, BELT_H)) pushX(p, s.x, s.w);
  for (const s of c.blinks) if (blinkOn(s, t) && blocks(p, s.x, s.y, s.w, BLINK_H)) pushX(p, s.x, s.w);
  c.crumbles.forEach((s, i) => { if (standing(p, i, t) && blocks(p, s.x, s.y, s.w, CRUMBLE_H)) pushX(p, s.x, s.w); });
  for (const m of c.movers) { const x = posX(m, t), y = posY(m, t); if (blocks(p, x, y, m.w, m.h)) pushX(p, x, m.w); }
  p.x = Math.max(HALF, p.x);

  p.y += p.vy * dt;
  p.ground = false;
  p.on = -1;
  p.belt = 0;
  for (const s of c.plats) if (hits(p, s.x, s.y, s.w, s.h)) pushY(p, s.y, s.h, -1);
  for (const s of c.belts) {
    if (!hits(p, s.x, s.y, s.w, BELT_H)) continue;
    pushY(p, s.y, BELT_H, -1);
    if (p.ground && p.y === s.y) p.belt = s.v;
  }
  for (const s of c.blinks) if (blinkOn(s, t) && hits(p, s.x, s.y, s.w, BLINK_H)) pushY(p, s.y, BLINK_H, -1);
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
      p.canDash = true;
      p.dashT = 0;
    }
  }
  for (const s of c.spikes) if (hits(p, s.x + 5, s.y - SPIKE_H + 5, s.w - 10, SPIKE_H)) p.dead = true;
  for (const s of c.traps) if (s.owner !== p.id && hits(p, s.x + 5, s.y - SPIKE_H + 5, s.w - 10, SPIKE_H)) p.dead = true;
  for (const s of c.saws) {
    const sx = posX(s, t), sy = posY(s, t);
    const nx = Math.max(p.x - HALF, Math.min(sx, p.x + HALF)), ny = Math.max(p.y - PH, Math.min(sy, p.y));
    if ((sx - nx) ** 2 + (sy - ny) ** 2 < (s.r - 3) ** 2) p.dead = true;
  }
  c.lavas.forEach((l, i) => {
    if (p.lava[i] == null && p.x >= l.trigger) p.lava = { ...p.lava, [i]: t };
    if (p.x + HALF > l.x0 && p.x - HALF < l.x1 && p.y > lavaTop(p, l, i, t) + 6) p.dead = true;
  });
  if (p.y > PIT) p.dead = true;
  if (p.ground) { p.canDash = true; p.dashT = 0; }   // landing ends a dash and gives it back
  if (p.dashT && p.vx === 0) p.dashT = 0;   // dashed into a wall
  if (p.ground) while (p.cp + 1 < c.segs.length && p.x >= c.segs[p.cp + 1] + 30) p.cp++;
}
