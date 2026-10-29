// The base class every minigame's browser half extends: drawing helpers, and what the stage
// calls (snap, key, pointer, draw, end).

import * as sfx from './audio.js?v=2';

export const TEAM_COLORS = ['#ff8a3d', '#5fb0ff'];

export class Game {
  constructor(stage) {
    this.s = stage;
    this.c = stage.c;
    this.params = stage.info.params || {};
    this.me = stage.you;
    this.playing = stage.info.ids.includes(stage.you);
    this.ids = stage.info.ids;
    this.sentDone = false;
  }
  get W() { return this.s.W; }
  get H() { return this.s.H; }
  get t() { return this.s.t; }
  player(id) { return this.s.players[id] || { name: '?', color: '#888' }; }
  send(m) { this.s.send(m); }
  sound(n) { sfx.play(n); }
  done(v) { if (!this.sentDone && this.playing) { this.sentDone = true; this.send({ t: 'done', v }); } }
  prog(v) { if (this.playing) this.send({ t: 'prog', v }); }
  // hooks
  snap() {}
  key() {}
  pointer() {}
  draw() {}
  end() {}

  text(str, x, y, size = 20, color = '#fff', align = 'center', weight = 700) {
    const c = this.c;
    c.font = `${weight} ${size}px "Source Sans 3", system-ui, sans-serif`;
    c.textAlign = align;
    c.textBaseline = 'middle';
    c.fillStyle = color;
    c.fillText(str, x, y);
  }

  title(str, x, y, size = 30, color = '#fff') {
    const c = this.c;
    c.font = `700 ${size}px "Source Serif 4", Georgia, serif`;
    c.textAlign = 'center';
    c.textBaseline = 'middle';
    c.lineWidth = 5;
    c.lineJoin = 'round';
    c.strokeStyle = 'rgba(0,0,0,0.6)';
    c.strokeText(str, x, y);
    c.fillStyle = color;
    c.fillText(str, x, y);
  }

  button(r, label, { color = '#3a2a52', text = '#fff', size = 22, on = false } = {}) {
    const c = this.c;
    c.fillStyle = on ? '#ffe066' : color;
    c.beginPath(); c.roundRect(r.x, r.y, r.w, r.h, 12); c.fill();
    c.strokeStyle = 'rgba(255,255,255,0.3)';
    c.lineWidth = 2;
    c.stroke();
    this.text(label, r.x + r.w / 2, r.y + r.h / 2 + 1, size, on ? '#1a1020' : text);
  }

  // Everyone's progress, as a strip of rows: [{id, text, frac}]
  board(rows, x, y, w, rowH = 30) {
    const c = this.c;
    rows.forEach((r, i) => {
      const p = this.player(r.id);
      const yy = y + i * rowH;
      c.fillStyle = r.id === this.me ? 'rgba(255,224,102,0.18)' : 'rgba(255,255,255,0.06)';
      c.fillRect(x, yy, w, rowH - 4);
      if (r.frac != null) {
        c.fillStyle = p.color;
        c.globalAlpha = 0.45;
        c.fillRect(x, yy, w * Math.max(0, Math.min(1, r.frac)), rowH - 4);
        c.globalAlpha = 1;
      }
      c.fillStyle = p.color;
      c.beginPath(); c.arc(x + 12, yy + (rowH - 4) / 2, 7, 0, Math.PI * 2); c.fill();
      this.text(p.name, x + 26, yy + (rowH - 4) / 2, 15, '#fff', 'left', 600);
      this.text(r.text || '', x + w - 8, yy + (rowH - 4) / 2, 15, '#ffe9b8', 'right', 700);
    });
  }

  // Layout: the play area, and the scoreboard of everyone's progress beside it (or below it on
  // a tall screen). Someone watching gets the scoreboard alone, in the middle.
  get portrait() { return this.H > this.W * 1.1; }
  sideH() { return 40 + this.ids.length * 32; }
  area() {
    const top = 48;
    if (this.portrait) return { x: 0, y: top, w: this.W, h: this.H - top - this.sideH() - 10 };
    return { x: 0, y: top, w: this.W * 0.7, h: this.H - top };
  }
  cx() { const a = this.area(); return a.x + a.w / 2; }
  side() {
    if (!this.playing) { const w = Math.min(500, this.W - 32); return { x: (this.W - w) / 2, y: 70, w }; }
    if (this.portrait) return { x: 16, y: this.H - this.sideH(), w: this.W - 32 };
    return { x: this.W * 0.72, y: 60, w: this.W * 0.26 };
  }
  sideBoard(title, rows) {
    const s = this.side();
    this.text(title, s.x + s.w / 2, s.y + 10, 15, '#cbbfe0');
    this.board(rows, s.x, s.y + 26, s.w, 32);
  }

  hit(r, x, y) { return x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h; }
}
