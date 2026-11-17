// The start of a room-code game, shared by Scramble and Holdfast: the menu (a name, make a room or
// join one by code), the connection, and the messages every such game gets (welcome, reload,
// error). The page needs elements with these ids: menu, name, create, code, join, status, and
// (in its lobby) share and copy. Styles are in lobby.css.
//
//   const room = startRoom({ key: 'scramble', path: '/games/scramble', title: 'Scramble',
//                            show, onMessage });
//   room.send({ t: 'start' });   room.you   room.code
//
// `show(id)` shows one of the page's screens ('menu' is ours); `onMessage(m)` gets every message,
// `welcome` included, after `you` and `code` are set.

import { GameSocket, identity } from './net.js?v=1';

const $ = id => document.getElementById(id);

export function startRoom({ key, path, title, show, onMessage }) {
  const { saved, save, tab } = identity(key);
  const room = { you: null, code: null, saved, save };
  let join = null;
  const status = text => { $('status').textContent = text; };
  // the page's own ?v=, so the server can tell a tab left open across a deploy to reload
  const version = new URL(document.querySelector('script[type=module][src]').src).searchParams.get('v');

  const sock = new GameSocket(`${path}/ws`, {
    hello: () => ({
      t: 'hello', v: version, name: saved.name || 'Player', token: saved.token, tab,
      room: room.code || join.room || '', create: !room.code && !!join.create,
    }),
    onStatus: status,
    onMessage: m => {
      if (m.t === 'welcome') {
        room.you = m.you;
        room.code = m.code;
        status('');
        history.replaceState(null, '', `${path}?room=${m.code}${debug ? '&debug' : ''}`);
        if ($('share')) $('share').value = `${location.origin}${path}?room=${m.code}`;
      } else if (m.t === 'reload') {
        // once per version, in case something keeps serving the old page
        let tried = null;
        try { tried = sessionStorage.getItem(`${key}-reload`); sessionStorage.setItem(`${key}-reload`, version); } catch {}
        sock.stop();
        if (tried !== version) location.reload();
        else status(`${title} has just been updated: reload the page to play.`);
        return;
      } else if (m.t === 'error') {
        sock.stop();
        room.code = null;
        history.replaceState(null, '', path);
        show('menu');
        status(m.msg);
        return;
      }
      onMessage(m);
    },
  });
  room.send = m => sock.send(m);
  const connect = opts => { join = opts; room.code = null; sock.open(); };

  const params = new URLSearchParams(location.search);
  const debug = params.has('debug');
  room.debug = debug;
  const roomParam = (params.get('room') || '').toUpperCase().slice(0, 4);
  $('name').value = saved.name || '';
  $('code').value = roomParam;

  const takeName = () => {
    const n = $('name').value.trim().slice(0, 16);
    if (!n) { $('name').focus(); status('Pick a name first.'); return false; }
    saved.name = n;
    save();
    return true;
  };
  const joinRoom = () => {
    if (!takeName()) return;
    const code = $('code').value.trim().toUpperCase();
    if (code.length !== 4) { status('Room codes are four letters.'); return; }
    connect({ room: code });
  };
  $('create').addEventListener('click', () => { if (takeName()) connect({ create: true }); });
  $('join').addEventListener('click', joinRoom);
  $('code').addEventListener('keydown', e => { if (e.key === 'Enter') joinRoom(); });
  $('code').addEventListener('input', () => { $('code').value = $('code').value.toUpperCase().replace(/[^A-Z]/g, ''); });
  $('copy')?.addEventListener('click', () => {
    navigator.clipboard?.writeText($('share').value).then(() => {
      $('copy').textContent = 'Copied!';
      setTimeout(() => { $('copy').textContent = 'Copy'; }, 1500);
    });
  });

  // Coming back to a room link with a name already saved: straight back in.
  if (roomParam && saved.name) connect({ room: roomParam });
  else show('menu');
  return room;
}

// A player's row for a lobby list: a dot in their colour, their name, and a tag on the right.
export function person(p, you, tag = '') {
  const li = document.createElement('li');
  if (p.on === false) li.className = 'off';
  const dot = document.createElement('span');
  dot.className = 'dot';
  dot.style.setProperty('--c', p.color);
  const name = document.createElement('span');
  name.textContent = p.name + (p.id === you ? ' (you)' : '');
  li.append(dot, name);
  if (tag) {
    const t = document.createElement('span');
    t.className = 'tag';
    t.textContent = tag;
    li.append(t);
  }
  return li;
}
