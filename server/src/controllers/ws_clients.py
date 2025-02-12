# ws_clients.py
import json
import logging
from datetime import datetime
from fastapi import WebSocket
from .ws_endpoint import clients  # Import clients from ws_endpoint

logger = logging.getLogger(__name__)

def convert_datetime(obj):
    """Convert datetime to ISO format for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

async def send_data_to_clients(message: str):
    """Send a message to all connected WebSocket clients."""
    for client in list(clients):
        try:
            await client.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message to client: {e}")
            try:
                clients.remove(client)
            except ValueError:
                logger.warning("Client already removed from clients list.")

async def process_and_send_live_ticks(ticks):
    """Process live tick data and send it to all WebSocket clients."""
    try:
        tick_data = {
            "event": "live_ticks",
            "data": ticks
        }
        tick_data_json = json.dumps(tick_data, default=convert_datetime)
        await send_data_to_clients(tick_data_json)
    except Exception as e:
        logger.error(f"Error processing and sending live ticks: {e}")
        raise

async def process_and_send_update_message():
    """Process a general update message and send it to all WebSocket clients."""
    try:
        update_message_data = {
            "event": "data_update",
            "data": datetime.now()
        }
        update_message_data_json = json.dumps(update_message_data, default=convert_datetime)
        await send_data_to_clients(update_message_data_json)
        logger.info("Update message sent to clients")
    except Exception as e:
        logger.error(f"Error sending update message: {e}")
        raise

async def process_and_send_alert_update_message(message):
    """Process an alert update message and send it to all WebSocket clients."""
    try:
        # Wrap the alert message in an event object.
        if isinstance(message, dict):
            payload = message
        else:
            payload = {"event": "alert_update", "data": message}
        message_json = json.dumps(payload, default=convert_datetime)
        await send_data_to_clients(message_json)
        logger.info("Alert update message sent to clients")
    except Exception as e:
        logger.error(f"Error sending alert update message: {e}")
        raise

async def process_and_send_alert_triggered_message(message):
    """Send an alert triggered message (used when a live alert is triggered)."""
    if not isinstance(message, dict):
        payload = {"event": "alert_triggered", "data": message}
    else:
        payload = message
    message_json = json.dumps(payload, default=convert_datetime)
    await send_data_to_clients(message_json)
    logger.info("Alert triggered message sent to clients")