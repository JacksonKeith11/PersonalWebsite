// Everything Board Brawl shows is drawn here with canvas paths: no images. Each function draws
// one thing centred on (x, y) at size s (roughly its radius).

export function ghost(c, x, y, s, { color = '#f4f1ff', t = 0, eyes = 2, mouth = 'o', tilt = 0, flip = false } = {}) {
  c.save();
  c.translate(x, y);
  c.rotate(tilt);
  if (flip) c.scale(-1, 1);
  c.fillStyle = color;
  c.beginPath();
  c.moveTo(-s, s * 0.9);
  c.lineTo(-s, -s * 0.1);
  c.arc(0, -s * 0.1, s, Math.PI, 0);
  c.lineTo(s, s * 0.9);
  const waves = 4;
  for (let i = 0; i < waves; i++) {
    const x1 = s - (2 * s * (i + 0.5)) / waves, x2 = s - (2 * s * (i + 1)) / waves;
    c.quadraticCurveTo(x1, s * (0.55 + 0.25 * Math.sin(t * 6 + i)), x2, s * 0.9);
  }
  c.closePath();
  c.fill();
  c.fillStyle = '#1d1426';
  if (eyes >= 1) { c.beginPath(); c.ellipse(-s * 0.35, -s * 0.2, s * 0.14, s * 0.2, 0, 0, Math.PI * 2); c.fill(); }
  if (eyes >= 2) { c.beginPath(); c.ellipse(s * 0.35, -s * 0.2, s * 0.14, s * 0.2, 0, 0, Math.PI * 2); c.fill(); }
  c.beginPath();
  if (mouth === 'o') c.ellipse(0, s * 0.25, s * 0.16, s * 0.2, 0, 0, Math.PI * 2);
  else c.ellipse(0, s * 0.3, s * 0.3, s * 0.07, 0, 0, Math.PI * 2);
  c.fill();
  c.restore();
}

export function pumpkin(c, x, y, s, { color = '#f07b1d', face = true, mouth = 'grin', eyes = 2, tilt = 0, flip = false } = {}) {
  c.save();
  c.translate(x, y);
  c.rotate(tilt);
  if (flip) c.scale(-1, 1);
  c.fillStyle = '#4b7d2a';
  c.fillRect(-s * 0.1, -s * 1.05, s * 0.2, s * 0.35);
  c.fillStyle = color;
  for (const [dx, w] of [[-0.45, 0.6], [0.45, 0.6], [0, 0.65]]) {
    c.beginPath();
    c.ellipse(dx * s, 0, w * s, s * 0.85, 0, 0, Math.PI * 2);
    c.fill();
  }
  c.strokeStyle = 'rgba(120, 50, 0, 0.45)';
  c.lineWidth = Math.max(1, s * 0.06);
  c.beginPath(); c.ellipse(0, 0, s * 0.3, s * 0.82, 0, 0, Math.PI * 2); c.stroke();
  if (face) {
    c.fillStyle = '#2a1500';
    const eye = sx => { c.beginPath(); c.moveTo(sx * s * 0.42, -s * 0.38); c.lineTo(sx * s * 0.22, -s * 0.08); c.lineTo(sx * s * 0.6, -s * 0.08); c.closePath(); c.fill(); };
    if (eyes >= 1) eye(-1);
    if (eyes >= 2) eye(1);
    c.beginPath();
    if (mouth === 'grin') {
      c.moveTo(-s * 0.55, s * 0.2);
      for (let i = 0; i <= 6; i++) c.lineTo(-s * 0.55 + (i * s * 1.1) / 6, s * (i % 2 ? 0.32 : 0.2) + Math.sin((i / 6) * Math.PI) * s * 0.12);
      c.quadraticCurveTo(0, s * 0.75, -s * 0.55, s * 0.2);
    } else {
      c.ellipse(0, s * 0.35, s * 0.18, s * 0.18, 0, 0, Math.PI * 2);
    }
    c.fill();
  }
  c.restore();
}

