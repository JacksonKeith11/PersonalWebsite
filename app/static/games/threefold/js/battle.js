// Battles: the Phaser scene that draws the board, and the rules, turn loop and AI that drive it.
import { GW, GH, T, TERRAIN, TERRAIN_HELP, THEMES, FOES, CLASSES, SKILLS } from './data.js?v=14';
import { rnd, pick, chance, shuffle, has, isClass, thornsOf, startShield, skStats, describe, statVal, heroStats, heroSprite, heroTitle } from './rules.js?v=14';
import { tileKey, TILE_VARIANTS, ANIMATED, spriteURL } from './art.js?v=14';
import { sfx } from './audio.js?v=14';
import { h, bar, sprImg, tip, tipText } from './ui.js?v=14';

const S = 4, TS = 16 * S;
const DIRS = [[1, 0], [-1, 0], [0, 1], [0, -1]];
const key = (x, y) => x + ',' + y;
const inb = (x, y) => x >= 0 && y >= 0 && x < GW && y < GH;
const dist = (a, b) => Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
const floorish = t => t === T.FLOOR || t === T.COVER || t === T.HILL || t === T.THORN;

// Set by main.js: game, run, speed, autoplay flag and the end-of-battle callback.
export const env = { game: null, run: null, speed: 1, auto: false, onEnd: null, side: null };
const sleep = ms => new Promise(r => setTimeout(r, ms * env.speed));

let B = null;     // battle state
let scene = null; // the live BattleScene

// ---------- setup ----------
export function startBattle({ kind, level, act, list, party }) {
  const grid = genGrid(act.terrain);
  B = { kind, level, theme: act.theme, grid, vari: grid.map(r => r.map(() => rnd(0, 3))), units: [], log: [], mode: null, active: null, frame: 0, uid: 0 };
  const rows = shuffle([...Array(GH).keys()]);
  party.forEach((p, i) => {
    const u = heroUnit(p);
    u.x = i === 0 ? 1 : 0; u.y = rows[i];
    if (u.hp <= 0) { u.hp = 0; u.dead = true; }
    B.units.push(u);
  });
  const spots = shuffle([...Array(GH).keys()].flatMap(y => [GW - 1, GW - 2, GW - 3].map(x => ({ x, y }))))
    .sort((a, b) => (a.x === GW - 3) - (b.x === GW - 3));
  for (const k of list) {
    const u = foeUnit(k, level);
    const s = FOES[k].boss ? { x: GW - 2, y: GH >> 1 } : spots.find(p => !B.units.some(o => o.x === p.x && o.y === p.y) && !(p.x === GW - 2 && p.y === GH >> 1));
    u.x = s.x; u.y = s.y;
    B.grid[u.y][u.x] = B.grid[u.y][u.x] === T.LAVA && !u.fireproof ? T.FLOOR : B.grid[u.y][u.x];
    B.units.push(u);
  }
  env.game.scene.start('battle');
}

function heroUnit(p) {
  const st = heroStats(p, env.run.gold);
  const u = { id: ++B.uid, side: 'hero', ref: p, spr: heroSprite(p), name: heroTitle(p), promo: p.promo, line: p.line || [], ...st, hp: Math.min(p.hp, st.maxHp),
    flank: CLASSES[p.cls].flank || 1.25, items: p.items, skills: p.skills.map(s => ({ id: s.id, mods: s.mods, cd: 0 })), st: {}, shield: 0,
    ct: rnd(0, 30), turns: 0, ai: p.cls === 'mage' ? 'ranged' : 'melee' };
  u.fireproof = isClass(u, 'pyromancer') || has(u, 'lavawalkers');
  u.anchored = isClass(u, 'juggernaut');
  u.slip = isClass(u, 'trickster');
  u.rampart = isClass(u, 'hoplite');
  u.shield = startShield(p, u.maxHp);
  if (isClass(u, 'chronomancer')) u.ct += 60;
  if (has(u, 'stopwatch')) u.ct += 150;
  return u;
}
function foeUnit(kind, lvl) {
  const d = FOES[kind];
  // later acts climb faster, since every hero promotes after each boss
  const act = Math.floor((lvl - 1) / 9);
  const hm = (1 + 0.065 * (lvl - 1)) * (1 + 0.12 * act), sm = (1 + 0.048 * (lvl - 1)) * (1 + 0.08 * act), dp = Math.floor((lvl - 1) / 5);
  const hp = Math.round(d.hp * (d.boss ? 1 + (hm - 1) * 0.75 : hm));
  return { id: ++B.uid, side: 'foe', kind, spr: kind, name: d.name, hp, maxHp: hp, atk: Math.round(d.atk * sm), mag: Math.round((d.mag || 0) * sm),
    def: d.def + dp, res: d.res + dp, spd: d.spd, mov: d.mov, crit: 5, flank: 1.25, items: [], line: [], ai: d.ai || 'melee', st: {}, shield: 0, turns: 0,
    fly: !!d.fly, phase: !!d.phase, fireproof: !!d.fireproof, trail: !!d.trail, boss: !!d.boss, anchored: !!d.boss, lure: !!d.lure, regen: d.regen || 0, scale: d.scale || 1, info: d.info,
    skills: d.skills.map(id => ({ id, mods: [], cd: id === 'e_raise' ? 1 : 0 })), ct: rnd(0, 30) };
}

function genGrid(rc) {
  const span = r => rnd(r[0], r[1]);
  const mid = () => ({ x: rnd(2, GW - 4), y: rnd(0, GH - 1) });
  for (let tries = 0; tries < 300; tries++) {
    const g = Array.from({ length: GH }, () => Array(GW).fill(T.FLOOR));
    const set = (x, y, t) => { if (inb(x, y)) g[y][x] = t; };
    for (let i = span(rc.cover); i > 0; i--) {
      const c = { x: rnd(1, GW - 2), y: rnd(0, GH - 1) };
      for (const [dx, dy] of [[0, 0], ...DIRS, [1, 1], [-1, -1]]) if (chance(0.55)) set(c.x + dx, c.y + dy, T.COVER);
    }
    for (let i = span(rc.hill); i > 0; i--) { const c = { x: rnd(0, GW - 1), y: rnd(0, GH - 1) }; set(c.x, c.y, T.HILL); if (chance(0.5)) set(c.x + 1, c.y, T.HILL); }
    for (let i = span(rc.rock); i > 0; i--) { const c = mid(); set(c.x, c.y, T.ROCK); }
    if (chance(rc.water)) {
      let { x, y } = mid();
      for (let i = rnd(2, 4); i > 0; i--) { if (x >= 2 && x < GW - 3) set(x, y, T.WATER); const [dx, dy] = pick(DIRS); x += dx; y += dy; }
    }
    for (let i = span(rc.walls); i > 0; i--) {
      let { x, y } = mid();
      const [dx, dy] = pick(DIRS);
      for (let j = rnd(2, 4); j > 0; j--) { set(x, y, T.WALL); x += dx; y += dy; if (chance(0.25)) { [x, y] = [x + dy, y + dx]; } }
    }
    for (let i = span(rc.lava); i > 0; i--) {
      let { x, y } = mid();
      for (let j = rnd(1, 3); j > 0; j--) { set(x, y, T.LAVA); const [dx, dy] = pick(DIRS); x += dx; y += dy; }
    }
    for (let i = span(rc.thorn); i > 0; i--) {
      let { x, y } = mid();
      for (let j = rnd(1, 3); j > 0; j--) { set(x, y, T.THORN); const [dx, dy] = pick(DIRS); x += dx; y += dy; }
    }
    for (let y = 0; y < GH; y++) for (const x of [0, 1, GW - 3, GW - 2, GW - 1]) if (![T.FLOOR, T.COVER, T.HILL].includes(g[y][x])) g[y][x] = T.FLOOR;
    const walk = (x, y) => TERRAIN[g[y][x]].cost < Infinity;
    let open = 0;
    for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) if (walk(x, y)) open++;
    const seen = new Set([key(0, 0)]), q = [[0, 0]];
    while (q.length) {
      const [x, y] = q.pop();
      for (const [dx, dy] of DIRS) {
        const nx = x + dx, ny = y + dy;
        if (inb(nx, ny) && walk(nx, ny) && !seen.has(key(nx, ny))) { seen.add(key(nx, ny)); q.push([nx, ny]); }
      }
    }
    if (seen.size === open) return g;
  }
  return Array.from({ length: GH }, () => Array(GW).fill(T.FLOOR));
}

// ---------- queries ----------
const alive = () => B.units.filter(u => !u.dead);
const unitAt = (x, y) => B.units.find(u => !u.dead && u.x === x && u.y === y);
const terr = (x, y) => TERRAIN[B.grid[y][x]];
const spdOf = u => Math.max(1, (u.st.slow > 0 ? Math.floor(u.spd / 2) : u.spd) + ((u.tmp && u.tmp.spd) || 0));
const onHill = u => B.grid[u.y][u.x] === T.HILL && !u.fly;
const inCover = u => B.grid[u.y][u.x] === T.COVER && !u.fly;
const targetable = (u, t) => !((t.st.stealth || t.st.airborne) && t.side !== u.side);
const isHero = u => u.side === 'hero' && u.ref;
// The side a unit really belongs to, under any charm or confusion.
const homeSide = u => u.origSide || u.madSide || u.side;
const DEBUFFS = ['poison', 'burn', 'slow', 'stun', 'blind', 'vuln', 'shock', 'doom', 'sleep', 'confuse', 'root', 'disarm', 'weak', 'oil', 'wet', 'taunt'];
const BUFFS = ['ward', 'guard', 'rally', 'focus', 'stealth', 'thorns', 'movUp', 'imbue', 'riposte'];
const debuffCount = t => DEBUFFS.filter(k => t.st[k] > 0).length;
function log(s) { B.log.push(s); if (B.log.length > 40) B.log.shift(); }

function moveCost(u, x, y) {
  const t = terr(x, y);
  if (t.los) return u.phase ? 1 : Infinity;
  if (u.fly) return 1;
  return t.cost;
}
const standable = (u, x, y) => inb(x, y) && !terr(x, y).los && moveCost(u, x, y) < Infinity;
function hazard(u, x, y) {
  const t = B.grid[y][x];
  if (u.fly) return 0;
  if (t === T.LAVA && !u.fireproof) return Math.round(u.maxHp * 0.12) + 4;
  if (t === T.THORN) return 3 + Math.floor(B.level / 3);
  return 0;
}

function reach(u) {
  const res = new Map([[key(u.x, u.y), { x: u.x, y: u.y, c: 0, prev: null, stop: true, risk: 0 }]]);
  if (u.st && u.st.root > 0) return res;
  const mov = u.mov + (u.st && u.st.movUp > 0 ? 1 : 0);
  if (has(u, 'blink')) {
    for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
      const d = Math.abs(x - u.x) + Math.abs(y - u.y);
      if (d > 0 && d <= mov && standable(u, x, y) && !unitAt(x, y)) res.set(key(x, y), { x, y, c: d, prev: key(u.x, u.y), stop: true, risk: hazard(u, x, y), blink: true });
    }
    return res;
  }
  const q = [[u.x, u.y, 0]];
  while (q.length) {
    q.sort((a, b) => a[2] - b[2]);
    const [x, y, c] = q.shift();
    const cur = res.get(key(x, y));
    if (c > cur.c) continue;
    if (c > 0 && !u.fly && alive().some(o => o.rampart && o.side !== u.side && Math.abs(o.x - x) + Math.abs(o.y - y) === 1)) continue; // Rampart: stop here
    for (const [dx, dy] of DIRS) {
      const nx = x + dx, ny = y + dy;
      if (!inb(nx, ny)) continue;
      const o = unitAt(nx, ny);
      if (o && o.side !== u.side && !u.fly && !u.slip && !u.phase) continue;
      const nc = c + moveCost(u, nx, ny);
      if (nc > mov) continue;
      const k = key(nx, ny), ex = res.get(k);
      if (!ex || nc < ex.c) {
        res.set(k, { x: nx, y: ny, c: nc, prev: key(x, y), stop: !o && standable(u, nx, ny), risk: cur.risk + hazard(u, nx, ny) });
        q.push([nx, ny, nc]);
      }
    }
  }
  return res;
}
function pathTo(res, k) {
  const out = [];
  for (let v = res.get(k); v; v = v.prev ? res.get(v.prev) : null) out.unshift({ x: v.x, y: v.y });
  return out;
}

function los(x0, y0, x1, y1) {
  const n = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0)) * 4;
  for (let i = 1; i < n; i++) {
    const tx = Math.round(x0 + (x1 - x0) * i / n), ty = Math.round(y0 + (y1 - y0) * i / n);
    if ((tx === x0 && ty === y0) || (tx === x1 && ty === y1)) continue;
    if (terr(tx, ty).los) return false;
  }
  return true;
}
const needsLos = o => !o.lob && o.range[1] > 1 && o.tgt !== 'self' && o.shape !== 'line';
function rangeOf(u, o) {
  const [a, b] = o.range;
  return o.tgt !== 'self' && b > 1 && onHill(u) ? [a, b + 1] : [a, b];
}
function inArea(cx, cy, x, y, r, diag) {
  const dx = Math.abs(cx - x), dy = Math.abs(cy - y);
  return diag ? Math.max(dx, dy) <= r : dx + dy <= r;
}
function leapSpot(u, t) {
  let best = null;
  for (const [dx, dy] of DIRS) {
    const x = t.x + dx, y = t.y + dy;
    if (!standable(u, x, y) || (unitAt(x, y) && unitAt(x, y) !== u)) continue;
    const d = Math.abs(x - u.x) + Math.abs(y - u.y) + hazard(u, x, y);
    if (!best || d < best.d) best = { x, y, d };
  }
  return best;
}
const canSwap = (u, t) => t !== u && !t.anchored && standable(t, u.x, u.y) && standable(u, t.x, t.y);

