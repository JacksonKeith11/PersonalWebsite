// Sprites and map icons as canvases for Phaser and the DOM. The sprites themselves are generated into
// sprites.js by tools/threefold-art (see docs/game-art.md); flat32() gives them their outline and matte shading.
import { SPRITES } from './sprites.js?v=31';

const K = '#1b1226';
export const ICONS = {
  battle: { pal: { w: '#eef2f7', k: '#3a2a1a', y: '#d9a33a' }, rows: ['.......w', '......ww', '.....ww.', '.k..ww..', '..kww...', '..yk....', '.y..k...', 'y.......'] },
  elite: { pal: { w: '#f1ead8', k: K }, rows: ['..wwww..', '.wwwwww.', '.wkwwkw.', '.wkwwkw.', '.wwwwww.', '..wkkw..', '..wwww..', '..w..w..'] },
  event: { pal: { y: '#ffe680' }, rows: ['..yyyy..', '.yy..yy.', '.....yy.', '....yy..', '...yy...', '...yy...', '........', '...yy...'] },
  shop: { pal: { k: '#6a4a1a', y: '#f2c94c', Y: '#fff0a0' }, rows: ['...kk...', '..kyyk..', '...kk...', '..yyyy..', '.yyYyyy.', '.yYyyyy.', '.yyyyyy.', '..yyyy..'] },
  boss: { pal: { y: '#f2c94c', r: '#e04848' }, rows: ['........', 'y..y..y.', 'yy.y.yy.', 'yyyyyyy.', 'yryyryy.', 'yyyyyyy.', 'yyyyyyy.', '........'] },
};

export const NODE_COLORS = { battle: '#8e3a35', elite: '#6a2f9a', event: '#2f5f99', shop: '#94701c', boss: '#5a1d2a' };

// Map icons are 8×8 letter grids drawn as-is.
export function paint(art) {
  const w = art.rows[0].length, ht = art.rows.length;
  const c = document.createElement('canvas');
  c.width = w; c.height = ht;
  const x = c.getContext('2d');
  art.rows.forEach((row, y) => {
    for (let i = 0; i < w; i++) {
      const col = art.pal[row[i]];
      if (!col) continue;
      x.fillStyle = col;
      x.fillRect(i, y, 1, 1);
    }
  });
  return c;
}

const hexRGB = c => { const n = parseInt(c.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
const DIR4 = [[0, -1], [1, 0], [0, 1], [-1, 0]];
// The finish for a sprite: each colour a flat fill, one darker band where it ends to the lower right, a
// faint lighter edge where it starts upper left, and a near-black outline around the outside tinted by
// what it wraps. 'e' (eyes) and 'o' (dark lines) stay flat. Matte on purpose: no highlights.
function flat32(art) {
  const rows = art.rows, h = rows.length, w = rows[0].length;
  const at = (x, y) => (x < 0 || y < 0 || x >= w || y >= h ? '.' : rows[y][x]);
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const x2 = c.getContext('2d'), img = x2.createImageData(w, h);
  const DARK = [24, 16, 40], LIGHT = [255, 240, 210];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
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

const canvases = {};
export function spriteCanvas(name) { return canvases[name] ||= flat32(SPRITES[name]); }
const urls = {};
export function spriteURL(name) { return urls[name] ||= spriteCanvas(name).toDataURL(); }
export function iconCanvas(name) { return canvases['icon_' + name] ||= paint(ICONS[name]); }

export function buildTextures(scene) {
  const tex = scene.textures;
  for (const name of Object.keys(SPRITES)) if (!tex.exists('s_' + name)) tex.addCanvas('s_' + name, spriteCanvas(name));
  for (const name of Object.keys(ICONS)) if (!tex.exists('i_' + name)) tex.addCanvas('i_' + name, iconCanvas(name));
  if (!tex.exists('px')) {
    const c = document.createElement('canvas'); c.width = c.height = 4;
    const x = c.getContext('2d'); x.fillStyle = '#fff'; x.fillRect(0, 0, 4, 4);
    tex.addCanvas('px', c);
  }
}
