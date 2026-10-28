"""Pull a song's chorus out of a MIDI transcription, checked against the real recording.

usage: extract.py OUT.json TITLE ARTIST MIDI [PREVIEW.wav]
Writes the arrangement (in songs.js notation) plus diagnostics. Optional environment overrides,
for when the automatic picks are wrong (see overrides.json): BAR (the chorus's first bar), MEL
(the melody's track index), CH (the chords' track index), SEMIS (transpose by this many semitones),
BARS (how many bars to take, when the chorus is shorter than the clip; it loops).
Needs pretty_midi and librosa.
"""
import json, math, os, re, sys, warnings
import numpy as np
import pretty_midi
import librosa

warnings.filterwarnings('ignore')
CLIP = 15.0
NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
note_name = lambda m: f'{NAMES[m % 12]}{m // 12 - 1}'
norm = lambda x: re.sub(r'[^a-z0-9 ]+', '', x.lower())

out_path, title, artist, midi_path = sys.argv[1:5]
wav = sys.argv[5] if len(sys.argv) > 5 else None
pm = pretty_midi.PrettyMIDI(midi_path)
beats = pm.get_beats()
downbeats = pm.get_downbeats()
ts = pm.time_signature_changes[0] if pm.time_signature_changes else None
meter = ts.numerator if ts and ts.denominator == 4 and ts.numerator in (3, 4) else 4
info = {'title': title, 'midi': midi_path.split('/')[-1]}


def beat_of(t):
    """Seconds -> fractional beat index on the MIDI's own beat grid."""
    i = np.searchsorted(beats, t, side='right') - 1
    i = max(0, min(i, len(beats) - 2))
    return i + (t - beats[i]) / (beats[i + 1] - beats[i])


# --- sort the tracks ------------------------------------------------------------------------------
tracks = [ins for ins in pm.instruments if ins.notes]
drums = [i for i in tracks if i.is_drum]
pitched = [i for i in tracks if not i.is_drum]


def mono(ins):
    """Share of notes that don't overlap the next one: 1.0 is a single line."""
    ns = sorted(ins.notes, key=lambda n: n.start)
    if len(ns) < 2:
        return 1.0
    return float(np.mean([a.end <= b.start + 0.05 for a, b in zip(ns, ns[1:])]))


def stats(ins):
    p = [n.pitch for n in ins.notes]
    return {'mean': float(np.mean(p)), 'n': len(p), 'mono': mono(ins), 'name': (ins.name or '').lower(), 'prog': ins.program}


VOCAL = re.compile(r'vocal|voice|vox|melod|sing|lyric|lead voc|tune')
bass_cands = [i for i in pitched if (32 <= i.program <= 39 or 'bass' in (i.name or '').lower()) and stats(i)['mean'] < 55]
bass = max(bass_cands, key=lambda i: len(i.notes)) if bass_cands else None
rest = [i for i in pitched if i is not bass]


def melody_prior(ins):
    s = stats(ins)
    score = 0.0
    if VOCAL.search(s['name']):
        score += 3
    if 'harmony' in s['name'] or 'backing' in s['name'] or 'bgv' in s['name']:
        score -= 2
    score += 2 * s['mono']
    score -= abs(s['mean'] - 68) / 12
    if s['n'] < 40:
        score -= 2
    if 112 <= s['prog'] <= 127:
        score -= 2
    return score


