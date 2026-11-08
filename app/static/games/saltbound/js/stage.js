// Fight backdrops: a small pixel painting behind the fighters, one per place a fight can happen,
// painted here in code (like the map's terrain) at 400×150 and scaled up with crisp pixels. Each is
// a dusky sky, far shapes, maybe the sea, and a floor the fighters stand on (from FLOOR down).
// Colours stay muted and mid-value (docs/game-art.md): the fighters and the UI must read on top.

const SW = 400, SH = 150, FLOOR = 74;
const urls = {};

const hash = (x, y, s = 0) => { let n = (x * 374761393 + y * 668265263 + s * 2147483647) | 0; n = (n ^ (n >>> 13)) * 1274126177 | 0; return ((n ^ (n >>> 16)) >>> 0) / 4294967296; };
const rgb = c => [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
const BAYER = [0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5].map(v => (v + 0.5) / 16);

function painter() {
  const c = document.createElement('canvas');
  c.width = SW; c.height = SH;
  const ctx = c.getContext('2d');
  const img = ctx.createImageData(SW, SH);
  const set = (x, y, col) => {
    x |= 0; y |= 0;
    if (x < 0 || y < 0 || x >= SW || y >= SH) return;
    const i = (y * SW + x) * 4, [r, g, b] = typeof col === 'string' ? rgb(col) : col;
    img.data[i] = r; img.data[i + 1] = g; img.data[i + 2] = b; img.data[i + 3] = 255;
  };
  const get = (x, y) => { const i = ((y | 0) * SW + (x | 0)) * 4; return [img.data[i], img.data[i + 1], img.data[i + 2]]; };
  // a vertical run of colours from y0 to y1, blended band to band with ordered dithering
  const gradient = (y0, y1, cols, x0 = 0, x1 = SW) => {
    const cs = cols.map(rgb);
    for (let y = y0; y < y1; y++) {
      const t = (y - y0) / Math.max(1, y1 - y0 - 1) * (cs.length - 1);
      const k = Math.min(cs.length - 2, Math.floor(t)), f = t - k;
      for (let x = x0; x < x1; x++) set(x, y, f > BAYER[(y & 3) * 4 + (x & 3)] ? cs[k + 1] : cs[k]);
    }
  };
  const rect = (x, y, w, h, col) => { for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) set(x + i, y + j, col); };
  // a ridge line: hills, islands or cliffs, filled down to `bottom`
  const ridge = (base, amp, col, seed, rough = 0.5, bottom = FLOOR, step = 1) => {
    let h = 0;
    for (let x = 0; x < SW; x++) {
      const n = Math.sin(x * 0.021 + seed) * 0.55 + Math.sin(x * 0.057 + seed * 2.3) * 0.3 + (hash(x >> 2, 1, seed) - 0.5) * rough;
      h = Math.round(n * amp / step) * step;
      for (let y = base - h; y < bottom; y++) set(x, y, col);
    }
  };
  // the floor: bands that get lighter toward the viewer, flecked with texture
  const floor = (cols, fleck, seed, density = 0.06) => {
    gradient(FLOOR, SH, cols);
    for (let y = FLOOR + 2; y < SH; y++) for (let x = 0; x < SW; x++) {
      if (hash(x, y, seed) < density) set(x, y, fleck);
    }
  };
  const done = () => {
    // darken the edges so the middle, where the fighters stand, holds the eye
    for (let y = 0; y < SH; y++) for (let x = 0; x < SW; x++) {
      const dx = (x - SW / 2) / (SW / 2), dy = (y - SH * 0.55) / (SH * 0.8);
      const v = Math.max(0, Math.min(1, (dx * dx * 0.7 + dy * dy) - 0.35));
      if (v > BAYER[(y & 3) * 4 + (x & 3)] * 0.9 + 0.1) { const [r, g, b] = get(x, y); set(x, y, [r * 0.72, g * 0.72, b * 0.78]); }
    }
    ctx.putImageData(img, 0, 0);
    return c.toDataURL();
  };
  return { set, get, gradient, rect, ridge, floor, done };
}

