import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

# Declare global variables
client_conn = None
client_cur = None

def get_client_db_connection():
    global client_conn, client_cur  # Declare globals to modify them inside the function

    if client_conn is None:
        client_conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
        )
    
    if client_cur is None:
        client_cur = client_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    return client_conn, client_cur

def close_client_db_connection():
    global client_conn, client_cur  # Access globals to close them properly

    if client_cur:
        client_cur.close()
        client_cur = None  # Reset cur after closing
    
    if client_conn:
        client_conn.close()
        client_conn = None  # Reset conn after closing
