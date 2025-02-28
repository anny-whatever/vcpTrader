import logging
import pandas as pd
from datetime import datetime, timedelta
from db import get_ticker_db_connection, release_ticker_db_connection
from models import SaveResample
# We do NOT alter the NonTradableTicks model code. Instead we'll just query the DB directly.

logger = logging.getLogger(__name__)

def _fetch_nontradable_ticks(instrument_tokens, start_time, end_time):
    """
    Directly fetch non-tradable ticks from the DB for the given tokens and time range.
    Returns a list of tuples: (instrument_token, exchange_timestamp, last_price).
    """
    conn, cur = get_ticker_db_connection()
    rows = []
    try:
        # We'll do a direct SQL query on nontradable_ticks table
        # to avoid modifying the NonTradableTicks class.
        tokens_list = list(instrument_tokens)
        query = """
        SELECT instrument_token, exchange_timestamp, last_price
        FROM nontradable_ticks
        WHERE instrument_token = ANY(%s)
          AND exchange_timestamp >= %s
          AND exchange_timestamp < %s
        ORDER BY exchange_timestamp ASC;
        """
        cur.execute(query, (tokens_list, start_time, end_time))
        rows = cur.fetchall()
    except Exception as e:
        logger.error(f"Error fetching nontradable ticks: {e}")
    finally:
        release_ticker_db_connection(conn, cur)
    return rows

def _fetch_ohlc_data(instrument_tokens, interval, start_time, end_time):
    """
    Fetch previously resampled data (e.g., 1min) from 'ohlc_resampled'.
    Returns a pandas DataFrame or empty DataFrame.
    """
    from db import get_ticker_db_connection, release_ticker_db_connection
    import pandas as pd

    conn, cur = get_ticker_db_connection()
    df = pd.DataFrame()
    try:
        query = """
        SELECT instrument_token, time_stamp, open, high, low, close
        FROM ohlc_resampled
        WHERE instrument_token = ANY(%s)
          AND interval = %s
          AND time_stamp >= %s
          AND time_stamp < %s
        ORDER BY time_stamp ASC;
        """
        cur.execute(query, (list(instrument_tokens), interval, start_time, end_time))
        rows = cur.fetchall()
        if rows:
            df = pd.DataFrame(rows, columns=[
                'instrument_token','time_stamp','open','high','low','close'
            ])
            df['time_stamp'] = pd.to_datetime(df['time_stamp'])
    except Exception as e:
        logger.error(f"Error fetching {interval} data from ohlc_resampled: {e}")
    finally:
        release_ticker_db_connection(conn, cur)

    return df

def calculate_ohlcv_1min(instrument_tokens, start_time, end_time):
    """
    1-min resampling from raw nontradable_ticks data.
    """
    # We'll create a fresh DB connection just for saving
    conn, cur = get_ticker_db_connection()
    try:
        SaveResample.create_table_ohlc_resampled(cur)

        # 1) Fetch raw non-tradable ticks
        rows = _fetch_nontradable_ticks(instrument_tokens, start_time, end_time)
        if not rows:
            logger.info("No nontradable ticks found for 1-min resampling.")
            return

        # 2) Convert to DataFrame
        df = pd.DataFrame(rows, columns=['instrument_token','exchange_timestamp','last_price'])
        df['exchange_timestamp'] = pd.to_datetime(df['exchange_timestamp'])

        # 3) Group by instrument_token & resample
        for token, group_df in df.groupby('instrument_token'):
            group_df.set_index('exchange_timestamp', inplace=True)
            ohlc = group_df['last_price'].resample('1min').agg(['first','max','min','last'])
            ohlc.dropna(how='all', inplace=True)
            if ohlc.empty:
                continue

            # 4) Save each row in 'ohlc_resampled'
            for ts, row in ohlc.iterrows():
                SaveResample.save_ohlc_resampled(
                    cur,
                    instrument_token=token,
                    time_stamp=ts,
                    open_price=row['first'],
                    high_price=row['max'],
                    low_price=row['min'],
                    close_price=row['last'],
                    interval='1min'
                )
        conn.commit()
        logger.info("1-min candles saved into 'ohlc_resampled'.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in calculate_ohlcv_1min: {e}")
    finally:
        release_ticker_db_connection(conn, cur)

def calculate_ohlcv_5min(instrument_tokens, start_time, end_time):
    """
    5-min resampling from previously saved 1-min data in 'ohlc_resampled'.
    """
    conn, cur = get_ticker_db_connection()
    try:
        SaveResample.create_table_ohlc_resampled(cur)

        df_1m = _fetch_ohlc_data(instrument_tokens, '1min', start_time, end_time)
        if df_1m.empty:
            logger.info("No 1-min data found for 5-min resampling.")
            return

        for token, group_df in df_1m.groupby('instrument_token'):
            group_df.set_index('time_stamp', inplace=True)
            ohlc = group_df[['open','high','low','close']].resample('5min').agg({
                'open':'first',
                'high':'max',
                'low':'min',
                'close':'last'
            })
            ohlc.dropna(how='all', inplace=True)
            if ohlc.empty:
                continue

            for ts, row in ohlc.iterrows():
                SaveResample.save_ohlc_resampled(
                    cur,
                    instrument_token=token,
                    time_stamp=ts,
                    open_price=row['open'],
                    high_price=row['high'],
                    low_price=row['low'],
                    close_price=row['close'],
                    interval='5min'
                )
        conn.commit()
        logger.info("5-min candles saved into 'ohlc_resampled'.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in calculate_ohlcv_5min: {e}")
    finally:
        release_ticker_db_connection(conn, cur)

def calculate_ohlcv_15min(instrument_tokens, start_time, end_time):
    """
    15-min resampling from previously saved 1-min data in 'ohlc_resampled'.
    """
    conn, cur = get_ticker_db_connection()
    try:
        SaveResample.create_table_ohlc_resampled(cur)

        df_1m = _fetch_ohlc_data(instrument_tokens, '1min', start_time, end_time)
        if df_1m.empty:
            logger.info("No 1-min data found for 15-min resampling.")
            return

        for token, group_df in df_1m.groupby('instrument_token'):
            group_df.set_index('time_stamp', inplace=True)
            ohlc = group_df[['open','high','low','close']].resample('15min').agg({
                'open':'first',
                'high':'max',
                'low':'min',
                'close':'last'
            })
            ohlc.dropna(how='all', inplace=True)
            if ohlc.empty:
                continue

            for ts, row in ohlc.iterrows():
                SaveResample.save_ohlc_resampled(
                    cur,
                    instrument_token=token,
                    time_stamp=ts,
                    open_price=row['open'],
                    high_price=row['high'],
                    low_price=row['low'],
                    close_price=row['close'],
                    interval='15min'
                )
        conn.commit()
        logger.info("15-min candles saved into 'ohlc_resampled'.")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error in calculate_ohlcv_15min: {e}")
    finally:
        release_ticker_db_connection(conn, cur)
