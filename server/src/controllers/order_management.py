import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from services.order_manager import execute_buy, execute_sell, execute_adjust, get_order_status  # Import order status function
from auth import require_admin

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/buy")
async def buy_stock(symbol: str, qty: int, user: dict = Depends(require_admin)):
    try:
        # The order manager now directly handles token refresh and WebSocket updates
        # when orders complete successfully
        result = execute_buy(symbol, qty)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in buy_stock (symbol: {symbol}, qty: {qty}): {e}")
        raise HTTPException(status_code=500, detail="Failed to execute buy order")

@router.get("/exit")
async def sell_stock(symbol: str, user: dict = Depends(require_admin)):
    try:
        # The order manager now directly handles token refresh and WebSocket updates
        # when orders complete successfully
        result = execute_sell(symbol)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in sell_stock (symbol: {symbol}): {e}")
        raise HTTPException(status_code=500, detail="Failed to execute sell order")

@router.get("/reduce")
async def reduce_stock(symbol: str, qty: int, user: dict = Depends(require_admin)):
    try:
        # The order manager now directly handles token refresh and WebSocket updates
        # when orders complete successfully
        result = execute_adjust(symbol, qty, 'decrease')
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in reduce_stock (symbol: {symbol}, qty: {qty}): {e}")
        raise HTTPException(status_code=500, detail="Failed to execute reduce order")

@router.get("/increase")
async def increase_stock(symbol: str, qty: int, user: dict = Depends(require_admin)):
    try:
        # The order manager now directly handles token refresh and WebSocket updates
        # when orders complete successfully
        result = execute_adjust(symbol, qty, 'increase')
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in increase_stock (symbol: {symbol}, qty: {qty}): {e}")
        raise HTTPException(status_code=500, detail="Failed to execute increase order")

@router.get("/change_sl")
async def change_sl(symbol: str, sl, user: dict = Depends(require_admin)):
    try:
        # Import locally to avoid circular dependency
        from services.manage_trade_params import adjust_trade_parameters
        response = adjust_trade_parameters(symbol, new_stop_loss=sl)
        if response.get("status") == "success":
            # For this method, we still need to manually trigger an update via WebSocket
            from controllers.ws_clients import process_and_send_update_message
            await process_and_send_update_message()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in change_sl (symbol: {symbol}, sl: {sl}): {e}")
        raise HTTPException(status_code=500, detail="Failed to change stop loss")

@router.get("/change_tgt")
async def change_tgt(symbol: str, tgt, user: dict = Depends(require_admin)):
    try:
        # Import locally to avoid circular dependency
        from services.manage_trade_params import adjust_trade_parameters
        response = adjust_trade_parameters(symbol, new_target=tgt)
        if response.get("status") == "success":
            # For this method, we still need to manually trigger an update via WebSocket
            from controllers.ws_clients import process_and_send_update_message
            await process_and_send_update_message()
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error in change_tgt (symbol: {symbol}, tgt: {tgt}): {e}")
        raise HTTPException(status_code=500, detail="Failed to change target")

@router.get("/toggle_auto_exit")
async def toggle_auto_exit(trade_id: int, auto_exit: bool, user: dict = Depends(require_admin)):
    """
    Toggle the auto_exit flag for a given trade.
    This endpoint allows the frontend to update the auto_exit setting.
    """
    try:
        # Import locally to avoid circular dependency
        from services.auto_exit import toggle_auto_exit_flag
        result = toggle_auto_exit_flag(trade_id, auto_exit)
        if result.get("status") == "success":
            # For this method, we still need to manually trigger an update via WebSocket
            from controllers.ws_clients import process_and_send_update_message
            await process_and_send_update_message()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error toggling auto_exit for trade_id {trade_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle auto_exit flag")

@router.get("/order_status")
async def order_status(symbol: str, user: dict = Depends(require_admin)):
    """
    Get the status of active orders for a symbol.
    """
    try:
        # Use the order_manager's get_order_status
        status = get_order_status(symbol)
        return JSONResponse(content=status)
    except Exception as e:
        logger.error(f"Error getting order status for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get order status for {symbol}")
