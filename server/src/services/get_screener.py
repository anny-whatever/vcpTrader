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
from models import ScreenerResult, AdvancedVcpResult
from models import SaveOHLC

# Import the advanced screener function
from .advanced_vcp_screener import run_advanced_vcp_scan as run_advanced_vcp_scan_logic

# Import the new display data functions - removed to avoid circular dependencies
# from .get_display_data import (
#     fetch_risk_pool_for_display,
#     fetch_trade_details_for_display,
#     fetch_historical_trade_details_for_display,
#     get_combined_ohlc,
#     get_all_alerts,
#     get_latest_alert_messages,
# )
from .get_token_data import download_nse_csv

logger = logging.getLogger(__name__)
TIMEZONE = pytz.timezone("Asia/Kolkata")

# We maintain a global cached copy of OHLC data, but no locking is used.
ohlc_data = None
# weekly_ohlc_data = None  # REMOVED weekly data cache

# Locks for thread safety
ohlc_lock = threading.Lock()
# weekly_ohlc_lock = threading.Lock()  # REMOVED weekly data lock

# Status flags for each screener
vcp_screener_running = False
# ipo_screener_running = False  # REMOVED IPO screener flag
# weekly_vcp_screener_running = False  # REMOVED weekly VCP screener flag

# Locks for each screener
vcp_screener_lock = threading.Lock()
# ipo_screener_lock = threading.Lock()  # REMOVED IPO screener lock
# weekly_vcp_screener_lock = threading.Lock()  # REMOVED weekly VCP screener lock

advanced_vcp_screener_running = False
advanced_vcp_screener_lock = threading.Lock()

def test_sequential_vcp_screener(max_symbols=5):
    """
    Test function for the sequential VCP screener.
    Processes a limited number of symbols to verify the approach works.
    """
    logger.info(f"=== TESTING Sequential VCP Screener (max {max_symbols} symbols) ===")
    
    try:
        from models import SaveOHLC
        from db import get_trade_db_connection, release_trade_db_connection
        
        # Get just a few symbols for testing
        conn, cur = get_trade_db_connection()
        try:
            symbols_list = SaveOHLC.fetch_symbols_for_screening(cur)
            test_symbols = symbols_list[:max_symbols]  # Limit for testing
            logger.info(f"Testing with {len(test_symbols)} symbols: {[s[0] for s in test_symbols]}")
        finally:
            release_trade_db_connection(conn, cur)
        
        if not test_symbols:
            logger.warning("No symbols found for testing")
            return False
        
        # Test processing one symbol
        symbol, instrument_token = test_symbols[0]
        logger.info(f"Testing single symbol processing: {symbol}")
        
        conn, cur = get_trade_db_connection()
        try:
            stock_df = SaveOHLC.fetch_ohlc_for_single_symbol(cur, symbol)
            logger.info(f"Successfully fetched {len(stock_df)} rows for {symbol}")
            
            if not stock_df.empty:
                logger.info(f"Data columns: {list(stock_df.columns)}")
                logger.info(f"Date range: {stock_df['date'].min()} to {stock_df['date'].max()}")
            
        finally:
            release_trade_db_connection(conn, cur)
        
        logger.info("✅ Sequential VCP screener test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Sequential VCP screener test failed: {e}", exc_info=True)
        return False

