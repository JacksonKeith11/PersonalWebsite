// The other bosses' arenas, drawn by code like the chapel (arena.js): a floor, a back wall and props,
// in each place's palette. Every painter returns {canvas, candles: [[x, y]], windows: [[x, y]], tint}.
import { drawChapel } from './arena.js?v=12';

function rng(seed) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}
const rgb = ([r, g, b], k = 1) => `rgb(${Math.max(0, Math.min(255, r * k)) | 0},${Math.max(0, Math.min(255, g * k)) | 0},${Math.max(0, Math.min(255, b * k)) | 0})`;
const hexc = h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];

function setup(w, h, seed) {
  const cv = document.createElement('canvas');
  cv.width = w; cv.height = h;
  const g = cv.getContext('2d');
  return { cv, g, R: rng(seed), rect: (x, y, ww, hh, c) => { g.fillStyle = c; g.fillRect(x | 0, y | 0, ww | 0, hh | 0); } };
}

// ------------------------------------------------------------------ floors
function slabs(P, w, h, top, base, sizes = [28, 22, 22, 8], vary = 0.1) {
  const { g, R, rect } = P;
  for (let y = top; y < h;) {
    const hh = sizes[2] + Math.floor(R() * sizes[3]);
    let x = -Math.floor(R() * 30);
    while (x < w) {
      const ww = sizes[0] + Math.floor(R() * sizes[1]), k = 1 - vary / 2 + R() * vary;
      rect(x + 1, y + 1, ww - 2, hh - 2, rgb(base, k));
      rect(x + 1, y + 1, ww - 2, 1, rgb(base, k * 1.07));
      rect(x + 1, y + hh - 2, ww - 2, 1, rgb(base, k * 0.85));
      for (let i = 0; i < 8; i++) rect(x + 2 + R() * (ww - 4), y + 2 + R() * (hh - 4), 1, 1, rgb(base, k * (0.88 + R() * 0.16)));
      x += ww;
    }
    y += hh;
  }
}

function speckle(P, w, h, top, base, n, size = 3) {
  const { R, rect } = P;
  for (let i = 0; i < n; i++) {
    const s = 1 + R() * size;
    rect(R() * w, top + R() * (h - top), s, s * 0.7, rgb(base, 0.8 + R() * 0.4));
  }
}

function planks(P, w, h, top, base) {
  const { R, rect } = P;
  for (let y = top; y < h; y += 10) {
    let x = -Math.floor(R() * 60);
    while (x < w) {
      const L = 40 + R() * 70, k = 0.9 + R() * 0.15;
      rect(x, y, L - 1, 9, rgb(base, k)); rect(x, y, L - 1, 1, rgb(base, k * 1.1)); rect(x, y + 8, L - 1, 1, rgb(base, k * 0.8));
      if (R() < 0.3) rect(x + R() * L, y + 3, 2, 2, rgb(base, 0.6));
      x += L;
    }
  }
}

function tiles(P, w, h, top, a, b, size = 24) {
  const { rect } = P;
  for (let y = top; y < h; y += size)
    for (let x = 0; x < w; x += size) {
      const c = ((x / size + y / size) | 0) % 2 ? a : b;
      rect(x, y, size - 1, size - 1, rgb(c)); rect(x, y, size - 1, 1, rgb(c, 1.12));
    }
}

// ------------------------------------------------------------------ walls and edges
function stoneWall(P, w, top, base) {
  const { R, rect } = P;
  for (let y = 0; y < top; y += 9) {
    const off = (y / 9) % 2 ? 0 : 10;
    for (let x = -off; x < w; x += 20) {
      const k = 0.9 + R() * 0.2;
      rect(x + 1, y + 1, 18, 7, rgb(base, k)); rect(x + 1, y + 1, 18, 1, rgb(base, k * 1.15)); rect(x + 1, y + 7, 18, 1, rgb(base, k * 0.75));
    }
  }
  ledge(P, w, top, base);
}

function ledge(P, w, top, base) {
  const { g, rect } = P;
  rect(0, top - 4, w, 4, rgb(base, 1.2)); rect(0, top - 4, w, 1, rgb(base, 1.4));
  for (let i = 0; i < 10; i++) { g.fillStyle = `rgba(10,6,14,${0.45 - i * 0.045})`; g.fillRect(0, top + i, w, 1); }
}

