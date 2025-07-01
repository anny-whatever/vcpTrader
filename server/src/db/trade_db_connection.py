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
            # Connection string with timeout and keepalive settings
            connection_params = {
                'host': os.getenv("DB_HOST"),
                'port': os.getenv("DB_PORT"),
                'user': os.getenv("DB_USER"),
                'password': os.getenv("DB_PASSWORD"),
                'database': os.getenv("DB_NAME"),
                # Add connection timeout and keepalive settings
                'connect_timeout': 10,  # Connection timeout in seconds
                'keepalives_idle': 600,  # Start keepalives after 10 minutes of inactivity
                'keepalives_interval': 30,  # Send keepalive every 30 seconds
                'keepalives_count': 3,  # Drop connection after 3 failed keepalives
                'application_name': 'vcpTrader_server',
                # SSL configuration - disable SSL for localhost connections
                'sslmode': os.getenv("DB_SSLMODE", "disable" if os.getenv("DB_HOST") == "localhost" else "prefer")
            }
            
            trade_conn_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,  # Minimum number of connections in the pool
                maxconn=20,  # Maximum number of connections in the pool
                **connection_params
            )
            logger.info("Trade DB connection pool initialized with keepalive settings")
    except Exception as e:
        logger.error(f"Error initializing trade DB connection pool: {e}")
        raise e

def _validate_connection(conn):
    """Validate that the connection is still alive and working."""
    try:
        # Check if connection is closed
        if conn.closed != 0:
            logger.warning("Connection is closed")
            return False
            
        # Simple query to check if connection is alive
        with conn.cursor() as test_cur:
            test_cur.execute("SELECT 1")
            test_cur.fetchone()
        return True
    except (psycopg2.OperationalError, psycopg2.InterfaceError, psycopg2.DatabaseError) as e:
        logger.warning(f"Connection validation failed: {e}")
        return False
    except Exception as e:
        logger.warning(f"Connection validation failed with unexpected error: {e}")
        return False

def get_trade_db_connection():
    global trade_conn_pool
    try:
        if trade_conn_pool is None:
            initialize_trade_pool()
        
        # Get a connection from the pool
        conn = trade_conn_pool.getconn()
        
        # Validate the connection before returning it
        if not _validate_connection(conn):
            logger.warning("Got invalid connection from pool, attempting to get a new one")
            try:
                # Return the bad connection to pool and get a new one
                trade_conn_pool.putconn(conn, close=True)
                conn = trade_conn_pool.getconn()
                
                # Validate the new connection
                if not _validate_connection(conn):
                    logger.error("Unable to get valid connection from pool")
                    raise Exception("Unable to get valid database connection")
            except Exception as e:
                logger.error(f"Error getting replacement connection: {e}")
                raise e
        
        # Create cursor with DictCursor factory
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return conn, cur
    except Exception as e:
        logger.error(f"Error getting trade DB connection: {e}")
        raise e

def release_trade_db_connection(conn, cur):
    global trade_conn_pool
    try:
        if cur and not cur.closed:
            cur.close()  # Close the cursor
    except Exception as e:
        logger.error(f"Error closing trade DB cursor: {e}")
    try:
        if conn:
            # Check if connection is still valid before returning to pool
            if conn.closed == 0:  # 0 means connection is open
                trade_conn_pool.putconn(conn)
            else:
                logger.warning("Connection was closed, not returning to pool")
                trade_conn_pool.putconn(conn, close=True)
    except Exception as e:
        logger.error(f"Error releasing trade DB connection: {e}")

def close_trade_pool():
    global trade_conn_pool
    try:
        if trade_conn_pool:
            trade_conn_pool.closeall()
            trade_conn_pool = None
            logger.info("Trade DB connection pool closed")
    except Exception as e:
        logger.error(f"Error closing trade DB connection pool: {e}")
