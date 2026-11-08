// Saltbound in the browser: the connection, and choosing which screen to show from the room
// state the server sends whenever anything changes.
import { S, saved, tab, setSender, send, mine } from './store.js?v=179';
import { $, toast } from './ui.js?v=179';
import { renderTitle, renderLobby, renderEnd } from './screens.js?v=179';
import { renderGame, handleFx, teardownGame } from './hud.js?v=179';
import { combatBusy } from './combat.js?v=179';
import * as sfx from './audio.js?v=179';
import { GameSocket } from '../../shared/net.js?v=1';

const VERSION = new URL(import.meta.url).searchParams.get('v');
const params = new URLSearchParams(location.search);
const DEBUG = params.has('bots');

let join = null;
const sock = new GameSocket('/games/saltbound/ws', {
  hello: () => ({
    t: 'hello', v: VERSION, name: saved.name || 'Sailor', token: saved.token, tab, debug: DEBUG,
    room: S.code || join.room || '', create: !S.code && !!join.create,
  }),
  onMessage: m => receive(m),
  onStatus: text => setStatus(text),
  onClose: retry => { if (retry) toast(`Connection lost. Reconnecting in ${retry}s…`, 'err'); },
});

export function connect(opts) {
  join = opts;
  sock.open();
}

export function disconnect() {
  S.code = null; S.room = null; S.game = null; S.world = null;
  sock.close();
  history.replaceState(null, '', location.pathname + (DEBUG ? '?bots' : ''));
  teardownGame();
  render();
}

setSender(m => sock.send(m));

function setStatus(text) { const el = $('status'); if (el) el.textContent = text; }

function receive(m) {
  switch (m.t) {
    case 'welcome':
      S.you = m.you; S.code = m.code; S.static = m.static;
      history.replaceState(null, '', `${location.pathname}?room=${m.code}${DEBUG ? '&bots' : ''}`);
      break;
    case 'saves': S.saves = m.list; render(); break;
    case 'world': S.world = m; S.fresh = true; break;
    case 'state': {
      const before = S.game;
      S.room = m.room; S.game = m.game;
      // worked gear (tempered or enchanted) has its own key: add it to the item list every lookup uses
      for (const [k, it] of Object.entries(S.game?.forged || {})) { S.static.items[k] = it; S.static.prices[k] = it.price; }
      if (S.game) {
        const fx = S.game.fx.filter(f => f.id > S.lastFx);
        if (S.fresh) { S.fresh = false; S.lastFx = S.game.fx.length ? S.game.fx[S.game.fx.length - 1].id : 0; render(); }
        else {
          // effects first, so animations start from the old positions instead of flashing the new state
          if (fx.length) S.lastFx = fx[fx.length - 1].id;
          if (shown === 'game') handleFx(fx, before);
          render();
          if (shown !== 'game') handleFx(fx, before);
        }
      } else {
        S.lastFx = 0; S.fresh = true; render();
      }
      break;
    }
    case 'err': toast(m.msg, 'err'); sfx.play('error'); break;
    case 'error': sock.stop(); S.code = null; render(); setStatus(m.msg); toast(m.msg, 'err'); break;
    case 'reload': location.reload(); break;
  }
}

let shown = null;
export function render() {
  renderScreen();
  sfx.music(shown === 'game' && combatOpenNow() ? 'fight' : shown === 'end' ? null : 'map');
}
function combatOpenNow() { return !!document.querySelector('.combat'); }
function renderScreen() {
  const r = S.room, g = S.game;
  if (!S.code || !r) { if (shown !== 'title') teardownGame(); shown = 'title'; renderTitle(); return; }
  if (!g) { if (shown === 'game' || shown === 'end') teardownGame(); shown = 'lobby'; renderLobby(); return; }
  if (g.phase === 'end' && !combatBusy()) { if (shown === 'game') teardownGame(); shown = 'end'; renderEnd(); return; }
  if (!S.world) return;
  if (S.sel === null || !mine().includes(S.sel)) S.sel = mine()[0] ?? 0;
  shown = 'game';
  renderGame();
}

export const debug = DEBUG;
if (params.get('room')) connect({ room: params.get('room').toUpperCase() });
else {
  render();
  // saved runs for the title screen, before joining any room
  fetch(`/games/saltbound/saves?token=${encodeURIComponent(saved.token)}`, { cache: 'no-store' })
    .then(r => (r.ok ? r.json() : [])).then(list => { if (!S.code && list.length) { S.saves = list; render(); } }).catch(() => {});
}
if (DEBUG) { window.saltbound = S; window.saltboundSend = send; }
