import datetime
import pandas as pd
import pandas_ta as ta
import pytz
import logging
import math
from controllers import kite

# Use your threaded DB pool
from db import get_trade_db_connection, release_trade_db_connection

# Import your models
from models import ScreenerResult
from models import SaveOHLC

logger = logging.getLogger(__name__)
TIMEZONE = pytz.timezone("Asia/Kolkata")

# We maintain a global cached copy of OHLC data, but no locking is used.
ohlc_data = None

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

def load_precomputed_ohlc():
    """
    Loads precomputed OHLC data (with indicators) from the database
    using SaveOHLC.fetch_precomputed_ohlc(...).
    Caches the DataFrame globally in `ohlc_data`.
    """
    logger.info("Loading precomputed OHLC data via SaveOHLC class...")
    global ohlc_data

    conn, cur = get_trade_db_connection()
    try:
        df = SaveOHLC.fetch_precomputed_ohlc(cur, limit=260)
        logger.info(f"Fetched {len(df)} rows from fetch_precomputed_ohlc.")
        ohlc_data = df
        return ohlc_data
    except Exception as e:
        logger.error(f"Error loading precomputed data: {e}")
        return pd.DataFrame()
    finally:
        release_trade_db_connection(conn, cur)

def fetch_live_quotes(batch_size=250):
    """
    Fetch live quote data from the 'equity_tokens' table in batches.
    Returns {instrument_token: last_price} mapping.
    """
    logger.info("Fetching live quotes from kite...")
    live_quotes_all = {}
    conn, cur = get_trade_db_connection()
    try:
        query = "SELECT instrument_token FROM equity_tokens;"
        cur.execute(query)
        tokens = cur.fetchall()
        instrument_tokens = [int(t[0]) for t in tokens]
        logger.debug(f"Found {len(instrument_tokens)} tokens to fetch quotes for.")

        for i in range(0, len(instrument_tokens), batch_size):
            batch = instrument_tokens[i:i+batch_size]
            logger.debug(f"Fetching quotes for batch of size {len(batch)}.")
            try:
                quotes = kite.quote(batch)
                for tkn, quote_data in quotes.items():
                    last_price = quote_data.get("last_price", 0.0)
                    live_quotes_all[int(tkn)] = safe_float(last_price, 0.0)
            except Exception as e:
                logger.error(f"Error fetching live quotes for batch {batch}: {e}")

        logger.info(f"Fetched live quotes for {len(live_quotes_all)} tokens.")
        return live_quotes_all
    except Exception as err:
        logger.error(f"Error fetching live quotes: {err}")
        return {}
    finally:
        release_trade_db_connection(conn, cur)

def update_live_data(df, live_data):
    """
    For each instrument token with a live quote, add a new row
    updating 'close' with the current price, then recalc
    ATR, 52-week highs, etc. for that row.
    """
    if df.empty:
        logger.warning("update_live_data called with empty DataFrame; returning as is.")
        return df
    if not live_data:
        logger.debug("No live data to update; returning original DataFrame.")
        return df

    logger.debug("Starting to update live data for each instrument token in df.")
    updated_groups = []

    for token, group in df.groupby("instrument_token"):
        group = group.sort_values("date").reset_index(drop=True)
        if token not in live_data:
            updated_groups.append(group)
            continue

        live_price = live_data[token]
        last_row = group.iloc[-1]

        # Build new row with the updated close.
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
            "segment": last_row["segment"],
            # Old indicators
            "sma_50": last_row["sma_50"],
            "sma_150": last_row["sma_150"],
            "sma_200": last_row["sma_200"],
            "atr": last_row["atr"],
            "52_week_high": last_row["52_week_high"],
            "52_week_low": last_row["52_week_low"],
            "away_from_high": last_row["away_from_high"],
            "away_from_low": last_row["away_from_low"],
        }

        group_updated = pd.concat([group, pd.DataFrame([new_row])], ignore_index=True)

        # Recompute ATR over the last 50 rows
        tail_window = 50
        subset = group_updated.tail(tail_window).copy()
        new_atr_series = ta.atr(
            high=subset["high"],
            low=subset["low"],
            close=subset["close"],
            length=min(tail_window, len(subset))
        )
        new_atr_val = safe_float(new_atr_series.iloc[-1] if not new_atr_series.empty else 0.0)

        # Recompute 52-week highs/lows over last 252 rows
        subset_252 = group_updated.tail(252)
        new_52_high = safe_float(subset_252["high"].max())
        new_52_low = safe_float(subset_252["low"].min())
        away_high = 0.0
        away_low = 0.0
        if new_52_high != 0:
            away_high = ((new_52_high - live_price) / new_52_high) * 100
        if new_52_low != 0:
            away_low = ((live_price - new_52_low) / new_52_low) * 100

        last_idx = len(group_updated) - 1
        group_updated.at[last_idx, "atr"] = new_atr_val
        group_updated.at[last_idx, "52_week_high"] = new_52_high
        group_updated.at[last_idx, "52_week_low"] = new_52_low
        group_updated.at[last_idx, "away_from_high"] = away_high
        group_updated.at[last_idx, "away_from_low"] = away_low

        updated_groups.append(group_updated)

    df_updated = pd.concat(updated_groups, ignore_index=True)
    logger.debug("Finished updating live data.")
    return df_updated

