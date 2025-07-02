#!/usr/bin/env python3
"""
Optimized OHLC Data Collection Service
Uses parallel processing and batch operations to improve performance
"""

import datetime
import time
import pandas as pd
import pandas_ta as ta
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional
import asyncio
from functools import partial
import threading

from controllers import kite
from db import get_db_connection, close_db_connection
from models import SaveOHLC

logger = logging.getLogger(__name__)

# Thread-safe counter for API rate limiting
class APIRateLimiter:
    def __init__(self, max_requests_per_second: int = 5):
        self.max_requests_per_second = max_requests_per_second
        self.request_times = []
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if we're hitting rate limits"""
        with self.lock:
            now = time.time()
            # Remove requests older than 1 second
            self.request_times = [t for t in self.request_times if now - t < 1.0]
            
            # If we're at the limit, wait
            if len(self.request_times) >= self.max_requests_per_second:
                sleep_time = 1.0 - (now - self.request_times[0])
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    # Clean up old requests after sleeping
                    now = time.time()
                    self.request_times = [t for t in self.request_times if now - t < 1.0]
            
            # Record this request
            self.request_times.append(now)

# Global rate limiter
rate_limiter = APIRateLimiter(max_requests_per_second=3)  # Conservative rate limit

def delay(ms):
    """Delay function to simulate async pauses."""
    time.sleep(ms / 1000)

def fetch_ohlc_for_token(token_data: Tuple, interval: str) -> Dict:
    """
    Fetch OHLC data for a single token with error handling and rate limiting.
    
    Args:
        token_data: Tuple of (instrument_token, symbol, segment, ...)
        interval: Time interval ('day' or 'week')
        
    Returns:
        Dict with success status and data or error
    """
    instrument_token, symbol, segment = token_data[0], token_data[1], token_data[4]
    
    try:
        if not kite.access_token:
            return {
                "success": False, 
                "symbol": symbol, 
                "error": "Missing Kite access token"
            }
        
        # Apply rate limiting
        rate_limiter.wait_if_needed()
        
        # Determine fetch parameters based on interval - use full API capacity
        if interval == "week":
            day_count = 2000
            loop_count = 1  # Single call for weekly data
        else:
            day_count = 2000  # Use full API capacity in single call
            loop_count = 1    # Only one call needed for 2000 days
        
        hist = []
        to_date = datetime.datetime.now()
        
        # Fetch historical data using full 2000-day API capacity in single call
        # This ensures sufficient data for accurate SMA calculations  
        for i in range(loop_count):
            time_window_to = to_date.isoformat()[:10]
            time_window_from = (to_date - datetime.timedelta(days=day_count)).isoformat()[:10]
            
            try:
                data = kite.historical_data(
                    instrument_token,
                    time_window_from,
                    time_window_to,
                    interval
                )
                if data:
                    hist.extend(data)
            except Exception as err:
                logger.error(f"Error fetching OHLC data for {symbol}: {err}")
                return {
                    "success": False,
                    "symbol": symbol,
                    "error": str(err)
                }
            
            to_date = to_date - datetime.timedelta(days=day_count + 1)
            # Small delay between chunks
            time.sleep(0.1)
        
        if not hist:
            return {
                "success": False,
                "symbol": symbol,
                "error": "No data returned from API"
            }
        
        # Process the data
        processed_data = process_ohlc_data(hist, instrument_token, symbol, interval, segment)
        
        return {
            "success": True,
            "symbol": symbol,
            "data": processed_data,
            "rows_count": len(processed_data)
        }
        
    except Exception as e:
        logger.error(f"Unexpected error fetching OHLC for {symbol}: {e}")
        return {
            "success": False,
            "symbol": symbol,
            "error": str(e)
        }

def process_ohlc_data(hist: List[Dict], instrument_token: int, symbol: str, interval: str, segment: str) -> List[Tuple]:
    """
    Process raw OHLC data and calculate technical indicators.
    
    Args:
        hist: Raw OHLC data from API
        instrument_token: Instrument token
        symbol: Stock symbol
        interval: Time interval
        segment: Market segment
        
    Returns:
        List of processed data tuples ready for database insertion
    """
    try:
        # Remove duplicates and sort
        hist = list({tuple(item.items()): item for item in hist}.values())
        hist.sort(key=lambda x: x['date'])
        
        # Convert to DataFrame
        df = pd.DataFrame(hist)
        
        # Convert to appropriate data types
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Calculate technical indicators efficiently
        df = calculate_indicators_efficiently(df)
        
        # Prepare data for batch insertion
        batch_data = []
        for _, row in df.iterrows():
            batch_data.append((
                instrument_token,
                symbol,
                interval,
                row['date'].isoformat() if isinstance(row['date'], (datetime.date, datetime.datetime)) else row['date'],
                float(row['open']),
                float(row['high']),
                float(row['low']),
                float(row['close']),
                float(row['volume']),
                segment,
                float(row.get("sma_50", 0)),
                float(row.get("sma_100", 0)),
                float(row.get("sma_200", 0)),
                float(row.get("atr", 0)),
                float(row.get("52_week_high", 0)),
                float(row.get("52_week_low", 0)),
                float(row.get("away_from_high", 0)),
                float(row.get("away_from_low", 0))
            ))
        
        return batch_data
        
    except Exception as e:
        logger.error(f"Error processing OHLC data for {symbol}: {e}")
        return []

