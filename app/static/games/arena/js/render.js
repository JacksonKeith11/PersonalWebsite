// Everything drawn: the map (box geometry with procedural textures), players, pickups, the
// weapon in your hands, and effects. No lights are added or removed after startup (that makes
// three.js recompile shaders); flashes borrow from a fixed pool of point lights.
import * as THREE from 'three';
import { rayWorld } from './physics.js?v=5';

const TEX_METRES = 2;  // one texture repeat covers 2 m

// ------------------------------------------------------------------ textures

function rng(seed) {
  return () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);
}

function canvasTex(size, draw, seed = 7) {
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  draw(g, size, rng(seed));
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 4;
  return t;
}

function speckle(g, s, r, n, alpha) {
  for (let i = 0; i < n; i++) {
    const v = Math.floor(r() * 255);
    g.fillStyle = `rgba(${v},${v},${v},${alpha * r()})`;
    g.fillRect(Math.floor(r() * s), Math.floor(r() * s), 1 + Math.floor(r() * 2), 1 + Math.floor(r() * 2));
  }
}

function shade(hex, f) {
  const c = new THREE.Color(hex).multiplyScalar(f);
  return `#${c.getHexString()}`;
}

const TEXTURES = {
  floor: (g, s, r) => {
    const n = 2, w = s / n;
    for (let i = 0; i < n; i++) for (let k = 0; k < n; k++) {
      g.fillStyle = shade('#4c443d', 0.85 + r() * 0.25);
      g.fillRect(i * w, k * w, w, w);
      g.fillStyle = 'rgba(255,255,255,0.05)';
      g.fillRect(i * w + 3, k * w + 3, w - 6, 3);
    }
    speckle(g, s, r, 3000, 0.18);
    g.strokeStyle = '#211c18';
    g.lineWidth = 4;
    for (let i = 0; i <= n; i++) {
      g.beginPath(); g.moveTo(i * w, 0); g.lineTo(i * w, s); g.stroke();
      g.beginPath(); g.moveTo(0, i * w); g.lineTo(s, i * w); g.stroke();
    }
  },
  wall: (g, s, r) => {
    g.fillStyle = '#2e2119';
    g.fillRect(0, 0, s, s);
    const rows = 8, h = s / rows, bw = s / 4;
    for (let y = 0; y < rows; y++) {
      for (let x = -1; x < 5; x++) {
        const ox = (y % 2) * bw / 2;
        g.fillStyle = shade('#74513a', 0.75 + r() * 0.35);
        g.fillRect(x * bw + ox + 2, y * h + 2, bw - 4, h - 4);
      }
    }
    speckle(g, s, r, 3500, 0.2);
  },
  metal: (g, s, r) => {
    g.fillStyle = '#5b6370';
    g.fillRect(0, 0, s, s);
    speckle(g, s, r, 2000, 0.12);
    g.strokeStyle = 'rgba(255,255,255,0.12)';
    g.lineWidth = 2;
    const step = s / 8;
    for (let i = -8; i < 16; i++) {
      g.beginPath(); g.moveTo(i * step, 0); g.lineTo(i * step + s, s); g.stroke();
      g.beginPath(); g.moveTo(i * step + s, 0); g.lineTo(i * step, s); g.stroke();
    }
    g.strokeStyle = '#2a2f36';
    g.lineWidth = 6;
    g.strokeRect(0, 0, s, s);
    g.fillStyle = '#8b95a3';
    for (const [x, y] of [[10, 10], [s - 10, 10], [10, s - 10], [s - 10, s - 10]]) {
      g.beginPath(); g.arc(x, y, 4, 0, 7); g.fill();
    }
  },
  stone: (g, s, r) => {
    g.fillStyle = '#3d362e';
    g.fillRect(0, 0, s, s);
    const rows = 3, h = s / rows;
    for (let y = 0; y < rows; y++) {
      const off = r() * s / 2;
      for (let x = -1; x < 3; x++) {
        g.fillStyle = shade('#857a68', 0.75 + r() * 0.3);
        g.fillRect(x * s / 2 + off + 3, y * h + 3, s / 2 - 6, h - 6);
      }
    }
    speckle(g, s, r, 4000, 0.22);
  },
  pillar: (g, s, r) => {
    g.fillStyle = '#58504a';
    g.fillRect(0, 0, s, s);
    for (let i = 0; i < 4; i++) {
      g.fillStyle = 'rgba(0,0,0,0.35)';
      g.fillRect(i * s / 4 + s / 8 - 4, 0, 8, s);
      g.fillStyle = 'rgba(255,255,255,0.08)';
      g.fillRect(i * s / 4 + s / 8 + 4, 0, 3, s);
    }
    g.fillStyle = 'rgba(0,0,0,0.4)';
    g.fillRect(0, 0, s, 6);
    speckle(g, s, r, 3000, 0.2);
  },
  crate: (g, s, r) => {
    for (let i = 0; i < 4; i++) {
      g.fillStyle = shade('#8c5c2c', 0.8 + r() * 0.3);
      g.fillRect(0, i * s / 4, s, s / 4);
      g.fillStyle = 'rgba(0,0,0,0.35)';
      g.fillRect(0, i * s / 4, s, 2);
    }
    speckle(g, s, r, 2500, 0.15);
    g.strokeStyle = '#4a2e14';
    g.lineWidth = 14;
    g.strokeRect(7, 7, s - 14, s - 14);
    g.beginPath(); g.moveTo(10, 10); g.lineTo(s - 10, s - 10); g.stroke();
  },
  grate: (g, s, r) => {  // catwalk grating
    g.fillStyle = '#1c2026';
    g.fillRect(0, 0, s, s);
    const n = 16, w = s / n;
    for (let i = 0; i < n; i++) for (let k = 0; k < n; k++) {
      g.fillStyle = shade('#6a737e', 0.8 + r() * 0.3);
      g.fillRect(i * w + 1, k * w + 1, w - 2, 3);
      g.fillRect(i * w + 1, k * w + 1, 3, w - 2);
    }
    g.strokeStyle = '#3a414a';
    g.lineWidth = 6;
    g.strokeRect(0, 0, s, s);
    speckle(g, s, r, 1500, 0.15);
  },
};

