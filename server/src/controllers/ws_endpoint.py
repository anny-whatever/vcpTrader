import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .ws_clients import clients, get_clients_lock, heartbeat

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Add the client to the set.
    async with get_clients_lock():
        clients.add(websocket)

    # Launch a heartbeat task to send periodic pings.
    heartbeat_task = asyncio.create_task(heartbeat(websocket))

    try:
        while True:
            data = await websocket.receive_text()
            # Instead of sending a plain text echo, wrap it as JSON.
            echo_payload = {"event": "echo", "data": data}
            await websocket.send_text(json.dumps(echo_payload))
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cancel the heartbeat task.
        heartbeat_task.cancel()
        # Remove the client from the set.
        async with get_clients_lock():
            clients.discard(websocket)
