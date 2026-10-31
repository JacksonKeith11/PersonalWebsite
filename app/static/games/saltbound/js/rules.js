// The client's copy of the map rules (terrain, step costs, routes) and how to describe actions.
// The server checks everything again; keep this in step with game.py.

export const W = 30, H = 22;
export const COST = { beach: 1, grass: 1, forest: 2, hills: 2, peak: 2, town: 1 };
export const TERRAIN_NAME = { deep: 'Open water', shoal: 'Shallows', beach: 'Beach', grass: 'Grassland', forest: 'Forest', hills: 'Hills', peak: 'Peak', town: 'Town' };

export const qr = i => [i % W, Math.floor(i / W)];
export const idx = (q, r) => r * W + q;
const EVEN = [[1, 0], [0, -1], [-1, -1], [-1, 0], [-1, 1], [0, 1]];
const ODD = [[1, 0], [1, -1], [0, -1], [-1, 0], [0, 1], [1, 1]];
export function neighbors(i) {
  const [q, r] = qr(i), out = [];
  for (const [dq, dr] of (r & 1 ? ODD : EVEN)) {
    const nq = q + dq, nr = r + dr;
    if (nq >= 0 && nq < W && nr >= 0 && nr < H) out.push(idx(nq, nr));
  }
  return out;
}
function cube(i) { const [q, r] = qr(i); const x = q - (r - (r & 1)) / 2; return [x, r, -x - r]; }
export function dist(a, b) { const A = cube(a), B = cube(b); return Math.max(Math.abs(A[0] - B[0]), Math.abs(A[1] - B[1]), Math.abs(A[2] - B[2])); }
export function within(i, n) {
  const seen = new Set([i]); let edge = [i];
  for (let k = 0; k < n; k++) { const nx = []; for (const t of edge) for (const u of neighbors(t)) if (!seen.has(u)) { seen.add(u); nx.push(u); } edge = nx; }
  return seen;
}

export function terrain(world, game, t) {
  const e = world.elev[t], sea = game.sea;
  if (e <= sea) return 'deep';
  if (e === sea + 1) return game.tide === 'high' ? 'deep' : 'shoal';
  return world.bio[t];
}

export function visibleTiles(game) {
  const out = new Set();
  game.heroes.forEach((hero, h) => {
    if (!hero.alive) return;
    const r = (hero.cls === 'arcanist' ? 3 : 2) + 1;
    for (const t of within(hero.tile, r)) out.add(t);
  });
  return out;
}

export function stepCost(world, game, static_, h, a, b, afloat) {
  const hero = game.heroes[h];
  if (!neighbors(a).includes(b)) return null;
  if (b === world.peak && game.cleared.length < 3) return null;
  const t = terrain(world, game, b);
  if (t === 'deep') return hero.skiff ? [afloat ? 1 : 2, true] : null;
  if (t === 'shoal') return afloat ? [1, true] : [2, false];
  let c = COST[t] ?? 1;
  const key = static_.classes[hero.cls].map.key;
  if (key === 'trailbreaker' && ['forest', 'hills', 'peak'].includes(t)) c = 1;
  if (key === 'wildspeak' && t === 'forest') c = 1;
  return [c + (afloat ? 1 : 0), false];
}

// Where a hero can get to this turn: {cost, prev} keyed by "tile|afloat", plus the best per tile.
export function reach(world, game, static_, h) {
  const hero = game.heroes[h];
  const vis = visibleTiles(game);
  const groupAt = new Set(game.groups.filter(g => vis.has(g.tile)).map(g => g.tile));
  const stops = new Set(groupAt);
  for (const [t, p] of Object.entries(game.places)) {
    if ((p.kind === 'dungeon' && !game.cleared.includes(p.region)) || p.kind === 'peak') stops.add(+t);
  }
  const start = hero.tile + '|' + (hero.afloat ? 1 : 0);
  const cost = { [start]: 0 }, prev = {}, best = new Map();
  const pq = [[0, hero.tile, hero.afloat]];
  while (pq.length) {
    pq.sort((a, b) => a[0] - b[0]);
    const [d, t, af] = pq.shift();
    const key = t + '|' + (af ? 1 : 0);
    if (d > cost[key]) continue;
    if (!best.has(t) || best.get(t).cost > d) best.set(t, { cost: d, key });
    if (t !== hero.tile && stops.has(t)) continue;
    for (const n of neighbors(t)) {
      const st = stepCost(world, game, static_, h, t, n, af);
      if (!st) continue;
      const nd = d + st[0];
      if (nd > hero.moves) continue;
      const nk = n + '|' + (st[1] ? 1 : 0);
      if (cost[nk] === undefined || nd < cost[nk]) { cost[nk] = nd; prev[nk] = key; pq.push([nd, n, st[1]]); }
    }
  }
  return { best, prev, start };
}

