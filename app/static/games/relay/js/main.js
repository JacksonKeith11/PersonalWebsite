// Sketch Relay in the browser: the connection, the menu and lobby, each step's job (write, draw or
// guess) and reading the books out at the end. The server sends the room's state whenever it
// changes; a player's job for the step and the finished books arrive once, in their own messages.

import { ERASER, H, PALETTE, Pad, W, WIDTHS, paint, show as showDrawing } from './pad.js?v=1';
import { GameSocket, identity } from '../../shared/net.js?v=1';

const $ = id => document.getElementById(id);
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
};

const { saved, save, tab } = identity('relay');

const S = {
  you: null, code: null, cfg: {},
  st: null,          // the room's state
  task: null,        // this step's job
  setUp: null,       // the step whose job is on screen
  deadline: null,    // performance.now() when the step's clock runs out
  timedOut: null,    // the step already handed in because the clock ran out
  books: [],
  tab: 0,            // the book open in the album
  drawn: null,       // what the pages list is showing: "book:pages"
};
let pad = null;

// ---------------------------------------------------------------- the connection

let join = null;

// this page's ?v=, so the server can tell a tab left open across a deploy to reload
const VERSION = new URL(import.meta.url).searchParams.get('v');

const sock = new GameSocket('/games/sketch-relay/ws', {
  hello: () => ({
    t: 'hello', v: VERSION, name: saved.name || 'Player', token: saved.token, tab,
    room: S.code || join.room || '', create: !S.code && !!join.create,
  }),
  onMessage: m => receive(m),
  onStatus: text => status(text),
});

function connect(opts) {
  join = opts;
  sock.open();
}

const send = m => sock.send(m);
const status = text => { $('status').textContent = text; };

function receive(m) {
  if (m.t === 'welcome') {
    S.you = m.you;
    S.code = m.code;
    S.cfg = m;
    status('');
    history.replaceState(null, '', `/games/sketch-relay?room=${m.code}`);
    if (!pad) pad = new Pad($('pad'), { ink: m.ink, onChange: showInk });
  } else if (m.t === 'state') {
    S.st = m;
    S.deadline = m.left != null ? performance.now() + m.left * 1000 : null;
    if (m.phase !== 'play') S.task = S.setUp = S.timedOut = null;
    render();
  } else if (m.t === 'task') {
    S.task = m;
    if (S.st) render();
  } else if (m.t === 'books') {
    S.books = m.books;
    S.drawn = null;
    if (S.st) render();
  } else if (m.t === 'reload') {
    // once per version, in case something keeps serving the old page
    let tried = null;
    try { tried = sessionStorage.getItem('relay-reload'); sessionStorage.setItem('relay-reload', VERSION); } catch {}
    sock.stop();
    if (tried !== VERSION) location.reload();
    else status('Sketch Relay has just been updated: reload the page to play.');
  } else if (m.t === 'error') {
    sock.stop();
    S.code = null;
    S.st = null;
    history.replaceState(null, '', '/games/sketch-relay');
    show('menu');
    status(m.msg);
  }
}

// ---------------------------------------------------------------- drawing the page from the state

function show(screen) {
  for (const id of ['menu', 'lobby', 'play', 'books']) $(id).hidden = id !== screen;
}

const player = id => S.st.players.find(p => p.id === id);
const nameOf = id => player(id)?.name || 'Someone';
const isHost = () => S.st.host === S.you;

function person(p, tag, tagClass = '') {
  const li = el('li', p.on ? '' : 'off');
  const dot = el('span', 'dot');
  dot.style.setProperty('--c', p.color);
  li.append(dot, el('span', '', p.name + (p.id === S.you ? ' (you)' : '')));
  if (tag) li.append(el('span', `tag ${tagClass}`, tag));
  return li;
}

function render() {
  const st = S.st;
  document.body.classList.toggle('host', isHost());
  if (st.phase === 'lobby') { show('lobby'); renderLobby(); }
  else if (st.phase === 'play') { show('play'); renderPlay(); }
  else { show('books'); renderBooks(); }
}

function renderLobby() {
  const st = S.st, n = st.players.length, { min, max } = S.cfg;
  $('room-code').textContent = S.code;
  $('share').value = `${location.origin}/games/sketch-relay?room=${S.code}`;
  $('count').textContent = `${n} of ${max}`;
  $('seats').replaceChildren(...st.players.map(p => person(p, p.id === st.host ? 'Host' : '')));
  $('timer').value = st.timer;
  $('timer').disabled = !isHost();
  $('start').disabled = n < min;
  $('lobby-note').textContent =
    n < min ? `Needs at least ${min} players: ${min - n} more to go.`
      : n > max ? `Only the first ${max} to join will play; the rest can watch.`
        : isHost() ? 'A game has as many steps as players, so more players means a longer game.'
          : `Waiting for ${nameOf(st.host)} to start the game.`;
}

