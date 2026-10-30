// Draws Haunted Hollow: the night, the graveyard scenery, the paths and spaces, the crown, the
// ghost, traps, webs, coin piles and everyone's pieces. Pieces glide from space to space; the
// dice and floating "+3"s are drawn over the top.

import * as art from './art.js?v=6';

const KIND_COLORS = {
  blue: ['#3f7fe0', '#1d4a99'],
  red: ['#d8403a', '#7d1a17'],
  event: ['#9b4fd1', '#4e1f75'],
  shop: ['#f0a030', '#8a5300'],
  item: ['#34b38a', '#11634a'],
  duel: ['#c9c9d6', '#5b5b70'],
  portal: ['#2fd1d1', '#0d5f6b'],
};
const SPACE_R = 22;
// one colour per way at a fork, matching the dots on the choice buttons
export const ROUTE_COLORS = ['#ffe066', '#6fe8ff', '#ff8adf'];

export class Board {
  constructor(canvas, board, { onPick } = {}) {
    this.cv = canvas;
    this.c = canvas.getContext('2d');
    this.b = board;
    this.onPick = onPick;
    this.st = null;
    this.you = null;
    this.tokens = new Map();  // id -> {x, y}
    this.ghost = null;
    this.floats = [];  // {x, y, text, color, t}
    this.dice = null;  // {values, t, rolling}
    this.shake = 0;
    this.bombs = [];
    this.scale = 1;
    this.ox = 0;
    this.oy = 0;
    this.bg = null;
    this.t = 0;
    canvas.addEventListener('pointerdown', e => this.click(e));
    canvas.addEventListener('pointermove', e => { this.hover = this.pickAt(e); });
    canvas.addEventListener('pointerleave', () => { this.hover = null; });
    this.hover = null;  // the fork choice being pointed at, here or on its button
    new ResizeObserver(() => this.resize()).observe(canvas.parentElement);
    this.resize();
  }

  resize() {
    const wrap = this.cv.parentElement;
    const w = wrap.clientWidth, h = wrap.clientHeight;
    if (!w || !h) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.cv.width = Math.round(w * dpr);
    this.cv.height = Math.round(h * dpr);
    this.cv.style.width = `${w}px`;
    this.cv.style.height = `${h}px`;
    this.dpr = dpr;
    this.scale = Math.min(w / this.b.w, h / this.b.h) * dpr;
    this.ox = (this.cv.width - this.b.w * this.scale) / 2;
    this.oy = (this.cv.height - this.b.h * this.scale) / 2;
    this.bg = null;
  }

  space(id) { return this.b.spaces[id]; }

  // Places each piece sits at: shared spaces fan out a little.
  targets() {
    const out = new Map();
    if (!this.st) return out;
    const seated = this.st.order.length ? this.st.order : [];
    const by = new Map();
    for (const id of seated) {
      const p = this.st.players.find(q => q.id === id);
      if (!p) continue;
      if (!by.has(p.pos)) by.set(p.pos, []);
      by.get(p.pos).push(p.id);
    }
    for (const [pos, ids] of by) {
      const s = this.space(pos);
      ids.forEach((id, i) => {
        const n = ids.length;
        const a = (i / n) * Math.PI * 2 - Math.PI / 2;
        const r = n > 1 ? 15 : 0;
        out.set(id, { x: s.x + Math.cos(a) * r, y: s.y + Math.sin(a) * r - 6 });
      });
    }
    return out;
  }

  update(st, you) {
    if (st.step !== 'path') this.hover = null;
    this.st = st;
    this.you = you;
    for (const f of st.fx || []) this.effect(f);
    if (st.step !== 'rolling' && this.dice && this.dice.rolling) this.dice.rolling = false;
  }

