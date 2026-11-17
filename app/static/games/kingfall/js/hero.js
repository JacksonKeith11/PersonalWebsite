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
import { Rig, sample, runCycle, rigDefaults, atlas } from './rig.js?v=45';
import { placeAttack, touches, wrap } from './moves.js?v=45';
import { crescent, lance, burst } from './fx.js?v=45';
import { sfx } from './audio.js?v=45';

let SKILLS = {};   // the welcome's skills table, for poses and swings drawn from an animation's name

// A hero's own weapon: the weapon's table with what their blessings change in it (app/kingfall/build.py,
// `Build.weapon`; the `mod` effects in content/upgrades.py). Each [path, value] is set in a copy.
const modded = new Map();
export function weaponOf(data, h) {
  const base = data.weapons[h.weapon], mods = (h.stats && h.stats.mods) || [];
  if (!mods.length) return base;
  const key = h.weapon + JSON.stringify(mods);
  if (!modded.has(key)) {
    const W = JSON.parse(JSON.stringify(base));
    for (const [path, value] of mods) {
      const keys = path.split('.');
      let at = W;
      for (const k of keys.slice(0, -1)) { if (at[k] == null) at[k] = {}; at = at[k]; }
      at[keys.at(-1)] = JSON.parse(JSON.stringify(value));
    }
    modded.set(key, W);
  }
  return modded.get(key);
}

// the attack an animation name plays, if it is one (a light, a weapon move, the heavy, the special)
function attackOf(W, an) {
  if (/^l\d+$/.test(an)) return W.light[Math.min(+an.slice(1), W.light.length - 1)];
  if (an[0] === 'm' && an[1] === '_') return (W.moves || {})[an.slice(2)];
  return an === 'hv' ? W.heavy : an === 'sp' ? W.special : null;
}
// when an attack's last blow has landed (its further hit windows too)
const lastHit = atk => Math.max(atk.hit ? atk.hit[1] : 0, ...(atk.more || []).map(w => w[1]));
const hex = c => Phaser.Display.Color.HexStringToColor(c).color;