function validTarget(u, o, x, y) {
  if (!inb(x, y)) return false;
  if (o.tgt === 'self') return x === u.x && y === u.y;
  const [a, b] = rangeOf(u, o);
  const d = Math.abs(u.x - x) + Math.abs(u.y - y);
  if (d < a || d > b) return false;
  if (o.shape === 'line' && x !== u.x && y !== u.y) return false;
  if (needsLos(o) && !los(u.x, u.y, x, y)) return false;
  const t = unitAt(x, y);
  if (o.tgt === 'foe' && (!t || t.side === u.side || !targetable(u, t))) return false;
  if (o.tgt === 'ally' && (!t || t.side !== u.side || (o.ctGive && t === u))) return false;
  if (o.leap && t && d > 1 && !leapSpot(u, t)) return false;
  if (o.swap && t && !canSwap(u, t)) return false;
  if (o.tgt === 'tile' && terr(x, y).los && !o.aoe) return false;
  if ((o.teleport || o.land) && (unitAt(x, y) || !standable(u, x, y))) return false;
  return true;
}
function hitFilter(u, o) {
  return t => o.hits === 'all' || (o.hits === 'allies' ? t.side === u.side : t.side !== u.side);
}
function lineTiles(u, o, x, y) {
  const dx = Math.sign(x - u.x), dy = Math.sign(y - u.y), out = [];
  const [, b] = rangeOf(u, o);
  for (let i = 1; i <= b; i++) {
    const tx = u.x + dx * i, ty = u.y + dy * i;
    if (!inb(tx, ty) || terr(tx, ty).los) break;
    out.push([tx, ty]);
  }
  return out;
}
// Who a use of skill o at (x,y) hits: [{ t, w }] where w scales the power. expect spreads random picks out as weights.
function hitList(u, o, x, y, expect) {
  const filt = hitFilter(u, o);
  if (o.shape === 'random') {
    const c = alive().filter(t => t.side !== u.side && targetable(u, t));
    if (!c.length) return [];
    return expect ? c.map(t => ({ t, w: 1 / c.length })) : [{ t: pick(c), w: 1 }];
  }
  if (o.shape === 'coin') {
    const side = s => alive().filter(t => (s ? t.side === u.side : t.side !== u.side));
    if (expect) return [...side(false).map(t => ({ t, w: 0.5 })), ...side(true).map(t => ({ t, w: 0.5 }))];
    B.coin = chance(0.5);
    return side(B.coin).map(t => ({ t, w: 1 }));
  }
  if (o.shape === 'math') return alive().filter(t => filt(t) && (o.hits === 'all' || targetable(u, t)) && mathRule(o.rule, t)).map(t => ({ t, w: 1 }));
  if (o.shape === 'multi') {
    const [, b] = rangeOf(u, o);
    const c = alive().filter(t => t.side !== u.side && targetable(u, t) && dist(u, t) <= b && (o.lob || los(u.x, u.y, t.x, t.y)));
    if (!c.length) return [];
    if (expect) return c.map(t => ({ t, w: Math.min(1, o.multiN / c.length) }));
    return Array.from({ length: o.multiN }, () => ({ t: pick(c), w: 1 }));
  }
  if (o.shape === 'line') return lineTiles(u, o, x, y).map(([tx, ty]) => unitAt(tx, ty)).filter(t => t && filt(t)).map(t => ({ t, w: 1 }));
  let out;
  if (o.aoe) {
    const cx = o.tgt === 'self' ? u.x : x, cy = o.tgt === 'self' ? u.y : y;
    out = alive().filter(t => inArea(cx, cy, t.x, t.y, o.aoe, o.diag) && filt(t)).map(t => ({ t, w: 1 }));
  } else {
    const t = unitAt(x, y);
    out = t ? [{ t, w: 1 }] : [];
  }
  if (o.shape === 'chain' && out.length) {
    let last = out[0].t;
    const seen = new Set([last]);
    for (let i = 0; i < o.chainN; i++) {
      const nxt = alive().filter(t => t.side !== u.side && !seen.has(t) && targetable(u, t) && dist(t, last) <= 3).sort((a, b) => dist(a, last) - dist(b, last))[0];
      if (!nxt) break;
      out.push({ t: nxt, w: o.chainPow });
      seen.add(nxt); last = nxt;
    }
  }
  return out;
}
function areaTiles(u, o, x, y) {
  if (o.shape === 'line') return lineTiles(u, o, x, y);
  if (o.aoe) {
    const cx = o.tgt === 'self' ? u.x : x, cy = o.tgt === 'self' ? u.y : y, out = [];
    for (let ty = 0; ty < GH; ty++) for (let tx = 0; tx < GW; tx++) if (inArea(cx, cy, tx, ty, o.aoe, o.diag)) out.push([tx, ty]);
    return out;
  }
  if (o.shape === 'random' || o.shape === 'multi' || o.shape === 'math' || o.shape === 'coin') return [];
  return [[x, y]];
}

const isPrime = n => { if (n < 2) return false; for (let i = 2; i * i <= n; i++) if (n % i === 0) return false; return true; };
const FIB = new Set([1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377]);
function mathRule(rule, t) {
  if (rule === 'prime') return isPrime(t.hp);
  if (rule === 'even') return t.hp % 2 === 0;
  if (rule === 'grid3') return (t.x + t.y) % 3 === 0;
  if (rule === 'poisoned') return t.st.poison > 0;
  if (rule === 'odd') return t.hp % 2 === 1;
  if (rule === 'square') return Number.isInteger(Math.sqrt(t.hp));
  if (rule === 'fib') return FIB.has(t.hp);
  if (rule === 'evenpos') return (t.x + t.y) % 2 === 0;
  if (rule === 'bramble') return B.grid[t.y][t.x] === T.THORN;
  if (rule === 'all') return true;
  return false;
}

// ---------- damage ----------
const powerVal = (u, o) => statVal(u, o.stat) * o.pow * (o.still && !u.moved ? 1.5 : 1);
const missingFrac = u => Math.max(0, 1 - u.hp / u.maxHp);
const thornsNow = u => thornsOf(u) * ((has(u, 'briarboots') && u.shield > 0) || (isClass(u, 'briarknight') && (u.shield > 0 || u.st.guard)) ? 2 : 1);
const hitsOf = o => o.times || (o.double ? 2 : 1);
function flanked(a, t) { return B.units.some(o => !o.dead && o !== a && o.side === a.side && dist(o, t) === 1); }
function dmgMult(a, t, o) {
  let m = 1;
  if (t.side !== a.side && flanked(a, t)) m *= o.backstab ? 2 : a.flank;
  if (inCover(t) && !has(a, 'concentrate')) m *= 0.8;
  if (onHill(a) && o.range[1] > 1) m *= 1.15;
  if (t.st.guard) m *= 0.6;
  if (t.st.vuln > 0) m *= 1 + (t.st.vulnAmt || 0.3);
  if (a.st.rally > 0) m *= 1.3;
  if (a.side === 'foe' && B.rage) m *= 1 + 0.1 * B.rage;
  if (o.execute && t.hp * 2 < t.maxHp) m *= 2;
  if (has(a, 'monocle')) m *= 1.5;
  if (has(t, 'monocle')) m *= 1.5;
  if (has(a, 'crown')) m *= 1.4;
  if (has(a, 'lantern') && !alive().some(x => x !== a && x.side === a.side && dist(x, a) <= 2)) m *= 1.45;
  if (has(a, 'collar')) m *= 1 + 0.15 * alive().filter(x => x !== a && x.side === a.side && dist(x, a) === 1).length;
  if (has(a, 'frostlocket') && t.st.slow > 0) m *= 1.4;
  if (t.st.shock > 0 && o.kind === 'mag') m *= 1.3;
  if (o.fester && t.st.poison > 0) m *= 1 + o.fester * t.st.poison;
  if (o.shatter && t.st.slow > 0) m *= 1.6;
  if (o.ironbark) m *= 1 + o.ironbark * a.def;
  if (o.sanguine) m *= 1 + missingFrac(a);
  if (isClass(a, 'samurai')) m *= 1 + Math.min(0.6, missingFrac(a) * 0.9);
  if (has(a, 'torc') && a.hp * 2 < a.maxHp) m *= 1.5;
  if (has(a, 'plaguemask') && t.st.poison > 0) m *= 1.25;
  if (has(a, 'tricore') && (t.st.burn > 0 || t.st.slow > 0 || t.st.shock > 0)) m *= 1.35;
  if (has(a, 'pauldron') && a.shield > 0) m *= 1.3;
  if (a.st.weak > 0) m *= 0.7;
  if (a.st.focus > 0) m *= 1.6;
  if (o.perDebuff) m *= 1 + o.perDebuff * debuffCount(t);
  if (o.pincer) m *= 1 + o.pincer * alive().filter(x => x !== a && x.side === a.side && dist(x, t) === 1).length;
  if (o.momentum) m *= 1 + o.momentum * dist(a, t);
  if (o.onLava && B.grid[t.y][t.x] === T.LAVA && !t.fly) m *= 1.6;
  if (t.side !== a.side && alive().some(x => x !== t && x.rampart && x.side === t.side && dist(x, t) === 1)) m *= 0.75; // Phalanx
  return m;
}
function calcDmg(a, t, o) {
  if (o.gravity) return Math.max(1, t.hp * o.gravity * (t.boss ? 0.5 : 1));
  const magic = o.kind === 'mag';
  return Math.max(1, powerVal(a, o) * 12 / (12 + (magic ? t.res : t.def)) * dmgMult(a, t, o));
}
function roll(a, t, o, w) {
  if (o.gravity) return { dmg: Math.max(1, Math.round(calcDmg(a, t, o) * w)), crit: false };
  let v = calcDmg(a, t, o) * w * (0.9 + Math.random() * 0.2);
  if (o.gamble) v *= Math.random() * 2.5;
  const crit = Math.random() * 100 < a.crit || (isClass(a, 'assassin') && t.hp * 2 < t.maxHp) || (isClass(a, 'arithmetician') && isPrime(t.hp));
  if (crit) v *= 1.5;
  return { dmg: Math.max(o.gamble ? 0 : 1, Math.round(v)), crit };
}

