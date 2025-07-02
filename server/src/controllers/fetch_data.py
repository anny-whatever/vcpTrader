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

@router.post("/test-single-stock")
async def test_single_stock_data_collection(
    instrument_token: int, 
    symbol: str, 
    interval: str = 'day', 
    segment: str = 'NSE',
    user: dict = Depends(require_user)
):
    """
    Test route to collect data for a single stock using Kite API.
    This will fetch fresh OHLC data and calculate technical indicators for testing purposes.
    
    Parameters:
    - instrument_token: Kite instrument token for the stock
    - symbol: Stock symbol (e.g., 'RELIANCE', 'INFY')
    - interval: Time interval ('day', 'week', 'minute', etc.)
    - segment: Market segment (default: 'NSE')
    """
    try:
        logger.info(f"Starting test data collection for {symbol} ({instrument_token})")
        
        # Import locally to avoid circular dependency
        from services.get_ohlc import get_ohlc
        
        # Call the existing get_ohlc function for single stock
        result = get_ohlc(
            instrument_token=instrument_token,
            interval=interval,
            symbol=symbol,
            segment=segment
        )
        
        logger.info(f"Test data collection completed for {symbol}: {result}")
        
        # Return detailed response for testing
        return JSONResponse(content={
            "status": "success",
            "message": f"Data collection test completed for {symbol}",
            "symbol": symbol,
            "instrument_token": instrument_token,
            "interval": interval,
            "segment": segment,
            "result": result
        })
        
    except Exception as e:
        error_msg = f"Error in test_single_stock_data_collection for {symbol} ({instrument_token}): {e}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.get("/test-single-stock")
async def test_single_stock_data_collection_get(
    instrument_token: int, 
    symbol: str, 
    interval: str = 'day', 
    segment: str = 'NSE',
    user: dict = Depends(require_user)
):
    """
    GET version of test route to collect data for a single stock using Kite API.
    Easier to test directly in browser or with simple curl commands.
    
    Example usage:
    GET /api/data/test-single-stock?instrument_token=738561&symbol=RELIANCE&interval=day
    """
    try:
        logger.info(f"Starting GET test data collection for {symbol} ({instrument_token})")
        
        # Import locally to avoid circular dependency
        from services.get_ohlc import get_ohlc
        
        # Call the existing get_ohlc function for single stock
        result = get_ohlc(
            instrument_token=instrument_token,
            interval=interval,
            symbol=symbol,
            segment=segment
        )
        
        logger.info(f"GET test data collection completed for {symbol}: {result}")
        
        # Return detailed response for testing
        return JSONResponse(content={
            "status": "success",
            "message": f"Data collection test completed for {symbol}",
            "symbol": symbol,
            "instrument_token": instrument_token,
            "interval": interval,
            "segment": segment,
            "result": result,
            "note": "This is a test endpoint for single stock data collection"
        })
        
    except Exception as e:
        error_msg = f"Error in GET test_single_stock_data_collection for {symbol} ({instrument_token}): {e}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
