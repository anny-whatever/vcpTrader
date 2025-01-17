from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from services import buy_order_execute, sell_order_execute, adjust_order_execute

router = APIRouter()

@router.get("/buy")
async def buy_stock(symbol:str, qty:int):
    try:
        response = buy_order_execute(symbol, qty)
        return JSONResponse(response)
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}

@router.get("/exit")
async def sell_stock(symbol):
    try:
        response = sell_order_execute(symbol)
        return JSONResponse(response)
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}

@router.get("/reduce")
async def reduce_stock(symbol, qty):
    try:
        response = adjust_order_execute(symbol, qty, 'decrease')
        return JSONResponse(response)
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}

@router.get("/increase")
async def increase_stock(symbol, qty):
    try:
        response = adjust_order_execute(symbol, qty, 'increase')
        return JSONResponse(response)
    except (Exception, HTTPException) as e:
        return {"error from controller": str(e)}