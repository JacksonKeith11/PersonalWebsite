// The branching path for the current act, drawn and made clickable with Phaser.
import { ROWS_PER_ACT } from './data.js?v=57';
import { NODE_COLORS } from './art.js?v=57';
import { groundTile, TP } from './tiles.js?v=57';

export const MAP = { W: 640, TOP: 78, STEP: 70, COLS: 6 };
// Rows above the first: the act's rows, then (in newer runs) the campfire, then the boss.
const extra = () => (mapEnv.run && mapEnv.run.map.camp ? 1 : 0);
export const mapHeight = () => MAP.TOP * 2 + (ROWS_PER_ACT + extra()) * MAP.STEP;
export function nodePos(n) {
  if (n.id === 'boss') return { x: MAP.W / 2, y: MAP.TOP };
  if (n.id === 'camp') return { x: MAP.W / 2, y: MAP.TOP + MAP.STEP };
  return { x: 70 + n.c * 100 + n.jx, y: MAP.TOP + (ROWS_PER_ACT + extra() - n.r) * MAP.STEP + n.jy };
}
const hex = s => parseInt(s.slice(1), 16);
const lighten = (c, k) => { const r = c >> 16, g = (c >> 8) & 255, b = c & 255, f = v => Math.min(255, Math.round(v + (255 - v) * k)); return (f(r) << 16) | (f(g) << 8) | f(b); };
export const NODE_NAMES = { battle: 'Battle', elite: 'Elite battle', event: 'Unknown event', shop: 'Shop', rest: 'Campfire', boss: 'Boss' };

// run, available(), pick(node), actName, theme, leader and boss (its sprite key) are set by main.js;
// hover is the id of a node the side panel's list is pointing at.
export const mapEnv = { run: null, available: () => [], pick: () => {}, actName: '', hover: null };