export function bat(c, x, y, s, { color = '#2b2135', t = 0, eyes = 2, tilt = 0, flip = false, eyeColor = '#ffd23f' } = {}) {
  c.save();
  c.translate(x, y);
  c.rotate(tilt);
  if (flip) c.scale(-1, 1);
  const flap = Math.sin(t * 14) * 0.35;
  c.fillStyle = color;
  for (const side of [-1, 1]) {
    c.save();
    c.scale(side, 1);
    c.rotate(-flap);
    c.beginPath();
    c.moveTo(s * 0.2, 0);
    c.quadraticCurveTo(s * 0.8, -s * 0.9, s * 1.5, -s * 0.3);
    c.quadraticCurveTo(s * 1.2, -s * 0.1, s * 1.15, s * 0.25);
    c.quadraticCurveTo(s * 0.95, 0, s * 0.75, s * 0.3);
    c.quadraticCurveTo(s * 0.55, s * 0.05, s * 0.2, s * 0.3);
    c.closePath();
    c.fill();
    c.restore();
  }
  c.beginPath(); c.ellipse(0, 0, s * 0.38, s * 0.5, 0, 0, Math.PI * 2); c.fill();
  c.beginPath(); c.moveTo(-s * 0.3, -s * 0.35); c.lineTo(-s * 0.2, -s * 0.7); c.lineTo(-s * 0.05, -s * 0.4);
  c.moveTo(s * 0.3, -s * 0.35); c.lineTo(s * 0.2, -s * 0.7); c.lineTo(s * 0.05, -s * 0.4); c.fill();
  c.fillStyle = eyeColor;
  if (eyes >= 1) { c.beginPath(); c.arc(-s * 0.14, -s * 0.12, s * 0.09, 0, Math.PI * 2); c.fill(); }
  if (eyes >= 2) { c.beginPath(); c.arc(s * 0.14, -s * 0.12, s * 0.09, 0, Math.PI * 2); c.fill(); }
  c.restore();
}

export function spider(c, x, y, s, { color = '#1b1b1f', t = 0, eyes = 2, tilt = 0, flip = false } = {}) {
  c.save();
  c.translate(x, y);
  c.rotate(tilt);
  if (flip) c.scale(-1, 1);
  c.strokeStyle = color;
  c.lineWidth = Math.max(1.5, s * 0.12);
  c.lineCap = 'round';
  for (const side of [-1, 1]) {
    for (let i = 0; i < 4; i++) {
      const a = -0.6 + i * 0.4 + Math.sin(t * 10 + i) * 0.08;
      c.beginPath();
      c.moveTo(0, 0);
      c.quadraticCurveTo(side * s * 0.8, -s * 0.6 + a * s * 0.6, side * s * 1.2, a * s * 1.1 + s * 0.3);
      c.stroke();
    }
  }
  c.fillStyle = color;
  c.beginPath(); c.ellipse(0, s * 0.15, s * 0.55, s * 0.6, 0, 0, Math.PI * 2); c.fill();
  c.beginPath(); c.arc(0, -s * 0.45, s * 0.32, 0, Math.PI * 2); c.fill();
  c.fillStyle = '#e8303a';
  if (eyes >= 1) { c.beginPath(); c.arc(-s * 0.12, -s * 0.5, s * 0.08, 0, Math.PI * 2); c.fill(); }
  if (eyes >= 2) { c.beginPath(); c.arc(s * 0.12, -s * 0.5, s * 0.08, 0, Math.PI * 2); c.fill(); }
  c.restore();
}

export function skull(c, x, y, s, { color = '#efe9dc', eyes = 2, mouth = 'teeth', tilt = 0, flip = false } = {}) {
  c.save();
  c.translate(x, y);
  c.rotate(tilt);
  if (flip) c.scale(-1, 1);
  c.fillStyle = color;
  c.beginPath(); c.arc(0, -s * 0.15, s * 0.85, 0, Math.PI * 2); c.fill();
  c.fillRect(-s * 0.45, s * 0.3, s * 0.9, s * 0.5);
  c.fillStyle = '#231a2b';
  if (eyes >= 1) { c.beginPath(); c.ellipse(-s * 0.33, -s * 0.15, s * 0.22, s * 0.26, 0, 0, Math.PI * 2); c.fill(); }
  if (eyes >= 2) { c.beginPath(); c.ellipse(s * 0.33, -s * 0.15, s * 0.22, s * 0.26, 0, 0, Math.PI * 2); c.fill(); }
  c.beginPath(); c.moveTo(0, s * 0.1); c.lineTo(-s * 0.1, s * 0.3); c.lineTo(s * 0.1, s * 0.3); c.fill();
  if (mouth === 'teeth') {
    for (let i = -2; i <= 2; i++) c.fillRect(i * s * 0.17 - s * 0.03, s * 0.48, s * 0.06, s * 0.28);
  } else {
    c.fillRect(-s * 0.3, s * 0.55, s * 0.6, s * 0.08);
  }
  c.restore();
}

