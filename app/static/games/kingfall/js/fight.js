// The fight: a Phaser scene with the arena, the boss and every hero. This browser's heroes are moved
// here and their hits checked here (both ways); the server says what the boss does and keeps score.
import { addFrames } from './rig.js?v=22';
import { LocalHero, RemoteHero } from './hero.js?v=22';
import { Boss } from './boss.js?v=22';
import { drawArena } from './arenas.js?v=22';
import { sfx } from './audio.js?v=22';
import { music } from './music.js?v=22';
import { deviceOfSlot } from './input.js?v=22';
import { orb, arrow, impact, pillar, allyArea } from './fx.js?v=22';

const INTERP = 0.1;
const NO_INPUT = { get: () => null };   // while the menu is open the heroes stand idle (the fight doesn't stop)
// an area hit's colour: the skill's, or gold for a weapon's (arrow rain)
const aoeCol = col => col ? Phaser.Display.Color.HexStringToColor(col).color : 0xffd23f;

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
    const A = drawArena(fight.arena, w, h, fight.pad);
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
    // darkness (the Briar Wolf's and the Moth Saint's second phase): black, but for light round the heroes
    this.darkAt = this.boss.B.dark || 0;
    this.dark = this.add.renderTexture(0, 0, w, h).setOrigin(0).setDepth(5500).setVisible(false);
    this.darkness = 0;
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
    this.sparks = this.add.graphics().setDepth(6000).setBlendMode(Phaser.BlendModes.ADD);
    this.shotG = this.add.graphics().setDepth(5600);                                         // arrows' shafts, area rims
    this.shotGlow = this.add.graphics().setDepth(5601).setBlendMode(Phaser.BlendModes.ADD);  // everything that glows
    this.shotFloor = this.add.graphics().setDepth(2.5);                                      // their shadows
    this.remoteShots = []; this.rings = []; this.pillars = [];
    this.sparkList = [];
    this.impacts = [];     // where a hero's hit landed: a flash and a cut across it
    this.reviveG = this.add.graphics().setDepth(6001);
    const cam = this.cameras.main;
    cam.setZoom(this.cfg.zoom());  // the canvas is at screen resolution; the camera does the magnifying
    cam.setBounds(0, 0, w, h + 56);  // room below the floor, so heroes at the bottom wall aren't under the HUD's panels
    cam.setBackgroundColor('#0c0a10');
    this.camX = w / 2; this.camY = h / 2;
    this.lastReport = 0;
    this.stop = 0;
    this.started = this.net.now();
    this.ended = false;
    music.play(fight.boss, 1);
    this.cfg.onReady && this.cfg.onReady(this);
  }

  world(screen) {
    const cam = this.cameras.main, canvas = this.game.canvas, r = canvas.getBoundingClientRect();
    const sx = (screen.x - r.left) / r.width * this.scale.width, sy = (screen.y - r.top) / r.height * this.scale.height;
    const p = cam.getWorldPoint(sx, sy);
    return { x: p.x, y: p.y };
  }

  collide(hero) {
    const [w, h] = this.size, [l, t, r, b] = this.pad, R = hero.HERO.radius;
    const now = this.net.now();
    for (const B of this.boss.bodies) {
      if (!B.alive || B.untouchable(now, B.mv) || B.z > 10) continue;
      const dx = hero.x - B.x, dy = hero.y - B.y, d = Math.hypot(dx, dy), min = B.r + R - 2;
      if (d < min && hero.state !== 'roll') {
        const k = d > 0.01 ? (min - d) / d : 1;
        hero.x += dx * k; hero.y += (d > 0.01 ? dy : 1) * k;
      }
    }
    hero.x = Math.max(l + R, Math.min(w - r - R, hero.x));
    hero.y = Math.max(t + R, Math.min(h - b - R, hero.y));
  }

  pan(x) { const v = this.cameras.main.worldView, hw = v.width / 2 || 320; return Math.max(-0.8, Math.min(0.8, (x - v.centerX) / hw)); }

  // ------------------------------------------------------------------ server messages
  onMsg(m) {
    const B = this.boss;
    switch (m.t) {
      case 's': {
        B.onSnap(m.st, m.b, m.a);
        for (const row of m.h) {
          const [id, x, y, , , , hp, mhp, flasks, down, bleed] = row;
          this.heroRows[id] = { hp, mhp, flasks, down, bleed, shield: row[12] || 0, rally: row[13] || 0, emp: row[14] || 0 };
          if (this.byId[id]) { this.byId[id].view.st = down ? null : this.heroRows[id]; this.byId[id].view.hp = [hp, mhp]; }
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
    const B = this.boss.bodies[m.e || 0] || this.boss.bodies[0], mine = this.local.find(l => l.id === m.h);
    switch (m.k) {
      case 'hit': case 'crit':
        B.flash = 0.04;
        this.number(B.x + (Math.random() - 0.5) * 16, B.y - 70, m.dmg, m.k === 'crit' ? '#ffd23f' : '#f4f0e0', m.k === 'crit');
        if (mine) mine.focus = Math.min(mine.HERO.focus, mine.focus + m.dmg * mine.HERO.focus_per_dmg * (mine.S.focus_gain || 1) + (mine.state === 'special' ? mine.S.focusback || 0 : 0));
        if (m.k === 'crit') { sfx.crit(this.pan(B.x)); this.cameras.main.shake(180, 0.008); this.burst(B.x, B.y - 40, 0xffd23f, 26); }
        else if (!mine) sfx.hit(this.pan(B.x));
        if (!mine && this.remote[m.h]) {  // someone else's hit: the cut where it landed, facing from them
          const r = this.remote[m.h], a = Math.atan2(B.y - r.y, B.x - r.x);
          this.impact(B.x - Math.cos(a) * Math.min(B.r, 14), B.y - 30, a, m.k === 'crit', r.view.colour);
        }
        break;
      case 'guarded':
        sfx.guarded(this.pan(B.x)); this.burst(B.x + Math.cos(B.face) * 18, B.y - 30, 0xffffff, 8);
        if (mine) mine.h && (mine.flash = 0);
        this.number(B.x, B.y - 74, 'Guarded', '#a8b0bc');
        break;
      case 'shot':
        if (this.local.some(l => l.id === m.h)) break;  // ours are drawn already
        this.remoteShots.push({ ...m, k: m.k2 });
        if (m.k === 'proj') sfx.swing(this.pan(m.x));
        break;
      case 'skill': {  // someone used a skill: a ring in its colour (as wide as its reach to allies) and its name
        const K = this.data.skills[m.sk];
        if (!K) break;
        this.rings.push({ x: m.x, y: m.y, r: K.radius || 26, life: 0.3, col: Phaser.Display.Color.HexStringToColor(K.col).color });
        this.number(m.x, m.y - 58, K.name, K.col, true);
        if (K.heal) break;  // the heal has its own sound
        K.ward ? sfx.clang(this.pan(m.x)) : K.rally ? sfx.parry(this.pan(m.x)) : K.blink ? 0 : sfx.heavySwing(this.pan(m.x));
        break;
      }
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
        B.staggerDur = m.dur || 5; B.staggerT = 0; this.burst(B.x, B.y - 40, 0xffd23f, 24); this.cameras.main.shake(160, 0.006);
        this.cameras.main.shake(140, 0.006);
        break;
      case 'parry':
        sfx.parry(this.pan(m.x)); this.burst(m.x, m.y - 20, 0xfff0c0, 18);
        this.number(m.x, m.y - 46, 'Parry!', '#fff0c0', true);
        this.stop = 0.12;
        break;
      case 'block': sfx.clang(this.pan(m.x)); this.burst(m.x, m.y - 18, 0xe8ecf2, 8); break;
      case 'warded': sfx.clang(this.pan(m.x)); this.burst(m.x, m.y - 18, 0xa8b0bc, 10); this.number(m.x, m.y - 46, 'Warded', '#a8b0bc'); break;
      case 'hurt':
        sfx.hurt(this.pan(m.x));
        this.number(m.x, m.y - 46, m.dmg, '#e05050');
        if (mine) { this.cameras.main.shake(120, 0.006); this.cfg.input.rumble(mine.dev, 0.7, 160); }
        else if (this.remote[m.h]) this.remote[m.h].flash = 0.12;
        break;
      case 'heal': sfx.heal(); this.burst(m.x, m.y - 20, 0x8be04e, 14); break;
      case 'down': sfx.down(); this.number(m.x, m.y - 46, 'Down!', '#e05050', true); if (mine) mine.down = true; break;  // at once, not at the next snapshot
      case 'unbowed': sfx.parry(this.pan(m.x)); this.number(m.x, m.y - 56, 'Unbowed', '#b8c0cc', true); this.burst(m.x, m.y - 20, 0xb8c0cc, 16); break;
      case 'secondwind': this.number(this.byId[m.h]?.x || 0, (this.byId[m.h]?.y || 0) - 56, 'Second Wind', '#ffd23f', true); break;
      case 'revive': sfx.revive(); this.burst(m.x, m.y - 20, 0xffd23f, 16); break;
      case 'core':
        this.burst(m.x, m.y - 10, 0xa0e0ff, 10); sfx.clang(this.pan(m.x));
        this.number(m.x, m.y - 30, m.left > 0 ? m.dmg : 'Broken!', '#a0e0ff', m.left <= 0);
        if (m.left <= 0) this.cameras.main.shake(160, 0.006);
        break;
      case 'topple':
        sfx.slam(this.pan(B.x)); this.number(B.x, B.y - 96, 'TOPPLED', '#ffd23f', true); this.cameras.main.shake(400, 0.012);
        break;
      case 'addhit': { const a = this.boss.adds[m.a]; if (a) a.flash = 0.08; this.number(m.x, m.y - 24, m.dmg, '#f4f0e0'); break; }
      case 'adddie': this.burst(m.x, m.y - 10, 0xc8c0b0, 10); break;
      case 'bodydown':
        if (this.boss.bodies.length > 1) { sfx.slam(this.pan(m.x)); this.number(m.x, m.y - 90, 'FELLED', '#ffd23f', true); }
        break;
      case 'bossdown':
        sfx.bossDown(); this.cameras.main.shake(400, 0.01); this.burst(m.x, m.y - 40, 0xff7a1a, 40);
        this.cfg.onBanner && this.cfg.onBanner('won');
        break;
      case 'wipe': sfx.wipe(); for (const l of this.local) if (!l.dead) l.down = true; this.cfg.onBanner && this.cfg.onBanner('lost'); break;
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

  // a hero's projectile: a glowing bolt (it has a colour) or an arrow
  drawShot(x, y, a, r, col) {
    if (col) orb(this.shotGlow, this.shotFloor, x, y, a, r + 1, Phaser.Display.Color.HexStringToColor(col).color, { lift: 14 });
    else arrow(this.shotGlow, this.shotG, this.shotFloor, x, y, a);
  }

  // a cut across the spot a hit landed: a white flash, a slash line across the aim and a ring
  impact(x, y, a, big, colour) { this.impacts.push({ x, y, a: a + Math.PI / 2 + (Math.random() - 0.5) * 0.6, big, colour, life: 0.2 }); }

  // a called-down area hit lands (Judgement): the beam, sparks and a thump
  pillarAt(x, y, r, col) {
    const c = aoeCol(col);
    this.pillars.push({ x, y, r, col: c, life: 0.35 });
    this.burst(x, y - 6, c, 18); sfx.slam(this.pan(x)); this.cameras.main.shake(120, 0.005);
  }

  burst(x, y, colour, n) {
    for (let i = 0; i < n; i++) {
      const a = Math.random() * Math.PI * 2, s = 40 + Math.random() * 120;
      const life = 0.25 + Math.random() * 0.3;
      this.sparkList.push({ x, y, vx: Math.cos(a) * s, vy: Math.sin(a) * s - 30, life, max: life, colour });
    }
  }

  // a local hero's attack connected (before the server's word, so it feels instant)
  onHit(hero, kind, tg) {
    sfx.hit(this.pan(tg.x));
    const ix = tg.x - Math.cos(hero.aim) * Math.min(tg.r, 14), iy = tg.y - (tg.up ? 0 : tg.kind === 'body' && !tg.seg ? 30 : 10);
    const small = kind === 'light' || kind.startsWith('proc:');   // an upgrade's extra hit lands as lightly as a light
    this.burst(ix, iy, 0xfff0c0, small ? 6 : 12);
    this.impact(ix, iy, hero.aim, !small, hero.view ? hero.view.colour : 0xffffff);
    if (tg.b) tg.b.flash = 0.04;
    this.stop = Math.max(this.stop, small ? 0.045 : 0.08);
    this.cfg.input.rumble(hero.dev, small ? 0.25 : 0.5, 70);
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
      input: this.cfg.menuOpen && this.cfg.menuOpen() ? NO_INPUT : this.cfg.input, boss: B, now, world: s => this.world(s), send: m => this.net.send(m),
      collide: h => this.collide(h), onHit: (h, k, tg) => this.onHit(h, k, tg), allies,
      onBlink: h => { this.burst(h.x, h.y - 18, 0xc8b4ff, 12); sfx.roll(this.pan(h.x)); },
      onDenied: () => sfx.uiBack(),
      onCharged: h => { this.burst(h.x, h.y - 22, h.view.colour, 10); sfx.ui(); },
      onPillar: (x, y, r, col) => this.pillarAt(x, y, r, col),
      onBoom: (x, y, r, col) => { const c = col ? aoeCol(col) : 0xc080ff; this.burst(x, y - 8, c, col ? 12 : 20); this.rings.push({ x, y, r, life: 0.3, col: c }); sfx.slam(this.pan(x)); },
    };
    for (const l of this.local) {
      const before = l.state;
      l.update(dt, ctx);
      if (l.state !== before) {
        if (l.state === 'roll') sfx.roll(this.pan(l.x));
        else if (l.state === 'atk' || l.state === 'special' || l.state === 'skill') sfx.swing(this.pan(l.x));
        else if (l.state === 'heavy') sfx.heavySwing(this.pan(l.x));
      } else if (l.state === 'atk' && l.t < dt * 1.5 && l.t > 0) sfx.swing(this.pan(l.x));
    }
    B.update(now, dtReal);
    // the boss's hits against this browser's heroes (the dodger decides)
    for (const l of this.local) {
      B.checkHero(now, l, (h, id, bx, by) => {
        if (l.invulnerable() && !l.perfects.has(id)) {  // rolled clean through it
          l.perfects.add(id);
          if (l.S.perfect_dash) { l.dashes = Math.min(l.maxDash, l.dashes + l.S.perfect_dash); this.number(l.x, l.y - 50, 'Perfect', '#fff0c0'); }
          this.net.send({ t: 'perfect', h: l.id });
          l.proc('perfect', ctx);
        }
        const r = l.takeHit(h, bx, by);
        if (!r) return false;
        this.net.send({ t: 'hurt', h: l.id, id, block: r === 'block' || r === 'counter' ? 1 : 0, parry: r === 'parry' ? 1 : 0, counter: r === 'counter' ? 1 : 0 });
        if (r === 'counter') { sfx.parry(this.pan(l.x)); this.number(l.x, l.y - 46, 'Counter!', '#fff0c0', true); }
        if (r === 'parry') this.stop = 0.12;
        if (r !== 'hurt') l.proc('guard', ctx);
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

    // projectiles and area hits: this browser's, and others' (relayed by the server)
    const sg = this.shotG;
    sg.clear(); this.shotGlow.clear(); this.shotFloor.clear();
    const cam0 = this.cameras.main, z = this.cfg.zoom();
    if (cam0.zoom !== z) cam0.setZoom(z);
    for (const l of this.local) {
      for (const s of l.shots) this.drawShot(s.x, s.y, s.a, s.r, s.col);
      for (const A of l.aoes) {
        // heroes' areas are dashed rings, never filled (fx.js, allyArea): bosses' are the solid ones
        allyArea(sg, this.shotGlow, { cx: A.x, cy: A.y, r: A.r }, aoeCol(A.col), 1, time / 1000, !!A.pool || A.ticks > 1);
      }
    }
    this.remoteShots = this.remoteShots.filter(s => {
      s.life -= dtReal;
      if (s.k === 'proj') { s.x += Math.cos(s.a) * s.v * dtReal; s.y += Math.sin(s.a) * s.v * dtReal; this.drawShot(s.x, s.y, s.a, s.r, s.col); }
      else {
        const c = aoeCol(s.col);
        allyArea(sg, this.shotGlow, { cx: s.x, cy: s.y, r: s.r }, c, Math.min(1, s.life * 3 + 0.2), time / 1000, s.p === 2);
        if (s.p && s.life <= 0) this.pillarAt(s.x, s.y, s.r, s.col);
      }
      return s.life > 0;
    });
    this.rings = this.rings.filter(r => {
      r.life -= dtReal;
      const u = 1 - r.life / 0.3, gl = this.shotGlow, c = r.col ?? 0xc080ff;
      gl.fillStyle(c, 0.3 * (1 - u)).fillCircle(r.x, r.y, r.r * (0.4 + 0.6 * u));
      gl.lineStyle(1 + 4 * (1 - u), c, 0.9 * (1 - u)).strokeCircle(r.x, r.y, r.r * (0.4 + 0.6 * u));
      gl.lineStyle(1, 0xffffff, 1 - u).strokeCircle(r.x, r.y, r.r * (0.4 + 0.6 * u) - 1);
      return r.life > 0;
    });

    this.pillars = this.pillars.filter(o => {
      o.life -= dtReal;
      pillar(this.shotGlow, o.x, o.y, o.r, 1 - o.life / 0.35, o.col);
      return o.life > 0;
    });

    // effects
    this.sparks.clear();
    this.sparkList = this.sparkList.filter(s => {
      s.life -= dtReal; s.x += s.vx * dtReal; s.y += s.vy * dtReal; s.vy += 220 * dtReal;
      // a short streak along its flight, thinning as it dies
      const k = Math.min(1, s.life / (s.max || 0.4) * 1.6);
      this.sparks.lineStyle(1.6 * k + 0.4, s.colour, k); this.sparks.lineBetween(s.x, s.y, s.x - s.vx * 0.035, s.y - s.vy * 0.035);
      return s.life > 0;
    });
    this.impacts = this.impacts.filter(o => {
      o.life -= dtReal;
      impact(this.sparks, o.x, o.y, o.a, 1 - o.life / 0.2, o.big, o.colour);
      return o.life > 0;
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

    if (this.darkAt) {
      const want = this.boss.bodies.some(b => b.phase >= this.darkAt && b.alive) ? 1 : 0;
      this.darkness += (want - this.darkness) * Math.min(1, dtReal * 1.5);
      this.dark.setVisible(this.darkness > 0.02);
      if (this.darkness > 0.02) {
        this.dark.clear().fill(0x05030a, 0.86 * this.darkness);
        for (const l of [...this.local, ...Object.values(this.remote)]) if (!l.dead) this.dark.erase('glow', l.x - 70, l.y - 90, 1).erase('glow', l.x - 50, l.y - 70);
        for (const b of this.boss.bodies) if (b.alive) this.dark.erase('glow', b.x - 32 + Math.cos(b.face) * 10, b.y - 70, 1);
        for (const L of this.lights) L.glow.setVisible(false);
      }
    }
    // camera: this browser's heroes, nudged toward the boss
    const live = this.local.filter(l => !l.dead);
    const focus = live.length ? live : this.local;
    if (focus.length) {
      let x = focus.reduce((s, l) => s + l.x, 0) / focus.length, y = focus.reduce((s, l) => s + l.y, 0) / focus.length;
      const nb = B.nearest(x, y);
      x += (nb.x - x) * 0.3; y += (nb.y - nb.z * 0.5 - y) * 0.3 + 8;
      this.camX += (x - this.camX) * Math.min(1, dtReal * 5); this.camY += (y - this.camY) * Math.min(1, dtReal * 5);
      this.cameras.main.centerOn(Math.round(this.camX * z) / z, Math.round(this.camY * z) / z);
    }

    // tell the server where this browser's heroes are, 20 times a second
    if (now - this.lastReport > 0.05) {
      this.lastReport = now;
      for (const l of this.local) this.net.send(l.report());
    }
    music.setLevel(this.boss.bodies.reduce((m, b) => Math.max(m, b.alive ? b.phase : 0), 1));
    this.cfg.onFrame && this.cfg.onFrame(this);
  }
}