function glowTex() {
  return canvasTex(64, (g, s) => {
    const grd = g.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
    grd.addColorStop(0, 'rgba(255,255,255,1)');
    grd.addColorStop(0.3, 'rgba(255,255,255,0.6)');
    grd.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grd;
    g.fillRect(0, 0, s, s);
  });
}

function smokeTex() {
  return canvasTex(64, (g, s, r) => {
    for (let i = 0; i < 14; i++) {
      const x = s / 2 + (r() - 0.5) * s * 0.4, y = s / 2 + (r() - 0.5) * s * 0.4, rad = s * (0.15 + r() * 0.2);
      const grd = g.createRadialGradient(x, y, 0, x, y, rad);
      grd.addColorStop(0, 'rgba(255,255,255,0.35)');
      grd.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = grd;
      g.fillRect(0, 0, s, s);
    }
  }, 3);
}

// ------------------------------------------------------------------ the map

function boxFaces(acc, b) {
  const [x0, y0, z0, x1, y1, z1] = b;
  const faces = [
    [[1, 0, 0], [[x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1]]],
    [[-1, 0, 0], [[x0, y0, z0], [x0, y1, z0], [x0, y1, z1], [x0, y0, z1]]],
    [[0, 1, 0], [[x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1]]],
    [[0, -1, 0], [[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]]],
    [[0, 0, 1], [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]],
    [[0, 0, -1], [[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0]]],
  ];
  for (const [n, q] of faces) {
    if (n[1] === -1 && y0 <= 0.001) continue;  // never seen
    // wind counter-clockwise as seen from outside
    const e1 = q[1].map((v, i) => v - q[0][i]), e2 = q[2].map((v, i) => v - q[0][i]);
    const cx = e1[1] * e2[2] - e1[2] * e2[1], cy = e1[2] * e2[0] - e1[0] * e2[2], cz = e1[0] * e2[1] - e1[1] * e2[0];
    if (cx * n[0] + cy * n[1] + cz * n[2] < 0) q.reverse();
    const uv = p => (n[0] ? [p[2], p[1]] : n[1] ? [p[0], p[2]] : [p[0], p[1]]).map(v => v / TEX_METRES);
    // cheap ambient occlusion: walls darken toward their foot
    const col = p => (n[1] ? 1 : p[1] <= y0 + 0.001 && y1 - y0 > 0.6 ? 0.55 : 1);
    for (const i of [0, 1, 2, 0, 2, 3]) {
      acc.pos.push(...q[i]);
      acc.nrm.push(...n);
      acc.uv.push(...uv(q[i]));
      const c = col(q[i]);
      acc.col.push(c, c, c);
    }
  }
}

function geometryOf(acc) {
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(acc.pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(acc.nrm, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(acc.uv, 2));
  g.setAttribute('color', new THREE.Float32BufferAttribute(acc.col, 3));
  return g;
}

// ------------------------------------------------------------------ models

const PICKUP_LOOK = {
  health: { color: 0xf2f2f2, glow: 0xff4040 },
  mega: { color: 0x4aa0ff, glow: 0x4aa0ff },
  armor: { color: 0xffc23a, glow: 0xffb020 },
  ammo: { color: 0x7d8a3c, glow: 0xd8e060 },
};

function pickupModel(kind) {
  const g = new THREE.Group();
  const look = PICKUP_LOOK[kind];
  const mat = new THREE.MeshStandardMaterial({ color: look.color, emissive: look.glow, emissiveIntensity: 0.35, roughness: 0.4 });
  if (kind === 'health') {
    g.add(new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.5, 0.5), mat));
    const red = new THREE.MeshStandardMaterial({ color: 0xd02020, emissive: 0xff2020, emissiveIntensity: 0.5 });
    // a red cross on every side
    for (const s of [[0.36, 0.12, 0.52], [0.12, 0.36, 0.52], [0.52, 0.36, 0.12], [0.52, 0.12, 0.36]]) {
      g.add(new THREE.Mesh(new THREE.BoxGeometry(...s), red));
    }
  } else if (kind === 'mega') {
    mat.emissiveIntensity = 0.9;
    g.add(new THREE.Mesh(new THREE.IcosahedronGeometry(0.38, 1), mat));
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.55, 0.04, 8, 32), mat);
    ring.rotation.x = Math.PI / 2;
    g.add(ring);
  } else if (kind === 'armor') {
    g.add(new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.55, 0.25), mat));
    for (const s of [-1, 1]) {
      const sh = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.15, 0.3), mat);
      sh.position.set(s * 0.38, 0.22, 0);
      g.add(sh);
    }
  } else {
    g.add(new THREE.Mesh(new THREE.BoxGeometry(0.55, 0.35, 0.35), mat));
    const band = new THREE.Mesh(new THREE.BoxGeometry(0.57, 0.08, 0.37),
      new THREE.MeshStandardMaterial({ color: 0xe0c040, emissive: 0xe0c040, emissiveIntensity: 0.4 }));
    g.add(band);
  }
  return g;
}

function labelSprite(text, color) {
  const c = document.createElement('canvas');
  c.width = 256; c.height = 64;
  const g = c.getContext('2d');
  g.font = '600 34px "Source Sans 3", system-ui, sans-serif';
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.lineWidth = 6;
  g.strokeStyle = 'rgba(0,0,0,0.8)';
  g.strokeText(text, 128, 32);
  g.fillStyle = color;
  g.fillText(text, 128, 32);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: t, transparent: true, depthWrite: false }));
  s.scale.set(1.6, 0.4, 1);
  return s;
}

const DARK = new THREE.MeshStandardMaterial({ color: 0x26282c, roughness: 0.7 });
const glowMat = color => new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 1.3 });

// Each power weapon's colour, for its pickup, its shots and its effects.
export const POWER_COLOR = { rg: 0x40ff90, vx: 0x9a50ff, io: 0x40c8ff, sw: 0xff50d0, yt: 0xff8a20 };