function damage(t, amount, src, opts = {}) {
  if (t.dead || amount <= 0) { if (amount <= 0 && !t.dead) fxText(t, '0', '#aaa'); return 0; }
  if (!opts.redirected) {
    const m = alive().find(x => x !== t && x.side === t.side && has(x, 'martyr') && dist(x, t) === 1);
    if (m) { fxText(t, 'Guarded', '#ddd'); return damage(m, Math.max(1, Math.round(amount / 2)), src, { ...opts, redirected: true }); }
  }
  if (src && src.side !== t.side && t.st.ward > 0 && !opts.reflected) {
    t.st.ward--;
    fxText(t, 'Warded', '#c9f7ff');
    sfx('shield');
    refreshView(t);
    return 0;
  }
  let left = amount;
  if (t.shield > 0) {
    const s = Math.min(t.shield, left);
    t.shield -= s; left -= s;
    if (s) fxText(t, `-${s}`, '#9fd8ff');
    if (s && t.shield === 0 && has(t, 'shrapnel')) {
      fxText(t, 'Shrapnel!', '#9fd8ff');
      for (const f of alive().filter(x => x.side !== t.side && dist(x, t) === 1)) damage(f, s, t, { reflected: true, quiet: true });
    }
  }
  if (left > 0) {
    if (t.st.sleep > 0) { t.st.sleep = 0; fxText(t, 'Wakes', '#c9f7ff', true); }
    t.hp = Math.max(0, t.hp - left);
    fxText(t, (opts.crit ? 'CRIT ' : '') + left, opts.crit ? '#ffd23f' : '#ffffff');
  }
  flash(t);
  burst('hit', t, opts.crit ? 14 : 7);
  sfx(opts.crit ? 'crit' : 'hit', opts.quiet ? 0.5 : 1);
  if (opts.crit) scene && scene.cameras.main.shake(120 * env.speed + 1, 0.006);
  if (t.hp <= 0) ko(t, src);
  if (src && src !== t && has(t, 'mirror') && !opts.reflected && !src.dead) damage(src, Math.max(1, Math.round(amount * 0.35)), t, { reflected: true, quiet: true });
  const th = src && src.side !== t.side && !opts.reflected && !opts.counter && !src.dead && (opts.melee || has(t, 'idol')) ? thornsNow(t) : 0;
  if (th > 0) {
    fxText(src, 'Thorns', '#c8b45a', true);
    damage(src, th, t, { reflected: true, quiet: true });
    if (has(t, 'rose') && !src.dead && !has(src, 'plaguemask')) { src.st.poison = Math.max(src.st.poison || 0, 2); src.st.poisonDmg = Math.max(src.st.poisonDmg || 0, Math.ceil(th / 3)); refreshView(src); }
  }
  if (src && opts.melee && !opts.counter && !t.dead && !src.dead && src.side !== t.side && (t.st.riposte || isClass(t, 'blademaster') || has(t, 'countertackle')) && dist(t, src) === 1) {
    fxText(t, 'Riposte', '#ffd23f');
    damage(src, Math.round(calcDmg(t, src, { kind: 'phys', stat: 'atk', pow: 0.6, range: [1, 1] })), t, { counter: true });
  }
  refreshView(t);
  return left;
}
function ko(t, killer) {
  if (has(t, 'laststand') && !t.lastStandUsed) {
    t.lastStandUsed = true;
    t.hp = 1;
    fxText(t, 'Last stand!', '#ff6a6a');
    log(`${t.name} refuses to fall!`);
    return;
  }
  if (has(t, 'phoenix') && !t.phoenixUsed) {
    t.phoenixUsed = true;
    t.hp = Math.ceil(t.maxHp / 2);
    fxText(t, 'Rebirth!', '#ffb03b');
    burst('fire', t, 30);
    sfx('fire');
    log(`${t.name} rises from the ashes!`);
    return;
  }
  const venom = t.st.poison > 0 ? { n: t.st.poison, dmg: t.st.poisonDmg, by: t.st.poisonBy } : null;
  if (t.origSide) { t.side = t.origSide; t.origSide = null; }
  t.pending = null;
  t.hp = 0; t.dead = true; t.st = {}; t.shield = 0;
  log(`${t.name} falls.`);
  sfx('death');
  if (t.side === 'foe') env.run.stats.kills++;
  if (t.view) scene.tweens.add({ targets: t.view, alpha: 0, duration: 450 * env.speed + 1, onComplete: () => t.view && t.view.setVisible(false) });
  if (has(t, 'spite')) {
    fxText(t, 'Spite!', '#ff6a6a');
    for (const f of alive().filter(x => x.side !== t.side)) damage(f, Math.round(f.maxHp * 0.3), null, { quiet: true });
  }
  if (killer && !killer.dead && isClass(killer, 'assassin')) killer.st.stealth = 1;
  if (killer && !killer.dead && killer.side !== t.side) {
    const f = (isClass(killer, 'warlock') ? 0.08 : 0) + (has(killer, 'chalice') ? 0.1 : 0);
    if (f) heal(killer, killer.maxHp * f);
  }
  if (venom && venom.by && (isClass(venom.by, 'plaguebringer') || has(venom.by, 'spores'))) {
    for (const n of alive().filter(x => x.side === t.side && dist(x, t) === 1 && !has(x, 'plaguemask'))) {
      n.st.poison = Math.max(n.st.poison || 0, Math.max(2, venom.n)); n.st.poisonDmg = Math.max(n.st.poisonDmg || 0, venom.dmg); n.st.poisonBy = venom.by;
      burst('poison', n, 10); refreshView(n);
    }
    log(`The plague spreads from ${t.name}.`);
  }
  if (killer && !killer.dead && has(killer, 'phylactery') && t.side !== killer.side && !t.boss) {
    const x = t.x, y = t.y;
    setTimeout(() => { if (B && !B.over && !unitAt(x, y)) spawn('skeleton', killer.side, x, y, true); }, 500 * env.speed);
  }
}
function heal(t, n, overflow) {
  if (t.dead) return 0;
  n = Math.max(0, Math.round(n));
  const a = Math.max(0, Math.min(n, healRoom(t)));
  t.hp += a;
  if (a > 0) fxText(t, '+' + a, '#7dff8a');
  if (overflow && n > a) addShield(t, n - a);
  refreshView(t);
  return a;
}
const healRoom = t => t.maxHp - t.hp;
function addShield(t, n) {
  if (t.dead) return;
  n = Math.max(0, Math.min(Math.round(n), t.maxHp - t.shield));
  if (!n) return;
  t.shield += n;
  fxText(t, '+' + n + ' shield', '#9fd8ff');
  burst('shield', t, 10);
  refreshView(t);
}
function setTile(x, y, type) {
  if (!inb(x, y) || B.grid[y][x] === type) return;
  B.grid[y][x] = type;
  if (B.tiles) B.tiles[y][x].setTexture(tileKey(B.theme, type, ANIMATED.has(type) ? B.frame % 3 : B.vari[y][x] % TILE_VARIANTS[type]));
}

function applyStatus(u, t, o) {
  const foe = t.side !== u.side;
  const hit = o.kind === 'phys' || o.kind === 'mag';
  const ext = isClass(u, 'bard') ? 1 : 0; // Encore
  if (o.stun && !t.boss) t.st.stun = 1;
  if (o.stunLow && !t.boss && t.hp * 2 < t.maxHp) t.st.stun = 1;
  if (o.slow) t.st.slow = Math.max(t.st.slow || 0, o.slow + ext);
  if (o.poison && !has(t, 'plaguemask')) {
    const dose = Math.max(1, Math.round(statVal(u, o.stat) * (o.poisonPow || 0.3)));
    const stack = (isClass(u, 'plaguebringer') || has(u, 'toxicheart')) && t.st.poison > 0;
    t.st.poisonDmg = stack ? Math.min(t.st.poisonDmg + dose, Math.round(t.maxHp * 0.2) + dose) : Math.max(t.st.poison > 0 ? t.st.poisonDmg || 0 : 0, dose);
    t.st.poison = Math.max(t.st.poison || 0, o.poison);
    t.st.poisonBy = u; t.st.leech = !!o.leech;
  }
  const burn = o.burn || (isClass(u, 'pyromancer') && o.kind === 'mag' ? 2 : 0);
  if (burn && !t.fireproof) {
    const ember = has(u, 'emberheart');
    t.st.burn = Math.max(t.st.burn || 0, burn + (ember ? 2 : 0));
    t.st.burnDmg = Math.max(t.st.burnDmg || 0, Math.max(1, Math.round(statVal(u, o.stat) * 0.3 * (ember ? 1.5 : 1))));
  }
  const shock = o.shock || (hit && o.kind === 'mag' && (isClass(u, 'stormcaller') || has(u, 'stormcrown')) ? 2 : 0);
  if (shock && foe) t.st.shock = Math.max(t.st.shock || 0, shock + ext);
  if (o.taunt && foe) { t.st.taunt = o.taunt; t.st.tauntBy = u; }
  if (o.vuln && foe) { t.st.vulnAmt = Math.max(t.st.vuln > 0 ? t.st.vulnAmt || 0 : 0, o.vulnAmt || 0.3); t.st.vuln = o.vuln + ext; }
  if (o.rally && !foe) t.st.rally = o.rally + ext;
  if (o.blind && foe) t.st.blind = o.blind + ext;
  if (o.ward && !foe) { t.st.ward = Math.max(t.st.ward || 0, o.ward); fxText(t, 'Ward', '#c9f7ff'); }
  if (o.doom && foe && !t.st.doom) { t.st.doom = o.doom; fxText(t, 'Doomed', '#c44dff'); }
  if (o.cdLock && foe) for (const s of t.skills) if (SKILLS[s.id].cd > 0) s.cd = Math.max(s.cd, o.cdLock + ext);
  if (o.charm && foe && !t.boss && !(t.st.resolve > 0)) {
    t.st.charm = o.charm + (isClass(u, 'mesmer') ? 1 : 0);
    if (!t.origSide) t.origSide = t.side;
    t.side = u.side;
    t.st.taunt = 0; t.st.tauntBy = null;
    fxText(t, 'Charmed', '#ff8ad8');
    log(`${t.name} switches sides!`);
  }
  if (o.root && foe && !t.boss) t.st.root = Math.max(t.st.root || 0, o.root + ext);
  if (o.disarm && foe && !t.boss) t.st.disarm = Math.max(t.st.disarm || 0, o.disarm + ext);
  if (o.weak && foe) t.st.weak = Math.max(t.st.weak || 0, o.weak + ext);
  if (o.oil && foe) { t.st.oil = Math.max(t.st.oil || 0, o.oil); fxText(t, 'Oiled', '#c8a040', true); }
  if (o.wet && foe) { t.st.wet = Math.max(t.st.wet || 0, o.wet); if (t.st.burn > 0) t.st.burn = 0; }
  if (o.sleep && foe && !t.boss) { t.st.sleep = Math.max(t.st.sleep || 0, o.sleep + ext); fxText(t, 'Zzz', '#c9f7ff'); }
  if (o.confuse && foe && !t.boss) { t.st.confuse = Math.max(t.st.confuse || 0, o.confuse + ext); fxText(t, 'Confused', '#ffd23f', true); }
  if (o.ctZero && foe) t.ct = Math.min(t.ct, 0);
  if (o.dispel && foe) {
    const had = BUFFS.some(k => t.st[k] > 0) || t.shield > 0;
    for (const k of BUFFS) t.st[k] = 0;
    t.shield = 0;
    if (had) fxText(t, 'Dispelled', '#c9a0ff', true);
  }
  if (o.stealShield && foe && t.shield > 0) { const n = t.shield; t.shield = 0; addShield(u, n); fxText(t, 'Stolen!', '#9fd8ff', true); }
  if (o.purify && !foe) { for (const k of DEBUFFS) t.st[k] = 0; fxText(t, 'Purified', '#7dff8a', true); }
  if (o.movUp && !foe) t.st.movUp = Math.max(t.st.movUp || 0, o.movUp + ext);
  if (o.focus && !foe) { t.st.focus = 1; fxText(t, 'Focus', '#ffd23f', true); }
  if (o.brace && !foe) t.st.guard = 1;
  if (o.thornsUp && !foe) { t.st.thorns = Math.max(t.st.thorns || 0, o.thornsUp + ext); fxText(t, 'Thorns', '#c8b45a', true); }
  if (o.imbue && !foe) { t.st.imbue = 3 + ext; t.st.imbueKind = o.imbue; fxText(t, 'Imbued', '#ffd23f', true); }
  if (o.counter && !foe) t.st.riposte = 1;
  if (hit && foe && u.st.imbue > 0) {
    const k = u.st.imbueKind;
    if (k === 'burn' && !t.fireproof) { t.st.burn = Math.max(t.st.burn || 0, 2); t.st.burnDmg = Math.max(t.st.burnDmg || 0, Math.round(statVal(u, 'atk') * 0.3) + 1); }
    if (k === 'poison' && !has(t, 'plaguemask')) { t.st.poison = Math.max(t.st.poison || 0, 3); t.st.poisonDmg = Math.max(t.st.poisonDmg || 0, Math.round(statVal(u, 'atk') * 0.3) + 1); t.st.poisonBy = u; }
    if (k === 'shock') t.st.shock = Math.max(t.st.shock || 0, 2);
    if (k === 'slow') t.st.slow = Math.max(t.st.slow || 0, 2);
  }
  // elemental reactions: oil + fire ignites, water + lightning or frost locks the target up
  if (t.st.oil > 0 && t.st.burn > 0 && !t.fireproof) {
    t.st.oil = 0; t.st.burn += 2; t.st.burnDmg *= 2;
    fxText(t, 'Ignite!', '#ff8a3d'); burst('fire', t, 24); sfx('fire');
    damage(t, t.st.burnDmg, u, { quiet: true });
  }
  if (t.st.wet > 0 && (t.st.shock > 0 || (o.slow && foe)) && !t.boss && !t.dead) {
    t.st.wet = 0; t.st.stun = 1;
    fxText(t, t.st.shock > 0 ? 'Conduct!' : 'Frozen!', '#c9f7ff');
  }
  if (o.ctGive && !foe) { t.ct += o.ctGive; for (const s of t.skills) s.cd = Math.max(0, s.cd - (o.cdReduce || 0)); fxText(t, 'Haste!', '#c9f7ff'); }
  if (o.ctTake && foe) t.ct -= o.ctTake;
  if (isClass(u, 'chronomancer') && o.kind === 'mag' && foe) t.ct -= 25;
  if (has(u, 'metronome') && foe && hit) t.ct -= 15;
  if (has(u, 'frostlocket') && foe && hit) t.st.slow = Math.max(t.st.slow || 0, 2);
  refreshView(t);
}
// Detonate: the target's remaining poison (or doubled burn) lands at once.
function detonate(u, t, what) {
  if (t.dead) return;
  if (what === 'poison' && t.st.poison > 0) {
    const n = t.st.poison * t.st.poisonDmg;
    t.st.poison = 0;
    burst('poison', t, 20);
    fxText(t, 'Burst!', '#8be04e', true);
    damage(t, n, u, { quiet: true });
  } else if (what === 'burn' && t.st.burn > 0) {
    const n = t.st.burn * t.st.burnDmg * 2;
    t.st.burn = 0;
    burst('fire', t, 24);
    fxText(t, 'Combust!', '#ff8a3d', true);
    sfx('fire');
    damage(t, n, u, { quiet: true });
  }
}

