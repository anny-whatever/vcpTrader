import psycopg2
from psycopg2 import pool
import psycopg2.extras
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize the connection pool globally
ticker_conn_pool = None

def initialize_pool():
    global ticker_conn_pool
    try:
        if ticker_conn_pool is None:
            # Connection parameters with SSL configuration
            connection_params = {
                'host': os.getenv("DB_HOST"),
                'port': os.getenv("DB_PORT"),
                'user': os.getenv("DB_USER"),
                'password': os.getenv("DB_PASSWORD"),
                'database': os.getenv("DB_NAME"),
                # Add connection timeout and keepalive settings
                'connect_timeout': 10,
                'keepalives_idle': 600,
                'keepalives_interval': 30,
                'keepalives_count': 3,
                'application_name': 'vcpTrader_ticker',
                # SSL configuration - disable SSL for localhost connections
                'sslmode': os.getenv("DB_SSLMODE", "disable" if os.getenv("DB_HOST") == "localhost" else "prefer")
            }
            
            ticker_conn_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,  # Minimum number of connections in the pool
                maxconn=20,  # Maximum number of connections in the pool
                **connection_params
            )

    except Exception as e:
        logger.error(f"Error initializing ticker DB connection pool: {e}")
        raise e

def get_ticker_db_connection():
    global ticker_conn_pool
    try:
        if ticker_conn_pool is None:
            initialize_pool()
        # Get a connection from the pool
        conn = ticker_conn_pool.getconn()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        return conn, cur
    except Exception as e:
        logger.error(f"Error getting ticker DB connection: {e}")
        raise e

def release_ticker_db_connection(conn, cur):
    global ticker_conn_pool
    try:
        if cur:
            cur.close()  # Close the cursor
    except Exception as e:
        logger.error(f"Error closing ticker DB cursor: {e}")
    try:
        if conn:
            ticker_conn_pool.putconn(conn)

    except Exception as e:
        logger.error(f"Error releasing ticker DB connection: {e}")

def close_ticker_pool():
    global ticker_conn_pool
    try:
        if ticker_conn_pool:
            ticker_conn_pool.closeall()
            ticker_conn_pool = None

    except Exception as e:
        logger.error(f"Error closing ticker DB connection pool: {e}")
