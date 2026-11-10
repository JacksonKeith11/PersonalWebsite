// Heroes in a fight. LocalHero is one this browser drives (its device's inputs, predicted at once and
// reported to the server 20 times a second); RemoteHero draws someone else's from the snapshots, 100 ms
// in the past. Both draw with heroPose(), from an animation name and the time into it.
//
// Weapons (app/kingfall/content/weapons.py) swing shapes, fire projectiles (`proj`), drop delayed
// area hits (`aoe`), blink, leap (`air`: untouchable) or shrug off hits (`hyper`). Each has its own
// defensive move: block, dash, counter, blink or rollshot.
//
// Skills (app/kingfall/content/skills.py) are played the same way, in state 'skill' (animation
// 'k_<id>'): a shape, a projectile or an area hit in the skill's colour, or nothing to hit at all
// (a blink, a cry). The hero's cooldowns live here; the server keeps its own and refuses early ones.
import { Rig, sample, runCycle, rigDefaults, atlas } from './rig.js?v=26';
import { placeAttack, touches, wrap } from './moves.js?v=26';
import { crescent, lance, burst } from './fx.js?v=26';

let SKILLS = {};   // the welcome's skills table, for poses and swings drawn from an animation's name
const hex = c => Phaser.Display.Color.HexStringToColor(c).color;