// ---------- movement and displacement ----------
async function enterTile(u) {
  const t = B.grid[u.y][u.x];
  if (u.fly) return;
  const trap = B.traps && B.traps.get(key(u.x, u.y));
  if (trap && trap.side !== homeSide(u)) {
    B.traps.delete(key(u.x, u.y));
    fxText(u, 'Trap!', '#ffd23f');
    burst(trap.o.burn ? 'fire' : trap.o.poison ? 'poison' : 'hit', u, 16);
    sfx('crit');
    log(`${u.name} springs a trap.`);
    if (trap.o.kind === 'phys' || trap.o.kind === 'mag') damage(u, Math.round(calcDmg(trap.u, u, trap.o)), trap.u, { quiet: true });
    if (!u.dead) applyStatus(trap.u, u, trap.o);
    if (u.dead) return;
  }
  if (t === T.LAVA && !u.fireproof) {
    log(`${u.name} is scorched by lava.`);
    sfx('lava');
    burst('fire', u, 12);
    damage(u, Math.round(u.maxHp * 0.12) + 4, null, { quiet: true });
    if (!u.dead) { u.st.burn = Math.max(u.st.burn || 0, 2); u.st.burnDmg = Math.max(u.st.burnDmg || 0, 3 + Math.floor(B.level / 3)); }
  } else if (t === T.THORN) {
    damage(u, 3 + Math.floor(B.level / 3), null, { quiet: true });
  }
}
async function stepTo(u, x, y, ms = 95) {
  const px = u.x, py = u.y;
  u.x = x; u.y = y;
  await tweenView(u, ms);
  if ((u.trail || has(u, 'lavawalkers')) && floorish(B.grid[py][px]) && !unitAt(px, py)) setTile(px, py, T.LAVA);
  await enterTile(u);
}
async function moveUnit(u, path, blink) {
  if (blink) {
    sfx('blink');
    await tw({ targets: u.view, alpha: 0, duration: 120 });
    const end = path[path.length - 1];
    u.x = end.x; u.y = end.y;
    placeView(u);
    await tw({ targets: u.view, alpha: viewAlpha(u), duration: 120 });
    await enterTile(u);
  } else {
    for (let i = 1; i < path.length && !u.dead; i++) {
      if (i % 2) sfx('step', 0.5);
      await stepTo(u, path[i].x, path[i].y);
    }
  }
  u.moved = true;
}
// Push t n tiles directly away from `from` (the attacker, or the centre of an area); a blocked push hurts.
async function knock(u, t, n = 1, from = u) {
  if (t.anchored || t.dead) return;
  let dx = Math.sign(t.x - from.x), dy = Math.sign(t.y - from.y);
  if (dx && dy) { if (Math.abs(t.x - from.x) >= Math.abs(t.y - from.y)) dy = 0; else dx = 0; }
  if (!dx && !dy) return;
  for (let i = 0; i < n && !t.dead; i++) {
    const nx = t.x + dx, ny = t.y + dy;
    if (standable(t, nx, ny) && !unitAt(nx, ny)) await stepTo(t, nx, ny, 110);
    else { log(`${t.name} slams into an obstacle.`); damage(t, Math.max(1, Math.round(u.atk * 0.3)), u, { quiet: true }); return; }
  }
}
async function pull(u, t, n) {
  if (t.anchored || t.dead) return;
  for (let i = 0; i < n && !t.dead && dist(u, t) > 1; i++) {
    const dx = u.x - t.x, dy = u.y - t.y, opts = [];
    if (dx) opts.push([t.x + Math.sign(dx), t.y, Math.abs(dx)]);
    if (dy) opts.push([t.x, t.y + Math.sign(dy), Math.abs(dy)]);
    opts.sort((a, b) => b[2] - a[2]);
    const next = opts.find(([x, y]) => standable(t, x, y) && !unitAt(x, y));
    if (!next) break;
    await stepTo(t, next[0], next[1], 80);
  }
}
async function dashAlong(u, o, x, y) {
  let last = null;
  for (const [tx, ty] of lineTiles(u, o, x, y)) if (standable(u, tx, ty) && !unitAt(tx, ty)) last = [tx, ty];
  if (!last) return;
  u.x = last[0]; u.y = last[1];
  await tweenView(u, 160);
  await enterTile(u);
}
async function hopAway(u, n) {
  const R = reach({ ...u, mov: n, items: [] });
  let best = null;
  const foes = alive().filter(t => t.side !== u.side);
  for (const v of R.values()) {
    if (!v.stop || v.risk) continue;
    const d = Math.min(...foes.map(f => Math.abs(f.x - v.x) + Math.abs(f.y - v.y)));
    if (!best || d > best.d) best = { v, d };
  }
  if (best && (best.v.x !== u.x || best.v.y !== u.y)) await moveUnit(u, pathTo(R, key(best.v.x, best.v.y)));
}
function spawn(kind, side, x, y, ally) {
  const sk = foeUnit(kind, B.level);
  Object.assign(sk, { x, y, side, summoned: true, ct: 0 });
  if (ally && kind === 'skeleton') { sk.spr = 'skeleton_ally'; sk.name = 'Risen Skeleton'; }
  else if (ally) sk.name = `Allied ${sk.name}`;
  B.units.push(sk);
  makeView(sk);
  sk.view.setAlpha(0);
  scene.tweens.add({ targets: sk.view, alpha: 1, duration: 400 * env.speed + 1 });
  burst('dark', sk, 16);
  sfx('summon');
}
function summon(u, kind, n = 2) {
  const spots = [];
  for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
    const d = Math.abs(x - u.x) + Math.abs(y - u.y);
    if (d > 0 && d <= 3 && standable({}, x, y) && !unitAt(x, y) && !hazard({ maxHp: 1 }, x, y)) spots.push({ x, y, d });
  }
  spots.sort((a, b) => a.d - b.d || Math.random() - 0.5);
  for (const s of spots.slice(0, n)) spawn(kind, u.side, s.x, s.y, u.side === 'hero');
  log(kind === 'skeleton' ? `${u.name} raises the dead!` : `${u.name} calls for help!`);
}
function raiseWalls(x, y) {
  for (const [dx, dy] of [[0, 0], ...DIRS]) {
    const tx = x + dx, ty = y + dy;
    if (inb(tx, ty) && floorish(B.grid[ty][tx]) && !unitAt(tx, ty)) { setTile(tx, ty, T.WALL); burst('dust', { x: tx, y: ty }, 8); }
  }
  sfx('hit');
}

// ---------- using a skill ----------
function castColor(o) {
  if (o.kind === 'heal') return 0x7dff8a;
  if (o.kind === 'shield') return 0x9fd8ff;
  if (o.burn || o.terrain === T.LAVA || o.id === 'fireball') return 0xff8a3d;
  if (o.shock) return 0xffe14d;
  if (o.poison) return 0x8be04e;
  if (o.slow) return 0xbfefff;
  if (o.kind === 'mag') return 0xc9a0ff;
  return 0xe8e8e8;
}
function castSound(o, ranged) {
  if (o.kind === 'heal') return 'heal';
  if (o.kind === 'shield') return 'shield';
  if (o.kind === 'buff') return o.stealth || o.teleport ? 'blink' : 'buff';
  if (o.kind === 'summon') return 'summon';
  if (o.burn || o.terrain === T.LAVA || o.id === 'fireball') return 'fire';
  if (o.slow && o.kind === 'mag') return 'ice';
  if (o.kind === 'mag') return 'magic';
  return ranged ? 'click' : 'slash';
}

// What a skill does when used: Mimic turns into the last skill an ally used.
function effective(u, s) {
  const o = skStats(u, s);
  if (!o.mimic) return o;
  const last = B.lastCast && B.lastCast[homeSide(u)];
  if (!last) return o;
  const m = skStats(u, { id: last.id, mods: last.mods });
  return { ...m, name: `${o.name}: ${m.name}`, cd: o.cd, mimicked: last };
}
// echoed: true for an echo, 'delayed' when a charged skill goes off, 'mimic' for the copied skill.
async function useSkill(u, s, tx, ty, echoed) {
  let o = effective(u, s);
  if (o.mimic && !o.mimicked) { s.cd = o.cd; u.acted = true; fxText(u, 'Nothing to copy', '#aaaaaa', true); await sleep(300); return; }
  if (o.mimicked) { s.cd = o.cd; u.acted = true; return useSkill(u, { id: o.mimicked.id, mods: o.mimicked.mods, cd: 0 }, tx, ty, 'mimic'); }
  if (!echoed) { s.cd = o.cd; u.acted = true; B.lastCast = { ...(B.lastCast || {}), [homeSide(u)]: { id: s.id, mods: s.mods } }; }
  B.mode = null; B.pending = null;
  renderPanel();
  log(`${u.name}: ${o.name}${echoed === true ? ' (echo)' : ''}`);
  fxText(u, echoed === true ? 'Echo!' : o.name, '#c9b8ff', true);
  if (echoed === 'mimic') echoed = false;
  if ((o.hpCost || o.bloodpact) && !echoed) {
    const cost = Math.round(u.maxHp * (o.hpCost || 0.1));
    u.hp = Math.max(1, u.hp - cost);
    fxText(u, '-' + cost, '#ff6a6a');
    refreshView(u);
  }
  if (o.delay && echoed !== 'delayed') {
    // charge now, land at the start of the caster's next turn
    u.pending = { s: { id: s.id, mods: s.mods, cd: 0 }, tx, ty };
    fxText(u, 'Charging...', '#ffd23f', true);
    sfx('buff');
    log(`${u.name} gathers power for ${o.name}.`);
    await sleep(320);
    return;
  }
  if (o.kind === 'phys' || o.kind === 'mag') u.st.stealth = 0;
  if (o.vortex) {
    const near = alive().filter(t => t.side !== u.side && dist(t, u) <= o.vortex + o.aoe && dist(t, u) > 1).sort((a, b) => dist(a, u) - dist(b, u));
    sfx('blink');
    for (const t of near) await pull(u, t, o.vortex);
  }
  if (o.leap) {
    const t = unitAt(tx, ty);
    const spot = t && dist(u, t) > 1 ? leapSpot(u, t) : null;
    if (spot) {
      sfx(o.stealth ? 'blink' : 'step');
      u.x = spot.x; u.y = spot.y;
      if (o.stealth) { await tw({ targets: u.view, alpha: 0, duration: 100 }); placeView(u); await tw({ targets: u.view, alpha: 1, duration: 100 }); }
      else await tweenView(u, 180, true);
      await enterTile(u);
      if (u.dead) { await sleep(300); checkEnd(); return; }
    }
  }
  if (o.land && !unitAt(tx, ty)) {
    sfx('step');
    u.x = tx; u.y = ty;
    await tweenView(u, 320, true);
    scene && scene.cameras.main.shake(140 * env.speed + 1, 0.006);
    burst('dust', u, 14);
    await enterTile(u);
    if (u.dead) { await sleep(300); checkEnd(); return; }
  }
  const list = hitList(u, o, tx, ty, false);
  const tiles = areaTiles(u, o, tx, ty);
  const ranged = o.tgt !== 'self' && Math.abs(u.x - tx) + Math.abs(u.y - ty) > 1;
  sfx(castSound(o, ranged));
  const color = castColor(o);
  if (o.shape === 'coin') { banner(B.coin ? 'Tails: allies!' : 'Heads: foes!'); await sleep(500); }
  if (o.shape === 'random' || o.shape === 'multi' || o.shape === 'math' || o.shape === 'coin') {
    for (const { t } of list) projectile(u, t.x, t.y, color, true);
    await sleep(320);
  } else if (ranged) await projectile(u, tx, ty, color, o.lob);
  else if (o.tgt !== 'self' && !(tx === u.x && ty === u.y)) await lunge(u, tx, ty);
  else await pulse(u);
  if (o.aoe || o.shape === 'line') areaFlash(tiles, color);
  if (o.kind === 'mag' && (o.burn || o.terrain === T.LAVA || o.id === 'fireball')) for (const [x, y] of tiles) burst('fire', { x, y }, 5);

  let dealt = 0;
  for (const { t, w } of list) {
    if (t.dead) continue;
    if (o.kind === 'heal') {
      heal(t, powerVal(u, o) * w, o.overflow);
      if (o.cleanse) { t.st.poison = 0; t.st.burn = 0; }
      burst('heal', t, 12);
      continue;
    }
    if (o.kind === 'shield') { addShield(t, powerVal(u, o) * w); if (o.brace) t.st.guard = 1; continue; }
    if (o.kind === 'buff') {
      if (o.shape === 'coin' && o.ctGive) { t.ct += o.ctGive; fxText(t, 'Haste!', '#c9f7ff'); }
      applyStatus(u, t, o); burst(t.side === u.side ? 'heal' : 'dark', t, 8);
      if (o.push && homeSide(t) !== homeSide(u) && !t.dead) await knock(u, t, o.push, o.tgt === 'tile' ? { x: tx, y: ty } : u);
      if (o.pull && homeSide(t) !== homeSide(u) && !t.dead) await pull(u, t, o.pull);
      continue;
    }
    if (o.kind === 'summon') continue;
    for (let i = 0; i < hitsOf(o) && !t.dead; i++) {
      const sure = has(u, 'concentrate') || o.sure;
      if (!sure && u.st.blind > 0 && chance(0.5)) { fxText(t, 'Miss', '#aaaaaa'); sfx('miss'); continue; }
      if (!sure && t.side !== u.side && ((isClass(t, 'oracle') && chance(0.2)) || (has(t, 'bladegrasp') && o.kind === 'phys' && chance(0.25)))) { fxText(t, 'Dodge', '#c9f7ff'); sfx('miss'); continue; }
      if (has(t, 'hollow') && t.side === u.side && t !== u) { heal(t, calcDmg(u, t, o) * w); continue; }
      const shocked = t.st.shock > 0;
      const r = roll(u, t, o, w);
      damage(t, r.dmg, u, { crit: r.crit, melee: dist(u, t) === 1 });
      dealt += r.dmg;
      if (shocked && o.kind === 'mag' && isClass(u, 'stormcaller') && t.side !== u.side && !u.dead) {
        const arc = alive().filter(x => x !== t && x.side === t.side && dist(x, t) <= 2).sort((a, b) => dist(a, t) - dist(b, t))[0];
        if (arc) { projectile(t, arc.x, arc.y, 0xffe14d); damage(arc, Math.max(1, Math.round(r.dmg * 0.5)), u, { quiet: true }); }
      }
      if (o.cull && !t.dead && !t.boss && t.hp <= t.maxHp * o.cull) { fxText(t, 'Culled', '#ff6a6a'); damage(t, t.hp + t.shield, u, { quiet: true }); }
      if (o.recoilDmg && !u.dead) damage(u, Math.max(1, Math.round(r.dmg * o.recoilDmg)), null, { quiet: true });
      if (!u.dead) {
        if (o.drain) heal(u, r.dmg * o.drain);
        if (has(u, 'fang')) heal(u, r.dmg * 0.2);
        if (o.selfShield) addShield(u, r.dmg * o.selfShield);
      }
      if (isClass(u, 'trickster') && t.side !== u.side && isHero(u)) env.run.gold += 3;
      if (i < hitsOf(o) - 1) await sleep(140);
    }
    if (o.detonate) detonate(u, t, o.detonate);
    if (t.dead) continue;
    applyStatus(u, t, o);
    if (o.steal && isHero(u) && t.side !== u.side) { const g = rnd(8, 15); env.run.gold += g; fxText(t, `+${g}g`, '#ffd23f', true); sfx('coin'); }
    if (o.spread) for (const n of alive().filter(x => x !== t && x.side === t.side && dist(x, t) === 1)) {
      for (const k of ['poison', 'burn', 'slow', 'shock', 'vuln', 'blind', 'weak', 'oil', 'wet']) if (t.st[k] > 0 && !(n.st[k] > 0)) {
        n.st[k] = t.st[k];
        if (k === 'poison') n.st.poisonDmg = t.st.poisonDmg;
        if (k === 'burn') n.st.burnDmg = t.st.burnDmg;
        if (k === 'vuln') n.st.vulnAmt = t.st.vulnAmt;
      }
      burst('poison', n, 8); refreshView(n);
    }
    if (o.swap) continue;
    if (o.push) await knock(u, t, o.push, o.tgt === 'tile' ? { x: tx, y: ty } : u);
    else if (o.knock) await knock(u, t);
    else if (o.pull) await pull(u, t, o.pull);
    else if (has(u, 'magnet') && t.side !== u.side && (o.kind === 'phys' || o.kind === 'mag')) await pull(u, t, 1);
    await sleep(50);
  }
  if (o.generous && dealt) {
    const a = alive().filter(x => x.side === u.side).sort((p, q) => p.hp / p.maxHp - q.hp / q.maxHp)[0];
    if (a) { heal(a, dealt * o.generous); burst('heal', a, 10); }
  }
  if (o.terrain != null) {
    let changed = false;
    const solid = o.terrain === T.WALL || o.terrain === T.ROCK;
    for (const [x, y] of tiles) if (floorish(B.grid[y][x]) && !(solid && unitAt(x, y))) { setTile(x, y, o.terrain); changed = true; }
    if (changed && o.terrain === T.LAVA) { sfx('lava'); for (const t of alive()) if (tiles.some(([x, y]) => x === t.x && y === t.y)) await enterTile(t); }
  }
  if (has(u, 'thornseed') && (o.kind === 'phys' || o.kind === 'mag')) for (const { t } of list) if (B.grid[t.y][t.x] === T.FLOOR) setTile(t.x, t.y, T.THORN);
  if (o.walls) raiseWalls(tx, ty);
  if (o.trap) {
    B.traps ||= new Map();
    for (const [x, y] of tiles) if (standable({}, x, y) && !unitAt(x, y)) B.traps.set(key(x, y), { side: homeSide(u), u, o });
    sfx('click');
  }
  if (o.swap) {
    const t = unitAt(tx, ty);
    if (t && canSwap(u, t)) {
      sfx('blink');
      const [ux, uy] = [u.x, u.y];
      u.x = t.x; u.y = t.y; t.x = ux; t.y = uy;
      await Promise.all([tweenView(u, 160), tweenView(t, 160)]);
      await enterTile(u); await enterTile(t);
    }
  }
  if (o.dash && !u.dead) await dashAlong(u, o, tx, ty);
  if (o.teleport && !u.dead && !unitAt(tx, ty)) {
    await tw({ targets: u.view, alpha: 0, duration: 120 });
    u.x = tx; u.y = ty;
    placeView(u);
    await tw({ targets: u.view, alpha: viewAlpha(u), duration: 120 });
    burst('dark', u, 10);
    await enterTile(u);
  }
  if (o.recoil && !u.dead) await hopAway(u, o.recoil);
  if (o.guard) u.st.guard = 1;
  if (o.riposte) u.st.riposte = 1;
  if (o.stealth && !u.dead) { u.st.stealth = 1; refreshView(u); }
  if (o.thornsUp && !u.dead && (o.kind !== 'buff' || !list.some(e => e.t === u))) { u.st.thorns = Math.max(u.st.thorns || 0, o.thornsUp); fxText(u, 'Thorns', '#c8b45a', true); }
  if (u.st.focus && (o.kind === 'phys' || o.kind === 'mag')) u.st.focus = 0;
  if (o.selfHaste && !u.dead) u.ct += o.selfHaste;
  if (o.selfShieldHp && !u.dead) addShield(u, u.maxHp * o.selfShieldHp);
  if ((o.leap || o.land) && isClass(u, 'dragoon') && !u.dead) { u.st.airborne = 1; fxText(u, 'Airborne', '#c9f7ff', true); refreshView(u); }
  if (o.kind === 'summon') summon(u, o.summon, o.summonN || 2);
  if (o.ctCost) u.ctDebt = (u.ctDebt || 0) + o.ctCost;
  if (!echoed && has(u, 'bees') && !u.dead) {
    const f = pick(alive().filter(x => x.side !== u.side));
    if (f) { sfx('bee'); fxText(f, 'Bzz', '#ffe14d'); damage(f, 3 + Math.floor(B.level / 2), u, { quiet: true }); }
  }
  refreshView(u);
  if (!echoed && !u.dead && !B.over && ((o.echo && chance(o.echo)) || (has(u, 'echo') && chance(0.25)))) {
    await sleep(250);
    if (o.tgt === 'self' || o.shape || validTarget(u, o, tx, ty)) await useSkill(u, s, tx, ty, true);
  }
  await sleep(320);
  checkEnd();
}