// ---------------------------------------------------------------- a step: write, draw or guess

const DOING = { write: 'Writing…', draw: 'Drawing…', guess: 'Guessing…' };

function renderPlay() {
  const st = S.st, task = S.task;
  $('step').textContent = `Step ${st.step + 1} of ${st.steps}`;
  const mine = player(S.you)?.playing && task && task.step === st.step && !task.done ? task : null;
  for (const id of ['write', 'draw', 'guess']) $(id).hidden = !mine || mine.kind !== id;
  $('waiting').hidden = !!mine;
  if (mine) {
    if (S.setUp !== mine.step) { S.setUp = mine.step; setUp(mine); }
  } else {
    const watching = !player(S.you)?.playing;
    const slow = st.order.map(player).filter(p => !p.done);
    $('waiting-title').textContent = watching ? 'A game is under way' : 'Passed on!';
    $('waiting-note').textContent = watching ? "You'll be dealt in when the next one starts."
      : slow.length ? 'Waiting for everyone else to finish.' : 'Everyone is done.';
    $('progress').replaceChildren(...st.order.map(player).map(p =>
      person(p, p.done ? 'Done' : p.on ? DOING[st.kind] : 'Away', p.done ? 'done' : '')));
    $('hurry').hidden = watching || !slow.length;
  }
  tick();
}

let stopReplay = () => {};

function setUp(task) {
  window.scrollTo(0, 0);
  if (task.kind === 'write') {
    $('write-text').value = '';
    $('write-text').maxLength = S.cfg.len;
    $('ideas').replaceChildren(...task.ideas.map(idea => {
      const b = el('button', '', idea);
      b.type = 'button';
      b.addEventListener('click', () => { $('write-text').value = idea; $('write-text').focus(); });
      return b;
    }));
    $('write-text').focus();
  } else if (task.kind === 'draw') {
    $('draw-prompt').textContent = task.page.text;
    pad.reset();
  } else {
    $('guess-text').value = '';
    $('guess-text').maxLength = S.cfg.len;
    stopReplay();
    stopReplay = showDrawing($('guess-sheet'), task.page.strokes, 1.2);
  }
}

function submit(extra) {
  const task = S.task;
  if (!task || task.done) return;
  send({ t: 'submit', step: task.step, ...extra });
  task.done = true;
  renderPlay();
}

function submitText(input) {
  const text = input.value.trim();
  if (!text) { input.focus(); return; }
  submit({ text });
}

$('write').addEventListener('submit', e => { e.preventDefault(); submitText($('write-text')); });
$('guess').addEventListener('submit', e => { e.preventDefault(); submitText($('guess-text')); });
$('draw-done').addEventListener('click', () => submit({ strokes: pad.drawing() }));
$('hurry').addEventListener('click', () => send({ t: 'hurry' }));

// The clock. When it runs out, hand in whatever is there (the server fills in for nothing at all).
function tick() {
  const st = S.st, clock = $('clock');
  if (!st || st.phase !== 'play' || S.deadline == null) { clock.hidden = true; return; }
  const left = Math.max(0, Math.ceil((S.deadline - performance.now()) / 1000));
  clock.hidden = false;
  clock.textContent = `${Math.floor(left / 60)}:${String(left % 60).padStart(2, '0')}`;
  clock.classList.toggle('low', left <= 10);
  const task = S.task;
  if (left > 0 || !task || task.done || task.step !== st.step || S.timedOut === task.step) return;
  S.timedOut = task.step;
  if (task.kind === 'draw') submit({ strokes: pad.drawing() });
  else {
    const text = $(`${task.kind}-text`).value.trim();
    if (text) submit({ text });
  }
}
setInterval(tick, 250);

// ---------------------------------------------------------------- the drawing tools

let brush = 0;      // the colour to go back to after the eraser

function pressed(group, i) {
  [...group.children].forEach((b, j) => b.setAttribute('aria-pressed', String(i === j)));
}

function pickColor(c) {
  if (c !== ERASER) brush = c;
  pad.color = c;
  pressed($('colors'), c === ERASER ? -1 : c);
  $('eraser').setAttribute('aria-pressed', String(c === ERASER));
}

