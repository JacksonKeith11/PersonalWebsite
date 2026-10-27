"""Narrates every uploaded book with Kokoro, one chapter MP3 at a time.

Runs in its own container (see Dockerfile.tts). Order of work: the chapter someone pressed
listen on and the rest of that book, then the newest upload first.
"""

import logging
import os
import time
from pathlib import Path

import lameenc
import numpy as np
from kokoro_onnx import Kokoro

from . import store

VOICE = os.environ.get("TTS_VOICE", "am_michael")
MODEL_DIR = Path(os.environ.get("KOKORO_DIR", "/models"))
RATE = 24000
PAUSE = np.zeros(int(RATE * 0.4), dtype=np.float32)  # between paragraphs
BITRATE = 48  # kbps mono; plenty for speech
BYTES_PER_SECOND = BITRATE * 1000 // 8

log = logging.getLogger("tts")


class Preempted(Exception):
    pass


def _priority() -> tuple[str | None, int]:
    p = store.read_json(store.PRIORITY) or {}
    return p.get("book"), p.get("chapter", 0)


def _wanted_elsewhere(book_id: str, n: int) -> bool:
    """True when someone is waiting to listen to a different chapter that has no audio yet."""
    pri_book, pri_chapter = _priority()
    if (pri_book, pri_chapter) == (book_id, n):
        return False
    pri = store.load_book(pri_book or "")
    return bool(pri) and pri_chapter < len(pri["chapters"]) and pri_chapter not in store.audio_done(pri_book)


def next_job() -> tuple[dict, int] | None:
    pri_book, pri_chapter = _priority()
    books = sorted(store.list_books(), key=lambda b: b["id"] != pri_book)
    for book in books:
        done = store.audio_done(book["id"])
        start = pri_chapter if book["id"] == pri_book else 0
        count = len(book["chapters"])
        for n in [*range(start, count), *range(0, min(start, count))]:
            if n not in done:
                return book, n
    return None


def _encoder() -> lameenc.Encoder:
    enc = lameenc.Encoder()
    enc.set_bit_rate(BITRATE)
    enc.set_in_sample_rate(RATE)
    enc.set_channels(1)
    enc.set_quality(2)
    return enc


def generate(kokoro: Kokoro, book: dict, n: int) -> None:
    folder = store.BOOKS_DIR / book["id"]
    texts = store.read_json(folder / "chapters" / f"{n}.json", [])
    timing = folder / "audio" / f"{n}.json"
    if not texts:
        store.write_json(timing, {"starts": [], "duration": 0})
        return

    # The MP3 grows paragraph by paragraph, and the .partial.json beside it records what's been
    # written, so the reader can start listening right away and paused work resumes where it left off.
    mp3 = folder / "audio" / f"{n}.mp3"
    tmp, partial = store.partial_paths(folder, n)
    state = store.read_json(partial) if tmp.exists() else None
    if state:
        with tmp.open("r+b") as f:
            f.truncate(state["bytes"])  # drop anything written after the last checkpoint
        starts, written = state["starts"], state["bytes"]
    else:
        tmp.write_bytes(b"")
        starts, written = [], 0
    # Constant bitrate, so the file length is the audio length.
    samples = written * RATE // BYTES_PER_SECOND
    enc = _encoder()
    began, began_at, last_status = len(starts), time.time(), 0.0

    def checkpoint() -> None:
        store.write_json(partial, {
            "starts": starts, "duration": round(written / BYTES_PER_SECOND, 3), "bytes": written, "segments": len(texts),
        })

    with tmp.open("ab") as out:
        for i in range(len(starts), len(texts)):
            if not folder.exists():
                raise Preempted  # book was deleted
            if _wanted_elsewhere(book["id"], n):
                tail = enc.flush()
                out.write(tail)
                written += len(tail)
                checkpoint()
                raise Preempted
            if time.time() - last_status > 2:
                done = i - began
                store.write_json(store.WORKER, {
                    "book": book["id"], "chapter": n, "segment": i, "segments": len(texts), "updated": time.time(),
                    "seconds_per_segment": (time.time() - began_at) / done if done else None,
                })
                last_status = time.time()

            starts.append(round(samples / RATE, 3))
            try:
                audio, _ = kokoro.create(texts[i], voice=VOICE, speed=1.0, lang="en-us")
            except Exception:
                log.exception("Couldn't narrate segment %d of %s chapter %d", i, book["id"], n)
                audio = np.zeros(0, dtype=np.float32)
            chunk = np.concatenate([audio.astype(np.float32), PAUSE])
            data = enc.encode((np.clip(chunk, -1, 1) * 32767).astype("<i2").tobytes())
            out.write(data)
            out.flush()
            written += len(data)
            samples += len(chunk)
            checkpoint()
        out.write(enc.flush())
    os.replace(tmp, mp3)
    store.write_json(timing, {"starts": starts, "duration": round(mp3.stat().st_size / BYTES_PER_SECOND, 3)})
    partial.unlink(missing_ok=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("phonemizer").setLevel(logging.ERROR)  # warns on nearly every paragraph
    os.nice(10)  # keep the website responsive while narrating
    kokoro = Kokoro(str(MODEL_DIR / "kokoro-v1.0.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
    log.info("Ready; narrating with %s", VOICE)
    while True:
        job = next_job()
        if not job:
            store.WORKER.unlink(missing_ok=True)
            time.sleep(5)
            continue
        book, n = job
        started = time.time()
        try:
            generate(kokoro, book, n)
            log.info("%s chapter %d/%d done in %.0fs", book["title"], n + 1, len(book["chapters"]), time.time() - started)
        except Preempted:
            log.info("%s chapter %d paused for a listen request", book["title"], n + 1)
        except Exception:
            log.exception("Failed on %s chapter %d", book["id"], n)
            time.sleep(30)


if __name__ == "__main__":
    main()
