# services/get_essential_tokens.py
import threading
import logging
import select
import psycopg2

from db import get_trade_db_connection, release_trade_db_connection

logger = logging.getLogger(__name__)

filtered_tokens = []

def refresh_tokens():
    """
    Opens and closes a short-lived connection from the pool
    to fetch instrument tokens from multiple tables.
    """
    global filtered_tokens
    new_set = set()
    conn, cur = None, None
    try:
        conn, cur = get_trade_db_connection()

        # 1) watchlist
        cur.execute("SELECT instrument_token FROM watchlist;")
        for row in cur.fetchall():
            new_set.add(row['instrument_token'])

        # 2) trades (column is 'token')
        cur.execute("SELECT token AS instrument_token FROM trades;")
        for row in cur.fetchall():
            new_set.add(row['instrument_token'])

        # 3) screener_results
        cur.execute("SELECT instrument_token FROM screener_results;")
        for row in cur.fetchall():
            new_set.add(row['instrument_token'])

        # 4) price_alerts
        cur.execute("SELECT instrument_token FROM price_alerts;")
        for row in cur.fetchall():
            new_set.add(row['instrument_token'])
            
        
        for token in new_set:
            filtered_tokens.append(token)
            
        logger.info(f"Refreshed tokens => {len(new_set)} items.")
    except Exception as e:
        logger.error(f"Error refreshing tokens: {e}", exc_info=True)
    finally:
        # Make sure we release this connection back to the pool.
        if conn and cur:
            release_trade_db_connection(conn, cur)

        


def listen_for_data_changes():
    """
    Dedicated listener for the 'data_changed' channel using a
    single, never-closed connection from the pool.
    """
    try:
        # Grab a connection from the pool
        listen_conn, listen_cur = get_trade_db_connection()

        # IMPORTANT: set autocommit for LISTEN/NOTIFY usage
        listen_conn.set_session(autocommit=True)

        # We won't release this connection back to the pool,
        # because we need to keep it open indefinitely.
        logger.info("Acquired dedicated connection for LISTEN/NOTIFY.")

        # Start listening on the single channel
        listen_cur.execute("LISTEN data_changed;")
        logger.info("Listening on channel 'data_changed'...")

        # Do an initial tokens fetch
        refresh_tokens()

        while True:
            # Wait for a notification indefinitely
            # (select.select blocks until read-ready)
            if select.select([listen_conn], [], [], None):
                listen_conn.poll()
                while listen_conn.notifies:
                    notify = listen_conn.notifies.pop(0)
                    table_name = notify.payload
                    logger.info(f"[NOTIFY] Table changed: {table_name}. Refreshing tokens...")
                    refresh_tokens()

    except Exception as e:
        logger.error(f"Error in listen_for_data_changes: {e}", exc_info=True)
        # If you want an auto-reconnect logic, you can add it here
    finally:
        # If we ever exit the loop, release resources
        # (In production, you might want an infinite loop with reconnect logic.)
        logger.info("Listener shutting down... Releasing dedicated connection.")
        if 'listen_conn' in locals() and 'listen_cur' in locals():
            release_trade_db_connection(listen_conn, listen_cur)
