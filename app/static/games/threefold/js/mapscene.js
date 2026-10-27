// The branching path for the current act, drawn and made clickable with Phaser.
import { ROWS_PER_ACT } from './data.js?v=20';
import { NODE_COLORS } from './art.js?v=20';
import { groundTile, TP } from './tiles.js?v=20';

export const MAP = { W: 640, TOP: 70, STEP: 70, COLS: 6 };
export const mapHeight = () => MAP.TOP * 2 + ROWS_PER_ACT * MAP.STEP;
export function nodePos(n) {
  if (n.id === 'boss') return { x: MAP.W / 2, y: MAP.TOP };
  return { x: 70 + n.c * 100 + n.jx, y: MAP.TOP + (ROWS_PER_ACT - n.r) * MAP.STEP + n.jy };
}
const hex = s => parseInt(s.slice(1), 16);

// run, available(), pick(node), actName and leader are set by main.js.
export const mapEnv = { run: null, available: () => [], pick: () => {}, actName: '' };

export class MapScene extends Phaser.Scene {
  constructor() { super('map'); }
  create() {
    const run = mapEnv.run, H = mapHeight();
    const cam = this.cameras.main;
    cam.setBounds(0, 0, MAP.W, H);
    // the act's own ground, dimmed so the path reads on top of it
    const theme = mapEnv.theme || 'wood';
    for (let v = 0; v < 4; v++) if (!this.textures.exists(`g_${theme}_${v}`)) this.textures.addCanvas(`g_${theme}_${v}`, groundTile(theme, v));
    for (let y = 0; y < H; y += TP * 2) for (let x = 0; x < MAP.W; x += TP * 2) this.add.image(x, y, `g_${theme}_${(x / 64 * 3 + y / 64 * 5) % 4}`).setOrigin(0).setScale(2);
    this.add.rectangle(0, 0, MAP.W, H, 0x120c1a, 0.62).setOrigin(0);
    const avail = new Set(mapEnv.available().map(n => n.id));
    const visited = new Set(run.visited);
    const nodes = Object.values(run.map);
    const lines = this.add.graphics();
    for (const n of nodes) {
      const a = nodePos(n);
      for (const id of n.next) {
        const b = nodePos(run.map[id]);
        const walked = visited.has(n.id) && visited.has(id);
        const next = (n.id === run.pos || (!run.pos && n.r === 0)) && avail.has(id);
        lines.fillStyle(walked ? 0xf2c94c : next ? 0xc8b8e0 : 0x4d3c66);
        const steps = Math.floor(Math.hypot(b.x - a.x, b.y - a.y) / 10);
        for (let i = 2; i < steps - 1; i++) lines.fillRect(Math.round(a.x + (b.x - a.x) * i / steps) - 2, Math.round(a.y + (b.y - a.y) * i / steps) - 2, 4, 4);
      }
    }
    for (const n of nodes) {
      const p = nodePos(n), big = n.type === 'boss', r = big ? 28 : 20, on = avail.has(n.id);
      const c = this.add.container(p.x, p.y);
      if (on) {
        const glow = this.add.rectangle(0, 0, r * 2 + 14, r * 2 + 14, 0xf2c94c);
        c.add(glow);
        this.tweens.add({ targets: glow, scale: 1.12, alpha: 0.6, duration: 500, yoyo: true, repeat: -1 });
      }
      c.add(this.add.rectangle(0, 0, r * 2 + 6, r * 2 + 6, 0x000000));
      c.add(this.add.rectangle(0, 0, r * 2, r * 2, visited.has(n.id) || on || big ? hex(NODE_COLORS[n.type]) : 0x3a2f48));
      c.add(this.add.image(0, 0, 'i_' + n.type).setScale(big ? 4 : 3).setAlpha(visited.has(n.id) ? 0.45 : on || big ? 1 : 0.7));
      if (on) {
        c.setSize(r * 2 + 14, r * 2 + 14).setInteractive({ useHandCursor: true });
        c.on('pointerup', ptr => { if (!this.dragged) mapEnv.pick(n); });
        c.on('pointerover', () => c.setScale(1.08));
        c.on('pointerout', () => c.setScale(1));
      }
      if (n.id === run.pos) {
        const hero = this.add.image(p.x, p.y - r - 18, 's_' + mapEnv.leader).setScale(1.25).setDepth(5);
        this.tweens.add({ targets: hero, y: hero.y - 6, duration: 400, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
      }
    }
    this.add.text(16, 12, mapEnv.actName, { fontFamily: '"Press Start 2P", monospace', fontSize: '14px', color: '#f2c94c', stroke: '#000', strokeThickness: 4 });
    // drag or wheel to scroll; a drag doesn't count as a click
    let startY = 0, startScroll = 0;
    this.input.on('pointerdown', p => { startY = p.y; startScroll = cam.scrollY; this.dragged = false; });
    this.input.on('pointermove', p => {
      if (!p.isDown) return;
      if (Math.abs(p.y - startY) > 8) this.dragged = true;
      if (this.dragged) cam.scrollY = startScroll - (p.y - startY);
    });
    this.input.on('wheel', (p, objs, dx, dy) => { cam.scrollY += dy * 0.5; });
    const first = [...avail][0];
    if (first) cam.scrollY = nodePos(run.map[first]).y - cam.height * 0.65;
  }
}
