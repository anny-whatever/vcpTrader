import os
import time
import asyncio
import logging
from datetime import datetime, time as dtime
from kiteconnect import KiteTicker
from dotenv import load_dotenv
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

from db import get_trade_db_connection, release_trade_db_connection

load_dotenv()
logger = logging.getLogger(__name__)

kite_ticker = None
executor = ThreadPoolExecutor(max_workers=20)

MONITOR_LIVE_TRADE_START = dtime(9, 20)
MONITOR_LIVE_TRADE_END = dtime(15, 29)

def is_within_monitor_live_trade_time_range():
    now = datetime.now().time()
    return MONITOR_LIVE_TRADE_START <= now <= MONITOR_LIVE_TRADE_END

def get_instrument_token():
    """
    Retrieve tokens for alerts and auto_exit functions.
    Tokens are fetched from watchlist, trades, screener_results, and price_alerts.
    """
    conn, cur = None, None
    tokens = []
    try:
        conn, cur = get_trade_db_connection()

        cur.execute("SELECT instrument_token FROM watchlist;")
        watchlist_tokens = cur.fetchall()

        cur.execute("SELECT token AS instrument_token FROM trades;")
        trades_tokens = cur.fetchall()

        cur.execute("SELECT instrument_token FROM screener_results;")
        screener_tokens = cur.fetchall()

        cur.execute("SELECT instrument_token FROM price_alerts;")
        price_alert_tokens = cur.fetchall()

        tokens.extend(item['instrument_token'] for item in (watchlist_tokens + trades_tokens + screener_tokens + price_alert_tokens))
        logger.info(f"Instrument tokens for alerts retrieved: {tokens}")
        return tokens
    except Exception as err:
        logger.error(f"Error fetching instrument tokens for alerts: {err}")
        return {"error": str(err)}
    finally:
        if conn and cur:
            release_trade_db_connection(conn, cur)

def update_kite_ticker_subscription(new_tokens):
    """
    Update the KiteTicker subscriptions with the new tokens.
    This function compares the currently subscribed tokens with the new list,
    subscribes to tokens not yet subscribed, and unsubscribes tokens that are no longer needed.
    """
    global kite_ticker
    try:
        # Ensure the ticker maintains a list of currently subscribed tokens.
        if not hasattr(kite_ticker, 'subscribed_tokens'):
            kite_ticker.subscribed_tokens = []
        
        current_tokens_set = set(kite_ticker.subscribed_tokens)
        new_tokens_set = set(new_tokens)
        
        tokens_to_add = list(new_tokens_set - current_tokens_set)
        tokens_to_remove = list(current_tokens_set - new_tokens_set)
        
        if tokens_to_remove:
            kite_ticker.unsubscribe(tokens_to_remove)
            logger.info(f"Unsubscribed tokens: {tokens_to_remove}")
        
        if tokens_to_add:
            kite_ticker.subscribe(tokens_to_add)
            # Set mode for the newly added tokens; ensure tokens are provided as a list.
            kite_ticker.set_mode(kite_ticker.MODE_FULL, tokens_to_add)
            logger.info(f"Subscribed new tokens: {tokens_to_add}")
        
        # Update the record of subscribed tokens
        kite_ticker.subscribed_tokens = list(new_tokens_set)
    except Exception as e:
        logger.error(f"Error updating ticker subscription: {e}")

def initialize_kite_ticker(access_token):
    """
    Called once at startup to:
    - Initialize the Kite Ticker
    - Start the DB listener thread
    - Start the ticker thread
    """
    global kite_ticker
    try:
        if kite_ticker is None:
            kite_ticker = KiteTicker(
                os.getenv("API_KEY"),
                access_token,
                debug=True,
                reconnect=True,
                reconnect_max_delay=5,
                reconnect_max_tries=300,
                connect_timeout=600
            )

            # Import from services to avoid circular dependencies
            from services import listen_for_data_changes

            # Start the DB listener thread (which will update subscriptions on data change)
            Thread(target=listen_for_data_changes, daemon=True).start()

            # Start the ticker in a background thread
            Thread(target=start_kite_ticker, daemon=True).start()

            logger.info("KiteTicker initialized successfully.")
        return kite_ticker
    except Exception as e:
        logger.error(f"Error initializing KiteTicker: {e}")
        raise

def start_kite_ticker():
    global kite_ticker

    # Import your other service modules
    from .ws_clients import process_and_send_live_ticks
    from services import process_live_alerts, process_live_auto_exit

    tokens = get_instrument_token()
    if isinstance(tokens, dict):  # Indicates an error occurred
        logger.error("Failed to retrieve tokens, aborting KiteTicker start.")
        return

    def on_ticks(ws, ticks):
        try:
            # Asynchronous execution helper
            def run_async_in_thread(coro, *args):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(coro(*args))
                finally:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                    loop.close()
            # Process ticks for live updates, alerts, and auto-exit actions
            executor.submit(run_async_in_thread, process_and_send_live_ticks, ticks)
            executor.submit(run_async_in_thread, process_live_alerts, ticks)
            if is_within_monitor_live_trade_time_range():
                executor.submit(run_async_in_thread, process_live_auto_exit, ticks)
        except Exception as e:
            logger.error(f"Error processing ticks: {e}")

    def on_connect(ws, response):
        logger.info("Connected to KiteTicker WebSocket.")
        try:
            ws.subscribe(tokens)
            ws.set_mode(ws.MODE_FULL, tokens)
        except Exception as e:
            logger.error(f"Error in on_connect: {e}")

    def on_close(ws, code, reason):
        logger.info(f"Connection closed: {code}, {reason}")

    def on_error(ws, code, reason):
        logger.error(f"Error: {code}, {reason}")

    def on_disconnect(ws, code, reason):
        logger.info(f"Disconnected: {code}, {reason}")
        retry_connection(ws)

    def retry_connection(ws):
        logger.info("Attempting to reconnect to KiteTicker...")
        max_retries = 50
        retries = 0
        while retries < max_retries:
            try:
                ws.connect(threaded=True)
                logger.info("Successfully reconnected to KiteTicker.")
                return
            except Exception as e:
                retries += 1
                logger.error(f"Reconnection attempt {retries} failed: {e}")
                time.sleep(5)
        logger.error("Max reconnection attempts reached. Could not reconnect to KiteTicker.")

    # Set event handlers for KiteTicker
    kite_ticker.on_ticks = on_ticks
    kite_ticker.on_connect = on_connect
    kite_ticker.on_close = on_close
    kite_ticker.on_error = on_error
    kite_ticker.on_disconnect = on_disconnect

    try:
        kite_ticker.connect(threaded=True)
        logger.info("KiteTicker connection initiated.")
    except Exception as e:
        logger.error(f"Error starting KiteTicker connection: {e}")