// ------------------------------------------------------------------ props
function palm(p, x, y, s = 1) {
  const trunk = '#3a3026', leaf = '#2e4630';
  for (let i = 0; i < 22 * s; i++) p.set(x + Math.sin(i * 0.12) * 3 * s, y - i, trunk), p.set(x + 1 + Math.sin(i * 0.12) * 3 * s, y - i, trunk);
  const tx = x + Math.sin(22 * s * 0.12) * 3 * s, ty = y - 22 * s;
  for (const [dx, dy] of [[1, 0.25], [-1, 0.25], [0.8, -0.35], [-0.8, -0.35], [0.4, 0.6], [-0.4, 0.6]]) {
    for (let i = 0; i < 12 * s; i++) { const xx = tx + dx * i, yy = ty + dy * i + (i * i) / (28 * s); p.set(xx, yy, leaf); p.set(xx, yy + 1, leaf); }
  }
}
function waves(p, y0, y1, hi, seed) {
  for (let y = y0; y < y1; y++) for (let x = 0; x < SW; x++) {
    if ((x + Math.floor(y * 3.7) + Math.floor(hash(y, 3, seed) * 40)) % 23 < 3 && hash(x >> 3, y, seed) > 0.4) p.set(x, y, hi);
  }
}
function arch(p, cx, top, w, h, col, inner) {
  for (let y = top; y < top + h; y++) for (let x = cx - w / 2; x < cx + w / 2; x++) {
    const dx = (x - cx) / (w / 2), dy = (y - top) / (w / 2);
    const inArch = y > top + w / 2 ? Math.abs(dx) < 0.62 : dx * dx + (1 - dy) * (1 - dy) < 0.62 * 0.62 * 1.0;
    p.set(x, y, inArch ? inner : col);
  }
}
function pillar(p, x, top, w, col, dark, broken = 0) {
  for (let y = top + broken; y < FLOOR + 6; y++) for (let i = 0; i < w; i++) p.set(x + i, y, i < 2 ? dark : i >= w - 2 ? dark : col);
  if (broken) for (let i = 0; i < w; i++) if (hash(i, x) > 0.4) p.set(x + i, top + broken - 1 - Math.floor(hash(i, x, 2) * 3), col);
}
function lantern(p, x, y) {
  p.rect(x - 1, y - 6, 3, 6, '#2a2018');
  p.rect(x - 2, y, 5, 6, '#e0a040'); p.rect(x - 1, y + 1, 3, 4, '#ffd27a');
  for (let r = 3; r < 12; r++) for (let a = 0; a < 40; a++) {
    const xx = x + Math.cos(a / 40 * 6.283) * r, yy = y + 3 + Math.sin(a / 40 * 6.283) * r;
    if (hash(xx | 0, yy | 0, r) < 0.18 - r * 0.012) { const [cr, cg, cb] = p.get(xx | 0, yy | 0); p.set(xx, yy, [Math.min(255, cr + 28), Math.min(255, cg + 20), cb + 4]); }
  }
}

function spike(p, x, base, h, w, col, lit, dark) {
  // a crystal: a tall faceted point, lit on its left face (a negative height hangs down from `base`)
  const down = h < 0;
  h = Math.abs(h);
  for (let y = 0; y < h; y++) {
    const half = Math.max(0, (w / 2) * (1 - (h - y) / h * 0.15) * Math.min(1, (y + 2) / (h * 0.35)));
    const yy = down ? base + (h - 1 - y) : base - h + y;
    for (let i = -half; i <= half; i++) p.set(x + i, yy, i < -half * 0.2 ? lit : i > half * 0.45 ? dark : col);
  }
}
function deadTree(p, x, y, s, col) {
  for (let i = 0; i < 26 * s; i++) { p.set(x, y - i, col); p.set(x + 1, y - i, col); }
  for (const [dx, dy, len] of [[1, -0.6, 10], [-1, -0.5, 9], [1, -1.2, 7], [-1, -1.4, 6]]) {
    const oy = y - 26 * s * (0.45 + Math.abs(dy) * 0.25);
    for (let i = 0; i < len * s; i++) p.set(x + dx * i, oy + dy * i * 0.6, col);
  }
}
function pineTree(p, x, y, s, col, snow) {
  for (let k = 0; k < 4; k++) {
    const top = y - 30 * s + k * 7 * s, w = (5 + k * 3) * s;
    for (let j = 0; j < 9 * s; j++) for (let i = -w * j / (9 * s); i <= w * j / (9 * s); i++) p.set(x + i, top + j, j < 2 && snow ? snow : col);
  }
  p.rect(x - 1, y - 6 * s, 3, 6 * s, '#3a2a20');
}
function puff(p, cx, cy, rx, ry, col, seed) {
  for (let y = -ry; y <= ry; y++) for (let x = -rx; x <= rx; x++) {
    if (x * x / (rx * rx) + y * y / (ry * ry) < 1 && hash(x >> 1, y >> 1, seed) > 0.08) p.set(cx + x, cy + y, col);
  }
}
function disc(p, cx, cy, r, col, edge) {
  for (let y = -r; y <= r; y++) for (let x = -r; x <= r; x++) { const d = Math.hypot(x, y); if (d < r) p.set(cx + x, cy + y, edge && d > r - 2 ? edge : col); }
}

