// Heroes in a fight. LocalHero is one this browser drives (its device's inputs, predicted at once and
// reported to the server 20 times a second); RemoteHero draws someone else's from the snapshots, 100 ms
// in the past. Both draw with heroPose(), from an animation name and the time into it.
import { Rig, sample, runCycle, rigDefaults } from './rig.js?v=2';
import { placeAttack, touches, wrap } from './moves.js?v=2';


export function heroFrames(h, W) {
  const p = `${h.look}.${h.colour}.`;
  const f = {};
  for (const k of ['cape', 'arm_b', 'leg_b', 'leg_f', 'torso', 'head', 'arm_f']) f[k] = p + k;
  f.weapon = 'w.' + W.art;
  if (W.offhand) f.shield = `w.${W.offhand}.${h.colour}`;
  return f;
}

// The rig pose for an animation `an` at `at` seconds in. Also returns a body roll angle (for rolls and
// falling down).
export function heroPose(W, HERO, an, at) {
  let p, spin = 0;
  const D = rigDefaults('hero');
  switch (an) {
    case 'run': p = runCycle(at * 13); break;
    case 'walk': p = runCycle(at * 9, 0.55); break;
    case 'roll': {
      const u = Math.min(1, at / HERO.roll.dur);
      p = { torso: 40, head: 20, leg_f: -60, leg_b: -40, arm_f: -40, arm_b: -60, cape: 50, dy: 4 };
      spin = 360 * u;
      break;
    }
    case 'l0': case 'l1': case 'l2': p = sample(W.light[+an[1]].anim, at, D); break;
    case 'hc': p = { ...W.heavy.hold, lean: Math.sin(at * 60) * (at > W.heavy.charge ? 0.8 : 0.3) }; break;
    case 'hv': p = sample(W.heavy.anim, at, D); break;
    case 'sp': p = sample(W.special.anim, at, D); break;
    case 'blk': p = { ...W.guard.anim }; break;
    case 'blkw': p = { ...W.guard.anim, ...runCycle(at * 7, 0.35), arm_b: W.guard.anim.arm_b }; break;
    case 'drink': p = { arm_f: -150 - Math.sin(at * 9) * 6, weapon: 150, head: -12, torso: -4 }; break;
    case 'hurt': p = { torso: -16, head: -12, lean: -3, arm_f: 20, arm_b: 30 }; break;
    case 'down': p = { torso: 0, head: -10, arm_f: -30, arm_b: 40, leg_f: 10, leg_b: -6 }; spin = -90; break;
    case 'dead': p = { torso: 0, head: -20, arm_f: -50, arm_b: 60 }; spin = -90; break;
    default: p = { torso: Math.sin(at * 2.2) * 1.5, head: Math.sin(at * 2.2 + 0.5) * 1.5, cape: 4 + Math.sin(at * 1.6) * 3 };
  }
  return { p, spin };
}

// Places a rig's container at feet (x, y), spinning about its middle for rolls and falls.
function placeRig(rig, x, y, spin, left) {
  const c = rig.c;
  if (!spin) { c.x = Math.round(x); c.y = Math.round(y); c.angle = 0; return; }
  const s = left ? -spin : spin;
  const r = s * Math.PI / 180, cy = spin === -90 || spin === 90 ? -6 : -18;
  // rotate about (0, cy): the container's origin moves around that point
  const ox = -Math.sin(r) * -cy * (left ? 1 : 1), oy = cy - Math.cos(r) * cy;
  c.angle = s;
  c.x = Math.round(x + ox); c.y = Math.round(y + oy + (Math.abs(spin) === 90 ? 2 : 0));
}

export class HeroView {
  constructor(scene, h, W, HERO) {
    this.W = W; this.HERO = HERO;
    this.rig = new Rig(scene, 'hero', heroFrames(h, W));
    this.shadow = scene.add.ellipse(0, 0, 18, 6, 0x000000, 0.35);
    this.ring = scene.add.ellipse(0, 0, 22, 9).setStrokeStyle(1, Phaser.Display.Color.HexStringToColor(h.colourHex).color, 0.85);
    this.colour = Phaser.Display.Color.HexStringToColor(h.colourHex).color;
  }
  draw(x, y, an, at, aim, flash) {
    const left = Math.cos(aim) < -0.05;
    const { p, spin } = heroPose(this.W, this.HERO, an, at);
    this.rig.pose(p, left);
    placeRig(this.rig, x, y, spin, left);
    this.shadow.setPosition(x, y); this.ring.setPosition(x, y);
    this.rig.c.setDepth(y); this.shadow.setDepth(1); this.ring.setDepth(1.1);
    this.rig.setTint(flash ? 0xffffff : null);
    this.rig.c.alpha = an === 'roll' ? 0.85 : 1;
  }
  destroy() { this.rig.destroy(); this.shadow.destroy(); this.ring.destroy(); }
}

