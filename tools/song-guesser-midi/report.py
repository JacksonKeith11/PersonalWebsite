"""Every 4-bar block of a MIDI: time, which tracks play, the top line of each melodic track, lyrics."""
import re, sys, warnings
import numpy as np, pretty_midi
warnings.filterwarnings('ignore')
N = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
pm = pretty_midi.PrettyMIDI(sys.argv[1])
tracks = [int(x) for x in sys.argv[2].split(',')] if len(sys.argv) > 2 and sys.argv[2] else None
if tracks is None:
    def prior(i):
        t = pm.instruments[i]
        if t.is_drum or not t.notes or (32 <= t.program <= 39) or 'bass' in (t.name or '').lower():
            return -99
        p = [n.pitch for n in t.notes]
        ns = sorted(t.notes, key=lambda n: n.start)
        mono = np.mean([a.end <= b.start + 0.05 for a, b in zip(ns, ns[1:])]) if len(ns) > 1 else 1
        return 3 * bool(re.search(r'vocal|voice|vox|melod|sing|lyric|lead voc', (t.name or '').lower())) + 2 * mono - abs(np.mean(p) - 68) / 12 - 2 * (len(p) < 40)
    tracks = sorted(range(len(pm.instruments)), key=prior, reverse=True)[:3]
beats = pm.get_beats()
print('tracks:', '; '.join(f"{i}:{(t.name or '')[:14]}/p{t.program}{'D' if t.is_drum else ''}/{len(t.notes)}" for i, t in enumerate(pm.instruments) if t.notes))
lyr = [(l.time, l.text) for l in pm.lyrics]
mel = [i for i in (tracks or [])]
for b in range(0, len(beats) - 4, 16):
    t0, t1 = beats[b], beats[min(b + 16, len(beats) - 1)]
    words = ''.join(t for tt, t in lyr if t0 <= tt < t1).replace('\r', ' ').replace('\n', ' ')
    row = f"bar {b // 4:3d} {t0:6.1f}s"
    for i in mel:
        ns = sorted((n for n in pm.instruments[i].notes if t0 <= n.start < t1), key=lambda n: n.start)
        top = []
        for n in ns:
            if top and abs(top[-1][0] - n.start) < 0.03:
                continue
            top.append((n.start, n.pitch))
        row += f" | {i}: " + ' '.join(N[p % 12] for _, p in top[:16])
    if words.strip():
        row += f" | {re.sub(' +', ' ', words.strip())[:70]}"
    print(row)
