// Overlords' fight playback: the server sends each fight's whole timeline (app/overlords/sim.py
// lists the events); this rebuilds what the battlefield looks like at any moment of it. Playback
// only goes forward; switching to another fight builds a new Playback and catches up at once.

export class Playback {
  constructor(fight, startedAt, cfg, onEvent = () => {}) {
    this.fight = fight;
    this.res = fight.res;
    this.startedAt = startedAt; // performance.now()/1000 when the fight's t=0 was
    this.cfg = cfg;
    this.onEvent = onEvent;
    this.units = new Map();
    this.fx = []; // { kind, at, life, ... } short-lived effects to draw
    this.i = 0;
    this.t = -1;
    this.quiet = false;
    for (const row of this.res.start) this.addUnit(row);
  }

  addUnit([id, side, key, star, c, r, max, maxmana, mana, items = []]) {
    this.units.set(id, {
      id, side, key, star, c, r, fc: c, fr: r, moveAt: -9, hp: max, max, mana, maxmana, shield: 0, items,
      alive: true, deadAt: 0, stunUntil: 0, attackAt: -9, castAt: -9, hitAt: -9, target: 0, burnUntil: 0,
      range: this.cfg.units[key].range,
    });
  }

  get done() { return this.t >= this.res.time; }

  // Moves playback on to fight time t (seconds), applying every event up to it. `quiet` (catching
  // up) makes no sounds.
  advance(t, quiet = false) {
    const ev = this.res.events;
    this.quiet = quiet;
    while (this.i < ev.length && ev[this.i][1] <= t) this.apply(ev[this.i++]);
    this.t = t;
    this.fx = this.fx.filter(f => t - f.at < f.life);
    this.quiet = false;
  }

  sound(name) { if (!this.quiet) this.onEvent(name); }

  apply(e) {
    const [kind, t] = e;
    const U = this.units;
    const u = kind === 'sp' || kind === 'v' ? null : U.get(kind === 'd' ? e[3] : e[2]);
    if (!u && kind !== 'sp' && kind !== 'v') return;
    switch (kind) {
      case 'm': // a unit only sets off once its last step is done, so it starts from a whole hex
        u.fc = u.c; u.fr = u.r;
        u.c = e[3]; u.r = e[4]; u.moveAt = t;
        break;
      case 'j':
        this.fx.push({ kind: 'jump', at: t, from: [u.c, u.r], to: [e[3], e[4]], life: 0.4 });
        u.c = u.fc = e[3]; u.r = u.fr = e[4]; u.moveAt = -9;
        break;
      case 'a': {
        const v = U.get(e[3]);
        u.attackAt = t;
        u.target = e[3];
        u.lastStrike = 'a';
        if (u.mana < u.maxmana) u.mana = Math.min(u.maxmana, u.mana + 10);
        if (v && u.range > 1) this.fx.push({ kind: 'shot', at: t, from: u.id, to: v.id, side: u.side, key: u.key, life: 0.22 });
        this.sound(u.range > 1 ? 'shot' : 'hit');
        break;
      }
      case 'x':
        this.fx.push({ kind: 'text', at: t, id: u.id, text: 'miss', color: '#cfd6e6', life: 0.7 });
        break;
      case 'd': {
        u.hp = e[7];
        if (e[5] === 3) { u.burnUntil = t + 1.5; break; } // burning comes in lumps (sim.BURN_LUMP)
        u.hitAt = t;
        const src = U.get(e[2]);
        if (src && src.castAt === t && src.id !== u.id) { // a spell landing: a bolt from its caster
          this.fx.push({ kind: 'bolt', at: t, from: src.id, to: u.id, key: src.key, life: 0.3 });
        }
        if (e[5] !== 3) {
          const colors = ['#ffb070', '#8fc4ff', '#ffffff'];
          this.fx.push({ kind: 'text', at: t, id: u.id, text: String(e[4]), color: colors[e[5]], big: !!e[6], life: 0.8 });
          if (e[6]) this.sound('crit');
        }
        break;
      }
      case 'c': {
        u.mana = 0;
        u.castAt = t;
        if (e[3]) u.target = e[3];
        const ab = this.cfg.units[u.key].ability;
        this.fx.push({ kind: 'cast', at: t, id: u.id, target: e[3], name: ab?.name, life: 1.0 });
        for (const st of ab?.steps || []) { // areas and lines show where the ability lands
          const [sel, n] = (st.to || '').split(':');
          if (st.do !== 'hit') continue;
          if (sel === 'around_target' && e[3]) this.fx.push({ kind: 'area', at: t, id: e[3], r: +n, key: u.key, life: 0.5 });
          if (sel === 'around_self') this.fx.push({ kind: 'area', at: t, id: u.id, r: +n, key: u.key, life: 0.5 });
          if (sel === 'line' && e[3]) this.fx.push({ kind: 'line', at: t, from: u.id, to: e[3], n: +n, key: u.key, life: 0.4 });
        }
        this.sound('cast');
        break;
      }
      case 'h':
        u.hp = Math.min(u.max, u.hp + e[3]);
        if (e[3] > 0) {
          this.fx.push({ kind: 'text', at: t, id: u.id, text: '+' + e[3], color: '#7be08a', life: 0.8 });
          this.fx.push({ kind: 'heal', at: t, id: u.id, life: 0.6 });
        }
        this.sound('heal');
        break;
      case 's':
        u.shield += e[3];
        this.fx.push({ kind: 'ring', at: t, id: u.id, color: '#e8f0ff', life: 0.5 });
        break;
      case 'st':
        u.stunUntil = t + e[3];
        this.sound('stun');
        break;
      case 'sp': {
        this.addUnit(e[2]);
        this.fx.push({ kind: 'ring', at: t, id: e[2][0], color: '#7be08a', life: 0.6 });
        break;
      }
      case 'r':
        u.hp = e[3];
        this.fx.push({ kind: 'ring', at: t, id: u.id, color: '#b9a6ff', life: 0.8 });
        this.sound('rise');
        break;
      case 'k':
        u.alive = false;
        u.deadAt = t;
        u.hp = 0;
        this.sound('death');
        break;
      case 'v':
        for (const [id, hp, mana, shield] of e[2]) {
          const w = U.get(id);
          if (w) { w.hp = hp; w.mana = mana; w.shield = shield; }
        }
        break;
    }
  }

  // Where a unit is at time t: `from` and `to` hexes and how far along (0..1). The drawing lerps
  // between the two hexes' pixel centres.
  pos(u, t) {
    const k = Math.min(1, Math.max(0, (t - u.moveAt) / this.cfg.rules.move_time));
    return { from: [u.fc, u.fr], to: [u.c, u.r], k };
  }
}
