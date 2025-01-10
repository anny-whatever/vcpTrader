import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

# Declare global variables
conn = None
cur = None

def get_db_connection():
    global conn, cur  # Declare globals to modify them inside the function

    if conn is None:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
    
    if cur is None:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    return conn, cur

def close_db_connection():
    global conn, cur  # Access globals to close them properly

    if cur:
        cur.close()
        cur = None  # Reset cur after closing
    
    if conn:
        conn.close()
        conn = None  # Reset conn after closing