function gunModel(w, scale = 1) {
  const g = new THREE.Group();
  const metal = new THREE.MeshStandardMaterial({ color: 0x8a8f99, roughness: 0.35, metalness: 0.6 });
  const add = (geo, mat, x, y, z, rx = 0) => {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x * scale, y * scale, z * scale);
    m.scale.setScalar(scale);
    m.rotation.x = rx;
    g.add(m);
    return m;
  };
  const tube = (r, len) => new THREE.CylinderGeometry(r, r, len, 12);
  if (w === 0) {  // machine gun
    add(new THREE.BoxGeometry(0.1, 0.12, 0.42), DARK, 0, 0, 0);
    add(tube(0.025, 0.4), metal, 0, 0.02, -0.38, Math.PI / 2);
    add(new THREE.BoxGeometry(0.05, 0.14, 0.08), DARK, 0, -0.11, 0.06);
  } else if (w === 1) {  // shotgun
    const wood = new THREE.MeshStandardMaterial({ color: 0x6b4423, roughness: 0.8 });
    add(new THREE.BoxGeometry(0.1, 0.1, 0.3), wood, 0, -0.02, 0.12);
    add(tube(0.03, 0.55), metal, -0.032, 0.02, -0.25, Math.PI / 2);
    add(tube(0.03, 0.55), metal, 0.032, 0.02, -0.25, Math.PI / 2);
  } else if (w === 2) {  // rocket launcher
    const olive = new THREE.MeshStandardMaterial({ color: 0x5c6a3a, roughness: 0.6 });
    add(tube(0.075, 0.75), olive, 0, 0, -0.15, Math.PI / 2);
    add(tube(0.09, 0.08), DARK, 0, 0, -0.52, Math.PI / 2);
    add(new THREE.BoxGeometry(0.05, 0.14, 0.08), DARK, 0, -0.12, 0.05);
  } else if (w === 3) {  // railgun
    const green = new THREE.MeshStandardMaterial({ color: 0x2d5a3a, roughness: 0.4, metalness: 0.4 });
    const coil = glowMat(0x40ff90);
    add(new THREE.BoxGeometry(0.1, 0.12, 0.85), green, 0, 0, -0.2);
    for (let i = 0; i < 4; i++) add(new THREE.TorusGeometry(0.07, 0.015, 6, 16), coil, 0, 0, -0.1 - i * 0.14);
  } else if (w === 4) {  // vortex
    const purple = new THREE.MeshStandardMaterial({ color: 0x2a1840, roughness: 0.4, metalness: 0.5 });
    add(new THREE.BoxGeometry(0.14, 0.14, 0.5), purple, 0, 0, -0.05);
    add(new THREE.SphereGeometry(0.1, 16, 12), glowMat(0x9a50ff), 0, 0, -0.38);
    add(new THREE.TorusGeometry(0.15, 0.02, 8, 24), glowMat(0xc080ff), 0, 0, -0.38);
  } else if (w === 5) {  // ion orb
    const teal = new THREE.MeshStandardMaterial({ color: 0x1e4a5a, roughness: 0.5, metalness: 0.4 });
    add(tube(0.09, 0.45), teal, 0, 0, 0, Math.PI / 2);
    add(new THREE.SphereGeometry(0.12, 16, 12), glowMat(0x40c8ff), 0, 0, -0.33);
    for (const a of [0, 1, 2]) add(new THREE.BoxGeometry(0.02, 0.02, 0.3), DARK, Math.cos(a * 2.1) * 0.13, Math.sin(a * 2.1) * 0.13, -0.3);
  } else if (w === 6) {  // swapper
    add(new THREE.BoxGeometry(0.08, 0.12, 0.5), new THREE.MeshStandardMaterial({ color: 0xff50d0, roughness: 0.4 }), -0.04, 0, -0.1);
    add(new THREE.BoxGeometry(0.08, 0.12, 0.5), new THREE.MeshStandardMaterial({ color: 0x40e0ff, roughness: 0.4 }), 0.04, 0, -0.15);
    add(new THREE.OctahedronGeometry(0.07), glowMat(0xffffff), 0, 0.02, -0.45);
  } else if (w === 7) {  // yeet cannon
    const orange = new THREE.MeshStandardMaterial({ color: 0xe0701a, roughness: 0.5, metalness: 0.3 });
    add(new THREE.CylinderGeometry(0.2, 0.07, 0.55, 16, 1, true), orange, 0, 0, -0.3, -Math.PI / 2).material.side = THREE.DoubleSide;
    add(new THREE.BoxGeometry(0.1, 0.1, 0.25), DARK, 0, 0, 0.08);
    add(new THREE.BoxGeometry(0.05, 0.14, 0.08), DARK, 0, -0.12, 0.05);
  } else {  // knife
    const steel = new THREE.MeshStandardMaterial({ color: 0xd8dde4, roughness: 0.2, metalness: 0.9 });
    add(new THREE.BoxGeometry(0.035, 0.05, 0.16), DARK, 0, 0, 0.05);
    add(new THREE.BoxGeometry(0.09, 0.02, 0.02), DARK, 0, 0, -0.04);
    add(new THREE.BoxGeometry(0.012, 0.05, 0.3), steel, 0, 0.005, -0.2);
  }
  return g;
}

