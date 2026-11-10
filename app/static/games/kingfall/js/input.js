// Every input device as the same set of actions, so a hero doesn't care whether it's driven by a
// keyboard and mouse or a controller. Devices: 'kb' (keyboard + mouse) and 'pad0'..'pad3'
// (Gamepad API, standard mapping). Couch co-op gives each device its own hero.
//
//   move    {x, y}            left stick / WASD
//   aim     {x, y} or null    right stick (null when centred); the mouse gives `mouse` instead
//   buttons light heavy special skill1 skill2 dodge block heal interact lock start back, plus up/down/left/right
//           for menus. `held(b)` and `pressed(b)` (this frame only).

const KEYS = {
  dodge: ['Space'], block: ['ShiftLeft', 'ShiftRight'], special: ['KeyQ'], heal: ['KeyR'], interact: ['KeyE', 'KeyF'],
  lock: ['Tab'], start: ['Enter'], back: ['Escape'], skill1: ['KeyZ', 'Digit1'], skill2: ['KeyX', 'Digit2'],
  up: ['ArrowUp', 'KeyW'], down: ['ArrowDown', 'KeyS'], left: ['ArrowLeft', 'KeyA'], right: ['ArrowRight', 'KeyD'],
};
// standard gamepad buttons
// (skills: LT and A. A also revives: beside a fallen ally it does only that. The D-pad is a second
// way to skill 2; otherwise it only steers menus.)
const PAD = { light: [5], heavy: [7], special: [3], dodge: [1], block: [4], heal: [2], interact: [0], lock: [11],
  skill1: [6], skill2: [0, 12, 13, 14, 15],
  start: [9], back: [1, 8], up: [12], down: [13], left: [14], right: [15], confirm: [0] };
const DEAD = 0.22;

class Device {
  constructor(id) {
    this.id = id;
    this.now = {}; this.prev = {};
    this.move = { x: 0, y: 0 }; this.aim = null;
    this.mouse = null; // screen px, for 'kb'
    this.lastUsed = 0;
  }
  held(b) { return !!this.now[b]; }
  pressed(b) { return !!this.now[b] && !this.prev[b]; }
  released(b) { return !this.now[b] && !!this.prev[b]; }
}

const deadzone = (x, y, dz = DEAD) => {
  const m = Math.hypot(x, y);
  if (m < dz) return { x: 0, y: 0 };
  const k = Math.min(1, (m - dz) / (1 - dz)) / m;
  return { x: x * k, y: y * k };
};

export class Input {
  constructor(canvasEl) {
    this.kb = new Device('kb');
    this.pads = {};
    this.keys = new Set();
    this.mouseBtn = new Set();
    this.canvas = canvasEl;
    addEventListener('keydown', e => {
      if (e.target.tagName === 'INPUT' && e.code !== 'Enter' && e.code !== 'Escape') return;
      this.keys.add(e.code);
      if (e.code === 'Tab' || e.code === 'Space') { if (e.target.tagName !== 'INPUT') e.preventDefault(); }
    });
    addEventListener('keyup', e => this.keys.delete(e.code));
    addEventListener('blur', () => { this.keys.clear(); this.mouseBtn.clear(); });
    addEventListener('mousemove', e => { this.kb.mouse = { x: e.clientX, y: e.clientY }; this.kb.lastUsed = performance.now(); });
    addEventListener('mousedown', e => { if (e.target.closest && e.target.closest('#ui button, #ui input, #ui select, #menu')) return; this.mouseBtn.add(e.button); });
    addEventListener('mouseup', e => this.mouseBtn.delete(e.button));
    addEventListener('contextmenu', e => { if (e.target.tagName === 'CANVAS') e.preventDefault(); });
  }

  setCanvas(el) { this.canvas = el; }

  // call once a frame
  poll() {
    const kb = this.kb;
    kb.prev = kb.now; kb.now = {};
    const k = this.keys;
    for (const [b, codes] of Object.entries(KEYS)) if (codes.some(c => k.has(c))) kb.now[b] = true;
    if (this.mouseBtn.has(0)) kb.now.light = true;
    if (this.mouseBtn.has(2)) kb.now.heavy = true;
    if (this.mouseBtn.has(1)) kb.now.lock = true;
    if (k.has('Enter') || k.has('Space')) kb.now.confirm = true;
    let mx = (k.has('KeyD') || k.has('ArrowRight') ? 1 : 0) - (k.has('KeyA') || k.has('ArrowLeft') ? 1 : 0);
    let my = (k.has('KeyS') || k.has('ArrowDown') ? 1 : 0) - (k.has('KeyW') || k.has('ArrowUp') ? 1 : 0);
    const m = Math.hypot(mx, my) || 1;
    kb.move = { x: mx / m, y: my / m };
    if (k.size || this.mouseBtn.size) kb.lastUsed = performance.now();

    const seen = new Set();
    for (const gp of (navigator.getGamepads ? navigator.getGamepads() : [])) {
      if (!gp || !gp.connected) continue;
      const id = 'pad' + gp.index;
      seen.add(id);
      const d = this.pads[id] ||= new Device(id);
      d.gp = gp;
      d.prev = d.now; d.now = {};
      for (const [b, idx] of Object.entries(PAD)) {
        if (idx.some(i => gp.buttons[i] && (gp.buttons[i].pressed || gp.buttons[i].value > 0.4))) d.now[b] = true;
      }
      d.move = deadzone(gp.axes[0] || 0, gp.axes[1] || 0);
      const a = deadzone(gp.axes[2] || 0, gp.axes[3] || 0, 0.35);
      d.aim = a.x || a.y ? a : null;
      // the left stick also navigates menus
      if (d.move.y < -0.6) d.now.up = true;
      if (d.move.y > 0.6) d.now.down = true;
      if (d.move.x < -0.6) d.now.left = true;
      if (d.move.x > 0.6) d.now.right = true;
      if (Object.keys(d.now).length || d.move.x || d.move.y || d.aim) d.lastUsed = performance.now();
    }
    for (const id of Object.keys(this.pads)) if (!seen.has(id)) delete this.pads[id];
  }

  devices() { return [this.kb, ...Object.values(this.pads)]; }
  get(id) { return id === 'kb' ? this.kb : this.pads[id]; }

  rumble(id, strength = 0.5, ms = 120) {
    const d = this.pads[id];
    const act = d && d.gp && d.gp.vibrationActuator;
    if (act && act.playEffect) act.playEffect('dual-rumble', { duration: ms, strongMagnitude: strength, weakMagnitude: strength * 0.6 }).catch(() => {});
  }
}

// which slot (0-3) a device's hero uses on this browser: the keyboard is 0, controllers 1-4
export const slotOf = id => id === 'kb' ? 0 : 1 + Number(id.slice(3));
export const deviceOfSlot = slot => slot === 0 ? 'kb' : 'pad' + (slot - 1);
// what to press for skill slot i (0 or 1) on a device
export const skillKey = (id, i) => id === 'kb' ? ['Z', 'X'][i] : ['LT', 'A'][i];
export const padName = id => id === 'kb' ? 'Keyboard & mouse' : 'Controller ' + (Number(id.slice(3)) + 1);
