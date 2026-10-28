// Song Guesser: picks a song, plays its clip one instrument at a time, and takes guesses.
import { SONGS, EXTRA } from './songs.js?v=3';
import { arrange, renderPart, mix, CLIP } from './synth.js?v=3';

const STORE = 'song-guesser';
const WEIGHT = { indie: 4, alt: 2, other: 1 };
const RECENT = 15; // songs not repeated until this many others have been played
const $ = id => document.getElementById(id);

// --- saved stats -------------------------------------------------------------------------------
function load() {
  try { return { played: 0, won: 0, streak: 0, best: 0, recent: [], ...JSON.parse(localStorage.getItem(STORE) || '{}') }; } catch (e) { return { played: 0, won: 0, streak: 0, best: 0, recent: [] }; }
}
const stats = load();
function save() { try { localStorage.setItem(STORE, JSON.stringify(stats)); } catch (e) { /* storage unavailable */ } }

// --- the guess list -----------------------------------------------------------------------------
const fold = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, ' ').trim();
const keyOf = (title, artist) => fold(`${title} ${artist}`);
const CHOICES = (() => {
  const all = new Map();
  for (const s of SONGS) all.set(keyOf(s.title, s.artist), { title: s.title, artist: s.artist });
  for (const [artist, titles] of Object.entries(EXTRA)) for (const title of titles) all.set(keyOf(title, artist), { title, artist });
  return [...all.entries()].map(([key, c]) => ({ ...c, key, label: `${c.title} — ${c.artist}` }))
    .sort((a, b) => a.title.localeCompare(b.title));
})();

function search(text) {
  const words = fold(text).split(' ').filter(Boolean);
  if (!words.length) return [];
  const hits = CHOICES.filter(c => words.every(w => c.key.split(' ').some(k => k.startsWith(w)) || c.key.includes(w)));
  // titles starting with what was typed first
  const q = fold(text);
  return hits.sort((a, b) => (fold(b.title).startsWith(q) - fold(a.title).startsWith(q))).slice(0, 40);
}

// --- audio ------------------------------------------------------------------------------------
// pos: where in the clip playback is or will resume, in seconds; dragging: the slider is held
const audio = { ctx: null, src: null, startedAt: 0, raf: 0, token: 0, pos: 0, dragging: false };

async function context() {
  if (!audio.ctx || audio.ctx.state === 'closed') {
    // iPhones mute web audio with the silent switch unless the session says it's playback
    try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch (e) { /* older Safari */ }
    audio.ctx = new (window.AudioContext || window.webkitAudioContext)();
  }
  if (audio.ctx.state !== 'running') {
    try { await audio.ctx.resume(); } catch (e) { /* replaced below */ }
    if (audio.ctx.state !== 'running') {
      // iOS can leave a context stuck after the page was in the background; start a fresh one
      try { audio.ctx.close(); } catch (e) { /* already closed */ }
      audio.ctx = new (window.AudioContext || window.webkitAudioContext)();
      await audio.ctx.resume();
    }
  }
  return audio.ctx;
}

const seek = $('sg-seek');
seek.max = CLIP;
const clock = t => `0:${String(Math.floor(t)).padStart(2, '0')}`;

// Moves the slider and time to t seconds; `remember` also makes it where Play starts.
function show(t, remember = true) {
  t = Math.max(0, Math.min(CLIP, t));
  if (remember) audio.pos = t;
  if (!audio.dragging) seek.value = t;
  seek.style.setProperty('--pos', `${(t / CLIP) * 100}%`);
  seek.setAttribute('aria-valuetext', `${Math.floor(t)} seconds`);
  $('sg-now').textContent = clock(t);
}

// Pauses where it is; `rewind` goes back to the start instead.
function stop(rewind = false) {
  audio.token++; // a play() still waiting on its clip won't start
  if (audio.src) {
    audio.src.onended = null;
    try { audio.src.stop(); } catch (e) { /* not started */ }
    audio.src = null;
  }
  cancelAnimationFrame(audio.raf);
  if (rewind) show(0);
  $('sg-play').textContent = 'Play';
}

function tick() {
  if (!audio.src) return;
  if (!audio.dragging) show(audio.ctx.currentTime - audio.startedAt);
  audio.raf = requestAnimationFrame(tick);
}

// --- a round ------------------------------------------------------------------------------------
let round = null;