def screen_eligible_stocks_vcp(df):
    """
    Returns a list of dicts representing VCP-eligible stocks from 'df'.
    """
    logger.debug("Screening stocks for VCP pattern...")
    data_to_screen = df[df["segment"] != "IPO"]  # exclude IPO
    eligible_stocks = []

    for symbol, group in data_to_screen.groupby("symbol"):
        group = group.sort_values("date").reset_index(drop=True)
        if len(group) < 2:
            continue

        last_index = len(group) - 1
        last_row = group.iloc[last_index]
        prev_row = group.iloc[last_index - 1]

        current_close = safe_float(last_row["close"])
        prev_close = safe_float(prev_row["close"])
        price_change = 0.0
        if prev_close != 0:
            price_change = ((current_close - prev_close) / prev_close) * 100.0

        # VCP screening logic
        if (
            current_close > last_row["sma_50"]
            and last_row["sma_50"] > last_row["sma_150"] > last_row["sma_200"]
            and safe_float(group.iloc[max(0, last_index - 25)]["sma_200"]) < safe_float(last_row["sma_200"])
            and safe_float(last_row["away_from_high"]) < 25
            and safe_float(last_row["away_from_low"]) > 50
        ):
            eligible_stocks.append({
                "instrument_token": int(safe_float(last_row["instrument_token"])),
                "symbol": str(last_row["symbol"]),
                "last_price": current_close,
                "change": price_change,
                "sma_50": safe_float(last_row["sma_50"]),
                "sma_150": safe_float(last_row["sma_150"]),
                "sma_200": safe_float(last_row["sma_200"]),
                "atr": safe_float(last_row["atr"]),
            })

    eligible_stocks.sort(key=lambda x: x["change"], reverse=True)
    logger.debug(f"Found {len(eligible_stocks)} stocks matching VCP criteria.")
    return eligible_stocks

def screen_eligible_stocks_ipo(df):
    """
    Returns a list of dicts representing IPO-eligible stocks from 'df'.
    """
    logger.debug("Screening stocks for IPO criteria...")
    data_to_screen = df[df["segment"] == "IPO"]
    eligible_stocks = []

    for symbol, group in data_to_screen.groupby("symbol"):
        group = group.sort_values("date").reset_index(drop=True)
        if len(group) < 2:
            continue

        last_index = len(group) - 1
        last_row = group.iloc[last_index]
        prev_row = group.iloc[last_index - 1]

        current_close = safe_float(last_row["close"])
        prev_close = safe_float(prev_row["close"])
        price_change = 0.0
        if prev_close != 0:
            price_change = ((current_close - prev_close) / prev_close) * 100.0

        # Simple IPO screening logic
        if (
            safe_float(last_row["away_from_high"]) < 25
            and safe_float(last_row["away_from_low"]) > 25
        ):
            eligible_stocks.append({
                "instrument_token": int(safe_float(last_row["instrument_token"])),
                "symbol": str(last_row["symbol"]),
                "last_price": current_close,
                "change": price_change,
                "sma_50": safe_float(last_row["sma_50"]),
                "sma_150": safe_float(last_row["sma_150"]),
                "sma_200": safe_float(last_row["sma_200"]),
                "atr": safe_float(last_row["atr"]),
            })

    eligible_stocks.sort(key=lambda x: x["change"], reverse=True)
    logger.debug(f"Found {len(eligible_stocks)} stocks matching IPO criteria.")
    return eligible_stocks

