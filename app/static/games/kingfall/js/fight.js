// The fight: a Phaser scene with the arena, the boss and every hero. This browser's heroes are moved
// here and their hits checked here (both ways); the server says what the boss does and keeps score.
import { addFrames } from './rig.js?v=1';
import { LocalHero, RemoteHero } from './hero.js?v=1';
import { Boss } from './boss.js?v=1';
import { drawChapel } from './arena.js?v=1';
import { sfx } from './audio.js?v=1';
import { deviceOfSlot } from './input.js?v=1';

const ARENAS = { chapel: drawChapel };
const INTERP = 0.1;

export class FightScene extends Phaser.Scene {
  constructor() { super('fight'); }

  init(cfg) { this.cfg = cfg; }

  create() {
    const { net, data, fight, heroes, me } = this.cfg;
    this.net = net; this.data = data; this.fightMsg = fight;
    addFrames(this);
    const [w, h] = fight.size;
    this.size = [w, h]; this.pad = fight.pad;
    if (this.textures.exists('arena')) this.textures.remove('arena');
    const A = ARENAS[fight.arena](w, h, fight.pad);
    this.textures.addCanvas('arena', A.canvas);
    this.add.image(0, 0, 'arena').setOrigin(0).setDepth(0);
    this.lights = [];
    if (!this.textures.exists('glow')) {
      const cv = document.createElement('canvas'); cv.width = cv.height = 64;
      const g = cv.getContext('2d'), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
      gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.35, 'rgba(255,255,255,0.35)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
      this.textures.addCanvas('glow', cv);
    }
    for (const [x, y] of A.windows) {
      const shaft = this.add.graphics().setDepth(3).setBlendMode(Phaser.BlendModes.ADD);
      shaft.fillStyle(0xa8b8ff, 0.05);
      shaft.fillPoints([{ x: x - 16, y: y - 30 }, { x: x + 16, y: y - 30 }, { x: x + 60, y: y + 150 }, { x: x - 10, y: y + 150 }], true);
    }
    for (const [x, y] of A.candles) {
      this.add.rectangle(x, y - 2, 2, 5, 0xd8d0c0).setDepth(y);
      const flame = this.add.rectangle(x, y - 6, 2, 3, 0xffd23f).setDepth(y + 0.1);
      const glow = this.add.image(x, y - 6, 'glow').setTint(0xff9a3a).setAlpha(0.35).setDisplaySize(56, 56).setDepth(4).setBlendMode(Phaser.BlendModes.ADD);
      this.lights.push({ flame, glow, seed: Math.random() * 10 });
    }

    this.boss = new Boss(this, data, fight);
    this.local = []; this.remote = {};
    for (const hh of heroes) {
      const at = fight.heroes[hh.id] || [w / 2, h * 0.75];
      const H = { ...hh, colourHex: data.colours[hh.colour] };
      if (hh.conn === me) {
        const lh = new LocalHero(this, H, deviceOfSlot(hh.slot), data, at[0], at[1]);
        lh.taken = new Set();
        lh.aim = -Math.PI / 2;
        this.local.push(lh);
      } else {
        this.remote[hh.id] = new RemoteHero(this, H, data);
      }
    }
    this.byId = {};
    for (const l of this.local) this.byId[l.id] = l;
    Object.assign(this.byId, this.remote);
    this.heroRows = {};
    this.texts = [];
    this.sparks = this.add.graphics().setDepth(6000);
    this.sparkList = [];
    this.reviveG = this.add.graphics().setDepth(6001);
    const cam = this.cameras.main;
    cam.setBounds(0, 0, w, h);
    cam.setBackgroundColor('#0c0a10');
    this.camX = w / 2; this.camY = h / 2;
    this.lastReport = 0;
    this.stop = 0;
    this.started = this.net.now();
    this.ended = false;
    this.cfg.onReady && this.cfg.onReady(this);
  }

  world(screen) {
    const cam = this.cameras.main, canvas = this.game.canvas, r = canvas.getBoundingClientRect();
    const sx = (screen.x - r.left) / r.width * this.scale.width, sy = (screen.y - r.top) / r.height * this.scale.height;
    return { x: cam.scrollX + sx, y: cam.scrollY + sy };
  }

