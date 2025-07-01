import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from services.async_data_services import (
    execute_trade_operation_async,
    adjust_trade_parameters_async,
    toggle_auto_exit_flag_async,
    get_order_status_async
)
from auth import require_admin

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/buy")
async def buy_stock(symbol: str, qty: int, user: dict = Depends(require_admin)):
    """Execute buy order - non-blocking async"""
    try:
        result = await execute_trade_operation_async('buy', symbol, qty)
        
        # Trigger WebSocket update if successful
        if result.get("status") == "success":
            from controllers.ws_clients import process_and_send_update_message
            await process_and_send_update_message()
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in buy_stock (symbol: {symbol}, qty: {qty}): {e}")
        raise HTTPException(status_code=500, detail="Failed to execute buy order")

@router.get("/exit")
async def sell_stock(symbol: str, user: dict = Depends(require_admin)):
    """Execute sell order - non-blocking async"""
    try:
        result = await execute_trade_operation_async('sell', symbol)
        
        # Trigger WebSocket update if successful
        if result.get("status") == "success":
            from controllers.ws_clients import process_and_send_update_message
            await process_and_send_update_message()
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in sell_stock (symbol: {symbol}): {e}")
        raise HTTPException(status_code=500, detail="Failed to execute sell order")

@router.get("/reduce")
async def reduce_stock(symbol: str, qty: int, user: dict = Depends(require_admin)):
    """Reduce position - non-blocking async"""
    try:
        result = await execute_trade_operation_async('reduce', symbol, qty)
        
        # Trigger WebSocket update if successful
        if result.get("status") == "success":
            from controllers.ws_clients import process_and_send_update_message
            await process_and_send_update_message()
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in reduce_stock (symbol: {symbol}, qty: {qty}): {e}")
        raise HTTPException(status_code=500, detail="Failed to execute reduce order")

@router.get("/increase")
async def increase_stock(symbol: str, qty: int, user: dict = Depends(require_admin)):
    """Increase position - non-blocking async"""
    try:
        result = await execute_trade_operation_async('increase', symbol, qty)
        
        # Trigger WebSocket update if successful
        if result.get("status") == "success":
            from controllers.ws_clients import process_and_send_update_message
            await process_and_send_update_message()
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in increase_stock (symbol: {symbol}, qty: {qty}): {e}")
        raise HTTPException(status_code=500, detail="Failed to execute increase order")

@router.get("/change_sl")
async def change_sl(symbol: str, sl, user: dict = Depends(require_admin)):
    """Change stop loss - non-blocking async"""
    try:
        response = await adjust_trade_parameters_async(symbol, new_stop_loss=sl)
        
        if response.get("status") == "success":
            from controllers.ws_clients import process_and_send_update_message
            await process_and_send_update_message()
        
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in change_sl (symbol: {symbol}, sl: {sl}): {e}")
        raise HTTPException(status_code=500, detail="Failed to change stop loss")

@router.get("/change_tgt")
async def change_tgt(symbol: str, tgt, user: dict = Depends(require_admin)):
    """Change target - non-blocking async"""
    try:
        response = await adjust_trade_parameters_async(symbol, new_target=tgt)
        
        if response.get("status") == "success":
            from controllers.ws_clients import process_and_send_update_message
            await process_and_send_update_message()
        
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in change_tgt (symbol: {symbol}, tgt: {tgt}): {e}")
        raise HTTPException(status_code=500, detail="Failed to change target")

@router.get("/toggle_auto_exit")
async def toggle_auto_exit(trade_id: int, auto_exit: bool, user: dict = Depends(require_admin)):
    """Toggle auto exit flag - non-blocking async"""
    try:
        result = await toggle_auto_exit_flag_async(trade_id, auto_exit)
        
        if result.get("status") == "success":
            from controllers.ws_clients import process_and_send_update_message
            await process_and_send_update_message()
        
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error toggling auto_exit for trade_id {trade_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle auto_exit flag")

@router.get("/order_status")
async def order_status(symbol: str, user: dict = Depends(require_admin)):
    """Get order status - non-blocking async"""
    try:
        status = await get_order_status_async(symbol)
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Error getting order status for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get order status for {symbol}") 