export class MapScene extends Phaser.Scene {
  constructor() { super('map'); }
  create() {
    const run = mapEnv.run, H = mapHeight();
    const cam = this.cameras.main;
    cam.setBounds(0, 0, MAP.W, H);
    // the act's own ground, dimmed so the path reads on top of it, darker toward the edges
    const theme = mapEnv.theme || 'wood';
    for (let v = 0; v < 4; v++) if (!this.textures.exists(`g_${theme}_${v}`)) this.textures.addCanvas(`g_${theme}_${v}`, groundTile(theme, v));
    for (let y = 0; y < H; y += TP * 2) for (let x = 0; x < MAP.W; x += TP * 2) this.add.image(x, y, `g_${theme}_${(x / 64 * 3 + y / 64 * 5) % 4}`).setOrigin(0).setScale(2);
    this.add.rectangle(0, 0, MAP.W, H, 0x120c1a, 0.55).setOrigin(0);
    const vig = this.add.graphics();
    for (let i = 0; i < 6; i++) { vig.fillStyle(0x0a0612, 0.09); vig.fillRect(0, 0, 18 + i * 10, H); vig.fillRect(MAP.W - 18 - i * 10, 0, 18 + i * 10, H); }
    const avail = new Set(mapEnv.available().map(n => n.id));
    const visited = new Set(run.visited);
    const nodes = Object.values(run.map);
    // trails: gently curved dotted paths; walked ones gold, the ones you can take now bright and moving
    const lines = this.add.graphics(), live = [];
    const curve = (a, b) => { const mx = (a.x + b.x) / 2 + (b.y - a.y) * 0.12 * (((a.x * 7 + b.x * 3) % 3) - 1), my = (a.y + b.y) / 2; return t => ({ x: (1 - t) * (1 - t) * a.x + 2 * (1 - t) * t * mx + t * t * b.x, y: (1 - t) * (1 - t) * a.y + 2 * (1 - t) * t * my + t * t * b.y }); };
    for (const n of nodes) {
      const a = nodePos(n);
      for (const id of n.next) {
        const b = nodePos(run.map[id]), f = curve(a, b);
        const walked = visited.has(n.id) && visited.has(id);
        const next = (n.id === run.pos || (!run.pos && n.r === 0)) && avail.has(id);
        const steps = Math.floor(Math.hypot(b.x - a.x, b.y - a.y) / 9);
        if (next) { live.push({ f, steps }); continue; }
        for (let i = 3; i < steps - 2; i++) {
          const p = f(i / steps);
          lines.fillStyle(0x000000, 0.45).fillRect(Math.round(p.x) - 2, Math.round(p.y) - 1, 5, 5);
          lines.fillStyle(walked ? 0xf2c94c : 0x6a5888, walked ? 1 : 0.8).fillRect(Math.round(p.x) - 2, Math.round(p.y) - 2, 4, 4);
        }
      }
    }
    const march = this.add.graphics();
    this.events.on('update', (time) => {
      march.clear();
      const o = (time / 120) % 1;
      for (const { f, steps } of live) for (let i = 3; i < steps - 2; i++) {
        const p = f((i + o) / steps);
        march.fillStyle(0x000000, 0.5).fillRect(Math.round(p.x) - 2, Math.round(p.y) - 1, 5, 5);
        march.fillStyle(0xfff0b0, 1).fillRect(Math.round(p.x) - 2, Math.round(p.y) - 2, 4, 4);
      }
    });
    const label = this.add.text(0, 0, '', { fontFamily: '"Press Start 2P", monospace', fontSize: '10px', color: '#fff', stroke: '#000', strokeThickness: 4, align: 'center' }).setOrigin(0.5, 1).setDepth(20).setVisible(false);
    this.nodeViews = new Map();
    for (const n of nodes) {
      const p = nodePos(n), big = n.type === 'boss', camp = n.id === 'camp', r = big ? 30 : camp ? 23 : 20, on = avail.has(n.id), seen = visited.has(n.id);
      const col = hex(NODE_COLORS[n.type]), c = this.add.container(p.x, p.y).setDepth(5);
      if (on) { // a soft pulsing halo
        const glow = this.add.circle(0, 0, r + 9, 0xf2c94c, 0.35);
        c.add(glow);
        this.tweens.add({ targets: glow, scale: 1.18, alpha: 0.12, duration: 650, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
      }
      // a medallion: dark rim, the type's colour, a lit upper edge
      const g = this.add.graphics();
      const base = seen ? 0x4a3f58 : on || big || camp ? col : 0x3a2f48;
      g.fillStyle(0x000000, 0.5).fillCircle(2, 4, r + 3);
      g.fillStyle(0x120b18).fillCircle(0, 0, r + 3);
      g.fillStyle(on ? 0xf2c94c : big ? 0xc8a050 : 0x2a2234).fillCircle(0, 0, r + 1);
      g.fillStyle(base).fillCircle(0, 0, r - 1);
      g.fillStyle(lighten(base, 0.28), 0.9).slice(0, 0, r - 3, Math.PI * 1.08, Math.PI * 1.92, false).fillPath();
      g.fillStyle(base).fillCircle(0, 2, r - 5);
      c.add(g);
      if (big && mapEnv.boss) c.add(this.add.image(0, r * 0.55, 's_' + mapEnv.boss).setOrigin(0.5, 1).setScale(1.5));
      else c.add(this.add.image(0, 0, 'i_' + n.type).setScale(camp ? 3.5 : 3).setAlpha(seen ? 0.45 : on || camp ? 1 : 0.75));
      if (seen && n.id !== run.pos) { // a tick on places already passed
        const t = this.add.graphics();
        t.lineStyle(4, 0x120b18, 1).beginPath().moveTo(r * 0.25, r * 0.55).lineTo(r * 0.5, r * 0.8).lineTo(r * 0.95, r * 0.25).strokePath();
        t.lineStyle(2, 0x9ad87a, 1).beginPath().moveTo(r * 0.25, r * 0.55).lineTo(r * 0.5, r * 0.8).lineTo(r * 0.95, r * 0.25).strokePath();
        c.add(t);
      }
      const name = big ? mapEnv.bossName || 'Boss' : NODE_NAMES[n.type];
      if (big || camp) c.add(this.add.text(0, r + 6, name, { fontFamily: '"Press Start 2P", monospace', fontSize: '9px', color: big ? '#f2c94c' : '#b8e0a8', stroke: '#000', strokeThickness: 4 }).setOrigin(0.5, 0));
      c.setSize(r * 2 + 14, r * 2 + 14).setInteractive({ useHandCursor: on });
      c.on('pointerover', () => { c.setScale(on ? 1.1 : 1.03); label.setText(name + (on ? '' : seen ? '\n(passed)' : '')).setPosition(p.x, p.y - r - 10).setVisible(!(big || camp) || on); });
      c.on('pointerout', () => { c.setScale(1); label.setVisible(false); });
      if (on) c.on('pointerup', () => { if (!this.dragged) mapEnv.pick(n); });
      this.nodeViews.set(n.id, { c, p, r, name });
      if (n.id === run.pos) {
        const hero = this.add.image(p.x, p.y - r - 16, 's_' + mapEnv.leader).setScale(1.25).setDepth(6);
        this.tweens.add({ targets: hero, y: hero.y - 6, duration: 400, yoyo: true, repeat: -1, ease: 'Sine.easeInOut' });
      }
    }
    // the side panel's choice list points at nodes here
    let shown = null;
    this.events.on('update', () => {
      if (mapEnv.hover === shown) return;
      if (shown && this.nodeViews.get(shown)) this.nodeViews.get(shown).c.setScale(1);
      shown = mapEnv.hover;
      const v = shown && this.nodeViews.get(shown);
      if (v) { v.c.setScale(1.12); label.setText(v.name).setPosition(v.p.x, v.p.y - v.r - 10).setVisible(true); cam.pan(cam.scrollX + cam.width / 2, Math.max(v.p.y, cam.height / 2), 250); } else label.setVisible(false);
    });
    // the act's name on a banner that stays at the top
    const bar = this.add.graphics().setScrollFactor(0).setDepth(30);
    bar.fillStyle(0x120b18, 0.88).fillRect(0, 0, MAP.W, 34); bar.fillStyle(0xf2c94c, 0.6).fillRect(0, 34, MAP.W, 2);
    this.add.text(16, 10, mapEnv.actName, { fontFamily: '"Press Start 2P", monospace', fontSize: '14px', color: '#f2c94c', stroke: '#000', strokeThickness: 4 }).setScrollFactor(0).setDepth(31);
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
