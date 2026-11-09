// Heroes in a fight. LocalHero is one this browser drives (its device's inputs, predicted at once and
// reported to the server 20 times a second); RemoteHero draws someone else's from the snapshots, 100 ms
// in the past. Both draw with heroPose(), from an animation name and the time into it.
//
// Weapons (app/kingfall/content/weapons.py) swing shapes, fire projectiles (`proj`), drop delayed
// area hits (`aoe`), blink, leap (`air`: untouchable) or shrug off hits (`hyper`). Each has its own
// defensive move: block, dash, counter, blink or rollshot.
import { Rig, sample, runCycle, rigDefaults, atlas } from './rig.js?v=2';
import { placeAttack, touches, wrap } from './moves.js?v=2';

export function heroFrames(h, W) {
  const p = `${h.look}.${h.colour}.`;
  const f = {};
  for (const k of ['cape', 'arm_b', 'leg_b', 'leg_f', 'torso', 'head', 'arm_f']) f[k] = p + k;
  f.weapon = 'w.' + W.art;
  if (W.offhand) {
    const coloured = `w.${W.offhand}.${h.colour}`;
    f.shield = atlas().frames[coloured] ? coloured : `w.${W.offhand}`;
  }
  return f;
}

const leapZ = (atk, at) => (atk && atk.air && at >= atk.air[0] && at <= atk.air[1]) ? Math.sin((at - atk.air[0]) / (atk.air[1] - atk.air[0]) * Math.PI) * 34 : 0;

// The rig pose for an animation `an` at `at` seconds in, a body roll angle (rolls, falling down) and
// a height (leaps).
export function heroPose(W, HERO, an, at) {
  let p, spin = 0, z = 0;
  const D = rigDefaults('hero');
  if (an[0] === 'l' && /^l\d+$/.test(an)) return { p: sample(W.light[Math.min(+an.slice(1), W.light.length - 1)].anim, at, D), spin, z };
  switch (an) {
    case 'run': p = runCycle(at * 13); break;
    case 'walk': p = runCycle(at * 9, 0.55); break;
    case 'roll': {
      const u = Math.min(1, at / HERO.roll.dur);
      p = { torso: 40, head: 20, leg_f: -60, leg_b: -40, arm_f: -40, arm_b: -60, cape: 50, dy: 4 };
      spin = 360 * u;
      break;
    }
    case 'dash': p = { torso: 24, lean: 6, head: 10, leg_f: 40, leg_b: -40, arm_f: 30, arm_b: 40, cape: 50 }; break;
    case 'blink': p = { torso: 10, cape: 40 }; break;
    case 'hc': p = { ...W.heavy.hold, lean: Math.sin(at * 60) * (at > W.heavy.charge ? 0.8 : 0.3) }; break;
    case 'hv': p = sample(W.heavy.anim, at, D); break;
    case 'sp': p = sample(W.special.anim, at, D); z = leapZ(W.special, at); break;
    case 'cs': p = { ...W.guard.anim, arm_f: -90, weapon: -90, torso: 12, lean: 6 }; break;
    case 'blk': case 'cnt': p = { ...W.guard.anim }; break;
    case 'blkw': p = { ...W.guard.anim, ...runCycle(at * 7, 0.35), arm_b: W.guard.anim.arm_b }; break;
    case 'drink': p = { arm_f: -150 - Math.sin(at * 9) * 6, weapon: 150, head: -12, torso: -4 }; break;
    case 'hurt': p = { torso: -16, head: -12, lean: -3, arm_f: 20, arm_b: 30 }; break;
    case 'down': p = { torso: 0, head: -10, arm_f: -30, arm_b: 40, leg_f: 10, leg_b: -6 }; spin = -90; break;
    case 'dead': p = { torso: 0, head: -20, arm_f: -50, arm_b: 60 }; spin = -90; break;
    default: p = { torso: Math.sin(at * 2.2) * 1.5, head: Math.sin(at * 2.2 + 0.5) * 1.5, cape: 4 + Math.sin(at * 1.6) * 3 };
  }
  return { p, spin, z };
}

