# Song Guesser MIDI pipeline

How the songs marked `source: 'midi'` in `songs.js` were made. It runs outside the site and needs
Python with `pretty_midi` and `librosa`, plus Node.

1. **Find a MIDI transcription.** The [Lakh MIDI dataset](https://colinraffel.com/projects/lmd/)'s
   `clean_midi` set (files named `Artist/Title.mid`, up to 2015) and [BitMidi](https://bitmidi.com)
   (its `/api/midi/search?q=` endpoint) covered 39 of the 85 songs. Check the artist: BitMidi
   searches by title and returns covers and namesakes.
2. **Get the record to compare against.** Apple's 30-second iTunes preview (`previewUrl` from
   `https://itunes.apple.com/search?entity=song&term=...`, about 20 searches a minute) decoded to a
   mono WAV with ffmpeg. YouTube refuses downloads from cloud machines, so previews stand in.
3. **Look before trusting the automatic picks.** `python report.py SONG.mid` prints every 4-bar
   block: the top line of the three likeliest melody tracks and any lyrics, so you can spot where
   the chorus starts and which track carries the vocal.
4. **Extract.** `BAR=44 MEL=3 python extract.py out.json "Buddy Holly" Weezer song.mid preview.wav`.
   It transposes to the record's key (comparing pitch-class profiles; Weezer and others tune down a
   half step, which this catches), takes the record's tempo when the MIDI's is within 10%, and
   writes 15 seconds of whole bars, quantized to sixteenths: drums as multi-bar patterns, bass and
   melody as single lines, chords note for note, plus a riff when a busy single-line track is left.
5. **Merge.** `node assemble.mjs done.json` (titles to outputs) rewrites those songs in `songs.js`,
   centring each vocal line in a singable octave. Then run `node tools/song-guesser-check.js`.

`overrides.json` holds the picks made by hand for every song. Songs with no usable vocal track in
their MIDI (Don't Stop Believin') or no MIDI at all keep their hand-written arrangements.