  effect(f) {
    const p = this.st.players.find(q => q.id === f.p);
    const at = () => (p ? this.tokens.get(p.id) || this.space(p.pos) : null);
    if (f.k === 'coins' && p) {
      const a = at();
      if (a) this.floats.push({ x: a.x, y: a.y - 20, text: `${f.n > 0 ? '+' : ''}${f.n}`, color: f.n > 0 ? '#ffe066' : '#ff6b6b', t: 0 });
    } else if (f.k === 'dice') {
      this.dice = { values: f.dice, t: 0, rolling: true };
    } else if (f.k === 'crown' && p) {
      const a = at();
      if (a) this.floats.push({ x: a.x, y: a.y - 30, text: '👑', color: '#ffd23f', t: 0, big: true });
    } else if (f.k === 'bomb') {
      const s = this.space(f.s);
      this.bombs.push({ x: s.x, y: s.y, t: 0 });
      this.shake = 0.5;
    } else if (f.k === 'boo' && p) {
      const a = at();
      if (a) this.floats.push({ x: a.x, y: a.y - 30, text: 'BOO!', color: '#e8e4ff', t: 0, big: true });
    } else if (f.k === 'web' || f.k === 'trap') {
      const s = this.space(f.s);
      this.floats.push({ x: s.x, y: s.y - 30, text: f.k === 'web' ? 'STUCK!' : 'SNAP!', color: '#fff', t: 0, big: true });
    }
  }

  click(e) {
    const i = this.pickAt(e);
    if (i != null && this.onPick) this.onPick(i);
  }

  // which fork choice is under the pointer: its first space, or where its routes end
  pickAt(e) {
    if (!this.st || this.st.step !== 'path' || this.st.cur !== this.you || !this.st.choices) return null;
    const r = this.cv.getBoundingClientRect();
    const x = ((e.clientX - r.left) * this.dpr - this.ox) / this.scale;
    const y = ((e.clientY - r.top) * this.dpr - this.oy) / this.scale;
    const near = id => { const s = this.space(id); return Math.hypot(s.x - x, s.y - y) < SPACE_R * 1.6; };
    const i = this.st.choices.findIndex((id, i) =>
      near(id) || (this.st.routes?.[i] || []).some(rt => near(rt[rt.length - 1])));
    return i < 0 ? null : i;
  }

  // ---------------------------------------------------------------- scenery (drawn once)

