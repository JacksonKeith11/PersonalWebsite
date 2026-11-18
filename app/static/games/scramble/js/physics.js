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
// What some themes do underfoot: snow is ice (slow to speed up, slow to stop), and in the dunes sand
// slows running on the ground (hop to keep your speed). course.py's bots know these numbers too.
export const ICE_ACC = 700, SAND = 0.8;
export const BAR_R = 9, BULLET_R = 9, RING_R = 20, BARREL_R = 24, FLING = 0.45, LEDGE_H = 12, PORTAL_R = 22;
export const LOW_G = 0.5, GOO = 0.45, UPDRAFT = 1100, UPDRAFT_V = 480;   // zones: low gravity, goo, updrafts
export const HONEY = 0.35, HONEY_W = 90, PLANK_W = 150, PLANK_H = 16;   // placed items (game.py too)
export const ARROW_V = 450, ARROW_GAP = 1.4, ARROW_RANGE = 650, FAN_W = 380, FAN_V = 230, HOLE_R = 210, HOLE_CORE = 20, HOLE_PULL = 190;
const HALF = PW / 2;

// Turn the server's arrays into objects.
export function prepare(c) {
  const swing = ([x, y, w, h, dx, dy, period, phase, kind = 0]) => ({ x, y, w, h, dx, dy, period, phase, kind });
  return {
    ...c,
    plats: c.plats.map(([x, y, w, h, look = 0]) => ({ x, y, w, h, look })),
    movers: c.movers.map(swing),
    saws: c.saws.map(([x, y, r, dx, dy, period, phase, kind = 0, look = 0]) => ({ x, y, r, dx, dy, period, phase, kind, look })),
    spikes: c.spikes.map(([x, y, w]) => ({ x, y, w })),
    pads: c.pads.map(([x, y, w, v = PAD_V]) => ({ x, y, w, v })),
    crumbles: (c.crumbles || []).map(([x, y, w]) => ({ x, y, w })),
    belts: (c.belts || []).map(([x, y, w, v]) => ({ x, y, w, v })),
    blinks: (c.blinks || []).map(([x, y, w, period, phase, look = 0]) => ({ x, y, w, period, phase, look })),
    winds: (c.winds || []).map(([x, y, w, h, v, period, phase]) => ({ x, y, w, h, v, period, phase })),
    lavas: (c.lavas || []).map(([x0, x1, trigger, base, rate, cap]) => ({ x0, x1, trigger, base, rate, cap })),
    bars: (c.bars || []).map(([x, y, len, n, period, phase, arms = 1]) => ({ x, y, len, n, period, phase, arms })),
    crushers: (c.crushers || []).map(v => { const m = swing(v); if (v.length < 9) m.kind = 3; return m; }),
    cannons: (c.cannons || []).map(([x, y, vx, vy, period, phase, range]) => ({ x, y, vx, vy, period, phase, range })),
    jets: (c.jets || []).map(([x, y, w, h, period, phase, duty, look = 0]) => ({ x, y, w, h, period, phase, duty, look })),
    rings: (c.rings || []).map(([x, y]) => ({ x, y })),
    barrels: (c.barrels || []).map(([x, y, angle, swing, period, phase, speed, auto]) => ({ x, y, angle, swing, period, phase, speed, auto })),
    chasers: (c.chasers || []).map(([x0, x1, trigger, speed]) => ({ x0, x1, trigger, speed })),
    zones: (c.zones || []).map(([x, y, w, h, kind]) => ({ x, y, w, h, kind })),
    ledges: (c.ledges || []).map(([x, y, w]) => ({ x, y, w })),
    portals: (c.portals || []).map(([ax, ay, bx, by]) => ({ ax, ay, bx, by })),
    traps: [],   // dropped by players: { id, x, y, w, owner }, kept up to date by main.js
    props: [],   // placed by players' items: { id, k, x, y, owner, since, until, face }, kept up to date by main.js
  };
}

