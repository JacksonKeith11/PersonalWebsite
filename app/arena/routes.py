"""Frag Arena's page and its WebSocket."""

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from .game import GAME

PAGE = Path(__file__).parent.parent / "static" / "games" / "arena" / "index.html"

router = APIRouter()


@router.get("/games/frag-arena", include_in_schema=False)
def page():
    return FileResponse(PAGE)


async def _writer(ws: WebSocket, queue: asyncio.Queue):
    while True:
        text = await queue.get()
        if text is None:
            await ws.close()
            return
        await ws.send_text(text)


@router.websocket("/games/frag-arena/ws")
async def socket(ws: WebSocket):
    await ws.accept()
    player = None
    writer = None
    try:
        hello = json.loads(await asyncio.wait_for(ws.receive_text(), 10))
        queue = asyncio.Queue(maxsize=90)
        player = GAME.join(queue, hello.get("name") if isinstance(hello, dict) else "")
        if player is None:
            await ws.send_text(json.dumps({"t": "full"}))
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
            GAME.handle(player, msg)
    except (WebSocketDisconnect, TimeoutError, ValueError, RuntimeError):
        pass
    finally:
        if player is not None:
            GAME.leave(player)
        if writer is not None:
            writer.cancel()