  collide(hero) {
    const [w, h] = this.size, [l, t, r, b] = this.pad, R = hero.HERO.radius;
    hero.x = Math.max(l + R, Math.min(w - r - R, hero.x));
    hero.y = Math.max(t + R, Math.min(h - b - R, hero.y));
    const B = this.boss;
    if (B.alive) {
      const dx = hero.x - B.x, dy = hero.y - B.y, d = Math.hypot(dx, dy), min = B.r + R - 2;
      if (d < min && hero.state !== 'roll') {
        const k = d > 0.01 ? (min - d) / d : 1;
        hero.x += dx * k; hero.y += (d > 0.01 ? dy : 1) * k;
      }
    }
  }

  pan(x) { const hw = this.scale.width / 2; return Math.max(-0.8, Math.min(0.8, (x - this.cameras.main.scrollX - hw) / hw)); }

  // ------------------------------------------------------------------ server messages
  onMsg(m) {
    const B = this.boss;
    switch (m.t) {
      case 's': {
        B.onSnap(m.st, m.b);
        for (const row of m.h) {
          const [id, x, y, , , , hp, mhp, flasks, down, bleed] = row;
          this.heroRows[id] = { hp, mhp, flasks, down, bleed };
          const r = this.remote[id];
          if (r) { r.push(m.st, row); r.down = down === 1; r.dead = down === 2; r.x = x; r.y = y; }
          const l = this.local.find(v => v.id === id);
          if (l) {
            const wasDown = l.down;
            l.down = down === 1; l.dead = down === 2; l.h.flasks = flasks;
            if (wasDown && !l.down) { l.state = 'idle'; l.t = 0; }
          }
        }
        break;
      }
      case 'mv':
        B.onMove(m);
        sfx.tell(m.id, this.pan(m.x));
        break;
      case 'aim': B.onAim(m); break;
      case 'cancel': B.onCancel(m); break;
      case 'fx': this.fx(m); break;
    }
  }

  fx(m) {
    const B = this.boss, mine = this.local.find(l => l.id === m.h);
    switch (m.k) {
      case 'hit': case 'crit':
        B.flash = 0.07;
        this.number(B.x + (Math.random() - 0.5) * 16, B.y - 70, m.dmg, m.k === 'crit' ? '#ffd23f' : '#f4f0e0', m.k === 'crit');
        if (mine) mine.focus = Math.min(mine.HERO.focus, mine.focus + m.dmg * mine.HERO.focus_per_dmg * (mine.S.focus_gain || 1) + (mine.state === 'special' ? mine.S.focusback || 0 : 0));
        if (m.k === 'crit') { sfx.crit(this.pan(B.x)); this.cameras.main.shake(180, 0.008); this.burst(B.x, B.y - 40, 0xffd23f, 26); }
        else if (!mine) sfx.hit(this.pan(B.x));
        break;
      case 'guarded':
        sfx.guarded(this.pan(B.x)); this.burst(B.x + Math.cos(B.face) * 18, B.y - 30, 0xffffff, 8);
        if (mine) mine.h && (mine.flash = 0);
        this.number(B.x, B.y - 74, 'Guarded', '#a8b0bc');
        break;
      case 'status': {
        const col = { burn: '#ff8a3a', frost: '#7fe3ff', bleed: '#e04a5a', rot: '#8be04e' }[m.kind];
        this.number(B.x, B.y - 92, m.kind.toUpperCase() + (m.dmg ? ' ' + m.dmg : ''), col, true);
        this.burst(B.x, B.y - 40, Phaser.Display.Color.HexStringToColor(col).color, 22);
        sfx.fire(this.pan(B.x));
        break;
      }
      case 'dot': this.number(B.x + 14, B.y - 60, m.dmg, '#8be04e'); break;
      case 'chain':
        this.bolt(B.x, B.y - 40); sfx.clang(this.pan(B.x));
        break;
      case 'immune': this.number(B.x, B.y - 74, 'Immune', '#a8b0bc'); break;
      case 'stagger':
        sfx.stagger(this.pan(B.x)); this.number(B.x, B.y - 86, 'STAGGERED', '#ffd23f', true);
        this.cameras.main.shake(140, 0.006);
        break;
      case 'parry':
        sfx.parry(this.pan(m.x)); this.burst(m.x, m.y - 20, 0xfff0c0, 18);
        this.number(m.x, m.y - 46, 'Parry!', '#fff0c0', true);
        this.stop = 0.12;
        break;
      case 'block': sfx.clang(this.pan(m.x)); this.burst(m.x, m.y - 18, 0xe8ecf2, 8); break;
      case 'hurt':
        sfx.hurt(this.pan(m.x));
        this.number(m.x, m.y - 46, m.dmg, '#e05050');
        if (mine) { this.cameras.main.shake(120, 0.006); this.cfg.input.rumble(mine.dev, 0.7, 160); }
        else if (this.remote[m.h]) this.remote[m.h].flash = 0.12;
        break;
      case 'heal': sfx.heal(); this.burst(m.x, m.y - 20, 0x8be04e, 14); break;
      case 'down': sfx.down(); this.number(m.x, m.y - 46, 'Down!', '#e05050', true); break;
      case 'secondwind': this.number(this.byId[m.h]?.x || 0, (this.byId[m.h]?.y || 0) - 56, 'Second Wind', '#ffd23f', true); break;
      case 'revive': sfx.revive(); this.burst(m.x, m.y - 20, 0xffd23f, 16); break;
      case 'bossdown':
        sfx.bossDown(); this.cameras.main.shake(400, 0.01); this.burst(m.x, m.y - 40, 0xff7a1a, 40);
        this.cfg.onBanner && this.cfg.onBanner('won');
        break;
      case 'wipe': sfx.wipe(); this.cfg.onBanner && this.cfg.onBanner('lost'); break;
    }
  }

