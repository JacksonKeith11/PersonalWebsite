// The hex map, drawn by Phaser: painted pixel terrain (repainted when the sea or tide changes), the
// places, enemies and heroes standing on it, fog, reachable hexes and planned routes.
// Everything else on screen is HTML.
import { W, H, terrain, visibleTiles, neighbors, seaMap, dist } from './rules.js?v=166';
import { spriteCanvas, placeCanvas } from './art.js?v=166';

export const HW = 48, HH = 54, RS = 40;
export const MAP_W = W * HW + HW / 2, MAP_H = (H - 1) * RS + HH;
const K = 41.5692 / RS, SIZE = HW / Math.sqrt(3);
export const SEATS = [0xe07a5f, 0x4fb3a9, 0xa48ad8];

export function center(t) {
  const q = t % W, r = Math.floor(t / W);
  return [q * HW + HW / 2 + (r & 1) * HW / 2, r * RS + HH / 2];
}
export function tileAt(px, py) {
  const x = px - HW / 2, y = (py - HH / 2) * K;
  let q = (Math.sqrt(3) / 3 * x - y / 3) / SIZE, r = (2 / 3 * y) / SIZE, s = -q - r;
  let rq = Math.round(q), rr = Math.round(r); const rs = Math.round(s);
  const dq = Math.abs(rq - q), dr = Math.abs(rr - r), ds = Math.abs(rs - s);
  if (dq > dr && dq > ds) rq = -rr - rs; else if (dr > ds) rr = -rq - rs;
  const col = rq + (rr - (rr & 1)) / 2, row = rr;
  if (col < 0 || col >= W || row < 0 || row >= H) return -1;
  return row * W + col;
}
const RARITY_COL = { common: 0xb8b0a0, uncommon: 0x6cc070, rare: 0x5aa0e8, legendary: 0xe0a040 };
const HEXPTS = [[0, -27], [24, -13], [24, 13], [0, 27], [-24, 13], [-24, -13]];
function hexPoints(t, inset = 0) {
  const [cx, cy] = center(t);
  return HEXPTS.map(([x, y]) => ({ x: cx + x * (1 - inset / 24), y: cy + y * (1 - inset / 27) }));
}

// ------------------------------------------------------------------ terrain painting
const hash = (x, y) => { let n = (x * 374761393 + y * 668265263) | 0; n = (n ^ (n >>> 13)) * 1274126177 | 0; return ((n ^ (n >>> 16)) >>> 0) / 4294967296; };
const rgb = c => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
const PAL = {
  deep: ['#1a4660', '#1d4f6a', '#235f7c', '#2c7290', '#3a87a3'].map(rgb), wave: rgb('#5aa3bd'), foam: rgb('#d6eef0'), foam2: rgb('#8cc6d4'),
  shoal: rgb('#bfa877'), shoalD: rgb('#a8925f'), puddle: rgb('#6aa6b4'),
  beach: rgb('#d9c48e'), beachD: rgb('#c4ad78'), beachL: rgb('#e8d8a8'),
  grass: rgb('#5d8c47'), grassD: rgb('#4c7a3a'), grassL: rgb('#79a85a'),
  forest: rgb('#4a7a3c'), forestD: rgb('#3e6a34'),
  hills: rgb('#7d8a4e'), hillsD: rgb('#6a7642'), hillsL: rgb('#95a060'),
  peak: rgb('#7f7a72'), peakD: rgb('#6a655e'), peakL: rgb('#9a958c'),
  town: rgb('#86955a'), dirt: rgb('#a08a62'),
};
// The other regions' land: the same five kinds of ground (beach, grass, forest, hills, peak) in each
// region's own colours, [base, dark, light] (the original three regions keep PAL).
const SKIN = Object.fromEntries(Object.entries({
  ash: { beach: ['#4a4448', '#3a3438', '#5e5658'], grass: ['#6a645e', '#5a544e', '#7e766e'], forest: ['#4e4844', '#3e3834'],
    hills: ['#5a4a44', '#4a3c38', '#6e5a50'], peak: ['#3e3438', '#2e2628', '#5a3a30'] },
  dunes: { beach: ['#e4d8b4', '#ccc098', '#f0e8cc'], grass: ['#d8b87a', '#c4a266', '#e8cc90'], forest: ['#b8a860', '#a09450'],
    hills: ['#c89c5e', '#b0864c', '#dcb070'], peak: ['#b07a52', '#966444', '#c8906a'] },
  petrified: { beach: ['#a8a49a', '#929086', '#bab6ac'], grass: ['#7a8070', '#6a7062', '#8c927e'], forest: ['#6e706a', '#5e605a'],
    hills: ['#8a867a', '#76726a', '#9e9a8c'], peak: ['#9a968c', '#84807a', '#b0aca2'] },
  jungle: { beach: ['#7a6a48', '#68583a', '#8c7c58'], grass: ['#3e7a34', '#336a2a', '#4e8c40'], forest: ['#2a5a2a', '#224a22'],
    hills: ['#4a6a34', '#3e5a2c', '#5a7c40'], peak: ['#5e6a52', '#4e5a44', '#727e64'] },
  heaven: { beach: ['#e8e6f0', '#d0cedc', '#f6f4fa'], grass: ['#c8b86a', '#b4a45a', '#dccc80'], forest: ['#a8b8a0', '#94a48c'],
    hills: ['#d8d4c8', '#c4c0b4', '#ecE8dc'], peak: ['#e8e4d8', '#d4d0c4', '#f8f4ea'] },
  crystal: { beach: ['#d8d0e0', '#c4bcd0', '#e8e0f0'], grass: ['#9a8ab8', '#8a7aa8', '#ae9ec8'], forest: ['#6a5a98', '#5a4a88'],
    hills: ['#8070a8', '#706098', '#9686bc'], peak: ['#b0a0d8', '#9a8ac4', '#c8bce8'] },
  dream: { beach: ['#e0d0e0', '#ccbccc', '#eee0ee'], grass: ['#a08ac0', '#9078b0', '#b49cd0'], forest: ['#6a5a8a', '#5a4a7a'],
    hills: ['#c8b8e0', '#b4a4d0', '#dccef0'], peak: ['#8a80b0', '#787098', '#a49ac8'] },
  frost: { beach: ['#d4e4ee', '#bcd0de', '#e8f2f8'], grass: ['#e0e8ee', '#ccd8e2', '#f2f6fa'], forest: ['#c8d4dc', '#b0c0cc'],
    hills: ['#b8d0e4', '#a0bcd4', '#d0e4f2'], peak: ['#eef4f8', '#d8e4ec', '#ffffff'] },
}).map(([r, kinds]) => [r, Object.fromEntries(Object.entries(kinds).map(([k, cs]) => [k, cs.map(rgb)]))]));
const ICE = ['#cfe3ee', '#a9c8da', '#eaf4fa'].map(rgb);
function groundPixel(kind, x, y, depth, skin) {
  const n = hash(x, y), n2 = hash(x >> 2, y >> 2);
  const sk = skin && skin[kind];
  if (sk) {
    const [b, d, l = b] = sk;
    if (kind === 'grass' || kind === 'forest') return n2 > 0.66 && n > 0.45 ? d : n > 0.965 ? l : b;
    return n > 0.9 ? d : n > 0.84 ? l : b;
  }
  if (kind === 'ice') {
    // the frozen sea: pale ice with a few long cracks
    const crack = Math.abs(Math.sin(x * 0.21 + y * 0.13 + hash(x >> 4, y >> 4) * 6)) < 0.04 && n2 > 0.4;
    return crack ? ICE[1] : n > 0.93 ? ICE[2] : ICE[0];
  }
  switch (kind) {
    case 'deep': {
      // depth below the sea; tidal shallows under a high tide are -1 and drawn lightest
      const base = PAL.deep[4 - Math.max(0, Math.min(4, depth))];
      if (y % 7 === 0 && (x + ((y / 7) | 0) * 5) % 16 < 3) return PAL.wave;
      if (n > 0.997) return PAL.wave;
      return base;
    }
    case 'shoal': return n2 > 0.86 ? PAL.puddle : n > 0.85 ? PAL.shoalD : PAL.shoal;
    case 'beach': return n > 0.9 ? PAL.beachD : n > 0.84 ? PAL.beachL : PAL.beach;
    case 'grass': return n2 > 0.7 && n > 0.45 ? PAL.grassD : n > 0.965 ? PAL.grassL : PAL.grass;
    case 'forest': return n2 > 0.6 && n > 0.5 ? PAL.forestD : PAL.forest;
    case 'hills': return n > 0.92 ? PAL.hillsD : n > 0.88 ? PAL.hillsL : PAL.hills;
    case 'peak': return n > 0.9 ? PAL.peakD : n > 0.84 ? PAL.peakL : PAL.peak;
    case 'town': return n2 > 0.75 ? PAL.dirt : n > 0.93 ? PAL.grassD : PAL.town;
  }
  return PAL.grass;
}

