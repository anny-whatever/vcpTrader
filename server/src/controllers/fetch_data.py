# fetch_data.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from services import (
    fetch_risk_pool_for_display,
    fetch_trade_details_for_display,
    fetch_historical_trade_details_for_display,
    get_combined_ohlc
)
from auth import get_current_user

router = APIRouter()

@router.get("/positions")
async def screen_stocks(user: dict = Depends(get_current_user)):
    try:
        response = fetch_trade_details_for_display()
        return JSONResponse(response)
    except Exception as e:
        return {"error from controller": str(e)}

@router.get("/riskpool")
async def screen_riskpool(user: dict = Depends(get_current_user)):
    try:
        response = fetch_risk_pool_for_display()
        return JSONResponse(response)
    except Exception as e:
        return {"error from controller": str(e)}
    
@router.get("/historicaltrades")
async def screen_historicaltrades(user: dict = Depends(get_current_user)):
    try:
        response = fetch_historical_trade_details_for_display()
        return JSONResponse(response)
    except Exception as e:
        return {"error from controller": str(e)}

@router.get("/chartdata")
async def screen_chartdata(token: int, symbol: str, user: dict = Depends(get_current_user)):
    try:
        response = get_combined_ohlc(instrument_token=token, symbol=symbol)
        return JSONResponse(response)
    except Exception as e:
        return {"error from controller": str(e)}
