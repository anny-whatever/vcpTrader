# get_screener.py

import threading
import datetime
import pandas as pd
import pandas_ta as ta
import pytz
import logging
import math

from controllers import kite
from db import get_db_connection, close_db_connection

logger = logging.getLogger(__name__)
TIMEZONE = pytz.timezone("Asia/Kolkata")

# Global DataFrame holding precomputed OHLC data with indicators
ohlc_data = None
# Lock for thread-safe access
ohlc_data_lock = threading.Lock()

def safe_float(value, default=0.0):
    """
    Utility to convert a value to float safely.
    Returns `default` if the value is NaN, infinite, or otherwise invalid.
    """
    try:
        val = float(value)
        return val if math.isfinite(val) else default
    except (TypeError, ValueError):
        return default

def load_ohlc_data():
    """
    Fetch OHLC data from the database, convert numeric columns,
    and compute historical indicators for each instrument token.
    """
    global ohlc_data
    with ohlc_data_lock:
        conn, cur = get_db_connection()
        try:
            # Modified query to select only the required columns.
            query = """
            SELECT instrument_token, symbol, interval, date, open, high, low, close, volume, segment
            FROM (
                SELECT 
                    *,
                    ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) AS rn
                FROM ohlc
                WHERE segment != 'ALL'
            ) sub
            WHERE rn <= 450;
            """
            cur.execute(query)
            data = cur.fetchall()
            df = pd.DataFrame(
                data,
                columns=["instrument_token", "symbol", "interval", "date", "open", "high", "low", "close", "volume", "segment"]
            )
            # Convert numeric columns to float and parse dates.
            for col in ["open", "high", "low", "close", "volume"]:
                df[col] = df[col].astype(float)
            df["date"] = pd.to_datetime(df["date"])

            # Compute technical indicators for each instrument token.
            groups = []
            for token, group in df.groupby("instrument_token"):
                group = group.sort_values("date").reset_index(drop=True)
                group["sma_50"] = ta.sma(group["close"], length=min(50, len(group)))
                group["sma_150"] = ta.sma(group["close"], length=min(150, len(group)))
                group["sma_200"] = ta.sma(group["close"], length=min(200, len(group)))
                group["atr"] = ta.atr(group["high"], group["low"], group["close"], length=min(50, len(group)))
                group["52_week_high"] = group["high"].rolling(window=min(252, len(group)), min_periods=1).max()
                group["52_week_low"] = group["low"].rolling(window=min(252, len(group)), min_periods=1).min()
                group["away_from_high"] = ((group["52_week_high"] - group["close"]) / group["52_week_high"]) * 100
                group["away_from_low"] = ((group["close"] - group["52_week_low"]) / group["52_week_low"]) * 100
                # Replace NaN/inf with 0 to keep things finite
                group = group.fillna(0)
                for col in [
                    "sma_50", "sma_150", "sma_200", "atr",
                    "52_week_high", "52_week_low", "away_from_high", "away_from_low"
                ]:
                    group[col] = group[col].apply(lambda x: safe_float(x, 0.0))
                groups.append(group)

            ohlc_data = pd.concat(groups, ignore_index=True)
            logger.info(f"OHLC data fetched: {len(ohlc_data)} rows.")
            return ohlc_data
        except Exception as err:
            logger.error(f"Error fetching OHLC data: {err}")
            return pd.DataFrame()
        finally:
            if conn and cur:
                close_db_connection()

def fetch_live_quotes(batch_size=250):
    """
    Fetch live quote data for all instrument tokens from the equity_tokens table in batches
    to avoid exceeding the URL length limit.
    
    Args:
        batch_size (int): Number of tokens to fetch in a single request.
    
    Returns:
        dict: Mapping from instrument_token to its last_price.
    """
    conn, cur = get_db_connection()
    try:
        query = "SELECT instrument_token FROM equity_tokens;"
        cur.execute(query)
        tokens = cur.fetchall()
        instrument_tokens = [int(token[0]) for token in tokens]

        live_quotes_all = {}
        # Process tokens in batches.
        for i in range(0, len(instrument_tokens), batch_size):
            batch = instrument_tokens[i:i+batch_size]
            # Fetch quotes for this batch.
            live_quotes = kite.quote(batch)
            # Merge batch results into the main dictionary.
            for tkn in live_quotes:
                last_price = live_quotes[tkn].get("last_price", 0.0)
                live_quotes_all[int(tkn)] = safe_float(last_price, 0.0)

        return live_quotes_all
    except Exception as err:
        logger.error(f"Error fetching live quotes in get_screener: {err}")
        return {}
    finally:
        if conn and cur:
            close_db_connection()