// Props stamped on top, in row order so nearer things overlap farther ones.
const STAMPS = {
  tree: { pal: { g: '#2c4a2a', G: '#3f7a3c', L: '#5a9a4a', D: '#2f5e30', t: '#5a3a24' }, rows: [
    '...gggg...', '..gGGGGg..', '.gGLLGGGg.', 'gGLLGGGGGg', 'gGGGGGGGDg', 'gGGGGGGDDg', '.gGGGGDDg.', '..gDDDDg..', '....tt....', '....tt....'] },
  palm: { pal: { g: '#2c4a2a', G: '#4a8a3c', L: '#6aa84a', t: '#7a5a34', T: '#5a4024' }, rows: [
    '.gg...gg..', 'gLGg.gGLg.', '..gGgGg...', '.gGGLGGg..', 'gG.gTg.Gg.', '....tT....', '....tT....', '...tT.....', '...tT.....'] },
  pine: { pal: { g: '#24402a', G: '#335e36', L: '#4a7a44', t: '#4a3020' }, rows: [
    '....gg....', '...gGGg...', '..gGLGGg..', '...gGGg...', '..gGLGGg..', '.gGGGGGGg.', 'gGGLGGGGGg', '.ggggggggg', '....tt....', '....tt....'] },
  round: { pal: { g: '#2c4a2a', G: '#4a7e3a', L: '#6a9a4e', t: '#5a3a24' }, rows: [
    '..gggggg..', '.gGLLGGGg.', 'gGLGGGGGGg', 'gGGGGGGGGg', '.gGGGGGGg.', '..gggggg..', '....tt....', '....tt....'] },
  bush: { pal: { g: '#2c4a2a', G: '#4a7a3c', L: '#62924a' }, rows: ['..gggg..', '.gGLGGg.', 'gGGGGGGg', '.gggggg.'] },
  mound: { pal: { h: '#56603a', H: '#7d8a4e', L: '#9aa866', D: '#68743f' }, rows: [
    '.....hhhhh......', '...hhHHLHHhh....', '..hHHLLHHHHHh...', '.hHLLHHHHHHDDh..', 'hHHHHHHHHHDDDDh.'] },
  rock: { pal: { k: '#4a4640', R: '#8f8a82', L: '#b2ada4', D: '#6e6a62' }, rows: [
    '...kkk....', '..kLLRk...', '.kLLRRRk..', '.kLRRRDDk.', 'kRRRRDDDDk', 'kkkkkkkkkk'] },
  snowrock: { pal: { k: '#4a4640', R: '#8f8a82', W: '#e8ecef', D: '#6e6a62' }, rows: [
    '....k.....', '...kWk....', '..kWWRk...', '.kWRRRDk..', 'kRRRRDDDk.', 'kkkkkkkkk.'] },
  house: { pal: { k: '#2a1e1a', r: '#a84a3a', R: '#7a3428', w: '#e0d4b8', W: '#b8a888', d: '#4a3020', y: '#ffd870' }, rows: [
    '...kkk...', '..krrrk..', '.krrrrrk.', 'kRRRRRRRk', '.kwwwwwk.', '.kwdwywk.', '.kwdwwWk.', '.kkkkkkk.'] },
  dock: { pal: { k: '#2a1e1a', w: '#8a6a44', W: '#6a4e30' }, rows: ['kkkkkkkk', 'wwwwwwww', 'WkWWkWWk', '.k..k..k'] },
  // the other regions' props
  cactus: { pal: { k: '#24402a', G: '#5a8a4a', L: '#7aa860' }, rows: [
    '....kk....', '...kGLk...', '.k.kGGk...', 'kLkkGGk.k.', 'kGGkGGkkLk', '.kkkGGkGGk', '...kGGkkk.', '...kGGk...', '...kGGk...'] },
  crystal: { pal: { k: '#2a2050', C: '#b8a8e8', L: '#e8e0ff', D: '#7a68b8' }, rows: [
    '....k.....', '...kLk..k.', '...kLCk.kL', '.k.kLCk.kC', 'kLkkLCDkkC', 'kLCkLCDkLC', 'kLCkLCDkLD', 'kkkkkkkkkk'] },
  shard: { pal: { k: '#2a2050', C: '#b8a8e8', L: '#e8e0ff' }, rows: ['..k...', '.kLk.k', '.kCkkL', 'kkkkkk'] },
  pillar: { pal: { k: '#3a3630', S: '#a8a49a', L: '#c8c4ba', D: '#827e76' }, rows: [
    '.kkkkk.', '.kLSDk.', '..kSDk.', '..kSDk.', '..kLDk.', '..kSDk.', '.kLSDDk', 'kkkkkkk'] },
  spire: { pal: { k: '#3a3630', S: '#9a968c', L: '#bab6ac', D: '#76726a' }, rows: [
    '...k....', '..kLk...', '..kSk...', '.kLSDk..', '.kLSDk..', 'kLSSDDk.', 'kLSSDDk.', 'kkkkkkkk'] },
  flower: { pal: { y: '#f0d870', w: '#fff8e0', g: '#5a7a3a' }, rows: ['.y.w.', 'yyywy', '.g.g.'] },
  lavender: { pal: { p: '#8a6ac8', P: '#b49ae0', g: '#5a6a4a' }, rows: ['P.p.P', 'p.P.p', 'g.g.g'] },
  fern: { pal: { g: '#24402a', G: '#3e7a34', L: '#5a9a4a' }, rows: ['G...G...', 'LG.GLG.G', '.LGGLGG.', '..gLLg..', '...gg...'] },
  vent: { pal: { k: '#1e1a1a', R: '#3a3030', o: '#e8782a', y: '#ffd23f' }, rows: ['..R..R..', '.RRkkRR.', 'RRkoykRR', '.RRkkRR.'] },
  column: { pal: { k: '#5a5650', W: '#eceae0', w: '#c8c4b8', y: '#d8c070' }, rows: [
    'kyyyyyk', '.kWWwk.', '.kWWwk.', '.kWWwk.', '.kWWwk.', '.kWWwk.', 'kyyyyyk'] },
  cloud: { pal: { w: '#f0ecf8', W: '#d8d0ec', k: '#8a80b0' }, rows: ['...wwww....', '.wwwWwwww..', 'wwwWWwwwwww', 'kWWWWWWWWk.'] },
  // a reef at low tide: dark rocks breaking the surface, ringed in foam
  reef: { pal: { k: '#2a2622', R: '#5e5850', L: '#7e776c', f: '#d6eef0' }, rows: [
    '..f.ff....ff..', '.fkkf..fkkkf..', 'fkLRkf.kLRRkf.', 'fkRRkffkRRRkf.', '.fkkf..fkkkf..', '..ff....fff...'] },
};
// the other regions' props: what grows on each kind of ground, and the palette its trees are painted in
// (`over`, swapped onto the tree, pine and round stamps)
const PROPS = {
  ash: { mound: { h: '#2e2628', H: '#5a4a44', L: '#6e5a50', D: '#4a3c38' }, tree: ['tree', 'pine'], over: { g: '#1e1a1a', G: '#3a3434', L: '#4e4644', D: '#2a2424', t: '#2a2020' }, grass: 'vent', hills: 'rock', grassRate: 0.85 },
  dunes: { mound: { h: '#96703e', H: '#c89c5e', L: '#dcb070', D: '#b0864c' }, tree: ['palm', 'cactus'], grass: 'cactus', grassRate: 0.9, beach: null },
  petrified: { mound: { h: '#5e5a52', H: '#8a867a', L: '#9e9a8c', D: '#76726a' }, tree: ['tree', 'round'], over: { g: '#4a4842', G: '#8a867c', L: '#a8a49a', D: '#6e6a62', t: '#5a5650' }, grass: 'pillar', hills: 'spire', grassRate: 0.85 },
  jungle: { mound: { h: '#24401e', H: '#4a6a34', L: '#5a7c40', D: '#3e5a2c' }, tree: ['round', 'tree', 'palm'], over: { g: '#16301a', G: '#3e8a34', L: '#6ab04a', D: '#2a5a26', t: '#4a3020' }, grass: 'fern', grassRate: 0.55, dense: true },
  heaven: { mound: { h: '#9a968c', H: '#d8d4c8', L: '#ecE8dc', D: '#c4c0b4' }, tree: ['round', 'tree'], over: { g: '#6a7a6a', G: '#c8d4c0', L: '#e8f0e0', D: '#a8b8a0', t: '#c8a040' }, grass: 'flower', hills: 'column', grassRate: 0.7 },
  crystal: { mound: { h: '#4a3a78', H: '#8070a8', L: '#9686bc', D: '#706098' }, tree: ['crystal'], grass: 'shard', hills: 'crystal', grassRate: 0.75 },
  dream: { mound: { h: '#8070a0', H: '#c8b8e0', L: '#dccef0', D: '#b4a4d0' }, tree: ['round'], over: { g: '#3a2a5a', G: '#8a6ac0', L: '#b49ae0', D: '#6a4a9a', t: '#5a4a6a' }, grass: 'lavender', hills: 'cloud', grassRate: 0.6 },
  frost: { mound: { h: '#6a8aa8', H: '#b8d0e4', L: '#d0e4f2', D: '#a0bcd4' }, tree: ['pine'], over: { g: '#4a5a6a', G: '#e8f0f4', L: '#ffffff', t: '#4a3a30' }, grass: 'snowrock', hills: 'snowrock', grassRate: 0.92 },
};
function stamp(img, s, x0, y0, over) {
  const { rows } = STAMPS[s];
  const pal = over ? { ...STAMPS[s].pal, ...over } : STAMPS[s].pal;
  for (let y = 0; y < rows.length; y++) for (let x = 0; x < rows[y].length; x++) {
    const ch = rows[y][x];
    if (ch === '.') continue;
    const X = x0 + x, Y = y0 + y;
    if (X < 0 || Y < 0 || X >= MAP_W || Y >= MAP_H) continue;
    const c = rgb(pal[ch]), i = (Y * MAP_W + X) * 4;
    img.data[i] = c[0]; img.data[i + 1] = c[1]; img.data[i + 2] = c[2]; img.data[i + 3] = 255;
  }
}

let OWNER = null;
function owners() {
  if (OWNER) return OWNER;
  OWNER = new Int16Array(MAP_W * MAP_H);
  for (let y = 0; y < MAP_H; y++) for (let x = 0; x < MAP_W; x++) OWNER[y * MAP_W + x] = tileAt(x + 0.5, y + 0.5);
  return OWNER;
}

const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map(v => (v + 0.5) / 16);
const LANDISH = k => k !== 'deep';
const ROAD = rgb('#a08a62'), ROAD_D = rgb('#7e6a48');

// Dirt roads between towns: each town joins its nearest other town by the cheapest walk over land
// (no water, no peaks), found once per map. Returns the hex sequences.
function roads(world, kinds) {
  const towns = [];
  for (let t = 0; t < W * H; t++) if (kinds[t] === 'town') towns.push(t);
  const ok = t => kinds[t] !== 'deep' && kinds[t] !== 'shoal' && kinds[t] !== 'peak';
  const cost = t => (kinds[t] === 'forest' || kinds[t] === 'hills' ? 2 : 1);
  const out = [], joined = new Set();
  for (const a of towns) {
    // Dijkstra on a small grid: fine for 30×22
    const dist = new Map([[a, 0]]), prev = new Map(), open = [[0, a]];
    let goal = -1;
    while (open.length) {
      open.sort((x, y) => x[0] - y[0]);
      const [d, t] = open.shift();
      if (d > dist.get(t)) continue;
      if (t !== a && kinds[t] === 'town') { goal = t; break; }
      for (const n of neighbors(t)) {
        if (!ok(n)) continue;
        const nd = d + cost(n);
        if (nd < (dist.get(n) ?? 1e9) && nd < 24) { dist.set(n, nd); prev.set(n, t); open.push([nd, n]); }
      }
    }
    if (goal < 0) continue;
    const key = [Math.min(a, goal), Math.max(a, goal)].join('-');
    if (joined.has(key)) continue;
    joined.add(key);
    const path = [goal];
    while (path[path.length - 1] !== a) path.push(prev.get(path[path.length - 1]));
    out.push(path);
  }
  return out;
}

