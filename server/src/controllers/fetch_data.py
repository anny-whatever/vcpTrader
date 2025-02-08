# fetch_data.py
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from services import (
    fetch_risk_pool_for_display,
    fetch_trade_details_for_display,
    fetch_historical_trade_details_for_display,
    get_combined_ohlc
)
from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/positions")
async def screen_stocks(user: dict = Depends(get_current_user)):
    try:
        response = fetch_trade_details_for_display()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_stocks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch positions data")

@router.get("/riskpool")
async def screen_riskpool(user: dict = Depends(get_current_user)):
    try:
        response = fetch_risk_pool_for_display()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_riskpool: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch risk pool data")
    
@router.get("/historicaltrades")
async def screen_historicaltrades(user: dict = Depends(get_current_user)):
    try:
        response = fetch_historical_trade_details_for_display()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_historicaltrades: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch historical trades")

@router.get("/chartdata")
async def screen_chartdata(token: int, symbol: str, user: dict = Depends(get_current_user)):
    try:
        response = get_combined_ohlc(instrument_token=token, symbol=symbol)
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_chartdata for token {token} and symbol {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chart data")
