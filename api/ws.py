from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/events")
async def events(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            await ws.send_text('{"type":"ping","ts":%d}' % __import__("time").time())
            await __import__("asyncio").sleep(5)
    except WebSocketDisconnect:
        pass