# --- the real recording: where the preview sits, its key and its sung pitch -----------------------
fps = 10.0
midi_chroma = pm.get_chroma(fs=fps)
midi_chroma = midi_chroma + 1e-3 * (midi_chroma.max() or 1)
midi_chroma = midi_chroma / np.linalg.norm(midi_chroma, axis=0, keepdims=True)
align = None
f0_times = f0 = None
if wav:
    y, sr = librosa.load(wav, sr=22050, mono=True)
    hop = int(sr / fps)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
    chroma = chroma + 1e-3
    chroma = chroma / np.linalg.norm(chroma, axis=0, keepdims=True)
    # the key: compare the record's overall pitch-class profile with the MIDI's
    rec_prof = chroma.mean(axis=1)
    midi_prof = midi_chroma.mean(axis=1)
    shift = int(np.argmax([np.corrcoef(np.roll(midi_prof, k), rec_prof)[0, 1] for k in range(12)]))
    # where the preview sits: slide it along the MIDI at a range of tempo ratios
    Y = np.roll(midi_chroma, shift, axis=0)
    n_p, n_m = chroma.shape[1], Y.shape[1]
    best = (-1, 0, 1.0)
    for r in np.linspace(0.8, 1.25, 28):
        idx = (np.arange(n_p) * r).astype(int)
        if idx[-1] >= n_m:
            continue
        for off in range(0, n_m - idx[-1]):
            sim = float(np.mean(np.sum(chroma * Y[:, off + idx], axis=0)))
            if sim > best[0]:
                best = (sim, off, r)
    sim, off, r = best
    cost = 1 - sim
    wp = [(i, off + int(i * r)) for i in range(n_p)]
    semis = shift if shift <= 6 else shift - 12
    align = {'cost': round(float(cost), 3), 'transpose': semis,
             'midi_start': float(wp[0][1] / fps), 'midi_end': float(wp[-1][1] / fps),
             'path': [(float(a / fps), float(b / fps)) for a, b in wp[::5]]}
    # the sung (or most prominent) pitch of the record, to check which MIDI line is the melody
    f0, voiced, _ = librosa.pyin(y, fmin=80, fmax=900, sr=sr, frame_length=2048, hop_length=512)
    f0_times = librosa.times_like(f0, sr=sr, hop_length=512)
    f0 = np.where(voiced, f0, np.nan)
    # librosa's tempo estimate snaps to coarse steps (112.3, 117.5, 123...): fit a line through the
    # beats it tracked instead, on a finer hop
    oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=128)
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=128)
    tempo = float(np.atleast_1d(tempo)[0])
    bt = librosa.frames_to_time(beat_frames, sr=sr, hop_length=128)
    if len(bt) > 8:
        tempo = 60.0 / float(np.polyfit(np.arange(len(bt)), bt, 1)[0])
    if os.environ.get('SEMIS'): semis = int(os.environ['SEMIS'])
    align['audio_tempo'] = round(tempo, 1)


def record_to_midi_time(t):
    xs = np.array([a for a, b in align['path']])
    ys = np.array([b for a, b in align['path']])
    return float(np.interp(t, xs, ys))


def melody_agreement(ins, t0, t1):
    """Share of the record's voiced frames whose pitch class the track is playing at that moment."""
    if f0 is None:
        return None
    hit = tot = 0
    for t, f in zip(f0_times, f0):
        if np.isnan(f):
            continue
        mt = record_to_midi_time(t)
        if not (t0 <= mt <= t1):
            continue
        pc = (int(round(librosa.hz_to_midi(f))) - align['transpose']) % 12
        playing = {n.pitch % 12 for n in ins.notes if n.start <= mt < n.end}
        if playing:
            tot += 1
            hit += pc in playing
    return hit / tot if tot > 20 else None


# --- pick the melody --------------------------------------------------------------------------------
cands = sorted(rest, key=melody_prior, reverse=True)[:5]
import os
if os.environ.get('MEL'):
    cands = [pm.instruments[int(os.environ['MEL'])]]
if align:
    lo, hi = align['midi_start'], align['midi_end']
    scored = []
    for c in cands:
        a = melody_agreement(c, lo, hi)
        scored.append(((a if a is not None else 0) * 4 + melody_prior(c), a, c))
    scored.sort(key=lambda x: -x[0])
    melody, info['melody_match'] = scored[0][2], scored[0][1]
    info['melody_candidates'] = [((c.name or f'prog {c.program}'), None if a is None else round(a, 2)) for _, a, c in scored]
