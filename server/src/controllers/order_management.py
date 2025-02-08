# order_management.py
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from services import buy_order_execute, sell_order_execute, adjust_order_execute, adjust_trade_parameters
from .ws_clients import process_and_send_update_message
from auth import require_admin

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/buy")
async def buy_stock(symbol: str, qty: int, user: dict = Depends(require_admin)):
    try:
        response = buy_order_execute(symbol, qty)
        if response.get("status") == "success":
            await process_and_send_update_message()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in buy_stock (symbol: {symbol}, qty: {qty}): {e}")
        raise HTTPException(status_code=500, detail="Failed to execute buy order")

@router.get("/exit")
async def sell_stock(symbol: str, user: dict = Depends(require_admin)):
    try:
        response = sell_order_execute(symbol)
        if response.get("status") == "success":
            await process_and_send_update_message()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in sell_stock (symbol: {symbol}): {e}")
        raise HTTPException(status_code=500, detail="Failed to execute sell order")

@router.get("/reduce")
async def reduce_stock(symbol: str, qty: int, user: dict = Depends(require_admin)):
    try:
        response = adjust_order_execute(symbol, qty, 'decrease')
        if response.get("status") == "success":
            await process_and_send_update_message()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in reduce_stock (symbol: {symbol}, qty: {qty}): {e}")
        raise HTTPException(status_code=500, detail="Failed to execute reduce order")

@router.get("/increase")
async def increase_stock(symbol: str, qty: int, user: dict = Depends(require_admin)):
    try:
        response = adjust_order_execute(symbol, qty, 'increase')
        if response.get("status") == "success":
            await process_and_send_update_message()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in increase_stock (symbol: {symbol}, qty: {qty}): {e}")
        raise HTTPException(status_code=500, detail="Failed to execute increase order")

@router.get("/change_sl")
async def change_sl(symbol: str, sl, user: dict = Depends(require_admin)):
    try:
        response = adjust_trade_parameters(symbol, new_stop_loss=sl)
        if response.get("status") == "success":
            await process_and_send_update_message()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in change_sl (symbol: {symbol}, sl: {sl}): {e}")
        raise HTTPException(status_code=500, detail="Failed to change stop loss")

@router.get("/change_tgt")
async def change_tgt(symbol: str, tgt, user: dict = Depends(require_admin)):
    try:
        response = adjust_trade_parameters(symbol, new_target=tgt)
        if response.get("status") == "success":
            await process_and_send_update_message()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in change_tgt (symbol: {symbol}, tgt: {tgt}): {e}")
        raise HTTPException(status_code=500, detail="Failed to change target")
