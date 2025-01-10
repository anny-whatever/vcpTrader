from typing import List
from fastapi import WebSocket
from .ws_endpoint import clients  # Import clients from ws_endpoint
import json
from datetime import datetime

# Global list to store connected clients

def convert_datetime(obj):
    """Convert datetime to ISO format for JSON serialization"""
    if isinstance(obj, datetime):
        return obj.isoformat()  # Convert datetime to a string
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


async def send_data_to_clients(message: str):
    """Send a message to all connected clients"""
    # print(clients)
    for client in clients:
        try:
            await client.send_text(message)
            # print(f"Message sent to client: {message}")
        except Exception as e:
            print(f"Error sending message: {e}")
            clients.remove(client)  # Remove the disconnected client


async def process_and_send_live_ticks(ticks):
    """Process live tick data and send it to all WebSocket clients"""
    tick_data = {
        "event": "live_ticks",  # Event label for the message
        "data": ticks  # Tick data to be sent
    }

    # Convert tick data to JSON format, handling datetime conversion
    tick_data_json = json.dumps(tick_data, default=convert_datetime)
    
    # Send the processed data to all connected WebSocket clients
    await send_data_to_clients(tick_data_json)
