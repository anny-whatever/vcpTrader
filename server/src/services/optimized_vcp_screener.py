#!/usr/bin/env python3
"""
Optimized VCP Real-Time Scanner using multiprocessing and batching
Designed to reduce thread load and improve performance
"""

import pandas as pd
import numpy as np
import multiprocessing as mp
from multiprocessing import Pool, Manager
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging
from datetime import datetime
from typing import Dict, List, Optional
import warnings
from functools import partial

from db import get_trade_db_connection, release_trade_db_connection
from models import AdvancedVcpResult
from .advanced_vcp_screener import (
    VCP_CONFIG, STAGE_FLAGS, REALTIME_FILTERS,
    calculate_technical_indicators, apply_realtime_filters,
    detect_realtime_vcp_breakout
)

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

# =============================================================================
# OPTIMIZED PROCESSING FUNCTIONS
# =============================================================================

def process_stock_batch(stock_batch: List[tuple], batch_id: int) -> List[Dict]:
    """
    Process a batch of stocks for VCP patterns in a separate process.
    
    Args:
        stock_batch: List of (symbol, stock_df) tuples
        batch_id: Batch identifier for logging
        
    Returns:
        List of VCP pattern results
    """
    batch_results = []
    batch_size = len(stock_batch)
    
    logger.info(f"Batch {batch_id}: Processing {batch_size} stocks")
    
    for i, (symbol, stock_df) in enumerate(stock_batch):
        try:
            # Sort by date and reset index for consistent processing
            stock_df = stock_df.sort_values('date').reset_index(drop=True)
            
            # Ensure required columns are present
            required_cols = ['open', 'high', 'low', 'close', 'volume', 'date', 'sma_50', 'sma_200']
            if not all(col in stock_df.columns for col in required_cols):
                continue

            # Calculate necessary indicators that might be missing
            stock_df = calculate_technical_indicators(stock_df)
            
            # Apply basic filters
            if not apply_realtime_filters(stock_df):
                continue
            
            # Run detection logic
            pattern = detect_realtime_vcp_breakout(stock_df, symbol)
            if pattern:
                batch_results.append(pattern)
                logger.info(f"Batch {batch_id}: VCP breakout found for {symbol}")
                
        except Exception as e:
            logger.error(f"Batch {batch_id}: Error processing {symbol}: {e}")
            continue
    
    logger.info(f"Batch {batch_id}: Completed processing, found {len(batch_results)} breakouts")
    return batch_results

