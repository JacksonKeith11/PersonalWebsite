// Terrain at 32px per tile, painted procedurally per theme and composed into one canvas per battle,
// so tiles can react to their neighbours: shorelines, cliff edges under high ground, shadows below
// walls and trees, lava glow on the ground beside it.
import { T, GW, GH } from './data.js?v=29';

export const TP = 32;
const DIR4 = [[0, -1], [1, 0], [0, 1], [-1, 0]];

function rng(seed) {
  return () => {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
const ri = (r, a, b) => a + Math.floor(r() * (b - a + 1));
function px(x, col, X, Y, w = 1, h = 1) { x.fillStyle = col; x.fillRect(X, Y, w, h); }

// A shaded blob: an ellipse lit from the upper left, coloured from a dark-to-light ramp, with a
// dark rim. The workhorse for canopies, boulders, rubble and slime-like shapes.
function blob(x, cx, cy, rx, ry, ramp, rim = ramp[0], light = 1) {
  for (let y = Math.floor(cy - ry - 1); y <= cy + ry + 1; y++) for (let X = Math.floor(cx - rx - 1); X <= cx + rx + 1; X++) {
    const dx = (X + 0.5 - cx) / rx, dy = (y + 0.5 - cy) / ry, d = dx * dx + dy * dy;
    if (d > 1) continue;
    const edge = d > 1 - 2.2 / Math.max(rx, ry);
    const n = Math.max(0, Math.min(0.999, 0.55 - (dx + dy) * 0.42 * light + (1 - d) * 0.15));
    px(x, edge ? rim : ramp[1 + Math.floor(n * (ramp.length - 1))] || ramp[ramp.length - 1], X, y);
  }
}
function shadowOval(x, cx, cy, rx, ry, a = 0.28) {
  x.fillStyle = `rgba(10,6,20,${a})`;
  for (let y = Math.floor(cy - ry); y <= cy + ry; y++) for (let X = Math.floor(cx - rx); X <= cx + rx; X++) {
    const dx = (X + 0.5 - cx) / rx, dy = (y + 0.5 - cy) / ry;
    if (dx * dx + dy * dy <= 1) x.fillRect(X, y, 1, 1);
  }
}
// noise of two tones over a base, in small clumps
function speckle(x, r, cols, n, w = 2) { for (let i = 0; i < n; i++) px(x, cols[i % cols.length], ri(r, 0, 31), ri(r, 0, 31), ri(r, 1, w), 1); }

// ---------- ground styles ----------
// Leafy tufts: x is the tuft's green, t its lighter tips.
const TUFTS = [
  ['t...t..', '.x.t.x.', 'x.x.x.x', '.xxxxx.', '..x.x..'],
  ['..t..t.', 't.x..x.', '.x.xx.t', 'x.xxx.x', '.xx.xx.'],
  ['.t.t.', 'x.x.x', '.xxx.', 'x.x.x'],
  ['t..t..t', '.x.x.x.', 'xx.x.xx', '.xxxxx.'],
  ['t..t', '.xx.', 'xxxx'],
];
const GROUND = {
  // Calm, warm grass after the owner's reference tileset: a flat base, a few soft leafy tufts a shade
  // darker (some tipped with yellow-green), and now and then a small flower. No speckle noise.
  grass(x, P, r) {
    px(x, P.g[1], 0, 0, 32, 32);
    // tufts come in a loose clump or two, so the ground has quiet stretches between them
    for (let k = ri(r, 1, 2); k > 0; k--) {
      const cx = ri(r, 4, 24), cy = ri(r, 4, 24);
      for (let i = ri(r, 1, 3); i > 0; i--) {
        const t = TUFTS[ri(r, 0, TUFTS.length - 1)], bx = Math.min(25, Math.max(0, cx + ri(r, -6, 6))), by = Math.min(26, Math.max(0, cy + ri(r, -4, 4)));
        const leaf = r() < 0.3 ? P.g[0] : P.tuft, tip = r() < 0.4 ? P.g[3] : P.g[2];
        t.forEach((row, y) => [...row].forEach((c, X) => { if (c === 'x') px(x, leaf, bx + X, by + y); else if (c === 't') px(x, tip, bx + X, by + y); }));
      }
    }
    if (r() < 0.18) { // a small flower: four petals around a bright centre, a leaf below
      const fx = ri(r, 4, 27), fy = ri(r, 4, 26), c = P.flower[ri(r, 0, P.flower.length - 1)];
      px(x, P.tuft, fx - 1, fy + 2, 3, 1); px(x, c, fx - 1, fy); px(x, c, fx + 1, fy); px(x, c, fx, fy - 1); px(x, c, fx, fy + 1); px(x, '#ffe680', fx, fy);
    }
  },
  flag(x, P, r, v) {
    px(x, P.mortar, 0, 0, 32, 32);
    for (let row = 0; row < 2; row++) {
      const off = (row + v) % 2 ? 8 : 0;
      for (let c = -1; c < 2; c++) {
        const X = c * 16 + off, Y = row * 16, col = P.g[ri(r, 1, 2)];
        px(x, col, X + 1, Y + 1, 14, 14);
        px(x, P.g[3], X + 1, Y + 1, 14, 1); px(x, P.g[3], X + 1, Y + 1, 1, 14);
        px(x, P.g[0], X + 1, Y + 14, 14, 1); px(x, P.g[0], X + 14, Y + 1, 1, 14);
      }
    }
    speckle(x, r, [P.g[0], P.g[2]], 8, 2);
    if (r() < 0.5) { let cx = ri(r, 4, 26), cy = ri(r, 4, 26); for (let i = 0; i < 6; i++) { px(x, P.mortar, cx, cy); cx += ri(r, 0, 1); cy += ri(r, -1, 1); } }
    if (r() < 0.4) for (let i = 0; i < 4; i++) px(x, P.moss, ri(r, 0, 31), ri(r, 0, 31), 2, 1);
  },
  basalt(x, P, r, v, frame) {
    px(x, P.g[1], 0, 0, 32, 32);
    speckle(x, r, [P.g[0], P.g[2]], 18, 3);
    for (let k = 0; k < 2; k++) { // cracks, a few of them smouldering
      let cx = ri(r, 0, 31), cy = ri(r, 0, 31);
      const hot = r() < 0.18;
      for (let i = 0; i < 7; i++) { px(x, hot ? (i % 3 === (frame % 3) ? P.glow[1] : P.glow[0]) : P.g[0], cx, cy); cx += ri(r, -1, 1); cy += 1; }
    }
    for (let i = 0; i < 5; i++) px(x, P.ash, ri(r, 0, 31), ri(r, 0, 31));
  },
  mud(x, P, r) {
    px(x, P.g[1], 0, 0, 32, 32);
    speckle(x, r, [P.g[0], P.g[2]], 22, 3);
    for (let i = 0; i < 2; i++) { const px0 = ri(r, 3, 24), py0 = ri(r, 3, 26); px(x, P.g[0], px0, py0 + 1, 6, 2); px(x, P.puddle, px0 + 1, py0, 4, 2); px(x, P.g[3], px0 + 1, py0, 1, 1); }
    for (let i = ri(r, 0, 2); i > 0; i--) { const bx = ri(r, 1, 30), by = ri(r, 3, 30); px(x, P.reed[1], bx, by - 3, 1, 3); px(x, P.reed[0], bx, by, 1, 1); }
  },
  snow(x, P, r) {
    px(x, P.g[2], 0, 0, 32, 32);
    speckle(x, r, [P.g[1], P.g[3]], 16, 3);
    for (let i = 0; i < 3; i++) { const sx = ri(r, 2, 26), sy = ri(r, 2, 28); px(x, P.g[1], sx, sy + 1, 5, 1); px(x, P.g[3], sx + 1, sy, 3, 1); }
    if (r() < 0.4) { const sx = ri(r, 4, 26), sy = ri(r, 4, 28); px(x, P.stone[1], sx, sy, 3, 2); px(x, P.g[3], sx, sy, 3, 1); }
  },
  plate(x, P, r, v) {
    px(x, P.mortar, 0, 0, 32, 32);
    for (let i = 0; i < 4; i++) {
      const X = (i % 2) * 16, Y = (i >> 1) * 16;
      px(x, P.g[1 + ((i + v) % 2)], X + 1, Y + 1, 14, 14);
      px(x, P.g[3], X + 1, Y + 1, 14, 1); px(x, P.g[0], X + 1, Y + 14, 14, 1);
      px(x, P.rivet, X + 2, Y + 2); px(x, P.rivet, X + 13, Y + 2); px(x, P.rivet, X + 2, Y + 12); px(x, P.rivet, X + 13, Y + 12);
    }
    speckle(x, r, [P.g[0], P.rust], 14, 2);
    if (r() < 0.35) { const gx = ri(r, 6, 22), gy = ri(r, 6, 22); px(x, P.g[0], gx, gy, 6, 1); px(x, P.g[0], gx, gy + 3, 6, 1); }
  },
};

// ---------- props (cover and rock) ----------
const PROP = {
  tree(x, P, r) {
    shadowOval(x, 16, 28, 11, 3.5);
    px(x, P.trunk[0], 14, 20, 5, 8); px(x, P.trunk[1], 15, 20, 2, 7); px(x, P.trunk[0], 13, 27, 7, 1);
    const ramp = P.leaf;
    blob(x, 16, 13, 12.5, 10.5, ramp);
    blob(x, 10, 11, 6, 5.5, ramp, ramp[1]);
    blob(x, 21, 9, 6.5, 6, ramp, ramp[1]);
    blob(x, 14, 6, 6, 4.5, ramp, ramp[2]);
    for (let i = 0; i < 7; i++) px(x, ramp[ramp.length - 1], ri(r, 8, 20), ri(r, 4, 12));
    for (let i = 0; i < 5; i++) px(x, ramp[0], ri(r, 6, 26), ri(r, 14, 21));
    if (r() < 0.3) for (let i = 0; i < 3; i++) px(x, P.berry, ri(r, 8, 24), ri(r, 7, 18));
  },
  boulder(x, P, r) {
    shadowOval(x, 16, 27, 12, 3.5);
    blob(x, 16, 19, 12, 9, P.stone);
    blob(x, 10, 22, 5, 4, P.stone);
    px(x, P.stone[3], 11, 13, 4, 1); px(x, P.stone[3], 10, 14, 1, 2);
    for (let i = 0; i < 3; i++) { const cx = ri(r, 12, 22), cy = ri(r, 16, 24); px(x, P.stone[0], cx, cy, 2, 1); px(x, P.stone[0], cx + 2, cy + 1); }
    if (P.moss && r() < 0.6) for (let i = 0; i < 6; i++) px(x, P.moss, ri(r, 9, 22), ri(r, 11, 14), 2, 1);
  },
  rubble(x, P, r) {
    for (let i = 0; i < 5; i++) {
      const cx = ri(r, 7, 25), cy = ri(r, 14, 25), s = ri(r, 3, 6);
      shadowOval(x, cx + 1, cy + s * 0.6, s, 2, 0.22);
      blob(x, cx, cy, s, s * 0.75, P.stone);
    }
    if (r() < 0.5) { px(x, P.bone, 20, 24, 5, 1); px(x, P.bone, 19, 23); px(x, P.bone, 25, 25); }
  },
  sarcophagus(x, P) {
    shadowOval(x, 16, 28, 13, 3);
    px(x, P.stone[0], 5, 6, 22, 22); px(x, P.stone[2], 6, 7, 20, 13); px(x, P.stone[1], 6, 20, 20, 7);
    px(x, P.stone[3], 6, 7, 20, 1); px(x, P.stone[3], 6, 7, 1, 13);
    px(x, P.gold, 15, 9, 2, 9); px(x, P.gold, 12, 12, 8, 2); px(x, '#fff0a0', 15, 9, 1, 3);
    px(x, P.stone[0], 6, 19, 20, 1);
  },
  ashmound(x, P, r) {
    shadowOval(x, 16, 27, 12, 3.5);
    blob(x, 16, 21, 12, 7, P.ashRamp);
    px(x, P.trunk[0], 18, 9, 2, 10); px(x, P.trunk[0], 20, 11, 3, 1); px(x, P.trunk[0], 14, 13, 4, 1);
    px(x, P.glow[1], 18, 12); px(x, P.glow[0], 15, 13);
  },
  obsidian(x, P, r) {
    shadowOval(x, 16, 27, 11, 3.5);
    const shard = (bx, h, w) => {
      for (let y = 0; y < h; y++) {
        const half = Math.max(1, Math.round(w * Math.min(1, (y + 2) / (h * 0.45)) / 2));
        for (let X = -half; X <= half; X++) px(x, X === -half || X === half ? P.obs[0] : X < 0 ? P.obs[2] : P.obs[1], bx + X, 27 - h + y);
      }
      px(x, P.obs[3], bx - 1, 27 - h + 2, 1, Math.floor(h / 2));
    };
    shard(12, 18, 8); shard(21, 13, 7); shard(16, 9, 6);
  },
  reeds(x, P, r) {
    for (let i = 0; i < 14; i++) {
      const bx = ri(r, 4, 27), h = ri(r, 10, 20), by = ri(r, 24, 30);
      px(x, P.reed[0], bx, by - h, 1, h); px(x, P.reed[1], bx + 1, by - h + 2, 1, h - 3);
      if (r() < 0.4) { px(x, P.cattail, bx, by - h - 3, 2, 4); }
    }
  },
  stump(x, P, r) {
    shadowOval(x, 16, 26, 10, 3);
    px(x, P.trunk[0], 9, 14, 14, 12); px(x, P.trunk[1], 10, 15, 12, 10);
    blob(x, 16, 14, 7, 3, [P.trunk[0], P.trunk[1], P.ring, P.ring]);
    px(x, P.trunk[0], 13, 13, 6, 1); px(x, P.trunk[0], 15, 14, 2, 1);
    if (P.moss) for (let i = 0; i < 4; i++) px(x, P.moss, ri(r, 9, 22), ri(r, 18, 25));
  },
  snowdrift(x, P, r) {
    shadowOval(x, 16, 27, 12, 3);
    blob(x, 16, 21, 13, 7, P.snowRamp);
    blob(x, 11, 19, 6, 5, P.snowRamp, P.snowRamp[1]);
    for (let i = 0; i < 4; i++) px(x, '#ffffff', ri(r, 8, 22), ri(r, 15, 20));
  },
  iceblock(x, P) {
    shadowOval(x, 16, 28, 12, 3);
    px(x, P.ice[0], 5, 7, 22, 21); px(x, P.ice[2], 6, 8, 20, 9); px(x, P.ice[1], 6, 17, 20, 10);
    px(x, P.ice[3], 7, 9, 6, 1); px(x, P.ice[3], 7, 9, 1, 5); px(x, P.ice[3], 20, 19, 1, 4);
    px(x, P.ice[0], 6, 16, 20, 1);
  },
  crate(x, P) {
    shadowOval(x, 16, 28, 12, 3);
    px(x, P.wood[0], 5, 8, 22, 20); px(x, P.wood[2], 6, 9, 20, 7); px(x, P.wood[1], 6, 16, 20, 11);
    px(x, P.wood[3], 6, 9, 20, 1);
    for (let i = 0; i < 3; i++) px(x, P.wood[0], 6, 19 + i * 3, 20, 1);
    px(x, P.rivet, 7, 10); px(x, P.rivet, 24, 10); px(x, P.rivet, 7, 25); px(x, P.rivet, 24, 25);
  },
  gearpile(x, P, r) {
    shadowOval(x, 16, 27, 12, 3);
    const gear = (cx, cy, R) => {
      for (let a = 0; a < 8; a++) { const ang = a * Math.PI / 4; px(x, P.metal[1], Math.round(cx + Math.cos(ang) * (R + 1)) - 1, Math.round(cy + Math.sin(ang) * (R + 1)) - 1, 3, 3); }
      blob(x, cx, cy, R, R, P.metal);
      blob(x, cx, cy, R * 0.35, R * 0.35, [P.metal[0], P.mortar, P.mortar]);
    };
    gear(12, 20, 6); gear(21, 18, 5); gear(17, 12, 4);
  },
};

// ---------- the other terrain ----------
function waterTile(x, P, r, frame) {
  px(x, P.water[1], 0, 0, 32, 32);
  speckle(x, r, [P.water[0]], 18, 4);
  for (let i = 0; i < 5; i++) { // ripples drift with the frame
    const wy = 3 + i * 6, wx = (ri(r, 0, 28) + frame * 3) % 30;
    px(x, P.water[2], wx, wy, 4, 1); px(x, P.water[2], (wx + 14) % 30, wy + 3, 3, 1);
  }
  px(x, P.water[3], (ri(r, 2, 26) + frame * 5) % 30, ri(r, 2, 28));
}
function pitTile(x, P, r, frame) {
  px(x, P.pit[0], 0, 0, 32, 32);
  speckle(x, r, [P.pit[1]], 6, 2);
  if (P.glow) for (let i = 0; i < 3; i++) px(x, P.glow[0], (ri(r, 0, 30) + frame * 5) % 31, ri(r, 4, 30));
}
function lavaTile(x, P, r, frame) {
  const L = ['#7a1e10', '#c8401a', '#ff7a1a', '#ffd23f'];
  px(x, L[1], 0, 0, 32, 32);
  for (let i = 0; i < 7; i++) { // dark crust plates that slide slowly
    const cx = (ri(r, 0, 31) + frame) % 32, cy = ri(r, 0, 31);
    blob(x, cx, cy, ri(r, 3, 5), ri(r, 2, 3), [L[0], L[0], '#5a1408'], L[0], 0);
  }
  for (let i = 0; i < 9; i++) px(x, L[2], (ri(r, 0, 29) + frame * 2) % 30, ri(r, 0, 30), 3, 1);
  for (let i = 0; i < 4; i++) px(x, L[3], (ri(r, 0, 30) + frame * 3) % 31, ri(r, 0, 31));
}
function wallTile(x, P, r) {
  const W = P.wall;
  px(x, W[0], 0, 0, 32, 32);
  px(x, W[2], 0, 0, 32, 11); px(x, W[3], 0, 0, 32, 1);
  speckle(x, r, [W[1], W[3]], 10, 3);
  for (let y = 12, row = 0; y < 30; y += 6, row++) { // the front face, in courses of bricks
    for (let bx = (row % 2) * 6 - 6; bx < 32; bx += 12) {
      px(x, W[1], bx + 1, y, 10, 5); px(x, W[2], bx + 1, y, 10, 1); px(x, W[0], bx + 1, y + 4, 10, 1);
    }
  }
  px(x, W[0], 0, 11, 32, 1);
  if (P.moss) for (let i = 0; i < 7; i++) { const mx = ri(r, 0, 29); px(x, P.moss, mx, ri(r, 9, 13), ri(r, 2, 4), 1); }
  if (P.wallGlow && r() < 0.6) { const gx = ri(r, 4, 26); px(x, P.wallGlow, gx, 13, 1, 12); }
}
function hillTop(x, P) { // high ground: a lighter plateau
  x.fillStyle = 'rgba(255,244,210,0.2)'; x.fillRect(0, 0, 32, 32);
}
function thornTile(x, P, r) {
  const style = P.thorn;
  if (style === 'bramble') {
    for (let k = 0; k < 3; k++) { const bx = ri(r, 7, 25), by = ri(r, 10, 24); shadowOval(x, bx, by + 4, 7, 2.5, 0.25); blob(x, bx, by, ri(r, 5, 7), ri(r, 4, 5), P.bush, P.bush[0]); }
    for (let k = 0; k < 6; k++) {
      let cx = ri(r, 2, 29), cy = ri(r, 4, 28);
      for (let i = 0; i < 12; i++) {
        px(x, P.vine[0], cx, cy + 1); px(x, P.vine[1], cx, cy);
        if (i % 3 === 0) px(x, P.vine[2], cx + (r() < 0.5 ? -1 : 1), cy - 1);
        cx = Math.max(1, Math.min(30, cx + ri(r, -1, 1))); cy = Math.max(2, Math.min(30, cy + (r() < 0.5 ? -1 : 1)));
      }
    }
    for (let i = 0; i < 3; i++) { const bx = ri(r, 3, 28), by = ri(r, 3, 28); px(x, '#c8203a', bx, by, 2, 2); px(x, '#ff8a9a', bx, by); }
  } else {
    for (let i = 0; i < 6; i++) {
      const sx = ri(r, 3, 27), sy = ri(r, 10, 28), h = ri(r, 5, 9);
      shadowOval(x, sx + 1, sy + 1, 3, 1, 0.3);
      for (let y = 0; y < h; y++) { const w = Math.max(1, Math.round((y / h) * 3)); px(x, P.spike[0], sx - w + 1, sy - h + y, w * 2 - 1, 1); px(x, P.spike[1], sx - w + 1, sy - h + y, 1, 1); }
    }
  }
}

// ---------- themes ----------
const THEME_ART = {
  wood: {
    ground: 'grass', cover: 'tree', rock: 'boulder', hole: 'water',
    // after the owner's grassland reference: warm olive grass, orange-brown earth, deep green canopies
    g: ['#6e8a44', '#a1b159', '#b4c264', '#cfd06e'], tuft: '#8a9e4c', under: '#7e9848', patch: ['#abba60', '#97a852'], flower: ['#e8902e', '#f2c94c', '#d85a3a', '#6a8ae0'],
    stone: ['#6a5848', '#a8907a', '#c8b098', '#e0d0b8'], moss: '#6e8a3c',
    leaf: ['#2c461d', '#3e5e24', '#4a6b28', '#5b7d33', '#738e3c', '#94ac50'], trunk: ['#5a3420', '#8a5434'], berry: '#d04a4a',
    water: ['#2a4a8a', '#3a62a8', '#5a86c8', '#c8e0ff'], bank: ['#945c37', '#b47c43'], foam: '#bcd8f8',
    wall: ['#5a4a3a', '#7a6650', '#9a8468', '#bca88a'], thorn: 'bramble', vine: ['#4a2a18', '#8a5434', '#e8d4a8'], bush: ['#2c461d', '#3e5e24', '#4a6b28', '#5b7d33'], cliff: ['#945c37', '#b47c43', '#7a4a2c'],
  },
  crypt: {
    ground: 'flag', cover: 'rubble', rock: 'sarcophagus', hole: 'pit',
    g: ['#2c2a3e', '#37344a', '#3e3b53', '#4b4864'], mortar: '#201e30', moss: '#3e5a34',
    stone: ['#2a2838', '#55536a', '#6e6c86', '#9a98b4'], bone: '#d8d0b8', gold: '#c8a040',
    pit: ['#05040a', '#0e0c18', '#22203a'], wall: ['#1e1a30', '#2e2a46', '#4a4470', '#6a62a0'], wallGlow: '#3a8a6a',
    thorn: 'spike', spike: ['#d8d0b8', '#ffffff'], cliff: ['#1e1c2c', '#2e2a46', '#16141f'],
  },
  ember: {
    ground: 'basalt', cover: 'ashmound', rock: 'obsidian', hole: 'pit',
    g: ['#221a1c', '#33292a', '#423636', '#5a4a48'], patch: ['#3a2f30', '#2c2324'], glow: ['#7a2414', '#ff6a2a'], ash: '#8a7c7e',
    ashRamp: ['#241c1e', '#3e3436', '#52484a', '#665a5c', '#7e7072'], trunk: ['#1a1210', '#2e221c'],
    obs: ['#0e0816', '#2e2240', '#4e3a6e', '#9a7ad8'], stone: ['#1a1216', '#3a2f30', '#5a4a48', '#7a6a66'],
    pit: ['#030203', '#0e0606', '#2a1410'], wall: ['#120c1a', '#211a2c', '#3a2e52', '#5a4a7a'], wallGlow: '#ff6a2a',
    thorn: 'spike', spike: ['#c48aff', '#ffd8a0'], cliff: ['#1a1214', '#2e2224', '#120c0e'],
  },
  marsh: {
    ground: 'mud', cover: 'reeds', rock: 'stump', hole: 'water',
    g: ['#2e3a24', '#3c4a2c', '#4a5a34', '#6a7a4a'], patch: ['#445232', '#344228'], puddle: '#2a3a3a', reed: ['#5a6a2a', '#8a9a3a'], cattail: '#5a3a1e',
    stone: ['#2e3028', '#4e5244', '#6a6e5c', '#8a8e78'], moss: '#5a7a34', trunk: ['#2e2016', '#4e3624'], ring: '#7a5a3a',
    water: ['#1a2e26', '#23403a', '#3a5e50', '#8ab0a0'], bank: ['#2a2016', '#3e2e1e'], foam: '#7a9a80',
    wall: ['#2a2e24', '#3e4436', '#56604a', '#76806a'], thorn: 'bramble', vine: ['#2a1a14', '#5a3a24', '#c8b48a'], bush: ['#18221a', '#22301e', '#2e4026', '#3e5430'],
    cliff: ['#2a2016', '#3e2e1e', '#1e160e'],
  },
  frost: {
    ground: 'snow', cover: 'snowdrift', rock: 'iceblock', hole: 'water',
    g: ['#9aaac4', '#c4d0e4', '#dfe8f4', '#f6faff'], patchBase: '#dfe8f4', patch: ['#eaf0f8', '#d0dcec'], stone: ['#4a5468', '#6a7488', '#8a94a8', '#b4bccc'],
    snowRamp: ['#8a9ab8', '#b0bed4', '#d0dcec', '#eaf2fa', '#ffffff'], ice: ['#4a7aa8', '#8ac0e8', '#b8e0f8', '#ffffff'],
    water: ['#1a3a5a', '#2a5478', '#5a8ab0', '#e0f4ff'], bank: ['#6a7a94', '#9aaac4'], foam: '#e8f4ff',
    wall: ['#3a5a7a', '#6a9ac0', '#9ac8e8', '#d8f0ff'], thorn: 'spike', spike: ['#b8e0f8', '#ffffff'], cliff: ['#6a7a94', '#8a9ab4', '#4a5a74'],
  },
  foundry: {
    ground: 'plate', cover: 'crate', rock: 'gearpile', hole: 'pit',
    g: ['#2a2a32', '#3a3a44', '#44444f', '#5a5a68'], mortar: '#1a1a20', rivet: '#8a8a9a', rust: '#6a3a24',
    wood: ['#3a2416', '#6a4426', '#8a5a32', '#aa7a46'], metal: ['#2a2a32', '#5a5a68', '#7a7a8a', '#a8a8b8'],
    pit: ['#050404', '#140a06', '#3a1a0a'], glow: ['#7a2a0a', '#ff7a1a'],
    wall: ['#1e1e26', '#34343e', '#4e4e5c', '#6e6e80'], wallGlow: '#c8a040', thorn: 'spike', spike: ['#a8a8b8', '#ffffff'], cliff: ['#1a1a20', '#2e2e38', '#121216'],
  },
};
export const THEME_KEYS = Object.keys(THEME_ART);
export function addThemes(more) { Object.assign(THEME_ART, more); THEME_KEYS.splice(0, THEME_KEYS.length, ...Object.keys(THEME_ART)); }

const isHole = t => t === T.WATER;
const solidish = t => t === T.WALL || t === T.ROCK || t === T.COVER;
const cache = new Map();
// One tile's own art, cached per theme, type, variant and animation frame.
function tileArt(theme, type, v, frame) {
  const animated = type === T.WATER || type === T.LAVA || (type === T.FLOOR && theme === 'ember');
  const k = `${theme}|${type}|${v}|${animated ? frame % 3 : 0}`;
  if (cache.has(k)) return cache.get(k);
  const P = THEME_ART[theme], c = document.createElement('canvas');
  c.width = c.height = TP;
  const x = c.getContext('2d'), seed = THEME_KEYS.indexOf(theme) * 7919 + v * 131, f = animated ? frame % 3 : 0;
  const ground = () => GROUND[P.ground](x, P, rng(seed + 1), v, f);
  if (type === T.WATER) (P.hole === 'water' ? waterTile : pitTile)(x, P, rng(seed + 3), f);
  else if (type === T.LAVA) lavaTile(x, P, rng(seed + 5), f);
  else if (type === T.WALL) wallTile(x, P, rng(seed + 7));
  else {
    ground();
    if (P.under && (type === T.COVER || type === T.ROCK)) { // darker grass gathered under trees and rocks
      const r = rng(seed + 9);
      for (let y = 20; y < 32; y++) for (let X = 2; X < 30; X++) { const dx = (X - 16) / 14, dy = (y - 26) / 5.5; if (dx * dx + dy * dy < 1 - r() * 0.25) px(x, P.under, X, y); }
    }
    if (type === T.COVER) PROP[P.cover](x, P, rng(seed + 11));
    else if (type === T.ROCK) PROP[P.rock](x, P, rng(seed + 13));
    else if (type === T.HILL) hillTop(x, P);
    else if (type === T.THORN) thornTile(x, P, rng(seed + 17));
  }
  cache.set(k, c);
  return c;
}

// A plain ground tile, for backdrops like the map.
export const groundTile = (theme, v) => tileArt(theme, T.FLOOR, v, 0);

// Broad, soft patches of lighter ground that run across tile edges, with stepped (dithered) borders:
// a value-noise mask per battle, seeded from its tile variants.
const patchCache = new WeakMap();
function patchMask(vari) {
  if (patchCache.has(vari)) return patchCache.get(vari);
  const r = rng(vari.flat().reduce((a, v, i) => a * 31 + v + i, 7) | 0), C = 10, gw = Math.ceil(GW * TP / C) + 2, gh = Math.ceil(GH * TP / C) + 2;
  const g = Array.from({ length: gh }, () => Array.from({ length: gw }, () => r()));
  const W = GW * TP, H = GH * TP, m = new Uint8Array(W * H), sm = t => t * t * (3 - 2 * t);
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const gx = x / C, gy = y / C, ix = Math.floor(gx), iy = Math.floor(gy), fx = sm(gx - ix), fy = sm(gy - iy);
    const v = (g[iy][ix] * (1 - fx) + g[iy][ix + 1] * fx) * (1 - fy) + (g[iy + 1][ix] * (1 - fx) + g[iy + 1][ix + 1] * fx) * fy;
    m[y * W + x] = v > 0.62 ? 2 : v > 0.58 && (x + y) % 2 === 0 ? 2 : v < 0.3 ? 1 : v < 0.33 && (x + y) % 2 === 0 ? 1 : 0;
  }
  patchCache.set(vari, m);
  return m;
}
const hex3 = h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];

