import psycopg2
from psycopg2 import pool
import psycopg2.extras
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize the connection pool globally
main_conn_pool = None

# Keep the global variables for backward compatibility but deprecate their use
conn = None
cur = None

def initialize_main_pool():
    global main_conn_pool
    try:
        if main_conn_pool is None:
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
                'application_name': 'vcpTrader_main'
            }
            
            main_conn_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,  # Minimum number of connections in the pool
                maxconn=15,  # Maximum number of connections in the pool
                **connection_params
            )
            logger.info("Main DB connection pool initialized with keepalive settings")
    except Exception as e:
        logger.error(f"Error initializing main DB connection pool: {e}")
        raise e

def _validate_connection(conn):
    """Validate that the connection is still alive and working."""
    try:
        # Simple query to check if connection is alive
        with conn.cursor() as test_cur:
            test_cur.execute("SELECT 1")
            test_cur.fetchone()
        return True
    except Exception as e:
        logger.warning(f"Connection validation failed: {e}")
        return False

def get_db_connection():
    global main_conn_pool
    try:
        if main_conn_pool is None:
            initialize_main_pool()
        
        # Get a connection from the pool
        conn = main_conn_pool.getconn()
        
        # Validate the connection before returning it
        if not _validate_connection(conn):
            logger.warning("Got invalid connection from pool, attempting to get a new one")
            try:
                # Return the bad connection to pool and get a new one
                main_conn_pool.putconn(conn, close=True)
                conn = main_conn_pool.getconn()
                
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
        logger.error(f"Error getting main DB connection: {e}")
        raise e

def release_main_db_connection(conn, cur):
    """
    Properly release a connection and cursor back to the pool.
    This should be used instead of close_db_connection() for new code.
    """
    global main_conn_pool
    try:
        if cur and not cur.closed:
            cur.close()  # Close the cursor
    except Exception as e:
        logger.error(f"Error closing main DB cursor: {e}")
    try:
        if conn and main_conn_pool:
            # Check if connection is still valid before returning to pool
            if conn.closed == 0:  # 0 means connection is open
                main_conn_pool.putconn(conn)
            else:
                logger.warning("Connection was closed, not returning to pool")
                main_conn_pool.putconn(conn, close=True)
    except Exception as e:
        logger.error(f"Error releasing main DB connection: {e}")

def close_db_connection():
    """
    Legacy function for backward compatibility.
    This function is kept for existing code but should be avoided for new implementations.
    Use release_main_db_connection(conn, cur) instead.
    
    NOTE: This function may not work properly in all contexts due to the global variable pattern.
    It's maintained primarily for backward compatibility.
    """
    # Try to find connection variables in various scopes
    import inspect
    import gc
    
    # Try to get conn and cur from calling frame
    try:
        frame = inspect.currentframe().f_back
        while frame:
            local_conn = frame.f_locals.get('conn')
            local_cur = frame.f_locals.get('cur')
            
            if local_conn is not None and local_cur is not None:
                release_main_db_connection(local_conn, local_cur)
                return
            frame = frame.f_back
    except Exception as e:
        logger.warning(f"Could not inspect frames for connection cleanup: {e}")
    
    # Fallback: close global variables if they exist
    global conn, cur
    if conn or cur:
        logger.warning("Using deprecated global connection cleanup - consider updating code to use release_main_db_connection()")
        close_db_connection_legacy()

def close_main_pool():
    global main_conn_pool
    try:
        if main_conn_pool:
            main_conn_pool.closeall()
            main_conn_pool = None
            logger.info("Main DB connection pool closed")
    except Exception as e:
        logger.error(f"Error closing main DB connection pool: {e}")

# Deprecated legacy function - keeping for backward compatibility
def close_db_connection_legacy():
    """
    Legacy function for backward compatibility.
    This closes the global connection variables (deprecated pattern).
    """
    global conn, cur
    try:
        if cur:
            cur.close()
            cur = None

    except Exception as e:
        logger.error(f"Error closing DB cursor: {e}")
    try:
        if conn:
            conn.close()
            conn = None

    except Exception as e:
        logger.error(f"Error closing DB connection: {e}")
