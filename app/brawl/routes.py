"""Board Brawl's page and its WebSocket."""

from pathlib import Path

from fastapi import APIRouter, WebSocket
from fastapi.responses import FileResponse

from ..rooms import Refused, page_version, serve
from . import game

PAGE = Path(__file__).parent.parent / "static" / "games" / "brawl" / "index.html"
# A tab opened before a deploy runs the old game code, which can't play the new server's
# minigames, so it's told to reload.
VERSION = page_version(PAGE)

router = APIRouter()


@router.get("/games/board-brawl", include_in_schema=False)
def page():
    return FileResponse(PAGE)


def enter(hello, queue):
    if str(hello.get("v")) != VERSION:
        raise Refused({"t": "reload"} if hello.get("v") else
                      {"t": "error", "msg": "Board Brawl has just been updated: reload the page to play."})
    room = game.ROOMS.new(game.Room) if hello.get("create") else game.ROOMS.find(hello.get("room"))
    if room is None:
        raise Refused({"t": "error", "msg": "There's no room with that code."})
    return room, room.join(queue, hello.get("name"), hello.get("token"), hello.get("tab"))


@router.websocket("/games/board-brawl/ws")
async def socket(ws: WebSocket):
    await serve(ws, enter, max_text=2000)