function pick() {
  const pool = SONGS.filter(s => !stats.recent.includes(keyOf(s.title, s.artist)));
  const list = pool.length ? pool : SONGS;
  let r = Math.random() * list.reduce((n, s) => n + WEIGHT[s.tier], 0);
  for (const s of list) if ((r -= WEIGHT[s.tier]) < 0) return s;
  return list[list.length - 1];
}

function newRound() {
  stop(true);
  const song = pick();
  round = { song, key: keyOf(song.title, song.artist), arr: arrange(song), stage: 0, guesses: [], over: false, won: false, parts: {}, mixes: {} };
  $('sg-genre').textContent = song.genre;
  $('sg-year').textContent = song.year;
  $('sg-input').value = '';
  $('sg-msg').textContent = '';
  $('sg-result').hidden = true;
  $('sg-form').hidden = false;
  closeList();
  draw();
  // render every stage in the background, first one first, so wrong guesses play straight away
  const r = round;
  (async () => { for (let n = 0; n <= lastStage() && r === round; n++) await clip(n); })().catch(() => {});
}

// The clip with the first n + 1 instruments, rendered and mixed once each.
function clip(n) {
  const r = round;
  if (!r.mixes[n]) {
    r.mixes[n] = (async () => {
      const names = r.arr.order.slice(0, n + 1);
      for (const name of names) {
        if (!r.parts[name]) r.parts[name] = renderPart(name, r.arr.parts[name]);
      }
      const rendered = {};
      for (const name of names) rendered[name] = await r.parts[name];
      const ctx = audio.ctx || { createBuffer: (c, l, sr) => new AudioBuffer({ numberOfChannels: c, length: l, sampleRate: sr }) };
      return mix(ctx, rendered);
    })();
  }
  return r.mixes[n];
}

const lastStage = () => round.arr.order.length - 1;

async function play() {
  if (audio.src) { stop(); return; }
  const r = round, token = ++audio.token;
  const from = audio.pos >= CLIP - 0.1 ? 0 : audio.pos;
  const n = r.over ? lastStage() : r.stage;
  $('sg-play').textContent = '…';
  const ctx = await context();
  const buf = await clip(n);
  if (token !== audio.token) return;
  const src = ctx.createBufferSource();
  src.buffer = buf;
  src.connect(ctx.destination);
  src.onended = () => { if (audio.src === src) stop(true); };
  audio.src = src;
  const at = ctx.currentTime + 0.05;
  audio.startedAt = at - from;
  src.start(at, from, CLIP + 0.6 - from);
  $('sg-play').textContent = 'Pause';
  tick();
}

function draw() {
  const r = round;
  const stages = $('sg-stages');
  stages.textContent = '';
  r.arr.order.forEach((name, i) => {
    const li = document.createElement('li');
    const shown = i <= r.stage || r.over;
    const span = document.createElement('span');
    span.textContent = shown ? r.arr.parts[name].label : '?';
    li.appendChild(span);
    li.className = [shown && 'on', i === r.stage && !r.over && i > 0 && 'new', r.guesses[i] && 'miss'].filter(Boolean).join(' ');
    stages.appendChild(li);
  });
  const hist = $('sg-history');
  hist.textContent = '';
  for (const g of r.guesses) {
    const li = document.createElement('li');
    li.textContent = g.skip ? 'Skipped' : g.label;
    if (g.skip) li.className = 'skip';
    hist.appendChild(li);
  }
  $('sg-skip').textContent = r.stage === lastStage() ? 'Give up' : 'Skip';
  const pct = stats.played ? Math.round((stats.won / stats.played) * 100) : 0;
  $('sg-stats').textContent = stats.played
    ? `Played ${stats.played} · won ${pct}% · streak ${stats.streak} (best ${stats.best})`
    : '';
}

function wrong(guess) {
  const r = round;
  r.guesses[r.stage] = guess;
  if (r.stage === lastStage()) return finish(false);
  r.stage++;
  draw();
  stop();
  safePlay();
}

