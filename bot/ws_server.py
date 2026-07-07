"""
WebSocket server — broadcasts real-time queue updates to the Next.js dashboard.

Uses FastAPI with native WebSocket support.
Also provides HTTP REST endpoints for initial state loading.
"""

import asyncio
import json
import logging
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import Config
from .queue_manager import video_queue
from .ram_monitor import log_ram_status

logger = logging.getLogger(__name__)

# --- FastAPI Application ---
app = FastAPI(title="Video Thumbnail Bot API", version="1.0.0")

# CORS — allow the Next.js dashboard to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Connected WebSocket clients ---
connected_clients: Set[WebSocket] = set()


async def broadcast_state() -> None:
    """Broadcast current queue state to all connected WebSocket clients."""
    if not connected_clients:
        return

    state = video_queue.get_full_status()
    ram = log_ram_status()

    message = json.dumps({
        "type": "queue_update",
        "data": state,
        "ram": ram,
    })

    disconnected = set()
    for ws in connected_clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)

    # Clean up disconnected clients
    for ws in disconnected:
        connected_clients.discard(ws)


# Register the broadcast callback with the queue manager
video_queue.set_state_callback(broadcast_state)


@app.on_event("startup")
async def start_periodic_broadcast():
    """Periodically broadcast container RAM and network speed updates every 1 second."""
    async def periodic():
        while True:
            await asyncio.sleep(1.0)
            if connected_clients:
                await broadcast_state()
    asyncio.create_task(periodic())


# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """
    WebSocket endpoint for real-time queue updates.

    On connect, sends the full current state.
    Then, state changes are pushed automatically via the queue callback.
    """
    await ws.accept()
    connected_clients.add(ws)
    logger.info("WebSocket client connected. Total: %d", len(connected_clients))

    # Send initial state
    try:
        state = video_queue.get_full_status()
        ram = log_ram_status()
        await ws.send_text(json.dumps({
            "type": "initial_state",
            "data": state,
            "ram": ram,
        }))
    except Exception as e:
        logger.error("Error sending initial state: %s", e)

    # Keep connection alive
    try:
        while True:
            # Wait for client messages (ping/pong or commands)
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("WebSocket connection ended: %s", e)
    finally:
        connected_clients.discard(ws)
        logger.info("WebSocket client disconnected. Total: %d", len(connected_clients))


# --- HTTP REST Endpoints ---
@app.get("/api/status")
async def get_status():
    """Get current queue status (for initial page load before WebSocket connects)."""
    return {
        "status": "ok",
        "queue": video_queue.get_full_status(),
        "ram": log_ram_status(),
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker/monitoring."""
    return {
        "status": "healthy",
        "queue_state": video_queue.state.value,
        "connected_clients": len(connected_clients),
    }
