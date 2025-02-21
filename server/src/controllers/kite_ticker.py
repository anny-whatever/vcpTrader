# controllers/kite_ticker.py
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
#  ^ same DB pool code. No changes here.

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
    Example for retrieving tokens from other tables (equity_tokens, watchlist, etc.).
    This is separate from the dynamic 'filtered_tokens' used for live filtering.
    """
    conn, cur = None, None
    tokens = []
    try:
        conn, cur = get_trade_db_connection()

        cur.execute("SELECT instrument_token FROM equity_tokens WHERE segment != 'ALL';")
        equity_tokens = cur.fetchall()

        cur.execute("SELECT instrument_token FROM watchlist;")
        watchlist_tokens = cur.fetchall()

        cur.execute("SELECT instrument_token FROM indices_instruments;")
        indices_tokens = cur.fetchall()

        tokens.extend(item['instrument_token'] for item in (equity_tokens + watchlist_tokens + indices_tokens))
        logger.info(f"Instrument tokens retrieved: {tokens}")
        return tokens
    except Exception as err:
        logger.error(f"Error fetching instrument tokens: {err}")
        return {"error": str(err)}
    finally:
        if conn and cur:
            release_trade_db_connection(conn, cur)

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

            # Import from services to avoid circular deps
            from services import listen_for_data_changes

            # Start the DB listener thread
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
    if isinstance(tokens, dict):  # Means an error
        logger.error("Failed to retrieve tokens, aborting KiteTicker start.")
        return

    def on_ticks(ws, ticks):
        try:
            # Import the same 'services' references
            from services import filtered_tokens

            current_set = filtered_tokens

            filtered = [tk for tk in ticks if tk.get('instrument_token') in current_set]
            logger.debug(f"Filtered {len(filtered)} ticks from {len(ticks)} total.")

            # Asynchronous execution
            def run_async_in_thread(coro, *args):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(coro(*args))
                finally:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                    loop.close()

            # Pass only the filtered ticks
            executor.submit(run_async_in_thread, process_and_send_live_ticks, filtered)
            # If you want all ticks for alerts, you can pass 'ticks' or 'filtered'
            executor.submit(run_async_in_thread, process_live_alerts, ticks)
            
            # Only run auto-exit if within monitored timeframe
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

    # Set event handlers
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
