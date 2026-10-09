#!/usr/bin/env python3
"""
ASTRA Web Bridge Server
Serves public/ assets and bridges orb_bridge events to browser via WebSocket.
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Set

from aiohttp import web, WSMsgType

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from Brain.orb_bridge import get_orb_bridge

PUBLIC_DIR = PROJECT_ROOT / "public"

# WebSocket clients
ws_clients: Set[web.WebSocketResponse] = set()


async def handle_websocket(request: web.Request) -> web.WebSocketResponse:
    """WebSocket endpoint for real-time orb state updates."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    ws_clients.add(ws)
    print(f"WS client connected ({len(ws_clients)} total)")

    # Send initial state
    bridge = get_orb_bridge()
    await ws.send_json({
        "type": "init",
        "state": bridge.status(),
    })

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    # Handle client messages if needed (e.g., ping)
                    if data.get("type") == "ping":
                        await ws.send_json({"type": "pong"})
                except json.JSONDecodeError:
                    pass
            elif msg.type == WSMsgType.ERROR:
                print(f"WS error: {ws.exception()}")
    finally:
        ws_clients.discard(ws)
        print(f"WS client disconnected ({len(ws_clients)} total)")

    return ws


async def broadcast_orb_event(event: dict) -> None:
    """Broadcast orb event to all connected WebSocket clients."""
    if not ws_clients:
        return
    dead = set()
    for ws in ws_clients:
        try:
            await ws.send_json(event)
        except Exception:
            dead.add(ws)
    for ws in dead:
        ws_clients.discard(ws)


def create_orb_bridge_subscriber() -> None:
    """Subscribe to orb_bridge and forward events to WebSocket clients."""
    bridge = get_orb_bridge()

    def on_event(event: dict) -> None:
        # Schedule broadcast on the event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop (e.g., called from thread), create task
            asyncio.run_coroutine_threadsafe(
                broadcast_orb_event(event), asyncio.get_event_loop()
            )
        else:
            loop.create_task(broadcast_orb_event(event))

    bridge.subscribe(on_event)
    print("Orb bridge subscriber registered")


async def on_startup(app: web.Application) -> None:
    """App startup hook."""
    create_orb_bridge_subscriber()


def create_app() -> web.Application:
    """Create the aiohttp web application."""
    app = web.Application()
    app.on_startup.append(on_startup)

    # Static files
    app.router.add_static("/static/", PUBLIC_DIR, show_index=True)
    app.router.add_get("/", lambda req: web.FileResponse(PUBLIC_DIR / "index.html"))
    app.router.add_get("/ws", handle_websocket)

    # Health check
    async def health(req: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "ws_clients": len(ws_clients)})

    app.router.add_get("/health", health)

    return app


def main() -> None:
    """Run the web server."""
    import argparse
    parser = argparse.ArgumentParser(description="ASTRA Web Bridge Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    print(f"Starting ASTRA Web Bridge on http://{args.host}:{args.port}")
    print(f"Serving static files from {PUBLIC_DIR}")
    print(f"WebSocket endpoint: ws://{args.host}:{args.port}/ws")

    app = create_app()
    web.run_app(app, host=args.host, port=args.port, print=None)


if __name__ == "__main__":
    main()