let swingSeq = Math.floor(Math.random() * 1e6);

// an attack shape stretched by the hero's reach
function reach(shape, k) {
  if (k === 1) return shape;
  const s = { ...shape };
  for (const key of ['r', 'x1', 'x']) if (s[key] != null) s[key] *= k;
  return s;
}

export class LocalHero {
  constructor(scene, h, dev, data, x, y) {
    this.h = h; this.id = h.id; this.dev = dev;
    this.W = data.weapons[h.weapon]; this.HERO = data.hero;
    this.S = h.stats || {};   // the hero's build: see app/kingfall/build.py, Build.client
    const S = this.S;
    this.maxSt = S.stamina || this.HERO.stamina;
    this.view = new HeroView(scene, h, this.W, this.HERO);
    this.x = x; this.y = y; this.aim = -Math.PI / 2;
    this.st = this.maxSt; this.stWait = 0;
    this.perfects = new Set();
    this.focus = 40;
    this.state = 'idle'; this.t = 0; this.anT = 0;
    this.combo = 0; this.comboWait = 0; this.queued = null;
    this.charge = 0;
    this.vx = 0; this.vy = 0;
    this.kb = null;
    this.flash = 0;
    this.down = false; this.dead = false;
    this.reviveT = 0; this.reviving = null;
    this.locked = false;
    this.swing = null;
    this.blockT = 0;
    this.drinking = false;
  }

  an() {
    switch (this.state) {
      case 'atk': return 'l' + this.combo;
      case 'heavy': return 'hv';
      case 'charge': return 'hc';
      case 'special': return 'sp';
      case 'block': return Math.hypot(this.vx, this.vy) > 5 ? 'blkw' : 'blk';
      default: return this.state;
    }
  }

  invulnerable() {
    if (this.state !== 'roll') return false;
    const [a, b] = this.HERO.roll.iframes;
    return this.t >= a && this.t <= b + (this.S.iframes || 0);
  }
  specialCost() { return this.W.special.focus * (this.S.special_cost || 1); }

  spend(n) {
    if (this.st <= 0) return false;
    this.st -= n; this.stWait = this.HERO.st_delay;
    return true;
  }

