# fetch_data.py
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
# Import directly to avoid circular dependencies - moved to local imports
from auth import require_user

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/positions")
async def screen_stocks(user: dict = Depends(require_user)):
    try:
        # Import locally to avoid circular dependency
        from services.get_display_data import fetch_trade_details_for_display
        response = fetch_trade_details_for_display()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_stocks: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch positions data")

@router.get("/riskpool")
async def screen_riskpool(user: dict = Depends(require_user)):
    try:
        # Import locally to avoid circular dependency
        from services.get_display_data import fetch_risk_pool_for_display
        response = fetch_risk_pool_for_display()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_riskpool: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch risk pool data")
    
@router.get("/historicaltrades")
async def screen_historicaltrades(user: dict = Depends(require_user)):
    try:
        # Import locally to avoid circular dependency
        from services.get_display_data import fetch_historical_trade_details_for_display
        response = fetch_historical_trade_details_for_display()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_historicaltrades: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch historical trades")

@router.get("/chartdata")
async def screen_chartdata(token: int, symbol: str, interval: str = 'day', user: dict = Depends(require_user)):
    try:
        # Import locally to avoid circular dependency
        from services.get_display_data import get_combined_ohlc
        response = get_combined_ohlc(instrument_token=token, symbol=symbol, interval=interval)
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in screen_chartdata for token {token}, symbol {symbol}, interval {interval}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch chart data")