// ------------------------------------------------------------------ the scenes
const SCENES = {
  // the Coral Shallows in the open: a pale reef beach under a teal dusk
  coral(p) {
    p.gradient(0, 50, ['#24404e', '#2f5a66', '#4a7a7c', '#7a9a88']);
    p.ridge(48, 6, '#3d6670', 2.0, 0.4, 56);
    p.gradient(48, FLOOR, ['#2c5a68', '#2a6474', '#3a7a84']);
    waves(p, 50, FLOOR, '#5d9aa0', 1);
    palm(p, 40, FLOOR + 4, 1.2); palm(p, 362, FLOOR + 6, 1.4); palm(p, 330, FLOOR + 2, 0.9);
    p.floor(['#8a7a5a', '#9a8862', '#a8946a', '#b09c70'], '#c4b084', 7, 0.05);
    for (let i = 0; i < 18; i++) { const x = hash(i, 9) * SW, y = FLOOR + 6 + hash(i, 10) * 60; p.rect(x, y, 2 + hash(i, 11) * 3, 2, hash(i, 12) > 0.5 ? '#b4685a' : '#8a5a78'); }
  },
  // the Smugglers' Keys: a dusk sky over the water, a fort on the far key, a plank dock underfoot
  keys(p) {
    p.gradient(0, 54, ['#2a2236', '#4a3048', '#7a4a4c', '#a8684e']);
    p.ridge(52, 5, '#3a2a36', 4.1, 0.5, 58);
    // the fort: walls, towers, a flag
    p.rect(250, 34, 60, 22, '#2e2430'); p.rect(246, 26, 12, 30, '#2e2430'); p.rect(300, 24, 12, 32, '#2e2430');
    for (let x = 250; x < 310; x += 6) p.rect(x, 31, 3, 3, '#2e2430');
    p.rect(305, 12, 1, 12, '#2a2026'); p.rect(306, 12, 7, 4, '#8a3a34');
    p.gradient(52, FLOOR, ['#3a3448', '#4a4054', '#5a4c5c']);
    waves(p, 54, FLOOR, '#8a6a6a', 2);
    p.floor(['#4a3828', '#56422e', '#604a32', '#6a5236'], '#3a2c20', 3, 0.0);
    for (let y = FLOOR; y < SH; y += 7) for (let x = 0; x < SW; x++) p.set(x, y, '#3a2c20');
    for (let y = FLOOR; y < SH; y++) for (let x = (Math.floor((y - FLOOR) / 7) % 2) * 23; x < SW; x += 46) p.set(x, y, '#3a2c20');
    for (const x of [20, 380]) { p.rect(x, FLOOR - 26, 5, 40, '#3a2c20'); lantern(p, x + 2, FLOOR - 30); }
  },
  // Stormcrag: slate sky, a far bolt, jagged cliffs, a rocky shelf
  storm(p) {
    p.gradient(0, FLOOR, ['#1e2430', '#2a3240', '#3a4452', '#4a5462']);
    let x = 300, y = 4;
    while (y < 40) { p.set(x, y, '#c8d8ec'); p.set(x + 1, y, '#8aa0bc'); y++; if (hash(y, 4) > 0.6) x += hash(y, 5) > 0.5 ? 1 : -1; }
    p.ridge(46, 16, '#2a303a', 7.3, 0.35, FLOOR, 2);
    p.ridge(60, 8, '#343a44', 3.7, 0.3, FLOOR, 1);
    p.floor(['#4a4c50', '#56585a', '#5e6062', '#666868'], '#3e4044', 11, 0.08);
    for (let i = 0; i < 14; i++) { const rx = hash(i, 20) * SW, ry = FLOOR + 10 + hash(i, 21) * 55; p.rect(rx, ry, 4 + hash(i, 22) * 6, 2 + hash(i, 23) * 3, '#3e4044'); p.rect(rx, ry, 3 + hash(i, 22) * 4, 1, '#76787a'); }
  },
  // out at sea (sea beasts): a grey-green swell to the horizon, the party's skiffs rocking underfoot
  sea(p) {
    p.gradient(0, 46, ['#1e2a36', '#2a3c48', '#3e5660', '#5a7676']);
    for (let i = 0; i < 6; i++) { const cx = 40 + hash(i, 40) * 320, cy = 10 + hash(i, 41) * 22; for (let x = -26; x < 26; x++) for (let y = -4; y < 4; y++) if (x * x / 676 + y * y / 16 < 1 && hash(x, y, i) > 0.2) p.set(cx + x, cy + y, '#4a5e68'); }
    p.gradient(46, SH, ['#24485a', '#2a5466', '#2e6070', '#346a78', '#3a7280']);
    waves(p, 48, SH, '#6aa0aa', 5);
    for (let y = FLOOR + 6; y < SH; y += 9) for (let x = 0; x < SW; x++) if (Math.sin(x * 0.06 + y) > 0.85) p.set(x, y, '#9ccad0');
    // skiff hulls along the floor
    for (const [x0, w] of [[60, 70], [170, 64], [276, 74]]) {
      for (let x = 0; x < w; x++) { const d = Math.abs(x - w / 2) / (w / 2), top = FLOOR + 16 + Math.round(d * d * 6); for (let y = top; y < FLOOR + 26 - Math.round(d * 3); y++) p.set(x0 + x, y, y === top ? '#a07a4a' : y < top + 3 ? '#7a5a34' : '#5a4024'); }
    }
  },
  // Cinderreach: a red sky, the volcano smoking far off, ash underfoot with cracks of lava
  ash(p) {
    p.gradient(0, FLOOR, ['#2a1616', '#4a2020', '#6a2e22', '#8a4a2e']);
    // the volcano, a glow at its mouth and a column of smoke
    for (let y = 18; y < FLOOR; y++) { const half = (y - 18) * 1.9 + 8; for (let x = -half; x <= half; x++) p.set(260 + x, y, hash(x >> 2, y >> 2, 51) > 0.85 ? '#3a2422' : '#2e1c1c'); }
    p.rect(252, 16, 17, 4, '#e8782a'); p.rect(256, 14, 9, 2, '#ffd23f');
    for (let i = 0; i < 9; i++) puff(p, 262 + Math.sin(i) * 8 + i * 3, 10 - i * 2, 12 + i * 2, 6, '#3a2a2a', 50 + i);
    for (const [x0, x1] of [[248, 226], [270, 300]]) for (let y = 20; y < FLOOR; y++) p.set(x0 + (x1 - x0) * (y - 20) / (FLOOR - 20) + Math.sin(y * 0.3) * 2, y, y % 3 ? '#c84a1a' : '#e8782a');
    p.ridge(58, 6, '#2a1c1c', 3.1, 0.4, FLOOR);
    p.floor(['#3e3434', '#4a3e3c', '#544644', '#5c4e4a'], '#2a2222', 41, 0.06);
    for (let i = 0; i < 6; i++) { let x = hash(i, 42) * SW, y = FLOOR + 8 + hash(i, 43) * 56; for (let k = 0; k < 30; k++) { p.set(x, y, k % 4 ? '#c84a1a' : '#ffa03a'); x += 1; y += hash(k, i, 44) > 0.5 ? 1 : -1; } }
    for (let i = 0; i < 40; i++) p.set(hash(i, 45) * SW, hash(i, 46) * FLOOR, '#ffa03a');
  },
  // the Shifting Sands: a white-hot sky, rolling dunes, a far pyramid
  dunes(p) {
    p.gradient(0, FLOOR, ['#a8c4d0', '#c8d0c0', '#e0d0a8', '#e8c890']);
    disc(p, 80, 22, 11, '#fff4d0', '#f0e0a8');
    for (let y = 30; y < 58; y++) { const half = (y - 30) * 1.1; for (let x = -half; x <= half; x++) p.set(300 + x, y, x > 0 ? '#b08a5a' : '#c8a070'); }
    p.ridge(56, 8, '#d0aa70', 1.7, 0.2, FLOOR);
    p.ridge(64, 6, '#c49a60', 4.3, 0.2, FLOOR);
    p.floor(['#d8b47a', '#dcbc84', '#e0c48e', '#e4ca96'], '#c4a06a', 47, 0.05);
    for (let y = FLOOR + 6; y < SH; y += 7) for (let x = 0; x < SW; x++) if (Math.sin(x * 0.05 + y * 0.7) > 0.92) p.set(x, y, '#c49a60');
    for (const x of [40, 352]) { p.rect(x, FLOOR - 22, 4, 26, '#5a7a40'); p.rect(x - 6, FLOOR - 14, 6, 3, '#5a7a40'); p.rect(x - 6, FLOOR - 20, 3, 8, '#5a7a40'); p.rect(x + 4, FLOOR - 10, 6, 3, '#5a7a40'); p.rect(x + 7, FLOOR - 16, 3, 7, '#5a7a40'); }
  },
  // the Stillwood: a pale still sky, grey stone trees, moss underfoot
  petrified(p) {
    p.gradient(0, FLOOR, ['#4a4e52', '#5e6266', '#74787a', '#868a88']);
    for (let i = 0; i < 10; i++) deadTree(p, 20 + i * 40 + hash(i, 61) * 20, FLOOR + 2, 1.6 + hash(i, 62) * 0.9, i % 2 ? '#6a6862' : '#5a5852');
    for (let i = 0; i < 5; i++) deadTree(p, 40 + i * 80 + hash(i, 63) * 30, FLOOR + 10, 2.4, '#8a867e');
    p.floor(['#5e6458', '#666c60', '#6e7468', '#767c6e'], '#8a9a6a', 61, 0.05);
    for (let i = 0; i < 16; i++) { const x = hash(i, 64) * SW, y = FLOOR + 6 + hash(i, 65) * 60; p.rect(x, y, 3 + hash(i, 66) * 5, 2, '#8a867c'); }
  },
  // the Verdant Deep: green gloom under the canopy, vines, ferns
  jungle(p) {
    p.gradient(0, FLOOR, ['#1a2a1a', '#1e3a22', '#24482a', '#2e5a32']);
    for (let i = 0; i < 14; i++) puff(p, hash(i, 71) * SW, hash(i, 72) * 30, 30 + hash(i, 73) * 20, 14, i % 2 ? '#2a4a26' : '#22401e', 70 + i);
    for (let i = 0; i < 9; i++) { const x = 10 + i * 46 + hash(i, 74) * 10; p.rect(x, 0, 6, FLOOR + 4, '#3a2e1e'); p.rect(x + 1, 0, 2, FLOOR + 4, '#4a3a26'); }
    for (let i = 0; i < 18; i++) { const x = hash(i, 75) * SW; for (let y = 0; y < 20 + hash(i, 76) * 40; y++) p.set(x + Math.sin(y * 0.2 + i) * 3, y, '#3e7a34'); }
    p.floor(['#2e4a24', '#36562a', '#3e602e', '#466a34'], '#5a8a40', 71, 0.07);
    for (let i = 0; i < 14; i++) puff(p, hash(i, 77) * SW, FLOOR + 4 + hash(i, 78) * 8, 14, 6, '#2e5a2a', 77 + i);
  },
  // Aetherhold: golden light, clouds below, marble columns
  heaven(p) {
    p.gradient(0, FLOOR, ['#e8d8a8', '#f0e4c0', '#f4ecd8', '#e8e4ec']);
    for (let i = 0; i < 12; i++) { const x = hash(i, 81) * SW; for (let y = 0; y < FLOOR; y++) if (hash(x | 0, y, 82) > 0.6) { const [r, g, b] = p.get(x, y); p.set(x, y, [Math.min(255, r + 10), Math.min(255, g + 8), b]); } }
    for (let i = 0; i < 9; i++) puff(p, 20 + i * 48, FLOOR - 6 + hash(i, 83) * 6, 34, 12, '#f8f4fa', 80 + i);
    for (const x of [30, 110, 290, 370]) { p.rect(x - 7, 14, 14, 3, '#d8c070'); p.rect(x - 5, 17, 10, FLOOR - 13, '#eceae0'); p.rect(x + 2, 17, 3, FLOOR - 13, '#c8c4b8'); p.rect(x - 7, FLOOR + 2, 14, 3, '#d8c070'); }
    p.floor(['#948f84', '#9c978c', '#a49f94', '#aaa59a'], '#86817a', 81, 0.0);
    for (let y = FLOOR; y < SH; y += 10) for (let x = 0; x < SW; x++) p.set(x, y, '#a8a498');
    for (let y = FLOOR; y < SH; y++) for (let x = (Math.floor((y - FLOOR) / 10) % 2) * 25; x < SW; x += 50) p.set(x, y, '#a8a498');
  },
  // the Prism Wood: violet dusk, a forest of crystals catching the light
  crystal(p) {
    p.gradient(0, FLOOR, ['#1e1a36', '#2e2850', '#40386a', '#544a80']);
    for (let i = 0; i < 30; i++) p.set(hash(i, 91) * SW, hash(i, 92) * 40, '#e8e0ff');
    for (let i = 0; i < 12; i++) spike(p, 10 + i * 34 + hash(i, 93) * 14, FLOOR + 2, 30 + hash(i, 94) * 30, 10 + hash(i, 95) * 8, '#6a5aa8', '#a898d8', '#4a3a80');
    for (let i = 0; i < 6; i++) spike(p, 30 + i * 70 + hash(i, 96) * 20, FLOOR + 6, 44 + hash(i, 97) * 20, 16, '#8a7ac8', '#d8d0f8', '#5a4a98');
    p.floor(['#4a4470', '#524c7a', '#5a5484', '#625c8c'], '#a898d8', 91, 0.05);
    for (let i = 0; i < 10; i++) spike(p, hash(i, 98) * SW, FLOOR + 14 + hash(i, 99) * 50, 6 + hash(i, 90) * 6, 4, '#8a7ac8', '#d8d0f8', '#5a4a98');
  },
  // the Drowsing Vale: a lilac night, a huge moon, soft hills of lavender
  dream(p) {
    p.gradient(0, FLOOR, ['#1e1a3a', '#2e2a54', '#4a3a6e', '#6a5a8a']);
    disc(p, 300, 30, 20, '#ece4c8', '#d8d0b0'); disc(p, 308, 26, 16, '#3a3260');
    for (let i = 0; i < 40; i++) p.set(hash(i, 101) * SW, hash(i, 102) * 50, hash(i, 103) > 0.7 ? '#e8d070' : '#d8d0f0');
    p.ridge(56, 9, '#5a4a7a', 2.3, 0.15, FLOOR);
    for (let i = 0; i < 7; i++) puff(p, 30 + i * 60, 50 + hash(i, 104) * 8, 22, 9, '#8a7ab0', 100 + i);
    p.floor(['#6a5a90', '#725e98', '#7a66a0', '#826ea8'], '#a88ad8', 101, 0.08);
    for (let i = 0; i < 20; i++) { const x = hash(i, 105) * SW, y = FLOOR + 6 + hash(i, 106) * 60; p.set(x, y, '#c8a8f0'); p.set(x, y - 1, '#c8a8f0'); }
  },
  // the Frostpeaks: a pale sky, snowy pines and peaks, snow underfoot
  frost(p) {
    p.gradient(0, FLOOR, ['#6a8aa8', '#8aa4bc', '#aac0d0', '#c8d8e4']);
    p.ridge(40, 16, '#b8c8d8', 6.1, 0.3, FLOOR, 2);
    for (let x = 0; x < SW; x++) for (let y = 20; y < 46; y++) { const [r, g, b] = p.get(x, y); if (r === 0xb8) p.set(x, y, y < 34 ? '#f0f6fa' : '#b8c8d8'); }
    for (let i = 0; i < 11; i++) pineTree(p, 14 + i * 38 + hash(i, 111) * 12, FLOOR + 4, 1 + hash(i, 112) * 0.5, '#3a5a5a', '#f0f6fa');
    p.floor(['#8ea2b2', '#96aab8', '#9eb2c0', '#a6b8c6'], '#c8d8e4', 111, 0.05);
    for (let i = 0; i < 60; i++) p.set(hash(i, 113) * SW, hash(i, 114) * SH, '#ffffff');
  },
  // the dungeons: the Caldera Forge (anvils, a glowing forge mouth, chains)
  forge(p) {
    p.gradient(0, FLOOR, ['#1e1414', '#2a1a18', '#34201c']);
    for (let x = 20; x < SW; x += 80) { p.rect(x, 0, 12, FLOOR, '#2a2020'); p.rect(x + 2, 0, 3, FLOOR, '#3a2c28'); }
    arch(p, 90, 16, 60, 58, '#3a2a26', '#a84a1a');
    for (let y = 40; y < FLOOR; y++) for (let x = 66; x < 114; x++) { const [r] = p.get(x, y); if (r === 0xa8) p.set(x, y, hash(x >> 1, y >> 1, 121) > 0.8 ? '#e8782a' : '#a84a1a'); }
    for (const x of [60, 320]) { for (let y = 0; y < 40; y += 4) p.rect(x, y, 3, 3, '#5a5a66'); }
    p.floor(['#3a3030', '#443838', '#4c3e3c', '#544644'], '#c84a1a', 121, 0.01);
  },
  // the Buried Tomb: sandstone walls, hieroglyph bands, torchlight
  tomb(p) {
    p.gradient(0, FLOOR, ['#3a2a1a', '#4a3620', '#5a4228']);
    for (let y = 10; y < FLOOR; y += 14) for (let x = 0; x < SW; x += 6) if (hash(x >> 3, y, 131) > 0.4) p.rect(x, y, 3, 5, '#7a5a34');
    for (const x of [30, 120, 280, 370]) { p.rect(x - 8, 0, 16, FLOOR, '#6a5032'); p.rect(x - 6, 0, 3, FLOOR, '#7a603e'); lantern(p, x, 30); }
    p.floor(['#6a5232', '#745a38', '#7c623e', '#846a44'], '#5a4228', 131, 0.0);
    for (let y = FLOOR; y < SH; y += 8) for (let x = 0; x < SW; x++) p.set(x, y, '#5a4228');
  },
  // the Heartwood Vault: inside a giant stone tree, root-arches, moss light
  heartwood(p) {
    p.gradient(0, FLOOR, ['#1e2220', '#262c28', '#2e3630']);
    for (const cx of [70, 200, 330]) arch(p, cx, 6, 90, 70, '#4a4a44', '#1a1e1c');
    for (let i = 0; i < 26; i++) { const x = hash(i, 141) * SW; for (let y = 0; y < 30; y++) p.set(x + Math.sin(y * 0.3 + i) * 2, y, '#5a6a44'); }
    p.floor(['#3a3e36', '#42463c', '#4a4e42', '#525648'], '#7a8a5a', 141, 0.05);
  },
  // the Strangled Ziggurat: a stone stair under roots, green light from above
  ziggurat(p) {
    p.gradient(0, FLOOR, ['#141e14', '#1c2a1c', '#223422']);
    for (let k = 0; k < 6; k++) p.rect(60 + k * 22, 10 + k * 9, SW - 120 - k * 44, 9, k % 2 ? '#4a4a3a' : '#54543e');
    for (let i = 0; i < 20; i++) { let x = hash(i, 151) * SW; for (let y = 0; y < FLOOR; y++) { p.set(x, y, '#3a6a2e'); x += Math.sin(y * 0.15 + i) * 0.8; } }
    for (const sx of [140, 260]) for (let y = 0; y < FLOOR; y++) for (let x = -8; x <= 8; x++) if ((1 - Math.abs(x) / 8) * 0.4 > BAYER[(y & 3) * 4 + ((sx + x) & 3)]) { const [r, g, b] = p.get(sx + x, y); p.set(sx + x, y, [r + 10, g + 26, b + 8]); }
    p.floor(['#3a3a2c', '#424232', '#4a4a38', '#52523e'], '#3e7a34', 151, 0.06);
  },
  // the Celestial Spire: a hall of light, white pillars to a golden ceiling
  spire(p) {
    p.gradient(0, FLOOR, ['#c8a860', '#e0c890', '#ece0c0']);
    for (const x of [40, 120, 200, 280, 360]) { p.rect(x - 8, 0, 16, FLOOR, '#eceae0'); p.rect(x + 3, 0, 4, FLOOR, '#c8c4b8'); }
    for (let y = 0; y < FLOOR; y++) for (let x = 180; x < 220; x++) { const w = 1 - Math.abs(x - 200) / 20; if (w * 0.5 > BAYER[(y & 3) * 4 + (x & 3)]) p.set(x, y, '#fff8e0'); }
    p.floor(['#8e8a80', '#969288', '#9e9a90', '#a6a298'], '#8a7a4a', 161, 0.0);
    for (let y = FLOOR; y < SH; y += 12) for (let x = 0; x < SW; x++) p.set(x, y, '#8a7a4a');
  },
  // the Heart Geode: inside a geode, walls of amethyst points
  geode(p) {
    p.gradient(0, FLOOR, ['#1a1430', '#241c40', '#2e2450']);
    for (let i = 0; i < 26; i++) spike(p, hash(i, 171) * SW, 4 + hash(i, 172) * 20, -(10 + hash(i, 173) * 12), 6, '#7a5ab8', '#b898e8', '#5a3a98');
    for (let i = 0; i < 18; i++) spike(p, i * 24 + hash(i, 174) * 10, FLOOR + 2, 16 + hash(i, 175) * 22, 8, '#7a5ab8', '#b898e8', '#5a3a98');
    p.floor(['#3a2e5a', '#423462', '#4a3a6a', '#524072'], '#b898e8', 171, 0.04);
  },
  // the Sleeping Palace: velvet curtains, a starry ceiling, a moonlit floor
  palace(p) {
    p.gradient(0, FLOOR, ['#140e26', '#1e1636', '#281e46']);
    for (let i = 0; i < 50; i++) p.set(hash(i, 181) * SW, hash(i, 182) * 30, '#e8d070');
    for (const x of [0, 340]) for (let y = 0; y < FLOOR + 10; y++) for (let k = 0; k < 60; k++) p.set(x + k, y, Math.sin((x + k) * 0.4) > 0.3 ? '#5a2a5a' : '#4a2250');
    for (const cx of [140, 260]) arch(p, cx, 14, 60, 60, '#3a3058', '#1a1430');
    p.floor(['#2a2448', '#322a52', '#3a305a', '#423662'], '#8a7ab0', 181, 0.03);
    for (let y = FLOOR; y < SH; y++) for (let x = 0; x < SW; x++) if (((x >> 4) + (y >> 3)) % 2 === 0) { const [r, g, b] = p.get(x, y); p.set(x, y, [r + 8, g + 8, b + 12]); }
  },
  // the Glacier Throne: blue ice walls, icicles, a frozen floor
  glacier(p) {
    p.gradient(0, FLOOR, ['#1e3448', '#2a4a62', '#3a5e78']);
    for (let i = 0; i < 40; i++) { const x = hash(i, 191) * SW, len = 6 + hash(i, 192) * 18; for (let y = 0; y < len; y++) for (let k = -1; k <= 1; k++) if (Math.abs(k) <= (1 - y / len) * 2) p.set(x + k, y, '#bfe0f4'); }
    for (let i = 0; i < 9; i++) spike(p, 20 + i * 45, FLOOR + 2, 22 + hash(i, 193) * 16, 12, '#7aa8c8', '#cfe6f4', '#4a7a98');
    p.floor(['#5e7e94', '#66869c', '#6e8ea4', '#7696aa'], '#a8c8dc', 191, 0.05);
  },
  // the open peak (fights on the way to the Crown)
  peak(p) {
    p.gradient(0, FLOOR, ['#20202c', '#2c2a38', '#3c3644', '#4c4450']);
    p.ridge(50, 12, '#2a2832', 5.5, 0.3, FLOOR, 2);
    p.ridge(62, 6, '#33303a', 2.1, 0.25, FLOOR, 1);
    p.floor(['#3e3c42', '#48464c', '#504e54', '#58565c'], '#36343a', 13, 0.07);
  },
  // the Drowned Crown: a red moon over the rising sea, broken pillars on the last dry stone
  crown(p) {
    p.gradient(0, 54, ['#140e1c', '#2a1424', '#4a1e2c', '#6a2c34']);
    for (let y = 0; y < 30; y++) for (let x = 0; x < 30; x++) { const d = Math.hypot(x - 15, y - 15); if (d < 13) p.set(186 + x, 8 + y, d < 11 ? (hash(x, y, 30) > 0.85 ? '#a85a50' : '#c4706a') : '#8a4a48'); }
    p.gradient(54, FLOOR, ['#2a2030', '#342838', '#3e3040']);
    waves(p, 56, FLOOR, '#6a4450', 3);
    pillar(p, 40, 18, 10, '#4a4250', '#3a3240', 6); pillar(p, 92, 30, 8, '#4a4250', '#3a3240', 14);
    pillar(p, 300, 26, 8, '#4a4250', '#3a3240', 9); pillar(p, 350, 14, 10, '#4a4250', '#3a3240', 0);
    p.floor(['#2e2a34', '#38323e', '#403a46', '#48424e'], '#5a3a44', 17, 0.03);
  },
  // the Sunken Chapel: stone arches, sea-green light through water
  chapel(p) {
    p.gradient(0, FLOOR, ['#16262c', '#1e3238', '#243c42']);
    for (const cx of [60, 160, 240, 340]) arch(p, cx, 10, 56, 64, '#2c3e44', '#1a2c30');
    for (const sx of [110, 200, 290]) for (let y = 0; y < FLOOR; y++) for (let x = -10; x <= 10; x++) {
      const xx = sx + x + y * 0.35, w = 1 - Math.abs(x) / 10;
      if (w * 0.45 > BAYER[(y & 3) * 4 + ((xx | 0) & 3)]) { const [r, g, b] = p.get(xx, y); p.set(xx, y, [r + 10, g + 22, b + 20]); }
    }
    p.floor(['#2a3a3c', '#324446', '#3a4c4e', '#425456'], '#2a5a58', 19, 0.05);
    for (let x = 0; x < SW; x++) if (hash(x >> 3, 0, 32) > 0.5) p.set(x, FLOOR + 1, '#4a7a74');
  },
  // the Black Fort: timber beams, lantern light, a plank floor
  fort(p) {
    p.gradient(0, FLOOR, ['#1c1614', '#261e1a', '#30261e']);
    for (let x = 30; x < SW; x += 90) p.rect(x, 0, 10, FLOOR, '#3a2c20');
    p.rect(0, 12, SW, 7, '#3a2c20');
    for (const x of [75, 165, 255, 345]) lantern(p, x, 26);
    for (let i = 0; i < 6; i++) p.rect(110 + i * 7, FLOOR - 16 + (i % 2) * 3, 6, 16 - (i % 2) * 3, '#4a3424');
    p.floor(['#3e2e22', '#4a3628', '#543e2c', '#5c4430'], '#2e2218', 23, 0.0);
    for (let y = FLOOR; y < SH; y += 6) for (let x = 0; x < SW; x++) p.set(x, y, '#2e2218');
  },
  // the Lighthouse: round stone walls, a window with the beam sweeping past
  lighthouse(p) {
    p.gradient(0, FLOOR, ['#1a1e26', '#22282f', '#2a3038']);
    for (let y = 0; y < FLOOR; y += 6) for (let x = ((y / 6) % 2) * 9; x < SW; x += 18) p.set(x, y, '#1a1e24'), p.rect(x, y, 1, 6, '#1a1e24');
    for (let y = 0; y < FLOOR; y += 6) for (let x = 0; x < SW; x++) p.set(x, y, '#1a1e24');
    for (let y = 0; y < 36; y++) for (let x = 0; x < 36; x++) { const d = Math.hypot(x - 18, y - 18); if (d < 17) p.set(182 + x, 18 + y, d < 14 ? '#2a3a4e' : '#3a3a40'); }
    for (let y = 36; y < FLOOR + 40; y++) {
      const half = 6 + (y - 36) * 0.9;
      for (let x = -half; x <= half; x++) {
        const xx = 200 + x, w = (1 - Math.abs(x) / half) * (1 - (y - 36) / 90);
        if (w * 0.5 > BAYER[(y & 3) * 4 + ((xx | 0) & 3)]) { const [r, g, b] = p.get(xx, y); p.set(xx, y, [Math.min(255, r + 26), Math.min(255, g + 24), Math.min(255, b + 12)]); }
      }
    }
    p.floor(['#3a3c40', '#44464a', '#4c4e52', '#545658'], '#34363a', 29, 0.06);
  },
};

