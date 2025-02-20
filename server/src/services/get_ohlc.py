import datetime
import time
import pandas as pd
import pandas_ta as ta
import logging
from controllers import kite
from db import get_db_connection, close_db_connection
from models import SaveOHLC

logger = logging.getLogger(__name__)

def delay(ms):
    """Delay function to simulate async pauses."""
    time.sleep(ms / 1000)

def get_ohlc(instrument_token, interval, symbol, segment):

    conn, cur = get_db_connection()  # Get connection and cursor
    try:
        try:
            SaveOHLC.delete_all(cur, instrument_token, interval)
        except Exception as err:
            logger.error(f"Error deleting OHLC data: {err}")
            return {"error": str(err)}
    
        if not kite.access_token:
            return {"error": "Access token not found"}
    
        loop_count = 1  # Number of 100-day windows
        hist = []
        to_date = datetime.datetime.now()  # Current date for the initial time window
    
        for _ in range(loop_count):
            time_window_to = to_date.isoformat()[:10]
            time_window_from = (to_date - datetime.timedelta(days=2000)).isoformat()[:10]
            logger.info(f"Fetching OHLC data from {time_window_from} to {time_window_to} for instrument {instrument_token}")
            try:
                data = kite.historical_data(instrument_token, time_window_from, time_window_to, interval)
                if data:
                    hist.extend(data)
            except Exception as err:
                logger.error(f"Error fetching OHLC data for instrument {instrument_token}: {err}")
                return {"error": str(err)}
            to_date = to_date - datetime.timedelta(days=2001)
            delay(200)
    
        if hist:
            try:
                hist = list({tuple(item.items()): item for item in hist}.values())
                hist.sort(key=lambda x: x['date'])
                hist = pd.DataFrame(hist)
                batch_data = []
                for _, row in hist.iterrows():
                    batch_data.append((
                        instrument_token,
                        symbol,
                        interval,
                        row['date'].isoformat() if isinstance(row['date'], (datetime.date, datetime.datetime)) else row['date'],
                        row['open'],
                        row['high'],
                        row['low'],
                        row['close'],
                        row['volume'],
                        segment
                    ))
                insert_query = """
                    INSERT INTO ohlc (instrument_token, symbol, interval, date, open, high, low, close, volume, segment)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cur.executemany(insert_query, batch_data)
                conn.commit()
            except Exception as e:
                logger.error(f"Error processing OHLC data for instrument {instrument_token}: {e}")
                return {"error": str(e)}
            finally:
                close_db_connection()
            return {"data": f"Inserted {len(batch_data)} rows"}
    
        return {"error": "No data found"}
    except Exception as e:
        logger.error(f"Unexpected error in get_ohlc: {e}")
        raise e
    finally:
        try:
            close_db_connection()
        except Exception as e:
            logger.error(f"Error closing DB connection: {e}")

def get_equity_ohlc_data_loop(interval):
    conn, cur = get_db_connection()  # Get connection and cursor
    try:
        select_query = "SELECT * FROM equity_tokens;"
        cur.execute(select_query)
        tokens = cur.fetchall()
        for token in tokens:
            get_ohlc(token[0], interval, token[1], token[4])
        return {"data": "Done"}
    except Exception as err:
        logger.error(f"Error in get_equity_ohlc_data_loop: {err}")
        return {"error": str(err)}
    finally:
        close_db_connection()

def get_indices_ohlc_data_loop(interval):
    conn, cur = get_db_connection()  # Get connection and cursor
    try:
        select_query = "SELECT * FROM indices_instruments;"
        cur.execute(select_query)
        tokens = cur.fetchall()
        for token in tokens:
            get_ohlc(token[0], interval, token[2], token[7])
        return {"data": "Done"}
    except Exception as err:
        logger.error(f"Error in get_indices_ohlc_data_loop: {err}")
        return {"error": str(err)}
    finally:
        close_db_connection()