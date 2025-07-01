#!/usr/bin/env python3
"""
Optimized Risk Calculator Service
Uses parallel processing and batch operations to improve performance
"""

import logging
import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Dict, Optional, Tuple
import multiprocessing as mp
from functools import partial
import time

from db import get_trade_db_connection, release_trade_db_connection
from models.risk_scores import RiskScore

logger = logging.getLogger(__name__)

class OptimizedRiskCalculator:
    """
    Optimized Risk Calculator with parallel processing and batch operations.
    """
    
    def __init__(self):
        self.risk_weights = {
            'volatility': 0.30,
            'atr_risk': 0.20,
            'drawdown_risk': 0.10,
            'gap_risk': 0.25,
            'volume_consistency': 0.10,
            'trend_stability': 0.05
        }
        
        # Cache for frequently used calculations
        self._cache = {}
    
    def calculate_batch_risk_scores(self, stock_batch: List[Dict]) -> List[Dict]:
        """
        Calculate risk scores for a batch of stocks efficiently.
        
        Args:
            stock_batch: List of stock data dictionaries
            
        Returns:
            List of risk score results
        """
        batch_results = []
        
        for stock_data in stock_batch:
            try:
                risk_result = self._calculate_single_stock_risk(stock_data)
                if risk_result:
                    batch_results.append(risk_result)
            except Exception as e:
                logger.error(f"Error calculating risk for {stock_data.get('symbol', 'unknown')}: {e}")
                continue
        
        return batch_results
    
    def _calculate_single_stock_risk(self, stock_data: Dict) -> Optional[Dict]:
        """
        Calculate risk score for a single stock using pre-loaded data.
        
        Args:
            stock_data: Dictionary containing stock data and OHLC DataFrame
            
        Returns:
            Risk score result dictionary
        """
        try:
            symbol = stock_data['symbol']
            instrument_token = stock_data['instrument_token']
            df = stock_data['ohlc_data']
            
            if len(df) < 50:  # Need minimum data
                return self._default_risk_score(symbol, instrument_token)
            
            # Calculate risk components efficiently
            risk_components = self._calculate_all_risk_components(df)
            
            # Calculate weighted overall risk score
            overall_risk = sum(
                score * self.risk_weights[component] 
                for component, score in risk_components.items()
            )
            
            return {
                'symbol': symbol,
                'instrument_token': instrument_token,
                'overall_risk_score': round(overall_risk, 1),
                'risk_components': risk_components,
                'data_points': len(df),
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in single stock risk calculation: {e}")
            return self._default_risk_score(
                stock_data.get('symbol'), 
                stock_data.get('instrument_token')
            )
    
    def _calculate_all_risk_components(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate all risk components efficiently in one pass.
        
        Args:
            df: OHLC DataFrame
            
        Returns:
            Dictionary of risk component scores
        """
        # Calculate returns once
        df = df.copy()
        df['returns'] = df['close'].pct_change()
        df['high_low_range'] = (df['high'] - df['low']) / df['close']
        
        # Calculate all components
        volatility_score = self._calculate_volatility_score_optimized(df)
        atr_risk_score = self._calculate_atr_risk_score_optimized(df)
        drawdown_score = self._calculate_drawdown_risk_score_optimized(df)
        gap_risk_score = self._calculate_gap_risk_score_optimized(df)
        volume_score = self._calculate_volume_consistency_score_optimized(df)
        trend_score = self._calculate_trend_stability_score_optimized(df)
        
        return {
            'volatility': volatility_score,
            'atr_risk': atr_risk_score,
            'drawdown_risk': drawdown_score,
            'gap_risk': gap_risk_score,
            'volume_consistency': volume_score,
            'trend_stability': trend_score
        }
    
    def _calculate_volatility_score_optimized(self, df: pd.DataFrame) -> float:
        """Optimized volatility calculation."""
        try:
            daily_vol = df['returns'].std()
            annual_vol = daily_vol * np.sqrt(252)
            
            # Use vectorized approach for scoring
            if annual_vol <= 0.15: return 1
            elif annual_vol <= 0.20: return 2
            elif annual_vol <= 0.25: return 3
            elif annual_vol <= 0.30: return 4
            elif annual_vol <= 0.35: return 5
            elif annual_vol <= 0.40: return 6
            elif annual_vol <= 0.45: return 7
            elif annual_vol <= 0.50: return 8
            elif annual_vol <= 0.60: return 9
            else: return 10
        except:
            return 5
    
    def _calculate_atr_risk_score_optimized(self, df: pd.DataFrame) -> float:
        """Optimized ATR risk calculation."""
        try:
            if 'atr' in df.columns and not df['atr'].isna().all():
                avg_atr = df['atr'].tail(50).mean()
                avg_price = df['close'].tail(50).mean()
            else:
                # Calculate ATR if not available
                avg_atr = df['high_low_range'].tail(50).mean() * df['close'].tail(50).mean()
                avg_price = df['close'].tail(50).mean()
            
            atr_percentage = (avg_atr / avg_price) * 100
            
            if atr_percentage <= 1.0: return 1
            elif atr_percentage <= 1.5: return 2
            elif atr_percentage <= 2.0: return 3
            elif atr_percentage <= 2.5: return 4
            elif atr_percentage <= 3.0: return 5
            elif atr_percentage <= 4.0: return 6
            elif atr_percentage <= 5.0: return 7
            elif atr_percentage <= 6.0: return 8
            elif atr_percentage <= 8.0: return 9
            else: return 10
        except:
            return 5
    
    def _calculate_drawdown_risk_score_optimized(self, df: pd.DataFrame) -> float:
        """Optimized drawdown calculation."""
        try:
            # Calculate rolling maximum and drawdown in one pass
            rolling_max = df['close'].expanding().max()
            drawdown = (df['close'] - rolling_max) / rolling_max
            max_drawdown = abs(drawdown.min()) * 100
            
            if max_drawdown <= 10: return 1
            elif max_drawdown <= 15: return 2
            elif max_drawdown <= 20: return 3
            elif max_drawdown <= 25: return 4
            elif max_drawdown <= 30: return 5
            elif max_drawdown <= 40: return 6
            elif max_drawdown <= 50: return 7
            elif max_drawdown <= 60: return 8
            elif max_drawdown <= 75: return 9
            else: return 10
        except:
            return 5
    
    def _calculate_gap_risk_score_optimized(self, df: pd.DataFrame) -> float:
        """Optimized gap risk calculation."""
        try:
            # Calculate gaps efficiently
            prev_close = df['close'].shift(1)
            gap_up = ((df['open'] - prev_close) / prev_close * 100).clip(lower=0)
            gap_down = ((prev_close - df['open']) / prev_close * 100).clip(lower=0)
            
            # Count significant gaps
            significant_gaps_up = (gap_up > 3).sum()
            significant_gaps_down = (gap_down > 3).sum()
            
            total_gaps = significant_gaps_up + significant_gaps_down
            gap_frequency = total_gaps / len(df) * 100
            
            if gap_frequency <= 2: return 1
            elif gap_frequency <= 4: return 2
            elif gap_frequency <= 6: return 3
            elif gap_frequency <= 8: return 4
            elif gap_frequency <= 10: return 5
            elif gap_frequency <= 12: return 6
            elif gap_frequency <= 15: return 7
            elif gap_frequency <= 18: return 8
            elif gap_frequency <= 22: return 9
            else: return 10
        except:
            return 5
    
    def _calculate_volume_consistency_score_optimized(self, df: pd.DataFrame) -> float:
        """Optimized volume consistency calculation."""
        try:
            volume_cv = df['volume'].std() / df['volume'].mean()
            avg_volume = df['volume'].mean()
            volume_spikes = (df['volume'] > avg_volume * 2).sum()
            spike_frequency = volume_spikes / len(df)
            
            volume_risk = (volume_cv * 0.7) + (spike_frequency * 0.3)
            
            if volume_risk <= 0.5: return 1
            elif volume_risk <= 1.0: return 2
            elif volume_risk <= 1.5: return 3
            elif volume_risk <= 2.0: return 4
            elif volume_risk <= 2.5: return 5
            elif volume_risk <= 3.0: return 6
            elif volume_risk <= 3.5: return 7
            elif volume_risk <= 4.0: return 8
            elif volume_risk <= 5.0: return 9
            else: return 10
        except:
            return 5
    
    def _calculate_trend_stability_score_optimized(self, df: pd.DataFrame) -> float:
        """Optimized trend stability calculation."""
        try:
            # Calculate short and long term trends
            short_sma = df['close'].rolling(20).mean()
            long_sma = df['close'].rolling(50).mean()
            
            # Count trend direction changes
            trend_direction = (short_sma > long_sma).astype(int)
            trend_changes = (trend_direction.diff() != 0).sum()
            
            change_frequency = trend_changes / len(df) * 100
            
            if change_frequency <= 5: return 1
            elif change_frequency <= 8: return 2
            elif change_frequency <= 12: return 3
            elif change_frequency <= 16: return 4
            elif change_frequency <= 20: return 5
            elif change_frequency <= 25: return 6
            elif change_frequency <= 30: return 7
            elif change_frequency <= 35: return 8
            elif change_frequency <= 42: return 9
            else: return 10
        except:
            return 5
    
    def _default_risk_score(self, symbol=None, instrument_token=None):
        """Return default medium risk score when calculation fails."""
        return {
            'symbol': symbol,
            'instrument_token': instrument_token,
            'overall_risk_score': 5.0,
            'risk_components': {
                'volatility': 5,
                'atr_risk': 5,
                'drawdown_risk': 5,
                'gap_risk': 5,
                'volume_consistency': 5,
                'trend_stability': 5
            },
            'data_points': 0,
            'calculated_at': datetime.now().isoformat(),
            'error': 'Insufficient data or calculation error'
        }

def load_stock_data_batch(symbols_batch: List[Tuple[str, int]], lookback_days: int = 252) -> List[Dict]:
    """
    Load OHLC data for a batch of symbols efficiently.
    
    Args:
        symbols_batch: List of (symbol, instrument_token) tuples
        lookback_days: Number of days to look back
        
    Returns:
        List of stock data dictionaries with OHLC DataFrames
    """
    try:
        conn, cur = get_trade_db_connection()
        
        # Build batch query for multiple symbols
        placeholders = ','.join(['%s'] * len(symbols_batch))
        instrument_tokens = [token for _, token in symbols_batch]
        
        query = f"""
            SELECT 
                instrument_token,
                symbol,
                date, 
                open, 
                high, 
                low, 
                close, 
                volume, 
                atr
            FROM ohlc
            WHERE instrument_token IN ({placeholders})
            AND interval = 'day'
            AND date >= NOW() - INTERVAL '%s days'
            ORDER BY instrument_token, date ASC
        """
        
        cur.execute(query, instrument_tokens + [lookback_days])
        rows = cur.fetchall()
        
        if not rows:
            return []
        
        # Convert to DataFrame and group by symbol
        columns = ['instrument_token', 'symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'atr']
        df = pd.DataFrame(rows, columns=columns)
        
        # Convert numeric columns
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'atr']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
        df['date'] = pd.to_datetime(df['date'])
        
        # Group by symbol and create stock data dictionaries
        stock_data_list = []
        for instrument_token, group_df in df.groupby('instrument_token'):
            symbol = group_df['symbol'].iloc[0]
            stock_data = {
                'symbol': symbol,
                'instrument_token': instrument_token,
                'ohlc_data': group_df.dropna()
            }
            stock_data_list.append(stock_data)
        
        return stock_data_list
        
    except Exception as e:
        logger.error(f"Error loading stock data batch: {e}")
        return []
    finally:
        if 'conn' in locals() and 'cur' in locals():
            release_trade_db_connection(conn, cur)

def calculate_risk_scores_parallel(symbols_list: Optional[List[str]] = None, 
                                 limit: Optional[int] = None,
                                 max_workers: int = None,
                                 batch_size: int = 50) -> List[Dict]:
    """
    Calculate risk scores using parallel processing.
    
    Args:
        symbols_list: Optional list of symbols to calculate
        limit: Maximum number of symbols to process
        max_workers: Number of parallel workers
        batch_size: Number of symbols per batch
        
    Returns:
        List of risk score results
    """
    start_time = time.time()
    
    try:
        # Determine optimal number of workers
        if max_workers is None:
            max_workers = max(1, mp.cpu_count() - 1)
        
        # Get symbols to process
        conn, cur = get_trade_db_connection()
        
        if symbols_list:
            placeholders = ','.join(['%s'] * len(symbols_list))
            query = f"""
                SELECT DISTINCT symbol, instrument_token
                FROM ohlc
                WHERE symbol IN ({placeholders})
                AND interval = 'day'
                ORDER BY symbol
            """
            cur.execute(query, symbols_list)
        else:
            query = """
                SELECT DISTINCT symbol, instrument_token
                FROM ohlc
                WHERE interval = 'day'
                ORDER BY symbol
            """
            if limit:
                query += f" LIMIT {limit}"
            cur.execute(query)
        
        symbols = cur.fetchall()
        release_trade_db_connection(conn, cur)
        
        if not symbols:
            logger.warning("No symbols found for risk calculation")
            return []
        
        logger.info(f"Starting parallel risk calculation for {len(symbols)} symbols using {max_workers} workers")
        
        # Split symbols into batches
        symbol_batches = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]
        logger.info(f"Split symbols into {len(symbol_batches)} batches of ~{batch_size} symbols each")
        
        all_results = []
        calculator = OptimizedRiskCalculator()
        
        # Process batches in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit batch processing tasks
            future_to_batch = {}
            for i, batch in enumerate(symbol_batches):
                future = executor.submit(process_risk_batch, batch, calculator, i)
                future_to_batch[future] = i
            
            # Collect results as they complete
            for future in as_completed(future_to_batch):
                batch_id = future_to_batch[future]
                try:
                    batch_results = future.result(timeout=600)  # 10 minute timeout per batch
                    all_results.extend(batch_results)
                    logger.info(f"Completed risk batch {batch_id}: {len(batch_results)} results")
                except Exception as e:
                    logger.error(f"Risk batch {batch_id} failed: {e}")
                    continue
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        logger.info(f"Parallel risk calculation completed in {processing_time:.2f} seconds")
        logger.info(f"Processed {len(all_results)}/{len(symbols)} symbols successfully")
        
        return all_results
        
    except Exception as e:
        logger.error(f"Error in parallel risk calculation: {e}")
        return []

def process_risk_batch(symbols_batch: List[Tuple[str, int]], 
                      calculator: OptimizedRiskCalculator, 
                      batch_id: int) -> List[Dict]:
    """
    Process a batch of symbols for risk calculation.
    
    Args:
        symbols_batch: List of (symbol, instrument_token) tuples
        calculator: Risk calculator instance
        batch_id: Batch identifier for logging
        
    Returns:
        List of risk calculation results
    """
    try:
        logger.info(f"Risk batch {batch_id}: Loading data for {len(symbols_batch)} symbols")
        
        # Load OHLC data for the batch
        stock_data_list = load_stock_data_batch(symbols_batch)
        
        if not stock_data_list:
            logger.warning(f"Risk batch {batch_id}: No data loaded")
            return []
        
        # Calculate risk scores for the batch
        logger.info(f"Risk batch {batch_id}: Calculating risk scores for {len(stock_data_list)} stocks")
        batch_results = calculator.calculate_batch_risk_scores(stock_data_list)
        
        logger.info(f"Risk batch {batch_id}: Completed {len(batch_results)} risk calculations")
        return batch_results
        
    except Exception as e:
        logger.error(f"Error in risk batch {batch_id}: {e}")
        return []

def calculate_daily_risk_scores_optimized():
    """
    Optimized version of daily risk score calculation.
    This replaces the original calculate_daily_risk_scores function.
    """
    try:
        logger.info("Starting optimized daily risk scores calculation...")
        
        # Calculate risk scores in parallel
        risk_results = calculate_risk_scores_parallel(
            symbols_list=None, 
            limit=None, 
            max_workers=6,  # Use more workers for risk calculation
            batch_size=100  # Larger batch size for better efficiency
        )
        
        if risk_results:
            # Save to database in batches
            logger.info(f"Saving {len(risk_results)} risk scores to database...")
            
            conn, cur = get_trade_db_connection()
            try:
                RiskScore.bulk_save_risk_scores(cur, risk_results)
                conn.commit()
                logger.info(f"Optimized daily risk calculation completed: {len(risk_results)} stocks processed")
            finally:
                release_trade_db_connection(conn, cur)
        else:
            logger.warning("No risk scores calculated - check if OHLC data is available")
        
        return len(risk_results)
        
    except Exception as e:
        logger.error(f"Error in optimized daily risk calculation: {e}")
        return 0

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_risk_calculation_status() -> Dict:
    """
    Get status information about recent risk calculations.
    
    Returns:
        Dictionary with calculation statistics
    """
    try:
        conn, cur = get_trade_db_connection()
        
        # Get count of recent risk calculations
        query = """
            SELECT 
                COUNT(*) as total_calculations,
                AVG(overall_risk_score) as avg_risk_score,
                MIN(overall_risk_score) as min_risk_score,
                MAX(overall_risk_score) as max_risk_score,
                MAX(calculated_at) as latest_calculation
            FROM risk_scores
            WHERE calculated_at >= NOW() - INTERVAL '24 hours';
        """
        
        cur.execute(query)
        result = cur.fetchone()
        
        if result:
            total, avg_risk, min_risk, max_risk, latest = result
            status = {
                "total_calculations": total,
                "avg_risk_score": round(float(avg_risk), 2) if avg_risk else 0,
                "min_risk_score": float(min_risk) if min_risk else 0,
                "max_risk_score": float(max_risk) if max_risk else 0,
                "latest_calculation": latest.isoformat() if latest else None,
                "last_updated": datetime.now().isoformat()
            }
        else:
            status = {
                "total_calculations": 0,
                "avg_risk_score": 0,
                "min_risk_score": 0,
                "max_risk_score": 0,
                "latest_calculation": None,
                "last_updated": datetime.now().isoformat()
            }
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting risk calculation status: {e}")
        return {"error": str(e)}
    finally:
        if 'conn' in locals() and 'cur' in locals():
            release_trade_db_connection(conn, cur) 