// `look`: role ('zombie' or 'jugg', from the round's mode) and bigHeads (a mutator).
function playerModel(color, name, look = {}) {
  const root = new THREE.Group();
  const zombie = look.role === 'zombie', jugg = look.role === 'jugg';
  const body = new THREE.MeshStandardMaterial({ color: zombie ? 0x5f8f3a : color, roughness: 0.55 });
  const box = (w, h, d, mat) => new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  const legs = [];
  for (const s of [-1, 1]) {
    const hip = new THREE.Group();
    hip.position.set(s * 0.14, 0.9, 0);
    const leg = box(0.22, 0.88, 0.26, DARK);
    leg.position.y = -0.44;
    hip.add(leg);
    root.add(hip);
    legs.push(hip);
  }
  const torso = box(0.62, 0.62, 0.36, body);
  torso.position.y = 1.22;
  root.add(torso);
  const aim = new THREE.Group();  // head and gun pitch together
  aim.position.y = 1.4;
  const head = box(0.34, 0.34, 0.34, body);
  const big = look.bigHeads ? 2.3 : 1;
  head.scale.setScalar(big);
  head.position.y = 0.24 + 0.17 * (big - 1);
  aim.add(head);
  const eyes = zombie ? 0xff3020 : jugg ? 0xffa020 : 0xffffff;
  const visor = box(0.28, 0.09, 0.03, new THREE.MeshStandardMaterial({ color: 0x111111, emissive: eyes, emissiveIntensity: zombie || jugg ? 1.4 : 0.6 }));
  visor.position.set(0, 0.03, -0.18);
  head.add(visor);
  const gunHolder = new THREE.Group();
  gunHolder.position.set(0.3, -0.12, -0.25);
  aim.add(gunHolder);
  root.add(aim);
  if (jugg) {  // the Juggernaut is bigger (its hitbox isn't) and wears a glowing ring
    root.scale.setScalar(1.3);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.32, 0.04, 8, 24), glowMat(0xffa020));
    ring.rotation.x = Math.PI / 2;
    ring.position.y = 2.05;
    root.add(ring);
  }
  const label = labelSprite(name, color);
  label.position.y = 2.25 + (big - 1) * 0.4;
  root.add(label);
  return { root, legs, aim, gunHolder, gun: -1, label, name, color, look: JSON.stringify(look), phase: 0, last: null };
}

// ------------------------------------------------------------------ the view

