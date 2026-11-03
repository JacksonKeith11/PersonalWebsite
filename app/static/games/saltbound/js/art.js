// Sprites (generated into sprites.js by tools/saltbound-art) and the map's place icons.
// flat32() gives each sprite its outline and matte shading, the same finish as Roguelike Tactics.
import { SPRITES } from './sprites.js?v=103';

const hexRGB = c => { const n = parseInt(c.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
const DIR4 = [[0, -1], [1, 0], [0, 1], [-1, 0]];

function flat32(art) {
  const rows = art.rows, ht = rows.length, w = rows[0].length;
  const at = (x, y) => (x < 0 || y < 0 || x >= w || y >= ht ? '.' : rows[y][x]);
  const c = document.createElement('canvas');
  c.width = w; c.height = ht;
  const x2 = c.getContext('2d'), img = x2.createImageData(w, ht);
  const DARK = [24, 16, 40], LIGHT = [255, 240, 210];
  for (let y = 0; y < ht; y++) for (let x = 0; x < w; x++) {
    const ch = at(x, y);
    let col;
    if (ch === '.') {
      const inside = DIR4.map(([dx, dy]) => at(x + dx, y + dy)).find(n => n !== '.');
      if (!inside) continue;
      col = mix(art.pal[inside] ? hexRGB(art.pal[inside]) : DARK, DARK, 0.86);
    } else {
      col = hexRGB(art.pal[ch] || '#ff00ff');
      if (ch !== 'e' && ch !== 'o') {
        const ne = (dx, dy) => at(x + dx, y + dy) !== ch;
        if (ne(1, 0) || ne(0, 1) || (ne(2, 0) && ne(1, 1))) col = mix(col, DARK, 0.32);
        else if (ne(-1, 0) || ne(0, -1)) col = mix(col, LIGHT, 0.08);
      }
    }
    const i = (y * w + x) * 4;
    img.data[i] = col[0]; img.data[i + 1] = col[1]; img.data[i + 2] = col[2]; img.data[i + 3] = 255;
  }
  x2.putImageData(img, 0, 0);
  return c;
}

const canvases = {}, urls = {};
export function spriteCanvas(name) { return canvases[name] ||= flat32(SPRITES[name] || SPRITES.deckhand); }
export function spriteURL(name) { return urls[name] ||= spriteCanvas(name).toDataURL(); }

// ------------------------------------------------------------------ pose frames
// Every character has one drawn frame; the fights' other poses are made from it on its pixel grid,
// before the outline and shading (so they get the same finish): `attack` leans into the swing,
// `cast` and `hurt` lean back (hurt further, and knocked a pixel back), `fallen` lies on its back.
// Sprites face right, so for enemies (mirrored in battle) the lean still points at the heroes.
export const POSES = ['attack', 'cast', 'hurt', 'fallen'];
function bounds(rows) {
  let top = rows.length, bottom = -1, left = rows[0].length, right = -1;
  rows.forEach((r, y) => { for (let x = 0; x < r.length; x++) if (r[x] !== '.') { top = Math.min(top, y); bottom = Math.max(bottom, y); left = Math.min(left, x); right = Math.max(right, x); } });
  return { top, bottom, left, right };
}
const shiftRow = (r, k) => (k > 0 ? '.'.repeat(k) + r.slice(0, r.length - k) : k < 0 ? r.slice(-k) + '.'.repeat(-k) : r);
// lean: the feet stay put and each row above slides by up to `k` pixels toward the top
function lean(rows, k, nudge = 0) {
  const { top, bottom } = bounds(rows), tall = Math.max(1, bottom - top);
  return rows.map((r, y) => shiftRow(r, Math.round(k * Math.max(0, bottom - y) / tall) + nudge));
}
function lieDown(rows) {
  const n = rows.length, w = rows[0].length, { top, bottom, left, right } = bounds(rows);
  if (right - left > (bottom - top) * 1.1) {
    // a creature wider than it's tall rolls belly-up, settled where its feet were
    const flipped = rows.slice(top, bottom + 1).reverse();
    return rows.map((r, y) => (y >= top && y <= bottom ? flipped[y - top] : '.'.repeat(w)));
  }
  // otherwise a quarter turn anticlockwise (falling backwards: the head ends up behind, to the
  // left), settled onto the floor row the feet stood on
  const out = [];
  for (let y = 0; y < w; y++) { let r = ''; for (let x = 0; x < n; x++) r += rows[x][w - 1 - y] ?? '.'; out.push(r); }
  const b = bounds(out), drop = bottom - b.bottom;
  const blank = '.'.repeat(n);
  const moved = out.map((_, y) => out[y - drop] ?? blank);
  // centred across where the figure stood
  const c = bounds(moved), shift = Math.round((w - 1 - c.right - c.left) / 2);
  return moved.map(r => shiftRow(r, shift));
}
export function poseCanvas(name, pose) {
  const key = name + '@' + pose;
  if (canvases[key]) return canvases[key];
  const art = SPRITES[name] || SPRITES.deckhand;
  const rows = pose === 'attack' ? lean(art.rows, 3, 1) : pose === 'cast' ? lean(art.rows, -2) : pose === 'hurt' ? lean(art.rows, -3, -1) : pose === 'fallen' ? lieDown(art.rows) : art.rows;
  return (canvases[key] = flat32({ pal: art.pal, rows }));
}
export function poseURL(name, pose) {
  if (!pose) return spriteURL(name);
  const key = name + '@' + pose;
  return urls[key] ||= poseCanvas(name, pose).toDataURL();
}
// Decode a fighter's poses ahead of time, so the first swap to one never shows a blank frame.
const warmed = new Set();
export function warmPoses(name) {
  if (warmed.has(name)) return;
  warmed.add(name);
  for (const p of POSES) { const im = new Image(); im.src = poseURL(name, p); }
}
export function placeURL(kind) { return urls['place_' + kind] ||= placeCanvas(kind).toDataURL(); }
export const hasSprite = name => !!SPRITES[name];

// ------------------------------------------------------------------ place icons, 16x16, drawn as-is with an outline
const K = '#1b1226';
export const PLACE_ART = {
  town: { pal: { r: '#a84a3a', R: '#7a3428', w: '#e0d4b8', W: '#b8a888', d: '#4a3020', y: '#ffd870' }, rows: [
    '................', '......rr........', '.....rrrr.......', '....rrrrrr..rr..', '...RRRRRRRRrrrr.', '....wwwwww.RRRR.',
    '....wdwwyw..ww..', '....wdwwww..wy..', '....wwwwww..ww..', '................'] },
  dungeon: { pal: { s: '#8a8a96', S: '#5e5e6a', d: '#1e1a26', y: '#c8a040' }, rows: [
    '.......y........', '.......s........', '......sss.......', '......sSs.......', '..s..sssss..s...', '.sss.sSdSs.sss..',
    '.sSs.ssdss.sSs..', '.sssssssssssss..', '.ssSssdddssSss..', '.sssssdddsssss..', '.SSSSSSSSSSSSS..'] },
  peak: { pal: { y: '#e0bb62', Y: '#a8842e', r: '#e07060' }, rows: [
    '................', '..y...y...y.....', '..yy.yyy.yy.....', '..yyyyyyyyy.....', '..yryyyyryy.....', '..yyyyyyyyy.....', '..YYYYYYYYY.....'] },
  shrine: { pal: { s: '#a8a8b4', S: '#787884', c: '#8fe8ff' }, rows: [
    '................', '...ssssssss.....', '...SSSSSSSS.....', '...ss....ss.....', '...ss.cc.ss.....', '...ss.cc.ss.....', '...ss....ss.....', '..SSSS..SSSS....'] },
  camp: { pal: { t: '#c8b080', T: '#9a8058', r: '#e04820', o: '#ff9a2a', y: '#ffe14d', k: '#5a3a24' }, rows: [
    '................', '....t...........', '...ttt..........', '..ttTtt....r....', '.tttTttt..ror...', 'ttttTtttt.oyo...', '..........kkk...'] },
  event: { pal: { p: '#e8dcc0', P: '#b8a888', k: '#6a5232', q: '#2a2430' }, rows: [
    '................', '..kppppppk......', '...pppqqpp......', '...ppqppqp......', '...pppppqp......', '...ppppqpp......', '...ppppqpp......', '...pppppPp......', '...ppppqpp......', '..kppppppk......'] },
  wreck: { pal: { w: '#7a5a3a', W: '#5a4028', s: '#e0d4b8' }, rows: [
    '................', '........s.......', '........ss......', '........sss.....', '.....w..s.......', 'ww...w..........', '.wwwwwwwwww.....', '..WWWWWWWW.w....'] },
  lair: { pal: { r: '#6a6a72', R: '#4a4a52', d: '#14101a', b: '#d8d0c0' }, rows: [
    '................', '....rrrrrr......', '...rrRRRRrr.....', '..rrRddddRrr....', '..rRddbbddRr....', '..rRdbdbbdRr....', '.rrRddbbddRrr...', '.RRRddddddRRR...'] },
  cache: { pal: { w: '#8a5a2a', W: '#5a3a1a', y: '#e0bb62', k: '#2a1a10' }, rows: [
    '................', '................', '...wwwwwwwww....', '..wWWWWWWWWWw...', '..wwwwwyywwww...', '..yyyyykyyyyy...', '..wwwwwyywwww...', '..WWWWWWWWWWW...'] },
  drift: { pal: { b: '#9a6a3a', B: '#6a4422', r: '#3a3a42', s: '#8fd0ff' }, rows: [
    '................', '.....bbbb.......', '....rrrrrr......', '....bBbbBb......', '....bBbbBb......', '....rrrrrr......', '..ss.bbbb.ss....', '.ssssssssssss...'] },
  healer: { pal: { t: '#e8e0d0', T: '#b8b0a0', r: '#d04a4a' }, rows: [
    '................', '.......t........', '......ttt.......', '.....ttrtt......', '....ttrrrtt.....', '...tttTrtttt....', '..ttttTttttt....', '..TTTTTTTTTT....'] },
  // out at sea: an islet with a palm and a half-buried chest
  cove: { pal: { g: '#4a8a3c', G: '#6aa84a', t: '#7a5a34', s: '#e0cc90', S: '#c4ad78', w: '#8a5a2a', y: '#e0bb62' }, rows: [
    '......gg.gg.....', '.....gGggGg.....', '.......tg.......', '.......t........', '......t..wwy....', '...sssssswwws...', '..sSssssssssSs..', '...SSSSSSSSSS...'] },
  flotsam: { pal: { b: '#9a6a3a', B: '#6a4422', r: '#3a3a42', p: '#8a6a44', s: '#8fd0ff' }, rows: [
    '................', '................', '.....bbb........', '....rrrrr.......', '....bBbBb..ppp..', '....rrrrr.pppp..', '..ss.....ss.ss..', '.ssssssssssssss.'] },
  lookout: { pal: { w: '#8a6a44', W: '#5a4028', r: '#a84a3a', R: '#7a3428', k: '#2a1e1a' }, rows: [
    '......rrr.......', '.....rrrrr......', '....RRRRRRR.....', '.....wkkkw......', '.....wwwww......', '.....w.w.w......', '.....ww.ww......', '....w.w.w.w.....', '....ww...ww.....', '...WWW...WWW....'] },
  grotto: { pal: { r: '#7a7a82', R: '#56565e', d: '#0e0c16', c: '#8fe8ff', g: '#4a7a3c' }, rows: [
    '.....g..g.......', '....rrrrrrr.....', '...rrRRRRRrr....', '..rrRdddddRrr...', '..rRddcdddRrr...', '..rRdddddcdRr...', '.rrRddddddRrrr..', '.RRRddddddRRRR..'] },
};
export function placeCanvas(kind) {
  const key = 'place_' + kind;
  if (canvases[key]) return canvases[key];
  const art = PLACE_ART[kind];
  const rows = art.rows, w = 16, ht = rows.length + 2;
  const c = document.createElement('canvas');
  c.width = w; c.height = ht;
  const x = c.getContext('2d');
  const at = (X, Y) => (Y < 0 || Y >= rows.length || X < 0 || X >= rows[Y].length ? '.' : rows[Y][X]);
  for (let Y = -1; Y <= rows.length; Y++) for (let X = 0; X < w; X++) {
    const ch = at(X, Y);
    if (ch !== '.') { x.fillStyle = art.pal[ch]; x.fillRect(X, Y + 1, 1, 1); continue; }
    if (DIR4.some(([dx, dy]) => at(X + dx, Y + dy) !== '.')) { x.fillStyle = K; x.fillRect(X, Y + 1, 1, 1); }
  }
  return (canvases[key] = c);
}