def calculate_indicators_efficiently(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate technical indicators efficiently with proper error handling.
    
    Args:
        df: OHLC DataFrame
        
    Returns:
        DataFrame with calculated indicators
    """
    try:
        # Use adaptive window sizes based on available data
        data_length = len(df)
        length_50 = min(50, data_length)
        length_100 = min(100, data_length)
        length_200 = min(200, data_length)
        length_252 = min(252, data_length)
        
        # Calculate indicators only if we have sufficient data
        if length_50 > 10:
            df["sma_50"] = ta.sma(df["close"], length=length_50)
        else:
            df["sma_50"] = 0
            
        if length_100 > 10:
            df["sma_100"] = ta.sma(df["close"], length=length_100)
        else:
            df["sma_100"] = 0
            
        if length_200 > 10:
            df["sma_200"] = ta.sma(df["close"], length=length_200)
        else:
            df["sma_200"] = 0
            
        if length_50 > 10:
            df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=length_50)
        else:
            df["atr"] = 0
        
        # 52-week high/low calculations
        if length_252 > 10:
            df["52_week_high"] = df["high"].rolling(window=length_252, min_periods=1).max()
            df["52_week_low"] = df["low"].rolling(window=length_252, min_periods=1).min()
        else:
            df["52_week_high"] = df["high"]
            df["52_week_low"] = df["low"]
        
        # Calculate percentages
        df["away_from_high"] = ((df["52_week_high"] - df["close"]) / df["52_week_high"] * 100).fillna(0)
        df["away_from_low"] = ((df["close"] - df["52_week_low"]) / df["52_week_low"] * 100).fillna(0)
        
        # Replace NaN and infinite values
        df = df.fillna(0)
        df.replace([float('inf'), float('-inf')], 0, inplace=True)
        
        return df
        
    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")
        # Return DataFrame with zero indicators if calculation fails
        for col in ["sma_50", "sma_100", "sma_200", "atr", "52_week_high", "52_week_low", "away_from_high", "away_from_low"]:
            df[col] = 0
        return df

def batch_insert_ohlc_data(all_batch_data: List[List[Tuple]], interval: str) -> bool:
    """
    Insert OHLC data in batches for better performance.
    
    Args:
        all_batch_data: List of batch data from all tokens
        interval: Time interval
        
    Returns:
        Success status
    """
    try:
        conn, cur = get_db_connection()
        
        # Flatten all batch data
        flattened_data = []
        for batch_data in all_batch_data:
            flattened_data.extend(batch_data)
        
        if not flattened_data:
            logger.warning("No data to insert")
            return True
        
        # Batch insert query with conflict resolution
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
            ON CONFLICT (instrument_token, symbol, interval, date) 
            DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                segment = EXCLUDED.segment,
                sma_50 = EXCLUDED.sma_50,
                sma_100 = EXCLUDED.sma_100,
                sma_200 = EXCLUDED.sma_200,
                atr = EXCLUDED.atr,
                "52_week_high" = EXCLUDED."52_week_high",
                "52_week_low" = EXCLUDED."52_week_low",
                away_from_high = EXCLUDED.away_from_high,
                away_from_low = EXCLUDED.away_from_low
        """
        
        # Insert in smaller batches to avoid memory issues
        batch_size = 1000
        total_inserted = 0
        
        for i in range(0, len(flattened_data), batch_size):
            batch = flattened_data[i:i + batch_size]
            cur.executemany(insert_query, batch)
            total_inserted += len(batch)
            
            if i % (batch_size * 10) == 0:  # Log progress every 10k rows
                logger.info(f"Inserted {total_inserted}/{len(flattened_data)} rows")
        
        conn.commit()
        logger.info(f"Successfully inserted {total_inserted} total rows for interval {interval}")
        return True
        
    except Exception as e:
        logger.error(f"Error in batch insert: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if 'conn' in locals() and 'cur' in locals():
            close_db_connection()

def get_equity_ohlc_data_optimized(interval: str, max_workers: int = 10) -> Dict:
    """
    Optimized OHLC data collection using parallel processing.
    
    Args:
        interval: Time interval ('day' or 'week')
        max_workers: Maximum number of parallel workers
        
    Returns:
        Result dictionary with status and statistics
    """
    start_time = time.time()
    
    try:
        # Clear existing data for the interval
        conn, cur = get_db_connection()
        SaveOHLC.delete_by_interval(cur, interval)
        logger.info(f"Cleared existing data for interval: {interval}")
        close_db_connection()
        
        # Get all equity tokens
        conn, cur = get_db_connection()
        select_query = "SELECT * FROM equity_tokens;"
        cur.execute(select_query)
        tokens = cur.fetchall()
        close_db_connection()
        
        logger.info(f"Starting optimized OHLC collection for {len(tokens)} tokens using {max_workers} workers")
        
        successful_fetches = []
        failed_fetches = []
        
        # Process tokens in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all fetch tasks
            future_to_token = {
                executor.submit(fetch_ohlc_for_token, token, interval): token[1] 
                for token in tokens
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_token):
                symbol = future_to_token[future]
                try:
                    result = future.result(timeout=300)  # 5 minute timeout per token
                    if result["success"]:
                        successful_fetches.append(result["data"])
                        if len(successful_fetches) % 50 == 0:
                            logger.info(f"Processed {len(successful_fetches)}/{len(tokens)} tokens successfully")
                    else:
                        failed_fetches.append({"symbol": symbol, "error": result["error"]})
                        logger.warning(f"Failed to fetch data for {symbol}: {result['error']}")
                except Exception as e:
                    failed_fetches.append({"symbol": symbol, "error": str(e)})
                    logger.error(f"Error processing {symbol}: {e}")
        
        # Batch insert all successful data
        if successful_fetches:
            logger.info(f"Starting batch insert of {len(successful_fetches)} successful fetches")
            batch_success = batch_insert_ohlc_data(successful_fetches, interval)
        else:
            batch_success = False
            logger.warning("No successful fetches to insert")
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        result = {
            "success": batch_success,
            "total_tokens": len(tokens),
            "successful_fetches": len(successful_fetches),
            "failed_fetches": len(failed_fetches),
            "processing_time_seconds": round(processing_time, 2),
            "failed_symbols": [f["symbol"] for f in failed_fetches[:10]]  # First 10 failures
        }
        
        if failed_fetches:
            logger.warning(f"Failed to fetch data for {len(failed_fetches)} tokens. First few: {result['failed_symbols']}")
        
        logger.info(f"Optimized OHLC collection completed in {processing_time:.2f} seconds")
        logger.info(f"Success rate: {len(successful_fetches)}/{len(tokens)} ({len(successful_fetches)/len(tokens)*100:.1f}%)")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in optimized OHLC collection: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_tokens": 0,
            "successful_fetches": 0,
            "failed_fetches": 0
        }

def get_ohlc_on_schedule_optimized():
    """
    Optimized version of the scheduled OHLC data collection task.
    This replaces the original get_ohlc_on_schedule function.
    """
    try:
        logger.info("Starting optimized scheduled OHLC data collection...")
        
        # Download CSV files first (keep this synchronous as it's fast)
        from services.get_token_data import download_nse_csv
        
        logger.info("Downloading NSE CSV files...")
        download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv", "500")
        download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv", "250")
        download_nse_csv("https://www.niftyindices.com/IndexConstituent/ind_niftyIPO_list.csv", "IPO")
        download_nse_csv("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv", "ALL")
        
        # Run optimized OHLC collection with higher worker count
        logger.info("Starting optimized daily OHLC collection...")
        daily_result = get_equity_ohlc_data_optimized("day", max_workers=8)
        
        if daily_result["success"]:
            logger.info(f"Daily OHLC collection successful: {daily_result['successful_fetches']}/{daily_result['total_tokens']} tokens")
        else:
            logger.error("Daily OHLC collection failed")
        
        # Load precomputed OHLC (this is now much faster since data is fresh)
        from services.get_screener import load_precomputed_ohlc
        load_precomputed_ohlc()
        
        # Run sequential VCP screener after data collection (lazy import to avoid circular dependencies)
        try:
            from services.get_screener import run_advanced_vcp_screener
            vcp_result = run_advanced_vcp_screener()  # Now uses memory-efficient sequential processing
        except ImportError as e:
            logger.warning(f"Could not import VCP screener: {e}. Skipping VCP screening.")
            vcp_result = False
        
        # Calculate risk scores
        from services.optimized_risk_calculator import calculate_daily_risk_scores_optimized
        calculate_daily_risk_scores_optimized()
        
        logger.info("Optimized OHLC data collection and processing completed")
        return daily_result
        
    except Exception as e:
        logger.error(f"Error in optimized scheduled OHLC collection: {e}")
        return {"success": False, "error": str(e)}

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_ohlc_collection_status() -> Dict:
    """
    Get status information about recent OHLC data collection.
    
    Returns:
        Dictionary with collection statistics
    """
    try:
        conn, cur = get_db_connection()
        
        # Get count of recent data
        query = """
            SELECT 
                interval,
                COUNT(DISTINCT symbol) as symbol_count,
                COUNT(*) as total_rows,
                MAX(date) as latest_date
            FROM ohlc 
            WHERE date >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY interval
            ORDER BY interval;
        """
        
        cur.execute(query)
        results = cur.fetchall()
        
        status = {
            "collection_status": {},
            "last_updated": datetime.datetime.now().isoformat()
        }
        
        for row in results:
            interval, symbol_count, total_rows, latest_date = row
            status["collection_status"][interval] = {
                "symbol_count": symbol_count,
                "total_rows": total_rows,
                "latest_date": latest_date.isoformat() if latest_date else None
            }
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting OHLC collection status: {e}")
        return {"error": str(e)}
    finally:
        if 'conn' in locals() and 'cur' in locals():
            close_db_connection() 