export class View {
  constructor(container) {
    const r = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    r.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
    r.toneMapping = THREE.ACESFilmicToneMapping;
    r.toneMappingExposure = 1.1;
    r.autoClear = false;
    container.appendChild(r.domElement);
    this.renderer = r;

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(0x5a3f36, 45, 160);
    this.scene = scene;
    this.camera = new THREE.PerspectiveCamera(75, 1, 0.05, 600);
    this.camera.rotation.order = 'YXZ';

    // sky: a gradient dome
    const sky = this.sky = new THREE.Mesh(new THREE.SphereGeometry(400, 32, 16), new THREE.ShaderMaterial({
      side: THREE.BackSide, depthWrite: false, fog: false,
      uniforms: { top: { value: new THREE.Color(0x1e1830) }, mid: { value: new THREE.Color(0x7a4a3a) }, bot: { value: new THREE.Color(0xd08a50) } },
      vertexShader: 'varying vec3 v; void main(){ v = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
      fragmentShader: 'uniform vec3 top; uniform vec3 mid; uniform vec3 bot; varying vec3 v; void main(){ float h = v.y; vec3 c = h > 0.15 ? mix(mid, top, smoothstep(0.15, 0.7, h)) : mix(bot, mid, smoothstep(-0.05, 0.15, h)); gl_FragColor = vec4(c, 1.0); }',
    }));
    scene.add(sky);

    this.hemi = new THREE.HemisphereLight(0xe8d2b8, 0x3a2a20, 1.6);
    scene.add(this.hemi);
    const sun = this.sun = new THREE.DirectionalLight(0xffd8a8, 2.0);
    sun.position.set(30, 60, 20);
    scene.add(sun);
    const fill = new THREE.DirectionalLight(0x8090ff, 0.5);
    fill.position.set(-30, 20, -40);
    scene.add(fill);

    this.lights = [];
    for (let i = 0; i < 6; i++) {
      const l = new THREE.PointLight(0xffa040, 0, 14, 1.6);
      scene.add(l);
      this.lights.push({ l, until: 0, follow: null, fade: 0.3, peak: 0 });
    }

    // the weapon in your hands is drawn in its own pass, so it never clips into walls
    this.vscene = new THREE.Scene();
    this.vcam = new THREE.PerspectiveCamera(60, 1, 0.01, 10);
    this.vscene.add(new THREE.HemisphereLight(0xe8d2b8, 0x3a2a20, 1.8));
    const vsun = new THREE.DirectionalLight(0xffffff, 1.5);
    vsun.position.set(1, 2, 1);
    this.vscene.add(vsun);
    this.vgun = new THREE.Group();
    this.vgun.scale.setScalar(0.6);
    this.vscene.add(this.vgun);
    this.vguns = [];  // built the first time each weapon is held
    this.flash = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex(), color: 0xffc070, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true }));
    this.flash.visible = false;
    this.vscene.add(this.flash);
    this.vweapon = -1;
    this.kick = 0;
    this.switchT = 0;
    this.flashUntil = 0;

    this.glow = glowTex();
    this.smoke = smokeTex();
    this.fx = [];  // effects with an update(dt) returning false when done
    this.players = new Map();
    this.rockets = new Map();
    this.pickups = [];
    this.time = 0;
    this.resize();
    window.addEventListener('resize', () => this.resize());
  }

  resize() {
    const w = window.innerWidth, h = window.innerHeight;
    this.renderer.setSize(w, h);
    this.camera.aspect = this.vcam.aspect = w / h;
    this.setFov(this.hfov || 100);
  }

  setFov(hfov) {
    this.hfov = hfov;
    const v = 2 * Math.atan(Math.tan(hfov * Math.PI / 360) / this.camera.aspect) * 180 / Math.PI;
    this.camera.fov = v;
    this.camera.updateProjectionMatrix();
    this.vcam.fov = Math.min(v, 70);
    this.vcam.updateProjectionMatrix();
  }

  // Each map has its own sky, fog and sunlight.
  setTheme(t) {
    if (!t || !t.sky) return;
    const u = this.sky.material.uniforms;
    u.top.value.set(t.sky[0]);
    u.mid.value.set(t.sky[1]);
    u.bot.value.set(t.sky[2]);
    this.scene.fog.color.set(t.fog);
    this.sun.color.set(t.sun);
    this.hemi.groundColor.set(t.ground);
  }

  buildMap(map) {
    if (this.mapGroup) {
      this.scene.remove(this.mapGroup);
      this.mapGroup.traverse(o => {  // the last map's meshes and canvas textures
        if (o.geometry) o.geometry.dispose();
        if (o.material) { if (o.material.map) o.material.map.dispose(); o.material.dispose(); }
      });
    }
    this.setTheme(map.theme);
    const group = new THREE.Group();
    const accs = {};
    for (const b of map.boxes) {
      const m = b[6];
      accs[m] = accs[m] || { pos: [], nrm: [], uv: [], col: [] };
      boxFaces(accs[m], b);
    }
    for (const [m, acc] of Object.entries(accs)) {
      const tex = canvasTex(256, TEXTURES[m] || TEXTURES.stone, m.length * 31);
      const mat = new THREE.MeshStandardMaterial({ map: tex, vertexColors: true, roughness: 0.85, metalness: m === 'metal' ? 0.3 : 0 });
      group.add(new THREE.Mesh(geometryOf(acc), mat));
    }
    // glowing trim along the top edges of the platforms
    const trim = new THREE.MeshStandardMaterial({ color: 0xff8a30, emissive: 0xff7a20, emissiveIntensity: 1.4 });
    for (const b of map.boxes) {
      if (!['metal', 'stone'].includes(b[6]) || b[4] < 2.5 || b[3] - b[0] < 3) continue;
      const [x0, , z0, x1, y1, z1] = b;
      const y = y1 - 0.12;
      for (const [cx, cz, sx, sz] of [[(x0 + x1) / 2, z0 - 0.01, x1 - x0, 0.03], [(x0 + x1) / 2, z1 + 0.01, x1 - x0, 0.03],
        [x0 - 0.01, (z0 + z1) / 2, 0.03, z1 - z0], [x1 + 0.01, (z0 + z1) / 2, 0.03, z1 - z0]]) {
        const s = new THREE.Mesh(new THREE.BoxGeometry(sx, 0.08, sz), trim);
        s.position.set(cx, y, cz);
        group.add(s);
      }
    }
    // jump pads
    this.pads = [];
    for (const [x, y, z, r] of map.pads) {
      const disc = new THREE.Mesh(new THREE.CylinderGeometry(r, r * 1.1, 0.06, 32),
        new THREE.MeshStandardMaterial({ color: 0x103040, emissive: 0x30d0ff, emissiveIntensity: 1.2 }));
      disc.position.set(x, y + 0.03, z);
      group.add(disc);
      const beam = new THREE.Mesh(new THREE.CylinderGeometry(r * 0.5, r, 3, 24, 1, true),
        new THREE.MeshBasicMaterial({ color: 0x40d8ff, transparent: true, opacity: 0.2, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, depthWrite: false }));
      beam.position.set(x, y + 1.5, z);
      group.add(beam);
      this.pads.push(beam);
    }
    // pickups
    this.powerSpots = map.power;
    this.powerId = null;
    this.pickups = map.pickups.map(([kind, x, y, z]) => {
      const base = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.6, 0.05, 24),
        new THREE.MeshStandardMaterial({ color: 0x222222, emissive: PICKUP_LOOK[kind].glow, emissiveIntensity: 0.4 }));
      base.position.set(x, y + 0.025, z);
      group.add(base);
      const m = pickupModel(kind);
      m.position.set(x, y + 0.7, z);
      group.add(m);
      return { m, kind, y: y + 0.7, phase: x + z };
    });
    this.mapGroup = group;
    this.scene.add(group);
  }

  setPickups(flags) {
    this.pickups.forEach((p, i) => { p.m.visible = flags[i] === '1'; });
  }

  // ---------------------------------------------------------------- players

  ensurePlayer(id, color, name, look = {}) {
    let p = this.players.get(id);
    if (p && p.name === name && p.color === color && p.look === JSON.stringify(look)) return p;
    if (p) this.scene.remove(p.root);
    p = playerModel(color, name, look);
    this.players.set(id, p);
    this.scene.add(p.root);
    return p;
  }

  removePlayer(id) {
    const p = this.players.get(id);
    if (p) { this.scene.remove(p.root); this.players.delete(id); }
  }

  updatePlayer(id, s, dt) {
    const p = this.players.get(id);
    if (!p) return;
    p.root.visible = s.alive;
    if (!s.alive) { p.last = null; return; }
    p.root.position.set(s.x, s.y, s.z);
    p.root.rotation.y = s.yaw;
    p.aim.rotation.x = s.pitch;
    if (p.gun !== s.w) {
      p.gunHolder.clear();
      p.gunHolder.add(gunModel(s.w, 0.9));
      p.gun = s.w;
    }
    const speed = p.last && dt > 0 ? Math.hypot(s.x - p.last[0], s.z - p.last[1]) / dt : 0;
    p.last = [s.x, s.z];
    p.speed = (p.speed || 0) * 0.8 + Math.min(speed, 15) * 0.2;
    p.phase += p.speed * dt * 1.3;
    const swing = Math.sin(p.phase) * 0.7 * Math.min(p.speed / 8, 1);
    p.legs[0].rotation.x = swing;
    p.legs[1].rotation.x = -swing;
  }

  // ---------------------------------------------------------------- effects

  light(pos, color, peak, fade, follow = null) {
    const slot = this.lights.reduce((a, b) => (b.until < a.until ? b : a));
    slot.l.color.set(color);
    slot.l.position.set(...pos);
    slot.peak = peak;
    slot.fade = fade;
    slot.start = this.time;
    slot.until = this.time + fade;
    slot.follow = follow;
    return slot;
  }

  sprite(pos, { color = 0xffffff, size = 1, grow = 0, life = 0.5, vel = [0, 0, 0], grav = 0, opacity = 1, tex = this.glow, additive = true }) {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({
      map: tex, color, transparent: true, depthWrite: false, opacity,
      blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    }));
    s.position.set(...pos);
    s.scale.setScalar(size);
    this.scene.add(s);
    let t = 0;
    const v = vel.slice();
    this.fx.push(dt => {
      t += dt;
      if (t >= life) { this.scene.remove(s); s.material.dispose(); return false; }
      v[1] -= grav * dt;
      s.position.x += v[0] * dt; s.position.y += v[1] * dt; s.position.z += v[2] * dt;
      s.scale.setScalar(size + grow * t);
      s.material.opacity = opacity * (1 - t / life);
      return true;
    });
  }

  beam(o, e, { color, radius, life, opacity = 1 }) {
    const dir = new THREE.Vector3(e[0] - o[0], e[1] - o[1], e[2] - o[2]);
    const len = dir.length();
    if (len < 0.01) return;
    const m = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, 1, 8, 1, true),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    m.position.set((o[0] + e[0]) / 2, (o[1] + e[1]) / 2, (o[2] + e[2]) / 2);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
    m.scale.set(1, len, 1);
    this.scene.add(m);
    let t = 0;
    this.fx.push(dt => {
      t += dt;
      if (t >= life) { this.scene.remove(m); m.geometry.dispose(); m.material.dispose(); return false; }
      m.material.opacity = opacity * (1 - t / life);
      return true;
    });
  }

  tracer(o, e, w) {
    // start the line a little ahead of the muzzle so it doesn't fill the screen
    const d = [e[0] - o[0], e[1] - o[1], e[2] - o[2]];
    const n = Math.hypot(...d) || 1;
    const s = [o[0] + d[0] / n * 0.8, o[1] + d[1] / n * 0.8 - 0.1, o[2] + d[2] / n * 0.8];
    this.beam(s, e, { color: 0xffd080, radius: w === 1 ? 0.012 : 0.018, life: 0.07, opacity: 0.8 });
    this.impact(e);
  }

  impact(p) {
    for (let i = 0; i < 4; i++) {
      this.sprite(p, { color: 0xffc080, size: 0.12, life: 0.25, vel: [(Math.random() - 0.5) * 6, Math.random() * 4, (Math.random() - 0.5) * 6], grav: 15 });
    }
    this.sprite(p, { color: 0x887766, size: 0.3, grow: 0.8, life: 0.5, tex: this.smoke, additive: false, opacity: 0.6, vel: [0, 0.5, 0] });
  }

  rail(o, e, color) {
    const len0 = Math.hypot(e[0] - o[0], e[1] - o[1], e[2] - o[2]) || 1;
    const k = Math.min(0.4, len0 / 2) / len0;
    const s = [o[0] + (e[0] - o[0]) * k, o[1] + (e[1] - o[1]) * k, o[2] + (e[2] - o[2]) * k];
    this.beam(s, e, { color: 0xffffff, radius: 0.02, life: 0.5 });
    this.beam(s, e, { color, radius: 0.07, life: 0.9, opacity: 0.6 });
    const len = Math.hypot(e[0] - s[0], e[1] - s[1], e[2] - s[2]);
    const n = Math.min(80, Math.floor(len / 0.6));
    for (let i = 1; i < n; i++) {
      const f = i / n, a = i * 0.9;
      const p = [s[0] + (e[0] - s[0]) * f + Math.cos(a) * 0.12, s[1] + (e[1] - s[1]) * f + Math.sin(a) * 0.12, s[2] + (e[2] - s[2]) * f];
      this.sprite(p, { color, size: 0.18, life: 0.9, vel: [0, 0.3, 0] });
    }
    this.impact(e);
    this.light(e, color, 25, 0.25);
  }

  explosion(p, color = 0xffa040, scale = 1) {
    this.sprite(p, { color, size: 1, grow: 14 * scale, life: 0.35 });
    this.sprite(p, { color: 0xffe0a0, size: 0.5, grow: 6 * scale, life: 0.18 });
    for (let i = 0; i < 16; i++) {
      const v = [(Math.random() - 0.5) * 14 * scale, Math.random() * 10 * scale, (Math.random() - 0.5) * 14 * scale];
      this.sprite(p, { color, size: 0.18, life: 0.5 + Math.random() * 0.3, vel: v, grav: 18 });
    }
    for (let i = 0; i < 8; i++) {
      const v = [(Math.random() - 0.5) * 2, 1 + Math.random() * 1.5, (Math.random() - 0.5) * 2];
      this.sprite([p[0] + v[0] * 0.3, p[1] + 0.2, p[2] + v[2] * 0.3], { color: 0x55504a, size: 1, grow: 2.5, life: 1.4, vel: v, tex: this.smoke, additive: false, opacity: 0.7 });
    }
    this.light(p, color, 120 * scale, 0.45);
  }

  // ---------------------------------------------------------------- power weapon effects

  swapBeam(o, e) {
    this.beam(o, e, { color: POWER_COLOR.sw, radius: 0.04, life: 0.45 });
    this.beam(o, e, { color: 0x40e0ff, radius: 0.1, life: 0.3, opacity: 0.4 });
    this.impact(e);
  }

  swapped(a, b) {
    this.teleport(a, POWER_COLOR.sw);
    this.teleport(b, 0x40e0ff);
    this.light(a, POWER_COLOR.sw, 30, 0.4);
  }

  yeet(o, e) {
    this.beam(o, e, { color: POWER_COLOR.yt, radius: 0.28, life: 0.22, opacity: 0.35 });
    this.beam(o, e, { color: 0xffe0b0, radius: 0.06, life: 0.15 });
    this.sprite(e, { color: POWER_COLOR.yt, size: 0.5, grow: 9, life: 0.3 });
    this.impact(e);
  }

  // Lightning from an ion orb to a player: a jagged line that flickers out.
  zap(a, b) {
    const n = 7;
    let prev = a;
    for (let i = 1; i <= n; i++) {
      const f = i / n, j = i === n ? 0 : 0.35;
      const p = [a[0] + (b[0] - a[0]) * f + (Math.random() - 0.5) * j, a[1] + (b[1] - a[1]) * f + (Math.random() - 0.5) * j,
        a[2] + (b[2] - a[2]) * f + (Math.random() - 0.5) * j];
      this.beam(prev, p, { color: 0xb0f0ff, radius: 0.025, life: 0.14 });
      this.beam(prev, p, { color: POWER_COLOR.io, radius: 0.08, life: 0.18, opacity: 0.5 });
      prev = p;
    }
    this.sprite(b, { color: POWER_COLOR.io, size: 0.6, grow: 2, life: 0.2 });
  }

  // A black hole: a dark core with a ring, and sparks spiralling in, until vortexEnd.
  vortex(key, p, secs) {
    const g = new THREE.Group();
    g.position.set(...p);
    g.add(new THREE.Mesh(new THREE.SphereGeometry(0.55, 24, 16), new THREE.MeshBasicMaterial({ color: 0x000000 })));
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.glow, color: POWER_COLOR.vx, blending: THREE.AdditiveBlending, depthWrite: false }));
    halo.scale.setScalar(3.5);
    g.add(halo);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(1.1, 0.05, 8, 48), glowMat(0xc080ff));
    g.add(ring);
    this.scene.add(g);
    const light = this.light(p, POWER_COLOR.vx, 40, secs + 1, g);
    let t = 0, sparks = 0;
    const v = { g, light, done: false };
    this.vortices = this.vortices || new Map();
    this.vortices.set(key, v);
    this.fx.push(dt => {
      t += dt;
      if (v.done || t > secs + 2) {
        this.scene.remove(g);
        if (light.follow === g) { light.follow = null; light.until = 0; }
        return false;
      }
      ring.rotation.x = t * 3; ring.rotation.y = t * 2;
      halo.scale.setScalar(3.5 + Math.sin(t * 20) * 0.3);
      for (sparks += dt * 90; sparks >= 1; sparks--) {  // 90 a second, whatever the frame rate
        const a = Math.random() * Math.PI * 2, e = (Math.random() - 0.5) * 2, r = 5 + Math.random() * 3;
        const from = [p[0] + Math.cos(a) * r, p[1] + e * 2, p[2] + Math.sin(a) * r];
        const life = 0.6;
        // aim a little to the side, so the sparks swirl
        const vel = [(p[0] - from[0]) / life - Math.sin(a) * 4, (p[1] - from[1]) / life, (p[2] - from[2]) / life + Math.cos(a) * 4];
        this.sprite(from, { color: 0xc080ff, size: 0.2, life, vel });
      }
      return true;
    });
  }

  vortexEnd(key, p) {
    const v = this.vortices && this.vortices.get(key);
    if (v) { v.done = true; this.vortices.delete(key); }
    this.explosion(p, POWER_COLOR.vx, 1.2);
  }

  // The power weapon waiting on the map, or none: [weapon, spot] or null.
  setPower(pw, keyOf) {
    const id = pw ? pw.join() : '';
    if (id === this.powerId) return;
    this.powerId = id;
    if (this.powerGroup) {
      this.scene.remove(this.powerGroup);
      if (this.powerLight.follow === this.powerGroup) { this.powerLight.follow = null; this.powerLight.until = 0; }
      this.powerGroup = this.powerGun = null;
    }
    if (!pw || !this.powerSpots) return;
    const [w, spot] = pw;
    const [x, y, z] = this.powerSpots[spot];
    const color = POWER_COLOR[keyOf(w)] || 0xffffff;
    const g = new THREE.Group();
    g.position.set(x, y, z);
    const gun = gunModel(w, 1.8);
    gun.position.y = 1;
    g.add(gun);
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.glow, color, blending: THREE.AdditiveBlending, depthWrite: false, opacity: 0.6 }));
    glow.scale.setScalar(2.2);
    glow.position.y = 1;
    g.add(glow);
    const column = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.9, 8, 24, 1, true),
      new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.18, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, depthWrite: false }));
    column.position.y = 4;
    g.add(column);
    const base = new THREE.Mesh(new THREE.TorusGeometry(0.9, 0.06, 8, 32), glowMat(color));
    base.rotation.x = Math.PI / 2;
    base.position.y = 0.05;
    g.add(base);
    this.scene.add(g);
    this.powerGroup = g;
    this.powerGun = gun;
    this.powerLight = this.light([x, y + 1.5, z], color, 30, 1e6, g);
  }

  gibs(p, color) {
    const mats = [new THREE.MeshStandardMaterial({ color }), new THREE.MeshStandardMaterial({ color: 0x8a1010 })];
    for (let i = 0; i < 10; i++) {
      const m = new THREE.Mesh(new THREE.BoxGeometry(0.18, 0.18, 0.18), mats[i % 2]);
      m.position.set(p[0], p[1] + 1, p[2]);
      this.scene.add(m);
      const v = [(Math.random() - 0.5) * 9, 4 + Math.random() * 7, (Math.random() - 0.5) * 9];
      const spin = [Math.random() * 10, Math.random() * 10];
      const floor = p[1] + 1 - rayWorld([p[0], p[1] + 1, p[2]], [0, -1, 0], 20);
      let t = 0;
      this.fx.push(dt => {
        t += dt;
        if (t > 3) { this.scene.remove(m); m.geometry.dispose(); return false; }
        v[1] -= 22 * dt;
        m.position.x += v[0] * dt; m.position.y += v[1] * dt; m.position.z += v[2] * dt;
        if (m.position.y < floor + 0.09) { m.position.y = floor + 0.09; v[1] *= -0.35; v[0] *= 0.6; v[2] *= 0.6; spin[0] *= 0.6; }
        m.rotation.x += spin[0] * dt; m.rotation.y += spin[1] * dt;
        if (t > 2.5) m.scale.setScalar((3 - t) * 2);
        return true;
      });
    }
    this.sprite([p[0], p[1] + 1, p[2]], { color: 0x700808, size: 1, grow: 3, life: 0.6, tex: this.smoke, additive: false, opacity: 0.8 });
  }

  teleport(p, color) {
    for (let i = 0; i < 14; i++) {
      const a = i / 14 * Math.PI * 2;
      this.sprite([p[0] + Math.cos(a) * 0.6, p[1] + 0.2, p[2] + Math.sin(a) * 0.6], { color, size: 0.25, life: 0.8, vel: [0, 2.5 + Math.random() * 2, 0] });
    }
  }

  // Rockets fly on their own from where and when they were fired; `t0` is in the same clock as `now` in frame().
  // `kind` is the weapon's key: rl draws a rocket, vx and io glowing orbs.
  addRocket(key, p, v, t0, kind = 'rl') {
    const g = new THREE.Group();
    let lightColor = 0xff8030;
    if (kind === 'rl') {
      const body = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.45, 8), DARK);
      body.rotation.x = Math.PI / 2;
      g.add(body);
      const flame = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.glow, color: 0xffa040, blending: THREE.AdditiveBlending, depthWrite: false }));
      flame.scale.setScalar(0.6);
      flame.position.z = 0.3;
      g.add(flame);
    } else {
      lightColor = POWER_COLOR[kind];
      const size = kind === 'io' ? 0.45 : 0.25;
      g.add(new THREE.Mesh(new THREE.SphereGeometry(size, 16, 12), glowMat(lightColor)));
      const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: this.glow, color: lightColor, blending: THREE.AdditiveBlending, depthWrite: false }));
      halo.scale.setScalar(size * 6);
      g.add(halo);
    }
    g.position.set(...p);
    g.lookAt(p[0] - v[0], p[1] - v[1], p[2] - v[2]);
    this.scene.add(g);
    const r = { g, p, v, t0, puff: 0, kind };
    r.light = this.light(p, lightColor, kind === 'io' ? 40 : 18, 20, g);
    this.rockets.set(key, r);
  }

  moveRocket(key, now) {
    const r = this.rockets.get(key);
    if (!r) return null;
    const t = Math.max(0, now - r.t0);
    const pos = [r.p[0] + r.v[0] * t, r.p[1] + r.v[1] * t, r.p[2] + r.v[2] * t];
    r.g.position.set(...pos);
    return pos;
  }

  removeRocket(key) {
    const r = this.rockets.get(key);
    if (!r) return;
    this.scene.remove(r.g);
    if (r.light.follow === r.g) { r.light.until = 0; r.light.follow = null; }
    this.rockets.delete(key);
  }

  // ---------------------------------------------------------------- your weapon

  setViewWeapon(w) {
    if (w === this.vweapon) return;
    if (!this.vguns[w]) {
      this.vguns[w] = gunModel(w, 1);
      this.vgun.add(this.vguns[w]);
    }
    this.vguns.forEach((g, i) => { if (g) g.visible = i === w; });
    this.vweapon = w;
    this.switchT = 0.25;
  }

  shoot(w, key) {
    if (key === 'kn') { this.swing = 0.3; return; }
    this.kick = w === 0 ? 0.035 : w >= 3 ? 0.14 : 0.1;
    this.flashUntil = this.time + (w >= 3 ? 0.08 : 0.05);
    this.flash.material.color.set(POWER_COLOR[key] || 0xffc070);
  }

  frame(dt, cam, { bob = 0, speed = 0, showGun = true }) {
    this.time += dt;
    this.camera.position.set(cam.x, cam.y, cam.z);
    this.camera.rotation.set(cam.pitch, cam.yaw, cam.roll || 0);

    for (const p of this.pickups) {
      p.m.rotation.y = this.time * 1.5 + p.phase;
      p.m.position.y = p.y + Math.sin(this.time * 2 + p.phase) * 0.12;
    }
    if (this.powerGun) {
      this.powerGun.rotation.y = this.time * 1.2;
      this.powerGun.position.y = 1 + Math.sin(this.time * 2) * 0.15;
    }
    for (const b of this.pads || []) b.material.opacity = 0.14 + Math.sin(this.time * 4) * 0.06;
    for (const s of this.lights) {
      if (s.follow) {
        s.l.position.copy(s.follow.position);
        s.l.intensity = s.peak;
      } else {
        const left = s.until - this.time;
        s.l.intensity = left > 0 ? s.peak * left / s.fade : 0;
      }
    }
    // Effects can start effects (the vortex's sparks); those land in the fresh list, not the one
    // being filtered, or they'd never be updated or removed.
    const running = this.fx;
    this.fx = [];
    this.fx = running.filter(f => f(dt)).concat(this.fx);
    for (const r of this.rockets.values()) {
      r.puff -= dt;
      if (r.puff <= 0 && r.kind === 'rl') {
        r.puff = 0.025;
        this.sprite(r.g.position.toArray(), { color: 0x8a8580, size: 0.25, grow: 1.4, life: 0.8, tex: this.smoke, additive: false, opacity: 0.5, vel: [0, 0.4, 0] });
      } else if (r.puff <= 0) {
        r.puff = 0.04;
        const jit = () => (Math.random() - 0.5) * 0.4;
        this.sprite(r.g.position.toArray().map(c => c + jit()), { color: POWER_COLOR[r.kind], size: 0.25, life: 0.5, vel: [jit(), jit(), jit()] });
      }
    }

    // weapon sway, bob, recoil and the raise after switching
    this.kick = Math.max(0, this.kick - dt * 0.6);
    this.switchT = Math.max(0, this.switchT - dt);
    const sway = Math.min(speed / 10, 1);
    this.vgun.position.set(0.2 + Math.cos(bob) * 0.012 * sway, -0.2 - Math.abs(Math.sin(bob)) * 0.015 * sway - this.switchT * 0.8, -0.45 + this.kick);
    this.vgun.rotation.x = this.kick * 1.2;
    this.swing = Math.max(0, (this.swing || 0) - dt);
    const slash = Math.sin(Math.min(1, (0.3 - this.swing) / 0.3) * Math.PI) * (this.swing > 0 ? 1 : 0);
    this.vgun.rotation.y = slash * 0.9;
    this.vgun.rotation.z = slash * 0.6;
    this.vgun.position.x -= slash * 0.12;
    this.vgun.visible = showGun;
    this.flash.visible = showGun && this.time < this.flashUntil;
    if (this.flash.visible) {
      this.flash.position.set(0.2, -0.18, -0.95 + this.kick);
      this.flash.scale.setScalar(0.3 + Math.random() * 0.12);
    }

    const r = this.renderer;
    r.clear();
    r.render(this.scene, this.camera);
    r.clearDepth();
    r.render(this.vscene, this.vcam);
  }
}