// Which backdrop a fight gets: the Crown's own, a dungeon's interior, or the open ground of the
// region it's fought in (the peak when the tile belongs to none).
export function stageKey(f, world) {
  if (f.kind === 'boss') return 'crown';
  if (world?.elev && world.elev[f.tile] <= 1) return 'sea';  // out on the water
  const reg = f.region || world?.reg?.[f.tile] || null;
  if (f.kind === 'dungeon') return { coral: 'chapel', keys: 'fort', storm: 'lighthouse', ash: 'forge', dunes: 'tomb', petrified: 'heartwood',
    jungle: 'ziggurat', heaven: 'spire', crystal: 'geode', dream: 'palace', frost: 'glacier' }[reg] || 'chapel';
  return SCENES[reg] ? reg : 'peak';
}

// `ground` (a fight's battleground, Game.ground_of) is painted on top: high ground raises a rocky
// slope under the side holding it (the party stands on the left, the enemies on the right); ambush
// ground hangs dark trees over both edges of the scene.
export function stageURL(key, ground = null) {
  const id = key + (ground ? `|${ground.k}-${ground.side}` : '');
  if (!urls[id]) {
    const p = painter();
    (SCENES[key] || SCENES.peak)(p);
    if (ground?.k === 'high') slope(p, ground.side === 'heroes' ? 'left' : 'right');
    if (ground?.k === 'woods') woods(p);
    urls[id] = p.done();
  }
  return urls[id];
}

