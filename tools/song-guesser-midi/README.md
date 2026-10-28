# Song Guesser MIDI pipeline

How the songs marked `source: 'midi'` in `songs.js` were made. It runs outside the site and needs
Python with `pretty_midi` and `librosa`, plus Node.

1. **Find a MIDI transcription.** The [Lakh MIDI dataset](https://colinraffel.com/projects/lmd/)'s
   `clean_midi` set (files named `Artist/Title.mid`, up to 2015) and [BitMidi](https://bitmidi.com)
   (its `/api/midi/search?q=` endpoint). Check the artist: BitMidi searches by title and returns
   covers and namesakes. A song usually has several files; prefer one with a track named for the
   vocal (`Vocal`, `Melody`, `Lead voc`...) or with lyrics (karaoke files), which show exactly where
   the chorus is and which track is sung. Songs added later were picked for exactly that: a
   popular song whose MIDI has a clear vocal line.
2. **Get the record to compare against.** A 30-second preview, decoded to a mono WAV with ffmpeg:
   Apple's (`previewUrl` from `https://itunes.apple.com/search?entity=song&term=...`), or Deezer's
   (`preview` from `https://api.deezer.com/search?q=...`) when Apple rate-limits, which it does after
   a dozen or so searches. Skip live takes, remixes, re-recordings and covers ("The Rolling Clones"):
   check the title and artist of what comes back. YouTube refuses downloads from cloud machines.
3. **Look before trusting the automatic picks.** `python report.py SONG.mid` prints every 4-bar
   block: the top line of the three likeliest melody tracks and any lyrics, so you can spot where
   the chorus starts and which track carries the vocal. With lyrics, the track whose notes start
   on the syllables is the vocal, but check it: a bass playing eighths can line up as well, and
   some files are a different version (a Spanish-language Hero, a live Lola). Files whose tracks are
   all program 0 get mislabelled instruments: fix `inst` in `songs.js` afterwards.
4. **Extract.** `BAR=44 MEL=3 python extract.py out.json "Buddy Holly" Weezer song.mid preview.wav`.
   It transposes to the record's key (comparing pitch-class profiles; Weezer and others tune down a
   half step, which this catches), takes the record's tempo when the MIDI's is within 10% (from a
   line fitted through the beats librosa tracks: its own tempo estimate snaps to coarse steps like
   112.3 and 117.5), and writes 15 seconds of whole bars, quantized to sixteenths: drums as
   multi-bar patterns, bass and melody as single lines, chords note for note, plus a riff when a
   busy single-line track is left that isn't a bass or a second vocal shadowing the melody.
   `BARS=4` takes fewer bars when the chorus is shorter than the clip (it loops). When the record
   matches the MIDI poorly (the `sim` it prints under about 0.6), its key guess is unreliable: check
   the MIDI's key yourself and set `SEMIS`; `BPM` sets the tempo when the detected one is off, and
   `CH` picks the chords track when the automatic pick is a backing vocal.
5. **Merge.** `node assemble.mjs done.json` rewrites those songs in `songs.js`, centring each vocal
   line in a singable octave; done.json maps titles to outputs. A song that isn't in `songs.js` yet
   maps to `{ out, artist, year, genre, tier, section }` and is added at the end of `SONGS` (and taken
   out of `EXTRA`). Then run `node tools/song-guesser-check.js`.

`overrides.json` holds the picks made by hand for every song (for the later ones, the Lakh file too).
Songs with no usable vocal track in their MIDI (Don't Stop Believin') or no MIDI at all keep their
hand-written arrangements, without a vocal line.
