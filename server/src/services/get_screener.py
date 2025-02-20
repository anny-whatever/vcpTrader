# get_screener.py
import threading
import datetime
import pandas as pd
import pandas_ta as ta
import pytz
import logging
from controllers import kite
from db import get_db_connection, close_db_connection

logger = logging.getLogger(__name__)
TIMEZONE = pytz.timezone("Asia/Kolkata")
ohlc_data = None  # Global DataFrame holding precomputed OHLC data with indicators
ohlc_data_lock = threading.Lock()  # Lock for thread-safe access

def load_ohlc_data():
    """
    Fetch OHLC data from the database, convert numeric columns,
    and compute historical indicators for each instrument token.
    """
    global ohlc_data
    with ohlc_data_lock:
        conn, cur = get_db_connection()
        try:
            query = "SELECT * FROM ohlc WHERE segment != 'ALL'"
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
                group = group.fillna(0)
                groups.append(group)

            ohlc_data = pd.concat(groups, ignore_index=True)
            return ohlc_data
        except Exception as err:
            logger.error(f"Error fetching OHLC data: {err}")
            return pd.DataFrame()
        finally:
            close_db_connection()

def fetch_live_quotes(batch_size=1000):
    """
    Fetch live quote data for all instrument tokens from the equity_tokens table in batches
    to avoid exceeding the URL length limit.
    
    Args:
        batch_size (int): Number of tokens to fetch in a single request. Defaults to 250.
    
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
        # Process tokens in batches
        for i in range(0, len(instrument_tokens), batch_size):
            batch = instrument_tokens[i:i+batch_size]
            # Fetch quotes for this batch
            live_quotes = kite.quote(batch)
            # Merge batch results into the main dictionary
            live_quotes_all.update({
                int(token): live_quotes[token]["last_price"] for token in live_quotes
            })

        return live_quotes_all
    except Exception as err:
        logger.error(f"Error fetching live quotes in get_screener: {err}")
        return {}
    finally:
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
            live_price = live_data[token]
            last_row = group.iloc[-1]

            # Construct new row using the last historical row and the live price
            new_row = {
                "instrument_token": token,
                "symbol": last_row["symbol"],
                "interval": last_row["interval"],
                "date": datetime.datetime.now(TIMEZONE),
                "open": last_row["close"],
                "high": max(last_row["close"], live_price),
                "low": min(last_row["close"], live_price),
                "close": live_price,
                "volume": 0,
                "segment": last_row["segment"]
            }

            group_updated = pd.concat([group, pd.DataFrame([new_row])], ignore_index=True)
            len_group = len(group_updated)

            # Determine window lengths
            win_50 = min(50, len_group)
            win_150 = min(150, len_group)
            win_200 = min(200, len_group)
            win_252 = min(252, len_group)

            # Compute indicators for the new (last) row
            sma_50 = ta.sma(group_updated["close"].tail(win_50), length=win_50).iloc[-1]
            sma_150 = ta.sma(group_updated["close"].tail(win_150), length=win_150).iloc[-1]
            sma_200 = ta.sma(group_updated["close"].tail(win_200), length=win_200).iloc[-1]
            atr_val = ta.atr(
                group_updated["high"],
                group_updated["low"],
                group_updated["close"],
                length=win_50
            ).iloc[-1]
            week_high = group_updated["high"].tail(win_252).max()
            week_low = group_updated["low"].tail(win_252).min()
            away_high = ((week_high - live_price) / week_high) * 100 if week_high != 0 else 0
            away_low = ((live_price - week_low) / week_low) * 100 if week_low != 0 else 0

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

        # Use live quotes only during market hours
        START_TIME = datetime.time(9, 15)
        END_TIME = datetime.time(15, 30, 5)
        now = datetime.datetime.now(TIMEZONE).time()
        live_data = fetch_live_quotes() if (START_TIME <= now <= END_TIME) else {}

        # Exclude IPO stocks for VCP screening
        data_to_screen = ohlc_data[ohlc_data['segment'] != 'IPO']

        # Update only the latest rows if live data is available
        if live_data:
            data_to_screen = update_live_data(data_to_screen, live_data)

        eligible_stocks = []
        for symbol, group in data_to_screen.groupby("symbol"):
            group = group.sort_values("date").reset_index(drop=True)
            if len(group) < 2:
                continue
            last_index = len(group) - 1

            # Screening criteria
            if (
                group.iloc[last_index]["close"] > group.iloc[last_index]["sma_50"] and
                group.iloc[last_index]["sma_50"] > group.iloc[last_index]["sma_150"] > group.iloc[last_index]["sma_200"] and
                group.iloc[max(0, last_index - 25)]["sma_200"] < group.iloc[last_index]["sma_200"] and
                group.iloc[last_index]["away_from_high"] < 25 and
                group.iloc[last_index]["away_from_low"] > 50
            ):
                eligible_stocks.append({
                    "instrument_token": int(group.iloc[last_index]["instrument_token"]),
                    "symbol": symbol,
                    "last_price": float(group.iloc[last_index]["close"]),
                    "change": (
                        (float(group.iloc[last_index]["close"]) - float(group.iloc[last_index - 1]["close"]))
                        / float(group.iloc[last_index - 1]["close"])
                    ) * 100,
                    "sma_50": float(group.iloc[last_index]["sma_50"]),
                    "sma_150": float(group.iloc[last_index]["sma_150"]),
                    "sma_200": float(group.iloc[last_index]["sma_200"]),
                    "atr": float(group.iloc[last_index]["atr"]),
                })

        # Sort by percentage change descending
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

            # Simplified IPO screening criteria
            if (
                group.iloc[last_index]["away_from_high"] < 25 and
                group.iloc[last_index]["away_from_low"] > 25
            ):
                eligible_stocks.append({
                    "instrument_token": int(group.iloc[last_index]["instrument_token"]),
                    "symbol": symbol,
                    "last_price": float(group.iloc[last_index]["close"] or 0),
                    "change": (
                        (float(group.iloc[last_index]["close"]) - float(group.iloc[last_index - 1]["close"]))
                        / float(group.iloc[last_index - 1]["close"])
                    ) * 100,
                    "sma_50": float(group.iloc[last_index]["sma_50"] or 0),
                    "sma_150": float(group.iloc[last_index]["sma_150"] or 0),
                    "sma_200": float(group.iloc[last_index]["sma_200"] or 0),
                    "atr": float(group.iloc[last_index]["atr"] or 0),
                })

        # Sort by percentage change descending
        eligible_stocks.sort(key=lambda x: x["change"], reverse=True)
        return eligible_stocks
    except Exception as e:
        logger.error(f"Error screening eligible stocks for IPO: {e}")
        raise e
