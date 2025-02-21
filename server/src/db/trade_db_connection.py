import psycopg2
from psycopg2 import pool
import psycopg2.extras
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize the connection pool globally
trade_conn_pool = None

def initialize_trade_pool():
    global trade_conn_pool
    try:
        if trade_conn_pool is None:
            trade_conn_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,  # Minimum number of connections in the pool
                maxconn=20,  # Maximum number of connections in the pool
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
            )
            logger.info("Trade DB connection pool initialized.")
    except Exception as e:
        logger.error(f"Error initializing trade DB connection pool: {e}")
        raise e

def get_trade_db_connection():
    global trade_conn_pool
    try:
        if trade_conn_pool is None:
            initialize_trade_pool()
        # Get a connection from the pool
        conn = trade_conn_pool.getconn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        logger.info("Trade DB connection retrieved from pool.")
        return conn, cur
    except Exception as e:
        logger.error(f"Error getting trade DB connection: {e}")
        raise e

def release_trade_db_connection(conn, cur):
    global trade_conn_pool
    try:
        if cur:
            cur.close()  # Close the cursor
            logger.info("Trade DB cursor closed.")
    except Exception as e:
        logger.error(f"Error closing trade DB cursor: {e}")
    try:
        if conn:
            trade_conn_pool.putconn(conn)
            logger.info("Trade DB connection released back to pool.")
    except Exception as e:
        logger.error(f"Error releasing trade DB connection: {e}")

def close_trade_pool():
    global trade_conn_pool
    try:
        if trade_conn_pool:
            trade_conn_pool.closeall()
            trade_conn_pool = None
            logger.info("Trade DB connection pool closed.")
    except Exception as e:
        logger.error(f"Error closing trade DB connection pool: {e}")