  number(x, y, text, colour, big = false) {
    const t = this.add.text(x, y, String(text), {
      fontFamily: 'Cinzel, Georgia, serif', fontSize: big ? '13px' : '10px', fontStyle: 'bold', color: colour,
      stroke: '#120e16', strokeThickness: 3, resolution: this.cfg.zoom(),
    }).setOrigin(0.5).setDepth(7000);
    this.texts.push({ t, life: 0.9, vy: -28 });
  }

  bolt(x, y) {
    const g = this.add.graphics().setDepth(6500);
    g.lineStyle(2, 0xd8ccff, 1);
    let px = x + (Math.random() - 0.5) * 20, py = y - 60;
    g.beginPath(); g.moveTo(px, py);
    for (let i = 0; i < 6; i++) { px = x + (Math.random() - 0.5) * 16; py += 10; g.lineTo(px, py); }
    g.strokePath();
    this.tweens.add({ targets: g, alpha: 0, duration: 220, onComplete: () => g.destroy() });
  }

  burst(x, y, colour, n) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2, s = 40 + Math.random() * 120;
      this.sparkList.push({ x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s - 30, life: 0.25 + Math.random() * 0.3, colour });
    }
  }

  // a local hero's attack connected (before the server's word, so it feels instant)
  onHit(hero, kind) {
    const B = this.boss;
    sfx.hit(this.pan(B.x));
    this.burst(B.x - Math.cos(hero.aim) * 8, B.y - 30, 0xfff0c0, kind === 'light' ? 6 : 12);
    this.stop = kind === 'light' ? 0.045 : 0.08;
    this.cfg.input.rumble(hero.dev, kind === 'light' ? 0.25 : 0.5, 70);
  }

  // ------------------------------------------------------------------ the frame
  update(time, deltaMs) {
    const dtReal = Math.min(0.05, deltaMs / 1000);
    const now = this.net.now();
    let dt = dtReal;
    if (this.stop > 0) { this.stop -= dtReal; dt = dtReal * 0.08; }
    const B = this.boss;
    const allies = [...this.local, ...Object.values(this.remote)];
    const ctx = {
      input: this.cfg.input, boss: B, world: s => this.world(s), send: m => this.net.send(m),
      collide: h => this.collide(h), onHit: (h, k) => this.onHit(h, k), allies,
    };
    for (const l of this.local) {
      const before = l.state;
      l.update(dt, ctx);
      if (l.state !== before) {
        if (l.state === 'roll') sfx.roll(this.pan(l.x));
        else if (l.state === 'atk' || l.state === 'special') sfx.swing(this.pan(l.x));
        else if (l.state === 'heavy') sfx.heavySwing(this.pan(l.x));
      } else if (l.state === 'atk' && l.t < dt * 1.5 && l.t > 0) sfx.swing(this.pan(l.x));
    }
    B.update(now, dtReal);
    // the boss's hits against this browser's heroes (the dodger decides)
    for (const l of this.local) {
      B.checkHero(now, l, (h, id, bx, by) => {
        if (l.invulnerable() && !l.perfects.has(id)) {  // rolled clean through it
          l.perfects.add(id);
          if (l.S.perfect_st) { l.st = Math.min(l.maxSt, l.st + l.S.perfect_st); this.number(l.x, l.y - 50, 'Perfect', '#fff0c0'); }
          this.net.send({ t: 'perfect', h: l.id });
        }
        const r = l.takeHit(h, bx, by);
        if (!r) return false;
        this.net.send({ t: 'hurt', h: l.id, id, block: r === 'block' ? 1 : 0, parry: r === 'parry' ? 1 : 0 });
        if (r === 'parry') this.stop = 0.12;
        return true;
      });
    }
    for (const l of this.local) l.draw();
    for (const r of Object.values(this.remote)) r.draw(now - INTERP, dtReal);

    // revive progress over the fallen
    this.reviveG.clear();
    for (const l of this.local) {
      if (!l.reviving) continue;
      const t = this.byId[l.reviving];
      if (!t) continue;
      const u = l.reviveT / l.HERO.down.revive;
      this.reviveG.lineStyle(3, 0x120e16, 0.8).beginPath().arc(t.x, t.y - 30, 9, 0, Math.PI * 2).strokePath();
      this.reviveG.lineStyle(2, 0xffd23f, 1).beginPath().arc(t.x, t.y - 30, 9, -Math.PI / 2, -Math.PI / 2 + u * Math.PI * 2).strokePath();
    }

    // effects
    this.sparks.clear();
    this.sparkList = this.sparkList.filter(s => {
      s.life -= dtReal; s.x += s.vx * dtReal; s.y += s.vy * dtReal; s.vy += 220 * dtReal;
      this.sparks.fillStyle(s.colour, Math.min(1, s.life * 4)); this.sparks.fillRect(Math.round(s.x), Math.round(s.y), 2, 2);
      return s.life > 0;
    });
    this.texts = this.texts.filter(o => {
      o.life -= dtReal; o.t.y += o.vy * dtReal; o.vy *= 0.94; o.t.alpha = Math.min(1, o.life * 3);
      if (o.life <= 0) { o.t.destroy(); return false; }
      return true;
    });
    for (const L of this.lights) {
      const f = 0.85 + Math.sin(time / 90 + L.seed) * 0.08 + Math.sin(time / 37 + L.seed * 3) * 0.06;
      L.glow.setDisplaySize(56 * f, 56 * f); L.flame.setScale(1, f);
    }

    // camera: this browser's heroes, nudged toward the boss
    const live = this.local.filter(l => !l.dead);
    const focus = live.length ? live : this.local;
    if (focus.length) {
      let x = focus.reduce((s, l) => s + l.x, 0) / focus.length, y = focus.reduce((s, l) => s + l.y, 0) / focus.length;
      x += (B.x - x) * 0.3; y += (B.y - y) * 0.3 - 16;
      this.camX += (x - this.camX) * Math.min(1, dtReal * 5); this.camY += (y - this.camY) * Math.min(1, dtReal * 5);
      this.cameras.main.centerOn(Math.round(this.camX), Math.round(this.camY));
    }

    // tell the server where this browser's heroes are, 20 times a second
    if (now - this.lastReport > 0.05) {
      this.lastReport = now;
      for (const l of this.local) this.net.send(l.report());
    }
    this.cfg.onFrame && this.cfg.onFrame(this);
  }
}