// Paint the whole board: each tile's art, then the touches that depend on neighbours.
export function drawBoard(ctx, theme, grid, vari, frame) {
  const P = THEME_ART[theme];
  const at = (x, y) => (x < 0 || y < 0 || x >= GW || y >= GH ? null : grid[y][x]);
  ctx.clearRect(0, 0, GW * TP, GH * TP);
  // plain ground gets eight variants (mixed with position so neighbours rarely match); other tiles four
  for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
    const t = grid[y][x], v = t === T.FLOOR ? (vari[y][x] * 3 + x * 5 + y * 7) % 8 : vari[y][x] % 4;
    ctx.drawImage(tileArt(theme, t, v, frame + vari[y][x]), x * TP, y * TP);
  }
  if (P.patch) { // only bare base-colour ground changes, so props and tufts are untouched
    const W = GW * TP, img = ctx.getImageData(0, 0, W, GH * TP), d = img.data, m = patchMask(vari);
    const base = hex3(P.patchBase || P.g[1]), light = hex3(P.patch[0]), dark = hex3(P.patch[1]);
    for (let i = 0; i < m.length; i++) {
      if (!m[i]) continue;
      const j = i * 4;
      if (d[j] !== base[0] || d[j + 1] !== base[1] || d[j + 2] !== base[2]) continue;
      const c = m[i] === 2 ? light : dark;
      d[j] = c[0]; d[j + 1] = c[1]; d[j + 2] = c[2];
    }
    ctx.putImageData(img, 0, 0);
  }
  for (let y = 0; y < GH; y++) for (let x = 0; x < GW; x++) {
    const t = grid[y][x], X = x * TP, Y = y * TP;
    if (isHole(t)) {
      // the bank above a pool, foam where water meets land
      const up = at(x, y - 1);
      if (up != null && !isHole(up) && up !== T.LAVA) {
        if (P.hole === 'water') { px(ctx, P.bank[0], X, Y, 32, 4); px(ctx, P.bank[1], X, Y, 32, 2); px(ctx, P.foam, X, Y + 4, 32, 1); }
        else { px(ctx, P.cliff[1], X, Y, 32, 7); px(ctx, P.cliff[0], X, Y, 32, 2); px(ctx, P.pit[2], X, Y + 7, 32, 3); px(ctx, P.pit[1], X, Y + 10, 32, 3); }
      }
      // a chasm glows from far below where it meets the ground again
      if (P.glow && P.hole === 'pit' && at(x, y + 1) !== T.WATER) { px(ctx, P.glow[0], X, Y + 26, 32, 6); px(ctx, P.glow[1], X + (frame * 7 + x * 5) % 28, Y + 29, 4, 1); }
      if (P.hole === 'water') for (const [dx, dy] of DIR4) {
        const n = at(x + dx, y + dy);
        if (n == null || isHole(n) || dy === -1) continue;
        ctx.fillStyle = P.foam;
        if (dx === 1) ctx.fillRect(X + 31, Y, 1, 32); else if (dx === -1) ctx.fillRect(X, Y, 1, 32); else ctx.fillRect(X, Y + 31, 32, 1);
      }
    }
    if (t === T.HILL) { // a plateau: lit rim where it starts, a cliff face where it drops away
      const ledge = 'rgba(255,248,220,0.35)';
      if (at(x, y - 1) !== T.HILL) px(ctx, ledge, X, Y, 32, 1);
      if (at(x - 1, y) !== T.HILL) { px(ctx, ledge, X, Y, 1, 24); px(ctx, P.cliff[1], X - (at(x - 1, y) == null ? 0 : 2), Y + 2, 2, 24); }
      if (at(x + 1, y) !== T.HILL) { px(ctx, P.cliff[0], X + 31, Y, 1, 24); }
      if (at(x, y + 1) !== T.HILL) {
        px(ctx, P.cliff[1], X, Y + 23, 32, 9); px(ctx, P.cliff[0], X, Y + 23, 32, 1); px(ctx, P.cliff[2], X, Y + 31, 32, 1);
        for (let i = 1; i < 32; i += 4) px(ctx, P.cliff[2], X + i, Y + 25 + (i % 3), 1, 3);
        if (P.g) for (let i = 0; i < 32; i += 3) px(ctx, P.g[2], X + i, Y + 23, 2, 1 + (i % 2));
      }
    }
    if (t === T.WALL && at(x, y + 1) != null && at(x, y + 1) !== T.WALL && !isHole(at(x, y + 1))) { ctx.fillStyle = 'rgba(10,6,20,0.32)'; ctx.fillRect(X, Y + 32, 32, 6); }
    if (t === T.LAVA) for (const [dx, dy] of DIR4) {
      const n = at(x + dx, y + dy);
      if (n == null || n === T.LAVA) continue;
      ctx.fillStyle = 'rgba(255,120,40,0.22)';
      ctx.fillRect(X + (dx === 1 ? 32 : dx === -1 ? -3 : 0), Y + (dy === 1 ? 32 : dy === -1 ? -3 : 0), dx ? 3 : 32, dy ? 3 : 32);
    }
  }
}
