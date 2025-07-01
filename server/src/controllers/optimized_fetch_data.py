# optimized_fetch_data.py
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from services.async_data_services import (
    fetch_trade_details_for_display_async,
    fetch_risk_pool_for_display_async,
    fetch_historical_trade_details_for_display_async,
    get_combined_ohlc_async
)
from auth import require_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/positions")
async def screen_stocks(user: dict = Depends(require_user)):
    """Get current trading positions - fully async"""
    try:
        response = await fetch_trade_details_for_display_async()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_stocks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch positions data")

@router.get("/riskpool")
async def screen_riskpool(user: dict = Depends(require_user)):
    """Get risk pool data - fully async"""
    try:
        response = await fetch_risk_pool_for_display_async()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_riskpool: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch risk pool data")
    
@router.get("/historicaltrades")
async def screen_historicaltrades(user: dict = Depends(require_user)):
    """Get historical trades - fully async"""
    try:
        response = await fetch_historical_trade_details_for_display_async()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_historicaltrades: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch historical trades")

@router.get("/chartdata")
async def screen_chartdata(token: int, symbol: str, interval: str = 'day', user: dict = Depends(require_user)):
    """Get chart data - fully async"""
    try:
        response = await get_combined_ohlc_async(instrument_token=token, symbol=symbol, interval=interval)
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_chartdata for token {token}, symbol {symbol}, interval {interval}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chart data") 