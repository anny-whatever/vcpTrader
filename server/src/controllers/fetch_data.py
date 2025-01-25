from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from services import  fetch_risk_pool_for_display, fetch_trade_details_for_display, fetch_historical_trade_details_for_display

router = APIRouter()

@router.get("/positions")
async def screen_stocks():
    try:
        response = fetch_trade_details_for_display()
        return JSONResponse(response)
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}

@router.get("/riskpool")
async def screen_stocks():
    try:
        response = fetch_risk_pool_for_display()
        return JSONResponse(response)
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}
    
@router.get("/historicaltrades")
async def screen_stocks():
    try:
        response = fetch_historical_trade_details_for_display()
        return JSONResponse(response)
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}