export const CRITTERS = { ghost, pumpkin, bat, spider, skull };

export function crown(c, x, y, s, glow = 0) {
  c.save();
  c.translate(x, y);
  if (glow) { c.shadowColor = '#ffd75e'; c.shadowBlur = s * glow; }
  c.fillStyle = '#ffcf33';
  c.strokeStyle = '#8a5a00';
  c.lineWidth = Math.max(1, s * 0.1);
  c.beginPath();
  c.moveTo(-s, s * 0.55);
  c.lineTo(-s, -s * 0.35);
  c.lineTo(-s * 0.5, s * 0.1);
  c.lineTo(0, -s * 0.7);
  c.lineTo(s * 0.5, s * 0.1);
  c.lineTo(s, -s * 0.35);
  c.lineTo(s, s * 0.55);
  c.closePath();
  c.fill();
  c.shadowBlur = 0;
  c.stroke();
  c.fillStyle = '#e8303a';
  c.beginPath(); c.arc(0, s * 0.2, s * 0.15, 0, Math.PI * 2); c.fill();
  c.restore();
}

export function coin(c, x, y, s, value = 1) {
  c.save();
  c.translate(x, y);
  if (value > 1) {
    // a golden apple
    c.fillStyle = '#ffcc2e';
    c.shadowColor = '#ffe680'; c.shadowBlur = s;
    c.beginPath(); c.arc(-s * 0.3, 0, s * 0.75, 0, Math.PI * 2); c.arc(s * 0.3, 0, s * 0.75, 0, Math.PI * 2); c.fill();
    c.shadowBlur = 0;
    c.fillStyle = '#6b3d10'; c.fillRect(-s * 0.06, -s, s * 0.12, s * 0.4);
    c.fillStyle = '#4caf50'; c.beginPath(); c.ellipse(s * 0.25, -s * 0.85, s * 0.3, s * 0.13, -0.5, 0, Math.PI * 2); c.fill();
  } else {
    // a wrapped sweet
    c.fillStyle = '#ff6fb1';
    c.beginPath(); c.moveTo(-s * 0.5, 0); c.lineTo(-s * 1.1, -s * 0.45); c.lineTo(-s * 1.1, s * 0.45); c.closePath(); c.fill();
    c.beginPath(); c.moveTo(s * 0.5, 0); c.lineTo(s * 1.1, -s * 0.45); c.lineTo(s * 1.1, s * 0.45); c.closePath(); c.fill();
    c.fillStyle = '#ff9fd0';
    c.beginPath(); c.arc(0, 0, s * 0.6, 0, Math.PI * 2); c.fill();
    c.strokeStyle = '#fff'; c.lineWidth = s * 0.15;
    c.beginPath(); c.arc(0, 0, s * 0.35, -1, 1.4); c.stroke();
  }
  c.restore();
}