// ---------- turns ----------
function nextActor() {
  for (let guard = 0; guard < 10000; guard++) {
    const ready = alive().filter(u => u.ct >= 100);
    if (ready.length) return ready.sort((a, b) => b.ct - a.ct || spdOf(b) - spdOf(a))[0];
    for (const u of alive()) u.ct += spdOf(u);
  }
  return alive()[0];
}
function predictOrder(n) {
  const sim = alive().map(u => ({ u, ct: u.ct, spd: spdOf(u) }));
  const out = [];
  if (B.active && !B.active.dead) { out.push(B.active); const a = sim.find(x => x.u === B.active); if (a) a.ct -= 100; }
  for (let guard = 0; out.length < n && guard < 5000; guard++) {
    const ready = sim.filter(x => x.ct >= 100);
    if (ready.length) { ready.sort((a, b) => b.ct - a.ct || b.spd - a.spd); out.push(ready[0].u); ready[0].ct -= 100; }
    else sim.forEach(x => { x.ct += x.spd; });
  }
  return out;
}
function checkEnd() {
  if (!B || B.over) return true;
  const heroes = B.units.some(u => u.ref && homeSide(u) === 'hero' && !u.dead), foes = B.units.some(u => homeSide(u) === 'foe' && !u.dead);
  if (heroes && foes) return false;
  B.over = true;
  if (B.resolveTurn) { const r = B.resolveTurn; B.resolveTurn = null; r(); }
  const b = B;
  sfx(heroes ? 'victory' : 'defeat');
  sleep(1000).then(() => { if (B === b) { B = null; env.onEnd(b, heroes); } });
  return true;
}
async function battleLoop(b) {
  if (b.kind === 'boss') {
    const boss = b.units.find(u => u.boss);
    sfx('roar');
    scene.cameras.main.shake(500 * env.speed + 1, 0.01);
    banner(boss.name);
    await sleep(1400);
  }
  while (B === b && !b.over) {
    const u = nextActor();
    b.active = u; b.inspect = null; b.startPos = null;
    u.moved = false; u.acted = false;
    renderPanel();
    const skip = await startTurn(u);
    if (B !== b || checkEnd()) return;
    if (!skip) {
      if (u.st.confuse > 0) {
        // a confused unit lashes out at whoever is nearest, friend or foe
        u.madSide = u.side; u.side = 'mad';
        fxText(u, '???', '#ffd23f');
        await aiTurn(u);
        if (u.madSide) { u.side = u.madSide; u.madSide = null; }
      } else if (isHero(u) && !env.auto) await playerTurn(u);
      else await aiTurn(u);
    }
    if (B !== b || b.over) return;
    endTurn(u);
  }
}
const CALM_TURNS = 27; // hero turns (about 9 rounds) before the enemy starts to rage
async function startTurn(u) {
  u.turns++;
  if (isHero(u)) {
    B.heroTurns = (B.heroTurns || 0) + 1;
    if (B.heroTurns > CALM_TURNS) {
      B.rage = Math.floor((B.heroTurns - CALM_TURNS + 2) / 3);
      if (!B.ragedAnnounced) { B.ragedAnnounced = true; banner('The foe grows furious!'); sfx('roar'); log('The enemy grows furious: +10% damage every round from now on.'); }
    }
  }
  for (const s of u.skills) if (s.cd > 0) s.cd--;
  u.st.guard = 0; u.st.riposte = 0; u.st.airborne = 0;
  if (isClass(u, 'bard')) for (const a of alive().filter(x => x !== u && x.side === u.side && dist(x, u) <= 2)) a.ct += 12;
  if (has(u, 'goad')) for (const f of alive().filter(x => x.side !== u.side && dist(x, u) <= 2)) { f.st.taunt = Math.max(f.st.taunt || 0, 1); f.st.tauntBy = u; refreshView(f); }
  u.tmp = null;
  if (has(u, 'chaos')) {
    const stat = pick(['atk', 'mag', 'def', 'res', 'spd']);
    u.tmp = { [stat]: 8 };
    fxText(u, `+8 ${stat.toUpperCase()}`, '#ffd23f');
  }
  if (u.regen) heal(u, u.maxHp * u.regen);
  if (has(u, 'crown')) { u.hp = Math.max(1, u.hp - Math.round(u.maxHp * 0.05)); refreshView(u); }
  if (B.grid[u.y][u.x] === T.LAVA && !u.fireproof && !u.fly) { await enterTile(u); await sleep(300); }
  if (!u.dead && u.st.poison > 0) {
    const by = u.st.poisonBy, n = damage(u, u.st.poisonDmg, null, { quiet: true });
    burst('poison', u, 8); log(`${u.name} suffers from poison.`);
    if (u.st.leech && by && !by.dead && n > 0) heal(by, n);
    await sleep(300);
  }
  if (!u.dead && u.st.doom > 0 && --u.st.doom === 0) {
    fxText(u, 'DOOM', '#c44dff');
    burst('dark', u, 26);
    sfx('death');
    log(`Doom falls on ${u.name}.`);
    damage(u, Math.round(u.maxHp * (u.boss ? 0.15 : 0.45)), null);
    await sleep(400);
  }
  if (!u.dead && u.st.burn > 0 && !u.fireproof) { damage(u, u.st.burnDmg, null, { quiet: true }); burst('fire', u, 8); log(`${u.name} burns.`); await sleep(300); }
  if (u.dead) return true;
  if (u.pending) {
    const p = u.pending;
    u.pending = null;
    await useSkill(u, p.s, p.tx, p.ty, 'delayed');
    if (u.dead || !B || B.over) return true;
  }
  if (u.st.sleep > 0) {
    u.st.sleep--;
    fxText(u, 'Zzz', '#c9f7ff');
    log(`${u.name} sleeps.`);
    refreshView(u);
    await sleep(450);
    return true;
  }
  if (u.st.stun) {
    u.st.stun = 0;
    fxText(u, 'Stunned', '#ffd23f');
    sfx('stun');
    log(`${u.name} is stunned.`);
    refreshView(u);
    await sleep(550);
    return true;
  }
  return false;
}
function endTurn(u) {
  if (u.dead) return;
  u.ct -= 100 - (u.moved ? 0 : 20) - (u.acted ? 0 : 20) + (u.ctDebt || 0);
  u.ctDebt = 0;
  for (const k of ['poison', 'burn', 'slow', 'taunt', 'vuln', 'rally', 'blind', 'shock', 'thorns', 'root', 'disarm', 'weak', 'oil', 'wet', 'movUp', 'imbue', 'confuse']) if (u.st[k] > 0) u.st[k]--;
  if (u.st.resolve > 0) u.st.resolve--;
  if (u.st.charm > 0 && --u.st.charm === 0 && u.origSide) { u.side = u.origSide; u.origSide = null; u.st.resolve = 2; fxText(u, 'Snaps out', '#ff8ad8', true); }
  if (!u.st.taunt) u.st.tauntBy = null;
  if (has(u, 'clockwork') && u.turns % 3 === 0) { u.ct += 100; fxText(u, 'Tick!', '#ffd23f'); }
  u.tmp = null;
  refreshView(u);
}

// ---------- player control ----------
// Phones stack the board above the panel: bring the board back into view when a hero's turn starts.
const narrow = () => window.innerWidth <= 920;
function showBoard() {
  if (!narrow()) return;
  const el = document.getElementById('game'), r = el.getBoundingClientRect();
  const bar = document.querySelector('#side .actions');
  const bottom = window.innerHeight - (bar ? bar.offsetHeight : 0);
  if (r.top < 0 || r.bottom > bottom) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}