  scenery() {
    const cv = document.createElement('canvas');
    cv.width = this.cv.width;
    cv.height = this.cv.height;
    const c = cv.getContext('2d');
    const W = cv.width, H = cv.height;
    const sky = c.createLinearGradient(0, 0, 0, H);
    sky.addColorStop(0, '#120a24');
    sky.addColorStop(0.6, '#1d1336');
    sky.addColorStop(1, '#14211f');
    c.fillStyle = sky;
    c.fillRect(0, 0, W, H);
    const rnd = art.rand(1031);
    c.fillStyle = 'rgba(255, 255, 240, 0.7)';
    for (let i = 0; i < 90; i++) {
      c.globalAlpha = 0.2 + rnd() * 0.6;
      c.fillRect(rnd() * W, rnd() * H * 0.6, 1.5, 1.5);
    }
    c.globalAlpha = 1;
    c.setTransform(this.scale, 0, 0, this.scale, this.ox, this.oy);
    // the moon
    const mg = c.createRadialGradient(840, 150, 10, 840, 150, 120);
    mg.addColorStop(0, 'rgba(255, 245, 200, 0.35)');
    mg.addColorStop(1, 'rgba(255, 245, 200, 0)');
    c.fillStyle = mg;
    c.fillRect(700, 20, 280, 280);
    c.fillStyle = '#f6efc9';
    c.beginPath(); c.arc(840, 150, 42, 0, Math.PI * 2); c.fill();
    c.fillStyle = 'rgba(200, 190, 150, 0.5)';
    for (const [x, y, r] of [[828, 140, 8], [852, 165, 6], [846, 132, 4]]) { c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.fill(); }
    // the ground inside the loop
    c.fillStyle = '#1f2b25';
    c.beginPath();
    c.roundRect(120, 105, 760, 430, 70);
    c.fill();
    c.fillStyle = 'rgba(60, 90, 60, 0.25)';
    for (let i = 0; i < 40; i++) {
      c.beginPath(); c.ellipse(140 + rnd() * 720, 120 + rnd() * 400, 20 + rnd() * 40, 6 + rnd() * 10, 0, 0, Math.PI * 2); c.fill();
    }
    // graves, trees and pumpkins in the four fields between the paths
    const fields = [[140, 120, 330, 170], [530, 120, 330, 170], [140, 350, 330, 170], [530, 350, 330, 170]];
    fields.forEach(([fx, fy, fw, fh], fi) => {
      for (let i = 0; i < 5; i++) {
        const x = fx + 30 + rnd() * (fw - 60), y = fy + 40 + rnd() * (fh - 60);
        art.tombstone(c, x, y, 13 + rnd() * 5, { cross: rnd() < 0.3, tilt: (rnd() - 0.5) * 0.3 });
      }
      art.deadTree(c, fx + (fi % 2 ? fw - 50 : 50), fy + fh - 25, 120, 7 + fi);
      for (let i = 0; i < 2; i++) {
        art.pumpkin(c, fx + 40 + rnd() * (fw - 80), fy + fh - 20 - rnd() * 30, 9, {});
      }
    });
    // an iron fence along the outside
    c.strokeStyle = 'rgba(20, 15, 30, 0.9)';
    c.lineWidth = 3;
    c.beginPath(); c.moveTo(20, 615); c.lineTo(980, 615); c.stroke();
    for (let x = 24; x < 980; x += 16) {
      c.beginPath(); c.moveTo(x, 615); c.lineTo(x, 596); c.stroke();
      c.beginPath(); c.moveTo(x - 3, 598); c.lineTo(x, 591); c.lineTo(x + 3, 598); c.fill();
    }
    // paths
    c.lineCap = 'round';
    for (const [w, col] of [[30, '#2a1d16'], [20, '#4a3426']]) {
      c.strokeStyle = col;
      c.lineWidth = w;
      for (const s of this.b.spaces) {
        for (const n of s.next) {
          const t = this.space(n);
          c.beginPath(); c.moveTo(s.x, s.y); c.lineTo(t.x, t.y); c.stroke();
        }
      }
    }
    // little arrows showing which way the paths run
    c.fillStyle = 'rgba(255, 220, 160, 0.35)';
    for (const s of this.b.spaces) {
      for (const n of s.next) {
        const t = this.space(n);
        const a = Math.atan2(t.y - s.y, t.x - s.x);
        c.save();
        c.translate((s.x + t.x) / 2, (s.y + t.y) / 2);
        c.rotate(a);
        c.beginPath(); c.moveTo(5, 0); c.lineTo(-4, -5); c.lineTo(-4, 5); c.closePath(); c.fill();
        c.restore();
      }
    }
    c.font = '700 13px "Source Serif 4", Georgia, serif';
    c.fillStyle = 'rgba(255, 230, 190, 0.55)';
    c.textAlign = 'center';
    c.fillText(this.b.name.toUpperCase(), 500, 625);
    // a little shop beside each shop space, on the side away from the middle of the board
    for (const sp of this.b.spaces) {
      if (sp.kind !== 'shop') continue;
      const dx = sp.x - 500, dy = sp.y - 320, m = Math.hypot(dx, dy) || 1;
      const out = sp.middle ? [0, -1] : [dx / m, dy / m];
      this.stall(c, sp.x + out[0] * 44, sp.y + out[1] * 44 + (out[1] < -0.5 ? 6 : 0));
    }
    // the spaces don't change, so they're drawn once here too (only the portals swirl)
    for (const s of this.b.spaces) this.drawSpace(c, s);
    return cv;
  }