export function routeTo(r, t) {
  const b = r.best.get(t);
  if (!b) return null;
  const out = [];
  let k = b.key;
  while (k && k !== r.start) { out.push(+k.split('|')[0]); k = r.prev[k]; }
  return out.reverse();
}

// ------------------------------------------------------------------ describing actions
export function reqText(req) {
  const n = req.n ?? 1;
  if (n === 0) return 'No die';
  if (req.face === 'S') return 'Shield face';
  const bits = [];
  if (req.exact !== undefined) bits.push(`exactly ${req.exact}`);
  if (req.min !== undefined) bits.push(`${req.min}+`);
  if (req.max !== undefined) bits.push(`${req.max} or less`);
  if (req.odd) bits.push('odd');
  if (req.even) bits.push('even');
  if (req.pair) bits.push('a pair');
  if (req.straight) bits.push('a straight');
  if (req.sum_min !== undefined) bits.push(`sum ${req.sum_min}+`);
  const head = req.upto ? `Up to ${n} dice` : n === 1 ? (bits.length ? '' : 'Any die') : `${n} dice`;
  return [head, bits.join(', ')].filter(Boolean).join(': ').replace(/^: /, '');
}

export function checkReq(req, dice) {
  const n = req.n ?? 1;
  if (req.upto ? !(dice.length >= 1 && dice.length <= n) : dice.length !== n) return false;
  const vals = dice.map(d => (typeof d.v === 'number' ? d.v : 0));
  for (let i = 0; i < dice.length; i++) {
    const v = vals[i];
    if (req.face === 'S' && dice[i].v !== 'S') return false;
    if (req.min !== undefined && v < req.min) return false;
    if (req.max !== undefined && v > req.max) return false;
    if (req.exact !== undefined && v !== req.exact) return false;
    if (req.odd && v % 2 === 0) return false;
    if (req.even && (v % 2 || v === 0)) return false;
  }
  if (req.pair && new Set(vals).size !== 1) return false;
  if (req.straight) { const s = [...vals].sort((a, b) => a - b); for (let i = 1; i < s.length; i++) if (s[i] - s[i - 1] !== 1) return false; }
  if (req.sum_min !== undefined && vals.reduce((a, b) => a + b, 0) < req.sum_min) return false;
  return true;
}

export const dieLabel = faces => {
  const nums = faces.filter(f => typeof f === 'number');
  const plain = nums.length === faces.length && nums.every((f, i) => f === i + 1);
  return plain ? 'd' + faces.length : faces.map(f => (f === 'S' ? '◆' : f)).join('·');
};

export const STATUS = {
  burn: { name: 'Burn', icon: 'flame', text: 'Takes this much damage at the end of the round, then it drops by 1.', bad: true },
  poison: { name: 'Poison', icon: 'drop', text: 'Takes this much damage at the start of each round.', bad: true },
  freeze: { name: 'Freeze', icon: 'snow', text: 'Heroes lose their lowest die next round; enemies hit for half.', bad: true },
  shock: { name: 'Shock', icon: 'bolt', text: 'The next hit also hits a neighbour for half.', bad: true },
  weak: { name: 'Weak', icon: 'down', text: 'Deals 25% less damage.', bad: true },
  vuln: { name: 'Vulnerable', icon: 'crack', text: 'Takes 25% more damage.', bad: true },
  stun: { name: 'Stun', icon: 'spark', text: 'Skips its next action.', bad: true },
  armor: { name: 'Armor', icon: 'shield', text: 'Blocks this much damage. Clears at the end of the round.' },
  mark: { name: 'Mark', icon: 'target', text: 'Takes +3 damage from every hit.', bad: true },
  root: { name: 'Root', icon: 'root', text: "Can't change rows or flee.", bad: true },
  doom: { name: 'Doom', icon: 'clock', text: 'Takes this much damage at the end of next round.', bad: true },
  lifeline: { name: 'Lifeline', icon: 'heart', text: 'Heals fully at the end of the round.' },
};
