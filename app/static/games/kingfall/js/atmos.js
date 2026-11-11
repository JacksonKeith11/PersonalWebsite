// The fight's atmosphere, drawn over the painted arena: a colour grade on the floor (characters and
// effects stay untouched, so they stand out), a vignette on the screen, motes drifting in the air (embers,
// spores, dust, ash, snow), a soft light under each hero in their colour, and dust kicked up by rolls and
// landings. Nothing here is gameplay; it all reads the scene and draws.

// per arena: grade (multiplied over the floor) and its strength; motes: colour, how many, how they drift
const LOOK = {
  chapel:   { grade: 0xffd8a8, ga: 0.5, mote: 0xffb060, n: 26, kind: 'ember', vig: 0.62 },
  bog:      { grade: 0x9ac890, ga: 0.55, mote: 0xb8f080, n: 40, kind: 'spore', vig: 0.7 },
  belfry:   { grade: 0xb0b8e0, ga: 0.5, mote: 0xd8d8f0, n: 30, kind: 'dust', vig: 0.66 },
  yard:     { grade: 0xe8c8a8, ga: 0.45, mote: 0xc8b8a0, n: 26, kind: 'dust', vig: 0.6 },
  forest:   { grade: 0x98c8a0, ga: 0.45, mote: 0x9ae070, n: 30, kind: 'leaf', vig: 0.72 },
  lab:      { grade: 0xd8c0f0, ga: 0.5, mote: 0xc8f0a0, n: 32, kind: 'spore', vig: 0.66 },
  boneyard: { grade: 0xc8c0b0, ga: 0.5, mote: 0xe8e0d0, n: 30, kind: 'ash', vig: 0.68 },
  glass:    { grade: 0xb8e0f0, ga: 0.45, mote: 0xe0f8ff, n: 38, kind: 'glint', vig: 0.6 },
  wall:     { grade: 0xf0c098, ga: 0.5, mote: 0xffa050, n: 28, kind: 'ember', vig: 0.62 },
  sanctum:  { grade: 0xf0d8b0, ga: 0.5, mote: 0xfff0c0, n: 44, kind: 'dust', vig: 0.7 },
  throne:   { grade: 0xc0a8d8, ga: 0.55, mote: 0xffd870, n: 30, kind: 'dust', vig: 0.72 },
  bridge:   { grade: 0xe0b0a0, ga: 0.5, mote: 0xff8040, n: 46, kind: 'ash', vig: 0.66 },
};
const DEFAULT = { grade: 0xe0d8d0, ga: 0.4, mote: 0xe8e0d0, n: 26, kind: 'dust', vig: 0.62 };

function vignetteTexture(scene) {
  if (scene.textures.exists('vignette')) return;
  const cv = document.createElement('canvas'); cv.width = cv.height = 256;
  const g = cv.getContext('2d'), gr = g.createRadialGradient(128, 128, 50, 128, 128, 150);
  gr.addColorStop(0, 'rgba(5,3,10,0)'); gr.addColorStop(0.5, 'rgba(5,3,10,0.3)'); gr.addColorStop(1, 'rgba(5,3,10,0.95)');
  g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
  scene.textures.addCanvas('vignette', cv);
}

export class Atmos {
  constructor(scene, arena, w, h) {
    this.scene = scene; this.w = w; this.h = h;
    this.L = LOOK[arena] || DEFAULT;
    // the grade sits just above the floor: below every character (their depth is their y) and effect
    this.grade = scene.add.rectangle(0, 0, w, h + 80, this.L.grade, this.L.ga).setOrigin(0).setDepth(0.5).setBlendMode(Phaser.BlendModes.MULTIPLY);
    vignetteTexture(scene);
    this.vig = scene.add.image(0, 0, 'vignette').setScrollFactor(0).setDepth(6900).setAlpha(this.L.vig);
    this.g = scene.add.graphics().setDepth(5200).setBlendMode(Phaser.BlendModes.ADD);   // motes, and embers from a fallen boss
    this.dustG = scene.add.graphics().setDepth(2.6);
    this.motes = []; this.puffs = []; this.glows = {};
    for (let i = 0; i < this.L.n; i++) this.motes.push(this.mote(true));
  }