  stall(c, x, y) {
    c.save();
    c.translate(x, y);
    c.fillStyle = 'rgba(0,0,0,0.35)';
    c.beginPath(); c.ellipse(0, 15, 24, 5, 0, 0, Math.PI * 2); c.fill();
    c.fillStyle = '#6b4a2b';
    c.fillRect(-20, -6, 40, 21);
    c.fillStyle = '#ffd77a';
    c.fillRect(-14, 0, 28, 9);
    for (let i = 0; i < 5; i++) {
      c.fillStyle = i % 2 ? '#f6efdc' : '#c0392b';
      c.beginPath(); c.moveTo(-24 + i * 9.6, -6); c.lineTo(-24 + (i + 1) * 9.6, -6); c.lineTo(-22 + (i + 1) * 9.6, -18); c.lineTo(-22 + i * 9.6, -18); c.fill();
    }
    c.fillStyle = '#2b1d16';
    c.fillRect(-14, -30, 28, 11);
    c.fillStyle = '#ffe7b0';
    c.font = '700 8px "Source Sans 3", system-ui, sans-serif';
    c.textAlign = 'center';
    c.textBaseline = 'middle';
    c.fillText('SHOP', 0, -24);
    c.restore();
  }

  // ---------------------------------------------------------------- each frame

  draw(dt) {
    this.t += dt;
    const c = this.c;
    if (!this.bg) this.bg = this.scenery();
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.drawImage(this.bg, 0, 0);
    let sx = 0, sy = 0;
    if (this.shake > 0) {
      this.shake -= dt;
      sx = (Math.random() - 0.5) * 10 * this.shake * this.dpr;
      sy = (Math.random() - 0.5) * 10 * this.shake * this.dpr;
    }
    c.setTransform(this.scale, 0, 0, this.scale, this.ox + sx, this.oy + sy);
    if (!this.st) return;
    const st = this.st;
    if (st.witching) {
      c.fillStyle = `rgba(120, 0, 30, ${0.12 + 0.04 * Math.sin(this.t * 2)})`;
      c.fillRect(-50, -50, this.b.w + 100, this.b.h + 100);
    }
    this.drawFog(c);
    for (const s of this.b.spaces) if (s.kind === 'portal') this.drawSpace(c, s);
    // highlight the ways to go at a fork
    if (st.step === 'path' && st.choices) {
      const mine = st.cur === this.you;
      st.choices.forEach((id, i) => {
        const s = this.space(id);
        c.strokeStyle = mine ? ROUTE_COLORS[i] : 'rgba(255, 255, 255, 0.5)';
        c.lineWidth = 3;
        c.beginPath(); c.arc(s.x, s.y, SPACE_R + 6 + Math.sin(this.t * 6) * 3, 0, Math.PI * 2); c.stroke();
      });
      if (st.routes) this.drawRoutes(c, st);
    }
    // piles, traps, webs
    for (const [sid, n] of Object.entries(st.piles || {})) {
      const s = this.space(+sid);
      for (let i = 0; i < Math.min(5, Math.ceil(n / 3)); i++) art.coin(c, s.x - 10 + i * 5, s.y + 14 - i * 2, 5);
      this.label(c, `${n}`, s.x + 18, s.y + 18, '#ffe066', 12);
    }
    for (const sid of Object.keys(st.webs || {})) {
      const s = this.space(+sid);
      art.web(c, s.x, s.y, SPACE_R + 4, 0.75);
    }
    for (const [sid, owner] of Object.entries(st.traps || {})) {
      const s = this.space(+sid);
      const p = st.players.find(q => q.id === owner);
      c.fillStyle = p ? p.color : '#fff';
      c.beginPath(); c.arc(s.x + 16, s.y - 16, 8, 0, Math.PI * 2); c.fill();
      this.label(c, '!', s.x + 16, s.y - 15, '#fff', 12);
    }
    // the crown
    if (st.crown != null) {
      const s = this.space(st.crown);
      c.fillStyle = `rgba(255, 210, 60, ${0.25 + 0.1 * Math.sin(this.t * 3)})`;
      c.beginPath(); c.arc(s.x, s.y, SPACE_R + 12, 0, Math.PI * 2); c.fill();
      art.crown(c, s.x, s.y - 34 + Math.sin(this.t * 2.5) * 3, 14, 1.2);
    }
    // the ghost glides to where it is
    if (st.ghost != null) {
      const s = this.space(st.ghost);
      if (!this.ghost) this.ghost = { x: s.x, y: s.y };
      const k = Math.min(1, dt * 2.5);
      this.ghost.x += (s.x + 22 - this.ghost.x) * k;
      this.ghost.y += (s.y - 26 - this.ghost.y) * k;
      c.globalAlpha = 0.85;
      art.ghost(c, this.ghost.x, this.ghost.y + Math.sin(this.t * 2) * 4, 15, { t: this.t, color: '#dcd6ff' });
      c.globalAlpha = 1;
    }
    this.drawTokens(c, dt);
    this.drawBombs(c, dt);
    this.drawFloats(c, dt);
    this.drawDice(c, dt);
  }

