// Each boss's arena, drawn by code onto a canvas, pixel by pixel, in the same matte palette as the
// sprites (docs/game-art.md). Walls and floor are one texture; candles and window light are separate
// so they can flicker. Returns where the lights are.

function rng(seed) {
  let s = seed >>> 0;
  return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; };
}
const hex = (r, g, b) => `rgb(${r | 0},${g | 0},${b | 0})`;
const shade = ([r, g, b], k) => hex(r * k, g * k, b * k);

export function drawChapel(w, h, pad) {
  const cv = document.createElement('canvas');
  cv.width = w; cv.height = h;
  const g = cv.getContext('2d');
  const R = rng(7);
  const px = (x, y, c, ww = 1, hh = 1) => { g.fillStyle = c; g.fillRect(x | 0, y | 0, ww, hh); };
  const top = pad[1];

  // floor: irregular flagstones
  g.fillStyle = '#211d26'; g.fillRect(0, 0, w, h);
  const rowsH = [];
  for (let y = top; y < h;) { const hh = 22 + Math.floor(R() * 8); rowsH.push([y, hh]); y += hh; }
  for (const [y, hh] of rowsH) {
    let x = -Math.floor(R() * 30);
    while (x < w) {
      const ww = 28 + Math.floor(R() * 22);
      const k = 0.92 + R() * 0.1;
      const base = [60 * k, 55 * k, 64 * k];
      g.fillStyle = shade(base, 1); g.fillRect(x + 1, y + 1, ww - 2, hh - 2);
      g.fillStyle = shade(base, 1.06); g.fillRect(x + 1, y + 1, ww - 2, 1);
      g.fillStyle = shade(base, 0.86); g.fillRect(x + 1, y + hh - 2, ww - 2, 1);
      // wear: speckles, a crack now and then, moss in the seams
      for (let i = 0; i < 10; i++) px(x + 2 + R() * (ww - 4), y + 2 + R() * (hh - 4), shade(base, 0.9 + R() * 0.14));
      if (R() < 0.14) {
        let cx = x + 4 + R() * (ww - 8), cy = y + 2;
        g.fillStyle = shade(base, 0.78);
        for (let k = 0; k < hh - 4; k++) { g.fillRect(cx | 0, cy + k, 1, 1); cx += R() < 0.5 ? -1 : 1; }
      }
      if (R() < 0.18) for (let i = 0; i < 5; i++) px(x + R() * ww, y + hh - 1 - R() * 2, R() < 0.5 ? '#4e5a3e' : '#3e4a32');
      x += ww;
    }
  }
  // pale light pooled under each window
  for (const wx of [w * 0.2, w * 0.5, w * 0.8]) {
    const lg = g.createRadialGradient(wx + 20, top + 110, 4, wx + 20, top + 110, 120);
    lg.addColorStop(0, 'rgba(170,180,230,0.10)'); lg.addColorStop(1, 'rgba(170,180,230,0)');
    g.fillStyle = lg; g.fillRect(wx - 120, top, 280, 260);
  }
  // a torn red runner from the altar down the nave
  const cx = w / 2;
  for (let y = top + 10; y < h - 30; y++) {
    const torn = (y % 53 < 2 && R() < 0.35) || R() < 0.006;
    if (torn) continue;
    const half = 30 + (R() < 0.08 ? -2 : 0);
    g.fillStyle = '#3e1a1e'; g.fillRect(cx - half, y, half * 2, 1);
    g.fillStyle = '#52222a'; g.fillRect(cx - half + 3, y, half * 2 - 6, 1);
    g.fillStyle = '#7a6430'; g.fillRect(cx - half + 3, y, 1, 1); g.fillRect(cx + half - 4, y, 1, 1);
    if (R() < 0.04) { g.fillStyle = '#4a181c'; g.fillRect(cx - half + R() * half * 2, y, 3 + R() * 6, 1); }
  }

  // back wall: stone courses, three tall windows with dim stained glass, buttresses between
  for (let y = 0; y < top; y += 9) {
    const off = (y / 9) % 2 ? 0 : 10;
    for (let x = -off; x < w; x += 20) {
      const b = [56 + R() * 10, 50 + R() * 8, 62 + R() * 10];
      g.fillStyle = shade(b, 1); g.fillRect(x + 1, y + 1, 18, 7);
      g.fillStyle = shade(b, 1.15); g.fillRect(x + 1, y + 1, 18, 1);
      g.fillStyle = shade(b, 0.75); g.fillRect(x + 1, y + 7, 18, 1);
    }
  }
  const glass = ['#7a2a2a', '#2a4280', '#94742a', '#3a5a3a', '#5b3a8a'];
  for (const wx of [w * 0.2, w * 0.5, w * 0.8]) {
    const ww = 34, wy = 6, wh = top - 18;
    g.fillStyle = '#18141c'; g.fillRect(wx - ww / 2 - 3, wy, ww + 6, wh + 3);
    for (let y = 0; y < wh; y++) {
      const arch = y < ww / 2 ? Math.round(Math.sqrt(Math.max(0, (ww / 2) ** 2 - (ww / 2 - y) ** 2))) : ww / 2;
      for (let x = -arch; x < arch; x++) {
        const cell = (Math.floor((x + 40) / 6) + Math.floor(y / 7)) % glass.length;
        const lead = (x + 40) % 6 === 0 || y % 7 === 0 || x === 0;
        px(wx + x, wy + 2 + y, lead ? '#141018' : glass[cell]);
      }
    }
    g.fillStyle = '#8a8478'; g.fillRect(wx - ww / 2 - 4, wy + wh + 2, ww + 8, 3);
  }
  for (const bx of [w * 0.35, w * 0.65, w * 0.05, w * 0.95]) {
    g.fillStyle = '#3e3844'; g.fillRect(bx - 9, 0, 18, top);
    g.fillStyle = '#4e4854'; g.fillRect(bx - 9, 0, 2, top);
    g.fillStyle = '#2a2530'; g.fillRect(bx + 7, 0, 2, top);
  }
  // the wall's foot: a ledge and its shadow on the floor
  g.fillStyle = '#4a4450'; g.fillRect(0, top - 4, w, 4);
  g.fillStyle = '#5e5864'; g.fillRect(0, top - 4, w, 1);
  for (let i = 0; i < 10; i++) { g.fillStyle = `rgba(10,6,14,${0.45 - i * 0.045})`; g.fillRect(0, top + i, w, 1); }

  // the altar against the wall, cloth hanging off it
  g.fillStyle = '#6a6270'; g.fillRect(cx - 40, top - 22, 80, 26);
  g.fillStyle = '#7e7684'; g.fillRect(cx - 40, top - 22, 80, 3);
  g.fillStyle = '#4a4450'; g.fillRect(cx - 40, top + 2, 80, 2);
  g.fillStyle = '#c8c0aa'; g.fillRect(cx - 28, top - 19, 56, 16);
  g.fillStyle = '#948c78'; for (let x = cx - 28; x < cx + 28; x += 4) g.fillRect(x, top - 4, 2, 3);
  g.fillStyle = '#a88a40'; g.fillRect(cx - 2, top - 34, 4, 14); g.fillRect(cx - 7, top - 30, 14, 3);

  // rubble and fallen stones along the sides; darkness at the edges
  for (let i = 0; i < 70; i++) {
    const side = R() < 0.5, x = side ? R() * pad[0] * 1.3 : w - R() * pad[2] * 1.3, y = top + R() * (h - top);
    const s = 2 + R() * 6, b = [70 + R() * 20, 64 + R() * 16, 74 + R() * 18];
    g.fillStyle = shade(b, 0.7); g.fillRect(x, y + 1, s, s * 0.7);
    g.fillStyle = shade(b, 1); g.fillRect(x, y, s - 1, s * 0.6);
  }
  // broken pews, toppled along both walls
  for (const [x, y, flip] of [[18, top + 70, 0], [w - 70, top + 150, 1], [22, top + 250, 1], [w - 66, top + 300, 0]]) {
    g.fillStyle = '#3a2618'; g.fillRect(x, y + 6, 48, 6);
    g.fillStyle = '#5a3a24'; g.fillRect(x, y, 48, 7); g.fillRect(flip ? x + 40 : x, y - 10, 6, 12);
    g.fillStyle = '#6a4a2e'; g.fillRect(x, y, 48, 1);
    g.fillStyle = '#2a1a12'; for (let k = 6; k < 48; k += 9) g.fillRect(x + k, y + 1, 1, 5);
  }
  const vg = g.createRadialGradient(w / 2, h * 0.55, h * 0.35, w / 2, h * 0.55, w * 0.62);
  vg.addColorStop(0, 'rgba(8,4,12,0)'); vg.addColorStop(1, 'rgba(8,4,12,0.55)');
  g.fillStyle = vg; g.fillRect(0, 0, w, h);

  const candles = [];
  for (const [x, y] of [[cx - 34, top - 22], [cx + 34, top - 22], [cx - 20, top - 22], [cx + 20, top - 22],
    [80, top + 30], [w - 80, top + 30], [70, h - 70], [w - 70, h - 70]]) candles.push([x, y]);
  const windows = [[w * 0.2, top + 40], [w * 0.5, top + 40], [w * 0.8, top + 40]];
  return { canvas: cv, candles, windows };
}
