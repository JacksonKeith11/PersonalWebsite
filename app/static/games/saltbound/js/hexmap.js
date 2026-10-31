// The hex map, drawn by Phaser: painted pixel terrain (repainted when the sea or tide changes), the
// places, enemies and heroes standing on it, fog, flood warnings, reachable hexes and planned routes.
// Everything else on screen is HTML.
import { W, H, terrain, visibleTiles } from './rules.js?v=1';
import { spriteCanvas, placeCanvas } from './art.js?v=1';

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
function groundPixel(kind, x, y, depth) {
  const n = hash(x, y), n2 = hash(x >> 2, y >> 2);
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
  mound: { pal: { h: '#56603a', H: '#7d8a4e', L: '#9aa866', D: '#68743f' }, rows: [
    '.....hhhhh......', '...hhHHLHHhh....', '..hHHLLHHHHHh...', '.hHLLHHHHHHDDh..', 'hHHHHHHHHHDDDDh.'] },
  rock: { pal: { k: '#4a4640', R: '#8f8a82', L: '#b2ada4', D: '#6e6a62' }, rows: [
    '...kkk....', '..kLLRk...', '.kLLRRRk..', '.kLRRRDDk.', 'kRRRRDDDDk', 'kkkkkkkkkk'] },
  snowrock: { pal: { k: '#4a4640', R: '#8f8a82', W: '#e8ecef', D: '#6e6a62' }, rows: [
    '....k.....', '...kWk....', '..kWWRk...', '.kWRRRDk..', 'kRRRRDDDk.', 'kkkkkkkkk.'] },
  house: { pal: { k: '#2a1e1a', r: '#a84a3a', R: '#7a3428', w: '#e0d4b8', W: '#b8a888', d: '#4a3020', y: '#ffd870' }, rows: [
    '...kkk...', '..krrrk..', '.krrrrrk.', 'kRRRRRRRk', '.kwwwwwk.', '.kwdwywk.', '.kwdwwWk.', '.kkkkkkk.'] },
  dock: { pal: { k: '#2a1e1a', w: '#8a6a44', W: '#6a4e30' }, rows: ['kkkkkkkk', 'wwwwwwww', 'WkWWkWWk', '.k..k..k'] },
};
function stamp(img, s, x0, y0) {
  const { pal, rows } = STAMPS[s];
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

export function paintTerrain(canvas, world, game) {
  const ctx = canvas.getContext('2d');
  const img = ctx.createImageData(MAP_W, MAP_H);
  const own = owners();
  const kinds = new Array(W * H);
  for (let t = 0; t < W * H; t++) kinds[t] = terrain(world, game, t);
  const water = t => t < 0 || kinds[t] === 'deep';
  for (let y = 0; y < MAP_H; y++) for (let x = 0; x < MAP_W; x++) {
    const p = y * MAP_W + x, t = own[p];
    let c;
    if (t < 0) c = PAL.deep[0];
    else {
      const k = kinds[t];
      c = groundPixel(k, x, y, game.sea - world.elev[t]);
      if (k === 'deep') {
        // foam where water meets land
        let near = 99;
        for (const [dx, dy, d] of [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1], [2, 0, 2], [-2, 0, 2], [0, 2, 2], [0, -2, 2]]) {
          const X = x + dx, Y = y + dy;
          if (X < 0 || Y < 0 || X >= MAP_W || Y >= MAP_H) continue;
          const o = own[Y * MAP_W + X];
          if (o >= 0 && !water(o)) near = Math.min(near, d);
        }
        if (near === 1) c = PAL.foam; else if (near === 2) c = PAL.foam2;
      }
      // a faint line where hexes meet
      const r = x + 1 < MAP_W ? own[p + 1] : t, d = y + 1 < MAP_H ? own[p + MAP_W] : t;
      if (r !== t || d !== t) {
        const f = k === 'deep' ? 0.92 : 0.84;
        c = [c[0] * f, c[1] * f, c[2] * f];
      }
    }
    const i = p * 4;
    img.data[i] = c[0]; img.data[i + 1] = c[1]; img.data[i + 2] = c[2]; img.data[i + 3] = 255;
  }
  // props, top to bottom
  for (let t = 0; t < W * H; t++) {
    const k = kinds[t], [cx, cy] = center(t);
    const r = hash(t, 7), r2 = hash(t, 13);
    const coast = k !== 'deep' && world.elev[t] <= game.sea + 3;
    if (k === 'forest') {
      const spots = [[-12, -14], [4, -16], [-4, -4], [10, -4], [-14, 4], [2, 6]];
      for (let i = 0; i < spots.length; i++) if (hash(t, i) > 0.25) stamp(img, coast && hash(t, i + 9) > 0.5 ? 'palm' : 'tree', cx + spots[i][0] - 5, cy + spots[i][1] - 4);
    } else if (k === 'hills') {
      stamp(img, 'mound', cx - 14 + (r * 6 | 0), cy - 10); stamp(img, 'mound', cx - 4 + (r2 * 6 | 0), cy + 2);
    } else if (k === 'peak') {
      stamp(img, world.elev[t] >= 17 ? 'snowrock' : 'rock', cx - 12 + (r * 4 | 0), cy - 12); stamp(img, 'rock', cx + (r2 * 4 | 0), cy - 2);
      if (r > 0.5) stamp(img, 'rock', cx - 10, cy + 6);
    } else if (k === 'grass' && r > 0.78) {
      stamp(img, 'tree', cx - 5 + (r2 * 16 - 8 | 0), cy - 8);
    } else if (k === 'beach' && r > 0.82) {
      stamp(img, 'palm', cx - 5 + (r2 * 12 - 6 | 0), cy - 8);
    } else if (k === 'town') {
      stamp(img, 'house', cx - 16, cy - 12); stamp(img, 'house', cx + 2, cy - 14); stamp(img, 'house', cx - 6, cy);
    }
  }
  ctx.putImageData(img, 0, 0);
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
    this.gFloods = scene.add.graphics();
    this.gReach = scene.add.graphics();
    this.layerPlaces = scene.add.container();
    this.gPaths = scene.add.graphics();
    this.layerUnits = scene.add.container();
    this.gFog = scene.add.graphics();
    this.gHover = scene.add.graphics();
    const cam = scene.cameras.main;
    cam.setBounds(-400, -300, MAP_W + 800, MAP_H + 600);
    cam.setZoom(this.zoom);
    scene.tweens.add({ targets: this.gFloods, alpha: { from: 1, to: 0.45 }, duration: 900, yoyo: true, repeat: -1 });
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
    this.ready = true;
    if (this.pending) { const [g, o] = this.pending; this.pending = null; this.setState(g, o); }
  }

  tick() {}

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
      paintTerrain(this.canvas, this.world, game);
      this.tex.refresh();
      this.paintedKey = key;
    }
    if (this.centerPending !== undefined) { this.centerOn(this.centerPending, false); this.centerPending = undefined; }
    this.drawFloods(); this.drawReach(); this.drawPlaces(); this.drawPaths(); this.drawUnits(); this.drawFog(); this.drawHover();
  }

  drawFloods() {
    const g = this.gFloods; g.clear();
    for (const t of this.state.floods || []) {
      if (this.state.seen[t] !== '1') continue;
      g.fillStyle(0x6aa2d8, 0.28); g.fillPoints(hexPoints(t, 2), true);
      g.lineStyle(1, 0x9ccbf0, 0.7); g.strokePoints(hexPoints(t, 2), true);
    }
  }

  drawReach() {
    const g = this.gReach; g.clear();
    const r = this.opts?.reach;
    if (!r) return;
    for (const [t] of r.best) {
      if (t === this.state.heroes[this.opts.sel]?.tile) continue;
      g.fillStyle(0xc9a24a, 0.13); g.fillPoints(hexPoints(t, 3), true);
      g.lineStyle(1, 0xc9a24a, 0.45); g.strokePoints(hexPoints(t, 3), true);
    }
  }

  drawPlaces() {
    const L = this.layerPlaces; L.removeAll(true);
    for (const [t, p] of Object.entries(this.state.places)) {
      const [cx, cy] = center(+t);
      const kind = p.kind === 'dungeon' && this.state.cleared.includes(p.region) ? 'dungeon' : p.kind;
      const tex = this.texFor('place_' + kind, () => placeCanvas(kind));
      const yoff = p.kind === 'town' ? 14 : 2;
      const img = this.scene.add.image(cx, cy + yoff, tex).setOrigin(0.5, 0.5);
      if (p.kind === 'town') img.setVisible(false);
      if (p.done || (p.kind === 'dungeon' && this.state.cleared.includes(p.region))) img.setAlpha(0.45);
      if (p.kind === 'peak' && this.state.cleared.length < 3) img.setTint(0x8a8a8a);
      L.add(img);
      if (p.kind === 'town' && p.docks) {
        // a small flag marks docks
        const fl = this.scene.add.rectangle(cx + 18, cy - 14, 2, 10, 0x2a1e1a).setOrigin(0.5, 1);
        const cloth = this.scene.add.rectangle(cx + 19, cy - 24, 7, 5, 0xc9a24a).setOrigin(0, 0);
        L.add(fl); L.add(cloth);
      }
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
        if (gr.foes.length > 1 || gr.lair) {
          const badge = this.scene.add.circle(13, -12, 7, gr.lair ? 0x6a1d2a : 0x10161f).setStrokeStyle(1, 0xd0624f);
          const txt = this.scene.add.text(13, -12, String(gr.foes.length), { fontFamily: 'Inter', fontSize: '10px', fontStyle: 'bold', color: '#ffd8cc', resolution: 4 }).setOrigin(0.5);
          c.add([badge, txt]);
        }
        L.add(c);
        tok = { c, tile: gr.tile, kind: 'g' };
        this.tokens.set(id, tok);
      } else if (tok.tile !== gr.tile && !tok.moving) {
        tok.c.setPosition(cx, cy); tok.tile = gr.tile;
      }
    }
    // heroes, spread out when sharing a hex
    const byTile = {};
    st.heroes.forEach((hero, h) => { if (hero.alive) (byTile[hero.tile] ||= []).push(h); });
    st.heroes.forEach((hero, h) => {
      const id = 'h' + h;
      if (!hero.alive) { const t = this.tokens.get(id); if (t) { t.c.destroy(); this.tokens.delete(id); } return; }
      seen.add(id);
      const mates = byTile[hero.tile], k = mates.indexOf(h), n = mates.length;
      const [cx0, cy] = center(hero.tile), cx = cx0 + (k - (n - 1) / 2) * 14;
      let tok = this.tokens.get(id);
      if (!tok) {
        const c = this.scene.add.container(cx, cy);
        const ring = this.scene.add.ellipse(0, 12, 24, 9, SEATS[h], 0.85);
        const ring2 = this.scene.add.ellipse(0, 12, 18, 6, 0x0b1017, 0.6);
        const boat = this.scene.add.image(0, 16, this.texFor('boat', boatCanvas)).setOrigin(0.5, 1).setVisible(false);
        const img = this.scene.add.image(0, 14, this.texFor('spr_' + hero.cls, () => spriteCanvas(hero.cls))).setOrigin(0.5, 1);
        c.add([ring, ring2, img, boat]);
        L.add(c);
        tok = { c, tile: hero.tile, boat, ring, kind: 'h', x: cx };
        this.tokens.set(id, tok);
      } else if (!tok.moving && (tok.tile !== hero.tile || tok.x !== cx)) {
        tok.c.setPosition(cx, cy); tok.tile = hero.tile; tok.x = cx;
      }
      tok.boat.setVisible(hero.afloat);
      tok.ring.setVisible(!hero.afloat);
      tok.c.setDepth(cy);
      const sel = this.opts?.sel === h;
      tok.c.setScale(1);
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
  playMove(id, path, speed = 1) {
    const tok = this.tokens.get(id);
    if (!tok || !path || path.length < 2) return Promise.resolve();
    tok.moving = true;
    const pts = path.slice(1).map(center);
    return new Promise(res => {
      this.scene.tweens.chain({
        targets: tok.c,
        tweens: pts.map(([x, y]) => ({ x, y, duration: 200 / speed, ease: 'Sine.easeInOut' })),
        onComplete: () => { tok.moving = false; tok.tile = path[path.length - 1]; res(); this.drawUnits(); },
      });
    });
  }

  destroy() { this.game.destroy(true); }
}

function boatCanvas() {
  const c = document.createElement('canvas'); c.width = 28; c.height = 8;
  const x = c.getContext('2d');
  const rows = ['.kkkkkkkkkkkkkkkkkkkkkkkkk..', 'kwwwwwwwwwwwwwwwwwwwwwwwwwk.', '.kWWWWWWWWWWWWWWWWWWWWWWWk..', '..kWWWWWWWWWWWWWWWWWWWWWk...', '...kkkkkkkkkkkkkkkkkkkkk....'];
  const pal = { k: '#2a1e1a', w: '#a07a4a', W: '#7a5a34' };
  rows.forEach((r, y) => [...r].forEach((ch, X) => { if (pal[ch]) { x.fillStyle = pal[ch]; x.fillRect(X, y + 3, 1, 1); } }));
  return c;
}