  // where each way at a fork leads: a dotted trail to a pin on every space it could end on
  drawRoutes(c, st) {
    const from = st.players.find(p => p.id === st.cur);
    if (!from) return;
    const pins = new Map();  // space -> choices that can end there
    const order = st.routes.map((_, i) => i).filter(i => i !== this.hover);
    if (this.hover != null && st.routes[this.hover]) order.push(this.hover);  // pointed-at one on top
    for (const i of order) {
      const lit = this.hover == null || this.hover === i;
      for (const rt of st.routes[i]) {
        const pts = [from.pos, ...rt].map(id => this.space(id));
        c.save();
        c.globalAlpha = lit ? 0.9 : 0.25;
        c.strokeStyle = ROUTE_COLORS[i];
        c.lineWidth = lit && this.hover === i ? 5 : 3.5;
        c.setLineDash([2, 9]);
        c.lineDashOffset = -this.t * 18;
        c.lineCap = 'round';
        c.beginPath();
        pts.forEach((p, k) => (k ? c.lineTo(p.x, p.y) : c.moveTo(p.x, p.y)));
        c.stroke();
        c.restore();
        const end = rt[rt.length - 1];
        if (!pins.has(end)) pins.set(end, []);
        if (!pins.get(end).includes(i)) pins.get(end).push(i);
      }
    }
    const bob = Math.sin(this.t * 4) * 3;
    for (const [id, is] of pins) {
      const s = this.space(id);
      is.forEach((i, k) => {
        const x = s.x + (k - (is.length - 1) / 2) * 24, y = s.y - SPACE_R - 24 + bob;
        const lit = this.hover == null || this.hover === i;
        c.globalAlpha = lit ? 1 : 0.35;
        c.fillStyle = ROUTE_COLORS[i];
        c.strokeStyle = '#1a1020';
        c.lineWidth = 2;
        c.beginPath();
        c.moveTo(x, y + 17);
        c.arc(x, y, 11, Math.PI * 0.75, Math.PI * 0.25);
        c.closePath();
        c.fill(); c.stroke();
        c.fillStyle = '#1a1020';
        c.beginPath(); c.arc(x, y, 4, 0, Math.PI * 2); c.fill();
        c.globalAlpha = 1;
      });
    }
  }

  drawFog(c) {
    for (let i = 0; i < 6; i++) {
      const x = ((this.t * (8 + i * 3) + i * 230) % 1300) - 150;
      const y = 120 + i * 85;
      const g = c.createRadialGradient(x, y, 10, x, y, 140);
      g.addColorStop(0, 'rgba(200, 200, 230, 0.07)');
      g.addColorStop(1, 'rgba(200, 200, 230, 0)');
      c.fillStyle = g;
      c.fillRect(x - 140, y - 140, 280, 280);
    }
  }

