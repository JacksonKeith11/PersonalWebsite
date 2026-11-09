// What the multiplayer games (Frag Arena, Board Brawl, Saltbound, Kingfall) share in the browser: who this
// browser is, and a WebSocket to the game that reconnects on its own. The server side is
// app/rooms.py.

const randomId = () => Array.from(crypto.getRandomValues(new Uint8Array(12)), b => b.toString(16).padStart(2, '0')).join('');

// Settings kept in localStorage under `key`, always holding a `token` that names this browser (so a
// reload or a dropped connection comes back as the same player), and `tab`, an id for this tab (so
// a second tab of the same browser plays as someone else). `save()` writes the settings back.
export function identity(key) {
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(key)) || {}; } catch { /* private mode */ }
  const save = () => { try { localStorage.setItem(key, JSON.stringify(saved)); } catch { /* private mode */ } };
  if (!saved.token) { saved.token = randomId(); save(); }
  let tab = '';
  try {
    tab = sessionStorage.getItem(`${key}-tab`) || randomId();
    sessionStorage.setItem(`${key}-tab`, tab);
  } catch { tab = randomId(); }
  return { saved, save, tab };
}

// A game's WebSocket at `path`. `open()` connects; a lost connection retries after 1, 2, 4... up to
// 16 seconds until `close()` (or `stop()`, which leaves the socket for the server to close).
//   hello()        the first message, sent on every connect
//   onMessage(m)   each message from the server
//   onStatus(text) "Connecting…", "Disconnected. Reconnecting in 2s…"
//   onClose(retry) the socket closed; `retry` is the seconds until the next try, or 0 for none
export class GameSocket {
  constructor(path, { hello, onMessage, onStatus = () => {}, onClose = () => {} }) {
    this.url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}${path}`;
    Object.assign(this, { hello, onMessage, onStatus, onClose });
    this.ws = null;
    this.wanted = false;
    this.retry = 1;
  }

  open() {
    this.wanted = true;
    if (this.ws && this.ws.readyState <= 1) return;
    const ws = new WebSocket(this.url);
    this.ws = ws;
    this.onStatus('Connecting…');
    ws.onopen = () => {
      this.retry = 1;
      ws.send(JSON.stringify(this.hello()));
    };
    ws.onmessage = e => this.onMessage(JSON.parse(e.data));
    ws.onclose = () => {
      if (this.ws !== ws) return;
      this.ws = null;
      if (!this.wanted) { this.onClose(0); return; }
      const wait = this.retry;
      this.retry = Math.min(this.retry * 2, 16);
      this.onStatus(`Disconnected. Reconnecting in ${wait}s…`);
      this.onClose(wait);
      setTimeout(() => { if (this.wanted && !this.ws) this.open(); }, wait * 1000);
    };
  }

  // stop reconnecting (the server turned us away and is closing the socket)
  stop() { this.wanted = false; }

  close() {
    this.wanted = false;
    if (this.ws) this.ws.close();
  }

  send(m) {
    if (this.ws && this.ws.readyState === 1) this.ws.send(JSON.stringify(m));
  }
}
