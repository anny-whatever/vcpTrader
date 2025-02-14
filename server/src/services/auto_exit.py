import logging
import asyncio
import threading
from db import get_trade_db_connection, release_trade_db_connection
from .place_exit import sell_order_execute
from .send_telegram_alert import _send_telegram_in_thread

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Lock and flag to ensure only one instance of auto-exit processing runs at a time.
auto_exit_lock = threading.Lock()
auto_exit_running = False

def get_all_active_trades():
    """
    Fetch all active trades from the trades table.
    Since all rows represent active trades, no extra filtering is needed.
    Returns a list of dictionaries with keys: trade_id, stock_name, token, entry_price, stop_loss, auto_exit.
    """
    try:
        conn, cur = get_trade_db_connection()
        query = """
            SELECT trade_id, stock_name, token, entry_price, stop_loss, auto_exit
            FROM trades;
        """
        cur.execute(query)
        trades = cur.fetchall()
        release_trade_db_connection(conn, cur)
        return trades
    except Exception as e:
        logger.error(f"Error fetching active trades: {e}")
        return []

async def process_live_auto_exit(ticks):
    """
    Process live tick data to check for auto exit conditions.
    
    For each active trade with auto_exit enabled, it looks for a matching tick (by token).
    If the live price is at or below the trade's stop_loss, the trade exit is triggered
    by calling sell_order_execute for that symbol.
    
    This function is intended to be called from your KiteTicker on_ticks callback,
    similar to process_live_alerts.
    
    :param ticks: List of tick data dictionaries received from KiteTicker.
    """
    global auto_exit_running
    # Ensure only one instance runs at a time.
    with auto_exit_lock:
        if auto_exit_running:
            logger.info("process_live_auto_exit is already running; exiting this call.")
            return
        auto_exit_running = True

    try:
        active_trades = get_all_active_trades()
        for trade in active_trades:
            # Proceed only if auto_exit flag is enabled.
            if not trade.get("auto_exit"):
                continue

            symbol = trade["stock_name"]
            stop_loss = float(trade["stop_loss"])
            token = trade["token"]

            # Find a matching tick for this trade (match based on instrument token).
            matching_tick = None
            for tick in ticks:
                if tick.get("instrument_token") == token:
                    matching_tick = tick
                    break

            if not matching_tick:
                continue

            current_price = float(matching_tick.get("last_price"))
            logger.info(f"Auto-exit check for {symbol}: Current Price = {current_price}, Stop Loss = {stop_loss}")

            if current_price <= stop_loss:
                logger.info(f"Auto exit triggered for {symbol}: current price {current_price} reached stop loss {stop_loss}")
                custom_message = f"Auto exit triggered for {symbol}: current price {current_price} reached stop loss {stop_loss}."
                # Run sell_order_execute in a separate thread (non-blocking).
                await asyncio.to_thread(sell_order_execute, symbol)
                thread = threading.Thread(target=_send_telegram_in_thread, args=(custom_message,))
                thread.start()

    except Exception as e:
        logger.exception(f"Error in process_live_auto_exit: {e}")
    finally:
        with auto_exit_lock:
            auto_exit_running = False


def toggle_auto_exit_flag(trade_id, new_auto_exit):
    """
    Toggle the auto_exit flag for a given trade.
    
    This function is intended to be used in an API endpoint to allow the frontend
    to change the auto_exit setting for a trade.
    
    :param trade_id: The ID of the trade to update.
    :param new_auto_exit: Boolean value to set for the auto_exit flag.
    :return: A dictionary with the status and a message.
    """
    try:
        conn, cur = get_trade_db_connection()
        # Import the model here to avoid circular dependency issues.
        from models import SaveTradeDetails
        SaveTradeDetails.update_auto_exit(cur, trade_id, new_auto_exit)
        conn.commit()
        release_trade_db_connection(conn, cur)
        logger.info(f"auto_exit flag updated to {new_auto_exit} for trade_id: {trade_id}")
        return {"status": "success", "message": f"auto_exit flag updated to {new_auto_exit} for trade_id {trade_id}"}
    except Exception as e:
        logger.exception(f"Error toggling auto_exit flag for trade_id {trade_id}: {e}")
        return {"status": "error", "message": f"Error updating auto_exit flag: {str(e)}"}