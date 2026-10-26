import logging
import threading
import time
import traceback
from functools import partial

from . import db
from .sources import email_inbox, fictionlive, royalroad, xenforo

log = logging.getLogger("serials")

# (name, fetch function, interval in seconds). Email runs first so newly discovered
# Royal Road and fiction.live stories are polled in the same pass. AO3 comes only from email.
SOURCES = [
    ("Email", email_inbox.fetch, 10 * 60),
    ("Royal Road", royalroad.fetch, 30 * 60),
    ("fiction.live", fictionlive.fetch, 30 * 60),
    *[(name, partial(xenforo.fetch, key), 10 * 60) for key, (name, _) in xenforo.FORUMS.items()],
]

_last_run: dict[str, float] = {}


def run_source(name: str) -> None:
    fetch = next(f for n, f, _ in SOURCES if n == name)
    try:
        fetch()
        db.record_status(name, None)
        log.info("%s: ok", name)
    except Exception as e:
        db.record_status(name, f"{type(e).__name__}: {e}")
        log.warning("%s failed\n%s", name, traceback.format_exc())


def _loop() -> None:
    while True:
        for name, _, interval in SOURCES:
            if time.time() - _last_run.get(name, 0) >= interval:
                _last_run[name] = time.time()
                run_source(name)
        time.sleep(60)


def start() -> None:
    threading.Thread(target=_loop, name="serials", daemon=True).start()