  drawSpace(c, s) {
    const [fill, edge] = KIND_COLORS[s.kind];
    c.save();
    c.translate(s.x, s.y);
    c.fillStyle = 'rgba(0, 0, 0, 0.4)';
    c.beginPath(); c.ellipse(0, 5, SPACE_R, SPACE_R * 0.75, 0, 0, Math.PI * 2); c.fill();
    const g = c.createRadialGradient(-6, -8, 2, 0, 0, SPACE_R);
    g.addColorStop(0, fill);
    g.addColorStop(1, edge);
    c.fillStyle = g;
    c.beginPath(); c.arc(0, 0, SPACE_R, 0, Math.PI * 2); c.fill();
    c.strokeStyle = 'rgba(255, 255, 255, 0.25)';
    c.lineWidth = 2;
    c.stroke();
    c.fillStyle = 'rgba(255, 255, 255, 0.92)';
    c.textAlign = 'center';
    c.textBaseline = 'middle';
    c.font = '700 20px "Source Sans 3", system-ui, sans-serif';
    if (s.kind === 'blue') c.fillText('+', 0, 1);
    else if (s.kind === 'red') c.fillText('−', 0, 0);
    else if (s.kind === 'event') c.fillText('?', 0, 1);
    else if (s.kind === 'shop') c.fillText('$', 0, 1);
    else if (s.kind === 'item') {
      c.fillStyle = '#ffe9a8';
      c.fillRect(-9, -5, 18, 12);
      c.fillStyle = '#7a4a10';
      c.fillRect(-9, -7, 18, 4);
      c.fillRect(-2, -7, 4, 14);
    } else if (s.kind === 'duel') {
      c.strokeStyle = '#2b2b3a';
      c.lineWidth = 3;
      c.beginPath(); c.moveTo(-9, -9); c.lineTo(9, 9); c.moveTo(9, -9); c.lineTo(-9, 9); c.stroke();
    } else if (s.kind === 'portal') {
      c.strokeStyle = '#e9ffff';
      c.lineWidth = 2;
      for (let i = 0; i < 3; i++) {
        c.beginPath();
        c.arc(0, 0, 5 + i * 5, this.t * (2 + i) + i, this.t * (2 + i) + i + 4);
        c.stroke();
      }
    }
    if (s.id === this.b.start) this.label(c, 'START', 0, -SPACE_R - 9, '#ffe7b0', 10);
    if (s.label) this.label(c, s.label.toUpperCase(), 0, SPACE_R + 11, 'rgba(255,231,176,0.8)', 9);
    c.restore();
  }

  drawTokens(c, dt) {
    const st = this.st;
    const tg = this.targets();
    const k = Math.min(1, dt * 9);
    for (const id of st.order) {
      const p = st.players.find(q => q.id === id);
      const t = tg.get(id);
      if (!p || !t) continue;
      let cur = this.tokens.get(id);
      if (!cur) { cur = { x: t.x, y: t.y, hop: 0 }; this.tokens.set(id, cur); }
      const far = Math.hypot(t.x - cur.x, t.y - cur.y);
      cur.x += (t.x - cur.x) * k;
      cur.y += (t.y - cur.y) * k;
      cur.hop = far > 2 ? Math.min(1, cur.hop + dt * 6) : Math.max(0, cur.hop - dt * 6);
    }
    // the current player is drawn last, on top
    const ids = [...st.order].sort((a, b) => (a === st.cur) - (b === st.cur));
    for (const id of ids) {
      const p = st.players.find(q => q.id === id);
      const cur = this.tokens.get(id);
      if (!p || !cur) continue;
      const me = id === st.cur;
      const bob = me ? Math.abs(Math.sin(this.t * 5)) * 5 : 0;
      const hop = Math.sin(cur.hop * Math.PI) * 8;
      const r = me ? 15 : 12;
      if (p.curse) {
        c.fillStyle = `rgba(160, 60, 220, ${0.3 + 0.15 * Math.sin(this.t * 5)})`;
        c.beginPath(); c.arc(cur.x, cur.y - bob - hop, r + 8, 0, Math.PI * 2); c.fill();
      }
      art.token(c, cur.x, cur.y - bob - hop, r, p.color, {
        label: p.name.slice(0, 1).toUpperCase(), ring: me ? '#ffe066' : '#fff', dim: !p.on && !p.bot, t: this.t + id,
      });
      if (p.hex) this.label(c, '🧹', cur.x + r, cur.y - r - bob, '#fff', 14);
      if (me && st.step === 'move' && st.left > 0) {
        this.label(c, `${st.left}`, cur.x, cur.y - r - 16 - bob, st.back ? '#ff9b9b' : '#fff', 18);
      }
    }
  }

