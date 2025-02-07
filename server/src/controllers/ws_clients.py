from fastapi import WebSocket
from .ws_endpoint import clients  # Import clients from ws_endpoint
import json
from datetime import datetime

def convert_datetime(obj):
    """Convert datetime to ISO format for JSON serialization."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

async def send_data_to_clients(message: str):
    """Send a message to all connected WebSocket clients."""
    # Iterate over a copy of the list so that removal does not affect the loop.
    for client in clients.copy():
        try:
            await client.send_text(message)
        except Exception as e:
            print(f"Error sending message: {e}")
            # Remove the client if an error occurs (it might have disconnected)
            try:
                clients.remove(client)
            except ValueError:
                pass

async def process_and_send_live_ticks(ticks):
    """Process live tick data and send it to all WebSocket clients."""
    tick_data = {
        "event": "live_ticks",  # Event label for the message
        "data": ticks  # Tick data to be sent
    }

    # Convert tick data to JSON format, handling datetime conversion
    tick_data_json = json.dumps(tick_data, default=convert_datetime)
    
    # Send the processed data to all connected WebSocket clients
    await send_data_to_clients(tick_data_json)

async def process_and_send_update_message():
    """Process an update message and send it to all WebSocket clients."""
    try:
        update_message_data = {
            "event": "data_update",  # Event label for the message
            "data": datetime.now()
        }

        # Convert update message to JSON format, handling datetime conversion
        update_message_data_json = json.dumps(update_message_data, default=convert_datetime)
        
        # Send the processed data to all connected WebSocket clients
        await send_data_to_clients(update_message_data_json)
        print("Update message sent to clients")
    except Exception as e:
        print(f"Error sending update message: {e}")
