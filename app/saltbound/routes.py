"""Saltbound's page and its WebSocket."""

import asyncio
import json
import re
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from . import room as R
from .combat import Invalid

PAGE = Path(__file__).parent.parent / "static" / "games" / "saltbound" / "index.html"
# The page's ?v=: a tab left open across a deploy runs old code against a new server, so it's
# told to reload.
VERSION = re.search(r"\?v=(\d+)", PAGE.read_text()).group(1)

router = APIRouter()


@router.get("/games/saltbound", include_in_schema=False)
def page():
    return FileResponse(PAGE, headers={"X-Robots-Tag": "noindex"})


async def _writer(ws: WebSocket, queue: asyncio.Queue):
    while True:
        text = await queue.get()
        if text is None:
            await ws.close()
            return
        await ws.send_text(text)


@router.websocket("/games/saltbound/ws")
async def socket(ws: WebSocket):
    await ws.accept()
    room = person = writer = None
    queue = asyncio.Queue(maxsize=200)
    try:
        hello = json.loads(await asyncio.wait_for(ws.receive_text(), 10))
        if not isinstance(hello, dict):
            return
        if str(hello.get("v")) != VERSION:
            await ws.send_text(json.dumps({"t": "reload"}))
            await ws.close()
            return
        room = R.new_room(bool(hello.get("debug"))) if hello.get("create") else R.find_room(hello.get("room"))
        if room is None:
            await ws.send_text(json.dumps({"t": "error", "msg": "There's no room with that code."}))
            await ws.close()
            return
        try:
            person = room.join(queue, hello.get("name"), hello.get("token"), hello.get("tab"))
        except Invalid as e:
            await ws.send_text(json.dumps({"t": "error", "msg": str(e)}))
            await ws.close()
            return
        writer = asyncio.create_task(_writer(ws, queue))
        while True:
            text = await ws.receive_text()
            if len(text) > 4000:
                continue
            try:
                msg = json.loads(text)
            except ValueError:
                continue
            if isinstance(msg, dict):
                room.handle(person, msg)
    except (WebSocketDisconnect, TimeoutError, ValueError, RuntimeError):
        pass
    finally:
        if person is not None:
            room.leave(person, queue)
        if writer is not None:
            writer.cancel()
