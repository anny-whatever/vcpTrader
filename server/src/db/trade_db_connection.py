import psycopg2
from psycopg2 import pool
import psycopg2.extras
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize the connection pool globally
trade_conn_pool = None

def initialize_pool():
    global trade_conn_pool
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
        print("Connection pool initialized")

def get_trade_db_connection():
    global trade_conn_pool
    
    if trade_conn_pool is None:
        # raise Exception("Connection pool is not initialized. Call initialize_pool() first.")
        initialize_pool()
    
    # Get a connection from the pool
    conn = trade_conn_pool.getconn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    
    return conn, cur

def release_trade_db_connection(conn, cur):
    global trade_conn_pool
    
    if cur:
        cur.close()  # Close the cursor
    
    if conn:
        # Release the connection back to the pool instead of closing it
        trade_conn_pool.putconn(conn)

def close_trade_pool():
    global trade_conn_pool
    
    if trade_conn_pool:
        # Close all connections in the pool
        trade_conn_pool.closeall()
        trade_conn_pool = None
        print("Connection pool closed")