def chunk_dataframe_by_symbol(df: pd.DataFrame, chunk_size: int = 50) -> List[List[tuple]]:
    """
    Split DataFrame into chunks by symbol for parallel processing.
    
    Args:
        df: Input OHLC DataFrame
        chunk_size: Number of symbols per chunk
        
    Returns:
        List of chunks, each containing (symbol, stock_df) tuples
    """
    chunks = []
    current_chunk = []
    
    for symbol, group_df in df.groupby('symbol'):
        current_chunk.append((symbol, group_df))
        
        if len(current_chunk) >= chunk_size:
            chunks.append(current_chunk)
            current_chunk = []
    
    # Add remaining symbols to final chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def optimize_dataframe_for_processing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Optimize DataFrame for faster processing by reducing memory usage
    and ensuring proper data types.
    """
    logger.info("Optimizing DataFrame for processing...")
    
    # Convert to most efficient data types
    float_cols = ['open', 'high', 'low', 'close', 'volume', 'sma_50', 'sma_100', 
                  'sma_200', 'atr', '52_week_high', '52_week_low']
    
    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce', downcast='float')
    
    # Convert date column to datetime if it's not already
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    # Remove unnecessary columns to reduce memory
    essential_cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 
                      'sma_50', 'sma_100', 'sma_200', 'atr', '52_week_high', '52_week_low']
    df = df[essential_cols].copy()
    
    logger.info(f"DataFrame optimized: {df.shape[0]} rows, {df.shape[1]} columns")
    return df

# =============================================================================
# MAIN OPTIMIZED SCANNING ENGINE
# =============================================================================

def run_optimized_vcp_scan(ohlc_df: pd.DataFrame, max_workers: int = None) -> bool:
    """
    Run optimized VCP scan using multiprocessing for better performance.
    
    Args:
        ohlc_df: Input OHLC DataFrame
        max_workers: Number of parallel processes (defaults to CPU count - 1)
        
    Returns:
        bool: Success status
    """
    if ohlc_df.empty:
        logger.warning("Optimized VCP screener called with empty OHLC data.")
        return False

    # Determine optimal number of workers
    if max_workers is None:
        max_workers = max(1, mp.cpu_count() - 1)  # Leave one CPU core for other tasks
    
    total_symbols = len(ohlc_df['symbol'].unique())
    logger.info(f"Starting optimized VCP scan on {total_symbols} stocks using {max_workers} processes")
    
    try:
        # Optimize DataFrame for processing
        ohlc_df = optimize_dataframe_for_processing(ohlc_df)
        
        # Calculate optimal chunk size based on number of workers and symbols
        chunk_size = max(10, total_symbols // (max_workers * 4))  # 4 batches per worker
        logger.info(f"Using chunk size of {chunk_size} symbols per batch")
        
        # Split data into chunks for parallel processing
        stock_chunks = chunk_dataframe_by_symbol(ohlc_df, chunk_size)
        logger.info(f"Split {total_symbols} symbols into {len(stock_chunks)} batches")
        
        all_breakouts = []
        
        # Process chunks in parallel using ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all batches for processing
            future_to_batch = {
                executor.submit(process_stock_batch, chunk, i): i 
                for i, chunk in enumerate(stock_chunks)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch_id = future_to_batch[future]
                try:
                    batch_results = future.result(timeout=300)  # 5 minute timeout per batch
                    all_breakouts.extend(batch_results)
                    logger.info(f"Completed batch {batch_id}: {len(batch_results)} breakouts found")
                except Exception as e:
                    logger.error(f"Batch {batch_id} failed: {e}")
                    continue
        
        logger.info(f"Optimized VCP scan completed. Found {len(all_breakouts)} total breakouts")
        
        # Save results to database
        return save_vcp_results_to_db(all_breakouts)
        
    except Exception as e:
        logger.error(f"Error in optimized VCP scan: {e}", exc_info=True)
        return False

def save_vcp_results_to_db(breakouts: List[Dict]) -> bool:
    """
    Save VCP results to database with error handling.
    
    Args:
        breakouts: List of VCP pattern results
        
    Returns:
        bool: Success status
    """
    if breakouts:
        conn, cur = None, None
        try:
            conn, cur = get_trade_db_connection()
            # Clear previous results before inserting new ones
            AdvancedVcpResult.delete_all(cur)
            AdvancedVcpResult.batch_save(cur, breakouts)
            
            # Send NOTIFY to trigger WebSocket subscription updates
            cur.execute("NOTIFY data_changed, 'advanced_vcp_results'")
            logger.info("Sent NOTIFY to update ticker subscriptions with advanced VCP screener tokens")
            
            conn.commit()
            logger.info(f"Successfully saved {len(breakouts)} advanced VCP results to database")
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to save advanced VCP results to database: {e}", exc_info=True)
            return False
        finally:
            if conn:
                release_trade_db_connection(conn, cur)
    else:
        # If no breakouts, still clear the old data
        logger.info("No breakouts found to save. Clearing old results from the database.")
        conn, cur = None, None
        try:
            conn, cur = get_trade_db_connection()
            AdvancedVcpResult.delete_all(cur)
            
            # Send NOTIFY even when clearing old results to update subscriptions
            cur.execute("NOTIFY data_changed, 'advanced_vcp_results'")
            logger.info("Sent NOTIFY to update ticker subscriptions after clearing advanced VCP results")
            
            conn.commit()
            logger.info("No new breakouts found. Cleared old advanced VCP results from database.")
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to clear old advanced VCP results: {e}", exc_info=True)
            return False
        finally:
            if conn:
                release_trade_db_connection(conn, cur)

# =============================================================================
# MEMORY-EFFICIENT DATA LOADING
# =============================================================================

def load_ohlc_data_efficiently(limit_symbols: int = None) -> pd.DataFrame:
    """
    Load OHLC data more efficiently with memory optimization.
    
    Args:
        limit_symbols: Optional limit on number of symbols to load
        
    Returns:
        Optimized DataFrame
    """
    try:
        conn, cur = get_trade_db_connection()
        
        # Build optimized query
        query = """
            SELECT 
                instrument_token,
                symbol,
                date,
                open,
                high,
                low,
                close,
                volume,
                sma_50,
                sma_200,
                atr
            FROM ohlc
            WHERE interval = 'day'
            AND date >= NOW() - INTERVAL '365 days'
            AND segment NOT IN ('IPO', 'ALL')
            ORDER BY symbol, date DESC
        """
        
        if limit_symbols:
            query += f" LIMIT {limit_symbols * 365}"  # Approximate limit
        
        logger.info("Loading OHLC data efficiently...")
        df = pd.read_sql(query, conn)
        
        if df.empty:
            logger.warning("No OHLC data loaded")
            return df
        
        # Optimize data types
        df = optimize_dataframe_for_processing(df)
        
        logger.info(f"Loaded {len(df)} rows for {len(df['symbol'].unique())} symbols efficiently")
        return df
        
    except Exception as e:
        logger.error(f"Error loading OHLC data efficiently: {e}", exc_info=True)
        return pd.DataFrame()
    finally:
        if 'conn' in locals() and 'cur' in locals():
            release_trade_db_connection(conn, cur)

# =============================================================================
# SCHEDULER INTEGRATION
# =============================================================================

def run_optimized_vcp_screener_scheduled():
    """
    Entry point for the optimized VCP screener from the scheduler.
    This replaces the original run_advanced_vcp_screener function.
    """
    try:
        logger.info("Starting optimized scheduled VCP screener...")
        
        # Load data efficiently
        df = load_ohlc_data_efficiently()
        if df.empty:
            logger.error("No OHLC data available for optimized VCP screening")
            return False
        
        # Run optimized scan
        success = run_optimized_vcp_scan(df)
        
        if success:
            logger.info("Optimized VCP screener completed successfully")
        else:
            logger.warning("Optimized VCP screener completed with issues")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in optimized scheduled VCP screener: {e}", exc_info=True)
        return False 