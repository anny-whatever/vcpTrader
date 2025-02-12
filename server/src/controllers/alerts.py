# alert_endpoints.py
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Literal
from auth import require_admin, require_user
from services import (
    get_all_alerts,
    get_latest_alert_messages,
    add_alert,
    remove_alert
)
from .ws_clients import process_and_send_alert_update_message

router = APIRouter()

class AlertData(BaseModel):
    instrument_token: int
    symbol: str
    price: float
    alert_type: Literal['target', 'sl']

@router.post("/add")
async def api_add_alert(alert_data: AlertData, user: dict = Depends(require_admin)):
    """
    Endpoint to add a new alert.
    """
    try:
        response = add_alert(
            instrument_token=alert_data.instrument_token,
            symbol=alert_data.symbol,
            price=alert_data.price,
            alert_type=alert_data.alert_type
        )
        # Send an update event to notify clients that alerts have changed.
        await process_and_send_alert_update_message(response)
        return JSONResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding alert: {e}")

@router.delete("/remove")
async def api_remove_alert(
    alert_id: int = Query(..., description="ID of the alert to remove"),
    user: dict = Depends(require_admin)
):
    """
    Endpoint to remove an alert.
    """
    try:
        response = remove_alert(alert_id)
        # Send an update event so clients know the alerts list was modified.
        await process_and_send_alert_update_message(response)
        return JSONResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing alert: {e}")

@router.get("/list")
async def api_list_alerts(user: dict = Depends(require_user)):
    """
    Endpoint to retrieve all active alerts.
    """
    try:
        alerts = get_all_alerts()
        return JSONResponse(content=alerts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {e}")

@router.get("/messages")
async def api_list_alert_messages(user: dict = Depends(require_user)):
    """
    Endpoint to retrieve the latest 10 alert messages.
    """
    try:
        messages = get_latest_alert_messages()
        return JSONResponse(content=messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching alert messages: {e}")
