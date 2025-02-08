# kite_ticker.py
import os
import time
import asyncio
import logging
from datetime import datetime, time as dtime
from kiteconnect import KiteTicker
from dotenv import load_dotenv
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
from db import get_db_connection, close_db_connection

load_dotenv()
logger = logging.getLogger(__name__)

# Global instances
kite_ticker = None
executor = ThreadPoolExecutor(max_workers=20)

# Constants for time ranges
START_TIME = dtime(9, 15)
END_TIME = dtime(15, 30)
RESAMPLE_START_TIME = dtime(9, 15)
RESAMPLE_END_TIME = dtime(15, 30, 5)
MONITOR_LIVE_TRADE_START = dtime(9, 15, 15)
MONITOR_LIVE_TRADE_END = dtime(15, 29, 30)

def get_instrument_token():
    conn, cur = get_db_connection()
    try:
        tokens = [256265]
        select_query = """SELECT instrument_token FROM equity_tokens;"""
        cur.execute(select_query)
        equity_tokens = cur.fetchall()
        tokens.extend(item['instrument_token'] for item in equity_tokens)
        logger.info(f"Instrument tokens retrieved: {tokens}")
        return tokens
    except Exception as err:
        logger.error(f"Error fetching instrument tokens: {err}")
        return {"error": str(err)}
    finally:
        try:
            close_db_connection()
        except Exception as close_err:
            logger.error(f"Error closing DB connection in get_instrument_token: {close_err}")

def initialize_kite_ticker(access_token):
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
            # Start the ticker in a separate thread
            Thread(target=start_kite_ticker).start()
        return kite_ticker
    except Exception as e:
        logger.error(f"Error initializing KiteTicker: {e}")
        raise e

def start_kite_ticker():
    global kite_ticker
    from .ws_clients import process_and_send_live_ticks

    tokens = get_instrument_token()
    if isinstance(tokens, dict):  # Means error occurred
        logger.error("Failed to retrieve tokens, aborting KiteTicker start.")
        return

    def on_ticks(ws, ticks):
        try:
            def run_async_in_thread(coroutine, *args):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(coroutine(*args))
                finally:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                    loop.close()
            executor.submit(run_async_in_thread, process_and_send_live_ticks, ticks)
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
        logger.info("Attempting to reconnect...")
        try:
            ws.connect(threaded=True)
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            time.sleep(5)
            retry_connection(ws)

    # Assign event handlers
    kite_ticker.on_ticks = on_ticks
    kite_ticker.on_connect = on_connect
    kite_ticker.on_close = on_close
    kite_ticker.on_error = on_error
    kite_ticker.on_disconnect = on_disconnect

    try:
        kite_ticker.connect(threaded=True)
    except Exception as e:
        logger.error(f"Error starting KiteTicker connection: {e}")