let ROADS = null, ROADS_FOR = null;
const SURF = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, -1], [1, -1], [-1, 1]];
// `surf` is two canvases the size of the map: two frames of foam a little way out from the shore,
// which the scene cross-fades so the surf seems to wash in and out.
export function paintTerrain(canvas, world, game, surf) {
  const ctx = canvas.getContext('2d');
  const img = ctx.createImageData(MAP_W, MAP_H);
  const sa = surf ? surf[0].getContext('2d').createImageData(MAP_W, MAP_H) : null;
  const sb = surf ? surf[1].getContext('2d').createImageData(MAP_W, MAP_H) : null;
  const sea = seaMap(world);
  const own = owners();
  const kinds = new Array(W * H);
  for (let t = 0; t < W * H; t++) kinds[t] = terrain(world, game, t);
  // each hex's region skin (only for the regions this world drew)
  const drawn = new Set(world.regions || []);
  const skins = new Array(W * H);
  for (let t = 0; t < W * H; t++) skins[t] = drawn.has(world.reg?.[t]) ? SKIN[world.reg[t]] : null;
  const water = t => t < 0 || kinds[t] === 'deep';
  const at = (x, y) => (x < 0 || y < 0 || x >= MAP_W || y >= MAP_H ? -1 : own[y * MAP_W + x]);
  for (let y = 0; y < MAP_H; y++) for (let x = 0; x < MAP_W; x++) {
    const p = y * MAP_W + x, t = own[p];
    let c;
    if (t < 0) c = PAL.deep[0];
    else {
      let k = kinds[t];
      // where two kinds of land meet, the edge is dithered over a few pixels instead of a hard line
      if (LANDISH(k)) {
        for (const [dx, dy] of [[3, 0], [-3, 0], [0, 3], [0, -3], [2, 2], [-2, -2]]) {
          const o = at(x + dx, y + dy);
          if (o >= 0 && o !== t && LANDISH(kinds[o]) && kinds[o] !== k && kinds[o] !== 'town' && k !== 'town') {
            const near = Math.max(Math.abs(dx), Math.abs(dy));
            const o1 = at(x + Math.sign(dx), y + Math.sign(dy));
            const d = o1 !== t ? 1 : near;
            if ((1 - d / 4) * 0.55 > BAYER[(y & 3) * 4 + (x & 3)]) { k = kinds[o]; }
            break;
          }
        }
      }
      c = groundPixel(k, x, y, game.sea - world.elev[t], skins[t]);
      // quicksand: rings of darker sand
      if (sea.sink.has(t)) {
        const [cx, cy] = center(t), r = Math.hypot(x - cx, (y - cy) * 1.3);
        if (r < 15 && Math.floor(r) % 4 === 0) c = [c[0] * 0.8, c[1] * 0.74, c[2] * 0.66];
      }
      if (kinds[t] === 'deep') {
        // foam where water meets land
        let near = 99;
        for (const [dx, dy, d] of [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1], [2, 0, 2], [-2, 0, 2], [0, 2, 2], [0, -2, 2]]) {
          const o = at(x + dx, y + dy);
          if (o >= 0 && !water(o)) near = Math.min(near, d);
        }
        if (near === 1) c = PAL.foam; else if (near === 2) c = PAL.foam2;
        else if (sa) {
          // the surf frames: a broken line of foam 3-4 pixels out (frame A) and 4-6 out (frame B)
          let far = 99;
          for (let d = 3; d <= 6 && far === 99; d++) for (const [dx, dy] of SURF) { const o = at(x + dx * d, y + dy * d); if (o >= 0 && !water(o)) { far = d; break; } }
          const i4 = p * 4, wav = (Math.sin(x * 0.35 + y * 0.2) + 1) / 2;
          if (far <= 4 && wav > 0.35) { sa.data[i4] = 214; sa.data[i4 + 1] = 238; sa.data[i4 + 2] = 240; sa.data[i4 + 3] = far === 3 ? 200 : 120; }
          if (far >= 4 && far <= 6 && wav < 0.65) { sb.data[i4] = 190; sb.data[i4 + 1] = 228; sb.data[i4 + 2] = 236; sb.data[i4 + 3] = far === 6 ? 70 : 150; }
        }
        // a reef under a high tide: a dark shape below the surface
        if (sea.reef.has(t) && game.tide === 'high' && hash(x >> 1, y >> 1) > 0.45) {
          const [cx, cy] = center(t);
          if (Math.hypot(x - cx, (y - cy) * 1.3) < 13) c = [c[0] * 0.62, c[1] * 0.7, c[2] * 0.74];
        }
        // a whirlpool: dark rings spiralling in
        if (sea.pool.has(t)) {
          const [cx, cy] = center(t), dx = x - cx, dy = (y - cy) * 1.2, r = Math.hypot(dx, dy);
          if (r < 19) {
            const arm = (Math.atan2(dy, dx) + r * 0.32) % (Math.PI / 1.5);
            if (arm < 0.5 && arm > -0.5 || arm > 1.6) c = r < 5 ? [12, 30, 44] : [c[0] * 0.55, c[1] * 0.6, c[2] * 0.68];
            else if (r > 6 && arm > 0.9 && arm < 1.1) c = PAL.foam2;
          }
        }
      } else {
        // height: a shadow where the ground drops away to the south-east, a lit lip where it rises
        const lo = at(x + 2, y + 3), hi = at(x - 2, y - 3);
        if (lo >= 0 && lo !== t && !water(lo) && world.elev[lo] < world.elev[t] - 2) c = [c[0] * 0.74, c[1] * 0.74, c[2] * 0.8];
        else if (hi >= 0 && hi !== t && !water(hi) && world.elev[hi] < world.elev[t] - 2) c = [Math.min(255, c[0] * 1.1), Math.min(255, c[1] * 1.1), Math.min(255, c[2] * 1.06)];
      }
      // the hex grid: a faint dotted line where hexes meet, enough to plan by
      const r = x + 1 < MAP_W ? own[p + 1] : t, d = y + 1 < MAP_H ? own[p + MAP_W] : t;
      if ((r !== t || d !== t) && ((x + y) & 1)) {
        const f = kinds[t] === 'deep' ? 0.92 : 0.86;
        c = [c[0] * f, c[1] * f, c[2] * f];
      }
    }
    const i = p * 4;
    img.data[i] = c[0]; img.data[i + 1] = c[1]; img.data[i + 2] = c[2]; img.data[i + 3] = 255;
  }
  // roads, before the props so trees stand beside them
  const key = world.elev.length + ':' + game.sea + game.tide;
  if (ROADS_FOR !== key) { ROADS = roads(world, kinds); ROADS_FOR = key; }
  const onRoad = new Set(ROADS.flat());
  const dot = (X, Y, col) => { X |= 0; Y |= 0; if (X < 0 || Y < 0 || X >= MAP_W || Y >= MAP_H) return; const i = (Y * MAP_W + X) * 4; img.data[i] = col[0]; img.data[i + 1] = col[1]; img.data[i + 2] = col[2]; };
  for (const path of ROADS) {
    for (let i = 1; i < path.length; i++) {
      const [x0, y0] = center(path[i - 1]), [x1, y1] = center(path[i]);
      const n = Math.ceil(Math.hypot(x1 - x0, y1 - y0));
      for (let k = 0; k <= n; k++) {
        const wob = Math.sin((i * 40 + k) * 0.25) * 1.2;
        const X = x0 + (x1 - x0) * k / n + wob, Y = y0 + (y1 - y0) * k / n + 6;
        for (let w = -1; w <= 1; w++) for (let v = -1; v <= 1; v++) dot(X + w, Y + v, hash((X | 0) + w, (Y | 0) + v) > 0.88 ? ROAD_D : ROAD);
        if (hash(k, i) > 0.6) dot(X + 2, Y + 2, ROAD_D);
      }
    }
  }
  // currents: pale chevrons pointing downstream on each hex of a lane
  for (const [a, b] of sea.cur) {
    const [x0, y0] = center(a), [x1, y1] = center(b);
    const ux = (x1 - x0) / HW, uy = (y1 - y0) / HW;
    for (const off of [-8, 6]) {
      const mx = x0 + ux * off, my = y0 + uy * off;
      for (let k = -5; k <= 5; k++) {
        const side = Math.abs(k), X = mx - ux * side * 0.9 + -uy * k, Y = my - uy * side * 0.9 + ux * k;
        dot(X, Y, PAL.wave); if (side < 4) dot(X + ux, Y + uy, rgb('#9fd2de'));
      }
    }
  }
  // props, top to bottom
  for (let t = 0; t < W * H; t++) {
    if (sea.reef.has(t) && game.tide === 'low') { const [cx, cy] = center(t); stamp(img, 'reef', cx - 7, cy - 3); continue; }
    const k = kinds[t], [cx, cy] = center(t);
    const r = hash(t, 7), r2 = hash(t, 13);
    const coast = k !== 'deep' && world.elev[t] <= game.sea + 3;
    const road = onRoad.has(t);
    const P = drawn.has(world.reg?.[t]) ? PROPS[world.reg[t]] : null;
    if (P && k !== 'town' && k !== 'deep' && k !== 'ice' && k !== 'shoal') {
      // the other regions' props
      const tr = i => P.tree[Math.floor(hash(t, i + 21) * P.tree.length)];
      if (k === 'forest') {
        const spots = P.dense ? [[-12, -14], [4, -16], [-4, -4], [10, -4], [-14, 4], [2, 6], [-6, -12], [8, 4]] : [[-12, -14], [4, -16], [-4, -4], [10, -4], [-14, 4], [2, 6]];
        for (let i = 0; i < spots.length; i++) if (hash(t, i) > (road ? 0.6 : P.dense ? 0.1 : 0.25)) { const s2 = tr(i); stamp(img, s2, cx + spots[i][0] - 5, cy + spots[i][1] - 4, ['tree', 'pine', 'round'].includes(s2) ? P.over : null); }
      } else if (k === 'hills') {
        stamp(img, 'mound', cx - 14 + (r * 6 | 0), cy - 10, P.mound);
        if (P.hills && r2 > 0.35) stamp(img, P.hills, cx - 2 + (r2 * 6 | 0), cy - 6);
      } else if (k === 'peak') {
        stamp(img, P.hills === 'spire' || P.hills === 'column' ? P.hills : world.elev[t] >= 17 ? 'snowrock' : 'rock', cx - 12 + (r * 4 | 0), cy - 12);
        stamp(img, P.hills || 'rock', cx + (r2 * 4 | 0), cy - 2);
      } else if (k === 'grass' && P.grass && r > P.grassRate && !road) {
        stamp(img, P.grass, cx - 5 + (r2 * 16 - 8 | 0), cy - 8);
        if (P.grass === 'flower' || P.grass === 'lavender') stamp(img, P.grass, cx + 4 - (r2 * 10 | 0), cy + 2);
      }
      continue;
    }
    const tree = i => (coast && hash(t, i + 9) > 0.5 ? 'palm' : ['tree', 'tree', 'pine', 'round'][Math.floor(hash(t, i + 21) * 4)]);
    if (k === 'forest') {
      const spots = [[-12, -14], [4, -16], [-4, -4], [10, -4], [-14, 4], [2, 6]];
      for (let i = 0; i < spots.length; i++) if (hash(t, i) > (road ? 0.6 : 0.25)) stamp(img, tree(i), cx + spots[i][0] - 5, cy + spots[i][1] - 4);
    } else if (k === 'hills') {
      stamp(img, 'mound', cx - 14 + (r * 6 | 0), cy - 10); stamp(img, r2 > 0.5 ? 'mound' : 'bush', cx - 4 + (r2 * 6 | 0), cy + 2);
    } else if (k === 'peak') {
      stamp(img, world.elev[t] >= 17 ? 'snowrock' : 'rock', cx - 12 + (r * 4 | 0), cy - 12); stamp(img, 'rock', cx + (r2 * 4 | 0), cy - 2);
      if (r > 0.5) stamp(img, 'rock', cx - 10, cy + 6);
    } else if (k === 'grass' && r > 0.72 && !road) {
      stamp(img, r2 > 0.6 ? 'bush' : tree(1), cx - 5 + (r2 * 16 - 8 | 0), cy - 8);
    } else if (k === 'beach' && r > 0.82) {
      stamp(img, 'palm', cx - 5 + (r2 * 12 - 6 | 0), cy - 8);
    } else if (k === 'town') {
      stamp(img, 'house', cx - 16, cy - 12); stamp(img, 'house', cx + 2, cy - 14); stamp(img, 'house', cx - 6, cy);
    }
  }
  ctx.putImageData(img, 0, 0);
  if (surf) { surf[0].getContext('2d').putImageData(sa, 0, 0); surf[1].getContext('2d').putImageData(sb, 0, 0); }
}

