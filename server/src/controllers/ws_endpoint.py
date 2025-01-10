from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

clients: List[WebSocket] = []

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()  # Accept the WebSocket connection
    clients.append(websocket)  # Add the client to the list of connected clients
    try:
        while True:
            data = await websocket.receive_text()  # Receive data from the client
            await websocket.send_text(f"Message received: {data}")  # Send a response back to the client
    except WebSocketDisconnect:
        print("Client disconnected")
        clients.remove(websocket)  # Remove the client from the list on disconnect
    except Exception as e:
        print(f"WebSocket error: {e}")
