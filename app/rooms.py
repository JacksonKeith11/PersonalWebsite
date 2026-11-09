"""What the multiplayer games (Frag Arena, Board Brawl, Saltbound, Kingfall) share on the server: the
WebSocket loop, sending to one connection, and rooms looked up by a short code.

Each connection gets an outgoing queue drained by its own writer task, so a slow browser never
holds up the game: the game drops text in the queue (`push`), and a connection that falls too far
behind is hung up (the browser reconnects and gets the full state again).

A game plugs in through `serve(ws, enter)`: `enter(hello, queue)` gets the browser's first message
and returns `(room, player)`, where `room.handle(player, msg)` takes each later message and
`room.leave(player, queue)` is called when the socket closes. To turn the browser away, raise
`Refused` with the message to send it.
"""

import asyncio
import json
import logging
import re
import secrets
import time
from pathlib import Path

from fastapi import WebSocket, WebSocketDisconnect

log = logging.getLogger("rooms")

CODE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # no I or O: codes get read aloud


def clean(text, n):
    """Printable text from a browser, trimmed and at most n characters ("" if it isn't text)."""
    if isinstance(text, int):
        text = str(text)
    if not isinstance(text, str):
        return ""
    return "".join(ch for ch in text if ch.isprintable()).strip()[:n]


def dumps(data):
    return json.dumps(data, separators=(",", ":"))


def push(queue, data, who="", game="game"):
    """Queue a message (dict or ready-made text) for one connection. If its queue is full the
    connection is hung up and this returns False: the caller marks the player as closing."""
    try:
        queue.put_nowait(data if isinstance(data, str) else dumps(data))
        return True
    except asyncio.QueueFull:
        log.info("%s: dropping %s, send queue full", game, who)
        hang_up(queue)
        return False


def hang_up(queue):
    """Empty a connection's queue and tell its writer to close the socket."""
    while not queue.empty():
        queue.get_nowait()
    queue.put_nowait(None)


def page_version(page: Path):
    """A game page's ?v= (its asset version): a tab opened before a deploy runs the old code
    against the new server, so the socket tells it to reload."""
    return re.search(r"\?v=(\d+)", page.read_text()).group(1)


class Refused(Exception):
    """Turn a connection away: `msg` (a dict) is sent before the socket closes."""

    def __init__(self, msg):
        super().__init__(msg)
        self.msg = msg


class Codes:
    """Rooms by four-letter code. A room sets `empty_since` (time.monotonic()) when its last player
    leaves, and is forgotten `keep` seconds later."""

    def __init__(self, keep):
        self.keep = keep
        self.rooms = {}

    def sweep(self):
        now = time.monotonic()
        for code in [c for c, r in self.rooms.items() if r.empty_since and now - r.empty_since > self.keep]:
            del self.rooms[code]

    def new(self, make):
        """A room with a fresh code: `make(code)` builds it."""
        self.sweep()
        while True:
            code = "".join(secrets.choice(CODE_LETTERS) for _ in range(4))
            if code not in self.rooms:
                self.rooms[code] = make(code)
                return self.rooms[code]

    def find(self, code):
        self.sweep()
        return self.rooms.get(clean(code, 8).upper())


async def _writer(ws: WebSocket, queue: asyncio.Queue):
    while True:
        text = await queue.get()
        if text is None:
            await ws.close()
            return
        await ws.send_text(text)


async def serve(ws: WebSocket, enter, queue_size=200, max_text=4000):
    """Run one game connection until it closes. Messages longer than `max_text`, and anything
    that isn't a JSON object, are ignored."""
    await ws.accept()
    room = player = writer = None
    queue = asyncio.Queue(maxsize=queue_size)
    try:
        hello = json.loads(await asyncio.wait_for(ws.receive_text(), 10))
        if not isinstance(hello, dict):
            return
        try:
            room, player = enter(hello, queue)
        except Refused as e:
            await ws.send_text(dumps(e.msg))
            await ws.close()
            return
        writer = asyncio.create_task(_writer(ws, queue))
        while True:
            text = await ws.receive_text()
            if len(text) > max_text:
                continue
            try:
                msg = json.loads(text)
            except ValueError:
                continue
            if isinstance(msg, dict):
                room.handle(player, msg)
    except (WebSocketDisconnect, TimeoutError, ValueError, RuntimeError):
        pass
    finally:
        if player is not None:
            room.leave(player, queue)
        if writer is not None:
            writer.cancel()