// A player's piece: a round blob in their colour, with a face and their initial.
export function token(c, x, y, r, color, { label = '', ring = null, dim = false, t = 0, squish = 0 } = {}) {
  c.save();
  c.translate(x, y);
  c.scale(1 + squish, 1 - squish);
  c.globalAlpha = dim ? 0.4 : 1;
  c.fillStyle = 'rgba(0, 0, 0, 0.35)';
  c.beginPath(); c.ellipse(0, r * 0.9, r * 0.9, r * 0.3, 0, 0, Math.PI * 2); c.fill();
  c.fillStyle = color;
  c.beginPath(); c.arc(0, 0, r, 0, Math.PI * 2); c.fill();
  c.lineWidth = Math.max(2, r * 0.14);
  c.strokeStyle = ring || '#fff';
  c.stroke();
  c.fillStyle = 'rgba(255, 255, 255, 0.35)';
  c.beginPath(); c.ellipse(-r * 0.35, -r * 0.45, r * 0.3, r * 0.18, -0.6, 0, Math.PI * 2); c.fill();
  c.fillStyle = '#1a1020';
  const blink = (t % 4) < 0.12 ? 0.2 : 1;
  c.beginPath(); c.ellipse(-r * 0.3, -r * 0.05, r * 0.11, r * 0.16 * blink, 0, 0, Math.PI * 2); c.fill();
  c.beginPath(); c.ellipse(r * 0.3, -r * 0.05, r * 0.11, r * 0.16 * blink, 0, 0, Math.PI * 2); c.fill();
  if (label) {
    c.fillStyle = '#fff';
    c.font = `700 ${Math.round(r * 0.62)}px "Source Sans 3", system-ui, sans-serif`;
    c.textAlign = 'center';
    c.textBaseline = 'middle';
    c.lineWidth = 3;
    c.strokeStyle = 'rgba(0,0,0,0.6)';
    c.strokeText(label, 0, r * 0.5);
    c.fillText(label, 0, r * 0.5);
  }
  c.restore();
}

export function web(c, x, y, s, alpha = 0.8) {
  c.save();
  c.translate(x, y);
  c.strokeStyle = `rgba(240, 240, 255, ${alpha})`;
  c.lineWidth = 1.2;
  for (let i = 0; i < 8; i++) {
    const a = (i / 8) * Math.PI * 2;
    c.beginPath(); c.moveTo(0, 0); c.lineTo(Math.cos(a) * s, Math.sin(a) * s); c.stroke();
  }
  for (let r = s * 0.3; r <= s; r += s * 0.3) {
    c.beginPath();
    for (let i = 0; i <= 8; i++) {
      const a = (i / 8) * Math.PI * 2;
      const px = Math.cos(a) * r, py = Math.sin(a) * r;
      if (i === 0) c.moveTo(px, py); else c.quadraticCurveTo(Math.cos(a - 0.4) * r * 0.85, Math.sin(a - 0.4) * r * 0.85, px, py);
    }
    c.stroke();
  }
  c.restore();
}

export function tombstone(c, x, y, s, { cross = false, tilt = 0 } = {}) {
  c.save();
  c.translate(x, y);
  c.rotate(tilt);
  c.fillStyle = '#5d5a6e';
  c.strokeStyle = '#2b2838';
  c.lineWidth = 2;
  c.beginPath();
  if (cross) {
    c.rect(-s * 0.15, -s * 1.1, s * 0.3, s * 1.6);
    c.rect(-s * 0.5, -s * 0.8, s, s * 0.28);
  } else {
    c.moveTo(-s * 0.55, s * 0.5);
    c.lineTo(-s * 0.55, -s * 0.5);
    c.arc(0, -s * 0.5, s * 0.55, Math.PI, 0);
    c.lineTo(s * 0.55, s * 0.5);
    c.closePath();
  }
  c.fill();
  c.stroke();
  if (!cross) {
    c.fillStyle = '#3e3b4d';
    c.fillRect(-s * 0.25, -s * 0.55, s * 0.5, s * 0.08);
    c.fillRect(-s * 0.25, -s * 0.35, s * 0.5, s * 0.08);
  }
  c.restore();
}

export function deadTree(c, x, y, s, seed = 1) {
  let r = seed;
  const rnd = () => { r = (r * 16807) % 2147483647; return r / 2147483647; };
  c.save();
  c.translate(x, y);
  c.strokeStyle = '#1c1424';
  c.lineCap = 'round';
  const branch = (len, w, depth) => {
    c.lineWidth = w;
    c.beginPath(); c.moveTo(0, 0); c.lineTo(0, -len); c.stroke();
    if (depth === 0) return;
    c.save();
    c.translate(0, -len);
    for (const d of [-1, 1]) {
      c.save();
      c.rotate(d * (0.3 + rnd() * 0.5));
      branch(len * (0.55 + rnd() * 0.2), w * 0.62, depth - 1);
      c.restore();
    }
    c.restore();
  };
  branch(s * 0.5, s * 0.1, 4);
  c.restore();
}

export function rand(seed) {
  let s = seed >>> 0 || 1;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
