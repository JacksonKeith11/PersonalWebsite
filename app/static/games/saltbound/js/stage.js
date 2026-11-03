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
  if (f.kind === 'dungeon') return { coral: 'chapel', keys: 'fort', storm: 'lighthouse' }[reg] || 'chapel';
  return SCENES[reg] ? reg : 'peak';
}

export function stageURL(key) {
  if (!urls[key]) { const p = painter(); (SCENES[key] || SCENES.peak)(p); urls[key] = p.done(); }
  return urls[key];
}
export const STAGE_FLOOR = FLOOR / SH;
