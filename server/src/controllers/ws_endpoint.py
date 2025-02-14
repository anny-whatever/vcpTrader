# ws_endpoint.py
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
from .ws_clients import clients, get_clients_lock

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Acquire the lock to append
    async with get_clients_lock():
        clients.append(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Acquire lock to remove
        async with get_clients_lock():
            try:
                clients.remove(websocket)
            except ValueError:
                logger.warning("WebSocket already removed from clients list")