function finish(won) {
  const r = round;
  r.over = true;
  r.won = won;
  stats.played++;
  if (won) { stats.won++; stats.streak++; stats.best = Math.max(stats.best, stats.streak); } else stats.streak = 0;
  stats.recent = [r.key, ...stats.recent.filter(k => k !== r.key)].slice(0, RECENT);
  save();
  const s = r.song, used = r.stage + 1, total = r.arr.order.length;
  const res = $('sg-result');
  res.className = `sg-result${won ? '' : ' lost'}`;
  res.innerHTML = '';
  const h = document.createElement('h2');
  h.textContent = won ? `Got it: ${s.title}` : `It was ${s.title}`;
  const p = document.createElement('p');
  p.textContent = `${s.artist}, ${s.year}. ${won ? (used === 1 ? 'With one instrument!' : `With ${used} of ${total} instruments.`) : 'Better luck with the next one.'} The clip was the ${s.section.toLowerCase()}.`;
  const next = document.createElement('button');
  next.type = 'button';
  next.className = 'sg-btn';
  next.textContent = 'Next song';
  next.addEventListener('click', newRound);
  res.append(h, p, next);
  res.hidden = false;
  $('sg-form').hidden = true;
  closeList();
  draw();
  stop(true);
  safePlay();
  next.focus();
}

// --- the search box ----------------------------------------------------------------------------
const input = $('sg-input'), list = $('sg-list');
let results = [], active = -1, chosen = null;

function closeList() {
  list.hidden = true;
  input.setAttribute('aria-expanded', 'false');
  input.removeAttribute('aria-activedescendant');
  active = -1;
}

function showList() {
  list.textContent = '';
  // with no matches, say so below the box rather than in a dropdown covering the buttons
  $('sg-msg').textContent = input.value.trim() && !results.length ? 'No songs match.' : '';
  if (!results.length) return closeList();
  results.forEach((c, i) => {
    const li = document.createElement('li');
    li.id = `sg-opt-${i}`;
    li.setAttribute('role', 'option');
    li.setAttribute('aria-selected', String(i === active));
    li.append(c.title, ' ');
    const small = document.createElement('small');
    small.textContent = c.artist;
    li.appendChild(small);
    li.addEventListener('mousedown', e => { e.preventDefault(); choose(c); });
    list.appendChild(li);
  });
  list.hidden = false;
  input.setAttribute('aria-expanded', 'true');
  if (active >= 0) {
    input.setAttribute('aria-activedescendant', `sg-opt-${active}`);
    $(`sg-opt-${active}`).scrollIntoView({ block: 'nearest' });
  }
}

function choose(c) {
  chosen = c;
  input.value = c.label;
  closeList();
  $('sg-msg').textContent = '';
}

input.addEventListener('input', () => {
  chosen = null;
  results = search(input.value);
  active = results.length ? 0 : -1;
  showList();
});
input.addEventListener('keydown', e => {
  if (list.hidden || !results.length) return;
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault();
    active = (active + (e.key === 'ArrowDown' ? 1 : -1) + results.length) % results.length;
    showList();
  } else if (e.key === 'Enter' && active >= 0) {
    e.preventDefault();
    choose(results[active]);
  } else if (e.key === 'Escape') {
    closeList();
  }
});
input.addEventListener('blur', () => setTimeout(closeList, 100));

$('sg-form').addEventListener('submit', e => {
  e.preventDefault();
  if (!round || round.over) return;
  const typed = fold(input.value.replace('—', ' '));
  const c = chosen || CHOICES.find(x => x.key === typed) || (search(input.value).length === 1 ? search(input.value)[0] : null);
  if (!c) { $('sg-msg').textContent = input.value.trim() ? 'Pick a song from the list.' : 'Type a song or artist to search.'; return; }
  input.value = '';
  chosen = null;
  $('sg-msg').textContent = '';
  if (c.key === round.key) finish(true);
  else wrong({ label: c.label });
});
$('sg-skip').addEventListener('click', () => { if (round && !round.over) wrong({ skip: true }); });
function safePlay() {
  play().catch(err => { console.error(err); stop(); $('sg-msg').textContent = 'The audio didn\'t start; try Play again.'; });
}
$('sg-play').addEventListener('click', safePlay);

// Dragging previews the time; letting go (or a click or arrow key) jumps there, playing or not.
seek.addEventListener('input', () => {
  audio.dragging = true;
  show(+seek.value, false);
});
seek.addEventListener('change', () => {
  audio.dragging = false;
  show(+seek.value);
  if (audio.src) { stop(); safePlay(); }
});

document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });

newRound();