// Where a mover, saw or crusher is at time t. By its `kind`: 0 swings dx, dy either side of its home;
// 1 goes round an ellipse dx wide and dy high; 2 is a pendulum dx long swinging dy radians either
// way, its home the bottom of the swing; 3 slams (waits, drops dx, dy fast, holds, eases back).
export function slam(u) {
  u = (u % 1 + 1) % 1;
  if (u < 0.4) return 0;
  if (u < 0.48) return ((u - 0.4) / 0.08) ** 2;
  if (u < 0.65) return 1;
  return 1 - (u - 0.65) / 0.35;
}
function offset(o, t) {
  const a = 2 * Math.PI * t / o.period + o.phase;
  switch (o.kind) {
    case 1: return [o.dx * Math.cos(a), o.dy * Math.sin(a)];
    case 2: { const g = o.dy * Math.sin(a); return [o.dx * Math.sin(g), -o.dx * (1 - Math.cos(g))]; }
    case 3: { const s = slam(a / (2 * Math.PI)); return [o.dx * s, o.dy * s]; }
    default: { const s = Math.sin(a); return [o.dx * s, o.dy * s]; }
  }
}
export const posX = (o, t) => o.x + offset(o, t)[0];
export const posY = (o, t) => o.y + offset(o, t)[1];
// The balls of a firebar: `arms` arms of `n` balls from its middle out to `len`, turning once a period.
export function barBalls(b, t) {
  const out = [];
  for (let j = 0; j < b.arms; j++) {
    const a = 2 * Math.PI * t / b.period + b.phase + j * 2 * Math.PI / b.arms;
    for (let i = 0; i < b.n; i++) {
      const d = b.n === 1 ? b.len : 10 + (b.len - 10) * i / (b.n - 1);
      out.push([b.x + Math.cos(a) * d, b.y + Math.sin(a) * d]);
    }
  }
  return out;
}
// A cannon's shots in flight: one fired every period (at (k + phase) periods), each flying `range` px.
export function shots(cn, t) {
  const out = [], v = Math.hypot(cn.vx, cn.vy), life = cn.range / v;
  for (let k = Math.floor(t / cn.period - cn.phase); ; k--) {
    const age = t - (k + cn.phase) * cn.period;
    if (age > life) break;
    if (age >= 0) out.push([cn.x + cn.vx * age, cn.y + cn.vy * age]);
  }
  return out;
}
// A crossbow placed by a player: arrows backwards (away from where they faced) every ARROW_GAP s.
export const crossbow = (pr, t) => shots({ x: pr.x - pr.face * 16, y: pr.y - 20, vx: -pr.face * ARROW_V, vy: 0,
  period: ARROW_GAP, phase: (pr.since + 0.4) / ARROW_GAP, range: ARROW_RANGE }, t).filter(() => t >= pr.since + 0.4);
// A timed jet (flame, pop-up spikes, laser, plant) is out for the first `duty` of each period.
export const jetOn = (j, t) => ((t / j.period + j.phase) % 1 + 1) % 1 < j.duty;
// Which way a barrel points at time t, in radians.
export const barrelAngle = (b, t) => (b.angle + b.swing * Math.sin(2 * Math.PI * t / b.period + b.phase)) * Math.PI / 180;
// A rolling boulder's front for this player: it sets off from x0 when they pass its trigger.
export const chaseFront = (p, ch, i, t) => (p.chase[i] == null ? -1e9 : ch.x0 + ch.speed * (t - p.chase[i]));
export const propOn = (pr, t) => t >= pr.since && t < pr.until;
// The plank a player put down, as a block.
export const plankOf = pr => ({ x: pr.face > 0 ? pr.x + 24 : pr.x - 24 - PLANK_W, y: pr.y, w: PLANK_W, h: PLANK_H });
export const fanOf = pr => ({ x: pr.face > 0 ? pr.x - 10 - FAN_W : pr.x + 10, y: pr.y - 260, w: FAN_W, h: 300, v: -pr.face * FAN_V });
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
    held: false, jumping: false, dead: false, cp, face: 1, stood: {}, lava: {}, chase: {}, speed: 1,
    dashT: 0, canDash: true, dashHeld: false, barrel: -1, barrelT: 0, lastBarrel: -1, lastBarrelT: -9, fling: 0 };
}

// Is crumbling block i still there for this player at time t?
export const standing = (p, i, t) => p.stood[i] == null || t - p.stood[i] < CRUMBLE;

