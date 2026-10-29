// A three.js view for the 3D minigames. three.js is only fetched when one starts. Its canvas
// sits under the stage's 2D canvas, which keeps drawing the HUD, names and touch controls on top.
// The flat 100 x 100 field maps to the ground: field (x, y) is world (x - 50, 0, y - 50).

let THREE = null;

export async function loadThree() {
  if (!THREE) THREE = await import('three');
  return THREE;
}

export class View3D {
  constructor(T, stage) {
    this.T = T;
    this.s = stage;
    this.canvas = document.createElement('canvas');
    this.canvas.className = 'three';
    stage.root.insertBefore(this.canvas, stage.cv);
    this.r = new T.WebGLRenderer({ canvas: this.canvas, antialias: true });
    this.r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.scene = new T.Scene();
    this.scene.background = new T.Color('#140d22');
    this.scene.fog = new T.Fog('#140d22', 160, 320);
    this.cam = new T.PerspectiveCamera(42, 1, 1, 700);
    this.scene.add(new T.HemisphereLight(0xc8b8ff, 0x22152e, 1.3));
    const sun = new T.DirectionalLight(0xffe2b8, 1.6);
    sun.position.set(40, 90, 50);
    this.scene.add(sun);
    this.w = this.h = 0;
  }

  resize() {
    const w = this.s.root.clientWidth, h = this.s.root.clientHeight;
    if (w === this.w && h === this.h) return;
    this.w = w;
    this.h = h;
    this.r.setSize(w, h, false);
    this.canvas.style.width = `${w}px`;
    this.canvas.style.height = `${h}px`;
    this.cam.aspect = w / h;
    // step back on tall screens so the whole field fits across
    const k = Math.max(1, 1.15 / Math.min(1.15, w / h));
    this.cam.position.set(0, 112 * k, 72 * k);
    this.scene.fog.near = 160 * k;
    this.scene.fog.far = 320 * k;
    this.cam.lookAt(0, 0, 6);
    this.cam.updateProjectionMatrix();
  }

  render() {
    this.resize();
    this.r.render(this.scene, this.cam);
  }

  // where a world point lands on the stage, in its logical units
  toStage(x, y, z) {
    const v = new this.T.Vector3(x, y, z).project(this.cam);
    const cx = ((v.x + 1) / 2) * this.w, cy = ((1 - v.y) / 2) * this.h;
    const s = this.s;
    return [(cx * s.dpr - s.ox) / s.scale, (cy * s.dpr - s.oy) / s.scale];
  }

  // a player: a shiny ball in their colour, with eyes
  blob(color, r = 4.2) {
    const T = this.T;
    const g = new T.Group();
    const body = new T.Mesh(new T.SphereGeometry(r, 24, 16), new T.MeshStandardMaterial({ color, roughness: 0.35 }));
    g.add(body);
    const eyeGeo = new T.SphereGeometry(r * 0.16, 10, 8);
    const eyeMat = new T.MeshBasicMaterial({ color: '#1a1020' });
    for (const sx of [-0.32, 0.32]) {
      const e = new T.Mesh(eyeGeo, eyeMat);
      e.position.set(sx * r, r * 0.25, r * 0.88);
      g.add(e);
    }
    this.scene.add(g);
    return g;
  }

  dispose() {
    this.scene.traverse(o => {
      if (o.geometry) o.geometry.dispose();
      if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => m.dispose());
    });
    this.r.dispose();
    this.canvas.remove();
  }
}
