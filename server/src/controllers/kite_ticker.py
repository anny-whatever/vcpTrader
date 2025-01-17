import os
from datetime import datetime, time
from kiteconnect import KiteTicker
from dotenv import load_dotenv
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
import asyncio
from db import get_db_connection, close_db_connection
from .schedulers import scheduler, setup_scheduler   

load_dotenv()

# Global instances
kite_ticker = None
executor = ThreadPoolExecutor(max_workers=20)

# Define constants for time ranges
START_TIME = time(9, 15)
END_TIME = time(15, 30)
RESAMPLE_START_TIME = time(9, 15)
RESAMPLE_END_TIME = time(15, 30, 5)
MONITOR_LIVE_TRADE_START = time(9, 15, 15)
MONITOR_LIVE_TRADE_END = time(15, 29, 30)


# Utility Functions
def is_within_time_range():
    now = datetime.now().time()
    return START_TIME <= now <= END_TIME

def is_within_resample_time_range():
    now = datetime.now().time()
    return RESAMPLE_START_TIME <= now <= RESAMPLE_END_TIME

def is_within_monitor_live_trade_time_range():
    now = datetime.now().time()
    return MONITOR_LIVE_TRADE_START <= now <= MONITOR_LIVE_TRADE_END


# Database Utility Functions
def get_instrument_token():
    conn, cur = get_db_connection()
    try:
        tokens = [256265]
        select_query = """SELECT instrument_token FROM equity_tokens;"""
        cur.execute(select_query)
        equity_tokens = cur.fetchall()
        
        tokens.extend(item['instrument_token'] for item in equity_tokens)
        print(tokens)

        return tokens
    except Exception as err:
        return {"error": str(err)}
    finally:
        close_db_connection()


# KiteTicker Setup
def initialize_kite_ticker(access_token):
    global kite_ticker
    if kite_ticker is None:
        kite_ticker = KiteTicker(
            os.getenv("API_KEY"), access_token, debug=True, reconnect=True,
            reconnect_max_delay=5, reconnect_max_tries=300, connect_timeout=600
        )
        # Start the ticker in a separate thread
        Thread(target=start_kite_ticker).start()
    return kite_ticker


def start_kite_ticker():
    global kite_ticker
    # from services.store_tick_data import save_options_ticks, save_indices_ticks
    
    from .ws_clients import process_and_send_live_ticks

    tokens = get_instrument_token()

    def on_ticks(ws, ticks):
        try:
            def run_async_in_thread(coroutine, *args):
                loop = asyncio.new_event_loop()  # Create a new event loop
                asyncio.set_event_loop(loop)     # Set it for this thread
                try:
                    loop.run_until_complete(coroutine(*args))  # Run the coroutine
                finally:
                    loop.run_until_complete(loop.shutdown_asyncgens())  # Clean up async generators
                    loop.close()  # Close the loop to deallocate resources

            # Example usage of submitting to ThreadPoolExecutor
            # if is_within_time_range():
            #     print(f"Ticks received: {len(ticks)}") 
                # executor.submit(save_options_ticks, ticks)
                # executor.submit(save_indices_ticks, ticks)

            # if is_within_monitor_live_trade_time_range():
                # executor.submit(monitor_live_position_sabbo_five_minute_short, ticks)
                # executor.submit(monitor_live_position_sabbo_five_minute_long, ticks)
                # executor.submit(monitor_live_position_danbo_five_minute_short, ticks)
                # executor.submit(monitor_live_position_danbo_five_minute_long, ticks)
                # executor.submit(monitor_live_position_sutbo_five_minute_short, ticks)
                # executor.submit(monitor_live_position_sutbo_five_minute_long, ticks)
                
            executor.submit(run_async_in_thread, process_and_send_live_ticks, ticks)
                
            if not is_within_resample_time_range() and scheduler.running:
                scheduler.shutdown()
            elif is_within_resample_time_range() and not scheduler.running:
                setup_scheduler()

        except Exception as e:
            print(f"Error processing ticks: {e}")

    def on_connect(ws, response):
        print("Connected to WebSocket.")
        ws.subscribe(tokens)
        ws.set_mode(ws.MODE_FULL, tokens)
        if is_within_resample_time_range() and not scheduler.running:
            setup_scheduler()  # Start the scheduler when connected

    def on_close(ws, code, reason):
        print(f"Connection closed: {code}, {reason}")
        # scheduler.shutdown()

    def on_error(ws, code, reason):
        print(f"Error: {code}, {reason}")

    def on_disconnect(ws, code, reason):
        print(f"Disconnected: {code}, {reason}")
        retry_connection(ws)  # Attempt reconnection or some recovery mechanism
    
    def retry_connection(ws):
        print("Attempting to reconnect...")
        try:
            ws.connect(threaded=True)
        except Exception as e:
            print(f"Reconnection failed: {e}")
            # Optionally add a retry delay
            time.sleep(5)
            retry_connection(ws)

    # Assigning event handlers
    kite_ticker.on_ticks = on_ticks
    kite_ticker.on_connect = on_connect
    kite_ticker.on_close = on_close
    kite_ticker.on_error = on_error
    kite_ticker.on_disconnect = on_disconnect

    # Start the connection
    kite_ticker.connect(threaded=True)