// A skill's casting pose (its `pose`), reaching its height as the skill's hit begins (or a third of the
// way in) and easing back at the end: 'cast' thrusts the weapon hand out, 'throw' hurls overhand, 'fan'
// sweeps the off hand across, 'raise' lifts both arms, 'slam' brings both hands down from overhead,
// 'spin' holds the weapon out level (the figure turns about), 'toss' lobs underarm, 'kneel' goes to one knee.
const POSES = {
  cast: [{ arm_f: 30, weapon: 60, arm_b: -20, torso: -14, lean: -3 }, { arm_f: -95, weapon: 150, arm_b: 30, torso: 16, lean: 6, head: 4 }],
  throw: [{ arm_f: -200, weapon: 60, arm_b: -70, torso: -18, lean: -4, head: -6 }, { arm_f: -70, weapon: 120, arm_b: 40, torso: 22, lean: 8, head: 6 }],
  fan: [{ arm_b: -150, shield: 60, arm_f: 20, weapon: 70, torso: -20, lean: -2 }, { arm_b: -40, shield: 120, arm_f: 30, weapon: 70, torso: 24, lean: 6, front: 1 }],
  raise: [{ arm_f: -60, arm_b: -60, torso: 6, dy: 2 }, { arm_f: -170, weapon: 170, arm_b: -170, shield: 170, torso: -8, head: -8 }],
  slam: [{ arm_f: -200, weapon: 120, arm_b: -200, shield: 120, torso: -16, head: -8, dy: -2 }, { arm_f: -50, weapon: -20, arm_b: -50, shield: -20, torso: 26, lean: 7, head: 10, dy: 3 }],
  spin: [{ arm_f: -95, weapon: 5, arm_b: 60, torso: 10, lean: 2 }, { arm_f: -100, weapon: 5, arm_b: 70, torso: 12, lean: 3, dy: 1 }],
  toss: [{ arm_f: 40, weapon: 70, arm_b: -30, torso: -10, lean: -3, dy: 2 }, { arm_f: -130, weapon: 150, arm_b: 30, torso: 10, lean: 4, head: -6 }],
  kneel: [{ arm_f: -40, arm_b: -40, torso: 14, dy: 3 }, { arm_f: -110, weapon: 170, arm_b: -110, shield: 170, torso: 22, head: 14, dy: 7, leg_f: -50, leg_b: 30 }],
};
function skillPose(S, at, D) {
  const t0 = S.hit ? S.hit[0] : S.dur * 0.3, t1 = Math.max(t0 + 0.12, S.hit ? S.hit[1] : S.dur * 0.6);
  const [a, b] = POSES[S.pose] || POSES.cast;
  return sample([[0, a], [t0, b], [t1, b], [S.dur, {}]], Math.min(at, S.dur), D);
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
  if (an[0] === 'k' && an[1] === '_') { const S = SKILLS[an.slice(2)]; return { p: S ? skillPose(S, at, D) : {}, spin, z: S ? leapZ(S, at) : 0 }; }
  if (an[0] === 'm' && an[1] === '_') { const M = (W.moves || {})[an.slice(2)]; return { p: M && M.anim ? sample(M.anim, at, D) : {}, spin, z }; }
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
    case 'rl': p = { arm_f: -70 + Math.sin(at * 14) * 8, weapon: 150, arm_b: -80, torso: 10, head: 10 }; break;   // reloading: head down over the breech
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
    this.scene = scene; this.lastAn = ''; this.lastZ = 0;
    this.ghosts = []; this.ghostT = 0; this.stepN = -1;
    this.mine = false;    // this browser's hero: its footsteps are louder
    this.noOff = false; this.noWeapon = false;   // what's out of the hands just now (a planted standard, thrown discs, the sickle)
    this.pips = null;     // [n, most, colour]: a second row under the dashes (a streak, rounds or discs left); this browser's heroes only
    this.reload = null;   // [share done, window from, window to, fumbled]: the ring over a reloading hero
  }
  // An afterimage: the figure as it stands, in the player's colour, left behind to fade. A roll or a dash
  // leaves a string of them; a blink leaves one where the hero stood.
  ghost(life = 0.2) {
    const c = this.rig.c, sc = this.scene;
    const g = sc.add.container(c.x, c.y).setDepth(c.depth - 0.05);
    g.scaleX = c.scaleX; g.angle = c.angle;
    for (const im of c.list) {
      if (!im.visible) continue;
      g.add(sc.add.image(im.x, im.y, 'atlas', im.frame.name).setOrigin(im.originX, im.originY).setAngle(im.angle).setTintFill(this.colour));
    }
    g.setBlendMode(Phaser.BlendModes.ADD);
    this.ghosts.push({ g, life, max: life });
  }
  drawGhosts(dt) {
    this.ghosts = this.ghosts.filter(o => {
      o.life -= dt;
      if (o.life <= 0) { o.g.destroy(); return false; }
      o.g.alpha = 0.55 * o.life / o.max;
      return true;
    });
  }
  draw(x, y, an, at, aim, flash) {
    this.drawSwing(x, y, an, at, aim);
    this.drawStatus(x, y);
    let left = Math.cos(aim) < -0.05;
    const A = an[0] === 'k' && SKILLS[an.slice(2)] && SKILLS[an.slice(2)].aoe;
    if (A && !A.at && at > 0.06) left = Math.floor((at - 0.06) / (A.every / 2)) % 2 === 1 ? !left : left;  // a whirl: the hero turns about with each strike
    const M = attackOf(this.W, an);
    if (M && M.whirl) left = Math.floor(at / (M.dur / 2)) % 2 === 1 ? !left : left;   // the whirlwind: the figure turns about as the blade goes round
    const { p, spin, z } = heroPose(this.W, this.HERO, an, at);
    if (this.noOff) p.shield_hide = 1;      // the standard is planted, or that disc is in the air
    if (this.noWeapon) p.weapon_hide = 1;   // the sickle or the last disc is away from the hand
    const dt = Math.min(0.05, this.scene.game.loop.delta / 1000), K0 = an[0] === 'k' && SKILLS[an.slice(2)];
    const dodge = an === 'roll' || an === 'dash', blinks = an === 'blink' || !!(K0 && K0.blink);
    if (blinks && an !== this.lastAn && this.lastAn) this.ghost(0.34);   // before the figure moves: it is still where it stood
    this.drawGhosts(dt);
    // footfalls: two to each turn of the legs (rig.js, runCycle)
    const pace = an === 'run' ? 13 : an === 'walk' ? 9 : an === 'blkw' ? 7 : 0;
    if (pace) {
      const n = Math.floor(at * pace / Math.PI);
      if (n !== this.stepN && this.stepN >= 0 && this.scene.floor) sfx.step(this.scene.floor, this.scene.pan(x), this.mine ? (pace === 13 ? 1 : 0.6) : 0.4);
      this.stepN = n;
    } else this.stepN = -1;
    // dust where a roll starts and where a leap lands
    const A2 = this.scene.atmos;
    if (A2) {
      if (an !== this.lastAn && (an === 'roll' || an === 'dash')) A2.dust(x, y, 5);
      if (this.lastZ > 8 && z < 1) A2.dust(x, y, 10, true);
    }
    this.lastAn = an; this.lastZ = z;
    this.rig.pose(p, left);
    placeRig(this.rig, x, y - z, spin, left);
    this.shadow.setPosition(x, y).setScale(1 - z / 80); this.ring.setPosition(x, y);
    this.rig.c.setDepth(y); this.shadow.setDepth(1); this.ring.setDepth(1.1);
    this.rig.setTint(flash ? 0xffffff : null);
    const K = an[0] === 'k' && SKILLS[an.slice(2)];
    this.rig.c.alpha = an === 'roll' || an === 'dash' ? 0.85 : an === 'blink' || (K && K.blink) ? 0.4 : 1;
    if (dodge) { this.ghostT -= dt; if (this.ghostT <= 0) { this.ghostT = 0.045; this.ghost(); } } else this.ghostT = 0;
    this.drawBars(x, y, z, an);
  }
  destroy() { this.rig.destroy(); this.shadow.destroy(); this.ring.destroy(); this.swingG.destroy(); this.barG.destroy(); this.ghosts.forEach(o => o.g.destroy()); }

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
    if (this.reload) {   // reloading: a ring closing over the head, the moment to press again marked on it
      const [u, w0, w1, bad] = this.reload, cy = hy - 12, A = v => -Math.PI / 2 + v * Math.PI * 2;
      g.lineStyle(4, 0x0c0a10, 0.8).beginPath().arc(Math.round(x), cy, 8, 0, Math.PI * 2).strokePath();
      g.lineStyle(3, bad ? 0x7a7488 : 0xffd23f, 1).beginPath().arc(Math.round(x), cy, 8, A(w0), A(w1)).strokePath();
      g.lineStyle(2, bad ? 0xc84040 : 0xffffff, 1).beginPath().arc(Math.round(x), cy, 8, A(0), A(Math.min(1, u))).strokePath();
    }
    if (!this.dash) return;
    if (this.pips) {   // a streak, or what's left to fire or throw
      const [pn, pmax, col] = this.pips, w = pmax > 8 ? 2 : pmax > 3 ? 4 : 7, gp = 1, px0 = Math.round(x) - (pmax * w + (pmax - 1) * gp) / 2, py = Math.round(y) + 14;
      for (let i = 0; i < pmax; i++) {
        g.fillStyle(0x0c0a10, 0.8); g.fillRect(px0 + i * (w + gp) - 1, py - 1, w + 2, 4);
        if (i < pn) { g.fillStyle(col, 1); g.fillRect(px0 + i * (w + gp), py, w, 2); }
      }
    }
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
    if (st.shield) {   // a ward (Stone Ward's is -1: it soaks anything, and is drawn harder)
      if (st.shield < 0) { g.lineStyle(2.5, 0xe8ecf2, 0.9); g.strokeEllipse(x, y - 16, 30, 42); }
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
    else if (an[0] === 'm' && an[1] === '_') { atk = (W.moves || {})[an.slice(2)]; rev = !!(atk && atk.whirl) && Math.cos(aim) < -0.05; }
    else if (an === 'hv') atk = W.heavy;
    else if (an === 'sp') atk = W.special;
    else if (an === 'cs') atk = { shape: W.guard.shape, hit: [0.08, 0.16] };
    if (!atk || !atk.shape || atk.proj || atk.aoe) return;
    let [h0, h1] = atk.hit;
    for (const w of atk.more || []) if (at >= w[0] - 0.03) [h0, h1] = w;   // a second jab: its own trail
    const pre = 0.03, after = atk.loop ? 0.05 : 0.2;
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
    this.W = weaponOf(data, h); this.HERO = data.hero;
    this.S = h.stats || {};   // the hero's build: see app/kingfall/build.py, Build.client
    SKILLS = data.skills || {};
    this.skills = (h.skills || []).map(id => SKILLS[id]).filter(Boolean);  // slot 0 is skill1, slot 1 skill2
    this.skillCd = {};        // skill id -> seconds until it can be used again
    this.skill = null;        // the one being cast
    this.skillBuf = null;     // a skill pressed while busy: it fires as soon as the hero is free (within 0.4 s)
    this.denied = null;       // {id, until}: a skill pressed while cooling down (the HUD chip shakes)
    this.aimDist = null;      // how far away the thing aimed at is (the cursor, a locked-on boss), if known
    this.view = new HeroView(scene, h, this.W, this.HERO);
    this.view.mine = true;
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
    this.mv = null;       // the weapon move being played (W.moves: a dash-strike, the riposte, the whirlwind...)
    this.sinceDodge = 9;  // seconds since a dodge ended: light pressed just after is still the dash-strike
    this.riposte = 0;     // seconds left in which light answers a block or parry with the riposte
    this.over = 0;        // seconds a charged heavy has been held at full (the bow's Power Shot is timed from it)
    this.power = false;   // this heavy was a Power Shot
    this.passing = false; // going through bosses (the daggers' cross-cuts)
    this.now = 0;         // server time, as of this frame
    this.wantA = null;    // where the player is aiming right now, even mid-swing (skills go there as they fire)
    this.wantDist = null; // ...and how far away the thing aimed at is
    this.freeUntil = 0;   // Second Breath: dashes cost nothing until then
    this.perfectFocus = 0;   // ...and each hit dodged through gives this much Focus
    this.wardUntil = 0;   // Stone Ward: the next hit before then is soaked whole and answered
    this.recast = null;   // {id, until, x, y}: a skill that acts again if pressed again (the step back, the knives' return)
    this.stuck = [];      // thrown knives lying where they landed, to be called back
    this.stuckId = 0;
    this.stillT = 0;      // seconds stood still (Patience charges the next heavy)
    this.oc = false;      // this heavy was held past full and drank health for it (Sanguine Cleave)
    this.echo = 0;        // seconds left in which the special may be used again for nothing (Echo)
    this.leapStep = 0;    // how far this cast's leap carries (Hammerfall)
    this.blinkDur = 0.16; // how long this blink leaves the hero untouchable
    this.skillBlink = false;  // this blink is a skill's, not the weapon's dodge
    this.passSwing = {};  // upgrade id -> the swing its dodge-through attack is striking with
    this.lastAoe = null;  // where this attack's own area landed (what blessings hang on a special goes off there)
    this.readyAt = {};    // skill id -> when it last came off cooldown (the HUD chip flashes)
    // the second six weapons (content/weapons.py)
    this.streak = 0; this.streakT = 0;   // gauntlets: hits landed in a row, and seconds until it lapses
    this.ammo = this.W.ammo ? this.W.ammo.max : 0;   // chakrams in hand, rounds in the cannon
    this.late = [];       // seconds until each disc that wasn't caught comes back to hand
    this.primed = false;  // the next throw or shot is a strong one (a disc caught, a reload timed)
    this.fumbled = false; // this reload was pressed at the wrong moment
    this.planted = null;  // {x, y}: where the war banner's standard stands
    this.nearStand = false;
    this.pullTo = null;   // {x, y}: where the sickle's chain is dragging the hero
  }

  an() {
    switch (this.state) {
      case 'atk': return 'l' + this.combo;
      case 'mv': return 'm_' + this.mv;
      case 'heavy': return 'hv';
      case 'charge': return 'hc';
      case 'special': return 'sp';
      case 'cstrike': return 'cs';
      case 'pull': return 'dash';
      case 'reload': return 'rl';
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
    if (this.state === 'dash' || this.state === 'pull') return true;  // untouchable for the whole dash (0.28 s: about a roll's worth), and while the chain pulls
    if (this.state === 'blink') return true;
    if (this.state === 'skill' && this.skill.air) return this.t >= this.skill.air[0] && this.t <= this.skill.air[1];
    if (this.state === 'special' && this.W.special.air) return this.t >= this.W.special.air[0] && this.t <= this.W.special.air[1];
    return false;
  }
  specialCost() { return this.W.special.focus * (this.S.special_cost || 1); }
  // the special can be used: there's the Focus for it, an Echo is waiting, or (Bloodletting) the health to pay instead
  canSpecial() { return this.echo > 0 || this.focus >= this.specialCost() || (!!this.S.bloodspecial && (this.view.hp ? this.view.hp[0] : 0) > 20); }
  startSpecial(ctx) {
    let fl = null;
    if (this.echo > 0) { this.echo = 0; fl = { eh: 1 }; }
    else {
      if (this.focus >= this.specialCost()) this.focus -= this.specialCost(); else ctx.send({ t: 'pay', h: this.id });
      if (this.S.echo) this.echo = this.W.special.dur + 2;
    }
    this.startAttack('special', ctx);
    if (fl) this.swing.fl = { ...this.swing.fl, ...fl };
  }
  // begin charging a heavy (Patience: after a second stood still it is charged at once)
  startCharge(ctx) {
    const W = this.W;
    if (this.planted) { this.recallStandard(ctx); return; }                                      // the war banner: heavy again calls the standard home
    if (W.heavy.proj && W.heavy.proj.hook && this.stuck.length) { this.yank(ctx); return; }       // the sickle lies thrown: yank it back
    if (W.heavy.proj && W.heavy.proj.hook && this.shots.some(q => q.hook || q.kind === 'move:yank')) return;   // ...or is still in the air
    if (W.heavy.ammo && this.ammo < W.heavy.ammo) {   // nothing to throw or fire
      if (W.ammo.reload) this.startReload(); else this.noDash = performance.now() + 300;
      return;
    }
    this.state = 'charge'; this.t = 0; this.anT = 0; this.over = 0; this.oc = false;
    this.charge = this.S.patience && this.stillT >= 1 ? this.W.heavy.charge - 0.001 : 0;
  }
  // the cannon: break it open (press again inside the window to finish at once, primed)
  startReload() {
    if (this.state === 'reload' || this.ammo >= this.W.ammo.max) return;
    this.state = 'reload'; this.t = 0; this.anT = 0; this.fumbled = false; this.queued = null;
  }
  // the war banner: the standard flies back to the hand through whatever is between
  recallStandard(ctx) {
    const P = this.planted;
    this.planted = null;
    ctx.send({ t: 'plant', h: this.id, up: 1 });
    this.comeHome(P.x, P.y, 'move:recall', 10, this.h.colourHex, ctx);
    ctx.onSwing && ctx.onSwing(this);
  }
  // the sickle, lying where it fell: yanked home on its chain
  yank(ctx) {
    for (const k of this.stuck) this.comeHome(k.x, k.y, 'move:yank', 8, k.col, ctx);
    ctx.send({ t: 'shot', h: this.id, k: 'end', id: this.stuckId });
    this.stuck = [];
    ctx.onSwing && ctx.onSwing(this);
  }
  // something of the hero's flies back to the hand from (x, y), striking afresh on the way
  comeHome(x, y, kind, r, col, ctx) {
    const a = Math.atan2(this.y - 10 - y, this.x - x), v = 540, far = Math.hypot(this.x - x, this.y - 10 - y);
    this.shots.push({ x, y, a, v, r, life: far / v + 0.4, pierce: true, col, kind, combo: 0, c: 0, home: true, swing: { seq: ++swingSeq, struck: new Set(), shot: true } });
    ctx.send({ t: 'shot', h: this.id, k: 'proj', x: Math.round(x), y: Math.round(y), a: Math.round(a * 1000) / 1000, v, r, life: Math.round(far / v * 100) / 100, col });
  }
  // what a blessing just gave (the server says): Focus, seconds off every skill's cooldown, dashes
  gain(m) {
    if (m.focus) this.focus = Math.min(this.HERO.focus, this.focus + m.focus);
    if (m.cd) for (const k in this.skillCd) this.skillCd[k] -= m.cd;
    if (m.dash) this.dashes = Math.min(this.maxDash, this.dashes + m.dash);
  }

  // spend n dashes (a blocked hit can cost part of one), if they're there
  useDash(n = 1) {
    if (this.now < this.freeUntil) return true;   // Second Breath
    if (this.dashes < n - 1e-6) { this.noDash = performance.now() + 300; return false; }
    this.dashes -= n;
    return true;
  }

  update(dt, ctx) {
    const d = ctx.input.get(this.dev);
    const H = this.HERO, W = this.W, G = W.guard;
    const M0 = this.state === 'mv' ? W.moves[this.mv] : null;
    const W0 = this.W, P0 = this.planted;
    this.nearStand = !!P0 && Math.hypot(P0.x - this.x, P0.y - this.y) <= W0.stand.r;
    // light attacks play faster with some upgrades, with a streak (gauntlets), beside the standard (war banner)
    const quick = this.state === 'atk' || (M0 && M0.slot === 'light')
      ? (this.S.light_speed || 1) * (this.haste > 0 ? this.S.haste_light || 1 : 1) * (W0.streak ? 1 + W0.streak.speed * this.streak : 1) * (this.nearStand ? W0.stand.speed : 1) : 1;
    this.t += dt * quick; this.anT += dt * quick;
    this.now = ctx.now; this.echo = Math.max(0, this.echo - dt);
    if (this.streak > 0 && (this.streakT -= dt) <= 0) this.streak = 0;   // a streak lapses without a hit
    if (this.late.length) {   // discs that weren't caught come back to hand in their own time
      this.late = this.late.map(v => v - dt);
      const back = this.late.filter(v => v <= 0).length;
      if (back) { this.ammo = Math.min(W0.ammo.max, this.ammo + back); this.late = this.late.filter(v => v > 0); }
    }
    if (this.recast && ctx.now >= this.recast.until) this.recast = null;
    this.sinceDodge += dt; this.riposte = Math.max(0, this.riposte - dt); this.passing = false;
    if (M0 && M0.drain) this.dashes = Math.max(0, this.dashes - (M0.drain + (this.S.dash_regen || 1) / (W.dodge.recharge * (this.S.dash_time || 1))) * dt);   // the whirlwind spends dashes, and none come back while it turns
    this.haste = Math.max(0, this.haste - dt);
    this.flash = Math.max(0, this.flash - dt);
    this.dashes = Math.min(this.maxDash, this.dashes + dt * (this.S.dash_regen || 1) / (W.dodge.recharge * (this.S.dash_time || 1)));
    for (const k in this.skillCd) {
      if (!(this.skillCd[k] > 0)) continue;
      this.skillCd[k] -= dt;
      if (this.skillCd[k] <= 0) { this.readyAt[k] = performance.now(); ctx.onReady && ctx.onReady(this, k); }   // ready again: a chime, and its chip flashes
    }
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
    const busy = ['atk', 'mv', 'heavy', 'special', 'skill', 'roll', 'dash', 'hurt', 'cstrike'].includes(this.state) && !((this.state === 'atk' || this.state === 'mv') && (this.t < 0.05 || this.fresh)) && !(M0 && M0.loop);   // each swing re-aims as it starts (`fresh`: even on a slow frame)
    this.fresh = false;
    // where they're aiming and how far off the thing aimed at is: kept every frame, so a skill cast
    // mid-swing still goes where the player points as it fires
    this.wantA = want; this.wantDist = null;
    if (want !== null) {
      if (boss.alive && Math.abs(wrap(want - Math.atan2(boss.y - this.y, boss.x - this.x))) < 0.01) this.wantDist = Math.hypot(boss.x - this.x, boss.y - this.y);
      else if (d.id === 'kb' && d.mouse && ctx.world) { const w = ctx.world(d.mouse); this.wantDist = Math.hypot(w.x - this.x, w.y - (this.y - 14)); }
    }
    if (want !== null && !busy) { this.aim = want; this.aimDist = this.wantDist; }

    const move = d.move;
    // Patience: a second stood still and the next heavy is charged at once (a flash says it's ready)
    const still0 = this.stillT;
    this.stillT = this.state === 'idle' && !(move.x || move.y) ? this.stillT + dt : 0;
    if (this.S.patience && still0 < 1 && this.stillT >= 1) { this.flash = 0.1; ctx.onCharged(this); }
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
      if (this.recast && this.recast.id === S.id) {   // pressed again: it acts a second time (knives still in the air aren't called yet)
        if (!S.stick || this.stuck.length) this.doRecast(S, ctx);
        return;
      }
      if (this.skillCd[S.id] > 0.4) { this.denied = { id: S.id, until: performance.now() + 350 }; ctx.onDenied(this); }
      else this.skillBuf = { S, t: 0.6 };
    });
    if (this.skillBuf && (this.skillBuf.t -= dt) < 0) this.skillBuf = null;
    // a skill cast on the move (a ward, a cry, the step) goes off at once, whatever the hero is doing, unless they're reeling
    if (this.skillBuf && this.skillBuf.S.instant && !(this.skillCd[this.skillBuf.S.id] > 0) && this.state !== 'hurt' && !(this.skillBuf.S.blink && this.isHeld(ctx.now))) {
      const S = this.skillBuf.S; this.skillBuf = null;
      this.useSkill(S, move, ctx);
    }

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
        const dur = this.state === 'roll' ? H.roll.dur : this.state === 'dash' ? G.dur : this.blinkDur;
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
          this.passStrike(ctx, null);   // what blessings make of a dodge: it strikes what it passes through
        }
        // what's pressed mid-roll happens the moment it ends
        if (d.pressed('light')) this.queued = 'light';
        if (d.pressed('heavy')) this.queued = 'heavy';
        if (d.pressed('dodge') && this.t > 0.1) this.queued = 'dodge';
        if (this.t >= dur) {
          const q = this.queued; this.queued = null;
          setState('idle');
          this.haste = 2;
          if (!this.skillBlink) this.proc('roll_end', ctx);
          if (this.S.dodge) ctx.send({ t: 'dodge', h: this.id, x0: Math.round(this.rollFrom[0]), y0: Math.round(this.rollFrom[1]), x1: Math.round(this.x), y1: Math.round(this.y) });
          // the bow's roll-shot flies where you're aiming now (the cursor, the stick, a locked-on boss), not the way you rolled
          if (G.kind === 'rollshot' && !this.skillBlink) { if (want !== null) this.aim = want; this.fire({ v: 380, r: G.boom ? 6 : 4, life: 0.9, n: G.n, spread: G.spread, boom: G.boom }, 'guard', ctx); }
          this.sinceDodge = 0;
          if (G.reload && W.ammo && !this.skillBlink) this.ammo = Math.min(W.ammo.max, this.ammo + G.reload);   // the cannon's slide chambers a round
          if (q === 'dodge') this.tryRoll(move, ctx);
          else if (q === 'light' || (q !== 'heavy' && d.held('light') && !d.held('heavy'))) {   // light out of a dodge: the dash-strike
            if (want !== null) this.aim = want;
            this.dashStrike(ctx) || this.startLight(0);
          }
          else if (q === 'heavy') this.startCharge(ctx);
        }
        speed = 0;
        break;
      }
      case 'atk': case 'mv': case 'heavy': case 'special': case 'cstrike': case 'skill': {
        const atk = this.attackData();
        // a step as you swing (back, for some); a skill's leap goes as far as what's aimed at, and lasts while it's in the air
        const stepPx = this.state === 'skill' && atk.leap ? this.leapStep : atk.step;
        const stepT = atk.step_t || (this.state === 'skill' && atk.air ? atk.air[1] : atk.hit ? atk.hit[1] : 0);
        if (stepPx && this.t < stepT) {
          const s = stepPx / stepT;
          this.x += Math.cos(this.aim) * s * dt; this.y += Math.sin(this.aim) * s * dt;
          this.passing = !!atk.pass;   // a cross-cut goes through what it cuts
        }
        if (atk.loop && want !== null) this.aim = want;   // the whirlwind has no front
        this.checkHit(atk, ctx);
        // what upgrades add to a strike, loosed once as it lands: on the combo's last light, on a heavy
        if (atk.hit && this.t >= atk.hit[0] && this.swing && !this.swing.proc) {
          this.swing.proc = true;
          if (this.state === 'atk' && this.combo === W.light.length - 1) this.proc('finisher', ctx);
          if (this.state === 'heavy') { this.proc('heavy', ctx); if (this.chargeU >= 0.95) this.proc('heavy_full', ctx); }
          if (this.state === 'special') this.proc('special', ctx);
          if (this.state === 'heavy' && atk.plant && !this.planted) {   // the war banner: the standard stays where it was slammed down
            this.planted = { x: this.x + Math.cos(this.aim) * 18, y: this.y + Math.sin(this.aim) * 18 };
            ctx.send({ t: 'plant', h: this.id, x: Math.round(this.planted.x), y: Math.round(this.planted.y) });
          }
        }
        if (this.state !== 'cstrike') {
          if (d.pressed('light')) this.queued = 'light';
          if (d.pressed('dodge')) this.queued = 'dodge';
          if (d.pressed('heavy')) this.queued = 'heavy';
          if (d.pressed('special') && this.canSpecial()) this.queued = 'special';
          if (d.pressed('heal') && this.h.flasks > 0) this.queued = 'heal';
        }
        const cut = this.queued === 'special' || this.queued === 'heal';
        const skillReady = this.skillBuf && !(this.skillCd[this.skillBuf.S.id] > 0);
        const chain = this.state === 'atk' || this.state === 'mv';   // lights and weapon moves flow into each other
        // a skill, the special or a drink pressed mid-combo goes off at the next gap, ahead of a held light
        if (chain && this.t >= atk.next && (skillReady || cut)) { this.comboWait = 0.45; setState('idle'); break; }
        // once the blow has landed (and the hero with it, if they leapt): a skill pressed during a heavy or a
        // special goes off, and a skill's own recovery gives way to a roll, a light or a heavy
        const landed = Math.max(atk.hit ? lastHit(atk) : atk.dur * 0.5, atk.air ? atk.air[1] : 0, atk.busy || 0) + 0.06;
        if ((this.state === 'heavy' || this.state === 'special') && skillReady && this.t >= landed) { setState('idle'); break; }
        if (this.state === 'skill' && this.t >= landed) {
          const q = this.queued || (d.held('light') && !d.held('heavy') ? 'light' : null);
          if (q === 'dodge') { this.queued = null; this.tryRoll(move, ctx); break; }
          if (q === 'light') { this.queued = null; if (want !== null) this.aim = want; this.startLight(0); break; }
          if (q === 'heavy') { this.queued = null; this.startCharge(ctx); break; }
          if (skillReady) { setState('idle'); break; }
        }
        if (atk.loop) {
          // the whirlwind: round again while light is held and there are dashes to spend; a roll or a heavy breaks out at once
          if (this.queued === 'dodge') { this.queued = null; this.tryRoll(move, ctx); break; }
          if (this.queued === 'heavy') { this.queued = null; this.startCharge(ctx); break; }
          if (this.t >= atk.dur) {
            this.queued = null;
            if (d.held('light') && this.dashes > 0.05) { this.t = 0; this.anT = 0; this.swing = { seq: ++swingSeq, struck: new Set(), fired: false }; ctx.onSwing && ctx.onSwing(this); }
            else { this.combo = 0; this.comboWait = 0; setState('idle'); }
          }
          speed = H.speed * speedK * (atk.walk || 0);
          break;
        }
        // Holding light runs the combo on, as a queued press does, and starts it again after the last hit.
        const more = this.queued || (chain && d.held('light') ? 'light' : null);
        if (chain && more && this.t >= atk.next) {
          this.queued = null;
          if (more === 'light' && this.state === 'mv') { this.startLight(0); break; }   // out of a dash-strike or a riposte, into the string
          if (more === 'light' && this.combo < W.light.length - 1) { this.startLight(this.combo + 1); break; }
          if (more === 'light' && atk.into && d.held('light') && this.dashes > 0.3) { this.startMove(atk.into, ctx); break; }   // held past the finisher: the whirlwind
          if (more === 'dodge') { this.tryRoll(move, ctx); break; }
          if (more === 'heavy') { this.startCharge(ctx); break; }
          this.queued = more === 'light' && !d.held('light') ? more : null;  // the last hit: a press waits for it to finish
        }
        // a roll cuts short the recovery of a heavy or a special too (once it has struck, and landed if it leapt)
        if (this.queued === 'dodge' && (this.state === 'heavy' || this.state === 'special')
            && this.t >= landed) {
          this.queued = null; this.tryRoll(move, ctx); break;
        }
        if (this.t >= atk.dur) {
          const q = skillReady ? null : this.queued || (chain && d.held('light') ? 'light' : null);
          const wasMove = this.state === 'mv';
          if (!cut) this.queued = null;
          this.comboWait = 0.45;
          setState('idle');
          if (q === 'dodge') this.tryRoll(move, ctx);
          else if (q === 'light') this.startLight(!wasMove && this.combo < W.light.length - 1 ? this.combo + 1 : 0);
        }
        speed = this.state === 'skill' && atk.walk ? H.speed * speedK * atk.walk : 0;   // some skills are cast walking
        break;
      }
      case 'pull': {   // the sickle has hooked a boss: the chain drags the hero to it, then the cut
        const P = this.pullTo, far = Math.hypot(P.x - this.x, P.y - this.y), go = 620 * dt;
        if (far <= 34 || this.t > 0.6) { this.aim = Math.atan2(P.y - this.y, P.x - this.x); this.startMove('reap', ctx); speed = 0; break; }
        this.x += (P.x - this.x) / far * Math.min(go, far); this.y += (P.y - this.y) / far * Math.min(go, far);
        this.passing = true;
        speed = 0;
        break;
      }
      case 'reload': {   // the cannon, broken open: press again as the ring passes the mark to finish at once, primed
        const R = W.ammo, u = this.t / R.reload;
        speed = H.speed * speedK * 0.5;
        if (d.pressed('dodge')) { this.tryRoll(move, ctx); break; }
        if (!this.fumbled && this.t > 0.12 && (d.pressed('light') || d.pressed('block'))) {
          if (this.t >= R.window[0] && this.t <= R.window[1]) { this.ammo = R.max; this.primed = true; setState('idle'); ctx.onCatch && ctx.onCatch(this, 'Primed!'); break; }
          this.fumbled = true; ctx.onDenied(this);
        }
        if (this.t >= R.reload + (this.fumbled ? R.fumble : 0)) { this.ammo = R.max; setState('idle'); ctx.onReload && ctx.onReload(this); }
        void u;
        break;
      }
      case 'charge':
        // fully charged: a flash and a chime. The bow's flash lasts as long as its Power Shot window: let fly while it shows.
        if (this.charge < W.heavy.charge && this.charge + dt >= W.heavy.charge) { this.flash = W.heavy.power ? W.heavy.power.window : 0.1; this.over = 0; ctx.onCharged(this); }
        else if (this.charge >= W.heavy.charge) {
          this.over += dt;
          // Sanguine Cleave: held half a second past full, it drinks health and hits harder (a second flash)
          if (this.S.overcharge && !this.oc && this.over >= 0.5 && (this.view.hp ? this.view.hp[0] : 0) > 10) { this.oc = true; this.flash = 0.14; ctx.onOver && ctx.onOver(this); }
        }
        this.charge = Math.min(W.heavy.charge, this.charge + dt);
        speed = H.speed * speedK * 0.25;
        if (!d.held('heavy')) {
          this.chargeU = this.charge / W.heavy.charge;
          this.power = !!W.heavy.power && this.chargeU >= 1 && this.over <= W.heavy.power.window;
          this.flash = 0;
          this.startAttack('heavy');
          if (this.power) ctx.onPower && ctx.onPower(this);
        }
        else if (d.pressed('dodge')) this.tryRoll(move, ctx);
        break;
      case 'drink':
        speed = H.speed * speedK * (this.S.drink_speed ? 1 : H.flask.speed);
        if (this.t >= H.flask.dur) setState('idle');
        if (d.pressed('dodge')) this.tryRoll(move, ctx);
        break;
      case 'block':
        speed = H.speed * speedK * G.speed;
        if (!d.held('block')) setState('idle');
        else if (d.pressed('dodge')) this.tryRoll(move, ctx);
        else if (d.pressed('light') && this.riposte > 0 && W.moves && W.moves.riposte) { this.riposte = 0; this.startMove('riposte', ctx); }   // the answer to a block or a parry
        else if (d.pressed('heavy') && W.moves && W.moves.rush && this.useDash()) this.startMove('rush', ctx);   // the charge behind the shield
        break;
      case 'cnt':  // the halberd's counter stance: anything that hits you now is answered
        speed = H.speed * speedK * (G.walk || 0);
        if (this.t >= G.window) setState('idle');
        break;
      default: { // idle / run
        if (this.comboWait > 0) this.comboWait -= dt; else this.combo = 0;
        const moving = move.x || move.y;
        this.state = moving ? 'run' : 'idle';
        if (d.pressed('dodge')) { this.tryRoll(move, ctx); break; }
        if (d.pressed('heavy')) { this.startCharge(ctx); break; }
        const q = this.queued; this.queued = null;   // the special or a drink asked for mid-attack
        if (d.pressed('light') && this.riposte > 0 && W.moves && W.moves.riposte) { this.riposte = 0; this.startMove('riposte', ctx); break; }
        if (d.pressed('light') && this.sinceDodge < 0.2 && this.dashStrike(ctx)) break;
        if ((d.pressed('special') || q === 'special') && this.canSpecial()) { this.startSpecial(ctx); break; }
        if (this.skillBuf && !(this.skillCd[this.skillBuf.S.id] > 0)) { const S = this.skillBuf.S; this.skillBuf = null; this.useSkill(S, move, ctx); break; }
        if ((d.pressed('heal') || q === 'heal') && this.h.flasks > 0) { setState('drink'); ctx.send({ t: 'drink', h: this.id }); this.proc('flask', ctx); break; }
        // light: a press, or the button held (after a roll, a skill or a drink the combo picks straight back up)
        if (d.pressed('light') || (d.held('light') && !d.held('heavy'))) { this.startLight(this.comboWait > 0 && this.combo < W.light.length - 1 ? this.combo + 1 : 0); break; }
        if (G.kind === 'block' && d.held('block')) { setState('block'); break; }
        if (W.ammo && W.ammo.reload && d.pressed('block')) { this.startReload(); break; }
        if (G.kind === 'counter' && d.pressed('block') && this.useDash(G.cost)) { setState('cnt'); break; }
      }
    }

    // reviving a downed ally: stand by them and hold interact
    const fallen = ctx.allies.find(a => a.down && !a.dead && Math.hypot(a.x - this.x, a.y - this.y) < 30);
    if (fallen && d.held('interact') && ['idle', 'run'].includes(this.state)) {
      this.reviving = fallen.id; this.reviveT += dt; speed = 0;
      if (this.reviveT >= H.down.revive * (this.S.revive_time || 1)) { ctx.send({ t: 'revive', h: this.id, who: fallen.id }); this.reviveT = 0; }
    } else { this.reviving = null; this.reviveT = 0; }

    if (this.isHeld(ctx.now)) speed = 0;
    this.vx = move.x * speed; this.vy = move.y * speed;
    this.x += this.vx * dt; this.y += this.vy * dt;
    if (this.state === 'run' && !(move.x || move.y)) this.state = 'idle';
    ctx.collide(this);
    // did they move this frame? (an edict to stand still is judged on this)
    this.moving = Math.hypot(this.x - (this.px ?? this.x), this.y - (this.py ?? this.y)) > 0.02;
    this.px = this.x; this.py = this.y;
  }

  attackData() {
    const W = this.W;
    switch (this.state) {
      case 'atk': return W.light[this.combo];
      case 'mv': return W.moves[this.mv];
      case 'heavy': return W.heavy;
      case 'special': return W.special;
      case 'skill': return this.skill;
      default: return { ...W.guard, dur: 0.45, hit: [0.08, 0.16], step: 14 };  // the counter-strike
    }
  }

  // caught by a tongue or a chain: can't move or dodge until it lets go (attacks still work)
  isHeld(now) { return !!this.held && now < this.held.until; }

  tryRoll(move, ctx) {
    if (this.isHeld(ctx.now)) { this.denied = { id: 'dash', until: performance.now() + 350 }; return; }
    const G = this.W.guard, dir = move.x || move.y ? Math.atan2(move.y, move.x) : this.aim;
    const kind = G.dodge || G.kind;   // a blessing can change the dodge itself (Stormstep: a blink)
    if (!this.useDash(kind === 'dash' && G.cost ? G.cost : 1)) return;   // the gauntlets' weave costs half a dash
    this.skillBlink = false; this.blinkDur = 0.16; this.passSwing = {};
    this.rollFrom = [this.x, this.y];
    if (kind === 'dash') this.state = 'dash';
    else if (kind === 'blink') {
      this.x += Math.cos(dir) * G.dist; this.y += Math.sin(dir) * G.dist;
      ctx && ctx.collide(this);
      ctx && ctx.onBlink(this);
      if (G.burst && ctx) {   // the catalyst leaves a burst where it stood
        const [bx, by] = this.rollFrom, U = G.burst;
        this.aoes.push({ x: bx, y: by, r: U.r, wait: U.delay, ticks: 1, every: 0.2, kind: 'move:' + (U.as || 'dash'), col: U.col, boom: true });
        ctx.send({ t: 'shot', h: this.id, k: 'aoe', x: Math.round(bx), y: Math.round(by), r: U.r, life: U.delay + 0.05, col: U.col, p: 0 });
      }
      this.state = 'blink';
      if (ctx) this.passStrike(ctx, this.rollFrom);
    } else this.state = 'roll';
    this.rollDir = dir;
    if (move.x || move.y) this.aim = dir;
    this.t = 0; this.anT = 0; this.queued = null;
  }

  // A dodge that strikes (blessings with a `pass` proc): everything within `pass` px of the hero as they
  // go, once a dodge; a blink strikes the whole line it crossed (`from`: where it began).
  passStrike(ctx, from) {
    for (const P of this.procs) {
      if (P.when !== 'pass') continue;
      const sw = this.passSwing[P.id] ||= { seq: ++swingSeq, struck: new Set() };
      const s = from ? { k: 'rect', cx: from[0], cy: from[1], a: Math.atan2(this.y - from[1], this.x - from[0]), x0: 0, x1: Math.hypot(this.x - from[0], this.y - from[1]), w: P.pass }
        : { k: 'circle', cx: this.x, cy: this.y, r: P.pass };
      if (from && ctx.onPass) ctx.onPass(from[0], from[1], this.x, this.y, P.col);
      this.strike(s, 'proc:' + P.id, sw, ctx);
    }
  }

  // Start a skill: its cooldown begins, the server is told (it applies cries, wards and heals, and shows
  // everyone), and a blink carries you off at once, the way you're walking or else the way you aim.
  useSkill(S, move, ctx) {
    let cd = S.cd * (this.S.skill_cd || 1), ff = 0;
    if (this.S.meditate && this.focus >= this.HERO.focus - 0.5) { this.focus -= 30; cd *= 0.5; ff = 1; }   // Meditation
    this.skillCd[S.id] = cd;
    if (S.dashes) this.dashes = this.maxDash;
    if (S.free) { this.freeUntil = ctx.now + S.free; this.perfectFocus = S.perfect_focus || 0; }
    if (S.guard) this.wardUntil = ctx.now + S.guard;
    this.focus = Math.min(this.HERO.focus, this.focus + (S.focus || 0) + (this.S.skill_focus || 0));
    if (!S.instant) {   // a cast: the hero plays it, facing where the player aims now
      if (this.wantA !== null) { this.aim = this.wantA; this.aimDist = this.wantDist; }
      this.skill = S; this.state = 'skill'; this.t = 0; this.anT = 0; this.queued = null;
      this.swing = { seq: ++swingSeq, struck: new Set(), fired: false };
      this.lastAoe = null;
      if (S.leap) this.leapStep = Math.max(20, Math.min(S.leap, (this.wantDist ?? S.leap * 0.65) - 18));
    }
    if (S.blink) {
      const dir = move.x || move.y ? Math.atan2(move.y, move.x) : this.aim, from = [this.x, this.y];
      this.x += Math.cos(dir) * S.blink; this.y += Math.sin(dir) * S.blink;
      ctx.collide(this); ctx.onBlink(this);
      this.blinkTo(from, dir, S.iframes || 0.16, ctx);
      if (S.recast) this.recast = { id: S.id, until: ctx.now + S.recast, x: from[0], y: from[1] };
    }
    ctx.send({ t: 'skill', h: this.id, sk: S.id, x: Math.round(this.x), y: Math.round(this.y), a: Math.round(this.aim * 100) / 100, ...(ff ? { ff } : {}) });
  }
  // a skill's blink has carried the hero: untouchable for `dur`, and it strikes what it crossed if a blessing says so
  blinkTo(from, dir, dur, ctx) {
    this.rollFrom = from; this.rollDir = dir; this.blinkDur = dur; this.skillBlink = true; this.passSwing = {};
    this.state = 'blink'; this.t = 0; this.anT = 0; this.queued = null;
    this.passStrike(ctx, from);
  }
  // a skill pressed again while its second act is waiting: step back to where you left, or call the knives home
  doRecast(S, ctx) {
    const R = this.recast;
    if (S.blink) {
      if (this.isHeld(ctx.now) || this.state === 'hurt') return;
      this.recast = null;
      const from = [this.x, this.y];
      this.x = R.x; this.y = R.y;
      ctx.collide(this); ctx.onBlink(this);
      this.blinkTo(from, Math.atan2(this.y - from[1], this.x - from[0]), 0.16, ctx);
    } else if (S.stick) {
      this.recast = null;
      for (const k of this.stuck) {
        const a = Math.atan2(this.y - 10 - k.y, this.x - k.x), v = 520;
        this.shots.push({ x: k.x, y: k.y, a, v, r: 5, life: Math.hypot(this.x - k.x, this.y - 10 - k.y) / v + 0.3, pierce: true, col: S.col, kind: 'skill:' + S.id + ':back', combo: 0, c: 0,
          home: true, swing: { seq: ++swingSeq, struck: new Set(), shot: true } });
        ctx.send({ t: 'shot', h: this.id, k: 'proj', x: Math.round(k.x), y: Math.round(k.y), a: Math.round(a * 1000) / 1000, v, r: 5, life: Math.hypot(this.x - k.x, this.y - 10 - k.y) / v, col: S.col });
      }
      if (this.stuck.length) { ctx.send({ t: 'shot', h: this.id, k: 'end', id: this.stuckId }); ctx.onSwing && ctx.onSwing(this); }
      this.stuck = [];
    }
  }
  // Stone Ward soaked a hit: half its cooldown comes back and a burst answers
  wardBurst(ctx) {
    const S = SKILLS.ward;
    if (!S) return;
    this.skillCd.ward = Math.max(0, (this.skillCd.ward || 0) - S.cd * (this.S.skill_cd || 1) * S.refund);
    this.aoes.push({ x: this.x, y: this.y, r: S.burst_r, wait: 0.02, ticks: 1, every: 0.2, kind: 'skill:ward:burst', col: S.col, boom: true });
    ctx.send({ t: 'shot', h: this.id, k: 'aoe', x: Math.round(this.x), y: Math.round(this.y), r: S.burst_r, life: 0.1, col: S.col, p: 0 });
  }

  startLight(i) {
    const W = this.W, need = W.light[i].ammo;
    if (need && this.ammo < need) {   // nothing in hand or in the breech
      if (W.ammo.reload) { this.startReload(); return; }
      this.combo = i; this.startMove('punch'); return;   // the chakrams are away: fists
    }
    this.combo = i;
    this.startAttack('atk');
  }

  // a weapon's named move (content/weapons.py, `moves`)
  startMove(name, ctx) {
    this.mv = name;
    this.startAttack('mv', ctx);
  }
  // light out of a dodge, if this weapon has a strike for it
  dashStrike(ctx) {
    const M = this.W.moves && this.W.moves.dash;
    if (!M || !M.anim) return false;
    this.sinceDodge = 9;
    this.startMove('dash', ctx);
    return true;
  }

  startAttack(kind, ctx) {
    this.state = kind; this.t = 0; this.anT = 0; this.fresh = true;
    if (kind !== 'heavy') this.power = false;
    this.swing = { seq: ++swingSeq, struck: new Set(), fired: false };
    this.lastAoe = null;
    if (kind === 'heavy' && this.oc) this.swing.fl = { oc: 1 };
    if (kind === 'heavy' && this.W.heavy.spend && this.streak > 0) this.swing.fl = { ...this.swing.fl, sk: this.streak };   // the uppercut spends the streak
    const atk = this.attackData();
    if (atk.blink) {  // the daggers' shadowstep: appear beside your target first
      const b = ctx && atk.behind ? ctx.boss.nearest(this.x, this.y) : null;
      if (b && b.alive && Math.hypot(b.x - this.x, b.y - this.y) < atk.blink + b.r + 30) {   // Umbral Step: out behind its back
        const back = b.face + Math.PI, d = b.r + 20;
        this.x = b.x + Math.cos(back) * d; this.y = b.y + Math.sin(back) * d;
        ctx.collide(this);
        this.aim = Math.atan2(b.y - this.y, b.x - this.x);
        this.swing.fl = { ...this.swing.fl, bk: 1 };   // from behind, whichever way it has turned by the time the cut lands
      } else { this.x += Math.cos(this.aim) * atk.blink; this.y += Math.sin(this.aim) * atk.blink; }
      if (ctx) { ctx.collide(this); ctx.onBlink(this); }
    }
  }

  // Loose every extra attack this hero's upgrades hang on `when` (finisher, heavy, heavy_full, roll_end,
  // guard, perfect, flask): a projectile along the aim, or an area hit. An area lands `at` px ahead (for
  // a bow or catalyst, on what's aimed at), or halfway back along the roll just made (`mid`). The server
  // prices each hit from the upgrade (atk 'proc').
  proc(when, ctx) {
    for (const P of this.procs) {
      if (P.when !== when || P.pass) continue;
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
        // for an attack that is a shot or lands far off, the area goes to what's aimed at, not the hero's feet
        const far = when === 'finisher' && this.W.light.at(-1).proj ? Math.min(260, this.aimDist ?? 150) : A.at;
        let x = this.x + Math.cos(this.aim) * far, y = this.y + Math.sin(this.aim) * far;
        if ((when === 'special' || when.startsWith('heavy')) && this.lastAoe) ({ x, y } = this.lastAoe);   // where the attack's own area landed (the bow's rain, the cannon's shell)
        if (A.mid && this.rollFrom) { x = (this.x + this.rollFrom[0]) / 2; y = (this.y + this.rollFrom[1]) / 2; }
        this.procArea(P, x, y, ctx);
      }
    }
  }

  // an upgrade's area hit, at (x, y)
  procArea(P, x, y, ctx) {
    const A = P.aoe;
    this.aoes.push({ x, y, r: A.r, wait: A.delay, ticks: A.ticks, every: A.every, kind: 'proc:' + P.id, col: A.col, pillar: !!A.pillar, boom: !!A.boom, pool: A.ticks > 1, clear: !!A.clear });
    ctx.send({ t: 'shot', h: this.id, k: 'aoe', x: Math.round(x), y: Math.round(y), r: A.r, life: A.delay + (A.ticks - 1) * A.every + 0.05, col: A.col, p: A.pillar ? 1 : A.ticks > 1 ? 2 : 0 });
  }

  // which attack a hit is reported as; a skill's is 'skill:<id>'
  slot() { return this.state === 'skill' ? 'skill:' + this.skill.id : this.state === 'mv' ? 'move:' + this.mv : { atk: 'light', heavy: 'heavy', special: 'special', cstrike: 'guard' }[this.state] || 'light'; }

  // one swing strikes each thing it touches once: a body (or one of its weak points), adds.
  // Ranged attacks fire their projectiles or call down their area hit instead.
  checkHit(atk, ctx) {
    if (!atk.hit || this.t < atk.hit[0]) return;
    const kind = this.slot();
    // further hit windows (the halberd's double jab): each strikes afresh, with its own sound
    let hit = atk.hit, win = 0;
    (atk.more || []).forEach((w, i) => { if (this.t >= w[0]) { hit = w; win = i + 1; } });
    if (win !== (this.swing.win || 0)) { this.swing = { seq: ++swingSeq, struck: new Set(), fired: false, proc: this.swing.proc, thrown: true, win, fl: this.swing.fl }; ctx.onSwing && ctx.onSwing(this); }
    // shots loosed with a melee swing (the daggers' knives), priced as their own move
    if (atk.throw && !this.swing.thrown) { this.swing.thrown = true; this.fire(atk.throw, 'move:' + atk.throw.as, ctx); }
    // A shot or a called-down area is loosed once, on the first frame at or after its moment: its
    // window is only 10 ms wide, and a frame (17 ms at 60 a second) can step clean over it.
    const skill = this.state === 'skill';
    if (atk.ammo && (atk.proj || atk.aoe) && !this.swing.fired) {   // a round fired, a disc thrown: a primed one (a caught disc, a timed reload) hits harder
      this.ammo = Math.max(0, this.ammo - atk.ammo);
      if (this.primed) { this.primed = false; this.swing.fl = { ...this.swing.fl, ch: 1 }; }
    }
    if ((atk.proj || atk.aoe) && skill && !this.swing.fired && this.wantA !== null) { this.aim = this.wantA; this.aimDist = this.wantDist; }   // a skill goes where the player aims as it fires
    if (atk.proj) {
      if (!this.swing.fired) {
        this.swing.fired = true;
        this.fire(this.state === 'heavy' && this.power ? atk.power.proj : skill && atk.stick ? { ...atk.proj, stick: atk.stick } : atk.proj, kind, ctx);
        if (skill && atk.trail) {   // the lance's path burns: pools along it
          const T = atk.trail;
          for (let i = 0; i < T.n; i++) {
            const x = this.x + Math.cos(this.aim) * (T.from + i * T.gap), y = this.y + Math.sin(this.aim) * (T.from + i * T.gap);
            this.aoes.push({ x, y, r: T.r, wait: T.delay + i * 0.04, ticks: T.ticks, every: T.every, kind: kind + ':trail', col: atk.col, pool: true });
            ctx.send({ t: 'shot', h: this.id, k: 'aoe', x: Math.round(x), y: Math.round(y), r: T.r, life: T.delay + T.ticks * T.every, col: atk.col, p: 2 });
          }
        }
        if (skill && atk.recast && atk.stick) this.recast = { id: atk.id, until: ctx.now + atk.recast };
      }
      return;
    }
    if (atk.aoe) {
      if (!this.swing.fired) {
        this.swing.fired = true;
        const A = atk.aoe;
        // `range`: it lands on what you aim at (the cursor, the boss you're locked on to), up to that far
        const at = A.range && this.aimDist != null ? Math.min(A.range, this.aimDist) : A.at;
        this.aoes.push({ x: this.x + Math.cos(this.aim) * at, y: this.y + Math.sin(this.aim) * at, r: A.r, wait: A.delay, ticks: A.ticks, every: A.every, kind,
          col: atk.col, pillar: !!A.range && A.ticks === 1 && !A.shell, boom: !!A.shell, pool: A.ticks > 3, carry: !!A.carry, follow: A.follow || 0, fl: this.swing.fl });
        this.lastAoe = { x: this.aoes.at(-1).x, y: this.aoes.at(-1).y };
        if (skill && atk.zone && atk.zone.at === 'aoe') ctx.send({ t: 'zone', h: this.id, sk: atk.id, x: Math.round(this.lastAoe.x), y: Math.round(this.lastAoe.y) });
        ctx.send({ t: 'shot', h: this.id, k: 'aoe', x: Math.round(this.aoes.at(-1).x), y: Math.round(this.aoes.at(-1).y), r: A.r,
          life: A.follow ? A.delay + A.every : A.range && A.ticks === 1 ? A.delay : A.delay + A.ticks * A.every, col: atk.col, p: A.range && A.ticks === 1 && !A.shell ? 1 : A.ticks > 3 ? 2 : 0 });
      }
      return;
    }
    if (this.t > hit[1]) return;
    const s = placeAttack(reach(atk.shape, this.state === 'skill' ? 1 : this.S.reach || 1), this.x, this.y, this.aim);
    this.strike(s, kind, this.swing, ctx);
    if (!skill && atk.clear && !this.swing.cleared) { this.swing.cleared = true; ctx.clearShots(this, this.x, this.y, atk.clear); }   // the chain whirl too
    if (skill && atk.clear && !this.swing.cleared) { this.swing.cleared = true; ctx.clearShots(this, this.x, this.y, atk.clear); }   // the nova shatters the boss's shots
  }

  // send a hit for everything shape s touches that this swing hasn't struck yet
  strike(s, kind, swing, ctx) {
    const [, sk, sub] = kind.split(':');   // a skill's hit is 'skill:<id>', one of its further hits 'skill:<id>:<sub>'
    const fl = swing.fl || {};             // what the server should know of this swing (an overcharge, an echo)
    const base = kind.startsWith('skill:') ? { h: this.id, atk: 'skill', sk, sw: swing.seq, ...(sub ? { sub } : {}) }
      : kind.startsWith('proc:') ? { h: this.id, atk: 'proc', p: kind.slice(5), sw: swing.seq }
      : kind.startsWith('move:') ? { h: this.id, atk: 'move', m: kind.slice(5), sw: swing.seq }
      : { h: this.id, atk: kind, i: this.combo, c: this.chargeU || 0, sw: swing.seq, ...fl };
    let any = false;
    for (const tg of ctx.boss.targets(ctx.now)) {
      const key = tg.kind === 'add' ? 'a' + tg.a : tg.kind === 'shot' ? 's' + tg.seq + ':' + tg.i : 'b' + tg.e;
      if (swing.struck.has(key) || !touches(s, tg.x, tg.y, tg.r)) continue;
      swing.struck.add(key);
      if (tg.kind === 'shot') {   // one of the boss's own projectiles, struck back at it
        tg.mv.gone.add(tg.i);
        ctx.send({ t: 'reflect', h: this.id, seq: tg.seq, i: tg.i });
        continue;
      }
      any = true;
      if (kind.startsWith('skill:') && SKILLS[sk] && SKILLS[sk].cdhit && !sub && !swing.cdhit) { swing.cdhit = true; this.skillCd[sk] -= SKILLS[sk].cdhit; }   // each strike that lands brings it back sooner
      const ST = this.W.streak;   // gauntlets: every blow of their own that lands adds to the streak; the uppercut that spent it starts it over
      if (ST && !kind.startsWith('skill:') && !kind.startsWith('proc:') && !swing.streaked) {
        swing.streaked = true;
        this.streak = fl.sk ? 0 : Math.min(ST.max, this.streak + 1); this.streakT = ST.live;
      }
      if (kind === 'move:dash' && this.S.dash_refund && !swing.refund) { swing.refund = true; this.dashes = Math.min(this.maxDash, this.dashes + 1); }   // Follow Through
      // what only this weapon does (the server prices it): from behind a boss, with the tip of the reach, a Power Shot
      const W = this.W, own = !kind.startsWith('skill:') && !kind.startsWith('proc:') && kind !== 'guard';
      let bonus = null;
      if (own && tg.kind === 'body' && tg.b) {
        if (W.backstab && Math.abs(wrap(Math.atan2(this.y - tg.b.y, this.x - tg.b.x) - tg.b.face)) > 2.0) bonus = 'bk';
        const far = s.k === 'rect' ? s.x1 : s.k === 'arc' ? s.r : 0;
        if (W.tip && far && !swing.shot && Math.hypot(tg.x - this.x, tg.y - this.y) - tg.r > far * W.tip_from) bonus = 'tip';
        if (swing.power) bonus = 'pw';
        if (fl.bk && W.backstab) bonus = 'bk';
        if (fl.ch) bonus = 'ch';
      }
      if (tg.kind === 'add') { ctx.send({ t: 'hitadd', a: tg.a, ...base }); tg.add.flash = 0.08; }
      else ctx.send({ t: 'hit', e: tg.e, core: tg.kind === 'core' ? tg.i : undefined, ...base, ...(bonus ? { [bonus]: 1 } : {}) });
      ctx.onHit(this, kind, tg, bonus);
    }
    return any;
  }

  fire(P, kind, ctx) {
    // upgrades: light arrows that pierce, an extra bolt on every light cast
    const light = kind === 'light', more = light ? this.S.light_shots || 0 : 0;
    if (light && this.S.light_pierce) P = { ...P, pierce: true };
    const n = (P.n_full && (this.chargeU || 0) >= 0.95 ? P.n_full : P.n || 1) + more, spread = P.spread || (more ? 12 : 0);
    for (let i = 0; i < n; i++) {
      const a = this.aim + (spread * (i - (n - 1) / 2)) * Math.PI / 180;
      const shot = { x: this.x + Math.cos(a) * 12, y: this.y + Math.sin(a) * 12, a, v: P.v, r: P.r, life: P.life, pierce: P.pierce, boom: P.boom, back: P.back, stick: P.stick, disc: P.disc, hover: P.hover, hook: P.hook,
        col: P.col, kind, combo: this.combo, c: this.chargeU || 0, swing: { seq: ++swingSeq, struck: new Set(), shot: true, power: kind === 'heavy' && this.power, fl: this.swing ? this.swing.fl : null } };
      this.shots.push(shot);
      ctx.send({ t: 'shot', h: this.id, k: 'proj', x: Math.round(shot.x), y: Math.round(shot.y), a: Math.round(a * 1000) / 1000, v: P.v, r: P.r, life: P.life, col: P.col });
    }
  }

  stepShots(dt, ctx) {
    for (const s of this.shots) {
      if (s.home) {   // flying back to the hand (a returning shield, knives called home): it follows the hero and is caught
        s.a = Math.atan2(this.y - 10 - s.y, this.x - s.x);
        if (Math.hypot(this.x - s.x, this.y - 10 - s.y) < 14) s.life = 0;
      }
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
      if (hit && s.hook && !s.home) {   // the sickle bites: the chain drags the hero in (untouchable on the way) to cut
        s.stick = 0;
        if (!this.down && !this.isHeld(ctx.now)) { this.pullTo = { x: s.x, y: s.y }; this.state = 'pull'; this.t = 0; this.anT = 0; this.queued = null; ctx.onBlink(this); }
      }
      if (s.disc && s.life <= 0) {
        const A = this.W.ammo;
        if (s.hover && !s.turned) {   // it hangs where it landed, sawing, then comes to hand
          const U = s.hover;
          this.aoes.push({ x: s.x, y: s.y, r: U.r, wait: 0.1, ticks: U.ticks, every: U.every, kind: 'move:' + U.as, col: s.col, pool: true });
          ctx.send({ t: 'shot', h: this.id, k: 'aoe', x: Math.round(s.x), y: Math.round(s.y), r: U.r, life: U.ticks * U.every, col: s.col, p: 2 });
          this.late.push(U.ticks * U.every + 0.3);
        } else if (!s.turned) {   // at the end of its flight a disc turns for where the hero stands now, cutting afresh on the way
          s.turned = true;
          const tx = this.x, ty = this.y - 10, far = Math.hypot(tx - s.x, ty - s.y);
          s.a = Math.atan2(ty - s.y, tx - s.x); s.life = Math.max(0.08, far / s.v);
          s.swing = { seq: ++swingSeq, struck: new Set(), shot: true, fl: s.swing.fl };
          ctx.send({ t: 'shot', h: this.id, k: 'proj', x: Math.round(s.x), y: Math.round(s.y), a: Math.round(s.a * 1000) / 1000, v: s.v, r: s.r, life: Math.round(s.life * 100) / 100, col: s.col });
        } else if (Math.hypot(this.x - s.x, this.y - 10 - s.y) <= A.catch && !this.down) {   // there to meet it: caught, and the next throw is the stronger for it
          this.ammo = Math.min(A.max, this.ammo + 1); this.primed = true;
          ctx.onCatch && ctx.onCatch(this, 'Caught!');
        } else this.late.push(A.late);   // it finds its own way back, later
      }
      if (s.life <= 0 && s.back && !s.home) {   // at the end of its flight it turns for home, striking afresh on the way
        s.home = true; s.pierce = true; s.life = Math.hypot(this.x - s.x, this.y - 10 - s.y) / s.v + 0.4;
        s.swing = { seq: ++swingSeq, struck: new Set(), shot: true, fl: s.swing.fl };
        s.a = Math.atan2(this.y - 10 - s.y, this.x - s.x);
        ctx.send({ t: 'shot', h: this.id, k: 'proj', x: Math.round(s.x), y: Math.round(s.y), a: Math.round(s.a * 1000) / 1000, v: s.v, r: s.r, life: Math.round((s.life - 0.4) * 100) / 100, col: s.col });
      } else if (s.life <= 0 && s.stick && !s.home) {   // a knife stays where it landed, to be called back
        if (!this.stuck.length) this.stuckId = ++swingSeq;
        this.stuck.push({ x: s.x, y: s.y, a: s.a, col: s.col, until: ctx.now + s.stick, r: s.hook ? 6 : 3 });
        ctx.send({ t: 'shot', h: this.id, k: 'proj', x: Math.round(s.x), y: Math.round(s.y), a: Math.round(s.a * 1000) / 1000, v: 0, r: 4, life: s.stick, col: s.col, id: this.stuckId });
      }
    }
    this.shots = this.shots.filter(s => s.life > 0);
    if (this.stuck.length) this.stuck = this.stuck.filter(k => k.until > ctx.now);
    for (const A of this.aoes) {
      if (A.carry) { A.x = this.x; A.y = this.y; }   // it goes with the hero (the whirl)
      A.wait -= dt;
      if (A.wait <= 0 && A.ticks > 0) {
        A.ticks--; A.wait = A.every;
        if (A.follow) {   // it drifts after the boss between strikes (Hunting Rain)
          const b = ctx.boss.nearest(A.x, A.y), d = Math.hypot(b.x - A.x, b.y - A.y), k = b.alive ? Math.min(1, A.follow / Math.max(1, d)) : 0;
          A.x += (b.x - A.x) * k; A.y += (b.y - A.y) * k;
          if (A.ticks > 0) ctx.send({ t: 'shot', h: this.id, k: 'aoe', x: Math.round(A.x), y: Math.round(A.y), r: A.r, life: A.every + 0.05, col: A.col, p: 0 });
        }
        if (A.pillar) ctx.onPillar(A.x, A.y, A.r, A.col);
        else if (A.boom) ctx.onBoom(A.x, A.y, A.r, A.col);
        this.strike({ k: 'circle', cx: A.x, cy: A.y, r: A.r }, A.kind, { seq: ++swingSeq, struck: new Set(), fl: A.fl }, ctx);
        if (A.clear) ctx.clearShots(this, A.x, A.y, A.r);
      }
    }
    this.aoes = this.aoes.filter(A => A.ticks > 0);
  }

  // a boss hit reached this hero on this browser: returns 'parry', 'block', 'counter' or 'hurt' (or null)
  takeHit(h, bossX, bossY) {
    if (this.down || this.dead || this.invulnerable()) return null;
    const W = this.W, G = W.guard;
    if (this.now < this.wardUntil && !h.room) { this.wardUntil = 0; return 'ward'; }   // Stone Ward: soaked whole (not a room-wide blast)
    const toBoss = Math.atan2(bossY - this.y, bossX - this.x);
    // Living Wall: while a heavy is charged, hits from the front are blocked (each uses a dash)
    if (this.state === 'charge' && W.heavy.guardcharge && !h.unblock && Math.abs(wrap(toBoss - this.aim)) <= G.arc * Math.PI / 180
        && this.useDash(G.cost * (this.S.block_cost || 1))) return 'block';
    if (this.state === 'block' && !h.unblock) {
      if (Math.abs(wrap(toBoss - this.aim)) <= G.arc * (this.S.guard_arc || 1) * Math.PI / 180) {
        if (this.parryWin > 0 && this.blockAge <= this.parryWin && !h.noparry) { this.riposte = 0.8; return 'parry'; }
        if (this.nearStand || this.useDash(G.cost * (this.S.block_cost || 1))) { this.riposte = 0.6; return 'block'; }   // beside the standard a block costs nothing  // a blocked hit uses a dash; with none left the guard breaks
      }
    }
    // the charge behind the shield (it paid its dash to start): hits from the front are blocked as it goes
    if (this.state === 'mv' && W.moves[this.mv].guarding && !h.unblock && this.t <= lastHit(W.moves[this.mv]) + 0.05
        && Math.abs(wrap(toBoss - this.aim)) <= G.arc * Math.PI / 180) return 'block';
    if (this.state === 'cnt' && !h.unblock) {  // answered: no damage, and a strike back
      this.aim = toBoss;
      this.state = 'cstrike'; this.t = 0; this.anT = 0;
      this.swing = { seq: ++swingSeq, struck: new Set(), fired: false };
      return 'counter';
    }
    this.flash = 0.12;
    if (W.streak) this.streak = Math.floor(this.streak * (W.streak.keep || 0));   // a hit taken ends the streak
    if (this.state === 'reload') this.fumbled = true;
    if (this.state === 'special' && W.special.hyper) return 'hurt';   // the scythe's Harvest isn't interrupted
    if (this.state === 'pull') return 'hurt';
    if (this.state === 'heavy' && W.heavy.hyper) return 'hurt';
    if (this.state === 'charge' && W.heavy.hypercharge) return 'hurt';   // Siegebreaker: the charge isn't broken either
    if (this.state === 'mv' && W.moves[this.mv].loop) return 'hurt';   // the whirlwind turns on through a hit  // hyper-armour: hurt, but no flinch
    const away = Math.atan2(this.y - bossY, this.x - bossX), kb = h.kb || 30;
    this.kb = { vx: Math.cos(away) * kb * 5, vy: Math.sin(away) * kb * 5, t: 0.2 };
    this.state = 'hurt'; this.t = 0; this.anT = 0;
    return 'hurt';
  }

  draw() {
    const W = this.W, V = this.view;
    V.pips = W.streak ? [this.streak, W.streak.max, 0xffa040] : W.ammo ? [this.ammo, W.ammo.max, this.primed ? 0xfff0c0 : 0xa8e0ff] : null;
    V.reload = this.state === 'reload' ? [this.t / W.ammo.reload, W.ammo.window[0] / W.ammo.reload, W.ammo.window[1] / W.ammo.reload, this.fumbled] : null;
    // what's out of the hands: a planted standard, discs in the air (the back hand's goes first), the thrown sickle
    V.noOff = !!this.planted || (!!W.ammo && !W.ammo.reload && this.ammo < W.ammo.max);
    V.noWeapon = (!!W.ammo && !W.ammo.reload && this.ammo < 1) || (!!(W.heavy.proj && W.heavy.proj.hook) && (this.stuck.length > 0 || this.shots.some(q => q.hook || q.kind === 'move:yank')));
    this.drawInner();
  }
  drawInner() { this.view.reachK = this.S.reach || 1; this.view.dash = [this.dashes, this.maxDash]; this.view.draw(this.x, this.y, this.an(), this.anT, this.aim, this.flash > 0); }
  report() { return { t: 'st', h: this.id, x: Math.round(this.x * 10) / 10, y: Math.round(this.y * 10) / 10, f: Math.round(this.aim * 100) / 100, an: this.an(), at: Math.round(this.anT * 100) / 100 }; }
}

export class RemoteHero {
  constructor(scene, h, data) {
    this.h = h; this.id = h.id;
    this.W = weaponOf(data, h); this.HERO = data.hero;
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