  // ctx: {input, scene, boss: {x, y, r, alive}, world: {toWorld(screen)}, arena, send, allies}
  update(dt, ctx) {
    const d = ctx.input.get(this.dev);
    const H = this.HERO, W = this.W;
    this.t += dt; this.anT += dt;
    this.flash = Math.max(0, this.flash - dt);
    if (this.stWait > 0) this.stWait -= dt; else this.st = Math.min(this.maxSt, this.st + H.st_regen * (this.S.st_regen || 1) * dt);
    if (this.down || this.dead) { this.state = this.dead ? 'dead' : 'down'; this.vx = this.vy = 0; return; }
    if (!d) { this.vx = this.vy = 0; if (!['idle', 'run'].includes(this.state)) this.state = 'idle'; return; }

    // aim: the mouse, the right stick, or where you're walking; lock-on points at the boss
    if (d.pressed('lock')) this.locked = !this.locked;
    const boss = ctx.boss.nearest(this.x, this.y);
    let want = null;
    if (this.locked && boss.alive) want = Math.atan2(boss.y - this.y, boss.x - this.x);
    else if (d.id === 'kb' && d.mouse && ctx.world) {
      const w = ctx.world(d.mouse);
      want = Math.atan2(w.y - (this.y - 14), w.x - this.x);
    } else if (d.aim) want = Math.atan2(d.aim.y, d.aim.x);
    else if (d.move.x || d.move.y) want = Math.atan2(d.move.y, d.move.x);
    if (want !== null && d.id !== 'kb' && !this.locked && boss.alive) {
      // gentle aim assist on controllers: within 25° of the boss, aim at it
      const tb = Math.atan2(boss.y - this.y, boss.x - this.x);
      if (Math.abs(wrap(want - tb)) < 0.44) want = tb;
    }
    const busy = ['atk', 'heavy', 'special', 'roll', 'hurt'].includes(this.state) && !(this.state === 'atk' && this.t < 0.05);
    if (want !== null && !busy) this.aim = want;

    const move = d.move;
    let speed = H.speed * (this.S.speed || 1);
    const setState = s => { this.state = s; this.t = 0; this.anT = 0; };

    // knockback slides you whatever you're doing
    if (this.kb) {
      this.kb.t -= dt;
      this.x += this.kb.vx * dt; this.y += this.kb.vy * dt;
      if (this.kb.t <= 0) this.kb = null;
    }

    switch (this.state) {
      case 'hurt':
        if (this.t > 0.32) setState('idle');
        speed = 0;
        break;
      case 'roll': {
        const R = H.roll, u = this.t / R.dur;
        const sp = R.dist / R.dur * (u < 0.75 ? 1.15 : 0.45);
        this.x += Math.cos(this.rollDir) * sp * dt; this.y += Math.sin(this.rollDir) * sp * dt;
        if (this.t >= R.dur) {
          setState('idle');
          if (this.S.dodge) ctx.send({ t: 'dodge', h: this.id, x0: Math.round(this.rollFrom[0]), y0: Math.round(this.rollFrom[1]), x1: Math.round(this.x), y1: Math.round(this.y) });
        }
        speed = 0;
        break;
      }
      case 'atk': case 'heavy': case 'special': {
        const atk = this.state === 'atk' ? W.light[this.combo] : this.state === 'heavy' ? W.heavy : W.special;
        if (this.t < atk.hit[1]) { // a small step forward as you swing
          const s = atk.step / atk.hit[1];
          this.x += Math.cos(this.aim) * s * dt; this.y += Math.sin(this.aim) * s * dt;
        }
        this.checkHit(atk, ctx);
        if (d.pressed('light')) this.queued = 'light';
        if (d.pressed('dodge')) this.queued = 'dodge';
        if (d.pressed('heavy')) this.queued = 'heavy';
        if (this.state === 'atk' && this.queued && this.t >= atk.next) {
          const q = this.queued; this.queued = null;
          if (q === 'light' && this.combo < W.light.length - 1) { this.startLight(this.combo + 1); break; }
          if (q === 'dodge') { this.tryRoll(move); break; }
          if (q === 'heavy') { setState('charge'); this.charge = 0; break; }
        }
        if (this.t >= atk.dur) {
          const q = this.queued; this.queued = null;
          this.comboWait = 0.45;
          setState('idle');
          if (q === 'dodge') this.tryRoll(move);
          else if (q === 'light') this.startLight(this.state === 'idle' && this.combo < W.light.length - 1 ? this.combo + 1 : 0);
        }
        speed = 0;
        break;
      }
      case 'charge':
        this.charge = Math.min(W.heavy.charge, this.charge + dt);
        speed = H.speed * (this.S.speed || 1) * 0.25;
        if (!d.held('heavy')) {
          if (this.spend(W.heavy.st)) { this.chargeU = this.charge / W.heavy.charge; this.startAttack('heavy'); }
          else setState('idle');
        } else if (d.pressed('dodge')) this.tryRoll(move);
        break;
      case 'drink':
        speed = H.speed * (this.S.speed || 1) * H.flask.speed;
        if (this.t >= H.flask.dur) setState('idle');
        if (d.pressed('dodge')) this.tryRoll(move);
        break;
      case 'block':
        speed = H.speed * (this.S.speed || 1) * W.guard.speed;
        if (!d.held('block')) setState('idle');
        else if (d.pressed('dodge')) this.tryRoll(move);
        break;
      default: { // idle / run
        if (this.comboWait > 0) this.comboWait -= dt; else this.combo = 0;
        const moving = move.x || move.y;
        this.state = moving ? 'run' : 'idle';
        if (d.pressed('dodge')) { this.tryRoll(move); break; }
        if (d.pressed('light')) { this.startLight(this.comboWait > 0 && this.combo < W.light.length - 1 ? this.combo + 1 : 0); break; }
        if (d.pressed('heavy') && this.st > 0) { setState('charge'); this.charge = 0; break; }
        if (d.pressed('special') && this.focus >= this.specialCost()) { this.focus -= this.specialCost(); this.startAttack('special'); break; }
        if (d.held('block') && W.guard.kind === 'block') { setState('block'); this.blockT = 0; break; }
        if (d.pressed('heal') && this.h.flasks > 0) { setState('drink'); ctx.send({ t: 'drink', h: this.id }); break; }
      }
    }
    if (this.state === 'block') this.blockT += dt;

    // reviving a downed ally: stand by them and hold interact
    const fallen = ctx.allies.find(a => a.down && !a.dead && Math.hypot(a.x - this.x, a.y - this.y) < 30);
    if (fallen && d.held('interact') && ['idle', 'run'].includes(this.state)) {
      this.reviving = fallen.id; this.reviveT += dt; speed = 0;
      if (this.reviveT >= H.down.revive * (this.S.revive_time || 1)) { ctx.send({ t: 'revive', h: this.id, who: fallen.id }); this.reviveT = 0; }
    } else { this.reviving = null; this.reviveT = 0; }

    this.vx = move.x * speed; this.vy = move.y * speed;
    this.x += this.vx * dt; this.y += this.vy * dt;
    if (this.state === 'run' && !(move.x || move.y)) this.state = 'idle';
    ctx.collide(this);
  }