// The objectives' landmarks, tall enough to see from far off and drawn above the fog, so the party
// always knows which way to go: the Sunken Chapel's spire, the Black Fort's tower, the Lighthouse
// (with its beam), the Drowned Peak's crown.
const LANDMARK = {
  coral: { pal: { s: '#9aa6a8', S: '#6a7678', d: '#1e1a26', c: '#5fb8a8', y: '#c8a040' }, rows: [
    '.......y........', '.......s........', '......sSs.......', '......sSs.......', '.....ssSss......', '.....sdSds......', '....ssSSSss.....',
    '....sdsSsds.....', '...sssSSSsss....', '..ssdsSSSsdss...', '..sssSSdSSsss...', '.cssSSSdSSSssc..', 'cccSSSSdSSSSccc.'] },
  keys: { pal: { s: '#7a6a5a', S: '#54483c', d: '#1a1410', r: '#b0302a', w: '#8a6a44' }, rows: [
    '......rrr.......', '......r..w......', '.........w......', '...s.s.s.s.s....', '...sssssssss....', '...sSdsssdSs....', '...sSsssssSs....',
    '...sSssdssSs....', '.s.sSssdssSs.s..', '.sssSsssssSsss..', '.sSsSsddssSsSs..', '.sSsSsddssSsSs..', 'SSSSSSSSSSSSSSS.'] },
  storm: { pal: { w: '#e8e4dc', r: '#b0302a', k: '#2a2430', y: '#ffe9a0', s: '#6a6a72' }, rows: [
    '.......k........', '......kyk.......', '......yyy.......', '.....kkkkk......', '......www.......', '......rrr.......', '......www.......',
    '.....wrrrw......', '.....wwwww......', '.....rrrrr......', '....wwwwwww.....', '...sssssssss....', '..sssssssssss...'] },
  // Cinderreach: the smoking volcano with lava down its flanks
  ash: { pal: { k: '#3a3030', K: '#2a2224', o: '#e8782a', y: '#ffd23f', g: '#8a8078' }, rows: [
    '....g.g..g......', '.....g.gg.......', '......gg........', '.....kyok.......', '....kkoyokk.....', '....kkkokkk.....',
    '...kkKkokKkk....', '...kkKkkoKkk....', '..kkKkkkkoKkk...', '..kKkkkkkkokk...', '.kkKkkkkkkoKkk..', 'KKKKKKKKKKKoKKK.'] },
  // the Shifting Sands: a stepped pyramid with a sun-disc
  dunes: { pal: { s: '#d8b87a', S: '#b0864c', d: '#3a2a1a', y: '#e8c040' }, rows: [
    '.......y........', '......yyy.......', '.......s........', '......sSs.......', '.....sssSs......', '.....sSdSs......',
    '....ssssSss.....', '....sSSSSSs.....', '...sssssSsss....', '..ssSSSSSSSSs...', '..sssssdSssss...', '.SSSSSSdSSSSSS..'] },
  // the Stillwood: a vast petrified tree
  petrified: { pal: { s: '#9a968c', S: '#76726a', d: '#3a3630', m: '#7a8a5a' }, rows: [
    '...ss.s..ss.....', '..sSs.ss.sSs....', '...sssSsss......', '....mssSsm......', '......sS........', '......sS........',
    '......sS........', '.....ssSs.......', '.....sdSs.......', '....ssSSss......', '...sSs..sSs.....', '..SSS....SSS....'] },
  // the Verdant Deep: a ziggurat swallowed by vines
  jungle: { pal: { s: '#8a8a72', S: '#62624e', d: '#1e1a14', g: '#3e7a34', G: '#2a5a2a' }, rows: [
    '......gGg.......', '.....gsssg......', '.....sSdSs......', '....gsssssg.....', '....sSSSSSs.....', '...gsssdsssg....',
    '...sSSSdSSSs....', '..gssssdssssg...', '..sSSSSSSSSSs...', '.gsssssssssssg..', '.sSSSSSSSSSSSs..', 'GGGGGGGGGGGGGGG.'] },
  // Aetherhold: a white spire with a halo
  heaven: { pal: { w: '#eceae0', W: '#c8c4b8', y: '#e8d070', Y: '#c8a040' }, rows: [
    '.....yyyyy......', '....y.....y.....', '.....yyyyy......', '.......w........', '......wWw.......', '......wWw.......',
    '.....wwWww......', '.....wyWyw......', '.....wwWww......', '....wwwWwww.....', '...yyyyyyyyy....', '..WWWWWWWWWWW...'] },
  // the Prism Wood: a great cluster of crystals
  crystal: { pal: { c: '#b8a8e8', C: '#7a68b8', l: '#e8e0ff', p: '#ff9ad5' }, rows: [
    '.......l........', '......lc........', '..l...lcC..c....', '..lc..lcC.lcC...', '..lcC.lpC.lcC...', '.llcC.lcCllcC...',
    '.lccC.lcClccC...', '.lccCllcCcccC...', 'llcccCcccCccCC..', 'lcccccccccccCC..', 'CCCCCCCCCCCCCC..'] },
  // the Drowsing Vale: a palace of towers under a crescent moon
  dream: { pal: { w: '#d8d0ec', W: '#a8a0c8', y: '#e8d070', p: '#8a6ac8', d: '#3a3058' }, rows: [
    '.........yy.....', '..........yy....', '..p.......yy....', '..w...p..yy.....', '..w...w.........', '.www..w...p.....', '.wdw.www..w.....',
    '.www.wdw.www....', '.wWwwwwwwwdw....', '.wWwwwdwwwww....', '.wWwwwwwwwWw....', 'WWWWWWWWWWWWW...'] },
  // the Frostpeaks: an ice throne on a glacier
  frost: { pal: { i: '#e8f4ff', I: '#a8c8e0', b: '#6a8aa8', w: '#ffffff' }, rows: [
    '..i.....i.......', '..iI...iI.......', '..iI.i.iI.i.....', '.iiIiIiiIiI.....', '.iIIiIiIIiI.....', '.iIbbbbbbIi.....',
    '.iIbIIIIbIi.....', '.iIbIIIIbIi.....', '.iIIIIIIIIi.....', 'wwiiiiiiiiiww...', 'wIIIIIIIIIIIIw..', 'IIIIIIIIIIIIIII.'] },
  peak: { pal: { y: '#e0bb62', Y: '#a8842e', r: '#e07060', k: '#6a655e' }, rows: [
    '................', '..y....y....y...', '..yy..yyy..yy...', '..yyyyyyyyyyy...', '..yryyyyyyryy...', '..yyyyyryyyyy...', '..YYYYYYYYYYY...',
    '................', '.....kkkkk......', '...kkkkkkkkk....', '.kkkkkkkkkkkkk..'] },
};
function landmarkCanvas(kind) {
  const art = LANDMARK[kind], rows = art.rows;
  const c = document.createElement('canvas'); c.width = 16; c.height = rows.length + 2;
  const x = c.getContext('2d');
  const at = (X, Y) => (Y < 0 || Y >= rows.length || X < 0 || X >= rows[Y].length ? '.' : rows[Y][X]);
  for (let Y = -1; Y <= rows.length; Y++) for (let X = 0; X < 16; X++) {
    const ch = at(X, Y);
    if (ch !== '.') { x.fillStyle = art.pal[ch]; x.fillRect(X, Y + 1, 1, 1); }
    else if ([[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => at(X + dx, Y + dy) !== '.')) { x.fillStyle = '#0b1017'; x.fillRect(X, Y + 1, 1, 1); }
  }
  return c;
}
// The lanes of each current, in order: every hex with a next hex that's nobody's next is a lane's start.
function lanes(world) {
  const { cur } = seaMap(world), into = new Set(cur.values()), out = [];
  for (const a of cur.keys()) {
    if (into.has(a)) continue;
    const lane = [a];
    while (cur.has(lane[lane.length - 1])) lane.push(cur.get(lane[lane.length - 1]));
    out.push(lane);
  }
  return out;
}

// ------------------------------------------------------------------ the scene
export class MapView {
  constructor(parent, world, handlers) {
    this.world = world;
    this.handlers = handlers;
    this.ready = false;
    this.pending = null;
    this.paintedKey = null;
    this.tokens = new Map();
    this.zoom = innerWidth > 1500 ? 2 : innerWidth > 900 ? 2 : 1;
    const self = this;
    this.game = new Phaser.Game({
      type: Phaser.AUTO, parent, backgroundColor: '#0d2433', pixelArt: true, roundPixels: true,
      scale: { mode: Phaser.Scale.RESIZE, width: '100%', height: '100%' },
      banner: false, audio: { noAudio: true },
      scene: { create() { self.create(this); }, update() { self.tick(); } },
    });
  }

  create(scene) {
    this.scene = scene;
    this.canvas = document.createElement('canvas');
    this.canvas.width = MAP_W; this.canvas.height = MAP_H;
    this.tex = scene.textures.addCanvas('terrain', this.canvas);
    scene.add.image(0, 0, 'terrain').setOrigin(0);
    this.surf = [0, 1].map(() => { const c = document.createElement('canvas'); c.width = MAP_W; c.height = MAP_H; return c; });
    this.surfTex = this.surf.map((c, i) => scene.textures.addCanvas('surf' + i, c));
    this.surfImg = [0, 1].map(i => scene.add.image(0, 0, 'surf' + i).setOrigin(0).setAlpha(i ? 0 : 1));
    // the surf washes in and out: frame B fades up as frame A fades down, and back
    scene.tweens.addCounter({ from: 0, to: 1, duration: 2400, yoyo: true, repeat: -1, ease: 'Sine.easeInOut',
      onUpdate: tw => { const v = tw.getValue(); this.surfImg[0].setAlpha(1 - v * 0.85); this.surfImg[1].setAlpha(v); } });
    // high tide: the whole map a shade darker and bluer
    this.tideTint = scene.add.rectangle(0, 0, MAP_W, MAP_H, 0x0a2a4a, 0).setOrigin(0);
    this.layerSea = scene.add.container();
    this.layerWaves = scene.add.container();
    // the other regions' changing ground: jungle trails, then lava (its bright cores pulse)
    this.gBiome = scene.add.graphics();
    this.gLavaHot = scene.add.graphics();
    scene.tweens.add({ targets: this.gLavaHot, alpha: { from: 0.35, to: 1 }, duration: 900, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
    this.gReach = scene.add.graphics();
    this.layerPlaces = scene.add.container();
    this.gPaths = scene.add.graphics();
    this.gForecast = scene.add.graphics();
    this.layerForecast = scene.add.container();
    this.layerUnits = scene.add.container();
    this.gFog = scene.add.graphics();
    // above the fog: what the party knows of without seeing it
    this.gWeather = scene.add.graphics();
    this.layerWeather = scene.add.container();
    this.gRaids = scene.add.graphics();
    this.layerLand = scene.add.container();
    this.layerLabels = scene.add.container();
    this.gHover = scene.add.graphics();
    const cam = scene.cameras.main;
    cam.setBounds(-400, -300, MAP_W + 800, MAP_H + 600);
    cam.setZoom(this.zoom);
    // input: drag to pan, click to choose, hover to inspect
    let down = null;
    scene.input.on('pointerdown', p => { down = { x: p.x, y: p.y, sx: cam.scrollX, sy: cam.scrollY, moved: false }; });
    scene.input.on('pointermove', p => {
      if (down && p.isDown) {
        const dx = p.x - down.x, dy = p.y - down.y;
        if (Math.abs(dx) + Math.abs(dy) > 6) down.moved = true;
        if (down.moved) { cam.scrollX = down.sx - dx / cam.zoom; cam.scrollY = down.sy - dy / cam.zoom; }
      }
      const wp = cam.getWorldPoint(p.x, p.y);
      const t = tileAt(wp.x, wp.y);
      if (t !== this.hoverTile) { this.hoverTile = t; this.drawHover(); }
      this.handlers.hover?.(t, p.event.clientX, p.event.clientY);
    });
    scene.input.on('pointerup', p => {
      if (down && !down.moved) {
        const wp = cam.getWorldPoint(p.x, p.y);
        const t = tileAt(wp.x, wp.y);
        if (t >= 0) this.handlers.click?.(t);
      }
      down = null;
    });
    scene.input.on('gameout', () => { this.hoverTile = -1; this.drawHover(); this.handlers.hover?.(-1); });
    scene.input.on('wheel', (p, objs, dx, dy) => this.zoomBy(dy > 0 ? -1 : 1, p.x, p.y));
    this.placeSea();
    this.placeLandmarks();
    this.ready = true;
    if (this.pending) { const [g, o] = this.pending; this.pending = null; this.setState(g, o); }
  }

  // The minimap follows the camera: redrawn when the view moves (checked each frame, drawn at most
  // a few times a second).
  tick() {
    if (!this.mini || !this.scene) return;
    const cam = this.scene.cameras.main, key = `${cam.scrollX | 0},${cam.scrollY | 0},${cam.zoom},${cam.width},${cam.height}`;
    const now = performance.now();
    if (key !== this.miniKey && now - (this.miniAt || 0) > 120) { this.miniKey = key; this.miniAt = now; this.drawMinimap(); }
  }

  zoomBy(d, px, py) {
    if (!this.scene) return;
    const steps = [1, 2, 3];
    const cam = this.scene.cameras.main;
    const i = Math.max(0, Math.min(steps.length - 1, steps.indexOf(this.zoom) + d));
    if (steps[i] === this.zoom) return;
    const before = cam.getWorldPoint(px ?? cam.width / 2, py ?? cam.height / 2);
    this.zoom = steps[i];
    cam.setZoom(this.zoom);
    cam.preRender();
    const after = cam.getWorldPoint(px ?? cam.width / 2, py ?? cam.height / 2);
    cam.scrollX += before.x - after.x; cam.scrollY += before.y - after.y;
    this.drawLabels();
  }

  centerOn(t, smooth = true) {
    if (!this.scene) { this.centerPending = t; return; }
    const [x, y] = center(t);
    const cam = this.scene.cameras.main;
    if (smooth) cam.pan(x, y, 400, 'Sine.easeInOut'); else cam.centerOn(x, y);
  }

  setState(game, opts) {
    if (!this.ready) { this.pending = [game, opts]; return; }
    this.state = game; this.opts = opts;
    const key = game.sea + game.tide;
    if (key !== this.paintedKey) {
      paintTerrain(this.canvas, this.world, game, this.surf);
      this.tex.refresh(); this.surfTex.forEach(t => t.refresh());
      this.paintedKey = key;
      this.placeWaves(game);
    }
    if (this.centerPending !== undefined) { this.centerOn(this.centerPending, false); this.centerPending = undefined; }
    const tint = game.tide === 'high' ? 0.16 : 0;
    if (this.tideTint.alpha !== tint && this.tintTo !== tint) { this.tintTo = tint; this.scene.tweens.add({ targets: this.tideTint, alpha: tint, duration: 1400 }); }
    this.drawBiome(); this.drawReach(); this.drawPlaces(); this.drawPaths(); this.drawForecast(); this.drawUnits(); this.drawFog();
    this.drawWeather(); this.drawRaids(); this.drawLandmarks(); this.drawLabels(); this.drawHover(); this.drawMinimap();
  }

  // Currents flow (light dashes running down each lane) and whirlpools turn. Placed once: the sea's
  // extras never change.
  placeSea() {
    const L = this.layerSea, sc = this.scene;
    for (const lane of lanes(this.world)) {
      for (let i = 0; i + 1 < lane.length; i++) {
        const [x0, y0] = center(lane[i]), [x1, y1] = center(lane[i + 1]);
        const ang = Math.atan2(y1 - y0, x1 - x0);
        for (const k of [0, 0.5]) {
          const r = sc.add.rectangle(x0, y0, 7, 2, 0xdff4f7).setAlpha(0).setRotation(ang);
          L.add(r);
          sc.tweens.add({ targets: r, x: x1, y: y1, duration: 1300, delay: (i * 260 + k * 1300) % 2600, repeat: -1,
            onRepeat: () => r.setPosition(x0, y0), alpha: { from: 0, to: 0.85 }, yoyo: false, ease: 'Linear' });
        }
      }
    }
    for (const t of seaMap(this.world).pool) {
      const [cx, cy] = center(t);
      const g = sc.add.graphics({ x: cx, y: cy });
      for (let k = 0; k < 3; k++) { g.lineStyle(2, 0xbfe4ec, 0.55 - k * 0.12); g.beginPath(); g.arc(0, 0, 6 + k * 5, k * 2, k * 2 + 2.4); g.strokePath(); }
      g.setScale(1, 0.8);
      L.add(g);
      sc.tweens.add({ targets: g, rotation: -Math.PI * 2, duration: 3200, repeat: -1 });
    }
  }

  // The objectives' landmarks above the fog (and the Lighthouse's beam sweeping round while it stands).
  placeLandmarks() {
    const sc = this.scene, L = this.layerLand;
    this.marks = [];
    for (const m of this.world.landmarks || []) {
      const [cx, cy] = center(m.tile);
      const kind = LANDMARK[m.region] ? m.region : 'peak';
      const key = 'mark_' + kind;
      if (!sc.textures.exists(key)) sc.textures.addCanvas(key, landmarkCanvas(kind));
      const c = sc.add.container(cx, cy + 12);
      if (kind === 'storm') {
        const beam = sc.add.graphics({ x: 0, y: -48 });
        beam.fillStyle(0xfff2b8, 0.22); beam.fillTriangle(0, 0, 90, -14, 90, 14);
        beam.fillStyle(0xfff2b8, 0.12); beam.fillTriangle(0, 0, 90, -26, 90, 26);
        c.add(beam);
        sc.tweens.add({ targets: beam, rotation: Math.PI * 2, duration: 6000, repeat: -1 });
        c.beam = beam;
      }
      c.add(sc.add.ellipse(0, 0, 30, 9, 0x000000, 0.3));
      c.add(sc.add.image(0, 2, key).setOrigin(0.5, 1).setScale(2.2));
      L.add(c);
      this.marks.push({ ...m, c });
    }
  }

  drawLandmarks() {
    const st = this.state;
    for (const m of this.marks || []) {
      const cleared = m.region !== 'peak' && st.cleared.includes(m.region);
      const sealed = m.region === 'peak' && st.cleared.length < 3;
      m.c.setAlpha(cleared ? 0.55 : 1);
      m.c.list.forEach(o => o.setTint?.(sealed ? 0x9a9aa6 : 0xffffff));
      if (m.c.beam) m.c.beam.setVisible(!cleared);
      m.c.setDepth(1);
    }
  }

  // Region names over the whole map when zoomed all the way out.
  drawLabels() {
    const L = this.layerLabels;
    if (!this.scene) return;
    if (!L.list.length && this.opts?.regions) {
      const sum = {};
      for (let t = 0; t < W * H; t++) {
        const r = this.world.reg[t];
        if (!r || r === 'peak' || this.world.elev[t] <= 1) continue;
        const [x, y] = center(t), a = (sum[r] ||= [0, 0, 0]);
        a[0] += x; a[1] += y; a[2]++;
      }
      for (const [r, [x, y, n]] of Object.entries(sum)) {
        L.add(this.scene.add.text(x / n, y / n, this.opts.regions[r].toUpperCase(), { fontFamily: 'Fraunces, Georgia, serif', fontSize: '22px', fontStyle: 'bold', color: '#f3ead2', stroke: '#0b1017', strokeThickness: 5, resolution: 3 })
          .setOrigin(0.5).setAlpha(0.9));
      }
    }
    L.setVisible(this.zoom <= 1);
  }

  // The Verdant Deep's cut trails (a beaten path through each, joined to the trails beside it) and
  // Cinderreach's lava (molten rock with a dark crust; the hot cores pulse).
  drawBiome() {
    const g = this.gBiome, hot = this.gLavaHot, st = this.state;
    g.clear(); hot.clear();
    const trails = new Set(Object.keys(st.trails || {}).map(Number));
    for (const t of trails) {
      const [cx, cy] = center(t);
      g.fillStyle(0x7a5a32, 0.5); g.fillEllipse(cx, cy + 3, 22, 11);
      for (const n of neighbors(t)) if (trails.has(n) && n > t) {
        const [nx, ny] = center(n);
        g.lineStyle(7, 0x7a5a32, 0.5); g.lineBetween(cx, cy + 3, nx, ny + 3);
        g.lineStyle(2, 0xa88a5a, 0.6); g.lineBetween(cx, cy + 3, nx, ny + 3);
      }
    }
    for (const [k, left] of Object.entries(st.lava || {})) {
      const t = +k, [cx, cy] = center(t);
      const cooling = left <= 1;
      g.fillStyle(cooling ? 0x5a2a1a : 0xa8381a, 0.92); g.fillPoints(hexPoints(t, 2), true);
      g.fillStyle(0x2a1a16, 0.85);
      for (let i = 0; i < 7; i++) g.fillEllipse(cx + (hash(t, i) - 0.5) * 34, cy + (hash(t, i + 9) - 0.5) * 34, 8 + hash(t, i + 3) * 8, 5 + hash(t, i + 5) * 4);
      if (!cooling) {
        hot.fillStyle(0xffa63a, 0.9);
        for (let i = 0; i < 5; i++) hot.fillEllipse(cx + (hash(t, i + 20) - 0.5) * 26, cy + (hash(t, i + 29) - 0.5) * 26, 6, 3);
        hot.fillStyle(0xffe07a, 0.9); hot.fillEllipse(cx, cy, 5, 3);
      }
    }
  }

  // Storms: a dark cloud over the hexes inside (rain for a squall, blown sand for a sandstorm, snow for
  // a blizzard), and a dashed ring where it drifts next.
  drawWeather() {
    const g = this.gWeather, L = this.layerWeather, sc = this.scene;
    g.clear();
    const ids = new Set();
    const r = this.opts?.squallR ?? 1;
    const LOOK = { squall: { shade: 0x0e1620, a: 0.32, cloud: 0x3a4250, drop: 0xa8c4d8 }, sandstorm: { shade: 0x5a3a18, a: 0.34, cloud: 0xa8844e, drop: 0xe0c48a },
      blizzard: { shade: 0xc8dcea, a: 0.26, cloud: 0xd8e4ee, drop: 0xffffff } };
    for (const q of this.state.squalls || []) {
      // the hexes under a storm go dark (or white, in a blizzard)
      const L2 = LOOK[q.kind] || LOOK.squall;
      for (let t = 0; t < W * H; t++) if (dist(t, q.tile) <= r) { g.fillStyle(L2.shade, L2.a); g.fillPoints(hexPoints(t, -0.5), true); }
    }
    for (const q of this.state.squalls || []) {
      ids.add(q.id);
      let c = L.list.find(o => o.qid === q.id);
      const [cx, cy] = center(q.tile);
      if (!c) {
        const L2 = LOOK[q.kind] || LOOK.squall;
        c = sc.add.container(cx, cy); c.qid = q.id;
        for (let k = 0; k < 9; k++) {
          const a = k / 9 * Math.PI * 2, d = k ? 26 + hash(k, q.id) * 22 : 0;
          c.add(sc.add.ellipse(Math.cos(a) * d * r, Math.sin(a) * d * 0.7 * r - 14, 46 + hash(k, 3) * 26, 26 + hash(k, 5) * 12, L2.cloud, q.kind === 'blizzard' ? 0.42 : 0.5));
        }
        for (let k = 0; k < 22; k++) {
          const x = (hash(k, 11) - 0.5) * 110 * r, y = (hash(k, 12) - 0.5) * 70 * r;
          if (q.kind === 'sandstorm') {
            // blown sand: streaks racing sideways
            const st2 = sc.add.rectangle(x, y, 9, 1, L2.drop, 0.7);
            c.add(st2);
            sc.tweens.add({ targets: st2, x: x + 30, alpha: { from: 0.8, to: 0 }, duration: 600, delay: hash(k, 13) * 600, repeat: -1 });
          } else if (q.kind === 'blizzard') {
            // snow: flakes drifting down slowly, swaying
            const fl = sc.add.rectangle(x, y, 2, 2, L2.drop, 0.9);
            c.add(fl);
            sc.tweens.add({ targets: fl, y: y + 22, x: x - 6, alpha: { from: 0.95, to: 0 }, duration: 1400, delay: hash(k, 13) * 1400, repeat: -1 });
          } else {
            const drop = sc.add.rectangle(x, y, 1, 7, L2.drop, 0.7).setRotation(0.25);
            c.add(drop);
            sc.tweens.add({ targets: drop, y: y + 18, x: x + 5, alpha: { from: 0.75, to: 0 }, duration: 520, delay: hash(k, 13) * 520, repeat: -1 });
          }
        }
        L.add(c);
        sc.tweens.add({ targets: c.list.slice(0, 9), scaleX: 1.08, scaleY: 1.06, duration: 2200, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
      } else if (!c.moving && (c.x !== cx || c.y !== cy)) {
        c.moving = true;
        sc.tweens.add({ targets: c, x: cx, y: cy, duration: 900, ease: 'Sine.easeInOut', onComplete: () => { c.moving = false; } });
      }
      if (q.next != null && !this.opts?.hideForecast) {
        const [nx, ny] = center(q.next);
        g.lineStyle(2, 0xa8c4d8, 0.6);
        for (let k = 0; k < 16; k += 2) g.lineBetween(nx + Math.cos(k / 16 * 6.283) * 30 * r, ny + Math.sin(k / 16 * 6.283) * 24 * r, nx + Math.cos((k + 1) / 16 * 6.283) * 30 * r, ny + Math.sin((k + 1) / 16 * 6.283) * 24 * r);
      }
    }
    for (const c of [...L.list]) if (!ids.has(c.qid)) { sc.tweens.killTweensOf([c, ...c.list]); c.destroy(); }
  }

  // Raids: the road each will take to its town, dashed red, and a torch on the town it's after; an
  // occupied town flies the raiders' red banner.
  drawRaids() {
    const g = this.gRaids; g.clear();
    if (this.raidMarks) this.raidMarks.forEach(o => o.destroy());
    this.raidMarks = [];
    for (const r of this.state.raids || []) {
      const [tx, ty] = center(r.to);
      if (!r.occupy && !this.opts?.hideForecast) {
        const pts = [r.tile, ...r.road].map(center);
        for (let i = 1; i < pts.length; i++) {
          const [x0, y0] = pts[i - 1], [x1, y1] = pts[i], n = Math.max(1, Math.floor(Math.hypot(x1 - x0, y1 - y0) / 6));
          for (let k = 0; k < n; k += 2) {
            const a = k / n, b = Math.min(1, (k + 1) / n);
            g.lineStyle(4, 0x0b1017, 0.5); g.lineBetween(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, x0 + (x1 - x0) * b, y0 + (y1 - y0) * b);
            g.lineStyle(2, 0xff6a4a, 0.9); g.lineBetween(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a, x0 + (x1 - x0) * b, y0 + (y1 - y0) * b);
          }
        }
        g.lineStyle(2, 0xff6a4a, 0.95); g.strokeCircle(tx, ty, 20);
        const t = this.scene.add.text(tx + 20, ty - 22, String(r.road.length), { fontFamily: 'Inter', fontSize: '10px', fontStyle: 'bold', color: '#ffd8cc', backgroundColor: '#6a1d2a', padding: { x: 3, y: 1 }, resolution: 4 }).setOrigin(0.5);
        this.raidMarks.push(t);
      } else if (r.occupy) {
        // smoke over the town (the raiders' own token carries their banner)
        for (let k = 0; k < 3; k++) {
          const puff = this.scene.add.circle(tx + 4 + k * 4, ty - 18, 4, 0x4a4650, 0.6);
          this.scene.tweens.add({ targets: puff, y: ty - 44, alpha: 0, scale: 2, duration: 1800, delay: k * 600, repeat: -1 });
          this.raidMarks.push(puff);
        }
      }
    }
    this.raidMarks.forEach(o => this.layerLand.add(o));
  }

  // What the rising tide brings, arriving: rings spread where each thing lands, and a wreck or a
  // landing party comes in on a boat from the nearest open water.
  arrive(t, kind) {
    if (!this.scene) return;
    const sc = this.scene, [cx, cy] = center(t);
    for (let k = 0; k < 3; k++) {
      const ring = sc.add.ellipse(cx, cy + 8, 22, 9).setStrokeStyle(kind === 'garrison' ? 3 : 2, kind === 'boon' ? 0xffe7a8 : kind === 'garrison' ? 0xe0705a : 0xbfe4ec, 0.9);
      this.layerLand.add(ring);
      sc.tweens.add({ targets: ring, scale: 3.2, alpha: 0, duration: 1300, delay: 250 + k * 320, onComplete: () => ring.destroy() });
    }
    if (!['wreckage', 'landing', 'warband'].includes(kind)) return;
    let from = null;
    for (let r = 2; r <= 4 && from == null; r++) for (let u = 0; u < W * H; u++) if (dist(u, t) === r && terrain(this.world, this.state, u) === 'deep') { from = u; break; }
    if (from == null) return;
    const [fx, fy] = center(from);
    const boat = sc.add.image(fx, fy + 8, this.texFor('boat', boatCanvas)).setScale(1.4).setAlpha(0);
    this.layerLand.add(boat);
    sc.tweens.add({ targets: boat, alpha: 1, duration: 200 });
    sc.tweens.add({ targets: boat, x: cx, y: cy + 8, duration: 1500, ease: 'Sine.easeOut', onComplete: () => sc.tweens.add({ targets: boat, alpha: 0, duration: 400, onComplete: () => boat.destroy() }) });
    sc.tweens.add({ targets: boat, angle: { from: -6, to: 6 }, duration: 380, yoyo: true, repeat: 3 });
  }

  // ---------------------------------------------------------------- the minimap
  attachMinimap(canvas, onPick) {
    this.mini = canvas; this.miniPick = onPick;
    canvas.addEventListener('pointerdown', e => {
      const r = canvas.getBoundingClientRect(), s = canvas.width / MAP_W;
      const x = (e.clientX - r.left) * (canvas.width / r.width) / s, y = (e.clientY - r.top) * (canvas.height / r.height) / s;
      this.scene?.cameras.main.pan(x, y, 300, 'Sine.easeInOut');
    });
    this.drawMinimap();
  }

  drawMinimap() {
    const c = this.mini, st = this.state;
    if (!c || !st) return;
    const x = c.getContext('2d'), s = c.width / MAP_W;
    x.fillStyle = '#0b1017'; x.fillRect(0, 0, c.width, c.height);
    x.fillStyle = '#111a24'; x.fillRect(HW / 2 * s, RS / 2 * s, (MAP_W - HW) * s, (MAP_H - RS) * s);
    const vis = visibleTiles(st), col = MINI_COL;
    for (let t = 0; t < W * H; t++) {
      const [cx, cy] = center(t);
      if (st.seen[t] !== '1') continue;  // the fog hides the unexplored here too
      const kind = terrain(this.world, st, t), sk = (this.world.regions || []).includes(this.world.reg[t]) ? SKIN[this.world.reg[t]]?.[kind] : null;
      x.fillStyle = sk ? `rgb(${sk[0].join(',')})` : col[kind] || col.grass;
      x.globalAlpha = vis.has(t) ? 1 : 0.6;
      x.fillRect((cx - HW / 2) * s, (cy - RS / 2) * s, HW * s + 0.6, RS * s + 0.6);
    }
    x.globalAlpha = 1;
    const dot = (t, color, r = 2.2) => { const [cx, cy] = center(t); x.fillStyle = color; x.beginPath(); x.arc(cx * s, cy * s, r, 0, 7); x.fill(); };
    for (const m of this.world.landmarks || []) dot(m.tile, st.cleared.includes(m.region) ? '#8a7a50' : '#e0bb62', 3);
    for (const r of st.raids || []) dot(r.tile, '#ff6a4a', 2.6);
    for (const o of st.opps || []) dot(o.tile, '#ffe7a8', 2);
    for (const q of st.squalls || []) { const [cx, cy] = center(q.tile); x.fillStyle = 'rgba(120,135,160,0.55)'; x.beginPath(); x.arc(cx * s, cy * s, 9, 0, 7); x.fill(); }
    st.heroes.forEach((hero, h) => { if (hero.alive) dot(hero.tile, '#' + SEATS[h].toString(16).padStart(6, '0'), 3); });
    const cam = this.scene?.cameras.main;
    if (cam) {
      const v = cam.worldView;
      x.strokeStyle = '#f3ead2'; x.lineWidth = 1.5;
      x.strokeRect(Math.max(0, v.x * s), Math.max(0, v.y * s), Math.min(c.width, v.width * s), Math.min(c.height, v.height * s));
    }
  }

  // Glints on the open sea: short light strokes that fade in and out, so the water moves. Cheap:
  // a few dozen tweened rectangles, placed again only when the sea or the tide changes.
  placeWaves(game) {
    const L = this.layerWaves;
    this.scene.tweens.killTweensOf(L.list);
    L.removeAll(true);
    const deep = [];
    for (let t = 0; t < W * H; t++) if (terrain(this.world, game, t) === 'deep') deep.push(t);
    const n = Math.min(90, Math.floor(deep.length / 3));
    for (let i = 0; i < n; i++) {
      const t = deep[Math.floor(hash(i, 77) * deep.length)];
      const [cx, cy] = center(t);
      const x = cx + (hash(i, 78) - 0.5) * 32, y = cy + (hash(i, 79) - 0.5) * 30;
      const r = this.scene.add.rectangle(x, y, 4 + Math.floor(hash(i, 80) * 4), 1, 0xbfe4ec).setAlpha(0);
      L.add(r);
      this.scene.tweens.add({ targets: r, alpha: 0.75, x: x + 3, duration: 1100 + hash(i, 81) * 900, delay: hash(i, 82) * 4000,
        yoyo: true, repeat: -1, repeatDelay: 1500 + hash(i, 83) * 3000, ease: 'Sine.easeInOut' });
    }
  }

  // Where the selected hero can get to this turn: a lit area with a bold outline around its edge,
  // and a red ring on hexes where walking in starts a fight.
  drawReach() {
    const g = this.gReach; g.clear();
    const r = this.opts?.reach;
    if (!r) return;
    const here = this.state.heroes[this.opts.sel]?.tile;
    const inReach = new Set([...r.best.keys()]);
    for (const t of inReach) {
      if (t === here) continue;
      g.fillStyle(0xe0bb62, 0.2); g.fillPoints(hexPoints(t, 1), true);
    }
    g.lineStyle(3, 0xffd77a, 0.95);
    for (const t of inReach) {
      const pts = hexPoints(t, 0), [cx, cy] = center(t);
      const nb = neighbors(t).map(n => [n, center(n)]);
      for (let i = 0; i < 6; i++) {
        const a = pts[i], b = pts[(i + 1) % 6];
        const mx = (a.x + b.x) - cx, my = (a.y + b.y) - cy;  // the centre of the hex across this edge
        const across = nb.find(([, [nx, ny]]) => Math.abs(nx - mx) < 6 && Math.abs(ny - my) < 6);
        if (!across || !inReach.has(across[0])) g.lineBetween(a.x, a.y, b.x, b.y);
      }
    }
    const vis = visibleTiles(this.state);
    for (const gr of this.state.groups) {
      if (!inReach.has(gr.tile) || !vis.has(gr.tile)) continue;
      g.lineStyle(3, 0xd0624f, 0.95); g.strokePoints(hexPoints(gr.tile, 4), true);
    }
  }

  // The turn as planned: where visible enemies will step (red arrows), the fights that will start
  // (a crossed-swords marker) and dashed lines from every hero who'll be pulled into one.
  drawForecast() {
    const g = this.gForecast; g.clear();
    const L = this.layerForecast; L.removeAll(true);
    const fc = this.state.forecast;
    if (!fc || this.opts?.hideForecast) return;
    for (const st of fc.steps) {
      const [x0, y0] = center(st.from), [x1, y1] = center(st.to);
      const dx = x1 - x0, dy = y1 - y0, len = Math.hypot(dx, dy), ux = dx / len, uy = dy / len;
      const sx = x0 + ux * 12, sy = y0 + uy * 12, ex = x1 - ux * 10, ey = y1 - uy * 10;
      g.lineStyle(3, 0x0b1017, 0.6); g.lineBetween(sx, sy, ex, ey);
      g.lineStyle(2, 0xff7a5c, 0.95); g.lineBetween(sx, sy, ex, ey);
      g.fillStyle(0xff7a5c, 0.95);
      g.fillTriangle(ex + ux * 6, ey + uy * 6, ex - uy * 5 - ux * 2, ey + ux * 5 - uy * 2, ex + uy * 5 - ux * 2, ey - ux * 5 - uy * 2);
    }
    for (const f of fc.fights) {
      const [fx, fy] = center(f.tile);
      for (const h of f.heroes) {
        const end = fc.ends[h];
        if (end === undefined || end === f.tile) continue;
        const [hx, hy] = center(end);
        const len = Math.hypot(fx - hx, fy - hy), n = Math.floor(len / 6);
        g.fillStyle(SEATS[h], 0.95);
        for (let k = 1; k < n; k += 2) g.fillCircle(hx + (fx - hx) * k / n, hy + (fy - hy) * k / n, 1.6);
      }
      g.fillStyle(0x6a1d2a, 0.85); g.fillCircle(fx, fy - 30, 11);
      g.lineStyle(2, 0xff9a80, 1); g.strokeCircle(fx, fy - 30, 11);
      const txt = this.scene.add.text(fx, fy - 30, '⚔', { fontFamily: 'Inter', fontSize: '13px', color: '#ffe8de', resolution: 4 }).setOrigin(0.5);
      L.add(txt);
      f.heroes.forEach((h, i) => {
        const dot = this.scene.add.circle(fx - (f.heroes.length - 1) * 5 + i * 10, fy - 15, 4, SEATS[h]).setStrokeStyle(1, 0x0b1017);
        L.add(dot);
      });
    }
  }

  drawPlaces() {
    const L = this.layerPlaces;
    if (this.oppRings) this.scene.tweens.killTweensOf(this.oppRings);
    this.oppRings = [];
    L.removeAll(true);
    for (const [t, p] of Object.entries(this.state.places)) {
      const [cx, cy] = center(+t);
      // an event shows what it risks in its icon (a seal's colour, a dagger for a fight); once seen, a plain note
      const kind = p.kind === 'event' && !p.done && (p.risk === 'risky' || p.risk === 'fight') ? `event_${p.risk}` : p.kind === 'beacon' && p.lit ? 'beacon_lit' : p.kind;
      const tex = this.texFor('place_' + kind, () => placeCanvas(kind));
      const yoff = p.kind === 'town' ? 14 : 2;
      // places are drawn half again as big as their 16px art, on a soft shadow, so they read at a glance
      // (objectives and the peak are drawn as landmarks, above the fog)
      const mark = p.kind === 'dungeon' || p.kind === 'peak';
      if (p.kind !== 'town' && !mark) L.add(this.scene.add.ellipse(cx, cy + yoff + 10, 22, 7, 0x000000, 0.3));
      const img = this.scene.add.image(cx, cy + yoff, tex).setOrigin(0.5, 0.5).setScale(1.5).setVisible(!mark);
      if (p.kind === 'town') {
        img.setVisible(false);
        // a town's name under it, so it's still findable with heroes standing on its houses
        L.add(this.scene.add.text(cx, cy + 25, p.name, { fontFamily: 'Inter', fontSize: '8px', fontStyle: 'bold', color: '#f3ead2', stroke: '#0b1017', strokeThickness: 3, resolution: 4 }).setOrigin(0.5, 0.5));
      }
      if (p.done || p.taken || (p.kind === 'dungeon' && this.state.cleared.includes(p.region))) img.setAlpha(0.45);
      if (p.kind === 'peak' && this.state.cleared.length < 3) img.setTint(0x8a8a8a);
      if (p.kind === 'shrine' && p.dark) img.setTint(0xb48ae0);
      if (p.kind === 'shrine' && p.sea) img.setTint(0x7ad8d0);
      L.add(img);
      // what's there, before anyone arrives: a wreck's loot, an event's risk, a garrison's size
      const dot = (x, y, col) => L.add(this.scene.add.circle(cx + x, cy + y, 3.5, col).setStrokeStyle(1, 0x0b1017));
      if (p.kind === 'wreck' && !p.done) dot(13, 10, RARITY_COL[p.rarity] || 0xb8b0a0);
      // an event with an option for a class someone in the party has: a gold spark by it
      if (p.kind === 'event' && !p.done && p.needs?.some(k => this.state.heroes.some(x => x.alive && x.cls === k)))
        L.add(this.scene.add.text(cx - 13, cy - 13, '✦', { fontFamily: 'Inter', fontSize: '11px', color: '#ffd870', stroke: '#0b1017', strokeThickness: 3, resolution: 4 }).setOrigin(0.5));
      if (p.kind === 'cove' && !p.done) dot(13, 10, RARITY_COL.rare);
      const gs = p.kind === 'dungeon' && !this.state.cleared.includes(p.region) ? this.state.garrison?.[p.region] : null;
      if (gs?.n) L.add(this.scene.add.text(cx + 12, cy - 16, '+' + gs.n, { fontFamily: 'Inter', fontSize: '10px', fontStyle: 'bold', color: '#ffb3a0', stroke: '#0b1017', strokeThickness: 3, resolution: 4 }).setOrigin(0.5));
      if (p.kind === 'town' && p.docks) {
        // a small flag marks docks
        const fl = this.scene.add.rectangle(cx + 18, cy - 14, 2, 10, 0x2a1e1a).setOrigin(0.5, 1);
        const cloth = this.scene.add.rectangle(cx + 19, cy - 24, 7, 5, 0xc9a24a).setOrigin(0, 0);
        L.add(fl); L.add(cloth);
      }
    }
    this.drawOpps(L);
    this.drawMerchants(L);
    this.drawJobs(L);
  }

  drawMerchants(L) {
    // travelling merchants: a wagon on land, a striped sail at sea, with a gold coin badge
    for (const m of this.state.merchants || []) {
      const [cx, cy] = center(m.tile);
      const sea = ['deep', 'shoal'].includes(terrain(this.world, this.state, m.tile));
      const kind = sea ? 'merchant_sea' : 'merchant';
      const tex = this.texFor('place_' + kind, () => placeCanvas(kind));
      L.add(this.scene.add.ellipse(cx - 2, cy + 16, 22, 6, 0x000000, 0.3));
      L.add(this.scene.add.image(cx - 2, cy + 6, tex).setScale(1.5));
      L.add(this.scene.add.circle(cx + 13, cy - 2, 5, 0xe0bb62).setStrokeStyle(1.5, 0x5a3a1a));
      L.add(this.scene.add.text(cx + 13, cy - 2, '$', { fontFamily: 'Inter', fontSize: '8px', fontStyle: 'bold', color: '#5a3a1a', resolution: 4 }).setOrigin(0.5));
    }
  }

  drawJobs(L) {
    // each job's next stop: a parchment tag with the turns left
    for (const q of this.state.quests || []) {
      if (q.done || q.failed || q.goal == null) continue;
      const [cx, cy] = center(q.goal);
      // a quest's site: a gold tag with a star (no deadline); a job's: parchment with the turns left
      const quest = q.kind === 'trail';
      L.add(this.scene.add.rectangle(cx + 15, cy - 14, 15, 15, quest ? 0xe8c060 : 0xe8dcc0).setStrokeStyle(2, quest ? 0x7a5420 : 0x6a5232).setAngle(45));
      L.add(this.scene.add.text(cx + 15, cy - 14, quest ? '★' : String(q.left), { fontFamily: 'Inter', fontSize: '10px', fontStyle: 'bold', color: '#2a2430', resolution: 4 }).setOrigin(0.5));
    }
  }

  drawOpps(L) {
    // chances that won't wait: a gold ring and the turns left
    for (const o of this.state.opps || []) {
      const [cx, cy] = center(o.tile);
      const ring = this.scene.add.circle(cx, cy + 2, 15).setStrokeStyle(2, 0xe0bb62, 0.95);
      L.add(ring);
      this.oppRings.push(ring);
      this.scene.tweens.add({ targets: ring, scale: 1.15, alpha: 0.55, duration: 900, yoyo: true, repeat: -1 });
      if (o.kind !== 'ship') {
        const tex = this.texFor('place_' + o.kind, () => placeCanvas(o.kind));
        L.add(this.scene.add.image(cx, cy + 2, tex));
      }
      L.add(this.scene.add.text(cx - 13, cy - 15, String(o.left), { fontFamily: 'Inter', fontSize: '10px', fontStyle: 'bold', color: '#ffe7a8', stroke: '#0b1017', strokeThickness: 3, resolution: 4 }).setOrigin(0.5));
    }
  }

  texFor(key, make) {
    if (!this.scene.textures.exists(key)) this.scene.textures.addCanvas(key, make());
    return key;
  }

  drawPaths() {
    const g = this.gPaths; g.clear();
    const plans = this.state.plans || {};
    for (const [hs, p] of Object.entries(plans)) {
      const h = +hs;
      const hero = this.state.heroes[h];
      const preview = this.opts?.preview && this.opts.sel === h ? this.opts.preview : null;
      const path = preview || p.path;
      if (!path || !path.length) continue;
      const mine = this.opts?.mine?.includes(h);
      const col = SEATS[h];
      const pts = [center(hero.tile), ...path.map(center)];
      const alpha = preview ? 0.75 : mine ? 1 : 0.6;
      for (let i = 1; i < pts.length; i++) {
        const [x0, y0] = pts[i - 1], [x1, y1] = pts[i];
        const len = Math.hypot(x1 - x0, y1 - y0), n = Math.floor(len / 7);
        for (let k = 1; k <= n; k++) {
          const f = k / n;
          g.fillStyle(0x0b1017, alpha * 0.6); g.fillRect(Math.round(x0 + (x1 - x0) * f) - 2, Math.round(y0 + (y1 - y0) * f) - 1, 4, 4);
          g.fillStyle(col, alpha); g.fillRect(Math.round(x0 + (x1 - x0) * f) - 1, Math.round(y0 + (y1 - y0) * f) - 2, 3, 3);
        }
      }
      const [ex, ey] = pts[pts.length - 1];
      g.lineStyle(2, col, alpha); g.strokeCircle(ex, ey, 9);
      g.fillStyle(col, alpha * 0.35); g.fillCircle(ex, ey, 8);
    }
  }

  drawUnits() {
    const L = this.layerUnits;
    const st = this.state;
    const seen = new Set();
    // enemies
    for (const gr of st.groups) {
      const id = 'g' + gr.id;
      seen.add(id);
      let tok = this.tokens.get(id);
      const [cx, cy] = center(gr.tile);
      if (!tok) {
        const c = this.scene.add.container(cx, cy);
        const shadow = this.scene.add.ellipse(0, 12, 26, 8, 0x000000, 0.35);
        const img = this.scene.add.image(0, 14, this.texFor('spr_' + gr.foes[0], () => spriteCanvas(gr.foes[0]))).setOrigin(0.5, 1).setFlipX(true);
        c.add([shadow, img]);
        if (gr.sea) {
          // sea beasts: a ring of ripples round them
          const rip = this.scene.add.ellipse(0, 12, 30, 9).setStrokeStyle(1.5, 0xbfe4ec, 0.8);
          c.add(rip);
          this.scene.tweens.add({ targets: rip, scaleX: 1.3, scaleY: 1.3, alpha: 0.2, duration: 1200, repeat: -1 });
        }
        if (gr.raid) {
          // raiders carry their banner
          c.add([this.scene.add.rectangle(-12, 10, 2, 22, 0x2a1e1a).setOrigin(0.5, 1), this.scene.add.rectangle(-11, -12, 9, 6, 0xb0302a).setOrigin(0, 0)]);
        }
        if (gr.foes.length > 1 || gr.lair) {
          const badge = this.scene.add.circle(13, -12, 7, gr.lair ? 0x6a1d2a : 0x10161f).setStrokeStyle(1, 0xd0624f);
          const txt = this.scene.add.text(13, -12, String(gr.foes.length), { fontFamily: 'Inter', fontSize: '10px', fontStyle: 'bold', color: '#ffd8cc', resolution: 4 }).setOrigin(0.5);
          c.add([badge, txt]);
        }
        // "!" over a group that's coming for you this turn
        const alert = this.scene.add.text(0, -24, '!', { fontFamily: 'Inter', fontSize: '16px', fontStyle: 'bold', color: '#ffd36b', stroke: '#6a1d2a', strokeThickness: 4, resolution: 4 }).setOrigin(0.5).setVisible(false);
        c.add(alert);
        L.add(c);
        tok = { c, img, alert, tile: gr.tile, kind: 'g' };
        if (!gr.lair) tok.bob = this.bob(img, 14);
        this.tokens.set(id, tok);
      } else if (tok.tile !== gr.tile && !tok.moving) {
        tok.c.setPosition(cx, cy); tok.tile = gr.tile;
      }
      const hunting = !!this.state.forecast?.steps?.some(st => st.g === gr.id) && !this.opts?.hideForecast;
      if (hunting && !tok.alert.visible) {
        tok.alert.setVisible(true).setScale(0);
        this.scene.tweens.add({ targets: tok.alert, scale: 1, duration: 260, ease: 'Back.easeOut' });
        this.scene.tweens.add({ targets: tok.alert, y: -27, duration: 500, yoyo: true, repeat: -1, delay: 260, ease: 'Sine.easeInOut' });
      } else if (!hunting && tok.alert.visible) {
        this.scene.tweens.killTweensOf(tok.alert);
        tok.alert.setVisible(false).setY(-24);
      }
    }
    // heroes, spread out when sharing a hex
    const byTile = {};
    st.heroes.forEach((hero, h) => { if (hero.alive) (byTile[hero.tile] ||= []).push(h); });
    st.heroes.forEach((hero, h) => {
      const id = 'h' + h;
      if (!hero.alive) { const t = this.tokens.get(id); if (t) { t.c.destroy(); this.tokens.delete(id); } return; }
      seen.add(id);
      // heroes sharing a hex fan out (the middle one a step back) and shrink a little, so each reads
      const mates = byTile[hero.tile], k = mates.indexOf(h), n = mates.length;
      const FAN = { 1: [[0, 0]], 2: [[-9, 0], [9, 0]], 3: [[-13, 2], [0, -4], [13, 2]] };
      const [dx, dy] = (FAN[n] || FAN[3])[Math.min(k, 2)];
      const [cx0, cy0] = center(hero.tile), cx = cx0 + dx, cy = cy0 + dy;
      let tok = this.tokens.get(id);
      if (!tok) {
        const c = this.scene.add.container(cx, cy);
        const ring = this.scene.add.ellipse(0, 12, 24, 9, SEATS[h], 0.85);
        const ring2 = this.scene.add.ellipse(0, 12, 18, 6, 0x0b1017, 0.6);
        const boat = this.scene.add.image(0, 16, this.texFor('boat', boatCanvas)).setOrigin(0.5, 1).setVisible(false);
        const img = this.scene.add.image(0, 14, this.texFor('spr_' + hero.cls, () => spriteCanvas(hero.cls))).setOrigin(0.5, 1);
        c.add([ring, ring2, img, boat]);
        L.add(c);
        tok = { c, img, tile: hero.tile, boat, ring, kind: 'h', x: cx, y: cy };
        tok.bob = this.bob(img, 14);
        this.tokens.set(id, tok);
      } else if (!tok.moving && (tok.tile !== hero.tile || tok.x !== cx || tok.y !== cy)) {
        tok.c.setPosition(cx, cy); tok.tile = hero.tile; tok.x = cx; tok.y = cy;
      }
      tok.boat.setVisible(hero.afloat);
      tok.ring.setVisible(!hero.afloat);
      // a skiff rocks on the swell
      if (hero.afloat && !tok.rock) tok.rock = this.scene.tweens.add({ targets: tok.c, angle: { from: -3, to: 3 }, duration: 1300 + h * 170, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
      else if (!hero.afloat && tok.rock) { tok.rock.remove(); tok.rock = null; tok.c.setAngle(0); }
      tok.c.setDepth(cy);
      const sel = this.opts?.sel === h;
      tok.c.setScale(n > 1 ? 0.85 : 1);
      tok.ring.setFillStyle(SEATS[h], sel ? 1 : 0.75);
    });
    for (const [id, tok] of this.tokens) if (!seen.has(id)) { tok.c.destroy(); this.tokens.delete(id); }
    L.sort('y');
  }

  drawFog() {
    const g = this.gFog; g.clear();
    const st = this.state, vis = visibleTiles(st);
    for (let t = 0; t < W * H; t++) {
      if (st.seen[t] !== '1') { g.fillStyle(0x0b1017, 0.93); g.fillPoints(hexPoints(t, -0.5), true); }
      else if (!vis.has(t)) { g.fillStyle(0x0b1017, 0.32); g.fillPoints(hexPoints(t, -0.5), true); }
    }
  }

  drawHover() {
    const g = this.gHover; g.clear();
    const t = this.hoverTile;
    if (t === undefined || t < 0) return;
    g.lineStyle(2, 0xe0bb62, 0.9); g.strokePoints(hexPoints(t, 1), true);
  }

  // ---------------------------------------------------------------- effects
  // Walk a token along a path, hex by hex, starting from where the path begins (the state may
  // already have it at the end). `delay` lets enemies move after the heroes.
  // A token's idle bob: its sprite rises and settles, out of step with the others.
  bob(img, y0) {
    return this.scene.tweens.add({ targets: img, y: y0 - 2, duration: 900 + Math.random() * 500, yoyo: true, repeat: -1, delay: Math.random() * 900, ease: 'Sine.easeInOut' });
  }

  // A fight starts here: crossed blades flash and sparks fly, just before the fight opens.
  clash(t) {
    if (!this.scene) return;
    const [cx, cy] = center(t), sc = this.scene;
    const g = sc.add.graphics({ x: cx, y: cy - 8 });
    g.lineStyle(4, 0x0b1017, 0.8); g.lineBetween(-13, -13, 13, 13); g.lineBetween(13, -13, -13, 13);
    g.lineStyle(2.5, 0xffe7c0, 1); g.lineBetween(-13, -13, 13, 13); g.lineBetween(13, -13, -13, 13);
    g.setScale(0.3).setAlpha(0);
    this.layerLand.add(g);
    sc.tweens.add({ targets: g, scale: 1.2, alpha: 1, duration: 160, ease: 'Back.easeOut', onComplete: () => sc.tweens.add({ targets: g, alpha: 0, scale: 1.5, duration: 320, delay: 160, onComplete: () => g.destroy() }) });
    for (let k = 0; k < 10; k++) {
      const a = k / 10 * Math.PI * 2, sp = sc.add.rectangle(cx, cy - 8, 3, 3, k % 2 ? 0xffd36b : 0xff8a5c);
      this.layerLand.add(sp);
      sc.tweens.add({ targets: sp, x: cx + Math.cos(a) * 30, y: cy - 8 + Math.sin(a) * 24, alpha: 0, duration: 420, ease: 'Quad.easeOut', onComplete: () => sp.destroy() });
    }
    const ring = sc.add.circle(cx, cy - 8, 6).setStrokeStyle(2, 0xffd36b, 0.9);
    this.layerLand.add(ring);
    sc.tweens.add({ targets: ring, scale: 4, alpha: 0, duration: 480, onComplete: () => ring.destroy() });
  }

  playMove(id, path, speed = 1, delay = 0) {
    const tok = this.tokens.get(id);
    if (!tok || !path || path.length < 2) return Promise.resolve();
    tok.moving = true;
    const [sx, sy] = center(path[0]);
    tok.c.setPosition(sx, sy);
    const pts = path.slice(1).map(center);
    // a little hop on every hex, instead of the idle bob
    tok.bob?.pause();
    const hop = tok.img ? this.scene.tweens.add({ targets: tok.img, y: 14 - 6, duration: 130 / speed, yoyo: true, repeat: pts.length - 1, delay, ease: 'Quad.easeOut' }) : null;
    return new Promise(res => {
      this.scene.tweens.chain({
        targets: tok.c,
        delay,
        tweens: pts.map(([x, y]) => ({ x, y, duration: 260 / speed, ease: 'Sine.easeInOut' })),
        onComplete: () => { tok.moving = false; tok.tile = -1; hop?.remove(); if (tok.img) tok.img.y = 14; tok.bob?.resume(); res(); this.drawUnits(); },
      });
    });
  }
  stepTime(speed) { return 260 / speed; }

  destroy() { this.game.destroy(true); }
}

const MINI_COL = { deep: '#1d4f6a', shoal: '#bfa877', beach: '#d9c48e', grass: '#5d8c47', forest: '#3e6a34', hills: '#7d8a4e', peak: '#7f7a72', town: '#c9a24a', ice: '#cfe3ee' };

function boatCanvas() {
  const c = document.createElement('canvas'); c.width = 28; c.height = 8;
  const x = c.getContext('2d');
  const rows = ['.kkkkkkkkkkkkkkkkkkkkkkkkk..', 'kwwwwwwwwwwwwwwwwwwwwwwwwwk.', '.kWWWWWWWWWWWWWWWWWWWWWWWk..', '..kWWWWWWWWWWWWWWWWWWWWWk...', '...kkkkkkkkkkkkkkkkkkkkk....'];
  const pal = { k: '#2a1e1a', w: '#a07a4a', W: '#7a5a34' };
  rows.forEach((r, y) => [...r].forEach((ch, X) => { if (pal[ch]) { x.fillStyle = pal[ch]; x.fillRect(X, y + 3, 1, 1); } }));
  return c;
}