function slope(p, side) {
  const x0 = side === 'left' ? 0 : SW / 2 - 10, x1 = side === 'left' ? SW / 2 + 10 : SW;
  for (let x = x0; x < x1; x++) {
    const u = (x - x0) / (x1 - x0), along = side === 'left' ? u : 1 - u;  // 0 at the outer edge
    const rise = Math.round(26 * Math.cos(Math.min(1, along * 1.05) * Math.PI / 2) + Math.sin(x * 0.11) * 2 + (hash(x >> 2, 77) - 0.5) * 3);
    if (rise <= 1) continue;
    const top = FLOOR + 34 - rise;
    for (let y = top; y < SH; y++) {
      const [r, g, b] = p.get(x, Math.min(SH - 1, y + rise));  // the floor, lifted
      const lit = y < top + 2, shade = y > top + 6 && hash(x, y, 78) < 0.08;
      p.set(x, y, lit ? [Math.min(255, r * 1.32 + 10), Math.min(255, g * 1.3 + 10), Math.min(255, b * 1.25 + 8)] : shade ? [r * 0.7, g * 0.7, b * 0.72] : [r * 0.92, g * 0.9, b * 0.9]);
    }
    if (hash(x, 79) > 0.965) p.rect(x, top + 6 + hash(x, 80) * 10, 3 + hash(x, 81) * 3, 2, '#3e3c40');
  }
}