// A skill's casting pose: 'cast' draws the weapon hand back and thrusts it out, the weapon held upright, 'raise' lifts both arms, each reaching
// its height as the skill's hit begins (or a third of the way in) and easing back at the end.
function skillPose(S, at, D) {
  const t0 = S.hit ? S.hit[0] : S.dur * 0.3, t1 = Math.max(t0 + 0.12, S.hit ? S.hit[1] : S.dur * 0.6);
  const keys = S.pose === 'cast'
    ? [[0, { arm_f: 30, weapon: 60, arm_b: -20, torso: -14, lean: -3 }], [t0, { arm_f: -95, weapon: 150, arm_b: 30, torso: 16, lean: 6, head: 4 }],
       [t1, { arm_f: -95, weapon: 150, arm_b: 30, torso: 16, lean: 6, head: 4 }], [S.dur, {}]]
    : [[0, { arm_f: -60, arm_b: -60, torso: 6, dy: 2 }], [t0, { arm_f: -170, weapon: 170, arm_b: -170, shield: 170, torso: -8, head: -8 }],
       [t1, { arm_f: -170, weapon: 170, arm_b: -170, shield: 170, torso: -8, head: -8 }], [S.dur, {}]];
  return sample(keys, Math.min(at, S.dur), D);
}

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
  if (an[0] === 'k' && an[1] === '_') { const S = SKILLS[an.slice(2)]; return { p: S ? skillPose(S, at, D) : {}, spin, z }; }
  if (an[0] === 'l' && /^l\d+$/.test(an)) return { p: sample(W.light[Math.min(+an.slice(1), W.light.length - 1)].anim, at, D), spin, z };
  switch (an) {
    case 'run': p = runCycle(at * 13); break;
    case 'walk': p = runCycle(at * 9, 0.55); break;
    case 'roll': {
      const u = Math.min(1, at / HERO.roll.dur);
      p = { torso: 40, head: 20, leg_f: -60, leg_b: -40, arm_f: -40, arm_b: -60, cape: 50, dy: 4 };
      spin = 360 * (1 - (1 - u) * (1 - u));
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
    this.swingG = scene.add.graphics().setDepth(5100).setBlendMode(Phaser.BlendModes.ADD);
    this.barG = scene.add.graphics().setDepth(5050);   // the health bar over the head, the dashes under the feet
    this.hp = null;       // [health, most] from the server's snapshot (every hero)
    this.dash = null;     // [dashes, most]: only this browser's heroes know theirs
    this.reachK = 1;
  }
  draw(x, y, an, at, aim, flash) {
    this.drawSwing(x, y, an, at, aim);
    this.drawStatus(x, y);
    let left = Math.cos(aim) < -0.05;
    const A = an[0] === 'k' && SKILLS[an.slice(2)] && SKILLS[an.slice(2)].aoe;
    if (A && !A.at && at > 0.06) left = Math.floor((at - 0.06) / (A.every / 2)) % 2 === 1 ? !left : left;  // a whirl: the hero turns about with each strike
    const { p, spin, z } = heroPose(this.W, this.HERO, an, at);
    this.rig.pose(p, left);
    placeRig(this.rig, x, y - z, spin, left);
    this.shadow.setPosition(x, y).setScale(1 - z / 80); this.ring.setPosition(x, y);
    this.rig.c.setDepth(y); this.shadow.setDepth(1); this.ring.setDepth(1.1);
    this.rig.setTint(flash ? 0xffffff : null);
    const K = an[0] === 'k' && SKILLS[an.slice(2)];
    this.rig.c.alpha = an === 'roll' || an === 'dash' ? 0.85 : an === 'blink' || (K && K.blink) ? 0.4 : 1;
    this.drawBars(x, y, z, an);
  }
  destroy() { this.rig.destroy(); this.shadow.destroy(); this.ring.destroy(); this.swingG.destroy(); this.barG.destroy(); }

  // Health over the head (every hero: red, brighter under 30%, framed in the player's colour) and, for
  // this browser's heroes, their dashes under the feet: a pip each, the one coming back filling in grey.
  drawBars(x, y, z, an) {
    const g = this.barG;
    g.clear();
    if (!this.hp || an === 'down' || an === 'dead') return;
    const [hp, most] = this.hp, W = 26, hx = Math.round(x) - W / 2, hy = Math.round(y - z) - 57;
    const f = Math.max(0, Math.min(1, hp / Math.max(1, most)));
    g.fillStyle(0x0c0a10, 0.8); g.fillRect(hx - 1, hy - 1, W + 2, 5);
    g.fillStyle(f < 0.3 ? 0xff5a48 : 0xc84040, 1); g.fillRect(hx, hy, W * f, 3);
    g.lineStyle(1, this.colour, 0.9); g.strokeRect(hx - 1.5, hy - 1.5, W + 3, 6);
    if (!this.dash) return;
    const [n, max] = this.dash, pw = 7, gap = 2, dx = Math.round(x) - (max * pw + (max - 1) * gap) / 2, dy = Math.round(y) + 9;
    for (let i = 0; i < max; i++) {
      const k = Math.max(0, Math.min(1, n - i)), px = dx + i * (pw + gap);
      g.fillStyle(0x0c0a10, 0.8); g.fillRect(px - 1, dy - 1, pw + 2, 4);
      g.fillStyle(k >= 1 ? 0xe8ecf2 : 0x7a7488, 1); g.fillRect(px, dy, pw * k, 2);
    }
  }

  // What's on the hero (this.st, from the server's snapshot): a ward is a pale shell round them, extra
  // damage a ring of embers turning at their feet, a charged next hit a violet spark circling the weapon hand.
  drawStatus(x, y) {
    const st = this.st, g = this.swingG, t = performance.now() / 1000;
    if (!st) return;
    if (st.shield > 0) {
      g.lineStyle(1.5, 0xa8b0bc, 0.55 + 0.2 * Math.sin(t * 4)); g.strokeEllipse(x, y - 16, 26, 38);
      g.fillStyle(0xa8b0bc, 0.07); g.fillEllipse(x, y - 16, 26, 38);
    }
    if (st.rally > 0) {
      g.lineStyle(1.5, 0xffb040, 0.6); g.strokeEllipse(x, y, 30, 12);
      for (let k = 0; k < 3; k++) { const a = t * 3 + k * 2.094; g.fillStyle(0xffb040, 0.9); g.fillCircle(x + Math.cos(a) * 15, y + Math.sin(a) * 6, 1.6); }
    }
    if (st.emp) {
      const a = t * 7;
      g.fillStyle(0xc8b4ff, 0.9); g.fillCircle(x + Math.cos(a) * 9, y - 20 + Math.sin(a) * 9, 2);
      g.fillStyle(0xffffff, 0.9); g.fillCircle(x + Math.cos(a) * 9, y - 20 + Math.sin(a) * 9, 1);
    }
  }

  // The swing's real hitbox, drawn as it plays (fx.js): a crescent sweeping across an arc, a spearhead
  // along a thrust, a burst for a slam, in the player's colour with a white-hot core, so you can see
  // exactly what a swing covers. Projectiles and called-down areas are drawn by the fight scene.
  drawSwing(x, y, an, at, aim) {
    const g = this.swingG;
    g.clear();
    const W = this.W;
    let atk = null, rev = false, colour = this.colour, k = this.reachK;
    if (an[0] === 'k' && an[1] === '_') {  // a skill: its own colour, and never stretched by the weapon's reach
      const S = SKILLS[an.slice(2)];
      if (!S) return;
      colour = hex(S.col); k = 1;
      if (S.shape) atk = S;
      else if (S.aoe && !S.aoe.at) {  // a whirl: one full turn of the blade for each strike
        const A = S.aoe, u = (at - S.hit[0] - A.delay) / A.every + 0.5, n = Math.min(Math.floor(u), A.ticks - 1);
        if (u >= 0 && u < A.ticks + 0.5) crescent(g, { cx: x, cy: y, a: aim, r: A.r, a0: -180, a1: 180 }, u < A.ticks ? u - n : 1 + (u - A.ticks) * 2, colour, { rev: n % 2 === 1 });
        return;
      } else return;
    }
    if (/^l\d+$/.test(an)) { const i = Math.min(+an.slice(1), W.light.length - 1); atk = W.light[i]; rev = i % 2 === 1; }
    else if (an === 'hv') atk = W.heavy;
    else if (an === 'sp') atk = W.special;
    else if (an === 'cs') atk = { shape: W.guard.shape, hit: [0.08, 0.16] };
    if (!atk || !atk.shape || atk.proj || atk.aoe) return;
    const [h0, h1] = atk.hit, pre = 0.03, after = 0.2;
    if (at < h0 - pre || at > h1 + after) return;
    // 0..1 across the strike, on to 2 as the trail dies away
    const p = at <= h1 ? (at - h0 + pre) / (h1 - h0 + pre) : 1 + (at - h1) / after;
    const s = placeAttack(reach(atk.shape, k), x, y, aim);
    if (s.k === 'arc') crescent(g, s, p, colour, { rev });
    else if (s.k === 'rect') lance(g, s, p, colour);
    else if (s.k === 'circle') burst(g, s, p, colour);
  }
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
    SKILLS = data.skills || {};
    this.skills = (h.skills || []).map(id => SKILLS[id]).filter(Boolean);  // slot 0 is skill1, slot 1 skill2
    this.skillCd = {};        // skill id -> seconds until it can be used again
    this.skill = null;        // the one being cast
    this.skillBuf = null;     // a skill pressed while busy: it fires as soon as the hero is free (within 0.4 s)
    this.denied = null;       // {id, until}: a skill pressed while cooling down (the HUD chip shakes)
    this.aimDist = null;      // how far away the thing aimed at is (the cursor, a locked-on boss), if known
    this.view = new HeroView(scene, h, this.W, this.HERO);
    this.x = x; this.y = y; this.aim = -Math.PI / 2;
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
    this.blockAge = 9;        // seconds since block was last pressed: a parry is timed from the press
    this.blockSpam = 0;       // quick presses in a row: each shrinks the parry window (HERO.parry)
    this.parryWin = 0;        // this press's parry window, in seconds
    this.shots = [];      // this hero's projectiles in flight
    this.aoes = [];       // area hits waiting to land (arrow rain)
    this.procs = this.S.procs || [];  // the extra attacks this hero's upgrades add (content/upgrades.py, `proc`)
    this.procAt = {};     // upgrade id -> when it last went off (for those with a cooldown)
    this.haste = 0;       // seconds of Tailwind left after a roll
    // Dashes: what a roll, dash or blink spends, and a blocked hit or a counter stance too. How many and
    // how fast they come back is the weapon's (W.dodge); a part-filled one can't be used yet.
    this.maxDash = this.W.dodge.charges + (this.S.dash_charges || 0);
    this.dashes = this.maxDash;
    this.noDash = 0;      // until when the HUD's dash pips shake (a dodge asked for with none left)
  }

  an() {
    switch (this.state) {
      case 'atk': return 'l' + this.combo;
      case 'heavy': return 'hv';
      case 'charge': return 'hc';
      case 'special': return 'sp';
      case 'cstrike': return 'cs';
      case 'skill': return 'k_' + this.skill.id;
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
    if (this.state === 'dash') return true;  // untouchable for the whole dash (0.28 s: about a roll's worth)
    if (this.state === 'blink') return true;
    if (this.state === 'skill' && this.skill.iframes) return this.t <= this.skill.iframes;
    if (this.state === 'special' && this.W.special.air) return this.t >= this.W.special.air[0] && this.t <= this.W.special.air[1];
    return false;
  }
  specialCost() { return this.W.special.focus * (this.S.special_cost || 1); }

  // spend n dashes (a blocked hit can cost part of one), if they're there
  useDash(n = 1) {
    if (this.dashes < n - 1e-6) { this.noDash = performance.now() + 300; return false; }
    this.dashes -= n;
    return true;
  }

  update(dt, ctx) {
    const d = ctx.input.get(this.dev);
    const H = this.HERO, W = this.W, G = W.guard;
    const quick = this.state === 'atk' ? this.S.light_speed || 1 : 1;   // light attacks play faster with some upgrades
    this.t += dt * quick; this.anT += dt * quick;
    this.haste = Math.max(0, this.haste - dt);
    this.flash = Math.max(0, this.flash - dt);
    this.dashes = Math.min(this.maxDash, this.dashes + dt * (this.S.dash_regen || 1) / (W.dodge.recharge * (this.S.dash_time || 1)));
    for (const k in this.skillCd) if (this.skillCd[k] > 0) this.skillCd[k] -= dt;
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
    const busy = ['atk', 'heavy', 'special', 'skill', 'roll', 'dash', 'hurt', 'cstrike'].includes(this.state) && !(this.state === 'atk' && this.t < 0.05);
    if (want !== null && !busy) {
      this.aim = want;
      const aimsAtBoss = boss.alive && Math.abs(wrap(want - Math.atan2(boss.y - this.y, boss.x - this.x))) < 0.01;
      if (aimsAtBoss) this.aimDist = Math.hypot(boss.x - this.x, boss.y - this.y);
      else if (d.id === 'kb' && d.mouse && ctx.world) { const w = ctx.world(d.mouse); this.aimDist = Math.hypot(w.x - this.x, w.y - (this.y - 14)); }
      else this.aimDist = null;
    }

    const move = d.move;
    const speedK = this.S.speed || 1;
    let speed = H.speed * speedK * (this.haste > 0 ? this.S.roll_haste || 1 : 1);
    const setState = s => { this.state = s; this.t = 0; this.anT = 0; };

    // The parry window opens at the press of block, wherever the hero is in an attack or a roll, so
    // holding block through a swing earns nothing. Pressing again soon after the last press shrinks it
    // (fishing for parries by tapping gets a narrower window each tap, then none); a pause restores it.
    this.blockAge += dt;
    if (G.kind === 'block' && d.pressed('block')) {
      const P = H.parry;
      this.blockSpam = this.blockAge < P.spam ? this.blockSpam + 1 : 0;
      this.parryWin = G.parry * P.shrink[Math.min(this.blockSpam, P.shrink.length - 1)];
      this.blockAge = 0;
    }

    // skills: a press while busy is held for a moment and fires when the hero is free; a press while
    // cooling down is refused aloud. On a controller A is also revive: beside a fallen ally it's only that.
    const reviving = d.id !== 'kb' && ctx.allies.some(a => a.down && !a.dead && Math.hypot(a.x - this.x, a.y - this.y) < 30);
    this.skills.forEach((S, i) => {
      if (!d.pressed('skill' + (i + 1)) || (reviving && d.held('interact'))) return;
      if (this.skillCd[S.id] > 0.4) { this.denied = { id: S.id, until: performance.now() + 350 }; ctx.onDenied(this); }
      else this.skillBuf = { S, t: 0.4 };
    });
    if (this.skillBuf && (this.skillBuf.t -= dt) < 0) this.skillBuf = null;

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
          // fast off the mark, easing down to a run by the end (the curve averages 1, so the distance holds),
          // and steered: it bends toward the stick as it goes
          const dist = this.state === 'roll' ? H.roll.dist : G.dist, u = Math.min(1, this.t / dur);
          if (move.x || move.y) {
            const turn = wrap(Math.atan2(move.y, move.x) - this.rollDir), max = (H.roll.turn || 0) * Math.PI / 180 * dt;
            this.rollDir += Math.max(-max, Math.min(max, turn));
          }
          const sp = dist / dur * (1.5 - u);
          this.x += Math.cos(this.rollDir) * sp * dt; this.y += Math.sin(this.rollDir) * sp * dt;
        }
        // what's pressed mid-roll happens the moment it ends
        if (d.pressed('light')) this.queued = 'light';
        if (d.pressed('heavy')) this.queued = 'heavy';
        if (d.pressed('dodge') && this.t > 0.1) this.queued = 'dodge';
        if (this.t >= dur) {
          const q = this.queued; this.queued = null;
          setState('idle');
          this.haste = 2;
          this.proc('roll_end', ctx);
          if (this.S.dodge) ctx.send({ t: 'dodge', h: this.id, x0: Math.round(this.rollFrom[0]), y0: Math.round(this.rollFrom[1]), x1: Math.round(this.x), y1: Math.round(this.y) });
          // the bow's roll-shot flies where you're aiming now (the cursor, the stick, a locked-on boss), not the way you rolled
          if (G.kind === 'rollshot') { if (want !== null) this.aim = want; this.fire({ v: 380, r: 4, life: 0.9 }, 'guard', ctx); }
          if (q === 'dodge') this.tryRoll(move, ctx);
          else if (q === 'light') this.startLight(0);
          else if (q === 'heavy') { setState('charge'); this.charge = 0; }
        }
        speed = 0;
        break;
      }
      case 'atk': case 'heavy': case 'special': case 'cstrike': case 'skill': {
        const atk = this.attackData();
        if (atk.hit && this.t < atk.hit[1] && atk.step) { // a step as you swing (back, for some)
          const s = atk.step / atk.hit[1];
          this.x += Math.cos(this.aim) * s * dt; this.y += Math.sin(this.aim) * s * dt;
        }
        this.checkHit(atk, ctx);
        // what upgrades add to a strike, loosed once as it lands: on the combo's last light, on a heavy
        if (atk.hit && this.t >= atk.hit[0] && this.swing && !this.swing.proc) {
          this.swing.proc = true;
          if (this.state === 'atk' && this.combo === W.light.length - 1) this.proc('finisher', ctx);
          if (this.state === 'heavy') { this.proc('heavy', ctx); if (this.chargeU >= 0.95) this.proc('heavy_full', ctx); }
        }
        if (this.state !== 'cstrike') {
          if (d.pressed('light')) this.queued = 'light';
          if (d.pressed('dodge')) this.queued = 'dodge';
          if (d.pressed('heavy')) this.queued = 'heavy';
          if (d.pressed('special') && this.focus >= this.specialCost()) this.queued = 'special';
          if (d.pressed('heal') && this.h.flasks > 0) this.queued = 'heal';
        }
        const cut = this.queued === 'special' || this.queued === 'heal';
        const skillReady = this.skillBuf && !(this.skillCd[this.skillBuf.S.id] > 0);
        // a skill, the special or a drink pressed mid-combo goes off at the next gap, ahead of a held light
        if (this.state === 'atk' && this.t >= atk.next && (skillReady || cut)) { this.comboWait = 0.45; setState('idle'); break; }
        // Holding light runs the combo on, as a queued press does, and starts it again after the last hit.
        const more = this.queued || (this.state === 'atk' && d.held('light') ? 'light' : null);
        if (this.state === 'atk' && more && this.t >= atk.next) {
          this.queued = null;
          if (more === 'light' && this.combo < W.light.length - 1) { this.startLight(this.combo + 1); break; }
          if (more === 'dodge') { this.tryRoll(move, ctx); break; }
          if (more === 'heavy') { setState('charge'); this.charge = 0; break; }
          this.queued = more === 'light' && !d.held('light') ? more : null;  // the last hit: a press waits for it to finish
        }
        // a roll cuts short the recovery of a heavy or a special too (once it has struck, and landed if it leapt)
        if (this.queued === 'dodge' && (this.state === 'heavy' || this.state === 'special')
            && this.t >= Math.max(atk.hit ? atk.hit[1] : 0, atk.air ? atk.air[1] : 0) + 0.06) {
          this.queued = null; this.tryRoll(move, ctx); break;
        }
        if (this.t >= atk.dur) {
          const q = skillReady ? null : this.queued || (this.state === 'atk' && d.held('light') ? 'light' : null);
          if (!cut) this.queued = null;
          this.comboWait = 0.45;
          setState('idle');
          if (q === 'dodge') this.tryRoll(move, ctx);
          else if (q === 'light') this.startLight(this.combo < W.light.length - 1 ? this.combo + 1 : 0);
        }
        speed = 0;
        break;
      }
      case 'charge':
        if (this.charge < W.heavy.charge && this.charge + dt >= W.heavy.charge) { this.flash = 0.1; ctx.onCharged(this); }  // fully charged: a flash and a chime
        this.charge = Math.min(W.heavy.charge, this.charge + dt);
        speed = H.speed * speedK * 0.25;
        if (!d.held('heavy')) { this.chargeU = this.charge / W.heavy.charge; this.startAttack('heavy'); }
        else if (d.pressed('dodge')) this.tryRoll(move, ctx);
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
        if (d.pressed('heavy')) { setState('charge'); this.charge = 0; break; }
        const q = this.queued; this.queued = null;   // the special or a drink asked for mid-attack
        if ((d.pressed('special') || q === 'special') && this.focus >= this.specialCost()) { this.focus -= this.specialCost(); this.startAttack('special', ctx); break; }
        if (this.skillBuf && !(this.skillCd[this.skillBuf.S.id] > 0)) { const S = this.skillBuf.S; this.skillBuf = null; this.useSkill(S, move, ctx); break; }
        if ((d.pressed('heal') || q === 'heal') && this.h.flasks > 0) { setState('drink'); ctx.send({ t: 'drink', h: this.id }); this.proc('flask', ctx); break; }
        // light: a press, or the button held (after a roll, a skill or a drink the combo picks straight back up)
        if (d.pressed('light') || (d.held('light') && !d.held('heavy'))) { this.startLight(this.comboWait > 0 && this.combo < W.light.length - 1 ? this.combo + 1 : 0); break; }
        if (G.kind === 'block' && d.held('block')) { setState('block'); break; }
        if (G.kind === 'counter' && d.pressed('block') && this.useDash(G.cost)) { setState('cnt'); break; }
      }
    }

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
      case 'skill': return this.skill;
      default: return { ...W.guard, dur: 0.45, hit: [0.08, 0.16], step: 14 };  // the counter-strike
    }
  }

  tryRoll(move, ctx) {
    const G = this.W.guard, dir = move.x || move.y ? Math.atan2(move.y, move.x) : this.aim;
    if (G.kind === 'dash') {
      if (!this.useDash()) return;
      this.state = 'dash';
    } else if (G.kind === 'blink') {
      if (!this.useDash()) return;
      this.rollFrom = [this.x, this.y];
      this.x += Math.cos(dir) * G.dist; this.y += Math.sin(dir) * G.dist;
      ctx && ctx.collide(this);
      ctx && ctx.onBlink(this);
      this.state = 'blink';
    } else {
      if (!this.useDash()) return;
      this.state = 'roll';
    }
    if (G.kind !== 'blink') this.rollFrom = [this.x, this.y];
    this.rollDir = dir;
    if (move.x || move.y) this.aim = dir;
    this.t = 0; this.anT = 0; this.queued = null;
  }

  // Start a skill: its cooldown begins, the server is told (it applies cries, wards and heals, and shows
  // everyone), and a blink carries you off at once, the way you're walking or else the way you aim.
  useSkill(S, move, ctx) {
    this.skill = S; this.skillCd[S.id] = S.cd * (this.S.skill_cd || 1);
    if (S.dashes) this.dashes = this.maxDash;
    this.focus = Math.min(this.HERO.focus, this.focus + (S.focus || 0) + (this.S.skill_focus || 0));
    this.state = 'skill'; this.t = 0; this.anT = 0; this.queued = null;
    this.swing = { seq: ++swingSeq, struck: new Set(), fired: false };
    if (S.blink) {
      const dir = move.x || move.y ? Math.atan2(move.y, move.x) : this.aim;
      this.x += Math.cos(dir) * S.blink; this.y += Math.sin(dir) * S.blink;
      ctx.collide(this); ctx.onBlink(this);
    }
    ctx.send({ t: 'skill', h: this.id, sk: S.id, x: Math.round(this.x), y: Math.round(this.y), a: Math.round(this.aim * 100) / 100 });
  }

  startLight(i) {
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

  // Loose every extra attack this hero's upgrades hang on `when` (finisher, heavy, heavy_full, roll_end,
  // guard, perfect, flask): a projectile along the aim, or an area hit. An area lands `at` px ahead (for
  // a bow or catalyst, on what's aimed at), or halfway back along the roll just made (`mid`). The server
  // prices each hit from the upgrade (atk 'proc').
  proc(when, ctx) {
    for (const P of this.procs) {
      if (P.when !== when) continue;
      if (P.cd && ctx.now - (this.procAt[P.id] ?? -99) < P.cd) continue;
      this.procAt[P.id] = ctx.now;
      const kind = 'proc:' + P.id;
      if (P.proj) this.fire(P.proj, kind, ctx);
      if (P.aoe) {
        const A = P.aoe;
        // A heavy that is a shot (the bow's arrow, the catalyst's orb) carries the area with it: it goes
        // off where the shot first strikes or comes to rest, not at the hero's feet or the cursor.
        const shot = when.startsWith('heavy') && this.W.heavy.proj ? this.shots.findLast(s => s.kind === 'heavy' && !s.landed) : null;
        if (shot) { (shot.procs ||= []).push(P); continue; }
        let x = this.x + Math.cos(this.aim) * A.at, y = this.y + Math.sin(this.aim) * A.at;
        if (A.mid && this.rollFrom) { x = (this.x + this.rollFrom[0]) / 2; y = (this.y + this.rollFrom[1]) / 2; }
        this.procArea(P, x, y, ctx);
      }
    }
  }

  // an upgrade's area hit, at (x, y)
  procArea(P, x, y, ctx) {
    const A = P.aoe;
    this.aoes.push({ x, y, r: A.r, wait: A.delay, ticks: A.ticks, every: A.every, kind: 'proc:' + P.id, col: A.col, pillar: !!A.pillar, boom: !!A.boom, pool: A.ticks > 1 });
    ctx.send({ t: 'shot', h: this.id, k: 'aoe', x: Math.round(x), y: Math.round(y), r: A.r, life: A.delay + (A.ticks - 1) * A.every + 0.05, col: A.col, p: A.pillar ? 1 : A.ticks > 1 ? 2 : 0 });
  }

  // which attack a hit is reported as; a skill's is 'skill:<id>'
  slot() { return this.state === 'skill' ? 'skill:' + this.skill.id : { atk: 'light', heavy: 'heavy', special: 'special', cstrike: 'guard' }[this.state] || 'light'; }

  // one swing strikes each thing it touches once: a body (or one of its weak points), adds.
  // Ranged attacks fire their projectiles or call down their area hit instead.
  checkHit(atk, ctx) {
    if (!atk.hit || this.t < atk.hit[0]) return;
    const kind = this.slot();
    // A shot or a called-down area is loosed once, on the first frame at or after its moment: its
    // window is only 10 ms wide, and a frame (17 ms at 60 a second) can step clean over it.
    if (atk.proj) { if (!this.swing.fired) { this.swing.fired = true; this.fire(atk.proj, kind, ctx); } return; }
    if (atk.aoe) {
      if (!this.swing.fired) {
        this.swing.fired = true;
        const A = atk.aoe;
        // `range`: it lands on what you aim at (the cursor, the boss you're locked on to), up to that far
        const at = A.range && this.aimDist != null ? Math.min(A.range, this.aimDist) : A.at;
        this.aoes.push({ x: this.x + Math.cos(this.aim) * at, y: this.y + Math.sin(this.aim) * at, r: A.r, wait: A.delay, ticks: A.ticks, every: A.every, kind,
          col: atk.col, pillar: !!A.range });
        ctx.send({ t: 'shot', h: this.id, k: 'aoe', x: Math.round(this.aoes.at(-1).x), y: Math.round(this.aoes.at(-1).y), r: A.r,
          life: A.range ? A.delay : A.delay + A.ticks * A.every, col: atk.col, p: A.range ? 1 : 0 });
      }
      return;
    }
    if (this.t > atk.hit[1]) return;
    const s = placeAttack(reach(atk.shape, this.state === 'skill' ? 1 : this.S.reach || 1), this.x, this.y, this.aim);
    this.strike(s, kind, this.swing, ctx);
  }

  // send a hit for everything shape s touches that this swing hasn't struck yet
  strike(s, kind, swing, ctx) {
    const base = kind.startsWith('skill:') ? { h: this.id, atk: 'skill', sk: kind.slice(6), sw: swing.seq }
      : kind.startsWith('proc:') ? { h: this.id, atk: 'proc', p: kind.slice(5), sw: swing.seq }
      : { h: this.id, atk: kind, i: this.combo, c: this.chargeU || 0, sw: swing.seq };
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
    // upgrades: light arrows that pierce, an extra bolt on every light cast
    const light = kind === 'light', more = light ? this.S.light_shots || 0 : 0;
    if (light && this.S.light_pierce) P = { ...P, pierce: true };
    const n = (P.n || 1) + more, spread = P.spread || (more ? 12 : 0);
    for (let i = 0; i < n; i++) {
      const a = this.aim + (spread * (i - (n - 1) / 2)) * Math.PI / 180;
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
      if ((hit || s.life <= 0) && !s.landed) {  // where it first strikes or comes to rest: what upgrades hung on it goes off here
        s.landed = true;
        for (const P of s.procs || []) this.procArea(P, s.x, s.y, ctx);
      }
    }
    this.shots = this.shots.filter(s => s.life > 0);
    for (const A of this.aoes) {
      A.wait -= dt;
      if (A.wait <= 0 && A.ticks > 0) {
        A.ticks--; A.wait = A.every;
        if (A.pillar) ctx.onPillar(A.x, A.y, A.r, A.col);
        else if (A.boom) ctx.onBoom(A.x, A.y, A.r, A.col);
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
        if (this.blockAge <= this.parryWin && !h.noparry) return 'parry';
        if (this.useDash(G.cost * (this.S.block_cost || 1))) return 'block';  // a blocked hit uses a dash; with none left the guard breaks
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

  draw() { this.view.reachK = this.S.reach || 1; this.view.dash = [this.dashes, this.maxDash]; this.view.draw(this.x, this.y, this.an(), this.anT, this.aim, this.flash > 0); }
  report() { return { t: 'st', h: this.id, x: Math.round(this.x * 10) / 10, y: Math.round(this.y * 10) / 10, f: Math.round(this.aim * 100) / 100, an: this.an(), at: Math.round(this.anT * 100) / 100 }; }
}

export class RemoteHero {
  constructor(scene, h, data) {
    this.h = h; this.id = h.id;
    this.W = data.weapons[h.weapon]; this.HERO = data.hero;
    SKILLS = data.skills || {};
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