logger.info("==== Screener module initialized ====")
logger.info("==== Sequential VCP Screener available for memory-efficient processing =====")

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
            "sma_100": last_row["sma_100"],
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
        
        # Debug logging for ATR calculation
        logger.debug(f"ATR calculation for {last_row['symbol']} - subset shape: {subset.shape}")
        logger.debug(f"ATR calculation - last 3 rows high/low/close: {subset[['high', 'low', 'close']].tail(3).to_dict()}")
        
        new_atr_series = ta.atr(
            high=subset["high"],
            low=subset["low"],
            close=subset["close"],
            length=min(tail_window, len(subset))
        )
        new_atr_val = float(new_atr_series.iloc[-1] if not new_atr_series.empty else 0.0)
        
        # Debug logging for ATR result
        logger.debug(f"ATR calculation for {last_row['symbol']} - new_atr_val: {new_atr_val}, series empty: {new_atr_series.empty}")
        if new_atr_val == 0.0 and not new_atr_series.empty:
            logger.warning(f"ATR is 0.0 but series not empty for {last_row['symbol']} - series: {new_atr_series.tail(3).to_dict()}")

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
                
            # 50 SMA > 100 SMA > 200 SMA (for uptrend)
            elif not (last_row["sma_50"] > last_row["sma_100"] and last_row["sma_50"] > last_row["sma_200"]):
                rejected_counts["sma_not_aligned"] += 1
                passed = False
                
            # 200 SMA is rising (comparison with 25 periods ago)
            elif not (float(group.iloc[max(0, last_index - 25)]["sma_200"]) < float(last_row["sma_200"])):
                rejected_counts["not_trending"] += 1
                passed = False
                
            # Stock is within 30% of 52-week high (relaxed from 25%)
            elif not (float(last_row["away_from_high"]) < 50):
                rejected_counts["too_extended"] += 1
                passed = False
                
            # # Stock is more than 40% above 52-week low (relaxed from 50%)
            # elif not (float(last_row["away_from_low"]) > 40):
            #     rejected_counts["too_far_from_low"] += 1
            #     passed = False
                
            if passed:
                logger.info(f"{symbol} PASSED VCP criteria! Adding to eligible stocks")
                eligible_stocks.append({
                    "instrument_token": int(float(last_row["instrument_token"])),
                    "symbol": str(last_row["symbol"]),
                    "last_price": current_close,
                    "change": price_change,
                    "sma_50": float(last_row["sma_50"]),
                    "sma_100": float(last_row["sma_100"]),
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
                    sma_100=stock["sma_100"],
                    sma_200=stock["sma_200"],
                    atr=stock["atr"]
                )
                rec.save(cur)

            logger.info("Committing VCP screener results to database")
            conn.commit()
            
            # Send NOTIFY to trigger socket subscription update
            cur.execute("NOTIFY data_changed, 'screener_results'")
            logger.info("Sent notification to update ticker subscriptions with VCP screener tokens")
            
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

def fetch_screener_data(screener_name):
    """
    Fetches the latest results for a given screener from the database.
    Now directs 'vcp' requests to the new advanced results table.
    """
    conn, cur = get_trade_db_connection()
    try:
        logger.info(f"Fetching screener data for '{screener_name}'")
        if screener_name == "vcp":
            # This now correctly fetches from the advanced results table
            data = AdvancedVcpResult.fetch_all(cur)
            logger.info(f"Fetched {len(data)} results from 'advanced_vcp_results' table.")
            return data
        else:
            # Preserving old logic for any other screeners
            data = ScreenerResult.fetch_by_screener(cur, screener_name)
            if not data:
                return []
            # Convert list of tuples to list of dicts for consistency
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in data]

    except Exception as e:
        logger.error(f"Error fetching data for screener '{screener_name}': {e}", exc_info=True)
        return []
    finally:
        if conn:
            release_trade_db_connection(conn, cur)

def run_advanced_vcp_screener():
    """
    Orchestrates the advanced VCP screening process using memory-efficient sequential processing.
    This prevents deadlocks and memory issues by processing one stock at a time.
    """
    global advanced_vcp_screener_running
    if advanced_vcp_screener_running:
        logger.info("Advanced VCP screener is already running.")
        return False

    with advanced_vcp_screener_lock:
        advanced_vcp_screener_running = True
        logger.info("Starting Sequential Advanced VCP Screener...")
        
        try:
            # Use the new sequential scanning approach
            # This eliminates the need to load all OHLC data into memory at once
            from .advanced_vcp_screener import run_advanced_vcp_scan_sequential
            success = run_advanced_vcp_scan_sequential()
            
            if success:
                logger.info("Sequential Advanced VCP Screener completed successfully.")
            else:
                logger.warning("Sequential Advanced VCP Screener completed with issues.")
            
            return success

        except Exception as e:
            logger.error(f"FATAL ERROR in run_advanced_vcp_screener: {e}", exc_info=True)
            return False
        finally:
            advanced_vcp_screener_running = False
            logger.info("Sequential Advanced VCP Screener finished.")

def run_advanced_vcp_screener_legacy():
    """
    DEPRECATED: Legacy bulk VCP screener - kept for backward compatibility.
    Use run_advanced_vcp_screener() for the optimized sequential version.
    """
    global advanced_vcp_screener_running
    if advanced_vcp_screener_running:
        logger.info("Legacy advanced VCP screener is already running.")
        return False

    with advanced_vcp_screener_lock:
        advanced_vcp_screener_running = True
        logger.warning("Using LEGACY Advanced VCP Screener - consider updating to sequential version")
        
        try:
            # 1. Load the precomputed OHLC data (this loads ALL data into memory)
            df = load_precomputed_ohlc()
            if df is None or df.empty:
                logger.error("OHLC data is empty. Aborting legacy VCP scan.")
                return False

            # 2. Run the legacy screener logic
            success = run_advanced_vcp_scan_logic(df)
            
            if success:
                logger.info("Legacy Advanced VCP Screener run completed successfully.")
            else:
                logger.warning("Legacy Advanced VCP Screener run did not complete successfully.")
            
            return success

        except Exception as e:
            logger.error(f"FATAL ERROR in run_advanced_vcp_screener_legacy: {e}", exc_info=True)
            return False
        finally:
            advanced_vcp_screener_running = False
            logger.info("Legacy Advanced VCP Screener finished.")
