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
    const r = 3 + (hero.cls === 'arcanist' ? 1 : 0) + (hero.cls === 'ranger' ? 2 : 0) + (hero.skills.includes('wayfinder') ? 1 : 0);
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
  if (req.or_face === 'S') bits.push('or a shield');
  if (req.marked) bits.push('on a Marked enemy');
  const head = req.upto ? `Up to ${n} dice` : n === 1 ? (bits.length ? '' : 'Any die') : `${n} dice`;
  return [head, bits.join(', ')].filter(Boolean).join(': ').replace(/^: /, '');
}

// ------------------------------------------------------------------ dice (keep in step with combat.py)
const TAGS = { F: 'burn', I: 'freeze', P: 'poison' };
export function face(f) {
  if (typeof f === 'number') return [f, null];
  if (f === 'S' || f === 'X') return [0, f];
  if (f === 'W') return [null, 'W'];
  return [+f.slice(1), TAGS[f[0]]];
}
export const topFace = faces => Math.max(0, ...faces.map(f => face(f)[0]).filter(v => v !== null));
export const meanFace = faces => faces.reduce((a, f) => a + (face(f)[1] === 'W' ? topFace(faces) : face(f)[0]), 0) / faces.length;

export function checkHit(req, vals, tags) {
  for (let i = 0; i < vals.length; i++) {
    const v = vals[i], t = tags[i];
    if (t === 'W') continue;
    let ok = true;
    if (req.min !== undefined && v < req.min) ok = false;
    if (req.max !== undefined && v > req.max) ok = false;
    if (req.exact !== undefined && v !== req.exact) ok = false;
    if (req.odd && v % 2 === 0) ok = false;
    if (req.even && (v % 2 || v === 0)) ok = false;
    if (!ok && !(req.or_face && t === req.or_face)) return false;
  }
  if (req.pair) { const real = vals.filter((v, i) => tags[i] !== 'W'); if (vals.length < 2 || new Set(real).size > 1) return false; }
  if (req.sum_min !== undefined && vals.reduce((a, b) => a + b, 0) < req.sum_min) return false;
  return true;
}
export const isRisky = req => ['min', 'max', 'exact', 'odd', 'even', 'sum_min', 'pair', 'or_face'].some(k => req[k] !== undefined);
export function countOk(req, dice) {
  const n = req.n ?? 1;
  return req.upto ? dice.length >= 1 && dice.length <= n : dice.length === n;
}

// What a die might come up as while planning: [[value, tag, chance]].
export function outcomes(d, hymn = 0) {
  const add = (d.bonus || 0) + hymn;
  let base;
  if (d.rolled) return [[d.v, d.tag, 1]];
  if (d.v !== null && d.v !== undefined) base = [[d.v, d.tag, 1]];
  else if (d.fc) base = [[d.fc[0], null, 0.5], [d.fc[1], null, 0.5]];
  else if (d.top) base = [[topFace(d.faces), null, 1]];
  else {
    let faces = d.faces;
    const top = topFace(d.faces);
    if (d.hint) {
      const lo = Math.min(...d.faces.map(f => face(f)[0] ?? 0)), mid = (lo + top) / 2;
      const val = f => (face(f)[1] === 'W' ? top : face(f)[0]);
      faces = d.faces.filter(f => (d.hint === 'high' ? val(f) > mid : val(f) <= mid));
      if (!faces.length) faces = d.faces;
    }
    base = faces.map(f => {
      let [v, t] = face(f);
      if (t === 'W') v = top;
      if (d.dk?.includes('exploding') && v === top && t !== 'W') v += Math.round(meanFace(d.faces));
      return [v, t, 1 / faces.length];
    });
  }
  return base.map(([v, t, p]) => [t === 'S' || t === 'X' ? v : v + add, t, p]);
}

// Chance that these dice make an action hit.
export function hitChance(req, dice, hymn = 0) {
  if (!isRisky(req) || !dice.length) return null;
  let p = 0;
  const per = dice.map(d => outcomes(d, hymn));
  const walk = (i, vals, tags, pr) => {
    if (i === per.length) { if (checkHit(req, vals, tags)) p += pr; return; }
    for (const [v, t, q] of per[i]) walk(i + 1, [...vals, v], [...tags, t], pr * q);
  };
  walk(0, [], [], 1);
  return p;
}
export const expected = d => outcomes(d).reduce((a, [v, , p]) => a + v * p, 0);

