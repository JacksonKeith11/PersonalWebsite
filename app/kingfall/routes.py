"""Kingfall's page and its WebSocket."""

from pathlib import Path

from fastapi import APIRouter, WebSocket
from fastapi.responses import FileResponse

from ..rooms import Refused, page_version, serve
from . import room as R

PAGE = Path(__file__).parent.parent / "static" / "games" / "kingfall" / "index.html"
VERSION = page_version(PAGE)

router = APIRouter()


@router.get("/games/kingfall", include_in_schema=False)
def page():
    return FileResponse(PAGE)


def enter(hello, queue):
    if str(hello.get("v")) != VERSION:
        raise Refused({"t": "reload"})
    room = R.ROOMS.new(R.Room) if hello.get("create") else R.ROOMS.find(hello.get("room"))
    if room is None:
        raise Refused({"t": "error", "msg": "There's no room with that code."})
    return room, room.join(queue, hello.get("token"), hello.get("tab"))


@router.websocket("/games/kingfall/ws")
async def socket(ws: WebSocket):
    await serve(ws, enter)