  drawBombs(c, dt) {
    this.bombs = this.bombs.filter(b => (b.t += dt) < 0.8);
    for (const b of this.bombs) {
      const r = 30 + b.t * 260;
      c.fillStyle = `rgba(255, 140, 30, ${0.6 * (1 - b.t / 0.8)})`;
      c.beginPath(); c.arc(b.x, b.y, r, 0, Math.PI * 2); c.fill();
    }
  }

  drawFloats(c, dt) {
    this.floats = this.floats.filter(f => (f.t += dt) < 1.6);
    for (const f of this.floats) {
      c.globalAlpha = Math.min(1, 2 * (1.6 - f.t));
      this.label(c, f.text, f.x, f.y - f.t * 30, f.color, f.big ? 24 : 18);
    }
    c.globalAlpha = 1;
  }

  drawDice(c, dt) {
    const d = this.dice;
    if (!d) return;
    d.t += dt;
    // shown while the roll is on screen, then faded out once walking starts
    if (this.st.step !== 'rolling' && d.t > 1.6) d.fade = (d.fade || 0) + dt;
    if (d.fade > 0.4) { this.dice = null; return; }
    const rolling = d.t < 0.9;
    const n = d.values.length;
    const size = 64;
    const cx = this.b.w / 2, cy = this.b.h / 2 - 20;
    const fade = 1 - (d.fade || 0) / 0.4;
    c.globalAlpha = fade;
    d.values.forEach((v, i) => {
      const x = cx + (i - (n - 1) / 2) * (size + 20);
      const y = cy - (rolling ? Math.abs(Math.sin(d.t * 12)) * 20 : 0);
      const show = rolling ? 1 + Math.floor(Math.random() * 10) : v;
      c.save();
      c.translate(x, y);
      c.rotate(rolling ? Math.sin(d.t * 17 + i) * 0.4 : 0);
      c.fillStyle = 'rgba(0,0,0,0.4)';
      c.beginPath(); c.roundRect(-size / 2 + 4, -size / 2 + 6, size, size, 12); c.fill();
      c.fillStyle = '#fbf3e4';
      c.beginPath(); c.roundRect(-size / 2, -size / 2, size, size, 12); c.fill();
      c.strokeStyle = '#7a1f1f';
      c.lineWidth = 3;
      c.stroke();
      c.fillStyle = '#7a1f1f';
      c.font = '700 36px "Source Serif 4", Georgia, serif';
      c.textAlign = 'center';
      c.textBaseline = 'middle';
      c.fillText(String(show), 0, 2);
      c.restore();
    });
    c.globalAlpha = 1;
  }

  label(c, text, x, y, color, size) {
    c.font = `700 ${size}px "Source Sans 3", system-ui, sans-serif`;
    c.textAlign = 'center';
    c.textBaseline = 'middle';
    c.lineWidth = 4;
    c.lineJoin = 'round';
    c.strokeStyle = 'rgba(0, 0, 0, 0.7)';
    c.strokeText(text, x, y);
    c.fillStyle = color;
    c.fillText(text, x, y);
  }
}
