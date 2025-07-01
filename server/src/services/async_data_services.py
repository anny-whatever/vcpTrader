import asyncio
import logging
from typing import Dict, List, Any, Optional
import psycopg2.extras
from db.async_connection import async_db, get_readonly_connection, get_main_connection

logger = logging.getLogger(__name__)

async def fetch_trade_details_for_display_async() -> Dict[str, Any]:
    """Async version of fetch_trade_details_for_display"""
    try:
        query = """
        SELECT 
            t.id,
            t.symbol,
            t.quantity,
            t.buy_price,
            t.current_price,
            t.stop_loss,
            t.target,
            t.pnl,
            t.pnl_percentage,
            t.status,
            t.buy_date,
            t.auto_exit,
            t.exit_date,
            t.exit_price,
            t.exit_reason
        FROM trades t 
        WHERE t.status IN ('active', 'partial')
        ORDER BY t.buy_date DESC
        """
        
        result = await async_db.execute_query(query, pool_name='readonly')
        
        return {
            "status": "success",
            "data": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error in fetch_trade_details_for_display_async: {e}")
        return {
            "status": "error",
            "message": str(e),
            "data": [],
            "count": 0
        }

async def fetch_risk_pool_for_display_async() -> Dict[str, Any]:
    """Async version of fetch_risk_pool_for_display"""
    try:
        query = """
        SELECT 
            rp.symbol,
            rp.current_price,
            rp.risk_score,
            rp.trend_score,
            rp.volume_score,
            rp.momentum_score,
            rp.volatility_score,
            rp.last_updated,
            rp.recommendation
        FROM risk_pool rp 
        WHERE rp.risk_score IS NOT NULL
        ORDER BY rp.risk_score DESC, rp.last_updated DESC
        LIMIT 100
        """
        
        result = await async_db.execute_query(query, pool_name='readonly')
        
        return {
            "status": "success",
            "data": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error in fetch_risk_pool_for_display_async: {e}")
        return {
            "status": "error",
            "message": str(e),
            "data": [],
            "count": 0
        }

async def fetch_historical_trade_details_for_display_async() -> Dict[str, Any]:
    """Async version of fetch_historical_trade_details_for_display"""
    try:
        query = """
        SELECT 
            ht.id,
            ht.symbol,
            ht.quantity,
            ht.buy_price,
            ht.sell_price,
            ht.stop_loss,
            ht.target,
            ht.pnl,
            ht.pnl_percentage,
            ht.buy_date,
            ht.sell_date,
            ht.exit_reason,
            ht.holding_period_days
        FROM historical_trades ht 
        ORDER BY ht.sell_date DESC
        LIMIT 200
        """
        
        result = await async_db.execute_query(query, pool_name='readonly')
        
        return {
            "status": "success",
            "data": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error in fetch_historical_trade_details_for_display_async: {e}")
        return {
            "status": "error",
            "message": str(e),
            "data": [],
            "count": 0
        }

async def get_combined_ohlc_async(instrument_token: int, symbol: str, interval: str = 'day') -> Dict[str, Any]:
    """Async version of get_combined_ohlc"""
    try:
        # Determine table name based on interval
        table_map = {
            'minute': 'ohlc_1min',
            '3minute': 'ohlc_3min', 
            '5minute': 'ohlc_5min',
            '15minute': 'ohlc_15min',
            '30minute': 'ohlc_30min',
            'hour': 'ohlc_1hour',
            'day': 'ohlc_daily'
        }
        
        table_name = table_map.get(interval, 'ohlc_daily')
        
        query = f"""
        SELECT 
            timestamp,
            open,
            high,
            low,
            close,
            volume,
            instrument_token
        FROM {table_name}
        WHERE instrument_token = %s
        ORDER BY timestamp DESC
        LIMIT 500
        """
        
        result = await async_db.execute_query(query, (instrument_token,), pool_name='readonly')
        
        return {
            "status": "success",
            "symbol": symbol,
            "instrument_token": instrument_token,
            "interval": interval,
            "data": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error in get_combined_ohlc_async for token {instrument_token}, symbol {symbol}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "data": [],
            "count": 0
        }

async def get_order_status_async(symbol: str) -> Dict[str, Any]:
    """Async version of get_order_status"""
    try:
        query = """
        SELECT 
            order_id,
            symbol,
            transaction_type,
            quantity,
            price,
            status,
            order_timestamp,
            exchange_order_id,
            filled_quantity,
            pending_quantity
        FROM orders 
        WHERE symbol = %s 
        AND status IN ('OPEN', 'PENDING', 'TRIGGER PENDING')
        ORDER BY order_timestamp DESC
        """
        
        result = await async_db.execute_query(query, (symbol,), pool_name='readonly')
        
        return {
            "status": "success",
            "symbol": symbol,
            "orders": result,
            "count": len(result)
        }
        
    except Exception as e:
        logger.error(f"Error in get_order_status_async for symbol {symbol}: {e}")
        return {
            "status": "error",
            "message": str(e),
            "orders": [],
            "count": 0
        }

async def execute_trade_operation_async(operation: str, symbol: str, quantity: int = None) -> Dict[str, Any]:
    """Async wrapper for trade operations that handles the async/sync boundary"""
    try:
        # Import the synchronous functions
        from services.order_manager import execute_buy, execute_sell, execute_adjust
        
        # Run the synchronous operation in a thread pool to prevent blocking
        loop = asyncio.get_event_loop()
        
        if operation == 'buy':
            result = await loop.run_in_executor(None, execute_buy, symbol, quantity)
        elif operation == 'sell':
            result = await loop.run_in_executor(None, execute_sell, symbol)
        elif operation == 'reduce':
            result = await loop.run_in_executor(None, execute_adjust, symbol, quantity, 'decrease')
        elif operation == 'increase':
            result = await loop.run_in_executor(None, execute_adjust, symbol, quantity, 'increase')
        else:
            return {"status": "error", "message": f"Unknown operation: {operation}"}
        
        return result
        
    except Exception as e:
        logger.error(f"Error in execute_trade_operation_async for {operation} {symbol}: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

async def adjust_trade_parameters_async(symbol: str, new_stop_loss: float = None, new_target: float = None) -> Dict[str, Any]:
    """Async wrapper for trade parameter adjustments"""
    try:
        # Import directly to avoid circular dependency
        from services.manage_trade_params import adjust_trade_parameters
        
        # Run in thread pool to prevent blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, adjust_trade_parameters, symbol, new_stop_loss, new_target)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in adjust_trade_parameters_async for {symbol}: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

async def toggle_auto_exit_flag_async(trade_id: int, auto_exit: bool) -> Dict[str, Any]:
    """Async wrapper for toggling auto exit flag"""
    try:
        # Import directly to avoid circular dependency
        from services.auto_exit import toggle_auto_exit_flag
        
        # Run in thread pool to prevent blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, toggle_auto_exit_flag, trade_id, auto_exit)
        
        return result
        
    except Exception as e:
        logger.error(f"Error in toggle_auto_exit_flag_async for trade_id {trade_id}: {e}")
        return {
            "status": "error",
            "message": str(e)
        } 