const buzz = ms => { try { if (navigator.vibrate) navigator.vibrate(ms); } catch (e) { /* unsupported */ } };
function playerTurn(u) {
  return new Promise(res => {
    B.resolveTurn = res;
    B.mode = 'move';
    B.reach = reach(u);
    B.sel = null; B.pending = null;
    renderPanel();
    showBoard();
  });
}
function finishTurn() {
  if (!B || !B.resolveTurn || B.busy) return;
  const r = B.resolveTurn;
  B.resolveTurn = null; B.mode = null; B.pending = null;
  r();
}
function afterHeroStep(u) {
  if (!B || B.over) return;
  if (u.dead || (u.moved && u.acted)) { finishTurn(); return; }
  B.mode = u.moved ? null : 'move';
  if (B.mode) B.reach = reach(u);
  B.sel = null; B.pending = null;
  renderPanel();
}
async function doMove(u, k) {
  const v = B.reach.get(k);
  B.busy = true;
  B.startPos = v.risk ? null : { x: u.x, y: u.y };
  B.mode = null;
  renderPanel();
  await moveUnit(u, pathTo(B.reach, k), v.blink);
  B.busy = false;
  if (!checkEnd()) afterHeroStep(u);
}
function undoMove(u) {
  if (!B.startPos || u.acted || B.busy) return;
  u.x = B.startPos.x; u.y = B.startPos.y;
  placeView(u);
  u.moved = false; B.startPos = null;
  afterHeroStep(u);
}
async function doSkill(u, s, x, y) {
  buzz(12);
  B.busy = true;
  await useSkill(u, s, x, y);
  if (!B) return;
  B.busy = false;
  B.startPos = null;
  afterHeroStep(u);
}
// Every tile a skill reaches from where u stands, whether or not anything is there to hit.
function rangeTiles(u, o) {
  if (o.tgt === 'self') {
    if (o.aoe) return areaTiles(u, o, u.x, u.y);
    if (o.shape !== 'multi') return [];
  }
  const [a, b] = rangeOf(u, o), out = [];
  for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
    const d = Math.abs(u.x - x) + Math.abs(u.y - y);
    if (d < Math.max(a, 1) || d > b) continue;
    if (o.shape === 'line' && x !== u.x && y !== u.y) continue;
    if (o.shape === 'line' && !lineTiles(u, o, x, y).some(([tx, ty]) => tx === x && ty === y)) continue;
    if ((needsLos(o) || (o.shape === 'multi' && !o.lob)) && !los(u.x, u.y, x, y)) continue;
    out.push([x, y]);
  }
  return out;
}
function selectSkill(i) {
  const u = B.active;
  sfx('select');
  if (B.mode === 'skill' && B.sel === i) { afterHeroStep(u); return; }
  const o = effective(u, u.skills[i]);
  B.mode = 'skill'; B.sel = i; B.selO = o;
  B.targets = new Set();
  for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) if (validTarget(u, o, x, y)) B.targets.add(key(x, y));
  B.rangeTiles = rangeTiles(u, o);
  B.pending = o.tgt === 'self' && B.targets.size ? { x: u.x, y: u.y } : null;
  // only one thing to aim at: aim at it, so a single tap on Confirm (or the tile) fires
  if (!B.pending && B.targets.size === 1) { const [x, y] = [...B.targets][0].split(',').map(Number); B.pending = { x, y }; }
  renderPanel();
}
function onTap(g, touch) {
  if (!B || B.busy || B.over || !g) return;
  const u = B.active;
  const mine = u && isHero(u) && B.resolveTurn && !env.auto;
  const who = unitAt(g.x, g.y);
  if (mine && B.mode === 'move') {
    const v = B.reach.get(key(g.x, g.y));
    if (v && v.stop && !(g.x === u.x && g.y === u.y)) { doMove(u, key(g.x, g.y)); return; }
  }
  if (mine && B.mode === 'skill' && B.targets.has(key(g.x, g.y))) {
    if (touch && !(B.pending && B.pending.x === g.x && B.pending.y === g.y)) { B.pending = g; sfx('click'); renderPanel(); return; }
    doSkill(u, u.skills[B.sel], g.x, g.y);
    return;
  }
  B.inspect = who || { tile: g };
  renderPanel();
}

// ---------- AI ----------
function scoreAction(u, o, list) {
  if (o.kind === 'summon') return B.units.filter(t => t.summoned && !t.dead && t.side === u.side).length < 2 ? 20 : 0;
  if (o.trap) return 0; // traps are a player's tool
  let s = 0;
  for (const { t, w } of list) {
    const foe = t.side !== u.side;
    if (o.kind === 'heal') { if (!foe) s += Math.min(healRoom(t), powerVal(u, o) * w) * 1.2 + (o.cleanse && (t.st.poison || t.st.burn) ? 3 : 0); continue; }
    if (o.kind === 'shield') { if (!foe) s += Math.min(powerVal(u, o) * w, t.maxHp - t.shield) * (t.hp < t.maxHp * 0.85 ? 0.7 : 0.35); continue; }
    if (o.kind === 'buff') {
      if (foe) s += (o.taunt ? 4 : 0) + (o.blind ? 6 : 0) + (o.vuln ? 4 + t.hp * 0.1 : 0) + (o.ctTake ? o.ctTake / 10 : 0) + (o.swap ? 1 : 0) + (o.slow && !(t.st.slow > 0) ? 4 : 0)
        + (o.root && !t.boss && !(t.st.root > 0) ? 3 : 0) + (o.disarm && !t.boss && !(t.st.disarm > 0) ? 5 + t.atk * 0.2 : 0) + (o.weak && !(t.st.weak > 0) ? 4 + t.atk * 0.2 : 0)
        + (o.sleep && !t.boss && !(t.st.sleep > 0) ? 8 : 0) + (o.confuse && !t.boss && !(t.st.confuse > 0) ? 9 : 0) + (o.oil && !(t.st.oil > 0) ? 3 : 0) + (o.wet && !(t.st.wet > 0) ? 2 : 0)
        + (o.dispel ? t.shield * 0.5 + BUFFS.filter(k => t.st[k] > 0).length * 4 : 0) + (o.stealShield ? t.shield * 0.8 : 0) + (o.ctZero ? Math.max(0, t.ct) / 10 : 0) + (o.push ? 1 : 0)
        + (o.charm && !t.boss && !t.st.charm && !(t.st.resolve > 0) && alive().filter(x => x.side === t.side).length > 1 ? 10 + t.atk * 0.5 : 0) + (o.doom && !t.st.doom ? t.maxHp * (t.boss ? 0.1 : 0.25) : 0) + (o.cdLock ? 3 + (t.boss ? 6 : 0) : 0) + (o.stun && !t.boss ? 8 : 0);
      else s += (o.rally ? 6 : 0) + (o.ctGive && t !== u ? 14 : 0) + (o.ward && !(t.st.ward > 0) ? 5 + (1 - t.hp / t.maxHp) * 8 : 0)
        + (o.stealth && t === u ? (u.hp < u.maxHp * 0.5 ? 8 : 2) : 0) + (o.thornsUp ? 4 : 0) + (o.purify ? debuffCount(t) * 4 : 0) + (o.movUp ? 2 : 0)
        + (o.focus && !t.st.focus ? 5 : 0) + (o.imbue && !(t.st.imbue > 0) ? 6 : 0) + (o.brace ? 3 : 0) + (o.counter ? 2 : 0);
      continue;
    }
    if (!foe && has(t, 'hollow') && t !== u) continue;
    let d = calcDmg(u, t, o) * w * hitsOf(o);
    if (t.lure && foe) s += 6;
    const kills = d + 0.5 >= t.hp + t.shield || (o.cull && !t.boss && t.hp - d <= t.maxHp * o.cull);
    d = Math.min(d, t.hp + t.shield);
    const extra = kills ? 25 : (o.stun && !t.boss ? 8 : 0) + (o.slow ? 3 : 0) + (o.poison ? o.poison * 2 : 0) + (o.burn ? 4 : 0) + (o.vuln ? 4 : 0) + (o.shock ? 3 : 0)
      + (o.detonate === 'poison' && t.st.poison > 0 ? t.st.poison * t.st.poisonDmg : 0) + (o.detonate === 'burn' && t.st.burn > 0 ? t.st.burn * t.st.burnDmg * 2 : 0);
    s += foe ? d + extra : -(d + extra) * 1.5;
  }
  if ((o.hpCost || o.bloodpact) && u.hp < u.maxHp * 0.35) s -= 15;
  if (o.kind === 'shield' && o.guard) s += 3;
  if (o.thornsUp && s > 0) s += 2;
  return s;
}
function distField(u, targets) {
  const d = Array.from({ length: GH }, () => Array(GW).fill(Infinity));
  const q = [];
  for (const t of targets) { d[t.y][t.x] = 0; q.push([t.x, t.y, 0]); }
  while (q.length) {
    q.sort((a, b) => a[2] - b[2]);
    const [x, y, c] = q.shift();
    if (c > d[y][x]) continue;
    for (const [dx, dy] of DIRS) {
      const nx = x + dx, ny = y + dy;
      if (!inb(nx, ny)) continue;
      const nc = c + moveCost(u, nx, ny) + (hazard(u, nx, ny) ? 4 : 0);
      if (nc < d[ny][nx]) { d[ny][nx] = nc; q.push([nx, ny, nc]); }
    }
  }
  return d;
}
function planAI(u) {
  const R = reach(u);
  const ox = u.x, oy = u.y;
  const hostile = alive().filter(t => t.side !== u.side);
  const taunter = u.st.taunt > 0 && u.st.tauntBy && !u.st.tauntBy.dead ? u.st.tauntBy : null;
  let best = null;
  for (const v of R.values()) {
    if (!v.stop) continue;
    u.x = v.x; u.y = v.y;
    let pos = (inCover(u) ? 1 : 0) - v.c * 0.05 - v.risk * 1.2 - hazard(u, v.x, v.y) * 0.8;
    if (u.ai === 'ranged') pos += (Math.min(...hostile.map(t => dist(t, v))) >= 2 ? 3 : -2) + (onHill(u) ? 1.5 : 0);
    for (const s of u.skills) {
      if (s.cd > 0 || u.st.disarm > 0) continue;
      const o = effective(u, s);
      if (o.mimic && !o.mimicked) continue;
      const cands = [];
      if (o.tgt === 'self') cands.push([u.x, u.y]);
      else {
        const [, b] = rangeOf(u, o);
        for (let y = Math.max(0, u.y - b); y <= Math.min(GH - 1, u.y + b); y++) for (let x = Math.max(0, u.x - b); x <= Math.min(GW - 1, u.x + b); x++) cands.push([x, y]);
      }
      for (const [x, y] of cands) {
        if (!validTarget(u, o, x, y)) continue;
        const list = hitList(u, o, x, y, true);
        if (!list.length) continue;
        if (taunter && (o.kind === 'phys' || o.kind === 'mag') && !list.some(e => e.t === taunter)) continue;
        const sc = scoreAction(u, o, list);
        if (sc <= 0) continue;
        if (!best || sc + pos > best.score) best = { score: sc + pos, v, s, x, y };
      }
    }
  }
  u.x = ox; u.y = oy;
  if (best) return { path: pathTo(R, key(best.v.x, best.v.y)), blink: best.v.blink, skill: best.s, tx: best.x, ty: best.y };
  const targets = taunter ? [taunter] : hostile.filter(t => targetable(u, t));
  const df = distField(u, targets.length ? targets : hostile);
  let bv = null, bs = Infinity;
  for (const v of R.values()) {
    if (!v.stop) continue;
    const dd = df[v.y][v.x];
    const sc = (u.ai === 'ranged' ? Math.abs(dd - 3) : dd) - (B.grid[v.y][v.x] === T.COVER ? 0.3 : 0) + v.c * 0.01 + v.risk + hazard(u, v.x, v.y);
    if (sc < bs) { bs = sc; bv = v; }
  }
  return { path: bv ? pathTo(R, key(bv.x, bv.y)) : null, blink: bv && bv.blink };
}
async function aiTurn(u) {
  B.busy = true;
  renderPanel();
  await sleep(300);
  const plan = planAI(u);
  if (plan.path && plan.path.length > 1) await moveUnit(u, plan.path, plan.blink);
  if (plan.skill && !B.over && !u.dead) {
    // the plan was made from the destination; re-check in case the walk changed things
    const o = effective(u, plan.skill);
    if (validTarget(u, o, plan.tx, plan.ty)) await useSkill(u, plan.skill, plan.tx, plan.ty);
  } else await sleep(150);
  if (B) B.busy = false;
}

