from services import get_historical_data, get_equity_historical_data_loop
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/")
async def historical_data(instrument_token: str, interval: str, symbol: str):
    try:
        return JSONResponse(get_historical_data(instrument_token, interval, symbol))
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}

@router.get("/equity")
async def historical_data( interval: str):
    try:
        return JSONResponse(get_equity_historical_data_loop(interval))
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}
