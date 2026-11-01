"""Frag Arena's page and its WebSocket."""

from pathlib import Path

from fastapi import APIRouter, WebSocket
from fastapi.responses import FileResponse

from ..rooms import Refused, serve
from .game import GAME

PAGE = Path(__file__).parent.parent / "static" / "games" / "arena" / "index.html"

router = APIRouter()


@router.get("/games/frag-arena", include_in_schema=False)
def page():
    return FileResponse(PAGE)


def enter(hello, queue):
    player = GAME.join(queue, hello.get("name"), hello.get("token"), hello.get("tab"))
    if player is None:
        raise Refused({"t": "full"})
    return GAME, player


@router.websocket("/games/frag-arena/ws")
async def socket(ws: WebSocket):
    await serve(ws, enter, queue_size=90)