def update_live_data(existing_data, live_data):
    """
    For each instrument token with a live quote, append a new live data row
    and recalculate the indicator values only for the new row using an appropriate tail window.
    """
    updated_groups = []
    for token, group in existing_data.groupby("instrument_token"):
        group = group.sort_values("date").reset_index(drop=True)
        if token in live_data:
            live_price = safe_float(live_data[token], 0.0)
            last_row = group.iloc[-1]

            # Construct new row using the last historical row and the live price.
            new_row = {
                "instrument_token": token,
                "symbol": last_row["symbol"],
                "interval": last_row["interval"],
                "date": datetime.datetime.now(TIMEZONE),
                "open": safe_float(last_row["close"], 0.0),
                "high": max(safe_float(last_row["close"], 0.0), live_price),
                "low": min(safe_float(last_row["close"], 0.0), live_price),
                "close": live_price,
                "volume": 0,
                "segment": last_row["segment"]
            }

            group_updated = pd.concat([group, pd.DataFrame([new_row])], ignore_index=True)
            len_group = len(group_updated)

            # Determine window lengths.
            win_50 = min(50, len_group)
            win_150 = min(150, len_group)
            win_200 = min(200, len_group)
            win_252 = min(252, len_group)

            # Compute indicators for the new (last) row.
            sma_50_series = ta.sma(group_updated["close"].tail(win_50), length=win_50)
            sma_50 = safe_float(sma_50_series.iloc[-1] if not sma_50_series.empty else 0.0)
            
            sma_150_series = ta.sma(group_updated["close"].tail(win_150), length=win_150)
            sma_150 = safe_float(sma_150_series.iloc[-1] if not sma_150_series.empty else 0.0)
            
            sma_200_series = ta.sma(group_updated["close"].tail(win_200), length=win_200)
            sma_200 = safe_float(sma_200_series.iloc[-1] if not sma_200_series.empty else 0.0)

            atr_series = ta.atr(
                group_updated["high"].tail(win_50),
                group_updated["low"].tail(win_50),
                group_updated["close"].tail(win_50),
                length=win_50
            )
            atr_val = safe_float(atr_series.iloc[-1] if not atr_series.empty else 0.0)

            week_high = safe_float(group_updated["high"].tail(win_252).max(), 0.0)
            week_low = safe_float(group_updated["low"].tail(win_252).min(), 0.0)

            away_high = 0.0
            if week_high != 0.0:
                away_high = safe_float(((week_high - live_price) / week_high) * 100, 0.0)
            away_low = 0.0
            if week_low != 0.0:
                away_low = safe_float(((live_price - week_low) / week_low) * 100, 0.0)

            # Update the new row in the group
            group_updated.at[len_group - 1, "sma_50"] = sma_50
            group_updated.at[len_group - 1, "sma_150"] = sma_150
            group_updated.at[len_group - 1, "sma_200"] = sma_200
            group_updated.at[len_group - 1, "atr"] = atr_val
            group_updated.at[len_group - 1, "52_week_high"] = week_high
            group_updated.at[len_group - 1, "52_week_low"] = week_low
            group_updated.at[len_group - 1, "away_from_high"] = away_high
            group_updated.at[len_group - 1, "away_from_low"] = away_low

            updated_groups.append(group_updated)
        else:
            updated_groups.append(group)
    return pd.concat(updated_groups, ignore_index=True)

