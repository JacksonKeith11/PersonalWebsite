// The minigame stage: a canvas over the board that each game draws into, in logical units
// 420-800 wide (the screen's width in CSS pixels, within those bounds) and as tall as suits the
// screen's shape. It runs the 3-2-1 countdown, the timer
// and the FINISH banner, and hands games the keyboard, pointer and server snapshots.

import * as sfx from './audio.js?v=7';
import { SOLO } from './games-solo.js?v=7';
import { LIVE } from './games-live.js?v=7';
import { MORE } from './games-more.js?v=7';
import { CLASSIC } from './games-classic.js?v=7';
import { SHOWDOWN } from './games-showdown.js?v=7';
import { Game, TEAM_COLORS } from './base.js?v=7';

const GAMES = { ...SOLO, ...LIVE, ...MORE, ...CLASSIC, ...SHOWDOWN };
const now = () => performance.now() / 1000;

export class Stage {
  constructor(root, canvas, input) {
    this.root = root;
    this.cv = canvas;
    this.c = canvas.getContext('2d');
    this.input = input;  // a text box some games use
    this.game = null;
    this.raf = 0;
    this.W = 800;
    this.H = 500;
    this.keys = e => this.onKey(e);
    window.addEventListener('keydown', this.keys);
    window.addEventListener('keyup', this.keys);
    for (const type of ['pointerdown', 'pointermove', 'pointerup', 'pointercancel']) {
      canvas.addEventListener(type, e => this.onPointer(e));
    }
    canvas.addEventListener('touchstart', e => e.preventDefault(), { passive: false });
    window.addEventListener('resize', () => this.resize());
  }

  get open() { return !!this.game; }

  start(info, ctx) {
    this.close(false);
    this.info = info;
    this.you = ctx.you;
    this.players = ctx.players;
    this.send = ctx.send;
    this.startAt = info.starts_in != null ? now() + info.starts_in : null;
    this.ended = null;
    this.counted = 3;
    this.root.hidden = false;
    this.resize();
    const G = GAMES[info.key];
    this.game = G ? new G(this) : new Game(this);
    this.game.teams = info.teams;
    this.game.mode = info.mode;
    if (this.early) { this.game.snap(this.early); this.early = null; }
    this.last = now();
    const loop = () => {
      this.raf = requestAnimationFrame(loop);
      this.frame();
    };
    loop();
  }

  // the state says the game is on: (re)sync the start time
  sync(info) {
    if (!this.game || info.starts_in == null) return;
    const at = now() + info.starts_in;
    if (this.startAt == null || Math.abs(at - this.startAt) > 0.25) this.startAt = at;
  }

  close(forget = true) {
    if (forget) this.early = null;
    cancelAnimationFrame(this.raf);
    if (this.game) this.game.end();
    this.game = null;
    this.root.hidden = true;
    this.input.hidden = true;
    this.input.onkeydown = null;
  }

  snap(m) {
    if (!this.game) { this.early = m; return; }  // arrived before the state that opens the game
    this.game.snap(m);
    if (m.end && !this.ended) {
      this.ended = now();
      sfx.play('end');
    }
  }

  get t() { return this.startAt == null ? -99 : now() - this.startAt; }

  resize() {
    const w = this.root.clientWidth, h = this.root.clientHeight;
    if (!w || !h) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.cv.width = Math.round(w * dpr);
    this.cv.height = Math.round(h * dpr);
    this.cv.style.width = `${w}px`;
    this.cv.style.height = `${h}px`;
    this.W = Math.max(420, Math.min(800, Math.round(w)));
    this.H = Math.max(Math.round(this.W * 0.56), Math.min(Math.round(this.W * 2), Math.round((this.W * h) / w)));
    this.scale = Math.min(this.cv.width / this.W, this.cv.height / this.H);
    this.ox = (this.cv.width - this.W * this.scale) / 2;
    this.oy = (this.cv.height - this.H * this.scale) / 2;
    this.dpr = dpr;
  }

  toLogical(e) {
    const r = this.cv.getBoundingClientRect();
    return [((e.clientX - r.left) * this.dpr - this.ox) / this.scale, ((e.clientY - r.top) * this.dpr - this.oy) / this.scale];
  }

  live() { return this.game && this.t >= 0 && !this.ended && this.game.playing; }

