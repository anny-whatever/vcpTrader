# controllers/kite_ticker_equity.py
import os
import time
import asyncio
import logging
from kiteconnect import KiteTicker
from datetime import datetime, time as dtime
from dotenv import load_dotenv
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

from db import get_trade_db_connection, release_trade_db_connection

load_dotenv()
logger = logging.getLogger(__name__)

# Global ticker instance and executor for async tasks.
kite_ticker_equity = None
executor = ThreadPoolExecutor(max_workers=20)

MONITOR_LIVE_TRADE_START = dtime(9, 15)
MONITOR_LIVE_TRADE_END = dtime(15, 30)

def is_within_trade_time_range():
    now = datetime.now().time()
    return MONITOR_LIVE_TRADE_START <= now <= MONITOR_LIVE_TRADE_END

def get_equity_tokens():
    """
    Fetch all instrument tokens from the equity_tokens table (all records, no filtering).
    """
    conn, cur = None, None
    try:
        conn, cur = get_trade_db_connection()
        cur.execute("SELECT instrument_token FROM equity_tokens;")
        tokens_data = cur.fetchall()
        tokens = [row['instrument_token'] for row in tokens_data]
        logger.info(f"Equity tokens retrieved: {tokens}")
        return tokens
    except Exception as err:
        logger.error(f"Error fetching equity tokens: {err}")
        return {"error": str(err)}
    finally:
        if conn and cur:
            release_trade_db_connection(conn, cur)

def initialize_kite_ticker_equity(access_token):
    """
    Initialize the Kite Ticker for equity tokens.
    This ticker will subscribe only to equity tokens and does NOT run alert or auto_exit processes.
    """
    global kite_ticker_equity
    try:
        if kite_ticker_equity is None:
            kite_ticker_equity = KiteTicker(
                os.getenv("API_KEY"),
                access_token,
                debug=True,
                reconnect=True,
                reconnect_max_delay=5,
                reconnect_max_tries=300,
                connect_timeout=600
            )
            # Start the ticker in a background thread.
            Thread(target=start_kite_ticker_equity, daemon=True).start()
            logger.info("KiteTickerEquity initialized successfully.")
        return kite_ticker_equity
    except Exception as e:
        logger.error(f"Error initializing KiteTickerEquity: {e}")
        raise

def start_kite_ticker_equity():
    global kite_ticker_equity
    tokens = get_equity_tokens()
    if isinstance(tokens, dict):  # error occurred
        logger.error("Failed to retrieve equity tokens, aborting KiteTickerEquity start.")
        return

    def on_ticks(ws, ticks):
        try:
            logger.debug(f"Received equity ticks: {ticks}")

            # Asynchronous execution helper: creates a new event loop for the coroutine.
            def run_async_in_thread(coro, *args):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(coro(*args))
                finally:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                    loop.close()

            # Define an async function that calls your tick-saving module.
            # async def async_save_ticks(ticks):
            #     from services import save_tradable_ticks, save_nontradable_ticks
            #     # Call your save functions (each function will iterate over ticks and decide which ones to save)
            #     if is_within_trade_time_range():
            #         save_tradable_ticks(ticks)
            #         save_nontradable_ticks(ticks)

            # # Submit the async_save_ticks coroutine to the executor.
            # executor.submit(run_async_in_thread, async_save_ticks, ticks)
        except Exception as e:
            logger.error(f"Error processing equity ticks: {e}")

    def on_connect(ws, response):
        logger.info("Connected to KiteTickerEquity WebSocket.")
        try:
            # ws.subscribe(tokens)
            # ws.set_mode(ws.MODE_FULL, tokens)
            print(tokens)
        except Exception as e:
            logger.error(f"Error in on_connect (equity): {e}")

    def on_close(ws, code, reason):
        logger.info(f"KiteTickerEquity Connection closed: {code}, {reason}")

    def on_error(ws, code, reason):
        logger.error(f"KiteTickerEquity Error: {code}, {reason}")

    def on_disconnect(ws, code, reason):
        logger.info(f"KiteTickerEquity Disconnected: {code}, {reason}")
        retry_connection(ws)

    def retry_connection(ws):
        logger.info("Attempting to reconnect to KiteTickerEquity...")
        max_retries = 50
        retries = 0
        while retries < max_retries:
            try:
                ws.connect(threaded=True)
                logger.info("Successfully reconnected to KiteTickerEquity.")
                return
            except Exception as e:
                retries += 1
                logger.error(f"Equity reconnection attempt {retries} failed: {e}")
                time.sleep(5)
        logger.error("Max reconnection attempts reached for KiteTickerEquity.")

    # Set event handlers.
    kite_ticker_equity.on_ticks = on_ticks
    kite_ticker_equity.on_connect = on_connect
    kite_ticker_equity.on_close = on_close
    kite_ticker_equity.on_error = on_error
    kite_ticker_equity.on_disconnect = on_disconnect

    try:
        kite_ticker_equity.connect(threaded=True)
        logger.info("KiteTickerEquity connection initiated.")
    except Exception as e:
        logger.error(f"Error starting KiteTickerEquity connection: {e}")