const inside = (p, z) => p.x > z.x && p.x < z.x + z.w && p.y > z.y && p.y - 4 < z.y + z.h;
const touches = (p, x, y, r) => {
  const nx = Math.max(p.x - HALF, Math.min(x, p.x + HALF)), ny = Math.max(p.y - PH, Math.min(y, p.y));
  return (x - nx) ** 2 + (y - ny) ** 2 < r * r;
};
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
  if (p.barrel >= 0) {   // in a barrel: held in it until it fires (a fresh jump press, or by itself)
    const b = c.barrels[p.barrel];
    Object.assign(p, { x: b.x, y: b.y + PH / 2, vx: 0, vy: 0, ground: false, on: -1, belt: 0 });
    const press = inp.jump && !p.held;
    p.held = inp.jump;
    if (!(b.auto ? t - p.barrelT >= 0.25 : press)) return;
    const a = barrelAngle(b, t);
    Object.assign(p, { vx: Math.cos(a) * b.speed, vy: Math.sin(a) * b.speed, fling: FLING, lastBarrel: p.barrel,
      lastBarrelT: t, barrel: -1, jumping: false, buffer: 0, coyote: 0, canDash: true, fired: t });
    if (Math.abs(p.vx) > 1) p.face = Math.sign(p.vx);
  }
  if (p.on >= 0) {   // ride the platform underfoot
    const m = c.movers[p.on];
    p.x += posX(m, t) - posX(m, t - dt);
    p.y += posY(m, t) - posY(m, t - dt);
  }
  if (p.belt) p.x += p.belt * dt;   // and the belt
  for (const w of c.winds) {   // and the wind
    if (gusting(w, t) && p.x + HALF > w.x && p.x - HALF < w.x + w.w && p.y > w.y && p.y - PH < w.y + w.h) p.x += w.v * dt;
  }
  // what's underfoot or around: zones of the course, and what other players put down
  let lowg = false, goo = false, iceZ = false, up = false, honey = false;
  for (const z of c.zones) {
    if (!inside(p, z)) continue;
    if (z.kind === 0) lowg = true; else if (z.kind === 1) goo = true; else if (z.kind === 2) iceZ = true; else up = true;
  }
  const planks = [];
  for (const pr of c.props) {
    if (!propOn(pr, t)) continue;
    if (pr.k === 'plank') { planks.push(plankOf(pr)); continue; }
    if (pr.owner === p.id) continue;
    if (pr.k === 'fan') {
      const f = fanOf(pr);
      if (p.x + HALF > f.x && p.x - HALF < f.x + f.w && p.y > f.y && p.y - PH < f.y + f.h) p.x += f.v * dt;
    } else if (pr.k === 'hole') {
      const dx = pr.x - p.x, dy = pr.y - 95 - (p.y - PH / 2), d = Math.hypot(dx, dy);
      if (d < HOLE_R && d > 1) { const k = HOLE_PULL * (1 - d / HOLE_R) * dt / d; p.x += dx * k; p.y += dy * k; }
    } else if (pr.k === 'honey' && p.ground && Math.abs(p.y - pr.y) < 3 && Math.abs(p.x - pr.x) < HONEY_W / 2) honey = true;
  }
  const ice = c.theme === 'snow' || (iceZ && p.ground), sand = c.theme === 'desert' && p.ground;
  p.fling = Math.max(0, p.fling - dt);
  const acc = (p.ground ? (ice ? ICE_ACC : 3000) : p.fling ? 0 : 1800) * dt;
  const want = inp.dir * RUN * (p.speed ?? 1) * (sand ? SAND : 1) * (goo && p.ground ? GOO : 1) * (honey ? HONEY : 1) - p.vx;
  if (inp.dir && !p.fling) p.face = inp.dir;

  // the air dash: a press in the air sends you level and fast for a moment, once until you land
  if (inp.dash && !p.dashHeld && !p.ground && p.canDash && !p.dashT) {
    p.dashT = DASH_T;
    p.canDash = false;
    p.fling = 0;
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
  if (p.buffer > 0) {   // a jump ring: touch one with a jump pressed and you jump again in mid-air
    for (const r of c.rings) {
      if (!touches(p, r.x, r.y, RING_R)) continue;
      Object.assign(p, { vy: -JUMP, buffer: 0, jumping: true, canDash: true, dashT: 0, fling: 0, ringT: t });
      break;
    }
  }
  if (p.jumping && !inp.jump && p.vy < -260) p.vy = -260;   // let go early for a short hop
  if (p.vy >= 0) p.jumping = false;
  if (!p.dashT) {
    if (up) p.vy = p.vy < -UPDRAFT_V ? p.vy + GRAV * dt : Math.max(p.vy - UPDRAFT * dt, -UPDRAFT_V);
    else p.vy = Math.min(p.vy + GRAV * (lowg ? LOW_G : 1) * dt, MAX_FALL);
  }

  p.x += p.vx * dt;
  for (const s of c.plats) if (blocks(p, s.x, s.y, s.w, s.h)) pushX(p, s.x, s.w);
  for (const s of planks) if (blocks(p, s.x, s.y, s.w, s.h)) pushX(p, s.x, s.w);
  for (const s of c.belts) if (blocks(p, s.x, s.y, s.w, BELT_H)) pushX(p, s.x, s.w);
  for (const s of c.blinks) if (blinkOn(s, t) && blocks(p, s.x, s.y, s.w, BLINK_H)) pushX(p, s.x, s.w);
  c.crumbles.forEach((s, i) => { if (standing(p, i, t) && blocks(p, s.x, s.y, s.w, CRUMBLE_H)) pushX(p, s.x, s.w); });
  for (const m of c.movers) { const x = posX(m, t), y = posY(m, t); if (blocks(p, x, y, m.w, m.h)) pushX(p, x, m.w); }
  p.x = Math.max(HALF, p.x);

  const y0 = p.y;
  p.y += p.vy * dt;
  p.ground = false;
  p.on = -1;
  p.belt = 0;
  for (const s of c.plats) if (hits(p, s.x, s.y, s.w, s.h)) pushY(p, s.y, s.h, -1);
  for (const s of planks) if (hits(p, s.x, s.y, s.w, s.h)) pushY(p, s.y, s.h, -1);
  for (const s of c.ledges) {   // one-way: you jump up through them and land on top
    if (p.vy >= 0 && y0 <= s.y + 0.01 && p.y >= s.y && p.x + HALF > s.x && p.x - HALF < s.x + s.w) {
      p.y = s.y;
      p.vy = 0;
      p.ground = true;
    }
  }
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
      p.vy = -s.v;
      p.jumping = false;
      p.ground = false;
      p.on = -1;
      p.sprung = t;
      p.canDash = true;
      p.dashT = 0;
    }
  }
  if (p.barrel < 0) {   // into a barrel (not straight back into the one just left)
    c.barrels.forEach((b, i) => {
      if (p.barrel >= 0 || (i === p.lastBarrel && t - p.lastBarrelT < 0.4) || !touches(p, b.x, b.y, BARREL_R)) return;
      Object.assign(p, { barrel: i, barrelT: t, vx: 0, vy: 0, dashT: 0, canDash: true, fling: 0, ground: false, jumping: false });
    });
  }
  for (const pt of c.portals) {   // through a portal: out of the other end, still moving
    if (t - (p.portT ?? -9) > 0.3 && touches(p, pt.ax, pt.ay, PORTAL_R)) {
      Object.assign(p, { x: pt.bx, y: pt.by + PH / 2, portT: t, on: -1, ground: false });
      break;
    }
  }
  // what kills
  for (const s of c.spikes) if (hits(p, s.x + 5, s.y - SPIKE_H + 5, s.w - 10, SPIKE_H)) p.dead = true;
  for (const s of c.traps) if (s.owner !== p.id && hits(p, s.x + 5, s.y - SPIKE_H + 5, s.w - 10, SPIKE_H)) p.dead = true;
  for (const s of c.saws) if (touches(p, posX(s, t), posY(s, t), s.r - 3)) p.dead = true;
  for (const b of c.bars) for (const [x, y] of barBalls(b, t)) if (touches(p, x, y, BAR_R - 2)) p.dead = true;
  for (const cn of c.cannons) for (const [x, y] of shots(cn, t)) if (touches(p, x, y, BULLET_R - 2)) p.dead = true;
  for (const m of c.crushers) if (hits(p, posX(m, t) + 3, posY(m, t) + 3, m.w - 6, m.h - 6)) p.dead = true;
  for (const j of c.jets) if (jetOn(j, t) && hits(p, j.x + 4, j.y + 4, j.w - 8, j.h - 8)) p.dead = true;
  for (const pr of c.props) {
    if (pr.owner === p.id || !propOn(pr, t)) continue;
    if (pr.k === 'crossbow') { for (const [x, y] of crossbow(pr, t)) if (touches(p, x, y, 7)) p.dead = true; }
    else if (pr.k === 'hole' && touches(p, pr.x, pr.y - 95, HOLE_CORE)) p.dead = true;
  }
  c.lavas.forEach((l, i) => {
    if (p.lava[i] == null && p.x >= l.trigger) p.lava = { ...p.lava, [i]: t };
    if (p.x + HALF > l.x0 && p.x - HALF < l.x1 && p.y > lavaTop(p, l, i, t) + 6) p.dead = true;
  });
  c.chasers.forEach((ch, i) => {
    if (p.chase[i] == null && p.x >= ch.trigger) p.chase = { ...p.chase, [i]: t };
    if (p.x < ch.x1 && p.x + HALF > ch.x0 && p.x - HALF < chaseFront(p, ch, i, t)) p.dead = true;
  });
  if (p.y > PIT) p.dead = true;
  if (p.ground) { p.canDash = true; p.dashT = 0; p.fling = 0; }   // landing ends a dash and gives it back
  if (p.dashT && p.vx === 0) p.dashT = 0;   // dashed into a wall
  if (p.ground) while (p.cp + 1 < c.segs.length && p.x >= c.segs[p.cp + 1] + 30) p.cp++;
}