  onKey(e) {
    if (!this.game) return;
    if (e.target === this.input) return;
    if (['Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) e.preventDefault();
    if (e.type === 'keydown' && e.repeat) return;
    this.game.key(e, e.type === 'keydown', this.live());
  }

  onPointer(e) {
    if (!this.game) return;
    sfx.unlock();
    const [x, y] = this.toLogical(e);
    if (e.type === 'pointerdown') this.cv.setPointerCapture?.(e.pointerId);
    this.game.pointer(e.type, x, y, e.pointerId, this.live());
  }

  frame() {
    const t0 = now();
    const dt = Math.min(0.1, t0 - this.last);
    this.last = t0;
    const c = this.c;
    c.setTransform(1, 0, 0, 1, 0, 0);
    if (this.game.transparent) {
      // a 3D game: its own canvas shows through from underneath
      c.clearRect(0, 0, this.cv.width, this.cv.height);
      c.setTransform(this.scale, 0, 0, this.scale, this.ox, this.oy);
    } else {
      c.fillStyle = '#0d0816';
      c.fillRect(0, 0, this.cv.width, this.cv.height);
      c.setTransform(this.scale, 0, 0, this.scale, this.ox, this.oy);
      const g = c.createLinearGradient(0, 0, 0, this.H);
      g.addColorStop(0, '#1f1236');
      g.addColorStop(1, '#120c1e');
      c.fillStyle = g;
      c.fillRect(0, 0, this.W, this.H);
    }
    const t = this.t;
    c.save();
    try {
      this.game.draw(t, dt);
    } catch (err) {
      console.error(err);
    }
    c.restore();
    this.hud(t);
  }

  hud(t) {
    const c = this.c;
    const g = this.game;
    c.fillStyle = 'rgba(0,0,0,0.35)';
    c.fillRect(0, 0, this.W, 40);
    g.text(this.info.name, 14, 20, 18, '#ffe9b8', 'left');
    if (this.info.teams && this.info.mode !== 'ffa') {
      const short = n => (this.W < 600 && n.length > 8 ? `${n.slice(0, 7)}…` : n);
      const names = this.info.teams.map(team => team.map(id => short((this.players[id] || {}).name || '?')).join(' & '));
      const mid = this.W > 600 ? this.W * 0.62 : this.W / 2;
      const y = this.W > 600 ? 20 : 52;
      g.text(names[0], mid - 18, y, 15, TEAM_COLORS[0], 'right');
      g.text('vs', mid, y, 14, '#bbb');
      g.text(names[1], mid + 18, y, 15, TEAM_COLORS[1], 'left');
    } else if (this.info.mode === 'duel') {
      g.text('Duel', this.W * 0.62, 20, 15, '#ffb3b3');
    }
    const left = Math.max(0, Math.ceil(this.info.dur - Math.max(0, t)));
    if (!this.game.noTimer) g.text(`${left}`, this.W - 14, 20, 22, left <= 5 && t > 0 ? '#ff6b6b' : '#fff', 'right');
    if (!this.game.playing) g.text('Watching', this.W - 60, 20, 14, '#aaa', 'right');
    if (t < 0 && t > -5) {
      const n = Math.ceil(-t);
      if (n < this.counted) { this.counted = n; sfx.play('count'); }
      c.fillStyle = 'rgba(0,0,0,0.45)';
      c.fillRect(0, 0, this.W, this.H);
      g.title(String(n), this.W / 2, this.H / 2, 110, '#ffe066');
      if (this.game.hint) {
        // on a dark pill, so it reads over whatever the game has drawn there
        c.font = '700 20px "Source Sans 3", system-ui, sans-serif';
        const w = c.measureText(this.game.hint).width + 36;
        c.fillStyle = 'rgba(16, 10, 28, 0.92)';
        c.beginPath(); c.roundRect(this.W / 2 - w / 2, this.H / 2 + 70, w, 40, 20); c.fill();
        g.text(this.game.hint, this.W / 2, this.H / 2 + 90, 20, '#fff');
      }
    } else if (t >= 0 && t < 0.7) {
      if (this.counted > 0) { this.counted = 0; sfx.play('go'); }
      g.title('GO!', this.W / 2, this.H / 2, 110 + t * 60, `rgba(255,224,102,${1 - t / 0.7})`);
    }
    if (this.ended) {
      const k = Math.min(1, (now() - this.ended) * 3);
      c.fillStyle = `rgba(0,0,0,${0.4 * k})`;
      c.fillRect(0, 0, this.W, this.H);
      g.title('FINISH!', this.W / 2, this.H / 2, 60 + 40 * k, '#ffe066');
    } else if (t < -5) {
      g.title('Get ready…', this.W / 2, this.H / 2, 40, '#ffe9b8');
    }
  }
}
