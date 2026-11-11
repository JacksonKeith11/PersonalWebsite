// The socket (the shared GameSocket) and the clock shared with the server. Boss moves are scheduled in
// server time, so everything about the boss is drawn at `now()`: the server's clock, right now.
import { GameSocket, identity } from '../../shared/net.js?v=1';

export const ME = identity('kingfall');

export class Net {
  constructor(version, onMessage) {
    this.offset = null;   // server time - local time (seconds)
    this.best = Infinity; // quickest round trip so far
    this.rtt = 0;
    this.pings = 0;
    this.hello = { v: version, token: ME.saved.token, tab: ME.tab };
    this.sock = new GameSocket('/games/kingfall/ws', {
      hello: () => this.hello,
      onMessage: m => this.message(m, onMessage),
      onStatus: s => this.status && this.status(s),
      onClose: retry => this.closed && this.closed(retry),
    });
    this.timer = null;
  }
  local() { return performance.now() / 1000; }
  now() { return this.local() + (this.offset ?? 0); }
  connect(hello) {
    Object.assign(this.hello, hello);
    this.sock.open();
    clearInterval(this.timer);
    this.timer = setInterval(() => this.ping(), 500);
  }
  ping() {
    this.pings++;
    if (this.pings > 12 && this.pings % 4) return; // quick pings at first, then every 2 s
    this.send({ t: 'ping', c: this.local() });
  }
  message(m, cb) {
    if (m.t === 'pong') {
      const rtt = this.local() - m.c;
      this.rtt = this.rtt ? this.rtt * 0.8 + rtt * 0.2 : rtt;
      // trust the quickest round trips; let the estimate drift slowly so a slow spike can't jolt it
      if (rtt < this.best * 1.25 || this.offset === null) {
        this.best = Math.min(this.best, rtt);
        const off = m.s + rtt / 2 - this.local();
        this.offset = this.offset === null ? off : this.offset + (off - this.offset) * 0.3;
      }
      return;
    }
    if (m.t === 'welcome' && this.offset === null) this.offset = m.st - this.local();
    cb(m);
  }
  send(m) { this.sock.send(m); }
}