const COLOR_NAMES = ['Black', 'Grey', 'Brown', 'Red', 'Orange', 'Yellow', 'Green', 'Teal', 'Blue', 'Purple', 'Pink'];
PALETTE.slice(0, ERASER).forEach((color, c) => {
  const b = el('button');
  b.type = 'button';
  b.style.setProperty('--c', color);
  b.setAttribute('aria-label', COLOR_NAMES[c]);
  b.setAttribute('aria-pressed', String(c === 0));
  b.addEventListener('click', () => pickColor(c));
  $('colors').append(b);
});
WIDTHS.forEach((width, w) => {
  const b = el('button');
  b.type = 'button';
  b.setAttribute('aria-label', ['Fine brush', 'Medium brush', 'Thick brush', 'Huge brush'][w]);
  b.setAttribute('aria-pressed', String(w === 1));
  const blob = el('i');
  blob.style.setProperty('--d', `${Math.min(width, 26) * 0.8 + 2}px`);
  b.append(blob);
  b.addEventListener('click', () => { pad.width = w; pressed($('widths'), w); });
  $('widths').append(b);
});
$('eraser').addEventListener('click', () => pickColor(pad.color === ERASER ? brush : ERASER));
$('undo').addEventListener('click', () => pad.undo());
$('clear').addEventListener('click', () => pad.clear());

function showInk() {
  const part = pad.left() / pad.ink;
  $('ink').hidden = part > 0.25;
  $('ink').textContent = part > 0 ? `Ink left: ${Math.ceil(part * 100)}%`
    : "You're out of ink. Undo something to draw more.";
}

// ---------------------------------------------------------------- the books

const VERB = { write: 'wrote', draw: 'drew', guess: 'guessed' };
const verb = (page, i) => VERB[i === 0 ? 'write' : page.k === 'draw' ? 'draw' : 'guess'];
const byline = (page, i) => `${nameOf(page.by)} ${verb(page, i)}${page.auto ? ' (ran out of time)' : ''}`;
const owner = b => nameOf(S.books[b][0].by);

function pageItem(page, i, replay) {
  const li = el('li');
  li.append(el('p', 'by', byline(page, i)));
  if (page.k === 'draw') {
    const canvas = el('canvas', 'sheet');
    li.append(canvas);
    // it has no size until it's on the page
    requestAnimationFrame(() => showDrawing(canvas, page.strokes, replay ? 1.4 : 0));
  } else {
    li.append(el('p', 'said', page.text));
  }
  return li;
}

function renderBooks() {
  const st = S.st, album = st.phase === 'album';
  if (!S.books.length) return;
  const [book, shown] = album ? [Math.min(S.tab, S.books.length - 1), Infinity] : st.reveal;
  const pages = S.books[book].slice(0, shown);
  $('books-code').textContent = S.code;
  $('book-count').textContent = album ? 'All the books' : `Book ${book + 1} of ${S.books.length}`;
  $('book-title').textContent = `${owner(book)}'s book`;

  // Add the pages that aren't showing yet; start again for a different book.
  const [was, had] = (S.drawn || '').split(':');
  const list = $('pages');
  let from = +had || 0;
  if (was !== `${album ? 'a' : 'r'}${book}` || from > pages.length) { list.replaceChildren(); from = 0; }
  const turning = !album && from > 0 && from === pages.length - 1;   // one new page, being read out
  pages.slice(from).forEach((page, i) => list.append(pageItem(page, from + i, turning)));
  if (turning) list.lastChild.scrollIntoView({ behavior: 'smooth', block: 'center' });
  else if (from === 0) window.scrollTo(0, 0);
  S.drawn = `${album ? 'a' : 'r'}${book}:${pages.length}`;

  $('tabs').hidden = !album;
  if (album) {
    $('tabs').replaceChildren(...S.books.map((_, b) => {
      const t = el('button', '', owner(b));
      t.type = 'button';
      t.setAttribute('role', 'tab');
      t.setAttribute('aria-selected', String(b === book));
      t.addEventListener('click', () => { S.tab = b; renderBooks(); });
      return t;
    }));
  }
  const last = shown >= S.books[book].length;
  $('next').hidden = album;
  $('next').textContent = !last ? 'Next page' : book + 1 < S.books.length ? 'Next book' : 'Finish';
  $('reveal-note').hidden = album || isHost();
  $('reveal-note').textContent = `${nameOf(st.host)} is turning the pages.`;
  for (const id of ['save', 'again', 'leave']) $(id).hidden = !album;
}

