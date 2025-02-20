import psycopg2
import psycopg2.extras
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# Declare global variables
conn = None
cur = None

def get_db_connection():
    global conn, cur  # Declare globals to modify them inside the function
    try:
        if conn is None:
            conn = psycopg2.connect(
                host=os.getenv("DB_HOST"),
                port=os.getenv("DB_PORT"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD"),
                database=os.getenv("DB_NAME"),
            )
            logger.info("DB connection established.")
        
        if cur is None:
            cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            logger.info("DB cursor created.")
        
        return conn, cur
    except Exception as e:
        logger.error(f"Error establishing DB connection: {e}")
        raise e

def close_db_connection():
    global conn, cur  # Access globals to close them properly
    try:
        if cur:
            cur.close()
            cur = None  # Reset cur after closing
            logger.info("DB cursor closed.")
    except Exception as e:
        logger.error(f"Error closing DB cursor: {e}")
    try:
        if conn:
            conn.close()
            conn = None  # Reset conn after closing
            logger.info("DB connection closed.")
    except Exception as e:
        logger.error(f"Error closing DB connection: {e}")
