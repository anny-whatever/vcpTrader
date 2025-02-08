import datetime
import time
import logging
import json
from controllers import kite
from db import get_db_connection, close_db_connection
from models import HistoricalData

logger = logging.getLogger(__name__)

def delay(ms):
    """Delay function to simulate async pauses."""
    time.sleep(ms / 1000)

def get_historical_data(instrument_token, interval, symbol):
    conn, cur = get_db_connection()  # Get connection and cursor
    try:
        # Create table and delete old data
        HistoricalData.create_table(cur)
        HistoricalData.delete_all(cur, instrument_token, interval)
    except Exception as err:
        logger.error(f"Error in preparing historical_data: {err}")
        return {"error": str(err)}
    
    if not kite.access_token:
        return {"error": "Access token not found"}
    
    loop_count = 1  # Number of 100-day windows
    hist = []
    to_date = datetime.datetime.now()  # Current date for the initial time window
    
    for _ in range(loop_count):
        time_window_to = to_date.isoformat()[:10]
        time_window_from = (to_date - datetime.timedelta(days=700)).isoformat()[:10]
        logger.info(f"Fetching historical data from {time_window_from} to {time_window_to}")
        try:
            data = kite.historical_data(instrument_token, time_window_from, time_window_to, interval)
            if data:
                hist.extend(data)  # Accumulate the data across all requests
        except Exception as err:
            logger.error(f"Error fetching historical data for instrument {instrument_token} between {time_window_from} and {time_window_to}: {err}")
            return {"error": str(err)}
        to_date = to_date - datetime.timedelta(days=701)
        delay(200)
        
    if hist:
        try:
            # Deduplicate and sort the data by date
            hist = list({tuple(item.items()): item for item in hist}.values())
            hist.sort(key=lambda x: x['date'])
            # Save each record to the database
            for item in hist:
                if isinstance(item['date'], (datetime.date, datetime.datetime)):
                    item['date'] = item['date'].isoformat()
                HistoricalData(instrument_token, symbol, interval, item['date'], item['open'], item['high'], item['low'], item['close'], item['volume']).save(cur)
            conn.commit()
        except Exception as e:
            logger.error(f"Error processing and saving historical data: {e}")
            return {"error": str(e)}
        finally:
            close_db_connection()
        return {"data": hist}
    
    close_db_connection()
    return {"error": "No data found"}
