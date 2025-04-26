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
weekly_ohlc_data = None

logger.info("==== Screener module initialized ====")

def load_precomputed_ohlc():
    """
    Loads precomputed OHLC data (with indicators) from the database
    using SaveOHLC.fetch_ohlc_exclude_ipo_and_all().
    This version uses a dedicated method for excluding both ALL and IPO segments.
    Caches the DataFrame globally in `ohlc_data`.
    """
    logger.info("STEP 1: Loading precomputed daily OHLC data via SaveOHLC class (excluding ALL and IPO segments)...")
    global ohlc_data

    logger.info("STEP 1.1: Getting database connection for OHLC data")
    conn, cur = get_trade_db_connection()
    try:
        logger.info("STEP 1.2: Executing fetch_ohlc_exclude_ipo_and_all to get daily data")
        # Use the new dedicated method for this specific exclusion case
        df = SaveOHLC.fetch_ohlc_exclude_ipo_and_all(cur)
        logger.info(f"STEP 1.3: Fetched {len(df)} rows of filtered data (no ALL or IPO)")
        
        if df.empty:
            logger.warning("STEP 1.4: EMPTY DataFrame returned from fetch! No data to screen")
        else:
            # Log some sample data for debugging
            symbols = df['symbol'].unique()
            logger.info(f"STEP 1.4: Data includes {len(symbols)} unique symbols: {', '.join(symbols[:5])}...")
            
            # Log data structure
            logger.info(f"STEP 1.5: DataFrame columns: {list(df.columns)}")
            logger.info(f"STEP 1.6: Date range: {df['date'].min()} to {df['date'].max()}")
            
            # Log segment information - should not include ALL or IPO
            segments = df['segment'].unique()
            logger.info(f"STEP 1.7: Segments in data: {segments}")
            
            # Check for NaN values in key columns
            nan_counts = {col: df[col].isna().sum() for col in ['close', 'sma_50', 'sma_150', 'sma_200']}
            logger.info(f"STEP 1.8: NaN counts in key columns: {nan_counts}")
        
        ohlc_data = df
        return ohlc_data
    except Exception as e:
        logger.error(f"ERROR in load_precomputed_ohlc: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        logger.info("STEP 1.9: Releasing database connection")
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
    logger.info("STEP 1W: Loading precomputed weekly OHLC data via SaveOHLC class (excluding only IPO)...")
    global weekly_ohlc_data

    logger.info("STEP 1W.1: Getting database connection for weekly OHLC data")
    conn, cur = get_trade_db_connection()
    try:
        logger.info("STEP 1W.2: Executing fetch_ohlc_exclude_ipo to get weekly data")
        # Use the dedicated method that excludes only IPO segment
        df = SaveOHLC.fetch_ohlc_exclude_ipo(cur)
        logger.info(f"STEP 1W.3: Fetched {len(df)} rows of filtered weekly data")
        
        if df.empty:
            logger.warning("STEP 1W.4: EMPTY DataFrame returned from fetch! No data to screen")
        else:
            # Log some sample data for debugging
            symbols = df['symbol'].unique()
            logger.info(f"STEP 1W.4: Weekly data includes {len(symbols)} unique symbols: {', '.join(symbols[:5])}...")
            
            # Log data structure
            logger.info(f"STEP 1W.5: DataFrame columns: {list(df.columns)}")
            logger.info(f"STEP 1W.6: Date range: {df['date'].min()} to {df['date'].max()}")
            
            # Check for partial week data by looking at the most recent dates
            current_date = datetime.datetime.now(TIMEZONE)
            # Extract just the date part for comparison
            current_date_str = current_date.strftime('%Y-%m-%d')
            last_dates = df.groupby('symbol')['date'].max()
            
            # Count stocks with data from the current week
            current_week_count = 0
            for symbol, last_date in last_dates.items():
                if isinstance(last_date, str):
                    last_date = pd.to_datetime(last_date)
                if not is_new_week(last_date, current_date):
                    current_week_count += 1
            
            logger.info(f"STEP 1W.7: Found {current_week_count} out of {len(symbols)} stocks with partial data from current week")
            
            # Log segment information - should include ALL but not IPO
            segments = df['segment'].unique()
            logger.info(f"STEP 1W.8: Segments in weekly data: {segments}")
            if "ALL" in segments:
                logger.info(f"STEP 1W.8.1: ALL segment is present in the weekly data")
            else:
                logger.warning(f"STEP 1W.8.2: ALL segment is NOT present in the weekly data!")
                
            # Check for NaN values in key columns
            nan_counts = {col: df[col].isna().sum() for col in ['close', 'sma_50', 'sma_150', 'sma_200']}
            logger.info(f"STEP 1W.9: NaN counts in key weekly columns: {nan_counts}")
        
        weekly_ohlc_data = df
        return weekly_ohlc_data
    except Exception as e:
        logger.error(f"ERROR in load_precomputed_weekly_ohlc: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        logger.info("STEP 1W.10: Releasing database connection")
        release_trade_db_connection(conn, cur)

def fetch_live_quotes(batch_size=250):
    """
    Fetch live quote data from the 'equity_tokens' table in batches.
    Returns {instrument_token: last_price} mapping.
    """
    logger.info("STEP 2: Starting to fetch live quotes from kite...")
    live_quotes_all = {}
    
    logger.info("STEP 2.1: Getting database connection to fetch instrument tokens")
    conn, cur = get_trade_db_connection()
    try:
        logger.info("STEP 2.2: Querying equity_tokens table for instruments")
        query = "SELECT instrument_token FROM equity_tokens;"
        cur.execute(query)
        tokens = cur.fetchall()
        instrument_tokens = [int(t[0]) for t in tokens]
        logger.info(f"STEP 2.3: Found {len(instrument_tokens)} tokens to fetch quotes for")
        
        if not instrument_tokens:
            logger.warning("STEP 2.4: No instrument tokens found in equity_tokens table")
            return {}

        # Log some token examples for debugging
        token_examples = instrument_tokens[:5]
        logger.info(f"STEP 2.5: Sample tokens: {token_examples}")

        logger.info(f"STEP 2.6: Fetching quotes in batches of {batch_size}")
        for i in range(0, len(instrument_tokens), batch_size):
            batch = instrument_tokens[i:i+batch_size]
            batch_start = i 
            batch_end = min(i+batch_size, len(instrument_tokens))
            logger.info(f"STEP 2.7: Processing batch {i//batch_size + 1}, tokens {batch_start}-{batch_end}")
            
            try:
                logger.info(f"STEP 2.8: Calling kite.quote for batch of {len(batch)} tokens")
                quotes = kite.quote(batch)
                logger.info(f"STEP 2.9: Received quotes for {len(quotes)} tokens")
                
                for tkn, quote_data in quotes.items():
                    last_price = quote_data.get("last_price", 0.0)
                    live_quotes_all[int(tkn)] = float(last_price)
                    
            except Exception as e:
                logger.error(f"ERROR in batch quotes: {e}", exc_info=True)
                logger.error(f"STEP 2.10: Failed to fetch quotes for batch starting at index {i}")

        logger.info(f"STEP 2.11: Completed fetching live quotes for {len(live_quotes_all)} tokens")
        
        # Log some sample prices for debugging
        if live_quotes_all:
            sample_tokens = list(live_quotes_all.keys())[:5]
            sample_prices = {t: live_quotes_all[t] for t in sample_tokens}
            logger.info(f"STEP 2.12: Sample prices: {sample_prices}")
        
        return live_quotes_all
    except Exception as err:
        logger.error(f"ERROR in fetch_live_quotes: {err}", exc_info=True)
        return {}
    finally:
        logger.info("STEP 2.13: Releasing database connection")
        release_trade_db_connection(conn, cur)

def update_live_data(df, live_data):
    """
    For each instrument token with a live quote, add a new row
    updating 'close' with the current price, then recalc
    ATR, 52-week highs, etc. for that row.
    """
    logger.info("STEP 3: Starting update_live_data to incorporate live prices")
    
    if df.empty:
        logger.warning("STEP 3.1: update_live_data called with empty DataFrame; returning as is")
        return df
        
    if not live_data:
        logger.debug("STEP 3.2: No live data to update; returning original DataFrame")
        return df

    logger.info(f"STEP 3.3: Starting to update live data for {len(df['instrument_token'].unique())} unique instruments")
    logger.info(f"STEP 3.4: We have live prices for {len(live_data)} instruments")
    
    # Find overlap between data and live quotes
    df_tokens = set(df['instrument_token'].unique())
    live_tokens = set(live_data.keys())
    overlap = df_tokens.intersection(live_tokens)
    logger.info(f"STEP 3.5: Overlap between DataFrame tokens and live data: {len(overlap)} instruments")
    
    updated_groups = []
    update_counts = {'updated': 0, 'skipped': 0}

    logger.info("STEP 3.6: Processing each instrument group")
    for token, group in df.groupby("instrument_token"):
        group = group.sort_values("date").reset_index(drop=True)
        
        if token not in live_data:
            updated_groups.append(group)
            update_counts['skipped'] += 1
            continue

        live_price = live_data[token]
        last_row = group.iloc[-1]
        
        logger.debug(f"STEP 3.7: Updating token {token} ({last_row['symbol']}) with live price {live_price}")

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

        logger.debug(f"STEP 3.8: Adding new row for {last_row['symbol']} with updated price")
        group_updated = pd.concat([group, pd.DataFrame([new_row])], ignore_index=True)

        # Recompute ATR over the last 50 rows
        logger.debug(f"STEP 3.9: Recalculating ATR for {last_row['symbol']}")
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
        logger.debug(f"STEP 3.10: Recalculating 52-week high/low for {last_row['symbol']}")
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
        
        # Log the updated values
        logger.debug(f"STEP 3.11: Updated indicators for {last_row['symbol']}: ATR={new_atr_val:.2f}, " +
                     f"52wk high={new_52_high:.2f}, 52wk low={new_52_low:.2f}, " +
                     f"away_high={away_high:.2f}%, away_low={away_low:.2f}%")

        updated_groups.append(group_updated)
        update_counts['updated'] += 1

    df_updated = pd.concat(updated_groups, ignore_index=True)
    logger.info(f"STEP 3.12: Finished updating live data. Updated {update_counts['updated']} symbols, " +
                f"skipped {update_counts['skipped']} symbols")
    
    # Verify the updated data
    logger.info(f"STEP 3.13: Updated DataFrame has {len(df_updated)} rows, original had {len(df)} rows")
    return df_updated

def screen_eligible_stocks_vcp(df):
    """
    Returns a list of dicts representing VCP-eligible stocks from 'df'.
    This function processes data already filtered at the database level 
    (ALL and IPO segments already excluded).
    """
    logger.info("STEP 4: Starting VCP screening process")
    
    if df.empty:
        logger.warning("STEP 4.1: Empty DataFrame provided to screen_eligible_stocks_vcp! Cannot screen empty data")
        return []
        
    logger.info("STEP 4.2: Proceeding with data filtering already done at database level")
    data_to_screen = df  # No additional segment filtering needed
    logger.info(f"STEP 4.3: Working with {len(data_to_screen)} rows to screen for VCP pattern")
    
    # Log what symbols we're screening
    unique_symbols = data_to_screen['symbol'].unique()
    logger.info(f"STEP 4.4: Screening {len(unique_symbols)} unique symbols for VCP pattern")
    if len(unique_symbols) > 0:
        logger.info(f"STEP 4.5: Sample symbols: {', '.join(unique_symbols[:5])}")
    
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
            logger.info(f"STEP 4.6: Processed {symbol_counter}/{len(unique_symbols)} symbols")
            
        group = group.sort_values("date").reset_index(drop=True)
        if len(group) < 2:
            logger.debug(f"STEP 4.7: Symbol {symbol} has insufficient data (rows={len(group)})")
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

            logger.debug(f"STEP 4.8: Processing {symbol} - close={current_close}, change={price_change:.2f}%")

            # VCP screening criteria - Check each condition
            passed = True
            
            # Price > 50 SMA
            if current_close <= last_row["sma_50"]:
                logger.debug(f"STEP 4.9: {symbol} FAILED: price ({current_close:.2f}) <= SMA50 ({last_row['sma_50']:.2f})")
                rejected_counts["price_below_sma50"] += 1
                passed = False
                
            # 50 SMA > 150 SMA > 200 SMA (for uptrend)
            elif not (last_row["sma_50"] > last_row["sma_150"] and last_row["sma_150"] > last_row["sma_200"]):
                logger.debug(f"STEP 4.10: {symbol} FAILED: SMAs not in order - SMA50={last_row['sma_50']:.2f}, " + 
                            f"SMA150={last_row['sma_150']:.2f}, SMA200={last_row['sma_200']:.2f}")
                rejected_counts["sma_not_aligned"] += 1
                passed = False
                
            # 200 SMA is rising (comparison with 25 periods ago)
            elif not (float(group.iloc[max(0, last_index - 25)]["sma_200"]) < float(last_row["sma_200"])):
                old_sma200 = float(group.iloc[max(0, last_index - 25)]["sma_200"])
                current_sma200 = float(last_row["sma_200"])
                logger.debug(f"STEP 4.11: {symbol} FAILED: SMA200 not rising - past={old_sma200:.2f}, current={current_sma200:.2f}")
                rejected_counts["not_trending"] += 1
                passed = False
                
            # Stock is within 30% of 52-week high (relaxed from 25%)
            elif not (float(last_row["away_from_high"]) < 30):
                away_high = float(last_row["away_from_high"])
                logger.debug(f"STEP 4.12: {symbol} FAILED: Too far from high - {away_high:.2f}% (max 30%)")
                rejected_counts["too_extended"] += 1
                passed = False
                
            # Stock is more than 40% above 52-week low (relaxed from 50%)
            elif not (float(last_row["away_from_low"]) > 40):
                away_low = float(last_row["away_from_low"])
                logger.debug(f"STEP 4.13: {symbol} FAILED: Too close to low - {away_low:.2f}% (min 40%)")
                rejected_counts["too_far_from_low"] += 1
                passed = False
                
            if passed:
                logger.info(f"STEP 4.14: {symbol} PASSED VCP criteria! Adding to eligible stocks")
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
    logger.info(f"STEP 4.15: VCP screening results: {len(eligible_stocks)} passed, {sum(rejected_counts.values())} rejected")
    for reason, count in rejected_counts.items():
        if count > 0:
            logger.info(f"STEP 4.16: VCP rejection reason '{reason}': {count} symbols")
    
    # Log the top 5 eligible stocks
    if eligible_stocks:
        top_stocks = [f"{s['symbol']}({s['change']:.2f}%)" for s in eligible_stocks[:5]]
        logger.info(f"STEP 4.17: Top VCP stocks: {', '.join(top_stocks)}")
    
    logger.info(f"STEP 4.18: Found {len(eligible_stocks)} stocks matching VCP criteria")
    return eligible_stocks

def screen_eligible_stocks_ipo(df):
    """
    Returns a list of dicts representing IPO-eligible stocks from 'df'.
    """
    logger.info("STEP 5: Starting IPO screening process")
    
    if df.empty:
        logger.warning("STEP 5.1: Empty DataFrame provided to screen_eligible_stocks_ipo! Cannot screen empty data")
        return []
        
    logger.info("STEP 5.2: Filtering for IPO segment only")
    data_to_screen = df[df["segment"] == "IPO"]
    logger.info(f"STEP 5.3: Found {len(data_to_screen)} rows (IPO segment only) to screen for IPO pattern")
    
    # Log what symbols we're screening
    unique_symbols = data_to_screen['symbol'].unique()
    logger.info(f"STEP 5.4: Screening {len(unique_symbols)} unique IPO symbols")
    if len(unique_symbols) > 0:
        logger.info(f"STEP 5.5: IPO Symbols: {', '.join(unique_symbols[:5])}")
    
    eligible_stocks = []
    rejected_counts = {
        "not_enough_data": 0,
        "too_far_from_high": 0,
        "too_close_to_low": 0
    }

    for symbol, group in data_to_screen.groupby("symbol"):
        group = group.sort_values("date").reset_index(drop=True)
        if len(group) < 2:
            logger.debug(f"STEP 5.6: IPO {symbol} has insufficient data (rows={len(group)})")
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

            logger.debug(f"STEP 5.7: Processing IPO {symbol} - close={current_close}, change={price_change:.2f}%")

            # Simple IPO screening logic - slightly relaxed
            away_from_high = float(last_row["away_from_high"])
            away_from_low = float(last_row["away_from_low"])
            
            # Check conditions separately for better logging
            passed = True
            
            if away_from_high >= 30:  # Relaxed from 25
                logger.debug(f"STEP 5.8: IPO {symbol} FAILED: Too far from high - {away_from_high:.2f}% (max 30%)")
                rejected_counts["too_far_from_high"] += 1
                passed = False
                
            elif away_from_low <= 20:  # Relaxed from 25
                logger.debug(f"STEP 5.9: IPO {symbol} FAILED: Too close to low - {away_from_low:.2f}% (min 20%)")
                rejected_counts["too_close_to_low"] += 1
                passed = False
                
            if passed:
                logger.info(f"STEP 5.10: IPO {symbol} PASSED criteria! Adding to eligible stocks")
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
    logger.info(f"STEP 5.11: IPO screening results: {len(eligible_stocks)} passed, {sum(rejected_counts.values())} rejected")
    for reason, count in rejected_counts.items():
        if count > 0:
            logger.info(f"STEP 5.12: IPO rejection reason '{reason}': {count} symbols")
    
    # Log the eligible stocks
    if eligible_stocks:
        ipo_stocks = [f"{s['symbol']}({s['change']:.2f}%)" for s in eligible_stocks]
        logger.info(f"STEP 5.13: Eligible IPO stocks: {', '.join(ipo_stocks)}")
    
    logger.info(f"STEP 5.14: Found {len(eligible_stocks)} stocks matching IPO criteria")
    return eligible_stocks

def screen_eligible_stocks_weekly(df):
    """
    Returns a list of dicts representing stocks meeting weekly screening criteria from 'df'.
    Weekly criteria: current close > 50sma > 150sma > 200sma
    This function processes data already filtered at the database level
    (IPO segment already excluded, ALL segment included).
    """
    logger.info("STEP 6: Starting Weekly VCP screening process")
    
    if df.empty:
        logger.warning("STEP 6.1: Empty DataFrame provided to screen_eligible_stocks_weekly! Cannot screen empty data")
        return []
        
    logger.info("STEP 6.2: Proceeding with data filtering already done at database level")
    data_to_screen = df  # No additional segment filtering needed
    logger.info(f"STEP 6.3: Working with {len(data_to_screen)} rows to screen for weekly pattern")
    
    # Log what symbols we're screening
    unique_symbols = data_to_screen['symbol'].unique()
    logger.info(f"STEP 6.4: Screening {len(unique_symbols)} unique symbols for weekly pattern")
    if len(unique_symbols) > 0:
        logger.info(f"STEP 6.5: Sample weekly symbols: {', '.join(unique_symbols[:5])}")
    
    # Get segment stats for debugging
    segment_counts = data_to_screen['segment'].value_counts().to_dict()
    logger.info(f"STEP 6.5.1: Segment distribution: {segment_counts}")
    
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
            logger.info(f"STEP 6.6: Processed {symbol_counter}/{len(unique_symbols)} symbols for weekly screening")
            
        group = group.sort_values("date").reset_index(drop=True)
        if len(group) < 2:
            logger.debug(f"STEP 6.7: Weekly symbol {symbol} has insufficient data (rows={len(group)})")
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

            logger.debug(f"STEP 6.8: Processing weekly {symbol} - close={current_close}, change={price_change:.2f}%")

            # Weekly screening criteria - Check each condition
            passed = True
            
            # Price > 50 SMA
            if current_close <= last_row["sma_50"]:
                logger.debug(f"STEP 6.9: Weekly {symbol} FAILED: price ({current_close:.2f}) <= SMA50 ({last_row['sma_50']:.2f})")
                rejected_counts["price_below_sma50"] += 1
                passed = False
                
            # 50 SMA > 150 SMA > 200 SMA (for uptrend)
            elif not (last_row["sma_50"] > last_row["sma_150"] and last_row["sma_150"] > last_row["sma_200"]):
                logger.debug(f"STEP 6.10: Weekly {symbol} FAILED: SMAs not in order - SMA50={last_row['sma_50']:.2f}, " + 
                            f"SMA150={last_row['sma_150']:.2f}, SMA200={last_row['sma_200']:.2f}")
                rejected_counts["sma_not_aligned"] += 1
                passed = False
                
            # 200 SMA is rising (comparison with 25 periods ago)
            elif not (float(group.iloc[max(0, last_index - 25)]["sma_200"]) < float(last_row["sma_200"])):
                old_sma200 = float(group.iloc[max(0, last_index - 25)]["sma_200"])
                current_sma200 = float(last_row["sma_200"])
                logger.debug(f"STEP 6.11: Weekly {symbol} FAILED: SMA200 not rising - past={old_sma200:.2f}, current={current_sma200:.2f}")
                rejected_counts["not_trending"] += 1
                passed = False
                
            # Stock is within 30% of 52-week high (relaxed from 25%)
            elif not (float(last_row["away_from_high"]) < 30):
                away_high = float(last_row["away_from_high"])
                logger.debug(f"STEP 6.12: Weekly {symbol} FAILED: Too far from high - {away_high:.2f}% (max 30%)")
                rejected_counts["too_extended"] += 1
                passed = False
                
            # Stock is more than 40% above 52-week low (relaxed from 50%)
            elif not (float(last_row["away_from_low"]) > 40):
                away_low = float(last_row["away_from_low"])
                logger.debug(f"STEP 6.13: Weekly {symbol} FAILED: Too close to low - {away_low:.2f}% (min 40%)")
                rejected_counts["too_far_from_low"] += 1
                passed = False
                
            if passed:
                logger.info(f"STEP 6.14: Weekly {symbol} PASSED criteria! Adding to eligible stocks")
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
            logger.error(f"ERROR processing weekly symbol {symbol}: {e}", exc_info=True)

    eligible_stocks.sort(key=lambda x: x["change"], reverse=True)
    
    # Log detailed stats about screening results
    logger.info(f"STEP 6.15: Weekly screening results: {len(eligible_stocks)} passed, {sum(rejected_counts.values())} rejected")
    for reason, count in rejected_counts.items():
        if count > 0:
            logger.info(f"STEP 6.16: Weekly rejection reason '{reason}': {count} symbols")
    
    # Log the top 5 eligible stocks
    if eligible_stocks:
        top_stocks = [f"{s['symbol']}({s['change']:.2f}%)" for s in eligible_stocks[:5]]
        logger.info(f"STEP 6.17: Top Weekly VCP stocks: {', '.join(top_stocks)}")
    
    logger.info(f"STEP 6.18: Found {len(eligible_stocks)} stocks matching weekly criteria")
    return eligible_stocks

def is_new_week(last_date, current_date):
    """
    Determines if two dates belong to different ISO calendar weeks.
    
    This is the key function for deciding when to create a new weekly candle 
    versus updating an existing one. Using ISO calendar week numbers ensures
    that candles align with standard weekly boundaries (Monday to Sunday).
    
    This approach naturally handles:
    - Weekend gaps (quotes from Friday and Monday belong to different weeks)
    - Holiday gaps (quotes before and after a holiday in the same week stay in the same candle)
    - Year transitions (week 1 of new year vs week 52/53 of previous year)
    
    Args:
        last_date: Datetime representing the last bar date
        current_date: Datetime representing the current date
    
    Returns:
        bool: True if current_date is in a new week compared to last_date
    """
    logger.debug(f"STEP W1: Checking if {current_date} is in a new week compared to {last_date}")
    
    # Convert to datetime objects if they're not already
    if isinstance(last_date, str):
        logger.debug("STEP W2: Converting last_date string to datetime")
        last_date = pd.to_datetime(last_date).to_pydatetime()
    if isinstance(current_date, str):
        logger.debug("STEP W3: Converting current_date string to datetime")
        current_date = pd.to_datetime(current_date).to_pydatetime()
    
    # Ensure timezone is set
    if last_date.tzinfo is None:
        logger.debug("STEP W4: Setting timezone for last_date")
        last_date = last_date.replace(tzinfo=TIMEZONE)
    if current_date.tzinfo is None:
        logger.debug("STEP W5: Setting timezone for current_date")
        current_date = current_date.replace(tzinfo=TIMEZONE)
    
    # Get ISO calendar year and week number
    # We check both year and week number to handle year transitions correctly
    last_year_week = (last_date.year, last_date.isocalendar()[1])
    current_year_week = (current_date.year, current_date.isocalendar()[1])
    
    logger.debug(f"STEP W6: Last date year-week: {last_year_week}, Current date year-week: {current_year_week}")
    
    is_new = last_year_week != current_year_week
    logger.debug(f"STEP W7: Is new week? {is_new}")
    return is_new

def update_weekly_live_data(df, live_data):
    """
    Updates weekly candle data with live quotes.
    
    Key logic:
    1. For each instrument with live quotes, we check if we're in the same week as the last candle
    2. If in the same week, we UPDATE the last candle's OHLC values (keeping original open, updating high/low/close)
    3. If in a new week, we CREATE a new candle with the live quote as OHLC values
    4. In both cases, we recalculate technical indicators
    
    This handles weekends and holidays naturally because:
    - Any quote from a mid-week holiday will be part of the same week's candle
    - Calendar week boundaries (not trading days) determine when to create a new candle
    
    Args:
        df: DataFrame containing weekly OHLC data
        live_data: Dictionary of instrument_token -> live price
        
    Returns:
        Updated DataFrame with live quotes incorporated
    """
    logger.info("STEP 10: Starting update_weekly_live_data to incorporate live prices")
    
    if df.empty:
        logger.warning("STEP 10.1: update_weekly_live_data called with empty DataFrame; returning as is")
        return df
        
    if not live_data:
        logger.debug("STEP 10.2: No live data to update weekly data; returning original DataFrame")
        return df

    logger.info(f"STEP 10.3: Starting to update weekly data for {len(df['instrument_token'].unique())} unique instruments")
    logger.info(f"STEP 10.4: We have live prices for {len(live_data)} instruments")
    
    # Find overlap between data and live quotes
    df_tokens = set(df['instrument_token'].unique())
    live_tokens = set(live_data.keys())
    overlap = df_tokens.intersection(live_tokens)
    logger.info(f"STEP 10.5: Overlap between weekly DataFrame tokens and live data: {len(overlap)} instruments")
    
    updated_groups = []
    current_date = datetime.datetime.now(TIMEZONE)
    logger.info(f"STEP 10.6: Current date for weekly update: {current_date}")
    
    update_counts = {'updated_existing': 0, 'created_new': 0, 'skipped': 0}
    
    logger.info("STEP 10.7: Processing each weekly instrument group")
    for token, group in df.groupby("instrument_token"):
        group = group.sort_values("date").reset_index(drop=True)
        
        if token not in live_data:
            updated_groups.append(group)
            update_counts['skipped'] += 1
            continue

        live_price = live_data[token]
        last_row = group.iloc[-1]
        symbol = last_row['symbol']
        
        # Check if last row is from the current week using ISO calendar week numbers
        last_date = pd.to_datetime(last_row["date"]).to_pydatetime()
        logger.debug(f"STEP 10.8: Checking week for {symbol}: last date = {last_date}")
        create_new_bar = is_new_week(last_date, current_date)
        
        if create_new_bar:
            logger.info(f"STEP 10.9: Creating NEW weekly bar for {symbol} with live price {live_price}")
            update_counts['created_new'] += 1
            
            # Create a new weekly bar with live price
            new_row = {
                "instrument_token": token,
                "symbol": last_row["symbol"],
                "interval": "week",
                "date": current_date,
                "open": live_price,  # For a new bar, open = current price
                "high": live_price,
                "low": live_price,
                "close": live_price,
                "volume": 0, # Volume for live tick is unknown/0
                "segment": last_row["segment"],
                # Indicators will be fully recalculated below
            }
        else:
            logger.debug(f"STEP 10.10: Updating EXISTING weekly bar for {symbol} with live price {live_price}")
            update_counts['updated_existing'] += 1
            
            # Update the existing weekly bar's OHLC values
            # - Keep the original open (from the week's first trading day)
            # - Update high/low if the live price exceeds current values
            # - Always update close to the latest price
            new_row = {
                "instrument_token": token,
                "symbol": last_row["symbol"],
                "interval": "week",
                "date": last_date,  # Keep the original date of the weekly bar
                "open": last_row["open"],  # Keep the original open
                "high": max(float(last_row["high"]), live_price), # Ensure comparison with float
                "low": min(float(last_row["low"]), live_price),   # Ensure comparison with float
                "close": live_price,
                "volume": last_row["volume"], # Keep existing volume (or add logic if available)
                "segment": last_row["segment"],
                 # Indicators will be fully recalculated below
            }
            
            # Remove the last row as we'll replace it
            group = group.iloc[:-1]

        # Add the updated or new row (without old indicators)
        logger.debug(f"STEP 10.11: Adding new/updated OHLC row to group for {symbol}")
        # Ensure consistent data types before concat
        group['high'] = group['high'].astype(float)
        group['low'] = group['low'].astype(float)
        group['close'] = group['close'].astype(float)
        new_row_df = pd.DataFrame([new_row])
        new_row_df['high'] = new_row_df['high'].astype(float)
        new_row_df['low'] = new_row_df['low'].astype(float)
        new_row_df['close'] = new_row_df['close'].astype(float)
        
        group_updated = pd.concat([group, new_row_df], ignore_index=True)
        
        # --- Full Recalculation of Indicators ---
        logger.debug(f"STEP 10.12: Starting full indicator recalculation for {symbol}")

        # Ensure required columns are numeric for pandas_ta
        group_updated['open'] = pd.to_numeric(group_updated['open'], errors='coerce')
        group_updated['high'] = pd.to_numeric(group_updated['high'], errors='coerce')
        group_updated['low'] = pd.to_numeric(group_updated['low'], errors='coerce')
        group_updated['close'] = pd.to_numeric(group_updated['close'], errors='coerce')
        group_updated['volume'] = pd.to_numeric(group_updated['volume'], errors='coerce')

        # Recalculate SMAs for the entire series
        logger.debug(f"STEP 10.13: Recalculating SMA series for {symbol}")
        for sma_len in [50, 150, 200]:
            col_name = f"sma_{sma_len}"
            if len(group_updated) >= sma_len:
                # Calculate the full SMA series
                sma_series = ta.sma(group_updated["close"], length=sma_len)
                # Assign the series back to the DataFrame
                group_updated[col_name] = sma_series.astype(float) 
                logger.debug(f"STEP 10.14: Recalculated {col_name} series. Last value: {group_updated[col_name].iloc[-1]:.2f}")
            else:
                 # Assign NaN if not enough data
                group_updated[col_name] = float('nan')
                logger.debug(f"STEP 10.14: Not enough data for {col_name}, assigning NaN.")

        # Recalculate ATR for the entire series
        logger.debug(f"STEP 10.15: Recalculating ATR series for {symbol}")
        # ATR typically uses length 14, ensure we have enough data
        atr_len = 14 
        if len(group_updated) > atr_len: # Need atr_len + 1 for calculation start
             # Calculate the full ATR series
             atr_series = ta.atr(
                 high=group_updated["high"],
                 low=group_updated["low"],
                 close=group_updated["close"],
                 length=atr_len
             )
             # Assign the series back
             group_updated["atr"] = atr_series.astype(float)
             logger.debug(f"STEP 10.16: Recalculated ATR series. Last value: {group_updated['atr'].iloc[-1]:.2f}")
        else:
            # Assign NaN if not enough data
            group_updated["atr"] = float('nan')
            logger.debug(f"STEP 10.16: Not enough data for ATR, assigning NaN.")


        # Recalculate 52-week high/low using rolling window on the updated series
        logger.debug(f"STEP 10.17: Recalculating 52-week high/low series for {symbol}")
        window_52_week = 52
        # Calculate rolling max over the 'high' column for the last 52 periods (or available)
        group_updated['52_week_high'] = group_updated['high'].rolling(window=window_52_week, min_periods=1).max()
        # Calculate rolling min over the 'low' column for the last 52 periods (or available)
        group_updated['52_week_low'] = group_updated['low'].rolling(window=window_52_week, min_periods=1).min()
        logger.debug(f"STEP 10.18: Recalculated 52-week high/low series. Last H/L: {group_updated['52_week_high'].iloc[-1]:.2f} / {group_updated['52_week_low'].iloc[-1]:.2f}")


        # Recalculate away_from_high / away_from_low based on the *last* values
        logger.debug(f"STEP 10.19: Recalculating away_from high/low for {symbol} using last values")
        last_idx = len(group_updated) - 1
        last_close = group_updated.at[last_idx, "close"]
        last_52_high = group_updated.at[last_idx, "52_week_high"]
        last_52_low = group_updated.at[last_idx, "52_week_low"]

        away_high = 0.0
        away_low = 0.0
        if pd.notna(last_52_high) and last_52_high != 0 and pd.notna(last_close):
            away_high = ((last_52_high - last_close) / last_52_high) * 100
        if pd.notna(last_52_low) and last_52_low != 0 and pd.notna(last_close):
            away_low = ((last_close - last_52_low) / last_52_low) * 100
        
        # Assign calculated percentages for the last row only (as they depend only on the last point)
        group_updated.loc[last_idx, "away_from_high"] = away_high
        group_updated.loc[last_idx, "away_from_low"] = away_low
        logger.debug(f"STEP 10.20: Updated away_from_high/low: {away_high:.2f}% / {away_low:.2f}%")
        # Fill potentially missing values in earlier rows if needed, though usually only the last matters for screening
        group_updated["away_from_high"].fillna(method='ffill', inplace=True) 
        group_updated["away_from_low"].fillna(method='ffill', inplace=True)


        # --- End of Full Recalculation ---

        updated_groups.append(group_updated)

    # Combine all updated groups
    df_updated = pd.concat(updated_groups, ignore_index=True)
    logger.info(f"STEP 10.22: Finished updating weekly data. Created {update_counts['created_new']} new bars, " +
                f"updated {update_counts['updated_existing']} existing bars, skipped {update_counts['skipped']} symbols")
    
    # Log final data shape
    logger.info(f"STEP 10.23: Updated weekly DataFrame has {len(df_updated)} rows (original had {len(df)} rows)")
    
    return df_updated

def run_vcp_screener():
    """
    1) Load precomputed data (or use cached global).
    2) If market is open, fetch live quotes and update last row.
    3) Screen VCP.
    4) Clear old "vcp" results from screener_results table.
    5) Insert new results for "vcp".
    """
    logger.info("===== STEP 7: Starting VCP Screener =====")
    global ohlc_data

    # Load or reuse cached data
    if ohlc_data is None or ohlc_data.empty:
        logger.info("STEP 7.1: No OHLC data cached; loading from DB")
        ohlc_data = load_precomputed_ohlc()
        
    if ohlc_data is None or ohlc_data.empty:
        logger.error("STEP 7.2: Failed to load OHLC data for VCP screener. Aborting")
        return False

    logger.info(f"STEP 7.3: Working with DataFrame of shape {ohlc_data.shape} for VCP screening")
    df = ohlc_data.copy()
    logger.info(f"STEP 7.4: Made a copy of OHLC data for processing")

    # Check market hours
    now = datetime.datetime.now(TIMEZONE).time()
    logger.info(f"STEP 7.5: Current time: {now}. Checking if within market hours (9:15-15:30)")
    
    if datetime.time(9,15) <= now <= datetime.time(15,30):
        logger.info("STEP 7.6: Market is open. Will fetch live quotes")
        try:
            live_data = fetch_live_quotes()
            if live_data:
                logger.info(f"STEP 7.7: Fetched live quotes for {len(live_data)} instruments")
                df = update_live_data(df, live_data)
                logger.info("STEP 7.8: Successfully updated data with live quotes")
            else:
                logger.warning("STEP 7.9: No live quotes fetched. Using historical data only")
        except Exception as e:
            logger.error(f"STEP 7.10: Error fetching live quotes: {e}. Using historical data only")
    else:
        logger.info("STEP 7.11: Market closed. Skipping live data update")

    # Screen for VCP
    try:
        logger.info("STEP 7.12: Starting VCP pattern screening")
        vcp_results = screen_eligible_stocks_vcp(df)
        logger.info(f"STEP 7.13: VCP screening returned {len(vcp_results)} eligible stocks")
    except Exception as e:
        logger.error(f"STEP 7.14: Error during VCP screening: {e}", exc_info=True)
        return False

    # Save results
    logger.info("STEP 7.15: Connecting to DB to save VCP screener results")
    conn, cur = get_trade_db_connection()
    try:
        # CLEAR old VCP results
        logger.info("STEP 7.16: Deleting old 'vcp' screener results")
        ScreenerResult.delete_all_by_screener(cur, "vcp")
        logger.info("STEP 7.17: Old VCP results deleted successfully")

        # INSERT new VCP results
        logger.info(f"STEP 7.18: Inserting {len(vcp_results)} new VCP results")
        for i, stock in enumerate(vcp_results):
            if i < 5 or i % 50 == 0:  # Log first 5 and then every 50th
                logger.info(f"STEP 7.19: Inserting VCP result {i+1}/{len(vcp_results)}: {stock['symbol']}")
                
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

        logger.info("STEP 7.20: Committing VCP screener results to database")
        conn.commit()
        logger.info(f"STEP 7.21: [VCP Screener] Successfully saved {len(vcp_results)} results")
        return True
    except Exception as e:
        logger.error(f"STEP 7.22: Error in run_vcp_screener: {e}", exc_info=True)
        logger.info("STEP 7.23: Rolling back database transaction")
        conn.rollback()
        return False
    finally:
        logger.info("STEP 7.24: Releasing database connection")
        release_trade_db_connection(conn, cur)
        logger.info("===== STEP 7.25: Finished VCP Screener =====")

def run_ipo_screener():
    """
    1) Load precomputed data (or use cached global).
    2) If market is open, fetch live quotes and update last row.
    3) Screen IPO.
    4) Clear old "ipo" results from screener_results table.
    5) Insert new results for "ipo".
    """
    logger.info("===== STEP 8: Starting IPO Screener =====")
    global ohlc_data

    # Load or reuse cached data
    if ohlc_data is None or ohlc_data.empty:
        logger.info("STEP 8.1: No OHLC data cached; loading from DB")
        ohlc_data = load_precomputed_ohlc()
        
    if ohlc_data is None or ohlc_data.empty:
        logger.error("STEP 8.2: Failed to load OHLC data for IPO screener. Aborting")
        return False

    logger.info(f"STEP 8.3: Working with DataFrame of shape {ohlc_data.shape} for IPO screening")
    df = ohlc_data.copy()
    logger.info(f"STEP 8.4: Made a copy of OHLC data for processing")

    # Check market hours
    now = datetime.datetime.now(TIMEZONE).time()
    logger.info(f"STEP 8.5: Current time: {now}. Checking if within market hours (9:15-15:30)")
    
    if datetime.time(9,15) <= now <= datetime.time(15,30):
        logger.info("STEP 8.6: Market is open. Will fetch live quotes")
        try:
            live_data = fetch_live_quotes()
            if live_data:
                logger.info(f"STEP 8.7: Fetched live quotes for {len(live_data)} instruments")
                df = update_live_data(df, live_data)
                logger.info("STEP 8.8: Successfully updated data with live quotes")
            else:
                logger.warning("STEP 8.9: No live quotes fetched. Using historical data only")
        except Exception as e:
            logger.error(f"STEP 8.10: Error fetching live quotes: {e}. Using historical data only")
    else:
        logger.info("STEP 8.11: Market closed. Skipping live data update")

    # Screen for IPO
    try:
        logger.info("STEP 8.12: Starting IPO screening")
        ipo_results = screen_eligible_stocks_ipo(df)
        logger.info(f"STEP 8.13: IPO screening returned {len(ipo_results)} eligible stocks")
    except Exception as e:
        logger.error(f"STEP 8.14: Error during IPO screening: {e}", exc_info=True)
        return False

    # Save results
    logger.info("STEP 8.15: Connecting to DB to save IPO screener results")
    conn, cur = get_trade_db_connection()
    try:
        # CLEAR old IPO results
        logger.info("STEP 8.16: Deleting old 'ipo' screener results")
        ScreenerResult.delete_all_by_screener(cur, "ipo")
        logger.info("STEP 8.17: Old IPO results deleted successfully")

        # INSERT new IPO results
        logger.info(f"STEP 8.18: Inserting {len(ipo_results)} new IPO results")
        for i, stock in enumerate(ipo_results):
            logger.info(f"STEP 8.19: Inserting IPO result {i+1}/{len(ipo_results)}: {stock['symbol']}")
                
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

        logger.info("STEP 8.20: Committing IPO screener results to database")
        conn.commit()
        logger.info(f"STEP 8.21: [IPO Screener] Successfully saved {len(ipo_results)} results")
        return True
    except Exception as e:
        logger.error(f"STEP 8.22: Error in run_ipo_screener: {e}", exc_info=True)
        logger.info("STEP 8.23: Rolling back database transaction")
        conn.rollback()
        return False
    finally:
        logger.info("STEP 8.24: Releasing database connection")
        release_trade_db_connection(conn, cur)
        logger.info("===== STEP 8.25: Finished IPO Screener =====")

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
    
    This function properly handles:
    - Partial week data (ongoing candle formation during the current week)
    - Weekend transitions
    - Holiday gaps within the same week
    
    NOTE: Unlike the daily VCP screener, this includes ALL segments except IPOs.
    """
    logger.info("===== STEP 9: Starting Weekly Screener =====")
    global weekly_ohlc_data

    # Load or reuse cached data
    if weekly_ohlc_data is None or weekly_ohlc_data.empty:
        logger.info("STEP 9.1: No weekly OHLC data cached; loading from DB")
        weekly_ohlc_data = load_precomputed_weekly_ohlc()
        
    if weekly_ohlc_data is None or weekly_ohlc_data.empty:
        logger.error("STEP 9.2: Failed to load weekly OHLC data for weekly screener. Aborting")
        return False

    logger.info(f"STEP 9.3: Working with DataFrame of shape {weekly_ohlc_data.shape} for weekly screening")
    df = weekly_ohlc_data.copy()
    logger.info(f"STEP 9.4: Made a copy of weekly OHLC data for processing")

    # Check market hours
    now = datetime.datetime.now(TIMEZONE).time()
    logger.info(f"STEP 9.5: Current time: {now}. Checking if within market hours (9:15-15:30)")
    
    if datetime.time(9,15) <= now <= datetime.time(15,30):
        logger.info("STEP 9.6: Market is open. Will fetch live quotes")
        try:
            live_data = fetch_live_quotes()
            if live_data:
                logger.info(f"STEP 9.7: Fetched live quotes for {len(live_data)} instruments")
                # Use the weekly-specific update function that handles same-week updates
                # and new-week transitions based on ISO calendar week
                df = update_weekly_live_data(df, live_data)
                logger.info("STEP 9.8: Successfully updated weekly data with live quotes")
            else:
                logger.warning("STEP 9.9: No live quotes fetched. Using historical data only")
        except Exception as e:
            logger.error(f"STEP 9.10: Error fetching live quotes: {e}. Using historical data only")
    else:
        logger.info("STEP 9.11: Market closed. Skipping live data update")

    # Screen for weekly pattern
    try:
        logger.info("STEP 9.12: Starting weekly pattern screening")
        weekly_results = screen_eligible_stocks_weekly(df)
        logger.info(f"STEP 9.13: Weekly screening returned {len(weekly_results)} eligible stocks")
    except Exception as e:
        logger.error(f"STEP 9.14: Error during weekly screening: {e}", exc_info=True)
        return False

    # Save results
    logger.info("STEP 9.15: Connecting to DB to save Weekly screener results")
    conn, cur = get_trade_db_connection()
    try:
        # CLEAR old Weekly results
        logger.info("STEP 9.16: Deleting old 'weekly_vcp' screener results")
        ScreenerResult.delete_all_by_screener(cur, "weekly_vcp")
        logger.info("STEP 9.17: Old weekly_vcp results deleted successfully")

        # INSERT new Weekly results
        logger.info(f"STEP 9.18: Inserting {len(weekly_results)} new Weekly results")
        for i, stock in enumerate(weekly_results):
            if i < 5 or i % 50 == 0:  # Log first 5 and then every 50th
                logger.info(f"STEP 9.19: Inserting weekly result {i+1}/{len(weekly_results)}: {stock['symbol']}")
                
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

        logger.info("STEP 9.20: Committing weekly screener results to database")
        conn.commit()
        logger.info(f"STEP 9.21: [Weekly Screener] Successfully saved {len(weekly_results)} results")
        return True
    except Exception as e:
        logger.error(f"STEP 9.22: Error in run_weekly_vcp_screener: {e}", exc_info=True)
        logger.info("STEP 9.23: Rolling back database transaction")
        conn.rollback()
        return False
    finally:
        logger.info("STEP 9.24: Releasing database connection")
        release_trade_db_connection(conn, cur)
        logger.info("===== STEP 9.25: Finished Weekly Screener =====")
