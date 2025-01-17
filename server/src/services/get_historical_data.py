import datetime
import time
import json
from controllers import kite
from db import get_db_connection, close_db_connection
from models import HistoricalData

def delay(ms):
    """Delay function to simulate async pauses."""
    time.sleep(ms / 1000)

def get_historical_data(instrument_token, interval, symbol):
    
    conn, cur = get_db_connection()  # Get connection and cursor
    
    try:
        # Create table and delete old data
        HistoricalData.create_table(cur)
        HistoricalData.delete_all(cur, instrument_token, interval)
    except (Exception) as err:
        return {"error": str(err)}
# Close connection in the end
    
    if not kite.access_token:
        return {"error": "Access token not found"}
    
    loop_count = 1 # Number of 100-day windows
    hist = []
    to_date = datetime.datetime.now()  # Current date for the initial time window
    
    for _ in range(loop_count):
        # Define the time window for each request
        time_window_to = to_date.isoformat()[:10]
        time_window_from = (to_date - datetime.timedelta(days=0)).isoformat()[:10]
        print(time_window_from, time_window_to)
        try:
            # Request historical data from the Kite Connect API
            data = kite.historical_data(instrument_token, time_window_from, time_window_to, interval)
            
            if data:
                hist.extend(data)  # Accumulate the data across all requests
            
            # print(f"Data from {time_window_from} to {time_window_to}: {data}")
        
        except Exception as err: 
            return {"error": str(err)}
        
        # Update `to_date` for the next iteration (move back by 101 days)
        to_date = to_date - datetime.timedelta(days=1)
        
        # Delay to avoid overwhelming the API
        delay(200)
        
    # create_table_query = """
    # CREATE TABLE IF NOT EXISTS five_minute_resampled (
    #         instrument_token BIGINT,
    #         time_stamp TIMESTAMPTZ,
    #         open DECIMAL,
    #         high DECIMAL,
    #         low DECIMAL,
    #         close DECIMAL
    #         );"""
    # cur.execute(create_table_query)
    
    # insert_query = """
    #     INSERT INTO five_minute_resampled (instrument_token, time_stamp, open, high, low, close)
    #     VALUES (%s, %s, %s, %s, %s, %s)
    #     """
    
    
    # Deduplicate and sort the data by date (no need for `fromisoformat`)
    if hist:
        hist = list({tuple(item.items()): item for item in hist}.values())  # Deduplicate by converting each dict to tuple
        hist.sort(key=lambda x: x['date'])  # Directly use 'date' as it is a datetime object
        
        # Save to a JSON file with custom serialization
        # hist_for_json = []
        for item in hist:
            if isinstance(item['date'], (datetime.date, datetime.datetime)):
                item['date'] = item['date'].isoformat()  # Convert datetime to ISO format string
            
            HistoricalData(instrument_token, symbol, interval, item['date'], item['open'], item['high'], item['low'], item['close'], item['volume']).save(cur)  # Save each instrument
            
            # cur.execute(insert_query, (instrument_token,item['date'], item['open'], item['high'], item['low'], item['close'],))
            
            # hist_for_json.append(item)
            # cur.execute(insert_query, (
            #     instrument_token,  # instrument_token
            #     item['date'],  # time_stamp
            #     item['open'],  # open
            #     item['high'],  # high
            #     item['low'],  # low
            #     item['close'],  # close
            #     ))
            
        # with open('hist_data.json', 'w') as json_file:
        #     json.dump(hist_for_json, json_file)
        conn.commit()  # Commit changes after insertions
        
        close_db_connection()  # Close connection in the end
        
        return {"data": hist}
    
    return {"error": "No data found"}