def screen_eligible_stocks_vcp():
    """
    Screen non-IPO stocks (VCP pattern) using precomputed indicators.
    During market hours, update the latest data using live quotes.
    """
    global ohlc_data
    try:
        if ohlc_data is None or ohlc_data.empty:
            ohlc_data = load_ohlc_data()

        # Use live quotes only during market hours.
        START_TIME = datetime.time(9, 15)
        END_TIME = datetime.time(15, 30, 5)
        now = datetime.datetime.now(TIMEZONE).time()
        live_data = fetch_live_quotes() if (START_TIME <= now <= END_TIME) else {}

        # Exclude IPO stocks for VCP screening.
        data_to_screen = ohlc_data[ohlc_data['segment'] != 'IPO']

        # Update only the latest rows if live data is available.
        if live_data:
            data_to_screen = update_live_data(data_to_screen, live_data)

        eligible_stocks = []
        for symbol, group in data_to_screen.groupby("symbol"):
            group = group.sort_values("date").reset_index(drop=True)
            if len(group) < 2:
                continue
            last_index = len(group) - 1

            last_row = group.iloc[last_index]
            prev_row = group.iloc[last_index - 1]

            # Safely compute the change
            prev_close = safe_float(prev_row["close"], 0.0)
            current_close = safe_float(last_row["close"], 0.0)
            if prev_close == 0.0:
                price_change = 0.0
            else:
                price_change = ((current_close - prev_close) / prev_close) * 100.0

            # Screening criteria
            if (
                current_close > safe_float(last_row["sma_50"]) and
                safe_float(last_row["sma_50"]) > safe_float(last_row["sma_150"]) > safe_float(last_row["sma_200"]) and
                safe_float(group.iloc[max(0, last_index - 25)]["sma_200"]) < safe_float(last_row["sma_200"]) and
                safe_float(last_row["away_from_high"]) < 25 and
                safe_float(last_row["away_from_low"]) > 50
            ):
                eligible_stocks.append({
                    "instrument_token": int(safe_float(last_row["instrument_token"], 0)),
                    "symbol": str(last_row["symbol"]),
                    "last_price": current_close,
                    "change": price_change,
                    "sma_50": safe_float(last_row["sma_50"]),
                    "sma_150": safe_float(last_row["sma_150"]),
                    "sma_200": safe_float(last_row["sma_200"]),
                    "atr": safe_float(last_row["atr"]),
                })

        # Sort by percentage change descending.
        eligible_stocks.sort(key=lambda x: x["change"], reverse=True)
        return eligible_stocks
    except Exception as e:
        logger.error(f"Error screening eligible stocks for VCP: {e}")
        raise e

def screen_eligible_stocks_ipo():
    """
    Screen IPO stocks using simplified criteria.
    During market hours, update the latest data using live quotes.
    """
    global ohlc_data
    try:
        if ohlc_data is None or ohlc_data.empty:
            ohlc_data = load_ohlc_data()

        START_TIME = datetime.time(9, 15)
        END_TIME = datetime.time(15, 30, 5)
        now = datetime.datetime.now(TIMEZONE).time()
        live_data = fetch_live_quotes() if (START_TIME <= now <= END_TIME) else {}

        data_to_screen = ohlc_data[ohlc_data['segment'] == 'IPO']

        if live_data:
            data_to_screen = update_live_data(data_to_screen, live_data)

        eligible_stocks = []
        for symbol, group in data_to_screen.groupby("symbol"):
            group = group.sort_values("date").reset_index(drop=True)
            if len(group) < 2:
                continue
            last_index = len(group) - 1

            last_row = group.iloc[last_index]
            prev_row = group.iloc[last_index - 1]

            # Safely compute the change
            prev_close = safe_float(prev_row["close"], 0.0)
            current_close = safe_float(last_row["close"], 0.0)
            if prev_close == 0.0:
                price_change = 0.0
            else:
                price_change = ((current_close - prev_close) / prev_close) * 100.0

            # Simplified IPO screening criteria
            if (
                safe_float(last_row["away_from_high"]) < 25 and
                safe_float(last_row["away_from_low"]) > 25
            ):
                eligible_stocks.append({
                    "instrument_token": int(safe_float(last_row["instrument_token"], 0)),
                    "symbol": str(last_row["symbol"]),
                    "last_price": current_close,
                    "change": price_change,
                    "sma_50": safe_float(last_row["sma_50"]),
                    "sma_150": safe_float(last_row["sma_150"]),
                    "sma_200": safe_float(last_row["sma_200"]),
                    "atr": safe_float(last_row["atr"]),
                })

        # Sort by percentage change descending.
        eligible_stocks.sort(key=lambda x: x["change"], reverse=True)
        return eligible_stocks
    except Exception as e:
        logger.error(f"Error screening eligible stocks for IPO: {e}")
        raise e
