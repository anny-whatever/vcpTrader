# order_management.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from services import buy_order_execute, sell_order_execute, adjust_order_execute, adjust_trade_parameters
from .ws_clients import process_and_send_update_message
from auth import require_admin

router = APIRouter()

@router.get("/buy")
async def buy_stock(symbol: str, qty: int, user: dict = Depends(require_admin)):
    try:
        response = buy_order_execute(symbol, qty)
        if response['status'] == 'success':
            await process_and_send_update_message()
        return JSONResponse(response)
    except Exception as e:
        return {"error from controller": str(e)}

@router.get("/exit")
async def sell_stock(symbol: str, user: dict = Depends(require_admin)):
    try:
        response = sell_order_execute(symbol)
        if response['status'] == 'success':
            await process_and_send_update_message()
        return JSONResponse(response)
    except Exception as e:
        return {"error from controller": str(e)}

@router.get("/reduce")
async def reduce_stock(symbol: str, qty: int, user: dict = Depends(require_admin)):
    try:
        response = adjust_order_execute(symbol, qty, 'decrease')
        if response['status'] == 'success':
            await process_and_send_update_message()
        return JSONResponse(response)
    except Exception as e:
        return {"error from controller": str(e)}

@router.get("/increase")
async def increase_stock(symbol: str, qty: int, user: dict = Depends(require_admin)):
    try:
        response = adjust_order_execute(symbol, qty, 'increase')
        if response['status'] == 'success':
            await process_and_send_update_message()
        return JSONResponse(response)
    except Exception as e:
        return {"error from controller": str(e)}

@router.get("/change_sl")
async def change_sl(symbol: str, sl, user: dict = Depends(require_admin)):
    try:
        response = adjust_trade_parameters(symbol, new_stop_loss=sl)
        if response['status'] == 'success':
            await process_and_send_update_message()
        return JSONResponse(response)
    except Exception as e:
        return {"error from controller": str(e)}

@router.get("/change_tgt")
async def change_tgt(symbol: str, tgt, user: dict = Depends(require_admin)):
    try:
        response = adjust_trade_parameters(symbol, new_target=tgt)
        if response['status'] == 'success':
            await process_and_send_update_message()
        return JSONResponse(response)
    except Exception as e:
        return {"error from controller": str(e)}
