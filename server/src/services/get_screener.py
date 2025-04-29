import datetime
import pandas as pd
import pandas_ta as ta
import pytz
import logging
import math
import threading
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
weekly_ohlc_data = None

# Locks for thread safety
ohlc_lock = threading.Lock()
weekly_ohlc_lock = threading.Lock()

# Status flags for each screener
vcp_screener_running = False
ipo_screener_running = False
weekly_vcp_screener_running = False

# Locks for each screener
vcp_screener_lock = threading.Lock()
ipo_screener_lock = threading.Lock()
weekly_vcp_screener_lock = threading.Lock()

logger.info("==== Screener module initialized ====")

def load_precomputed_ohlc():
    """
    Loads precomputed OHLC data (with indicators) from the database
    using SaveOHLC.fetch_ohlc_exclude_ipo().
    This version uses a dedicated method for excluding only IPO segment.
    Caches the DataFrame globally in `ohlc_data`.
    """
    logger.info("Loading precomputed daily OHLC data (excluding only IPO segment)")
    global ohlc_data

    conn, cur = get_trade_db_connection()
    try:
        df = SaveOHLC.fetch_ohlc_exclude_ipo(cur)
        logger.info(f"Fetched {len(df)} rows of filtered data")
        
        if df.empty:
            logger.warning("EMPTY DataFrame returned from fetch! No data to screen")
        else:
            symbols = df['symbol'].unique()
            segments = df['segment'].unique()
            logger.info(f"Data includes {len(symbols)} unique symbols with segments: {segments}")
        
        ohlc_data = df
        return ohlc_data
    except Exception as e:
        logger.error(f"ERROR in load_precomputed_ohlc: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        release_trade_db_connection(conn, cur)

def load_precomputed_weekly_ohlc():
    """
    Loads precomputed weekly OHLC data (with indicators) from the database.
    
    Notes on weekly candle handling:
    - The last candle for each instrument may be an incomplete week
    - When the market is open, this partial week data will be extended
      by the update_weekly_live_data function to include current prices
    - Indicators stored in the DB will be recalculated after updates
    
    Returns:
        DataFrame: Weekly OHLC data including all segments except IPO
                  Includes technical indicators (SMAs, ATR, etc.)
    """
    logger.info("Loading precomputed weekly OHLC data (excluding only IPO)")
    global weekly_ohlc_data

    conn, cur = get_trade_db_connection()
    try:
        df = SaveOHLC.fetch_ohlc_exclude_ipo(cur)
        logger.info(f"Fetched {len(df)} rows of filtered weekly data")
        
        if df.empty:
            logger.warning("EMPTY DataFrame returned from fetch! No data to screen")
        else:
            symbols = df['symbol'].unique()
            segments = df['segment'].unique()
            logger.info(f"Weekly data includes {len(symbols)} unique symbols with segments: {segments}")
        
        weekly_ohlc_data = df
        return weekly_ohlc_data
    except Exception as e:
        logger.error(f"ERROR in load_precomputed_weekly_ohlc: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        release_trade_db_connection(conn, cur)

def fetch_live_quotes(batch_size=100):
    """
    Fetch live quote data from the 'equity_tokens' table in batches.
    Returns {instrument_token: last_price} mapping.
    
    Uses backoff strategy when rate limits are hit.
    """
    import time
    from kiteconnect.exceptions import NetworkException
    
    logger.info("Fetching live quotes from kite")
    live_quotes_all = {}
    
    conn, cur = get_trade_db_connection()
    try:
        query = "SELECT instrument_token FROM equity_tokens;"
        cur.execute(query)
        tokens = cur.fetchall()
        instrument_tokens = [int(t[0]) for t in tokens]
        logger.info(f"Found {len(instrument_tokens)} tokens to fetch quotes for")
        
        if not instrument_tokens:
            logger.warning("No instrument tokens found in equity_tokens table")
            return {}

        logger.info(f"Fetching quotes in batches of {batch_size}")
        for i in range(0, len(instrument_tokens), batch_size):
            batch = instrument_tokens[i:i+batch_size]
            batch_start = i 
            batch_end = min(i+batch_size, len(instrument_tokens))
            
            # Exponential backoff parameters
            max_retries = 3
            retry_count = 0
            base_delay = 0.2  # Start with 200ms delay
            
            while retry_count <= max_retries:
                try:
                    # Add delay between batches (and increase on retries)
                    if i > 0 or retry_count > 0:
                        current_delay = base_delay * (2 ** retry_count)
                        logger.debug(f"Sleeping for {current_delay:.2f}s before fetching batch {i//batch_size + 1}")
                        time.sleep(current_delay)
                        
                    quotes = kite.quote(batch)
                    
                    for tkn, quote_data in quotes.items():
                        last_price = quote_data.get("last_price", 0.0)
                        live_quotes_all[int(tkn)] = float(last_price)
                    
                    # Success, break out of retry loop
                    break
                    
                except NetworkException as e:
                    if "Too many requests" in str(e) and retry_count < max_retries:
                        retry_count += 1
                        logger.warning(f"Rate limit hit, retrying batch {i//batch_size + 1} after backoff ({retry_count}/{max_retries})")
                    else:
                        logger.error(f"ERROR in batch quotes: {e} (after {retry_count} retries)", exc_info=True)
                        break
                except Exception as e:
                    logger.error(f"ERROR in batch quotes: {e}", exc_info=True)
                    break

        logger.info(f"Completed fetching live quotes for {len(live_quotes_all)} tokens")
        return live_quotes_all
    except Exception as err:
        logger.error(f"ERROR in fetch_live_quotes: {err}", exc_info=True)
        return {}
    finally:
        release_trade_db_connection(conn, cur)

def update_live_data(df, live_data):
    """
    For each instrument token with a live quote, add a new row
    updating 'close' with the current price, then recalc
    ATR, 52-week highs, etc. for that row.
    """
    logger.info("Updating data with live prices")
    
    if df.empty:
        logger.warning("update_live_data called with empty DataFrame; returning as is")
        return df
        
    if not live_data:
        logger.debug("No live data to update; returning original DataFrame")
        return df

    logger.info(f"Updating data for {len(df['instrument_token'].unique())} instruments with {len(live_data)} live prices")
    
    # Find overlap between data and live quotes
    df_tokens = set(df['instrument_token'].unique())
    live_tokens = set(live_data.keys())
    overlap = df_tokens.intersection(live_tokens)
    logger.info(f"Overlap between DataFrame tokens and live data: {len(overlap)} instruments")
    
    updated_groups = []
    update_counts = {'updated': 0, 'skipped': 0}

    for token, group in df.groupby("instrument_token"):
        group = group.sort_values("date").reset_index(drop=True)
        
        if token not in live_data:
            updated_groups.append(group)
            update_counts['skipped'] += 1
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
        new_atr_val = float(new_atr_series.iloc[-1] if not new_atr_series.empty else 0.0)

        # Recompute 52-week highs/lows over last 252 rows
        subset_252 = group_updated.tail(252)
        new_52_high = float(subset_252["high"].max())
        new_52_low = float(subset_252["low"].min())
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
        update_counts['updated'] += 1

    df_updated = pd.concat(updated_groups, ignore_index=True)
    logger.info(f"Finished updating live data. Updated {update_counts['updated']} symbols, skipped {update_counts['skipped']} symbols")
    
    return df_updated

def screen_eligible_stocks_vcp(df):
    """
    Returns a list of dicts representing VCP-eligible stocks from 'df'.
    This function processes data already filtered at the database level 
    (only IPO segment excluded, ALL segment included).
    """
    logger.info("Starting VCP screening process")
    
    if df.empty:
        logger.warning("Empty DataFrame provided to screen_eligible_stocks_vcp! Cannot screen empty data")
        return []
        
    data_to_screen = df  # No additional segment filtering needed
    logger.info(f"Screening {len(data_to_screen['symbol'].unique())} unique symbols for VCP pattern")
    
    eligible_stocks = []
    rejected_counts = {
        "not_enough_data": 0,
        "price_below_sma50": 0,
        "sma_not_aligned": 0,
        "not_trending": 0,
        "too_extended": 0,
        "too_far_from_low": 0
    }

    symbol_counter = 0
    for symbol, group in data_to_screen.groupby("symbol"):
        symbol_counter += 1
        if symbol_counter % 100 == 0:
            logger.info(f"Processed {symbol_counter}/{len(data_to_screen['symbol'].unique())} symbols")
            
        group = group.sort_values("date").reset_index(drop=True)
        if len(group) < 2:
            rejected_counts["not_enough_data"] += 1
            continue

        last_index = len(group) - 1
        last_row = group.iloc[last_index]
        prev_row = group.iloc[last_index - 1]

        # Try-except to catch any issues with individual stocks
        try:
            current_close = float(last_row["close"])
            prev_close = float(prev_row["close"])
            price_change = 0.0
            if prev_close != 0:
                price_change = ((current_close - prev_close) / prev_close) * 100.0

            # VCP screening criteria - Check each condition
            passed = True
            
            # Price > 50 SMA
            if current_close <= last_row["sma_50"]:
                rejected_counts["price_below_sma50"] += 1
                passed = False
                
            # 50 SMA > 150 SMA > 200 SMA (for uptrend)
            elif not (last_row["sma_50"] > last_row["sma_150"] and last_row["sma_150"] > last_row["sma_200"]):
                rejected_counts["sma_not_aligned"] += 1
                passed = False
                
            # 200 SMA is rising (comparison with 25 periods ago)
            elif not (float(group.iloc[max(0, last_index - 25)]["sma_200"]) < float(last_row["sma_200"])):
                rejected_counts["not_trending"] += 1
                passed = False
                
            # Stock is within 30% of 52-week high (relaxed from 25%)
            elif not (float(last_row["away_from_high"]) < 30):
                rejected_counts["too_extended"] += 1
                passed = False
                
            # Stock is more than 40% above 52-week low (relaxed from 50%)
            elif not (float(last_row["away_from_low"]) > 40):
                rejected_counts["too_far_from_low"] += 1
                passed = False
                
            if passed:
                logger.info(f"{symbol} PASSED VCP criteria! Adding to eligible stocks")
                eligible_stocks.append({
                    "instrument_token": int(float(last_row["instrument_token"])),
                    "symbol": str(last_row["symbol"]),
                    "last_price": current_close,
                    "change": price_change,
                    "sma_50": float(last_row["sma_50"]),
                    "sma_150": float(last_row["sma_150"]),
                    "sma_200": float(last_row["sma_200"]),
                    "atr": float(last_row["atr"]),
                })
        except Exception as e:
            logger.error(f"ERROR processing symbol {symbol} in VCP screener: {e}", exc_info=True)

    eligible_stocks.sort(key=lambda x: x["change"], reverse=True)
    
    # Log detailed stats about screening results
    logger.info(f"VCP screening results: {len(eligible_stocks)} passed, {sum(rejected_counts.values())} rejected")
    for reason, count in rejected_counts.items():
        if count > 0:
            logger.info(f"VCP rejection reason '{reason}': {count} symbols")
    
    # Log the top 5 eligible stocks
    if eligible_stocks:
        top_stocks = [f"{s['symbol']}({s['change']:.2f}%)" for s in eligible_stocks[:5]]
        logger.info(f"Top VCP stocks: {', '.join(top_stocks)}")
    
    return eligible_stocks

def screen_eligible_stocks_ipo(df):
    """
    Returns a list of dicts representing IPO-eligible stocks from 'df'.
    """
    logger.info("Starting IPO screening process")
    
    if df.empty:
        logger.warning("Empty DataFrame provided to screen_eligible_stocks_ipo! Cannot screen empty data")
        return []
        
    logger.info("Filtering for IPO segment only")
    data_to_screen = df[df["segment"] == "IPO"]
    logger.info(f"Found {len(data_to_screen)} rows (IPO segment only) to screen for IPO pattern")
    
    eligible_stocks = []
    rejected_counts = {
        "not_enough_data": 0,
        "too_far_from_high": 0,
        "too_close_to_low": 0
    }

    for symbol, group in data_to_screen.groupby("symbol"):
        group = group.sort_values("date").reset_index(drop=True)
        if len(group) < 2:
            rejected_counts["not_enough_data"] += 1
            continue

        last_index = len(group) - 1
        last_row = group.iloc[last_index]
        prev_row = group.iloc[last_index - 1]

        try:
            current_close = float(last_row["close"])
            prev_close = float(prev_row["close"])
            price_change = 0.0
            if prev_close != 0:
                price_change = ((current_close - prev_close) / prev_close) * 100.0

            # Simple IPO screening logic - slightly relaxed
            away_from_high = float(last_row["away_from_high"])
            away_from_low = float(last_row["away_from_low"])
            
            # Check conditions separately for better logging
            passed = True
            
            if away_from_high >= 30:  # Relaxed from 25
                rejected_counts["too_far_from_high"] += 1
                passed = False
                
            elif away_from_low <= 20:  # Relaxed from 25
                rejected_counts["too_close_to_low"] += 1
                passed = False
                
            if passed:
                logger.info(f"{symbol} PASSED IPO criteria! Adding to eligible stocks")
                eligible_stocks.append({
                    "instrument_token": int(float(last_row["instrument_token"])),
                    "symbol": str(last_row["symbol"]),
                    "last_price": current_close,
                    "change": price_change,
                    "sma_50": float(last_row["sma_50"]),
                    "sma_150": float(last_row["sma_150"]),
                    "sma_200": float(last_row["sma_200"]),
                    "atr": float(last_row["atr"]),
                })
        except Exception as e:
            logger.error(f"ERROR processing IPO symbol {symbol}: {e}", exc_info=True)

    eligible_stocks.sort(key=lambda x: x["change"], reverse=True)
    
    # Log reasons for rejection
    logger.info(f"IPO screening results: {len(eligible_stocks)} passed, {sum(rejected_counts.values())} rejected")
    for reason, count in rejected_counts.items():
        if count > 0:
            logger.info(f"IPO rejection reason '{reason}': {count} symbols")
    
    # Log the eligible stocks
    if eligible_stocks:
        ipo_stocks = [f"{s['symbol']}({s['change']:.2f}%)" for s in eligible_stocks]
        logger.info(f"Eligible IPO stocks: {', '.join(ipo_stocks)}")
    
    return eligible_stocks

def screen_eligible_stocks_weekly(df):
    """
    Returns a list of dicts representing weekly VCP-eligible stocks from 'df'.
    Like the daily VCP screener but with weekly candles and slightly
    different criteria to account for weekly timeframe.
    """
    logger.info("Starting weekly VCP screening process")
    
    if df.empty:
        logger.warning("Empty DataFrame provided to screen_eligible_stocks_weekly! Cannot screen empty data")
        return []
    
    logger.info(f"Screening {len(df['symbol'].unique())} unique symbols for weekly VCP pattern")
    
    eligible_stocks = []
    rejected_counts = {
        "not_enough_data": 0,
        "price_below_sma50": 0,
        "sma_not_aligned": 0,
        "not_trending": 0,
        "too_extended": 0,
        "too_far_from_low": 0,
        "low_volume": 0
    }
    
    for symbol, group in df.groupby("symbol"):
        group = group.sort_values("date").reset_index(drop=True)
        
        # Need a minimum number of weeks of data
        if len(group) < 2:
            rejected_counts["not_enough_data"] += 1
            continue
            
        last_index = len(group) - 1
        last_row = group.iloc[last_index]
        prev_row = group.iloc[last_index - 1]
        
        try:
            current_close = float(last_row["close"])
            prev_close = float(prev_row["close"])
            price_change = 0.0
            if prev_close != 0:
                price_change = ((current_close - prev_close) / prev_close) * 100.0
                
            # Weekly VCP criteria - slightly different than daily
            passed = True
            
            # Price > 50-week SMA
            if current_close <= last_row["sma_50"]:
                rejected_counts["price_below_sma50"] += 1
                passed = False
                
            # 50-week SMA > 150-week SMA > 200-week SMA (uptrend)
            elif not (last_row["sma_50"] > last_row["sma_150"] and last_row["sma_150"] > last_row["sma_200"]):
                rejected_counts["sma_not_aligned"] += 1
                passed = False
                
            # 200-week SMA is rising
            elif not (float(group.iloc[max(0, last_index - 12)]["sma_200"]) < float(last_row["sma_200"])):
                rejected_counts["not_trending"] += 1
                passed = False
                
            # Stock is within 30% of 52-week high
            elif not (float(last_row["away_from_high"]) < 30):
                rejected_counts["too_extended"] += 1
                passed = False
                
            # Stock is more than 30% above 52-week low
            elif not (float(last_row["away_from_low"]) > 30):
                rejected_counts["too_far_from_low"] += 1
                passed = False
                
            if passed:
                logger.info(f"{symbol} PASSED weekly VCP criteria! Adding to eligible stocks")
                eligible_stocks.append({
                    "instrument_token": int(float(last_row["instrument_token"])),
                    "symbol": str(last_row["symbol"]),
                    "last_price": current_close,
                    "change": price_change,
                    "sma_50": float(last_row["sma_50"]),
                    "sma_150": float(last_row["sma_150"]),
                    "sma_200": float(last_row["sma_200"]),
                    "atr": float(last_row["atr"]),
                })
        except Exception as e:
            logger.error(f"ERROR processing symbol {symbol} in weekly screener: {e}", exc_info=True)
    
    eligible_stocks.sort(key=lambda x: x["change"], reverse=True)
    
    # Log summary statistics
    logger.info(f"Weekly VCP screening results: {len(eligible_stocks)} passed, {sum(rejected_counts.values())} rejected")
    for reason, count in rejected_counts.items():
        if count > 0:
            logger.info(f"Weekly VCP rejection reason '{reason}': {count} symbols")
    
    # Log the top eligible stocks
    if eligible_stocks:
        top_stocks = [f"{s['symbol']}({s['change']:.2f}%)" for s in eligible_stocks[:5]]
        logger.info(f"Top weekly VCP stocks: {', '.join(top_stocks)}")
    
    return eligible_stocks

def is_new_week(last_date, current_date):
    """
    Determine if current_date is in a new week compared to last_date.
    Uses the ISO calendar where week starts on Monday (day 1).
    
    Returns:
        bool: True if dates are in different calendar weeks, False otherwise
    """
    # Handle cases where we have string dates
    if isinstance(last_date, str):
        last_date = pd.to_datetime(last_date)
    if isinstance(current_date, str):
        current_date = pd.to_datetime(current_date)
        
    # Get the ISO year and week for both dates
    last_year, last_week, _ = last_date.isocalendar()
    current_year, current_week, _ = current_date.isocalendar()
    
    # Different week if either year or week number differs
    return (last_year != current_year) or (last_week != current_week)

def update_weekly_live_data(df, live_data):
    """
    Update weekly OHLC data with live quotes:
    1. For each symbol with a live quote:
       - If the most recent candle is from the current week,
         update its OHLC values with the live price
       - If the most recent candle is from a previous week,
         create a new weekly candle with the live price
    2. Recalculate technical indicators on the updated data
    
    Returns the updated DataFrame
    """
    logger.info("Updating weekly data with live prices")
    
    if df.empty:
        logger.warning("update_weekly_live_data called with empty DataFrame; returning as is")
        return df
        
    if not live_data:
        logger.debug("No live data to update; returning original weekly DataFrame")
        return df
        
    logger.info(f"Updating weekly data for {len(df['instrument_token'].unique())} instruments with {len(live_data)} live prices")
    
    # Find overlap between data and live quotes
    df_tokens = set(df['instrument_token'].unique())
    live_tokens = set(live_data.keys())
    overlap = df_tokens.intersection(live_tokens)
    logger.info(f"Overlap between weekly DataFrame tokens and live data: {len(overlap)} instruments")
    
    # Track update statistics
    update_counts = {'created_new': 0, 'updated_existing': 0, 'skipped': 0}
    updated_groups = []
    
    # Get current date/time in correct timezone
    current_dt = datetime.datetime.now(TIMEZONE)
    
    for token, group in df.groupby("instrument_token"):
        # Sort group by date (ascending)
        group = group.sort_values("date").reset_index(drop=True)
        
        # Skip if no live data for this token
        if token not in live_data:
            updated_groups.append(group)
            update_counts['skipped'] += 1
            continue
            
        live_price = live_data[token]
        last_row = group.iloc[-1]
        last_date = pd.to_datetime(last_row["date"])
        
        # Determine if we need a new candle or to update existing candle
        if is_new_week(last_date, current_dt):
            # Create a new weekly candle
            new_row = {
                "instrument_token": token,
                "symbol": last_row["symbol"],
                "interval": last_row["interval"],
                "date": current_dt,
                "open": live_price,
                "high": live_price,
                "low": live_price,
                "close": live_price,
                "volume": 0,
                "segment": last_row["segment"],
                # Copy previous indicators for now (will update)
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
            update_counts['created_new'] += 1
            
        else:
            # Update existing candle for current week
            last_idx = len(group) - 1
            
            # Update OHLC
            group.at[last_idx, "high"] = max(float(group.at[last_idx, "high"]), live_price)
            group.at[last_idx, "low"] = min(float(group.at[last_idx, "low"]), live_price)
            group.at[last_idx, "close"] = live_price
            
            group_updated = group
            update_counts['updated_existing'] += 1
            
        # --- Recalculate Technical Indicators ---
        
        # Recalculate atr with last 14 bars
        bar_window = min(14, len(group_updated))
        tail = group_updated.tail(bar_window).copy()
        atr_series = ta.atr(
            high=tail["high"],
            low=tail["low"],
            close=tail["close"],
            length=bar_window
        )
        new_atr = float(atr_series.iloc[-1]) if not atr_series.empty else float(group_updated.iloc[-1]["atr"])
        
        # Recalculate 52-week high/low
        lookback = min(52, len(group_updated))
        year_data = group_updated.tail(lookback)
        new_52_high = float(year_data["high"].max())
        new_52_low = float(year_data["low"].min())
        
        # Calculate away_from_high and away_from_low
        latest_close = float(group_updated.iloc[-1]["close"])
        away_high = ((new_52_high - latest_close) / new_52_high) * 100 if new_52_high > 0 else 0
        away_low = ((latest_close - new_52_low) / new_52_low) * 100 if new_52_low > 0 else 0
        
        # Update the indicators in the last row
        last_idx = len(group_updated) - 1
        group_updated.at[last_idx, "atr"] = new_atr
        group_updated.at[last_idx, "52_week_high"] = new_52_high
        group_updated.at[last_idx, "52_week_low"] = new_52_low 
        group_updated.at[last_idx, "away_from_high"] = away_high
        group_updated.at[last_idx, "away_from_low"] = away_low
        
        # --- End of Full Recalculation ---

        updated_groups.append(group_updated)

    # Combine all updated groups
    df_updated = pd.concat(updated_groups, ignore_index=True)
    logger.info(f"Weekly data update summary: {update_counts['created_new']} new bars, {update_counts['updated_existing']} updated bars")
    
    return df_updated

def run_vcp_screener():
    """
    1) Load precomputed data (or use cached global).
    2) If market is open, fetch live quotes and update last row.
    3) Screen VCP.
    4) Clear old "vcp" results from screener_results table.
    5) Insert new results for "vcp".
    
    Now runs in its own thread to prevent blocking app operations.
    """
    global vcp_screener_running, ohlc_data
    
    # Check if another instance is already running
    with vcp_screener_lock:
        if vcp_screener_running:
            logger.info("VCP screener already running, skipping this invocation")
            return False
        vcp_screener_running = True
    
    try:
        logger.info("===== Starting VCP Screener =====")

        # Load or reuse cached data
        with ohlc_lock:
            if ohlc_data is None or ohlc_data.empty:
                logger.info("No OHLC data cached; loading from DB")
                ohlc_data = load_precomputed_ohlc()
                
            if ohlc_data is None or ohlc_data.empty:
                logger.error("Failed to load OHLC data for VCP screener. Aborting")
                return False

            logger.info(f"Working with DataFrame of shape {ohlc_data.shape} for VCP screening")
            df = ohlc_data.copy()

        # Check market hours
        now = datetime.datetime.now(TIMEZONE).time()
        logger.info(f"Current time: {now}. Checking if within market hours (9:15-15:30)")
        
        if datetime.time(9,15) <= now <= datetime.time(15,30):
            logger.info("Market is open. Will fetch live quotes")
            try:
                live_data = fetch_live_quotes()
                if live_data:
                    logger.info(f"Fetched live quotes for {len(live_data)} instruments")
                    df = update_live_data(df, live_data)
                    logger.info("Successfully updated data with live quotes")
                else:
                    logger.warning("No live quotes fetched. Using historical data only")
            except Exception as e:
                logger.error(f"Error fetching live quotes: {e}. Using historical data only")
        else:
            logger.info("Market closed. Skipping live data update")

        # Screen for VCP
        try:
            logger.info("Starting VCP pattern screening")
            vcp_results = screen_eligible_stocks_vcp(df)
            logger.info(f"VCP screening returned {len(vcp_results)} eligible stocks")
        except Exception as e:
            logger.error(f"Error during VCP screening: {e}", exc_info=True)
            return False

        # Save results
        logger.info("Connecting to DB to save VCP screener results")
        conn, cur = get_trade_db_connection()
        try:
            # CLEAR old VCP results
            logger.info("Deleting old 'vcp' screener results")
            ScreenerResult.delete_all_by_screener(cur, "vcp")

            # INSERT new VCP results
            logger.info(f"Inserting {len(vcp_results)} new VCP results")
            for i, stock in enumerate(vcp_results):
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

            logger.info("Committing VCP screener results to database")
            conn.commit()
            logger.info(f"Successfully saved {len(vcp_results)} VCP screener results")
            return True
        except Exception as e:
            logger.error(f"Error in run_vcp_screener: {e}", exc_info=True)
            conn.rollback()
            return False
        finally:
            release_trade_db_connection(conn, cur)
            logger.info("===== Finished VCP Screener =====")
    finally:
        # Reset running flag even if an exception occurs
        with vcp_screener_lock:
            vcp_screener_running = False

def run_ipo_screener():
    """
    1) Load precomputed data (or use cached global).
    2) If market is open, fetch live quotes and update last row.
    3) Screen IPO.
    4) Clear old "ipo" results from screener_results table.
    5) Insert new results for "ipo".
    
    Now runs in its own thread to prevent blocking app operations.
    """
    global ipo_screener_running, ohlc_data
    
    # Check if another instance is already running
    with ipo_screener_lock:
        if ipo_screener_running:
            logger.info("IPO screener already running, skipping this invocation")
            return False
        ipo_screener_running = True
    
    try:
        logger.info("===== Starting IPO Screener =====")
        
        # Load or reuse cached data
        with ohlc_lock:
            if ohlc_data is None or ohlc_data.empty:
                logger.info("No OHLC data cached; loading from DB")
                ohlc_data = load_precomputed_ohlc()
                
            if ohlc_data is None or ohlc_data.empty:
                logger.error("Failed to load OHLC data for IPO screener. Aborting")
                return False

            logger.info(f"Working with DataFrame of shape {ohlc_data.shape} for IPO screening")
            df = ohlc_data.copy()

        # Check market hours
        now = datetime.datetime.now(TIMEZONE).time()
        logger.info(f"Current time: {now}. Checking if within market hours (9:15-15:30)")
        
        if datetime.time(9,15) <= now <= datetime.time(15,30):
            logger.info("Market is open. Will fetch live quotes")
            try:
                live_data = fetch_live_quotes()
                if live_data:
                    logger.info(f"Fetched live quotes for {len(live_data)} instruments")
                    df = update_live_data(df, live_data)
                    logger.info("Successfully updated data with live quotes")
                else:
                    logger.warning("No live quotes fetched. Using historical data only")
            except Exception as e:
                logger.error(f"Error fetching live quotes: {e}. Using historical data only")
        else:
            logger.info("Market closed. Skipping live data update")

        # Screen for IPO
        try:
            logger.info("Starting IPO screening")
            ipo_results = screen_eligible_stocks_ipo(df)
            logger.info(f"IPO screening returned {len(ipo_results)} eligible stocks")
        except Exception as e:
            logger.error(f"Error during IPO screening: {e}", exc_info=True)
            return False

        # Save results
        logger.info("Connecting to DB to save IPO screener results")
        conn, cur = get_trade_db_connection()
        try:
            # CLEAR old IPO results
            logger.info("Deleting old 'ipo' screener results")
            ScreenerResult.delete_all_by_screener(cur, "ipo")

            # INSERT new IPO results
            logger.info(f"Inserting {len(ipo_results)} new IPO results")
            for i, stock in enumerate(ipo_results):
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

            logger.info("Committing IPO screener results to database")
            conn.commit()
            logger.info(f"Successfully saved {len(ipo_results)} IPO screener results")
            return True
        except Exception as e:
            logger.error(f"Error in run_ipo_screener: {e}", exc_info=True)
            conn.rollback()
            return False
        finally:
            release_trade_db_connection(conn, cur)
            logger.info("===== Finished IPO Screener =====")
    finally:
        # Reset running flag even if an exception occurs
        with ipo_screener_lock:
            ipo_screener_running = False

def run_weekly_vcp_screener():
    """
    Weekly VCP screener that handles partial week data.
    
    Process:
    1) Load precomputed weekly data (or use cached global).
    2) If market is open, fetch live quotes and update:
       - If in the same week as the last candle, update that candle's OHLC values
       - If in a new week, create a new candle with the live quote
    3) Recalculate indicators for accurate screening
    4) Screen for weekly VCP patterns
    5) Clear old "weekly_vcp" results from screener_results table
    6) Insert new results for "weekly_vcp"
    
    NOTE: Unlike the daily VCP screener, this includes ALL segments except IPOs.
    
    Now runs in its own thread to prevent blocking app operations.
    """
    global weekly_vcp_screener_running, weekly_ohlc_data
    
    # Check if another instance is already running
    with weekly_vcp_screener_lock:
        if weekly_vcp_screener_running:
            logger.info("Weekly VCP screener already running, skipping this invocation")
            return False
        weekly_vcp_screener_running = True
    
    try:
        logger.info("===== Starting Weekly Screener =====")
        
        # Load or reuse cached data
        with weekly_ohlc_lock:
            if weekly_ohlc_data is None or weekly_ohlc_data.empty:
                logger.info("Loading weekly OHLC data from database")
                weekly_ohlc_data = load_precomputed_weekly_ohlc()
                
            if weekly_ohlc_data is None or weekly_ohlc_data.empty:
                logger.error("Failed to load weekly OHLC data. Aborting screener run.")
                return False

            df = weekly_ohlc_data.copy()

        # Check market hours
        now = datetime.datetime.now(TIMEZONE).time()
        
        if datetime.time(9,15) <= now <= datetime.time(15,30):
            logger.info("Market is open - fetching live quotes for weekly data")
            try:
                live_data = fetch_live_quotes()
                if live_data:
                    df = update_weekly_live_data(df, live_data)
                    logger.info("Weekly data updated with live quotes")
                else:
                    logger.warning("No live quotes retrieved - using historical data only")
            except Exception as e:
                logger.error(f"Error fetching live quotes: {e}")
        else:
            logger.info("Market closed - using historical weekly data only")

        # Screen for weekly pattern
        try:
            weekly_results = screen_eligible_stocks_weekly(df)
            logger.info(f"Weekly screening found {len(weekly_results)} eligible stocks")
        except Exception as e:
            logger.error(f"Error during weekly screening: {e}", exc_info=True)
            return False

        # Save results
        conn, cur = get_trade_db_connection()
        try:
            # Clear old Weekly results
            logger.info("Deleting old 'weekly_vcp' screener results")
            ScreenerResult.delete_all_by_screener(cur, "weekly_vcp")
            
            # Insert new Weekly results
            logger.info(f"Inserting {len(weekly_results)} new weekly VCP results")
            for i, stock in enumerate(weekly_results):
                rec = ScreenerResult(
                    screener_name="weekly_vcp",
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
            logger.info(f"Successfully saved {len(weekly_results)} weekly VCP screener results")
            return True
        except Exception as e:
            logger.error(f"Error saving weekly VCP results: {e}", exc_info=True)
            conn.rollback()
            return False
        finally:
            release_trade_db_connection(conn, cur)
            logger.info("===== Finished Weekly Screener =====")
    finally:
        # Reset running flag even if an exception occurs
        with weekly_vcp_screener_lock:
            weekly_vcp_screener_running = False