else:
    melody = cands[0] if cands else None
    info['melody_match'] = None
info['melody_track'] = melody.name if melody else None

# --- find the chorus: lyrics with the title, the most repeated melody, the preview ---------------
bar_len = meter
n_bars = int(len(beats) // bar_len)
bar_starts = [beats[i * bar_len] for i in range(n_bars)]


def sig(i, bars=4):
    t0 = bar_starts[i]
    t1 = bar_starts[min(i + bars, n_bars - 1)] if i + bars < n_bars else pm.get_end_time()
    b0 = beat_of(t0)
    return {(round((beat_of(n.start) - b0) * 2) / 2, n.pitch) for n in melody.notes if t0 <= n.start < t1}


score = np.zeros(n_bars)
if melody:
    sigs = [sig(i) for i in range(n_bars)]
    for i in range(n_bars):
        if len(sigs[i]) < 6:
            score[i] = -9
            continue
        for j in range(n_bars):
            if abs(i - j) >= 4 and sigs[j]:
                inter = len(sigs[i] & sigs[j])
                if inter / max(len(sigs[i] | sigs[j]), 1) >= 0.6:
                    score[i] += 1
lyr = [(l.time, norm(l.text)) for l in pm.lyrics]
title_words = [w for w in norm(re.sub(r'\(.*?\)', '', title)).split() if w]
title_hits = []
if lyr and title_words:
    text, times = '', []
    for t, w in lyr:
        for ch in w:
            text += ch
            times.append(t)
    flat = re.sub(r'\s+', '', text)
    flat_times = [t for t, ch in zip(times, text) if not ch.isspace()]
    key = ''.join(title_words)
    for m in re.finditer(re.escape(key), flat):
        title_hits.append(flat_times[m.start()])
info['title_in_lyrics'] = len(title_hits)
for i in range(n_bars):
    t0, t1 = bar_starts[i], bar_starts[i] + CLIP
    two_bars = bar_starts[min(i + 2, n_bars - 1)] - t0 if i + 2 < n_bars else 4.0
    if any(t0 - 0.2 <= h < t0 + two_bars for h in title_hits):
        score[i] += 3  # the title line opens (or nearly opens) the window
    elif any(t0 <= h < t0 + CLIP * 0.6 for h in title_hits):
        score[i] += 1
    if align and align['midi_start'] - 2 <= t0 <= align['midi_end'] - CLIP * 0.5:
        score[i] += 1.5
    score[i] -= 0.02 * i  # prefer the first chorus
    song_len = pm.get_end_time()
    if t0 < 0.12 * song_len or t0 > 0.8 * song_len:
        score[i] -= 4  # intros and outros
import os
best_bar = int(os.environ['BAR']) if os.environ.get('BAR') else int(np.argmax(score))
t_start = bar_starts[best_bar]
info['chorus_bar'] = best_bar
info['chorus_time'] = round(float(t_start), 1)

# --- tempo, transposition and the window ----------------------------------------------------------
b_start = best_bar * bar_len
local = beats[b_start:b_start + 16]
spb = float(np.median(np.diff(local))) if len(local) > 2 else 0.5
bpm = 60.0 / spb
if align and align.get('audio_tempo'):
    at = align['audio_tempo']
    for k in (0.5, 1, 2):  # fan MIDIs are often a few percent off the record's tempo
        if abs(at * k - bpm) / bpm < 0.10:
            bpm = at * k
bars = math.ceil(CLIP * bpm / 60 / bar_len)
if os.environ.get('BARS'):
    bars = int(os.environ['BARS'])  # a short chorus: take just its bars and let the clip loop them
n_beats = bars * bar_len
semis = align['transpose'] if align and align['cost'] < 0.5 else 0
if os.environ.get('SEMIS'):
    semis = int(os.environ['SEMIS'])  # set by hand when the record comparison is wrong
info.update({'bpm': round(bpm, 1), 'bars': bars, 'transpose': semis, 'align': {k: v for k, v in (align or {}).items() if k != 'path'}})


def notes_in(ins):
    """Notes in the window as (onset beat, length beats, pitch), quantized to sixteenths."""
    res = []
    for n in ins.notes:
        b = beat_of(n.start) - b_start
        if -0.1 <= b < n_beats - 0.01:  # a note a hair before the bar line still belongs to it
            e = min(beat_of(n.end) - b_start, n_beats)
            q0 = max(0.0, round(b * 4) / 4)
            if q0 >= n_beats:
                continue  # rounds onto the next bar, past the clip
            q1 = min(n_beats, max(q0 + 0.25, round(e * 4) / 4))
            res.append((q0, q1 - q0, n.pitch + semis, n.velocity))
    return res


def fmt_len(x):
    s = f'{x:.2f}'.rstrip('0').rstrip('.')
    return s[1:] if s.startswith('0.') else s


def to_line(ns, pick=max, lo=None, hi=None, legato=0.0):
    """A single line: one pitch per onset (the top, or the bottom for a bass)."""
    by = {}
    for b, l, p, v in ns:
        by.setdefault(b, []).append((p, l))
    onsets = sorted(by)
    toks, at = [], 0.0
    for i, b in enumerate(onsets):
        if b > at + 1e-6:
            toks.append(f'-:{fmt_len(b - at)}')
        p, l = pick(by[b])
        nxt = onsets[i + 1] if i + 1 < len(onsets) else n_beats
        if nxt - (b + l) <= legato:
            l = nxt - b  # sung lines join up across short gaps
        l = max(0.25, min(l, nxt - b, n_beats - b))
        while lo is not None and p < lo:
            p += 12
        while hi is not None and p > hi:
            p -= 12
        toks.append(f'{note_name(p)}:{fmt_len(l)}')
        at = b + l
    if at < n_beats - 1e-6:
        toks.append(f'-:{fmt_len(n_beats - at)}')
    return ' '.join(toks), len(onsets)


def to_chords(ns):
    by = {}
    for b, l, p, v in ns:
        by.setdefault(b, []).append((p, l))
    onsets = sorted(by)
    toks, at = [], 0.0
    for i, b in enumerate(onsets):
        if b > at + 1e-6:
            toks.append(f'-:{fmt_len(b - at)}')
        ps = sorted({p for p, _ in by[b]})
        ps = sorted({p + 12 * max(0, math.ceil((45 - p) / 12)) for p in ps})
        ps = sorted({p - 12 * max(0, math.ceil((p - 84) / 12)) for p in ps})  # nothing above C6
        if len(ps) > 4:
            ps = [ps[0], ps[len(ps) // 3], ps[2 * len(ps) // 3], ps[-1]]
        nxt = onsets[i + 1] if i + 1 < len(onsets) else n_beats
        l = max(0.25, min(max(x for _, x in by[b]), nxt - b, n_beats - b))
        toks.append('+'.join(note_name(p) for p in ps) + f':{fmt_len(l)}')
        at = b + l
    if at < n_beats - 1e-6:
        toks.append(f'-:{fmt_len(n_beats - at)}')
    return ' '.join(toks), len(onsets)


DRUM_MAP = {35: 'k', 36: 'k', 37: 'r', 38: 's', 40: 's', 39: 'c', 42: 'h', 44: 'h', 46: 'o', 49: 'y', 57: 'y', 52: 'y', 55: 'y',
            51: 'h', 59: 'h', 53: 'h', 41: 't', 43: 't', 45: 't', 47: 't', 48: 't', 50: 't', 54: 'z', 69: 'z', 70: 'z', 82: 'z', 56: 'r', 75: 'r', 76: 'r', 77: 'r'}


def to_drums(ins_list):
    steps = n_beats * 4
    lanes = {}
    for ins in ins_list:
        for b, l, p, v in notes_in(ins):
            d = DRUM_MAP.get(p - semis)
            if not d:
                continue
            i = int(round(b * 4))
            if 0 <= i < steps:
                lane = lanes.setdefault(d, ['.'] * steps)
                c = 'X' if v >= 112 else 'g' if v < 55 else 'x'
                if lane[i] == '.' or c == 'X':
                    lane[i] = c
    if not lanes:
        return None
    return {'bars': bars, **{k: ''.join(v) for k, v in lanes.items()}}


def inst_for(ins, default):
    p = ins.program
    if 0 <= p <= 7: return 'piano'
    if 8 <= p <= 15: return 'bell'
    if 16 <= p <= 23: return 'organ'
    if p in (24, 25): return 'guitar'
    if 26 <= p <= 28: return 'clean'
    if 29 <= p <= 31: return 'dist'
    if 40 <= p <= 51: return 'strings'
    if 56 <= p <= 71: return 'horn'
    if 72 <= p <= 79: return 'whistle'
    if 80 <= p <= 87: return 'square'
    if 88 <= p <= 103: return 'synth'
    return default


song = {'bpm': round(bpm), 'meter': meter if meter != 4 else None, 'fill': False, 'crash': False}
if drums:
    song['drums'] = to_drums(drums)
if bass:
    line, n = to_line(notes_in(bass), pick=min, lo=28, hi=55)
    if n >= 4:
        song['bass'] = line
if melody:
    line, n = to_line(notes_in(melody), lo=48, hi=84, legato=0.5)
    info['melody_notes'] = n
    song['melody'] = {'notes': line, **({} if VOCAL.search((melody.name or '').lower()) or True else {})}
# chords: the busiest polyphonic track left; riff: the busiest single line left
others = [i for i in rest if i is not melody]
in_win = lambda ins: len(notes_in(ins))
poly = sorted([i for i in others if mono(i) < 0.75 and in_win(i) >= 4], key=in_win, reverse=True)
if os.environ.get('CH'):
    poly = [pm.instruments[int(os.environ['CH'])]]  # set by hand
short = lambda ins: np.mean([l for _, l, _, _ in notes_in(ins)] or [9]) <= 1.0  # a riff moves; held notes are pads
is_bass = lambda ins: 32 <= ins.program <= 39 or re.search(r'bass|bas\b|basgit', (ins.name or '').lower())
mel_hits = {(b, p % 12) for b, _, p, _ in notes_in(melody)} if melody else set()
# a second vocal or a harmony line that shadows the melody isn't a riff
doubles = lambda ins: np.mean([(b, p % 12) in mel_hits or any((b, (p + k) % 12) in mel_hits for k in (3, 4, 8, 9)) for b, _, p, _ in notes_in(ins)] or [0]) > 0.5
lines = sorted([i for i in others if not is_bass(i) and not doubles(i) and mono(i) >= 0.75 and in_win(i) >= 12 and short(i) and i not in poly[:1]], key=in_win, reverse=True)
if poly and 'bass' not in song:
    # no bass track: the bottom of the chords stands in for one
    line, n = to_line(notes_in(poly[0]), pick=min, lo=28, hi=50)
    if n >= 4:
        song['bass'] = line
        info['bass_from_chords'] = True
if poly:
    text, n = to_chords(notes_in(poly[0]))
    song['guitar'] = {'inst': inst_for(poly[0], 'guitar'), 'notes': text}
    info['chords_track'] = poly[0].name or f'prog {poly[0].program}'
else:
    song['guitar'] = None
if lines:
    line, n = to_line(notes_in(lines[0]), lo=48, hi=88)
    song['riff'] = {'inst': inst_for(lines[0], 'lead'), 'notes': line}
    info['riff_track'] = lines[0].name or f'prog {lines[0].program}'
song = {k: v for k, v in song.items() if v is not None}
json.dump({'info': info, 'song': song}, open(out_path, 'w'), indent=1)
print(json.dumps(info))