function woods(p) {
  const trunk = '#2a2420', leaf = ['#1e3020', '#24382a', '#2c4430'];
  for (const [cx, w] of [[10, 12], [SW - 12, 14], [44, 7], [SW - 46, 8]]) {
    for (let y = 0; y < SH; y++) for (let i = 0; i < w; i++) p.set(cx - w / 2 + i + Math.sin(y * 0.05) * 2, y, i < 2 || i > w - 3 ? '#1c1814' : trunk);
  }
  // canopy over the top corners
  for (let y = 0; y < 46; y++) for (let x = 0; x < SW; x++) {
    const edge = Math.min(x, SW - 1 - x);
    const reach = 90 - y * 1.6 + Math.sin(x * 0.09 + y * 0.3) * 8 + (hash(x >> 1, y >> 1, 90) - 0.5) * 14;
    if (edge < reach) p.set(x, y, leaf[Math.floor(hash(x >> 2, y >> 2, 91) * 3)]);
  }
  // undergrowth along the bottom edges
  for (let x = 0; x < SW; x++) {
    const edge = Math.min(x, SW - 1 - x), h = Math.round(Math.max(0, 22 - edge * 0.25) + hash(x >> 1, 92) * 4);
    for (let y = SH - h; y < SH; y++) if (edge < 120) p.set(x, y, leaf[(x + y) % 3]);
  }
}