def run_vcp_screener():
    """
    1) Load precomputed data (or use cached global).
    2) If market is open, fetch live quotes and update last row.
    3) Screen VCP.
    4) Clear old "vcp" results from screener_results table.
    5) Insert new results for "vcp".
    """
    logger.info("----- Starting VCP Screener -----")
    global ohlc_data

    # Load or reuse cached data
    if ohlc_data is None or ohlc_data.empty:
        logger.debug("No OHLC data cached; loading from DB.")
        ohlc_data = load_precomputed_ohlc()

    df = ohlc_data.copy()

    # Check market hours
    now = datetime.datetime.now(TIMEZONE).time()
    logger.debug(f"Current time: {now}. Checking if within market hours (9:15-15:30).")
    if datetime.time(9,15) <= now <= datetime.time(15,30):
        live_data = fetch_live_quotes()
        df = update_live_data(df, live_data)
    else:
        logger.debug("Market closed. Skipping live data update.")

    # Screen for VCP
    vcp_results = screen_eligible_stocks_vcp(df)

    # Save results
    logger.debug("Connecting to DB to save VCP screener results.")
    conn, cur = get_trade_db_connection()
    try:
        # CLEAR old VCP results
        logger.debug("Deleting old 'vcp' screener results.")
        ScreenerResult.delete_all_by_screener(cur, "vcp")

        # INSERT new VCP results
        logger.debug(f"Inserting {len(vcp_results)} new VCP results.")
        for stock in vcp_results:
            rec = ScreenerResult(
                screener_name="vcp",
                instrument_token=stock["instrument_token"],
                symbol=stock["symbol"],
                last_price=stock["last_price"],
                change_pct=stock["change"],
                sma_50=stock["sma_50"],
                sma_150=stock["sma_150"],
                sma_200=stock["sma_200"],
                atr=stock["atr"]
            )
            rec.save(cur)

        conn.commit()
        logger.info(f"[VCP Screener] Successfully saved {len(vcp_results)} results.")
    except Exception as e:
        logger.error(f"Error in run_vcp_screener: {e}")
        conn.rollback()
    finally:
        release_trade_db_connection(conn, cur)
    logger.info("----- Finished VCP Screener -----")

def run_ipo_screener():
    """
    1) Load precomputed data (or use cached global).
    2) If market is open, fetch live quotes and update last row.
    3) Screen IPO.
    4) Clear old "ipo" results from screener_results table.
    5) Insert new results for "ipo".
    """
    logger.info("----- Starting IPO Screener -----")
    global ohlc_data

    # Load or reuse cached data
    if ohlc_data is None or ohlc_data.empty:
        logger.debug("No OHLC data cached; loading from DB.")
        ohlc_data = load_precomputed_ohlc()

    df = ohlc_data.copy()

    # Check market hours
    now = datetime.datetime.now(TIMEZONE).time()
    logger.debug(f"Current time: {now}. Checking if within market hours (9:15-15:30).")
    if datetime.time(9,15) <= now <= datetime.time(15,30):
        live_data = fetch_live_quotes()
        df = update_live_data(df, live_data)
    else:
        logger.debug("Market closed. Skipping live data update.")

    # Screen for IPO
    ipo_results = screen_eligible_stocks_ipo(df)

    # Save results
    logger.debug("Connecting to DB to save IPO screener results.")
    conn, cur = get_trade_db_connection()
    try:
        # CLEAR old IPO results
        logger.debug("Deleting old 'ipo' screener results.")
        ScreenerResult.delete_all_by_screener(cur, "ipo")

        # INSERT new IPO results
        logger.debug(f"Inserting {len(ipo_results)} new IPO results.")
        for stock in ipo_results:
            rec = ScreenerResult(
                screener_name="ipo",
                instrument_token=stock["instrument_token"],
                symbol=stock["symbol"],
                last_price=stock["last_price"],
                change_pct=stock["change"],
                sma_50=stock["sma_50"],
                sma_150=stock["sma_150"],
                sma_200=stock["sma_200"],
                atr=stock["atr"]
            )
            rec.save(cur)

        conn.commit()
        logger.info(f"[IPO Screener] Successfully saved {len(ipo_results)} results.")
    except Exception as e:
        logger.error(f"Error in run_ipo_screener: {e}")
        conn.rollback()
    finally:
        release_trade_db_connection(conn, cur)
    logger.info("----- Finished IPO Screener -----")
