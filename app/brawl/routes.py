"""Board Brawl's page and its WebSocket."""

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from . import game

PAGE = Path(__file__).parent.parent / "static" / "games" / "brawl" / "index.html"

router = APIRouter()


@router.get("/games/board-brawl", include_in_schema=False)
def page():
    return FileResponse(PAGE)


async def _writer(ws: WebSocket, queue: asyncio.Queue):
    while True:
        text = await queue.get()
        if text is None:
            await ws.close()
            return
        await ws.send_text(text)


@router.websocket("/games/board-brawl/ws")
async def socket(ws: WebSocket):
    await ws.accept()
    room = player = writer = None
    queue = asyncio.Queue(maxsize=200)
    try:
        hello = json.loads(await asyncio.wait_for(ws.receive_text(), 10))
        if not isinstance(hello, dict):
            return
        room = game.new_room() if hello.get("create") else game.find_room(hello.get("room"))
        if room is None:
            await ws.send_text(json.dumps({"t": "error", "msg": "There's no room with that code."}))
            await ws.close()
            return
        player = room.join(queue, hello.get("name"), hello.get("token"), hello.get("tab"))
        writer = asyncio.create_task(_writer(ws, queue))
        while True:
            text = await ws.receive_text()
            if len(text) > 2000:
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
