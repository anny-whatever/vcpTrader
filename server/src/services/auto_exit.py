import logging
import asyncio
import threading
import select
from db import get_trade_db_connection, release_trade_db_connection
from .place_exit import sell_order_execute
from .send_telegram_alert import _send_telegram_in_thread

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Lock and flag to ensure only one instance of auto-exit processing runs at a time.
auto_exit_lock = threading.Lock()
auto_exit_running = False

# Global cache for active trades and a lock to protect it.
active_trades_cache = []
cache_lock = threading.Lock()

def get_all_active_trades_from_db():
    """
    Fetch all active trades directly from the database.
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
        logger.error(f"Error fetching active trades from DB: {e}")
        return []

def listen_for_trade_changes():
    """
    Listen for NOTIFY events on the 'trades_changed' channel.
    When a notification is received, update the global active_trades_cache.
    """
    try:
        # Unpack the connection and cursor.
        conn, _ = get_trade_db_connection()
        # Set autocommit mode.
        conn.set_isolation_level(0)
        # Create a new cursor to execute the LISTEN command.
        cur = conn.cursor()
        cur.execute("LISTEN trades_changed;")
        logger.info("Listening on channel 'trades_changed'")
        while True:
            if select.select([conn], [], [], None):
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    logger.info("Received notification: " + notify.payload)
                    new_trades = get_all_active_trades_from_db()
                    with cache_lock:
                        global active_trades_cache
                        active_trades_cache = new_trades
    except Exception as e:
        logger.error(f"Error in listen_for_trade_changes: {e}")


# Start the listener thread (daemonized so it shuts down with your application).
listener_thread = threading.Thread(target=listen_for_trade_changes, daemon=True)
listener_thread.start()

async def process_live_auto_exit(ticks):
    """
    Process live tick data to check for auto exit conditions using the cached trades.
    
    For each cached trade with auto_exit enabled, if the live price is at or below its stop_loss,
    the trade exit is triggered by calling sell_order_execute.
    
    :param ticks: List of tick data dictionaries received from KiteTicker.
    """
    global auto_exit_running
    with auto_exit_lock:
        if auto_exit_running:
            logger.info("process_live_auto_exit is already running; exiting this call.")
            return
        auto_exit_running = True

    try:
        with cache_lock:
            trades = active_trades_cache.copy()  # Work on a snapshot of the cache.
        for trade in trades:
            # Only process trades with auto_exit enabled.
            if not trade.get("auto_exit"):
                continue

            symbol = trade["stock_name"]
            stop_loss = float(trade["stop_loss"])
            token = trade["token"]

            # Look for a matching tick by instrument token.
            matching_tick = None
            for tick in ticks:
                if tick.get("instrument_token") == token:
                    matching_tick = tick
                    break

            if not matching_tick:
                continue

            current_price = float(matching_tick.get("last_price"))

            if current_price <= stop_loss:
                logger.info(f"Auto exit triggered for {symbol}: current price {current_price} reached stop loss {stop_loss}")
                custom_message = f"Auto exit triggered for {symbol}: current price {current_price} reached stop loss {stop_loss}."
                # Execute exit in a non-blocking thread.
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
    
    Intended for use in an API endpoint to allow the frontend
    to change the auto_exit setting.
    
    :param trade_id: The ID of the trade to update.
    :param new_auto_exit: Boolean value to set for auto_exit.
    :return: A dictionary with status and a message.
    """
    try:
        conn, cur = get_trade_db_connection()
        from models import SaveTradeDetails
        SaveTradeDetails.update_auto_exit(cur, trade_id, new_auto_exit)
        conn.commit()
        release_trade_db_connection(conn, cur)
        logger.info(f"auto_exit flag updated to {new_auto_exit} for trade_id: {trade_id}")
        return {"status": "success", "message": f"auto_exit flag updated to {new_auto_exit} for trade_id {trade_id}"}
    except Exception as e:
        logger.exception(f"Error toggling auto_exit flag for trade_id {trade_id}: {e}")
        return {"status": "error", "message": f"Error updating auto_exit flag: {str(e)}"}