// ---------- side panel ----------
function statusText(u) {
  const st = u.st, out = [];
  if (u.shield > 0) out.push(tip(`Shield ${u.shield}`, 'shield'));
  if (u.side === 'foe' && B.rage) out.push(tip(`Furious +${B.rage * 10}%`, 'rage'));
  if (st.stun) out.push(tip('Stunned', 'stun'));
  if (st.poison > 0) out.push(tip(`Poisoned (${st.poison})`, 'poison'));
  if (st.burn > 0) out.push(tip(`Burning (${st.burn})`, 'burn'));
  if (st.slow > 0) out.push(tip(`Slowed (${st.slow})`, 'slow'));
  if (st.taunt > 0) out.push(tip(`Taunted (${st.taunt})`, 'taunt'));
  if (st.vuln > 0) out.push(tip(`Exposed +${Math.round((st.vulnAmt || 0.3) * 100)}% (${st.vuln})`, 'vuln'));
  if (st.rally > 0) out.push(tip(`Rallied (${st.rally})`, 'rally'));
  if (st.blind > 0) out.push(tip(`Blinded (${st.blind})`, 'blind'));
  if (st.stealth) out.push(tip('Stealthed', 'stealth'));
  if (st.airborne) out.push(tip('Airborne', 'airborne'));
  if (st.shock > 0) out.push(tip(`Shocked (${st.shock})`, 'shock'));
  if (st.charm > 0) out.push(tip(`Charmed (${st.charm})`, 'charm'));
  if (st.resolve > 0) out.push(tip('Can\'t be charmed', 'resolve'));
  if (st.sleep > 0) out.push(tip(`Asleep (${st.sleep})`, 'sleep'));
  if (st.confuse > 0) out.push(tip(`Confused (${st.confuse})`, 'confuse'));
  if (st.root > 0) out.push(tip(`Rooted (${st.root})`, 'root'));
  if (st.disarm > 0) out.push(tip(`Disarmed (${st.disarm})`, 'disarm'));
  if (st.weak > 0) out.push(tip(`Weakened −30% (${st.weak})`, 'weak'));
  if (st.oil > 0) out.push(tip(`Oiled (${st.oil})`, 'oil'));
  if (st.wet > 0) out.push(tip(`Wet (${st.wet})`, 'wet'));
  if (st.focus) out.push(tip('Focused +60%', 'focus'));
  if (st.movUp > 0) out.push(tip(`+1 MOV (${st.movUp})`, 'movUp'));
  if (st.imbue > 0) out.push(tip(`Imbued: ${st.imbueKind} (${st.imbue})`, 'imbue'));
  if (u.pending) out.push(tip(`Charging ${SKILLS[u.pending.s.id].name}`, 'pending'));
  if (st.doom > 0) out.push(tip(`Doomed in ${st.doom}`, 'doom'));
  if (st.ward > 0) out.push(tip(`Ward ×${st.ward}`, 'ward'));
  const th = thornsNow(u);
  if (th > 0) out.push(tip(`Thorns ${th}`, 'thorns'));
  if (u.rampart) out.push(tip('Rampart', 'rampart'));
  if (st.guard) out.push(tip('Guarding', 'guard'));
  if (st.riposte) out.push(tip('Riposte ready', 'riposte'));
  if (inCover(u)) out.push(tip('In cover', 'cover'));
  if (onHill(u)) out.push(tip('High ground', 'hill'));
  return out.flatMap((x, i) => i ? [' · ', x] : [x]);
}
function unitCard(u, withSkills) {
  const extra = [u.fly ? 'Flying' : null, u.phase ? 'Passes walls' : null, u.fireproof ? 'Fireproof' : null, u.info].filter(Boolean).join(' · ');
  return h('div', { class: 'card' },
    h('div', { class: 'card-head' }, sprImg(u.spr, u.side === 'foe' ? 'flip' : ''),
      h('div', { class: 'who' }, h('b', {}, u.name), bar(u.hp, u.maxHp, u.side === 'foe', u.shield), `${u.hp}/${u.maxHp} HP${u.shield ? ` +${u.shield} shield` : ''}`)),
    h('div', { class: 'stats' }, `ATK ${u.atk} · MAG ${u.mag} · DEF ${u.def} · RES ${u.res} · SPD ${spdOf(u)} · MOV ${u.mov}`),
    extra ? h('div', { class: 'stats' }, extra) : null,
    h('div', { class: 'status' }, statusText(u)),
    withSkills ? h('div', { class: 'skill-list' }, u.skills.map(s => {
      const o = skStats(u, s);
      return h('div', {}, h('b', {}, o.name), s.cd > 0 ? h('span', {}, ` (ready in ${s.cd})`) : null, h('br'), h('span', {}, tipText(describe(o, u) + (o.txt ? '. ' + o.txt : ''))));
    })) : null);
}
function tileCard(x, y) {
  const t = B.grid[y][x];
  return h('div', { class: 'card' }, h('b', { class: 'px' }, THEMES[B.theme][t]), h('div', { class: 'stats' }, TERRAIN_HELP[t]));
}
// "Confirm: Goblin −12", "Confirm: KO Bat", "Confirm: 3 targets"
function confirmLabel(u) {
  const o = B.selO, p = B.pending;
  if (!o || !p || !(o.kind === 'phys' || o.kind === 'mag') || o.gamble) return 'Confirm';
  const list = hitList(u, o, p.x, p.y, true), seen = new Map();
  for (const { t, w } of list) seen.set(t, (seen.get(t) || 0) + w);
  if (seen.size !== 1) return seen.size ? `Confirm: ${seen.size} targets` : 'Confirm';
  const [[t, w]] = [...seen];
  const d = Math.round(calcDmg(u, t, o) * w * hitsOf(o));
  return d >= t.hp + t.shield ? `Confirm: KO ${t.name}` : `Confirm: ${t.name} −${d}`;
}
function hintText() {
  const u = B.active;
  if (B.mode === 'move') return 'Tap a blue tile to move, or choose an action. Tap anything to inspect it.';
  if (B.mode === 'skill') {
    const o = B.selO;
    const what = `${o.name}: ${describe(o, u)}.${o.txt ? ' ' + o.txt : ''}`;
    if (!B.targets.size) return `${what} No targets in range${needsLos(o) ? ' or sight' : ''}.`;
    if (B.pending) return `${what} Tap again or press Confirm.`;
    return `${what} Tap a highlighted tile.`;
  }
  if (u.moved && u.acted) return '';
  return u.acted ? 'Move, or end your turn.' : 'Choose an action, or end your turn.';
}
function renderPanel() {
  if (!B || !env.side) return;
  const u = B.active;
  const mine = u && isHero(u) && B.resolveTurn && !B.busy && !env.auto;
  const kids = [h('div', { class: 'order' }, h('span', { class: 'lbl' }, 'NEXT'),
    predictOrder(9).map((t, i) => h('img', { class: `spr ${t.side}${i === 0 ? ' now' : ''}${t.side === 'foe' ? ' flip' : ''}`, src: spriteURL(t.spr), title: t.name, alt: t.name })))];
  const shown = B.inspect && !B.inspect.dead ? B.inspect : u;
  if (shown && shown.tile) kids.push(tileCard(shown.tile.x, shown.tile.y));
  else if (shown) kids.push(unitCard(shown, !(mine && shown === u)));
  if (shown && !shown.tile && shown !== u) kids.push(h('div', { class: 'hint' }, `Shaded tiles: where ${shown.name} can move this turn${shown.st.root > 0 ? ' (rooted)' : ''}.`));
  if (mine) {
    kids.push(h('div', { class: 'actions' },
      h('button', { class: 'btn' + (B.mode === 'move' ? ' sel' : ''), disabled: u.moved, onclick: () => { sfx('click'); if (B.mode === 'move') { B.mode = null; renderPanel(); } else afterHeroStep(u); } }, 'Move'),
      u.moved && !u.acted && B.startPos ? h('button', { class: 'btn', onclick: () => undoMove(u) }, 'Undo move') : null,
      u.skills.map((s, i) => {
        const o = effective(u, s);
        return h('button', { class: 'btn' + (B.mode === 'skill' && B.sel === i ? ' sel' : ''), disabled: u.acted || s.cd > 0 || u.st.disarm > 0, title: `${o.name}: ${describe(o, u)}`, onclick: () => selectSkill(i) },
          o.name, s.cd > 0 ? h('span', { class: 'cd' }, ` ${s.cd}`) : null);
      }),
      B.mode === 'skill' && B.pending ? h('button', { class: 'btn go', onclick: () => doSkill(u, u.skills[B.sel], B.pending.x, B.pending.y) }, confirmLabel(u)) : null,
      h('button', { class: 'btn', onclick: () => { sfx('click'); finishTurn(); } }, 'End turn'),
      h('div', { class: 'hint' }, hintText()),
    ));
  } else kids.push(h('div', { class: 'actions waiting' }, h('div', { class: 'hint' }, u && !B.over ? `${u.name} is acting…` : '')));
  kids.push(h('div', { class: 'log' }, B.log.slice(-5).map(l => h('div', {}, l))));
  env.side.replaceChildren(...kids);
}

// ---------- the Phaser scene ----------
function tw(cfg) {
  return new Promise(res => {
    if (!scene || !cfg.targets) { res(); return; }
    scene.tweens.add({ ...cfg, duration: Math.max(1, (cfg.duration || 200) * env.speed), onComplete: () => res() });
  });
}
function counter(ms, fn) {
  return new Promise(res => {
    if (!scene) { res(); return; }
    scene.tweens.addCounter({ from: 0, to: 1, duration: Math.max(1, ms * env.speed), onUpdate: t => fn(t.getValue()), onComplete: () => { fn(1); res(); } });
  });
}
const viewAlpha = u => u.st.stealth || u.st.airborne ? 0.45 : u.spr === 'ghost' ? 0.8 : 1;
function placeView(u) {
  if (!u.view) return;
  u.view.setPosition(u.x * TS, u.y * TS);
  u.view.setDepth(10 + u.y * 10);
}
async function tweenView(u, ms, hop) {
  if (!u.view) return;
  const sx = u.view.x, sy = u.view.y, ex = u.x * TS, ey = u.y * TS;
  await counter(ms, p => {
    u.view.x = sx + (ex - sx) * p;
    u.view.y = sy + (ey - sy) * p - (hop ? Math.sin(p * Math.PI) * 30 : 0);
    u.view.setDepth(10 + (u.view.y / TS) * 10);
  });
  placeView(u);
}
async function lunge(u, x, y) {
  const dx = Math.sign(x - u.x) * TS * 0.35, dy = Math.sign(y - u.y) * TS * 0.35;
  await counter(180, p => { const k = p < 0.5 ? p * 2 : (1 - p) * 2; u.view.x = u.x * TS + dx * k; u.view.y = u.y * TS + dy * k; });
  placeView(u);
}
async function pulse(u) {
  const sp = u.view.list[1];
  const s0 = sp.scaleX;
  await counter(220, p => sp.setScale(s0 * (1 + Math.sin(p * Math.PI) * 0.15)));
  sp.setScale(s0);
}
function projectile(u, x, y, color, arc) {
  const img = scene.add.image(u.x * TS + TS / 2, u.y * TS + TS / 2, 'px').setScale(3).setTint(color).setDepth(900);
  const trail = scene.add.particles(0, 0, 'px', { follow: img, lifespan: 220, scale: { start: 1.2, end: 0 }, tint: color, frequency: 20, alpha: { start: 0.8, end: 0 } }).setDepth(899);
  const sx = img.x, sy = img.y, ex = x * TS + TS / 2, ey = y * TS + TS / 2;
  const d = Math.abs(u.x - x) + Math.abs(u.y - y);
  return counter(60 * d + 90, p => {
    img.x = sx + (ex - sx) * p;
    img.y = sy + (ey - sy) * p - (arc ? Math.sin(p * Math.PI) * (20 + d * 8) : 0);
  }).then(() => { img.destroy(); scene.time.delayedCall(250, () => trail.destroy()); });
}
function areaFlash(tiles, color) {
  const g = scene.add.graphics().setDepth(6);
  g.fillStyle(color, 0.55);
  for (const [x, y] of tiles) g.fillRect(x * TS, y * TS, TS, TS);
  scene.tweens.add({ targets: g, alpha: 0, duration: 420 * env.speed + 1, onComplete: () => g.destroy() });
}
function flash(t) {
  if (!t.view) return;
  const sp = t.view.list[1];
  sp.setTintFill(0xffffff);
  scene.time.delayedCall(140 * Math.max(env.speed, 0.1), () => sp.active && sp.clearTint());
}
function fxText(t, text, color, small) {
  if (!scene || !t.view && t.x == null) return;
  const x = t.x * TS + TS / 2, y = t.y * TS + 10;
  const txt = scene.add.text(x, y, text, { fontFamily: '"Press Start 2P", monospace', fontSize: small || text.length > 7 ? '12px' : '18px', color, stroke: '#000', strokeThickness: 5 })
    .setOrigin(0.5).setDepth(1000);
  scene.tweens.add({ targets: txt, y: y - 30, alpha: { from: 1, to: 0 }, ease: 'Cubic.easeIn', duration: 1000 * Math.max(env.speed, 0.05), onComplete: () => txt.destroy() });
}
const BURSTS = {
  hit: { tint: [0xffffff, 0xffe0a0], speed: { min: 60, max: 160 }, lifespan: 260, scale: { start: 1, end: 0 } },
  fire: { tint: [0xffd23f, 0xff8a3d, 0xe5574f], speed: { min: 30, max: 120 }, lifespan: 520, scale: { start: 1.4, end: 0 }, gravityY: -140, blendMode: 'ADD' },
  heal: { tint: [0x7dff8a, 0xd8ffd0], speed: { min: 10, max: 50 }, lifespan: 700, scale: { start: 1, end: 0 }, gravityY: -90 },
  shield: { tint: [0x9fd8ff, 0xffffff], speed: { min: 40, max: 90 }, lifespan: 500, scale: { start: 1, end: 0 }, blendMode: 'ADD' },
  dark: { tint: [0x9a5aff, 0x3a2a5a], speed: { min: 20, max: 80 }, lifespan: 600, scale: { start: 1.3, end: 0 }, gravityY: -60 },
  poison: { tint: [0x8be04e, 0x4a8a2a], speed: { min: 10, max: 40 }, lifespan: 600, scale: { start: 1, end: 0 }, gravityY: -60 },
  dust: { tint: [0x9a8a7a, 0x5a4a3a], speed: { min: 30, max: 90 }, lifespan: 500, scale: { start: 1.5, end: 0 } },
};
function burst(kind, at, n) {
  if (!scene || !scene.bursts || env.speed < 0.05) return;
  scene.bursts[kind].explode(n, at.x * TS + TS / 2, at.y * TS + TS / 2);
}
function banner(text) {
  const t = scene.add.text(GW * TS / 2, GH * TS / 2, text, { fontFamily: '"Press Start 2P", monospace', fontSize: '28px', color: '#f2c94c', stroke: '#000', strokeThickness: 8 })
    .setOrigin(0.5).setDepth(2000).setAlpha(0).setScale(0.6);
  scene.tweens.add({ targets: t, alpha: 1, scale: 1, duration: 400 * env.speed + 1, yoyo: true, hold: 900 * env.speed, onComplete: () => t.destroy() });
}