  tryRoll(move) {
    if (!this.spend(this.HERO.roll.st * (this.S.roll_st || 1))) return;
    this.rollFrom = [this.x, this.y];
    this.rollDir = move.x || move.y ? Math.atan2(move.y, move.x) : this.aim;
    if (move.x || move.y) this.aim = this.rollDir;
    this.state = 'roll'; this.t = 0; this.anT = 0; this.queued = null;
    this.drinking = false;
  }

  startLight(i) {
    if (!this.spend(this.W.light[i].st)) { this.state = 'idle'; return; }
    this.combo = i;
    this.startAttack('atk');
  }

  startAttack(kind) {
    this.state = kind; this.t = 0; this.anT = 0;
    this.swing = { seq: ++swingSeq, struck: new Set() };
  }

  // one swing strikes each thing it touches once: a body (or one of its weak points), adds
  checkHit(atk, ctx) {
    if (this.t < atk.hit[0] || this.t > atk.hit[1]) return;
    const s = placeAttack(reach(atk.shape, this.S.reach || 1), this.x, this.y, this.aim);
    const kind = this.state === 'atk' ? 'light' : this.state;
    const base = { h: this.id, atk: kind, i: this.combo, c: this.chargeU || 0, sw: this.swing.seq };
    for (const tg of ctx.boss.targets(ctx.now)) {
      const key = tg.kind === 'add' ? 'a' + tg.a : 'b' + tg.e;
      if (this.swing.struck.has(key) || !touches(s, tg.x, tg.y, tg.r)) continue;
      this.swing.struck.add(key);
      if (tg.kind === 'add') { ctx.send({ t: 'hitadd', a: tg.a, ...base }); tg.add.flash = 0.08; }
      else ctx.send({ t: 'hit', e: tg.e, core: tg.kind === 'core' ? tg.i : undefined, ...base });
      ctx.onHit(this, kind, tg);
    }
  }

  // a boss hit reached this hero on this browser: returns 'parry', 'block' or 'hurt' (or null: no effect)
  takeHit(h, bossX, bossY) {
    if (this.down || this.dead || this.invulnerable()) return null;
    const W = this.W;
    if (this.state === 'block' && !h.unblock) {
      const toBoss = Math.atan2(bossY - this.y, bossX - this.x);
      if (Math.abs(wrap(toBoss - this.aim)) <= W.guard.arc * (this.S.guard_arc || 1) * Math.PI / 180) {
        if (this.blockT <= W.guard.parry && !h.noparry) return 'parry';
        const cost = h.dmg * W.guard.st_per_dmg * (this.S.block_st || 1);
        if (this.st >= cost * 0.5) { this.st -= cost; this.stWait = this.HERO.st_delay; return 'block'; }
      }
    }
    const away = Math.atan2(this.y - bossY, this.x - bossX), kb = h.kb || 30;
    this.kb = { vx: Math.cos(away) * kb * 5, vy: Math.sin(away) * kb * 5, t: 0.2 };
    this.state = 'hurt'; this.t = 0; this.anT = 0;
    this.flash = 0.12;
    return 'hurt';
  }

  draw() { this.view.draw(this.x, this.y, this.an(), this.anT, this.aim, this.flash > 0); }
  report() { return { t: 'st', h: this.id, x: Math.round(this.x * 10) / 10, y: Math.round(this.y * 10) / 10, f: Math.round(this.aim * 100) / 100, an: this.an(), at: Math.round(this.anT * 100) / 100 }; }
}

export class RemoteHero {
  constructor(scene, h, data) {
    this.h = h; this.id = h.id;
    this.W = data.weapons[h.weapon]; this.HERO = data.hero;
    this.view = new HeroView(scene, h, this.W, this.HERO);
    this.buf = [];
    this.x = 0; this.y = 0; this.down = false; this.dead = false;
    this.flash = 0;
  }
  push(st, row) { this.buf.push([st, ...row]); if (this.buf.length > 30) this.buf.shift(); }
  // render time rt (server time 100 ms ago)
  draw(rt, dt) {
    this.flash = Math.max(0, this.flash - dt);
    const b = this.buf;
    if (!b.length) return;
    let i = b.findIndex(r => r[0] > rt);
    let row;
    if (i <= 0) row = i === 0 ? b[0] : b[b.length - 1];
    else {
      const a = b[i - 1], c = b[i], u = (rt - a[0]) / Math.max(1e-6, c[0] - a[0]);
      row = [...a]; row[2] = a[2] + (c[2] - a[2]) * u; row[3] = a[3] + (c[3] - a[3]) * u;
      row[6] = a[6] + (c[6] - a[6]) * u;
    }
    // [st, id, x, y, face, anim, at, hp, mhp, flasks, down, bleed, drinking]
    this.x = row[2]; this.y = row[3];
    const an = row[10] === 2 ? 'dead' : row[10] === 1 ? 'down' : row[5];
    this.view.draw(row[2], row[3], an, row[6], row[4], this.flash > 0);
  }
}
