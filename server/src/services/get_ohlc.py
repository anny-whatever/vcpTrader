import datetime
import time
import pandas as pd
import pandas_ta as ta
from controllers import kite
from db import get_db_connection, close_db_connection
from models import SaveOHLC

def delay(ms):
    """Delay function to simulate async pauses."""
    time.sleep(ms / 1000)

def get_ohlc(instrument_token, interval, symbol):
    conn, cur = get_db_connection()  # Get connection and cursor

    try:
        # Create table and delete old data
        SaveOHLC.delete_all(cur, instrument_token, interval)
    except Exception as err:
        return {"error": str(err)}

    if not kite.access_token:
        return {"error": "Access token not found"}

    loop_count = 1  # Number of 100-day windows
    hist = []
    to_date = datetime.datetime.now()  # Current date for the initial time window

    for _ in range(loop_count):
        # Define the time window for each request
        time_window_to = to_date.isoformat()[:10]
        time_window_from = (to_date - datetime.timedelta(days=700)).isoformat()[:10]
        print(time_window_from, time_window_to)

        try:
            # Request historical data from the Kite Connect API
            data = kite.historical_data(instrument_token, time_window_from, time_window_to, interval)

            if data:
                hist.extend(data)  # Accumulate the data across all requests

            print(f"Data from {time_window_from} to {time_window_to}")

        except Exception as err:
            return {"error": str(err)}

        # Update `to_date` for the next iteration (move back by 101 days)
        to_date = to_date - datetime.timedelta(days=701)

        # Delay to avoid overwhelming the API
        delay(200)

    # Deduplicate and sort the data by date
    if hist:
        hist = list({tuple(item.items()): item for item in hist}.values())  # Deduplicate by converting each dict to tuple
        hist.sort(key=lambda x: x['date'])  # Sort by 'date'
        hist = pd.DataFrame(hist)  # Convert to pandas DataFrame

        # Calculate simple moving averages

        print(hist)

        # Prepare data for batch insertion
        batch_data = []
        for _, row in hist.iterrows():
            batch_data.append(
                (
                    instrument_token,
                    symbol,
                    interval,
                    row['date'].isoformat() if isinstance(row['date'], (datetime.date, datetime.datetime)) else row['date'],
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume'],
                )
            )

        # Perform batch insert
        try:
            insert_query = """
                INSERT INTO ohlc (instrument_token, symbol, interval, date, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.executemany(insert_query, batch_data)
            conn.commit()  # Commit changes after batch insertion

        except Exception as err:
            return {"error": str(err)}

        return {"data": f"Inserted {len(batch_data)} rows"}

    return {"error": "No data found"}

def get_equity_ohlc_data_loop(interval):
    conn, cur = get_db_connection()  # Get connection and cursor

    try:
        select_query = "SELECT * FROM equity_tokens;"
        cur.execute(select_query)
        tokens = cur.fetchall()

        # print(tokens)
        for token in tokens:
            get_ohlc(token[0], interval, token[1])

        return {"data": "Done"}

    except Exception as err:
        return {"error": str(err)}

    finally:
        close_db_connection()  # Close connection in the end
