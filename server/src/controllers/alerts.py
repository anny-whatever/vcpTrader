# alert_endpoints.py

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from auth import require_admin, require_user
from services import get_all_alerts, get_latest_alert_messages, add_alert, remove_alert

router = APIRouter()

@router.post("/alerts/add")
async def api_add_alert(alert_data: dict, user: dict = Depends(require_admin)):
    """
    Endpoint to add a new alert.
    Expected JSON payload:
    {
        "instrument_token": int,
        "symbol": str,
        "price": float,
        "alert_type": "target" or "sl"
    }
    """
    try:
        instrument_token = alert_data.get("instrument_token")
        symbol = alert_data.get("symbol")
        price = alert_data.get("price")
        alert_type = alert_data.get("alert_type")
        response = add_alert(instrument_token, symbol, price, alert_type)
        return JSONResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding alert: {e}")

@router.get("/alerts/remove")
async def api_remove_alert(alert_id: int, user: dict = Depends(require_admin)):
    """
    Endpoint to remove an alert.
    Expects an alert_id as a query parameter.
    """
    try:
        response = remove_alert(alert_id)
        return JSONResponse(content=response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing alert: {e}")

@router.get("/alerts/list")
async def api_list_alerts(user: dict = Depends(require_user)):
    """
    Endpoint to retrieve all active alerts.
    """
    try:
        alerts = get_all_alerts()
        return JSONResponse(content=alerts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching alerts: {e}")

@router.get("/alerts/messages")
async def api_list_alert_messages(user: dict = Depends(require_user)):
    """
    Endpoint to retrieve the latest 10 alert messages.
    """
    try:
        messages = get_latest_alert_messages()
        return JSONResponse(content=messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching alert messages: {e}")