function trees(P, w, top, trunk, leaf) {
  const { g, R, rect } = P;
  rect(0, 0, w, top, rgb(leaf, 0.35));
  for (let x = -10; x < w; x += 26 + R() * 20) {
    const tw = 8 + R() * 8;
    rect(x, 0, tw, top + 4, rgb(trunk, 0.8 + R() * 0.3)); rect(x, 0, 2, top + 4, rgb(trunk, 1.15));
    for (let i = 0; i < 4; i++) { g.fillStyle = rgb(leaf, 0.6 + R() * 0.4); g.beginPath(); g.arc(x + R() * 30, R() * top * 0.7, 10 + R() * 14, 0, 7); g.fill(); }
  }
  for (let i = 0; i < 10; i++) { g.fillStyle = `rgba(8,10,6,${0.5 - i * 0.05})`; g.fillRect(0, top + i, w, 1); }
}

function vignette(P, w, h, strength = 0.55, colour = '8,4,12') {
  const { g } = P;
  const vg = g.createRadialGradient(w / 2, h * 0.55, h * 0.35, w / 2, h * 0.55, w * 0.62);
  vg.addColorStop(0, `rgba(${colour},0)`); vg.addColorStop(1, `rgba(${colour},${strength})`);
  g.fillStyle = vg; g.fillRect(0, 0, w, h);
}

function pool(P, x, y, rx, ry, c, d) {
  const { g } = P;
  g.fillStyle = c; g.beginPath(); g.ellipse(x, y, rx, ry, 0, 0, 7); g.fill();
  g.fillStyle = d; g.beginPath(); g.ellipse(x + rx * 0.15, y + ry * 0.2, rx * 0.7, ry * 0.6, 0, 0, 7); g.fill();
}