// Places a rig's container at feet (x, y), spinning about its middle for rolls and falls.
function placeRig(rig, x, y, spin, left) {
  const c = rig.c;
  if (!spin) { c.x = Math.round(x); c.y = Math.round(y); c.angle = 0; return; }
  const s = left ? -spin : spin;
  const r = s * Math.PI / 180, cy = spin === -90 || spin === 90 ? -6 : -18;
  const ox = Math.sin(r) * cy, oy = cy - Math.cos(r) * cy;
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
    const { p, spin, z } = heroPose(this.W, this.HERO, an, at);
    this.rig.pose(p, left);
    placeRig(this.rig, x, y - z, spin, left);
    this.shadow.setPosition(x, y).setScale(1 - z / 80); this.ring.setPosition(x, y);
    this.rig.c.setDepth(y); this.shadow.setDepth(1); this.ring.setDepth(1.1);
    this.rig.setTint(flash ? 0xffffff : null);
    this.rig.c.alpha = an === 'roll' || an === 'dash' ? 0.85 : an === 'blink' ? 0.4 : 1;
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
    this.maxSt = this.S.stamina || this.HERO.stamina;
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
    this.shots = [];      // this hero's projectiles in flight
    this.aoes = [];       // area hits waiting to land (arrow rain)
    const G = this.W.guard;
    this.dashes = (G.charges || 0) + (this.S.dash_charges || 0); this.dashT = 0;
  }

  an() {
    switch (this.state) {
      case 'atk': return 'l' + this.combo;
      case 'heavy': return 'hv';
      case 'charge': return 'hc';
      case 'special': return 'sp';
      case 'cstrike': return 'cs';
      case 'block': return Math.hypot(this.vx, this.vy) > 5 ? 'blkw' : 'blk';
      default: return this.state;
    }
  }

  // a roll's or dash's or blink's invulnerability, or a leap's
  invulnerable() {
    if (this.state === 'roll') {
      const [a, b] = this.HERO.roll.iframes;
      return this.t >= a && this.t <= b + (this.S.iframes || 0);
    }
    if (this.state === 'dash') return this.t <= this.W.guard.dur - 0.04 + (this.S.iframes || 0);
    if (this.state === 'blink') return true;
    if (this.state === 'special' && this.W.special.air) return this.t >= this.W.special.air[0] && this.t <= this.W.special.air[1];
    return false;
  }
  specialCost() { return this.W.special.focus * (this.S.special_cost || 1); }

  spend(n) {
    if (this.st <= 0) return false;
    this.st -= n; this.stWait = this.HERO.st_delay;
    return true;
  }

  update(dt, ctx) {
    const d = ctx.input.get(this.dev);
    const H = this.HERO, W = this.W, G = W.guard;
    this.t += dt; this.anT += dt;
    this.flash = Math.max(0, this.flash - dt);
    if (this.stWait > 0) this.stWait -= dt; else this.st = Math.min(this.maxSt, this.st + H.st_regen * (this.S.st_regen || 1) * dt);
    const maxDash = (G.charges || 0) + (this.S.dash_charges || 0);
    if (this.dashes < maxDash && (this.dashT += dt) >= G.recharge) { this.dashes++; this.dashT = 0; }
    this.stepShots(dt, ctx);
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
    const busy = ['atk', 'heavy', 'special', 'roll', 'dash', 'hurt', 'cstrike'].includes(this.state) && !(this.state === 'atk' && this.t < 0.05);
    if (want !== null && !busy) this.aim = want;

    const move = d.move;
    const speedK = this.S.speed || 1;
    let speed = H.speed * speedK;
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
      case 'roll': case 'dash': case 'blink': {
        const dur = this.state === 'roll' ? H.roll.dur : this.state === 'dash' ? G.dur : 0.16;
        if (this.state !== 'blink') {
          const dist = this.state === 'roll' ? H.roll.dist : G.dist, u = this.t / dur;
          const sp = dist / dur * (u < 0.75 ? 1.15 : 0.45);
          this.x += Math.cos(this.rollDir) * sp * dt; this.y += Math.sin(this.rollDir) * sp * dt;
        }
        if (this.t >= dur) {
          setState('idle');
          if (this.S.dodge) ctx.send({ t: 'dodge', h: this.id, x0: Math.round(this.rollFrom[0]), y0: Math.round(this.rollFrom[1]), x1: Math.round(this.x), y1: Math.round(this.y) });
          if (G.kind === 'rollshot') this.fire({ v: 380, r: 4, life: 0.9 }, 'guard', ctx);
        }
        speed = 0;
        break;
      }
      case 'atk': case 'heavy': case 'special': case 'cstrike': {
        const atk = this.attackData();
        if (this.t < atk.hit[1] && atk.step) { // a step as you swing (back, for some)
          const s = atk.step / atk.hit[1];
          this.x += Math.cos(this.aim) * s * dt; this.y += Math.sin(this.aim) * s * dt;
        }
        this.checkHit(atk, ctx);
        if (this.state !== 'cstrike') {
          if (d.pressed('light')) this.queued = 'light';
          if (d.pressed('dodge')) this.queued = 'dodge';
          if (d.pressed('heavy')) this.queued = 'heavy';
        }
        if (this.state === 'atk' && this.queued && this.t >= atk.next) {
          const q = this.queued; this.queued = null;
          if (q === 'light' && this.combo < W.light.length - 1) { this.startLight(this.combo + 1); break; }
          if (q === 'dodge') { this.tryRoll(move, ctx); break; }
          if (q === 'heavy') { setState('charge'); this.charge = 0; break; }
        }
        if (this.t >= atk.dur) {
          const q = this.queued; this.queued = null;
          this.comboWait = 0.45;
          setState('idle');
          if (q === 'dodge') this.tryRoll(move, ctx);
          else if (q === 'light') this.startLight(this.combo < W.light.length - 1 ? this.combo + 1 : 0);
        }
        speed = 0;
        break;
      }
      case 'charge':
        this.charge = Math.min(W.heavy.charge, this.charge + dt);
        speed = H.speed * speedK * 0.25;
        if (!d.held('heavy')) {
          if (this.spend(W.heavy.st)) { this.chargeU = this.charge / W.heavy.charge; this.startAttack('heavy'); }
          else setState('idle');
        } else if (d.pressed('dodge')) this.tryRoll(move, ctx);
        break;
      case 'drink':
        speed = H.speed * speedK * H.flask.speed;
        if (this.t >= H.flask.dur) setState('idle');
        if (d.pressed('dodge')) this.tryRoll(move, ctx);
        break;
      case 'block':
        speed = H.speed * speedK * G.speed;
        if (!d.held('block')) setState('idle');
        else if (d.pressed('dodge')) this.tryRoll(move, ctx);
        break;
      case 'cnt':  // the halberd's counter stance: anything that hits you now is answered
        speed = 0;
        if (this.t >= G.window) setState('idle');
        break;
      default: { // idle / run
        if (this.comboWait > 0) this.comboWait -= dt; else this.combo = 0;
        const moving = move.x || move.y;
        this.state = moving ? 'run' : 'idle';
        if (d.pressed('dodge')) { this.tryRoll(move, ctx); break; }
        if (d.pressed('light')) { this.startLight(this.comboWait > 0 && this.combo < W.light.length - 1 ? this.combo + 1 : 0); break; }
        if (d.pressed('heavy') && this.st > 0) { setState('charge'); this.charge = 0; break; }
        if (d.pressed('special') && this.focus >= this.specialCost()) { this.focus -= this.specialCost(); this.startAttack('special', ctx); break; }
        if (G.kind === 'block' && d.held('block')) { setState('block'); this.blockT = 0; break; }
        if (G.kind === 'counter' && d.pressed('block') && this.spend(G.st)) { setState('cnt'); break; }
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

  attackData() {
    const W = this.W;
    switch (this.state) {
      case 'atk': return W.light[this.combo];
      case 'heavy': return W.heavy;
      case 'special': return W.special;
      default: return { ...W.guard, dur: 0.45, hit: [0.08, 0.16], step: 14 };  // the counter-strike
    }
  }

  tryRoll(move, ctx) {
    const G = this.W.guard, dir = move.x || move.y ? Math.atan2(move.y, move.x) : this.aim;
    if (G.kind === 'dash') {
      if (this.dashes <= 0 || !this.spend(G.st * (this.S.roll_st || 1))) return;
      this.dashes--;
      this.state = 'dash';
    } else if (G.kind === 'blink') {
      if (!this.spend(G.st * (this.S.roll_st || 1))) return;
      this.rollFrom = [this.x, this.y];
      this.x += Math.cos(dir) * G.dist; this.y += Math.sin(dir) * G.dist;
      ctx && ctx.collide(this);
      ctx && ctx.onBlink(this);
      this.state = 'blink';
    } else {
      if (!this.spend(this.HERO.roll.st * (this.S.roll_st || 1))) return;
      this.state = 'roll';
    }
    if (G.kind !== 'blink') this.rollFrom = [this.x, this.y];
    this.rollDir = dir;
    if (move.x || move.y) this.aim = dir;
    this.t = 0; this.anT = 0; this.queued = null;
  }

  startLight(i) {
    if (!this.spend(this.W.light[i].st)) { this.state = 'idle'; return; }
    this.combo = i;
    this.startAttack('atk');
  }

  startAttack(kind, ctx) {
    this.state = kind; this.t = 0; this.anT = 0;
    this.swing = { seq: ++swingSeq, struck: new Set(), fired: false };
    const atk = this.attackData();
    if (atk.blink) {  // the daggers' shadowstep: appear beside your target first
      this.x += Math.cos(this.aim) * atk.blink; this.y += Math.sin(this.aim) * atk.blink;
      if (ctx) { ctx.collide(this); ctx.onBlink(this); }
    }
  }

  slot() { return { atk: 'light', heavy: 'heavy', special: 'special', cstrike: 'guard' }[this.state] || 'light'; }

  // one swing strikes each thing it touches once: a body (or one of its weak points), adds.
  // Ranged attacks fire their projectiles or call down their area hit instead.
  checkHit(atk, ctx) {
    if (this.t < atk.hit[0] || this.t > atk.hit[1]) return;
    const kind = this.slot();
    if (atk.proj) { if (!this.swing.fired) { this.swing.fired = true; this.fire(atk.proj, kind, ctx); } return; }
    if (atk.aoe) {
      if (!this.swing.fired) {
        this.swing.fired = true;
        const A = atk.aoe;
        this.aoes.push({ x: this.x + Math.cos(this.aim) * A.at, y: this.y + Math.sin(this.aim) * A.at, r: A.r, wait: A.delay, ticks: A.ticks, every: A.every, kind });
        ctx.send({ t: 'shot', h: this.id, k: 'aoe', x: Math.round(this.aoes.at(-1).x), y: Math.round(this.aoes.at(-1).y), r: A.r, life: A.delay + A.ticks * A.every });
      }
      return;
    }
    const s = placeAttack(reach(atk.shape, this.S.reach || 1), this.x, this.y, this.aim);
    this.strike(s, kind, this.swing, ctx);
  }

  // send a hit for everything shape s touches that this swing hasn't struck yet
  strike(s, kind, swing, ctx) {
    const base = { h: this.id, atk: kind, i: this.combo, c: this.chargeU || 0, sw: swing.seq };
    let any = false;
    for (const tg of ctx.boss.targets(ctx.now)) {
      const key = tg.kind === 'add' ? 'a' + tg.a : 'b' + tg.e;
      if (swing.struck.has(key) || !touches(s, tg.x, tg.y, tg.r)) continue;
      swing.struck.add(key);
      any = true;
      if (tg.kind === 'add') { ctx.send({ t: 'hitadd', a: tg.a, ...base }); tg.add.flash = 0.08; }
      else ctx.send({ t: 'hit', e: tg.e, core: tg.kind === 'core' ? tg.i : undefined, ...base });
      ctx.onHit(this, kind, tg);
    }
    return any;
  }

  fire(P, kind, ctx) {
    const n = P.n || 1;
    for (let i = 0; i < n; i++) {
      const a = this.aim + ((P.spread || 0) * (i - (n - 1) / 2)) * Math.PI / 180;
      const shot = { x: this.x + Math.cos(a) * 12, y: this.y + Math.sin(a) * 12, a, v: P.v, r: P.r, life: P.life, pierce: P.pierce, boom: P.boom,
        col: P.col, kind, combo: this.combo, c: this.chargeU || 0, swing: { seq: ++swingSeq, struck: new Set() } };
      this.shots.push(shot);
      ctx.send({ t: 'shot', h: this.id, k: 'proj', x: Math.round(shot.x), y: Math.round(shot.y), a: Math.round(a * 1000) / 1000, v: P.v, r: P.r, life: P.life, col: P.col });
    }
  }

  stepShots(dt, ctx) {
    for (const s of this.shots) {
      s.x += Math.cos(s.a) * s.v * dt; s.y += Math.sin(s.a) * s.v * dt; s.life -= dt;
      const shape = { k: 'circle', cx: s.x, cy: s.y, r: s.r };
      const saved = this.combo; this.combo = s.combo;
      const hit = this.strike(shape, s.kind, s.swing, ctx);
      this.combo = saved;
      if (hit && !s.pierce) {
        if (s.boom) this.strike({ k: 'circle', cx: s.x, cy: s.y, r: s.boom }, s.kind, { seq: ++swingSeq, struck: new Set(s.swing.struck) }, ctx);
        if (s.boom) ctx.onBoom(s.x, s.y, s.boom);
        s.life = 0;
      }
      if (s.life <= 0 && s.boom && !hit) { this.strike({ k: 'circle', cx: s.x, cy: s.y, r: s.boom }, s.kind, s.swing, ctx); ctx.onBoom(s.x, s.y, s.boom); }
    }
    this.shots = this.shots.filter(s => s.life > 0);
    for (const A of this.aoes) {
      A.wait -= dt;
      if (A.wait <= 0 && A.ticks > 0) {
        A.ticks--; A.wait = A.every;
        this.strike({ k: 'circle', cx: A.x, cy: A.y, r: A.r }, A.kind, { seq: ++swingSeq, struck: new Set() }, ctx);
      }
    }
    this.aoes = this.aoes.filter(A => A.ticks > 0);
  }

  // a boss hit reached this hero on this browser: returns 'parry', 'block', 'counter' or 'hurt' (or null)
  takeHit(h, bossX, bossY) {
    if (this.down || this.dead || this.invulnerable()) return null;
    const W = this.W, G = W.guard;
    const toBoss = Math.atan2(bossY - this.y, bossX - this.x);
    if (this.state === 'block' && !h.unblock) {
      if (Math.abs(wrap(toBoss - this.aim)) <= G.arc * (this.S.guard_arc || 1) * Math.PI / 180) {
        if (this.blockT <= G.parry && !h.noparry) return 'parry';
        const cost = h.dmg * G.st_per_dmg * (this.S.block_st || 1);
        if (this.st >= cost * 0.5) { this.st -= cost; this.stWait = this.HERO.st_delay; return 'block'; }
      }
    }
    if (this.state === 'cnt' && !h.unblock) {  // answered: no damage, and a strike back
      this.aim = toBoss;
      this.state = 'cstrike'; this.t = 0; this.anT = 0;
      this.swing = { seq: ++swingSeq, struck: new Set(), fired: false };
      return 'counter';
    }
    this.flash = 0.12;
    if (this.state === 'heavy' && W.heavy.hyper) return 'hurt';  // hyper-armour: hurt, but no flinch
    const away = Math.atan2(this.y - bossY, this.x - bossX), kb = h.kb || 30;
    this.kb = { vx: Math.cos(away) * kb * 5, vy: Math.sin(away) * kb * 5, t: 0.2 };
    this.state = 'hurt'; this.t = 0; this.anT = 0;
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