$('next').addEventListener('click', () => send({ t: 'next' }));
$('again').addEventListener('click', () => { S.tab = 0; send({ t: 'again' }); });

// One book as a tall picture, to keep or send on.
function bookPicture(b) {
  const PAD = 40, WIDE = 800, inner = WIDE - PAD * 2, sheetH = inner * H / W;
  const canvas = document.createElement('canvas');
  const measure = canvas.getContext('2d');
  const SAID = '600 34px "Source Serif 4", Georgia, serif', BY = '18px "Source Sans 3", sans-serif';
  const wrap = text => {
    measure.font = SAID;
    const lines = [''];
    for (const word of text.split(/\s+/)) {
      const line = lines[lines.length - 1];
      if (line && measure.measureText(`${line} ${word}`).width > inner) lines.push(word);
      else lines[lines.length - 1] = line ? `${line} ${word}` : word;
    }
    return lines;
  };
  const rows = S.books[b].map((page, i) => ({ page, by: byline(page, i), lines: page.k === 'draw' ? null : wrap(page.text) }));
  const height = row => 30 + (row.lines ? row.lines.length * 42 : sheetH) + 28;
  canvas.width = WIDE;
  canvas.height = PAD + 60 + rows.reduce((h, r) => h + height(r), 0) + PAD - 28;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#fbf7ef';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.textBaseline = 'top';
  ctx.fillStyle = '#2b2620';
  ctx.font = '700 36px "Source Serif 4", Georgia, serif';
  ctx.fillText(`${owner(b)}'s book`, PAD, PAD);
  let y = PAD + 60;
  for (const row of rows) {
    ctx.font = BY;
    ctx.fillStyle = '#6f6355';
    ctx.fillText(row.by, PAD, y);
    y += 30;
    if (row.lines) {
      ctx.font = SAID;
      ctx.fillStyle = '#2b2620';
      row.lines.forEach((line, i) => ctx.fillText(line, PAD, y + i * 42));
    } else {
      const sheet = document.createElement('canvas');
      sheet.width = inner;
      sheet.height = sheetH;
      paint(sheet, row.page.strokes);
      ctx.drawImage(sheet, PAD, y);
      ctx.strokeStyle = '#dccfb8';
      ctx.strokeRect(PAD + 0.5, y + 0.5, inner - 1, sheetH - 1);
    }
    y += height(row) - 30;
  }
  return canvas;
}

$('save').addEventListener('click', () => {
  const b = Math.min(S.tab, S.books.length - 1);
  bookPicture(b).toBlob(blob => {
    const a = el('a');
    a.href = URL.createObjectURL(blob);
    a.download = `sketch-relay-${owner(b).replace(/[^\w-]+/g, '-').toLowerCase() || 'book'}.png`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  }, 'image/png');
});

// ---------------------------------------------------------------- the menu and lobby

const params = new URLSearchParams(location.search);
const roomParam = (params.get('room') || '').toUpperCase().slice(0, 4);
$('name').value = saved.name || '';
$('code').value = roomParam;

function takeName() {
  const n = $('name').value.trim().slice(0, 16);
  if (!n) { $('name').focus(); status('Pick a name first.'); return false; }
  saved.name = n;
  save();
  return true;
}

$('create').addEventListener('click', () => {
  if (!takeName()) return;
  S.code = null;
  connect({ create: true });
});

function joinRoom() {
  if (!takeName()) return;
  const code = $('code').value.trim().toUpperCase();
  if (code.length !== 4) { status('Room codes are four letters.'); return; }
  S.code = null;
  connect({ room: code });
}
$('join').addEventListener('click', joinRoom);
$('code').addEventListener('keydown', e => { if (e.key === 'Enter') joinRoom(); });
$('name').addEventListener('keydown', e => { if (e.key === 'Enter' && $('code').value) joinRoom(); });
$('code').addEventListener('input', () => { $('code').value = $('code').value.toUpperCase().replace(/[^A-Z]/g, ''); });

$('copy').addEventListener('click', () => {
  navigator.clipboard?.writeText($('share').value).then(() => { $('copy').textContent = 'Copied!'; setTimeout(() => { $('copy').textContent = 'Copy'; }, 1500); });
});
$('timer').addEventListener('change', () => send({ t: 'timer', v: $('timer').value }));
$('start').addEventListener('click', () => send({ t: 'start' }));

// Coming back to a room link with a name already saved: straight back in.
if (roomParam && saved.name) connect({ room: roomParam });
else show('menu');

if (params.has('debug')) window.relay = { S, send, get pad() { return pad; } };