// ------------------------------------------------------------------ the arenas
const ARENAS = {
  chapel: drawChapel,

  bog(w, h, pad) {  // a drowned bog: mud, black water, reeds, dead trees behind
    const P = setup(w, h, 11), top = pad[1];
    P.rect(0, 0, w, h, '#2a2a1e');
    speckle(P, w, h, top, [62, 60, 40], 900, 4);
    speckle(P, w, h, top, [48, 56, 36], 500, 6);
    for (let i = 0; i < 9; i++) pool(P, P.R() * w, top + 40 + P.R() * (h - top - 60), 30 + P.R() * 40, 10 + P.R() * 12, '#1e2a24', '#24342c');
    trees(P, w, top, [58, 50, 38], [46, 58, 38]);
    for (let i = 0; i < 70; i++) {  // reeds
      const x = P.R() < 0.5 ? P.R() * pad[0] * 1.6 : w - P.R() * pad[2] * 1.6, y = top + P.R() * (h - top);
      for (let k = 0; k < 4; k++) P.rect(x + k * 2, y - 8 - P.R() * 10, 1, 10 + P.R() * 8, rgb([90, 100, 60], 0.7 + P.R() * 0.5));
    }
    vignette(P, w, h, 0.6, '6,10,6');
    return { canvas: P.cv, candles: [], windows: [], tint: 0x9ab07a, fog: 0x3a4a2a };
  },

  belfry(w, h, pad) {  // a belfry floor: old planks, fallen bells, ropes, a great window of night sky
    const P = setup(w, h, 13), top = pad[1];
    P.rect(0, 0, w, h, '#241c1a');
    planks(P, w, h, top, [74, 56, 42]);
    stoneWall(P, w, top, [58, 52, 64]);
    for (const wx of [w * 0.3, w * 0.7]) {
      P.rect(wx - 20, 6, 40, top - 16, '#141626');
      for (let i = 0; i < 12; i++) P.rect(wx - 18 + P.R() * 36, 8 + P.R() * (top - 22), 1, 1, '#c8c8e0');
    }
    for (const [x, y] of [[90, top + 60], [w - 110, top + 240], [140, h - 80]]) {  // fallen bells
      P.g.fillStyle = '#6e5232'; P.g.beginPath(); P.g.ellipse(x, y, 22, 14, 0.3, 0, 7); P.g.fill();
      P.g.fillStyle = '#946c3a'; P.g.beginPath(); P.g.ellipse(x - 4, y - 4, 14, 8, 0.3, 0, 7); P.g.fill();
    }
    for (const x of [w * 0.15, w * 0.5, w * 0.85]) P.rect(x, 0, 2, top + 30 + P.R() * 40, '#8a7a5a');  // ropes hanging down
    vignette(P, w, h);
    return { canvas: P.cv, candles: [[60, top + 20], [w - 60, top + 20], [w / 2, h - 50]], windows: [[w * 0.3, top + 30], [w * 0.7, top + 30]], tint: 0xd0b8a0 };
  },

  yard(w, h, pad) {  // the execution yard: packed earth, cobbles, a scaffold and a block
    const P = setup(w, h, 17), top = pad[1];
    P.rect(0, 0, w, h, '#3a3028');
    speckle(P, w, h, top, [80, 66, 52], 1400, 3);
    slabs(P, w * 0.6, h, h - 90, [70, 66, 66], [16, 10, 12, 4]);
    stoneWall(P, w, top, [70, 62, 60]);
    P.rect(w / 2 - 70, top - 30, 140, 30, '#4a3424'); for (let x = w / 2 - 66; x < w / 2 + 66; x += 10) P.rect(x, top - 30, 1, 30, '#3a2618');  // scaffold
    P.rect(w / 2 - 14, top + 6, 28, 16, '#5a3a24'); P.rect(w / 2 - 14, top + 6, 28, 2, '#6a4a2e'); P.rect(w / 2 - 6, top + 6, 12, 3, '#3a1418');  // the block
    for (let i = 0; i < 6; i++) pool(P, 80 + P.R() * (w - 160), top + 60 + P.R() * 300, 10 + P.R() * 10, 4 + P.R() * 4, '#3a1a1c', '#4a2024');
    vignette(P, w, h);
    return { canvas: P.cv, candles: [[w / 2 - 80, top - 10], [w / 2 + 80, top - 10]], windows: [], tint: 0xe0c8b0 };
  },

  forest(w, h, pad) {  // a thorn forest clearing: dark earth, roots, brambles round the edge
    const P = setup(w, h, 19), top = pad[1];
    P.rect(0, 0, w, h, '#22261a');
    speckle(P, w, h, top, [52, 58, 38], 1300, 4);
    speckle(P, w, h, top, [70, 60, 40], 300, 3);
    trees(P, w, top, [50, 42, 34], [34, 46, 28]);
    for (let i = 0; i < 26; i++) {  // roots
      let x = P.R() * w, y = top + P.R() * (h - top);
      for (let k = 0; k < 30; k++) { P.rect(x, y, 3, 2, '#3e3224'); x += P.R() * 4 - 1; y += P.R() * 2 - 1; }
    }
    for (let i = 0; i < 80; i++) {  // brambles at the edges
      const x = P.R() < 0.5 ? P.R() * pad[0] * 1.5 : w - P.R() * pad[2] * 1.5, y = top + P.R() * (h - top);
      P.g.fillStyle = rgb([46, 60, 34], 0.7 + P.R() * 0.5); P.g.beginPath(); P.g.arc(x, y, 6 + P.R() * 8, 0, 7); P.g.fill();
      P.rect(x, y - 6, 1, 3, '#d8d0c0');
    }
    vignette(P, w, h, 0.65, '4,8,4');
    return { canvas: P.cv, candles: [], windows: [], tint: 0xa0b088, fog: 0x2a3a22 };
  },

  lab(w, h, pad) {  // a ruined laboratory: checked tiles, shelves of flasks, scorch marks
    const P = setup(w, h, 23), top = pad[1];
    P.rect(0, 0, w, h, '#1e1c22');
    tiles(P, w, h, top, [64, 60, 58], [52, 50, 52], 22);
    stoneWall(P, w, top, [56, 52, 58]);
    for (let x = 30; x < w - 30; x += 70) {  // shelves of flasks along the wall
      P.rect(x, 18, 56, 3, '#5a3a24'); P.rect(x, 40, 56, 3, '#5a3a24');
      for (let k = 0; k < 6; k++) { const c = ['#8be04e', '#4aa0e0', '#e05a2a', '#c8c060'][(x + k) % 4]; P.rect(x + 3 + k * 9, 30, 5, 10, c); P.rect(x + 4 + k * 9, 27, 3, 3, '#c8d0d8'); }
    }
    for (let i = 0; i < 9; i++) { P.g.fillStyle = 'rgba(10,8,8,0.35)'; P.g.beginPath(); P.g.arc(80 + P.R() * (w - 160), top + 50 + P.R() * 320, 14 + P.R() * 20, 0, 7); P.g.fill(); }
    P.rect(70, top + 120, 60, 26, '#4a3424'); P.rect(w - 140, top + 220, 70, 26, '#4a3424');  // broken tables
    vignette(P, w, h);
    return { canvas: P.cv, candles: [[100, top + 110], [w - 110, top + 210], [w / 2, top + 10]], windows: [], tint: 0xc8d8b0 };
  },

  boneyard(w, h, pad) {  // a boneyard: grey dust, bones and skulls, tilted headstones
    const P = setup(w, h, 29), top = pad[1];
    P.rect(0, 0, w, h, '#2e2a28');
    speckle(P, w, h, top, [72, 66, 60], 1300, 4);
    for (let i = 0; i < 140; i++) {
      const x = P.R() * w, y = top + P.R() * (h - top), L = 4 + P.R() * 8;
      P.rect(x, y, L, 2, rgb([200, 190, 170], 0.6 + P.R() * 0.3)); P.rect(x - 1, y - 1, 2, 4, '#c8bca0');
    }
    for (let x = 20; x < w; x += 46) {  // headstones along the back
      const hh = 26 + P.R() * 14, k = 0.8 + P.R() * 0.3;
      P.rect(x, top - hh + 10, 22, hh, rgb([90, 86, 92], k)); P.rect(x, top - hh + 10, 22, 2, rgb([110, 106, 112], k));
    }
    P.rect(0, 0, w, top - 30, '#1a1820');
    ledge(P, w, top, [60, 56, 62]);
    vignette(P, w, h, 0.6);
    return { canvas: P.cv, candles: [[60, top + 10], [w - 60, top + 10]], windows: [], tint: 0xb0c0b0, fog: 0x2a3a30 };
  },

  glass(w, h, pad) {  // the hall of glass: dark polished floor, tall mirrors that catch the light
    const P = setup(w, h, 31), top = pad[1];
    P.rect(0, 0, w, h, '#14181e');
    tiles(P, w, h, top, [36, 42, 52], [30, 34, 44], 40);
    P.rect(0, 0, w, top, '#1a2028');
    for (let x = 20; x < w; x += 60) {  // mirrors
      P.rect(x, 4, 40, top - 10, '#8aa0b0'); P.rect(x + 3, 7, 34, top - 16, '#3a4a5a');
      P.g.fillStyle = 'rgba(220,240,255,0.25)'; P.g.beginPath(); P.g.moveTo(x + 6, 9); P.g.lineTo(x + 16, 9); P.g.lineTo(x + 6, top - 20); P.g.fill();
    }
    ledge(P, w, top, [40, 48, 58]);
    for (let i = 0; i < 40; i++) P.rect(P.R() * w, top + P.R() * (h - top), 2, 1, '#a0c0d0');  // shards on the floor
    vignette(P, w, h, 0.5, '6,8,14');
    return { canvas: P.cv, candles: [[50, top + 20], [w - 50, top + 20], [w / 2, h - 40]], windows: [[w * 0.25, top + 30], [w * 0.75, top + 30]], tint: 0xb8d0e0 };
  },

  wall(w, h, pad) {  // the top of a siege wall: big battlement stones, crenels, a stormy sky
    const P = setup(w, h, 37), top = pad[1];
    P.rect(0, 0, w, h, '#2a2830');
    slabs(P, w, h, top, [78, 74, 80], [44, 26, 30, 10], 0.14);
    const sky = P.g.createLinearGradient(0, 0, 0, top);
    sky.addColorStop(0, '#20263a'); sky.addColorStop(1, '#3a3e52');
    P.g.fillStyle = sky; P.g.fillRect(0, 0, w, top - 22);
    for (let x = 0; x < w; x += 40) { P.rect(x, top - 34, 24, 34, '#5e5a64'); P.rect(x, top - 34, 24, 2, '#7a7680'); }  // crenels
    ledge(P, w, top, [62, 58, 66]);
    for (let i = 0; i < 12; i++) P.rect(P.R() * w, top + P.R() * (h - top), 10 + P.R() * 14, 6, '#4a464e');  // rubble
    vignette(P, w, h, 0.5);
    return { canvas: P.cv, candles: [[80, top + 30], [w - 80, top + 30]], windows: [], tint: 0xc0c4d8 };
  },

  sanctum(w, h, pad) {  // a candlelit sanctum: pale marble, a rose window, rows of candles
    const P = setup(w, h, 41), top = pad[1];
    P.rect(0, 0, w, h, '#2a2428');
    slabs(P, w, h, top, [96, 88, 84], [34, 18, 26, 6], 0.08);
    stoneWall(P, w, top, [74, 66, 70]);
    const cx = w / 2, cy = top / 2;  // rose window
    for (let r = 26; r > 0; r -= 4) { P.g.fillStyle = ['#7a2a2a', '#94742a', '#2a4280', '#5b3a8a'][(r / 4) % 4]; P.g.beginPath(); P.g.arc(cx, cy, r, 0, 7); P.g.fill(); }
    P.rect(cx - 50, top + 30, 100, 3, '#c8a040');
    vignette(P, w, h, 0.5);
    const candles = [];
    for (let x = 60; x < w; x += 70) { candles.push([x, top + 12]); candles.push([x + 20, h - 40]); }
    return { canvas: P.cv, candles, windows: [[cx, top + 30]], tint: 0xf0d8b0 };
  },

  throne(w, h, pad) {  // the throne room: a long violet carpet, gilt pillars, the empty throne
    const P = setup(w, h, 43), top = pad[1];
    P.rect(0, 0, w, h, '#1e1a24');
    slabs(P, w, h, top, [70, 64, 78], [32, 18, 24, 6], 0.08);
    for (let y = top + 6; y < h; y++) { P.rect(w / 2 - 34, y, 68, 1, '#3a2460'); P.rect(w / 2 - 30, y, 60, 1, '#5b3a8a'); P.rect(w / 2 - 31, y, 1, 1, '#c8a040'); P.rect(w / 2 + 30, y, 1, 1, '#c8a040'); }
    stoneWall(P, w, top, [60, 54, 70]);
    P.rect(w / 2 - 22, 8, 44, top - 6, '#5a4220'); P.rect(w / 2 - 18, 12, 36, top - 14, '#3a2460'); P.rect(w / 2 - 26, top - 12, 52, 10, '#c8a040');  // the throne
    for (const x of [w * 0.15, w * 0.35, w * 0.65, w * 0.85]) { P.rect(x - 8, 0, 16, top + 6, '#8a6a30'); P.rect(x - 8, 0, 3, top + 6, '#c8a050'); }
    for (const x of [w * 0.25, w * 0.75]) { P.rect(x - 10, 4, 20, 40, '#5b3a8a'); P.rect(x - 10, 40, 20, 4, '#c8a040'); }  // banners
    vignette(P, w, h, 0.55);
    return { canvas: P.cv, candles: [[w * 0.15, top + 14], [w * 0.35, top + 14], [w * 0.65, top + 14], [w * 0.85, top + 14]], windows: [[w / 2, top + 40]], tint: 0xd8c8f0 };
  },

  bridge(w, h, pad) {  // the broken sky-bridge: worn stones over nothing, an eclipse overhead
    const P = setup(w, h, 47), top = pad[1];
    const sky = P.g.createLinearGradient(0, 0, 0, h);
    sky.addColorStop(0, '#120c1e'); sky.addColorStop(1, '#2a1a2e');
    P.g.fillStyle = sky; P.g.fillRect(0, 0, w, h);
    for (let i = 0; i < 80; i++) P.rect(P.R() * w, P.R() * h, 1, 1, '#c8c0d8');
    P.g.fillStyle = '#ff8a3a'; P.g.beginPath(); P.g.arc(w * 0.78, top * 0.5, 22, 0, 7); P.g.fill();  // the eclipse
    P.g.fillStyle = '#120c1e'; P.g.beginPath(); P.g.arc(w * 0.78, top * 0.5, 19, 0, 7); P.g.fill();
    const l = pad[0] - 10, r = w - pad[2] + 10;
    const Q = { ...P, g: P.g };
    P.g.save(); P.g.beginPath(); P.g.rect(l, top - 10, r - l, h - top); P.g.clip();
    slabs(Q, w, h, top - 10, [74, 66, 70], [30, 20, 22, 8], 0.12);
    P.g.restore();
    P.rect(l - 6, top - 10, 6, h - top + 10, '#3e3644'); P.rect(r, top - 10, 6, h - top + 10, '#3e3644');  // parapets
    for (let i = 0; i < 10; i++) P.rect(l + P.R() * (r - l), top + P.R() * (h - top), 18, 2, '#2a2228');  // cracks
    vignette(P, w, h, 0.45, '10,4,14');
    return { canvas: P.cv, candles: [[l + 10, top + 20], [r - 10, top + 20]], windows: [], tint: 0xffc8a0 };
  },
};

export function drawArena(key, w, h, pad) { return (ARENAS[key] || ARENAS.chapel)(w, h, pad); }
