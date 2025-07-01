import datetime
import time
import pandas as pd
import pandas_ta as ta
import logging
from controllers.kite_auth import kite  # Direct import to avoid circular dependency
from db import get_db_connection, close_db_connection
from models import SaveOHLC

logger = logging.getLogger(__name__)

def delay(ms):
    """Delay function to simulate async pauses."""
    time.sleep(ms / 1000)

def get_ohlc(instrument_token, interval, symbol, segment):
    """
    Fetch and save OHLC data for a single instrument_token + interval.
    This version deletes existing rows, fetches fresh data from Kite,
    computes indicators, and saves everything into the `ohlc` table.
    """
    conn, cur = get_db_connection()  # Get connection and cursor
    try: 
        if not kite.access_token:
            logger.error(f"Missing Kite access token for {symbol} ({instrument_token})")
            return {"error": "Access token not found"}
        else:
            logger.info(f"Found valid Kite access token, proceeding with data fetch for {symbol}")
    
        loop_count = 1  # Number of 100-day windows or any chunk window you want
        hist = []
        to_date = datetime.datetime.now()  # Current date for the initial time window
        logger.info(f"Starting OHLC fetch for {symbol} ({instrument_token}), current date: {to_date.isoformat()}")

        
        if interval == "week":
            day_count = 2000
            loop_count = 3
        else:
            day_count = 500
            loop_count = 2
        logger.info(f"Using day_count of {day_count} for interval {interval}")

        # 2) Fetch historical data from the API
        for i in range(loop_count):
            time_window_to = to_date.isoformat()[:10]
            # Example: fetch ~2000 days in one go if your subscription/data source allows
            time_window_from = (to_date - datetime.timedelta(days=day_count)).isoformat()[:10]
            logger.info(f"Fetching OHLC data from {time_window_from} to {time_window_to} "
                        f"for instrument {instrument_token}, loop {i+1}/{loop_count}")
            try:
                logger.info(f"Calling kite.historical_data for {symbol} ({instrument_token})")
                data = kite.historical_data(
                    instrument_token,
                    time_window_from,
                    time_window_to,
                    interval
                )
                logger.info(f"Received response from kite.historical_data, data length: {len(data) if data else 0}")
                if data:
                    hist.extend(data)
                    logger.info(f"Added {len(data)} records, total records: {len(hist)}")
                else:
                    logger.warning(f"No data returned from kite.historical_data for {symbol} ({instrument_token})")
            except Exception as err:
                logger.error(f"Error fetching OHLC data for instrument {instrument_token}: {err}")
                return {"error": str(err)}
            # Move our 'to_date' pointer back another block of days
            to_date = to_date - datetime.timedelta(days=day_count + 1)
            logger.info(f"Waiting 200ms before next request, new to_date: {to_date.isoformat()}")
            delay(200)
    
        # 3) Process and insert into database
        if hist:
            logger.info(f"Processing {len(hist)} records for {symbol} ({instrument_token})")
            try:
                # Remove duplicates if any
                old_len = len(hist)
                hist = list({tuple(item.items()): item for item in hist}.values())
                logger.info(f"Removed {old_len - len(hist)} duplicate records")
                
                # Sort by date ascending
                hist.sort(key=lambda x: x['date'])
                logger.info(f"Sorted {len(hist)} records by date")
                
                hist = pd.DataFrame(hist)
                logger.info(f"Created DataFrame with shape {hist.shape}")

                # Log the head of the fetched data
                logger.info(f"Fetched OHLC data for {symbol} ({instrument_token}), interval: {interval}")
                logger.info(f"Data shape: {hist.shape}")
                logger.info(f"Data head:\n{hist.head().to_string()}")

                # Convert to appropriate data types
                # (Kite data is typically numeric in open/high/low/close/volume, but confirm as needed)
                hist["open"] = hist["open"].astype(float)
                hist["high"] = hist["high"].astype(float)
                hist["low"] = hist["low"].astype(float)
                hist["close"] = hist["close"].astype(float)
                hist["volume"] = hist["volume"].astype(float)
                logger.info(f"Converted data types to float for numeric columns")
                
                # ---- Compute Indicators ----
                # Use rolling windows that don't exceed the length of the dataset
                length_50 = min(50, len(hist))
                length_100 = min(100, len(hist))
                length_200 = min(200, len(hist))
                length_252 = min(252, len(hist))
                
                logger.info(f"Computing technical indicators with adjusted lengths: SMA50={length_50}, SMA100={length_100}, SMA200={length_200}, 52W={length_252}")
                
                hist["sma_50"] = ta.sma(hist["close"], length=length_50)
                hist["sma_100"] = ta.sma(hist["close"], length=length_100)
                hist["sma_200"] = ta.sma(hist["close"], length=length_200)
                hist["atr"] = ta.atr(
                    hist["high"],
                    hist["low"],
                    hist["close"],
                    length=length_50
                )

                hist["52_week_high"] = (
                    hist["high"].rolling(window=length_252, min_periods=1).max()
                )
                hist["52_week_low"] = (
                    hist["low"].rolling(window=length_252, min_periods=1).min()
                )

                hist["away_from_high"] = (
                    (hist["52_week_high"] - hist["close"]) / hist["52_week_high"] * 100
                )
                hist["away_from_low"] = (
                    (hist["close"] - hist["52_week_low"]) / hist["52_week_low"] * 100
                )
                logger.info(f"Computed all technical indicators successfully")

                # Replace NaN or infinite values with 0
                hist = hist.fillna(0)
                hist.replace([float('inf'), float('-inf')], 0, inplace=True)
                logger.info(f"Replaced NaN and infinite values with 0")

                # Log the processed data head with indicators
                logger.info(f"Processed OHLC data with indicators for {symbol}:")
                logger.info(f"Processed data head:\n{hist.head().to_string()}")

                # 4) Prepare data for insertion into `ohlc` table (with new columns)
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
                        segment,
                        row["sma_50"],
                        row["sma_100"],
                        row["sma_200"],
                        row["atr"],
                        row["52_week_high"],
                        row["52_week_low"],
                        row["away_from_high"],
                        row["away_from_low"]
                    ))
                logger.info(f"Prepared {len(batch_data)} rows for database insertion")

                # Make sure your `ohlc` table has these extra columns
                insert_query = """
                    INSERT INTO ohlc (
                        instrument_token, symbol, interval, date,
                        open, high, low, close, volume, segment,
                        sma_50, sma_100, sma_200, atr,
                        "52_week_high", "52_week_low",
                        away_from_high, away_from_low
                    )
                    VALUES (%s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s,
                            %s, %s)
                """

                logger.info(f"Executing database insert for {len(batch_data)} rows")
                cur.executemany(insert_query, batch_data)
                conn.commit()
                logger.info(f"Successfully inserted {len(batch_data)} rows for {symbol} ({instrument_token})")

                return {"data": f"Inserted {len(batch_data)} rows with technical indicators."}

            except Exception as e:
                logger.error(f"Error processing OHLC data for instrument {instrument_token}: {e}")
                return {"error": str(e)}
        else:
            logger.warning(f"No data found for {symbol} ({instrument_token}), interval: {interval}")
            return {"error": "No data found"}
    except Exception as e:
        logger.error(f"Unexpected error in get_ohlc: {e}")
        raise e
    finally:
        # Ensure the DB connection is closed even if there's an error
        try:
            if conn and cur:
                logger.info(f"Closing database connection for {symbol} ({instrument_token})")
                close_db_connection()
        except Exception as e:
            logger.error(f"Error closing DB connection: {e}")


def get_equity_ohlc_data_loop(interval):
    conn, cur = get_db_connection()  # Get connection and cursor
    try:
        SaveOHLC.delete_by_interval(cur, interval)
        logger.info(f"Successfully deleted data for interval: {interval}")
    except Exception as err:
        logger.error(f"Error deleting OHLC data: {err}")
        return {"error": str(err)}
    try:
        select_query = "SELECT * FROM equity_tokens;"
        cur.execute(select_query)
        tokens = cur.fetchall()
        #Remove existing OHLC data for this token + interval (if that's your desired logic)
        
        for token in tokens:
        # for token in tokens[:1]:
            get_ohlc(token[0], interval, token[1], token[4])
        return {"data": "Done"}
    except Exception as err:
        logger.error(f"Error in get_equity_ohlc_data_loop: {err}")
        return {"error": str(err)}
    finally:
        if conn and cur:
            close_db_connection()