const KIND_NAME = { seer: 'Seer', augur: 'Augur', fate: 'Fate', exploding: 'Exploding', steady: 'Steady', heirloom: 'Heirloom' };
export const KIND_TEXT = {
  seer: 'Rolled and shown while you plan.',
  augur: 'Shows whether it rolled high or low while you plan.',
  fate: 'Shows two faces while you plan; one of them comes up.',
  exploding: 'A top-face roll rolls again and adds.',
  steady: 'If its action misses, it rerolls once.',
  heirloom: 'Its lowest face rises every level.',
  link: 'Linked: rolls the same as the other die in its group.',
  top: 'Always comes up on its top face.',
};
// "d8", "Seer d4", "◆ d6": the die's size (or its faces, when they're unusual) and its kinds.
export function dieLabel(d) {
  const faces = Array.isArray(d) ? d : d.faces;
  const kinds = (Array.isArray(d) ? [] : d.dk || []).filter(k => KIND_NAME[k]).map(k => KIND_NAME[k]);
  // the size, marked with what's unusual about its faces; the tooltip lists them all
  const plain = faces.every((f, i) => f === i + 1);
  const marks = (faces.includes('S') ? '◆' : '') + (faces.includes('X') ? '☠' : '') + (faces.includes('W') ? '★' : '') +
    (faces.some(f => typeof f === 'string' && 'FIP'.includes(f[0])) ? '✦' : '') +
    (!plain && faces.every(f => typeof f === 'number') ? '~' : '');
  const size = marks + 'd' + faces.length;
  return [...kinds, size].join(' ');
}
export const faceText = f => ({ S: '◆', X: '☠', W: '★' }[f] || (typeof f === 'string' ? `${f.slice(1)}${{ F: '🔥', I: '❄', P: '☣' }[f[0]]}` : String(f)));
export function dieTip(d) {
  const faces = Array.isArray(d) ? d : d.faces;
  const kinds = Array.isArray(d) ? [] : d.dk || [];
  const plain = faces.every((f, i) => f === i + 1);
  // a plain d8 needs no face list; unusual dice do
  const lines = [dieLabel(d), plain ? `Rolls 1 to ${faces.length}.` : 'Faces: ' + faces.map(faceText).join(' ')];
  for (const k of kinds) { const key = k.startsWith('link:') ? 'link' : k; if (KIND_TEXT[key]) lines.push(KIND_TEXT[key]); }
  const seen = new Set();
  for (const f of faces) {
    const key = typeof f === 'string' ? f[0] : null;
    if (key && !seen.has(key)) { seen.add(key); lines.push(faceTip(f)); }
  }
  return lines.join('\n');
}
// What a special face does (plain numbers just count their value).
export function faceTip(f) {
  if (typeof f !== 'string') return `${f}: counts as ${f}.`;
  return {
    S: '◆ Shield face: worth 0, but blocks 3 damage this round.',
    X: '☠ Skull face: worth 0, and you take 3 damage.',
    W: '★ Wild face: counts as the top face and passes any condition.',
    F: `${faceText(f)} Fire face: worth ${f.slice(1)} and Burns the target.`,
    I: `${faceText(f)} Ice face: worth ${f.slice(1)} and Freezes the target.`,
    P: `${faceText(f)} Poison face: worth ${f.slice(1)} and Poisons the target.`,
  }[f[0]] || faceText(f);
}

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
  dodge: { name: 'Dodge', icon: 'boot', text: 'The next hit misses.' },
  riposte: { name: 'Riposte', icon: 'sword', text: 'If a hit is fully blocked this round, hits back for this much.' },
  crescendo: { name: 'Crescendo', icon: 'up', text: 'The next damaging action deals 50% more.' },
  thorns: { name: 'Thorns', icon: 'spark', text: 'Attackers take this much this round.' },
};
