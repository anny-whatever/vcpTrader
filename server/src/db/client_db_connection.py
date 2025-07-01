import psycopg2
import psycopg2.extras
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Declare global variables
client_conn = None
client_cur = None

def get_client_db_connection():
    global client_conn, client_cur  # Declare globals to modify them inside the function
    try:
        if client_conn is None:
            client_conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
                connect_timeout=10,
                keepalives_idle=600,
                keepalives_interval=30,
                keepalives_count=3,
                application_name='vcpTrader_client',
                # SSL configuration - disable SSL for localhost connections
                sslmode=os.getenv("DB_SSLMODE", "disable" if os.getenv("DB_HOST") == "localhost" else "prefer")
            )

        
        if client_cur is None:
            client_cur = client_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        
        return client_conn, client_cur
    except Exception as e:
        logger.error(f"Error establishing client DB connection: {e}")
        raise e

def close_client_db_connection():
    global client_conn, client_cur  # Access globals to close them properly
    try:
        if client_cur:
            client_cur.close()
            client_cur = None  # Reset cur after closing

    except Exception as e:
        logger.error(f"Error closing client DB cursor: {e}")
    try:
        if client_conn:
            client_conn.close()
            client_conn = None  # Reset conn after closing
    except Exception as e:
        logger.error(f"Error closing client DB connection: {e}")
