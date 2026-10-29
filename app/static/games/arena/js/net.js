// The WebSocket to the match, the clock shared with the server, and the snapshot buffer that
// other players are drawn from (INTERP seconds in the past, smoothly interpolated).

const now = () => performance.now() / 1000;

export class Net {
  constructor(h) {
    this.h = h;  // onWelcome, onSnap, onRoster, onPong, onStatus
    this.ws = null;
    this.name = '';
    this.offset = null;  // server time minus local time
    this.samples = [];
    this.rtt = 0;
    this.snaps = [];
    this.interp = 0.1;
    this.wanted = false;
    this.retry = 1;
  }

  connect(name) {
    this.name = name;
    this.wanted = true;
    if (this.ws && this.ws.readyState <= 1) return;
    const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/games/frag-arena/ws`;
    const ws = new WebSocket(url);
    this.ws = ws;
    this.h.onStatus('Connecting…');
    ws.onopen = () => {
      this.retry = 1;
      ws.send(JSON.stringify({ t: 'hello', name: this.name }));
    };
    ws.onmessage = e => this.receive(JSON.parse(e.data));
    ws.onclose = () => {
      if (this.ws !== ws) return;
      this.ws = null;
      clearInterval(this.pinger);
      this.snaps = [];
      if (!this.wanted) return;
      this.h.onStatus(`Disconnected. Reconnecting in ${this.retry}s…`);
      setTimeout(() => this.connect(this.name), this.retry * 1000);
      this.retry = Math.min(this.retry * 2, 16);
    };
  }

  send(obj) {
    if (this.ws && this.ws.readyState === 1) this.ws.send(JSON.stringify(obj));
  }

  receive(m) {
    if (m.t === 's') {
      this.snaps.push(m);
      if (this.snaps.length > 60) this.snaps.shift();
      this.h.onSnap(m);
    } else if (m.t === 'welcome') {
      this.interp = m.interp;
      this.offset = m.ts - now();
      this.samples = [];
      this.snaps = [];
      this.h.onStatus('');
      this.h.onWelcome(m);
      let n = 0;
      const ping = () => {
        this.send({ t: 'ping', c: now(), rtt: Math.round(this.rtt * 1000) });
        // quick pings at first to settle the clock, then every two seconds
        if (++n === 6) { clearInterval(this.pinger); this.pinger = setInterval(ping, 2000); }
      };
      clearInterval(this.pinger);
      this.pinger = setInterval(ping, 250);
    } else if (m.t === 'pong') {
      const t = now();
      const rtt = t - m.c;
      this.samples.push({ rtt, off: m.s + rtt / 2 - t });
      if (this.samples.length > 10) this.samples.shift();
      // the quickest round trips give the truest offset
      const best = this.samples.reduce((a, b) => (b.rtt < a.rtt ? b : a));
      this.rtt = this.rtt ? this.rtt * 0.7 + rtt * 0.3 : rtt;
      if (Math.abs(best.off - this.offset) > 0.25) this.offset = best.off;
      else this.target = best.off;
    } else if (m.t === 'roster') {
      this.h.onRoster(m.list);
    } else if (m.t === 'full') {
      this.wanted = false;
      this.h.onStatus('The arena is full (12 players). Try again in a bit.');
    }
  }

  serverNow() {
    if (this.target !== undefined) {
      // drift toward the latest estimate rather than jumping
      this.offset += Math.max(-0.002, Math.min(0.002, this.target - this.offset));
    }
    return now() + (this.offset || 0);
  }

  renderTime() { return this.serverNow() - this.interp; }

  // Every player's state at time t, interpolated between the snapshots either side.
  sample(t) {
    const s = this.snaps;
    const out = new Map();
    if (!s.length) return out;
    let a = s[0], b = s[0];
    for (let i = s.length - 1; i >= 0; i--) {
      if (s[i].ts <= t) { a = s[i]; b = s[i + 1] || s[i]; break; }
    }
    const f = b.ts > a.ts ? Math.min(1, Math.max(0, (t - a.ts) / (b.ts - a.ts))) : 0;
    const prev = new Map(a.p.map(r => [r[0], r]));
    for (const r of b.p) {
      const q = prev.get(r[0]);
      if (!q || q[7] !== r[7] || Math.hypot(r[1] - q[1], r[2] - q[2], r[3] - q[3]) > 6) {
        out.set(r[0], { x: r[1], y: r[2], z: r[3], yaw: r[4], pitch: r[5], w: r[6], alive: !!r[7] });
        continue;
      }
      let dy = r[4] - q[4];
      dy = ((dy + Math.PI) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI) - Math.PI;
      out.set(r[0], {
        x: q[1] + (r[1] - q[1]) * f, y: q[2] + (r[2] - q[2]) * f, z: q[3] + (r[3] - q[3]) * f,
        yaw: q[4] + dy * f, pitch: q[5] + (r[5] - q[5]) * f, w: f < 0.5 ? q[6] : r[6], alive: !!r[7],
      });
    }
    return out;
  }
}
