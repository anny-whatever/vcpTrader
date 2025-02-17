import asyncio
import json
import logging
from datetime import datetime
from typing import List
from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)

# Global clients list
clients: List[WebSocket] = []

# Store a tuple (lock, loop) so we know which event loop the lock was created on.
_lock_info = None

def get_clients_lock() -> asyncio.Lock:
    global _lock_info
    current_loop = asyncio.get_running_loop()
    # If no lock exists, or the existing lock is tied to a different event loop, create a new one.
    if _lock_info is None or _lock_info[1] != current_loop:
        _lock_info = (asyncio.Lock(), current_loop)
    return _lock_info[0]

def convert_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

async def send_data_to_clients(message: str):
    """Send a message to all connected WebSocket clients."""
    lock = get_clients_lock()
    # Copy the current clients list while holding the lock.
    async with lock:
        current_clients = list(clients)

    # Send messages outside the lock.
    for client in current_clients:
        # Check if the client is still connected
        if client.client_state != WebSocketState.CONNECTED:
            logger.info("Client not connected, removing from list.")
            async with lock:
                try:
                    clients.remove(client)
                except ValueError:
                    logger.warning("Client already removed from clients list.")
            continue

        try:
            await client.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            # Remove client if sending fails.
            async with lock:
                try:
                    clients.remove(client)
                except ValueError:
                    logger.warning("Client already removed from clients list.")

async def process_and_send_live_ticks(ticks):
    """Process live tick data and send it to all WebSocket clients."""
    try:
        tick_data = {"event": "live_ticks", "data": ticks}
        tick_data_json = json.dumps(tick_data, default=convert_datetime)
        await send_data_to_clients(tick_data_json)
    except Exception as e:
        logger.error(f"Error processing and sending live ticks: {e}")
        raise

async def process_and_send_update_message():
    """Process a general update message and send it to all WebSocket clients."""
    try:
        update_message_data = {"event": "data_update", "data": datetime.now()}
        update_message_data_json = json.dumps(update_message_data, default=convert_datetime)
        await send_data_to_clients(update_message_data_json)
        logger.info("Update message sent to clients")
    except Exception as e:
        logger.error(f"Error sending update message: {e}")
        raise

async def process_and_send_alert_update_message(message):
    """Process an alert update message and send it to all WebSocket clients."""
    try:
        payload = {"event": "alert_update", "data": message}
        message_json = json.dumps(payload, default=convert_datetime)
        await send_data_to_clients(message_json)
        logger.info("Alert update message sent to clients")
    except Exception as e:
        logger.error(f"Error sending alert update message: {e}")
        raise

async def process_and_send_alert_triggered_message(message):
    """Send an alert triggered message (used when a live alert is triggered)."""
    try:
        payload = {"event": "alert_triggered", "data": message}
        message_json = json.dumps(payload, default=convert_datetime)
        await send_data_to_clients(message_json)
        logger.info("Alert triggered message sent to clients")
    except Exception as e:
        logger.error(f"Error sending alert update message: {e}")
        raise

async def heartbeat(websocket: WebSocket):
    """Send a ping message periodically to keep the connection alive."""
    while websocket.client_state == WebSocketState.CONNECTED:
        try:
            ping_message = json.dumps({"event": "ping", "data": "keepalive"})
            await websocket.send_text(ping_message)
        except Exception as e:
            logger.error(f"Error sending ping: {e}")
            break
        await asyncio.sleep(30)
