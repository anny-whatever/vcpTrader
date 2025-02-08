# historical_data.py
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from services import get_historical_data, get_equity_ohlc_data_loop

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def historical_data(instrument_token: str, interval: str, symbol: str):
    try:
        data = get_historical_data(instrument_token, interval, symbol)
        return JSONResponse(content=data)
    except Exception as e:
        logger.error(f"Error fetching historical data for instrument {instrument_token}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch historical data")

@router.get("/equity")
async def historical_data_equity(interval: str):
    try:
        data = get_equity_ohlc_data_loop(interval)
        return JSONResponse(content=data)
    except Exception as e:
        logger.error(f"Error fetching equity historical data for interval {interval}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch equity historical data")