  mote(anywhere, x, y, col, rise) {
    const L = this.L, cam = this.scene.cameras.main.worldView;
    const vx0 = L.kind === 'leaf' ? 14 : L.kind === 'ash' ? 8 : 4;
    return {
      x: x ?? (anywhere ? Math.random() * this.w : cam.x + Math.random() * Math.max(cam.width, 200)),
      y: y ?? (anywhere ? Math.random() * this.h : cam.y + Math.random() * Math.max(cam.height, 200)),
      vx: (Math.random() - 0.5) * vx0 + (L.kind === 'leaf' ? 6 : 0),
      vy: rise ? -(30 + Math.random() * 60) : L.kind === 'ember' ? -(6 + Math.random() * 12) : L.kind === 'ash' || L.kind === 'leaf' ? 5 + Math.random() * 8 : (Math.random() - 0.5) * 6,
      r: rise ? 1 + Math.random() * 1.4 : L.kind === 'glint' ? 0.7 : 0.5 + Math.random() * 0.8,
      life: rise ? 1.2 + Math.random() * 1.6 : 4 + Math.random() * 6, age: 0,
      seed: Math.random() * 10, col: col ?? L.mote, rise: !!rise,
    };
  }

  // dust kicked up at someone's feet (a roll, a landing)
  dust(x, y, n = 4, big = false) {
    for (let i = 0; i < n; i++) {
      const a = Math.PI + (Math.random() - 0.5) * Math.PI * 1.2 + (Math.random() < 0.5 ? Math.PI : 0);
      this.puffs.push({ x: x + (Math.random() - 0.5) * 6, y: y + Math.random() * 2, vx: Math.cos(a) * (big ? 40 : 22), vy: Math.sin(a) * 6 - 3,
        r: big ? 3 + Math.random() * 3 : 2 + Math.random() * 2, life: 0.45 + Math.random() * 0.25, max: 0.7 });
    }
  }

  // a fallen boss: embers that rise and drift, in its colour
  embers(x, y, n, col) { for (let i = 0; i < n; i++) this.motes.push(this.mote(false, x + (Math.random() - 0.5) * 50, y - Math.random() * 50, col, true)); }

  update(dt, time, heroes) {
    const cam = this.scene.cameras.main, z = cam.zoom, vw = cam.width / z, vh = cam.height / z;
    this.vig.setPosition(cam.width / 2, cam.height / 2).setDisplaySize(vw * 1.02, vh * 1.02);
    const g = this.g; g.clear();
    const view = cam.worldView, pad = 30;
    this.motes = this.motes.filter(m => {
      m.age += dt;
      const wob = Math.sin(time / 900 + m.seed) * (this.L.kind === 'leaf' ? 10 : 4);
      m.x += (m.vx + wob) * dt; m.y += m.vy * dt;
      if (m.rise) m.vy *= 1 - dt * 0.4;
      // fade in and out over its life; motes that drift off screen are reborn in view
      const f = Math.min(1, m.age * 1.5, (m.life - m.age) * 1.2);
      if (m.age > m.life || m.x < view.x - pad || m.x > view.right + pad || m.y < view.y - pad || m.y > view.bottom + pad) {
        if (m.rise) return false;
        Object.assign(m, this.mote(false)); return true;
      }
      const tw = this.L.kind === 'glint' ? 0.5 + 0.5 * Math.sin(time / 120 + m.seed * 7) : 1;
      g.fillStyle(m.col, (m.rise ? 0.8 : 0.45) * f * tw); g.fillCircle(m.x, m.y, m.r * 0.8);
      if (m.rise) { g.fillStyle(m.col, 0.1 * f); g.fillCircle(m.x, m.y, m.r * 2); }
      return true;
    });
    const d = this.dustG; d.clear();
    this.puffs = this.puffs.filter(p => {
      p.life -= dt; p.x += p.vx * dt; p.y += p.vy * dt; p.vx *= 1 - dt * 4; p.r += dt * 9;
      const u = Math.max(0, p.life / p.max);
      d.fillStyle(0xb8ac9c, 0.32 * u); d.fillCircle(p.x, p.y - p.r * 0.4, p.r);
      return p.life > 0;
    });
    // a soft light under each hero, in their colour: who is who at a glance, and a little warmth
    const seen = new Set();
    for (const h of heroes) {
      seen.add(h.id);
      const gl = this.glows[h.id] ||= this.scene.add.image(0, 0, 'glow').setBlendMode(Phaser.BlendModes.ADD).setDepth(1.2);
      gl.setTint(h.colour).setPosition(h.x, h.y - 2).setDisplaySize(64, 30).setAlpha(h.dead ? 0 : 0.26);
    }
    for (const id of Object.keys(this.glows)) if (!seen.has(+id) && !seen.has(id)) { this.glows[id].destroy(); delete this.glows[id]; }
  }
}
