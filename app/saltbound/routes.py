"""Saltbound's page and its WebSocket."""

from pathlib import Path

from fastapi import APIRouter, WebSocket
from fastapi.responses import FileResponse, JSONResponse

from ..rooms import Refused, page_version, serve
from . import room as R
from . import save as S
from .combat import Invalid

PAGE = Path(__file__).parent.parent / "static" / "games" / "saltbound" / "index.html"
# The page's ?v=: a tab left open across a deploy runs old code against a new server, so it's
# told to reload.
VERSION = page_version(PAGE)

router = APIRouter()


@router.get("/games/saltbound", include_in_schema=False)
def page():
    return FileResponse(PAGE)


@router.get("/games/saltbound/saves", include_in_schema=False)
def saves(token: str = ""):
    """The runs a browser has saved, so the title screen can offer them before joining a room."""
    return JSONResponse(S.list_for(token[:40]), headers={"Cache-Control": "no-store"})


def enter(hello, queue):
    if str(hello.get("v")) != VERSION:
        raise Refused({"t": "reload"})
    room = R.ROOMS.new(lambda code: R.Room(code, bool(hello.get("debug")))) if hello.get("create") else R.ROOMS.find(hello.get("room"))
    if room is None:
        raise Refused({"t": "error", "msg": "There's no room with that code."})
    try:
        return room, room.join(queue, hello.get("name"), hello.get("token"), hello.get("tab"))
    except Invalid as e:
        raise Refused({"t": "error", "msg": str(e)})


@router.websocket("/games/saltbound/ws")
async def socket(ws: WebSocket):
    await serve(ws, enter)
