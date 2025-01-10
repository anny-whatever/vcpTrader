import datetime
import time
import json
import pandas as pd
from controllers import kite
from db import get_db_connection, close_db_connection
from models import EquityHistoricalData

def delay(ms):
    """Delay function to simulate async pauses."""
    time.sleep(ms / 1000)

def get_equity_historical_data(instrument_token, interval, symbol):
    
    conn, cur = get_db_connection()  # Get connection and cursor
    
    try:
        # Create table and delete old data
        EquityHistoricalData.create_table(cur)
        EquityHistoricalData.delete_all(cur, instrument_token, interval)
    except (Exception) as err:
        return {"error": str(err)}
# Close connection in the end
    
    if not kite.access_token:
        return {"error": "Access token not found"}
    
    loop_count = 1  # Number of 100-day windows
    hist = []
    to_date = datetime.datetime.now()  # Current date for the initial time window
    
    for _ in range(loop_count):
        # Define the time window for each request
        time_window_to = to_date.isoformat()[:10]
        time_window_from = (to_date - datetime.timedelta(days=500)).isoformat()[:10]
        
        try:
            # Request historical data from the Kite Connect API
            data = kite.historical_data(instrument_token, time_window_from, time_window_to, interval)
            
            if data:
                hist.extend(data)  # Accumulate the data across all requests
            
            print(f"Data from {time_window_from} to {time_window_to}: {data}")
        
        except Exception as err: 
            return {"error": str(err)}
        
        # Update `to_date` for the next iteration (move back by 101 days)
        to_date = to_date - datetime.timedelta(days=501)
        
        # Delay to avoid overwhelming the API
        delay(200)
        
    # Deduplicate and sort the data by date (no need for `fromisoformat`)
    if hist:
        hist = list({tuple(item.items()): item for item in hist}.values())  # Deduplicate by converting each dict to tuple
        hist.sort(key=lambda x: x['date'])  # Directly use 'date' as it is a datetime object
        
        for item in hist:
            if isinstance(item['date'], (datetime.date, datetime.datetime)):
                item['date'] = item['date'].isoformat()  # Convert datetime to ISO format string
            
            EquityHistoricalData(instrument_token, symbol, interval, item['date'], item['open'], item['high'], item['low'], item['close'], item['volume']).save(cur)  # Save each instrument
            
        conn.commit()  # Commit changes after insertions
        
        # close_db_connection()  # Close connection in the end
        
        return {"data": hist}
    
    return {"error": "No data found"}

def get_equity_historical_data_loop(interval):
    conn, cur = get_db_connection()  # Get connection and cursor
    
    try:
        select_query = """SELECT * FROM equity_tokens;"""
        cur.execute(select_query)
        tokens = cur.fetchall()
        
        for token in tokens:
            get_equity_historical_data(token[0], interval, token[1])
            delete_query = """DELETE FROM equity_tokens WHERE instrument_token = %s;"""
            cur.execute(delete_query, (token[0],))
            conn.commit()

        return {"data": "Done"}
    except (Exception) as err:
        return {"error": str(err)}  
    
    finally:
        close_db_connection()  # Close connection in the end