function makeView(u) {
  const c = scene.add.container(u.x * TS, u.y * TS);
  const shadow = scene.add.rectangle(TS / 2, TS - 6, 32 * Math.min(u.scale || 1, 1.4), 8, 0x000000, 0.3);
  const sp = scene.add.image(TS / 2, TS - 2, 's_' + u.spr).setOrigin(0.5, 1).setScale(S * (u.scale || 1));
  sp.flipX = u.side === 'foe';
  const g = scene.add.graphics();
  c.add([shadow, sp, g]);
  u.view = c;
  if (u.fly) scene.tweens.add({ targets: sp, y: TS - 10, duration: 500, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
  if (u.dead) c.setVisible(false);
  placeView(u);
  refreshView(u);
}
function refreshView(u) {
  if (!u.view || !scene) return;
  const g = u.view.list[2];
  g.clear();
  u.view.setAlpha(u.dead ? u.view.alpha : viewAlpha(u));
  if (u.dead) return;
  const bx = 8, by = TS - 8, bw = TS - 16;
  const total = Math.max(u.maxHp, u.hp + u.shield);
  g.fillStyle(0x120b18); g.fillRect(bx - 2, by - 2, bw + 4, 8);
  g.fillStyle(u.side === 'hero' ? 0x74d65e : 0xe5574f); g.fillRect(bx, by, Math.round(bw * u.hp / total), 4);
  if (u.shield > 0) { g.fillStyle(0x9fd8ff); g.fillRect(bx + Math.round(bw * u.hp / total), by, Math.round(bw * u.shield / total), 4); }
  const pips = [];
  if (u.st.poison > 0) pips.push(0x8be04e);
  if (u.st.burn > 0) pips.push(0xff8a3d);
  if (u.st.slow > 0) pips.push(0x7fd8ff);
  if (u.st.stun) pips.push(0xffe14d);
  if (u.st.taunt > 0) pips.push(0xff4d4d);
  if (u.st.vuln > 0) pips.push(0xc44dff);
  if (u.st.rally > 0) pips.push(0xffb03b);
  if (u.st.blind > 0) pips.push(0x777777);
  if (u.st.guard || u.st.riposte) pips.push(0xd8d8e8);
  if (u.st.shock > 0) pips.push(0xffe14d);
  if (u.st.charm > 0) pips.push(0xff8ad8);
  if (u.st.doom > 0) pips.push(0x5a1d8a);
  if (u.st.ward > 0) pips.push(0xffffff);
  if (u.st.sleep > 0 || u.st.confuse > 0) pips.push(0xb0a0ff);
  if (u.st.root > 0 || u.st.disarm > 0) pips.push(0x8a6a4a);
  if (u.st.wet > 0 || u.st.oil > 0) pips.push(u.st.oil > 0 ? 0xc8a040 : 0x4a8cff);
  pips.forEach((col, i) => { g.fillStyle(0x000000); g.fillRect(2 + i * 13, 2, 12, 12); g.fillStyle(col); g.fillRect(4 + i * 13, 4, 8, 8); });
}

export class BattleScene extends Phaser.Scene {
  constructor() { super('battle'); }
  create() {
    scene = this;
    const b = B;
    b.tiles = b.grid.map((row, y) => row.map((t, x) => this.add.image(x * TS, y * TS,
      tileKey(b.theme, t, ANIMATED.has(t) ? (b.vari[y][x] % 3) : b.vari[y][x] % TILE_VARIANTS[t])).setOrigin(0).setScale(S)));
    const grid = this.add.graphics().setDepth(1);
    grid.fillStyle(0x000000, 0.13);
    for (let x = 1; x < GW; x++) grid.fillRect(x * TS - 1, 0, 2, GH * TS);
    for (let y = 1; y < GH; y++) grid.fillRect(0, y * TS - 1, GW * TS, 2);
    this.ov = this.add.graphics().setDepth(5);
    this.marks = Array.from({ length: 14 }, () => this.add.text(0, 0, '', { fontFamily: '"Press Start 2P", monospace', fontSize: '16px', color: '#fff', stroke: '#000', strokeThickness: 5 })
      .setOrigin(0.5).setDepth(950).setVisible(false));
    this.bursts = {};
    for (const [k, cfg] of Object.entries(BURSTS)) this.bursts[k] = this.add.particles(0, 0, 'px', { ...cfg, emitting: false }).setDepth(800);
    for (const u of b.units) makeView(u);
    this.time.addEvent({ delay: 450, loop: true, callback: () => {
      if (!B || B !== b) return;
      b.frame++;
      for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) if (ANIMATED.has(b.grid[y][x])) b.tiles[y][x].setTexture(tileKey(b.theme, b.grid[y][x], (b.frame + b.vari[y][x]) % 3));
    } });
    const cell = p => { const x = Math.floor(p.worldX / TS), y = Math.floor(p.worldY / TS); return inb(x, y) ? { x, y } : null; };
    this.input.on('pointermove', p => { if (B && !p.wasTouch) B.hover = cell(p); });
    this.input.on('gameout', () => { if (B) B.hover = null; });
    // a drag isn't a tap; a long press only inspects, so it can never move or attack by accident
    let down = null;
    this.input.on('pointerdown', p => { down = { x: p.x, y: p.y, t: p.downTime || performance.now() }; });
    this.input.on('pointerup', p => {
      const d = down; down = null;
      if (d && Math.hypot(p.x - d.x, p.y - d.y) > 14 * (this.scale.displayScale.x || 1)) return;
      if (d && (p.upTime || performance.now()) - d.t > 450) { const g = cell(p); if (B && g && !B.busy) { B.inspect = unitAt(g.x, g.y) || { tile: g }; renderPanel(); buzz(8); } return; }
      onTap(cell(p), p.wasTouch);
    });
    this.events.once('shutdown', () => { if (scene === this) scene = null; });
    battleLoop(b);
  }
  update(time) {
    const b = B, g = this.ov;
    g.clear();
    this.marks.forEach(m => m.setVisible(false));
    if (!b) return;
    const u = b.active;
    const mine = u && isHero(u) && b.resolveTurn && !env.auto && !b.busy;
    const fill = (x, y, col, a) => { g.fillStyle(col, a); g.fillRect(x * TS, y * TS, TS, TS); };
    const line = (x, y, col, a, w) => { g.lineStyle(w, col, a); g.strokeRect(x * TS + w / 2, y * TS + w / 2, TS - w, TS - w); };
    // A set of tiles drawn as one soft region: each tile filled, but only the region's outer edge
    // outlined, so neighbouring tiles don't double their borders.
    const region = (tiles, col, a, edge, ea, w = 2) => {
      if (!tiles.length) return;
      const set = new Set(tiles.map(([x, y]) => key(x, y)));
      g.fillStyle(col, a);
      for (const [x, y] of tiles) g.fillRect(x * TS, y * TS, TS, TS);
      if (!ea) return;
      g.fillStyle(edge, ea);
      for (const [x, y] of tiles) {
        const X = x * TS, Y = y * TS;
        if (!set.has(key(x, y - 1))) g.fillRect(X, Y, TS, w);
        if (!set.has(key(x, y + 1))) g.fillRect(X, Y + TS - w, TS, w);
        if (!set.has(key(x - 1, y))) g.fillRect(X, Y, w, TS);
        if (!set.has(key(x + 1, y))) g.fillRect(X + TS - w, Y, w, TS);
      }
    };
    const reachTiles = (r, me, pred = () => true) => [...r.values()].filter(v => v.stop && !(v.x === me.x && v.y === me.y) && pred(v)).map(v => [v.x, v.y]);
    // an inspected unit shows where it could move: red for foes, teal for allies
    const insp = b.inspect && !b.inspect.tile && !b.inspect.dead && b.inspect !== u ? b.inspect : null;
    if (insp) {
      const k = b.units.map(x => x.dead ? '' : `${x.x},${x.y}`).join('|') + `|${insp.st.root || 0}|${insp.st.movUp || 0}`;
      if (!b.inspReach || b.inspReach.u !== insp || b.inspReach.k !== k) b.inspReach = { u: insp, k, r: reach(insp) };
      const foe = homeSide(insp) !== 'hero';
      region(reachTiles(b.inspReach.r, insp), foe ? 0xc8504a : 0x4ab0a8, 0.2, foe ? 0xf2b0a8 : 0x9ad8d0, 0.6);
    }
    if (mine && b.mode === 'move' && b.reach) {
      region(reachTiles(b.reach, u, v => !v.risk), 0x5a8fd6, 0.3, 0xb0d0f4, 0.55);
      region(reachTiles(b.reach, u, v => v.risk), 0xd9894a, 0.3, 0xf0c49a, 0.55);
    }
    let preview = null;
    if (mine && b.mode === 'skill') {
      const o = b.selO;
      const help = o.kind === 'heal' || o.kind === 'shield' || o.ctGive || o.hits === 'allies';
      const col = help ? 0x5cbf86 : 0xd65a5a, edge = help ? 0xa8e0c0 : 0xeaa4a4;
      // the whole range faintly, then the tiles you can actually pick a little stronger
      region(b.rangeTiles || [], col, 0.16, edge, 0.55);
      region([...b.targets].map(k => k.split(',').map(Number)), col, 0.2, help ? 0xd8f4e4 : 0xf8d4d4, 0.7);
      const p = b.hover && b.targets.has(key(b.hover.x, b.hover.y)) ? b.hover : b.pending;
      if (p) {
        region(areaTiles(u, o, p.x, p.y), 0xf2c94c, 0.28, 0xf6dc8c, 0.6);
        line(p.x, p.y, 0xfff0b0, 0.9, 3);
        preview = { o, list: hitList(u, o, p.x, p.y, true) };
      }
    }
    if (b.traps) for (const [k, tr] of b.traps) {
      const [x, y] = k.split(',').map(Number);
      g.lineStyle(3, tr.side === 'hero' ? 0xffd23f : 0xff4646, 0.8);
      g.strokeCircle(x * TS + TS / 2, y * TS + TS / 2, 10);
    }
    for (const c of b.units) if (c.pending && !c.dead) {
      const po = skStats(c, c.pending.s);
      region(areaTiles(c, po, c.pending.tx, c.pending.ty), 0xe08a4a, 0.12, 0xf0a870, 0.45 + 0.25 * Math.sin(time / 150));
    }
    if (b.hover && mine) line(b.hover.x, b.hover.y, 0xffffff, 0.5, 2);
    if (u && !u.dead && !b.over && u.view) {
      const pl = Math.floor(time / 250) % 2 ? 4 : 2, L = 14, px = u.view.x, py = u.view.y;
      g.fillStyle(0xffe14d, 1);
      for (const [cx, cy, sx, sy] of [[px, py, 1, 1], [px + TS, py, -1, 1], [px, py + TS, 1, -1], [px + TS, py + TS, -1, -1]]) {
        g.fillRect(cx - (sx < 0 ? L : 0), cy - (sy < 0 ? pl : 0), L, pl);
        g.fillRect(cx - (sx < 0 ? pl : 0), cy - (sy < 0 ? L : 0), pl, L);
      }
    }
    if (preview) {
      const totals = new Map();
      for (const { t, w } of preview.list) totals.set(t, (totals.get(t) || 0) + w);
      let i = 0;
      for (const [t, w] of totals) {
        if (i >= this.marks.length) break;
        const o = preview.o;
        let label, col;
        if (o.kind === 'heal') { if (t.side !== u.side) continue; label = '+' + Math.round(Math.max(0, Math.min(healRoom(t), powerVal(u, o) * w))); col = '#7dff8a'; }
        else if (o.kind === 'shield') { if (t.side !== u.side) continue; label = '+' + Math.round(powerVal(u, o) * w); col = '#9fd8ff'; }
        else if (o.kind === 'buff') { label = o.sleep ? 'SLEEP' : o.confuse ? 'CONFUSE' : o.root ? 'ROOT' : o.disarm ? 'DISARM' : o.weak ? 'WEAKEN' : o.dispel ? 'DISPEL' : o.purify ? 'PURIFY' : o.focus ? 'FOCUS' : o.imbue ? 'IMBUE' : o.push ? 'PUSH' : o.charm ? (t.boss ? 'IMMUNE' : 'CHARM') : o.doom ? 'DOOM' : o.cdLock ? 'SILENCE' : o.ward ? 'WARD' : o.taunt ? 'TAUNT' : o.blind ? 'BLIND' : o.vuln ? 'MARK' : o.rally ? 'RALLY' : o.ctGive ? 'HASTE' : o.slow ? 'SLOW' : 'OK'; col = t.side === u.side ? '#7dff8a' : '#ff8080'; }
        else {
          const d = Math.round(calcDmg(u, t, o) * w * hitsOf(o));
          label = o.gamble ? '?' : d >= t.hp + t.shield ? 'KO' : (w < 1 && (o.shape === 'random' || o.shape === 'multi') ? '~' : '-') + d;
          col = t.side === u.side ? '#ff9a9a' : '#ffe14d';
        }
        this.marks[i++].setText(label).setColor(col).setPosition(t.view.x + TS / 2, t.view.y + 18).setVisible(true);
      }
    }
  }
}
