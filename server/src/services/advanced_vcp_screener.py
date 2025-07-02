#!/usr/bin/env python3
"""
VCP Real-Time Scanner for Live Market Detection
Identifies stocks breaking out from VCP patterns on the latest candle
Designed for end-of-day execution when candles are nearly complete
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta, time
from typing import Dict, List, Tuple, Optional
import warnings
import logging
import pytz
from db import get_trade_db_connection, release_trade_db_connection
from models import AdvancedVcpResult
from controllers import kite
warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

# Timezone configuration
TIMEZONE = pytz.timezone("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 45)

# =============================================================================
# CONFIGURATION - SAME AS BACKTEST FOR CONSISTENCY
# =============================================================================

VCP_CONFIG = {
    'min_pattern_duration': 40,           # Reduced from 60
    'max_pattern_duration': 150,          # Reduced from 150
    'min_contractions': 2,
    'max_contractions': 8,
    'volume_multiplier': 1.2,             # Reduced from 1.3
    'compression_threshold': 0.85,        # Relaxed from 0.8
    'prior_uptrend_min': 3.0,             # Reduced from 5.0
    'prior_uptrend_max': 150.0,           # Increased from 100.0
    'minimum_quality_score': 3,           # Reduced from 4
    'min_data_candles': 500,              # Minimum data requirement (we collect 2000 days)
}

STAGE_FLAGS = {
    'require_prior_uptrend': True,
    'require_volume_contraction': True,   # Disabled for more results
    'require_sma_position': True,
    'require_volume_surge': True,         # Disabled for more results  
    'require_volatility_compression': True,
    'quality_score_weight': True,
}

# Additional filters for real-time scanning
REALTIME_FILTERS = {
    'min_price': 2.0,           # Reduced from 5.0
    'max_price': 10000000.0,        # Increased from 500.0  
    'min_avg_volume': 500,    # Reduced from 100000
    'min_market_cap': None,     # Optional market cap filter
    'exclude_penny_stocks': False,  # Disabled for more results
}

# =============================================================================
# UTILITY FUNCTIONS (ADAPTED FROM BACKTEST)
# =============================================================================

def load_latest_stock_data(file_path: str, lookback_candles: int = 1000) -> pd.DataFrame:
    """Load latest stock data for real-time analysis"""
    try:
        df = pd.read_parquet(file_path)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # Take only the most recent candles
        df = df.tail(lookback_candles).reset_index(drop=True)
        
        if len(df) < VCP_CONFIG['min_data_candles']:
            return None
            
        # Calculate technical indicators
        df = calculate_technical_indicators(df)
        
        return df
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return None

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate technical indicators efficiently"""
    import pandas_ta as ta
    
    if df.empty or len(df) < 50:
        return df
        
    # Use rolling windows that don't exceed the length of the dataset
    length_20 = min(20, len(df))
    length_50 = min(50, len(df))
    length_100 = min(100, len(df))
    length_200 = min(200, len(df))
    length_252 = min(252, len(df))
    
    df["sma_20"] = ta.sma(df["close"], length=length_20)
    df["sma_50"] = ta.sma(df["close"], length=length_50)
    df["sma_100"] = ta.sma(df["close"], length=length_100)
    df["sma_200"] = ta.sma(df["close"], length=length_200)
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=length_50)
    
    df["52_week_high"] = df["high"].rolling(window=length_252, min_periods=1).max()
    df["52_week_low"] = df["low"].rolling(window=length_252, min_periods=1).min()
    
    df["away_from_high"] = ((df["52_week_high"] - df["close"]) / df["52_week_high"] * 100)
    df["away_from_low"] = ((df["close"] - df["52_week_low"]) / df["52_week_low"] * 100)
    
    # Replace NaN or infinite values with 0
    df = df.fillna(0)
    df.replace([float('inf'), float('-inf')], 0, inplace=True)
    
    return df

def apply_realtime_filters(df: pd.DataFrame) -> bool:
    """Apply basic filters before VCP analysis."""
    if df is None or len(df) < 50: # Need at least 50 days for some indicators
        return False
        
    latest_candle = df.iloc[-1]
    
    if latest_candle['close'] < REALTIME_FILTERS['min_price']:
        return False
    if latest_candle['close'] > REALTIME_FILTERS['max_price']:
        return False
        
    avg_volume = df['volume'].tail(20).mean()
    if avg_volume < REALTIME_FILTERS['min_avg_volume']:
        return False
        
    if REALTIME_FILTERS['exclude_penny_stocks'] and latest_candle['close'] < 5.0:
        return False
        
    return True

# =============================================================================
# LIVE DATA INTEGRATION FUNCTIONS
# =============================================================================

def check_market_hours() -> bool:
    """
    Check if the market is currently open.
    Returns True if market is open, False otherwise.
    """
    now = datetime.now(TIMEZONE).time()
    is_open = MARKET_OPEN <= now <= MARKET_CLOSE
    logger.info(f"Market hours check: Current time {now}, Market open: {is_open}")
    return is_open

def fetch_batch_live_data(instrument_tokens: List[int]) -> Dict[int, Dict]:
    """
    Fetch live quotes for a batch of instrument tokens efficiently.
    Uses Kite API's ability to fetch up to 500 instruments at once.
    
    Args:
        instrument_tokens: List of instrument tokens to fetch
        
    Returns:
        Dict mapping instrument_token to OHLCV data dict
    """
    if not instrument_tokens:
        return {}
    
    batch_size = min(len(instrument_tokens), 500)  # Kite API limit
    logger.debug(f"Fetching live data for batch of {len(instrument_tokens)} symbols")
    
    try:
        # Fetch quotes for the entire batch at once
        quote_data = kite.quote(instrument_tokens)
        
        live_data_batch = {}
        for token in instrument_tokens:
            token_str = str(token)
            if token_str in quote_data:
                quote = quote_data[token_str]
                ohlc = quote.get('ohlc', {})
                
                # Try multiple volume field names
                volume_today = quote.get('volume_today', 0) or quote.get('volume', 0) or quote.get('day_volume', 0)
                
                live_data = {
                    'open': float(ohlc.get('open', 0)),
                    'high': float(ohlc.get('high', 0)), 
                    'low': float(ohlc.get('low', 0)),
                    'close': float(quote.get('last_price', 0)),
                    'volume': float(volume_today)
                }
                
                # Log volume data for debugging
                if volume_today == 0:
                    logger.debug(f"Zero volume for {token}. Available fields: {list(quote.keys())}")
                
                # Validate live data (allow zero volume during market hours)
                if live_data['close'] > 0 and live_data['open'] > 0:
                    live_data_batch[token] = live_data
                else:
                    logger.debug(f"Invalid live data for {token}: {live_data}")
            else:
                logger.debug(f"No quote data for token {token}")
        
        logger.info(f"Successfully fetched live data for {len(live_data_batch)}/{len(instrument_tokens)} symbols")
        return live_data_batch
        
    except Exception as e:
        logger.error(f"Failed to fetch batch live data: {e}")
        return {}

def fetch_single_symbol_live_data(instrument_token: int) -> Optional[Dict]:
    """
    DEPRECATED: Use fetch_batch_live_data instead for efficiency.
    Kept for backward compatibility only.
    """
    batch_data = fetch_batch_live_data([instrument_token])
    return batch_data.get(instrument_token)

def create_same_day_candle(historical_df: pd.DataFrame, live_ohlcv: Dict, symbol: str) -> pd.DataFrame:
    """
    Create a proper same-day candle using actual OHLCV data and append to historical data.
    Recalculates technical indicators with the new data point.
    
    Args:
        historical_df: Historical OHLC DataFrame
        live_ohlcv: Live OHLCV data dictionary
        symbol: Stock symbol
        
    Returns:
        Updated DataFrame with same-day candle and recalculated indicators
    """
    if historical_df.empty:
        logger.warning(f"Empty historical data for {symbol}")
        return historical_df
        
    last_row = historical_df.iloc[-1]
    today = datetime.now(TIMEZONE).date()
    
    # Check if we already have today's data
    last_date = pd.to_datetime(last_row['date']).date()
    if last_date >= today:
        logger.debug(f"Already have today's data for {symbol}, last_date: {last_date}")
        return historical_df
    
    # Validate live OHLCV data
    if not all(key in live_ohlcv for key in ['open', 'high', 'low', 'close', 'volume']):
        logger.warning(f"Incomplete live OHLCV data for {symbol}: {live_ohlcv}")
        return historical_df
        
    if live_ohlcv['close'] <= 0 or live_ohlcv['open'] <= 0:
        logger.warning(f"Invalid price data for {symbol}: {live_ohlcv}")
        return historical_df
    
    # Handle zero volume by using historical average
    actual_volume = live_ohlcv['volume']
    if actual_volume == 0:
        # Use average of last 20 days volume as estimate
        recent_volume = historical_df['volume'].tail(20).mean()
        estimated_volume = recent_volume * 0.6  # Assume partial day trading
        logger.debug(f"Zero volume for {symbol}, using estimated volume: {estimated_volume:.0f}")
        volume_to_use = estimated_volume
    else:
        volume_to_use = actual_volume
    
    # Create same-day candle with actual OHLCV data
    same_day_candle = {
        "instrument_token": last_row["instrument_token"],
        "symbol": symbol,
        "interval": "day",
        "date": TIMEZONE.localize(datetime.combine(today, MARKET_CLOSE)),  # Market close time
        "open": live_ohlcv['open'],      # Actual opening price
        "high": live_ohlcv['high'],      # Actual high
        "low": live_ohlcv['low'],        # Actual low  
        "close": live_ohlcv['close'],    # Current price
        "volume": volume_to_use,         # Actual or estimated volume
        "segment": last_row["segment"],
        # Initialize indicators (will be recalculated)
        "sma_20": 0, "sma_50": 0, "sma_100": 0, "sma_200": 0,
        "atr": 0, "52_week_high": 0, "52_week_low": 0,
        "away_from_high": 0, "away_from_low": 0
    }
    
    volume_type = "estimated" if actual_volume == 0 else "actual"
    logger.info(f"Creating same-day candle for {symbol}: O:{live_ohlcv['open']:.2f} H:{live_ohlcv['high']:.2f} L:{live_ohlcv['low']:.2f} C:{live_ohlcv['close']:.2f} V:{volume_to_use:.0f}({volume_type})")
    
    # Append same-day candle to historical data
    updated_df = pd.concat([historical_df, pd.DataFrame([same_day_candle])], ignore_index=True)
    
    # Recalculate technical indicators with new data point
    updated_df = calculate_technical_indicators(updated_df)
    
    logger.debug(f"Updated {symbol} with same-day candle. New DataFrame shape: {updated_df.shape}")
    
    return updated_df

# =============================================================================
# VCP DETECTION FUNCTIONS (ADAPTED FOR REAL-TIME)
# =============================================================================

def check_prior_uptrend(df: pd.DataFrame, pattern_start: int, pattern_length: int) -> Dict:
    """Stage 1: Prior uptrend validation (same as backtest)"""
    if not STAGE_FLAGS['require_prior_uptrend']:
        return {'valid': True, 'gain': 0, 'details': 'Skipped'}
    
    uptrend_period = min(40, pattern_length // 2)
    uptrend_start = max(0, pattern_start - uptrend_period)
    
    if uptrend_start >= pattern_start - 10:
        return {'valid': False, 'gain': 0, 'details': 'Insufficient history'}
    
    start_price = df.iloc[uptrend_start]['close']
    end_price = df.iloc[pattern_start]['close']
    if start_price == 0: return {'valid': False, 'gain': 0, 'details': 'Start price is zero'}
    uptrend_gain = ((end_price - start_price) / start_price) * 100
    
    valid = VCP_CONFIG['prior_uptrend_min'] <= uptrend_gain <= VCP_CONFIG['prior_uptrend_max']
    
    return {
        'valid': valid,
        'gain': uptrend_gain,
        'period': uptrend_period,
        'details': f'Gain: {uptrend_gain:.2f}%'
    }

def find_contractions(df: pd.DataFrame, pattern_start: int, pattern_end: int) -> List[int]:
    """Stage 2: Contraction analysis (same as backtest)"""
    contractions = []
    
    subset_df = df.iloc[pattern_start:pattern_end].copy()
    if len(subset_df) < 9:
        return contractions
    
    highs = subset_df['high'].values
    lows = subset_df['low'].values
    
    for i in range(5, len(subset_df) - 3):
        current_range = highs[i] - lows[i]
        prev_range = highs[i-1] - lows[i-1]
        
        start_idx = max(0, i-3)
        max_prev_3_high = np.max(highs[start_idx:i]) if i > start_idx else 0
        
        tighter_range = current_range < prev_range * 0.95
        higher_low = lows[i] > lows[i-1]
        lower_high = highs[i] < max_prev_3_high
        
        if tighter_range and higher_low and lower_high:
            contractions.append(pattern_start + i)
    
    return contractions

def check_volume_contraction(df: pd.DataFrame, contractions: List[int], pattern_start: int) -> Dict:
    """Stage 3: Volume contraction validation (same as backtest)"""
    if not STAGE_FLAGS['require_volume_contraction'] or not contractions:
        return {'valid': True, 'ratio': 1.0, 'details': 'Skipped or no contractions'}
    
    contraction_start = contractions[0]
    pre_contraction_volume = df.iloc[pattern_start:contraction_start]['volume'].mean()
    contraction_volume = df.iloc[contraction_start:]['volume'].mean()
    
    if pre_contraction_volume == 0:
        return {'valid': False, 'ratio': 0, 'details': 'Invalid volume data'}
    
    ratio = contraction_volume / pre_contraction_volume
    valid = ratio < 1.0
    
    return {
        'valid': valid,
        'ratio': ratio,
        'details': f'Volume ratio: {ratio:.3f}'
    }

def check_sma_position(df: pd.DataFrame, breakout_idx: int) -> Dict:
    """Stage 4: Comprehensive SMA filter with alignment requirement"""
    if not STAGE_FLAGS['require_sma_position']:
        return {'valid': True, 'details': 'Skipped'}
    
    row = df.iloc[breakout_idx]
    breakout_close = row['close']
    sma_50 = row['sma_50']
    sma_100 = row['sma_100']
    sma_200 = row['sma_200']
    
    # Comprehensive SMA filter as specified
    sma_filter = (not pd.isna(sma_50) and not pd.isna(sma_100) and not pd.isna(sma_200) and
                  breakout_close > sma_50 and 
                  breakout_close > sma_100 and 
                  breakout_close > sma_200 and
                  sma_50 > sma_100 > sma_200)
    
    # Individual checks for reporting
    above_sma50 = breakout_close > sma_50 if not pd.isna(sma_50) else False
    above_sma100 = breakout_close > sma_100 if not pd.isna(sma_100) else False
    above_sma200 = breakout_close > sma_200 if not pd.isna(sma_200) else False
    sma_alignment = sma_50 > sma_100 > sma_200 if not pd.isna(sma_50) and not pd.isna(sma_100) and not pd.isna(sma_200) else False
    
    return {
        'valid': sma_filter,
        'above_sma50': above_sma50,
        'above_sma100': above_sma100,
        'above_sma200': above_sma200,
        'sma_alignment': sma_alignment,
        'price_vs_sma50_pct': ((breakout_close - sma_50) / sma_50) * 100 if not pd.isna(sma_50) and sma_50 != 0 else 0,
        'price_vs_sma100_pct': ((breakout_close - sma_100) / sma_100) * 100 if not pd.isna(sma_100) and sma_100 != 0 else 0,
        'price_vs_sma200_pct': ((breakout_close - sma_200) / sma_200) * 100 if not pd.isna(sma_200) and sma_200 != 0 else 0,
        'details': f'Above SMAs: 50({above_sma50}), 100({above_sma100}), 200({above_sma200}), Aligned({sma_alignment})'
    }

def validate_realtime_breakout(df: pd.DataFrame, pattern_start: int, breakout_idx: int) -> Dict:
    """Stage 5: Enhanced breakout validation with additional VCP conditions"""
    
    # Pattern high (excluding the breakout candle itself)
    pattern_data = df.iloc[pattern_start:breakout_idx]
    if len(pattern_data) == 0:
        return {'valid': False, 'details': 'No pattern data'}
        
    pattern_high = pattern_data['high'].max()
    
    breakout_candle = df.iloc[breakout_idx]
    breakout_high = breakout_candle['high']
    breakout_close = breakout_candle['close']
    breakout_open = breakout_candle['open']
    breakout_volume = breakout_candle['volume']
    
    # Get previous candle for comparison
    previous_close = df.iloc[breakout_idx - 1]['close'] if breakout_idx > 0 else breakout_close
    
    # Price breakout check - TODAY's high must exceed pattern high
    price_breakout = breakout_high > pattern_high * 1.005  # 0.5% buffer
    
    # Volume surge check for TODAY's candle
    if STAGE_FLAGS['require_volume_surge']:
        recent_volume = df.iloc[max(0, breakout_idx-10):breakout_idx]['volume'].mean()
        volume_ratio = breakout_volume / recent_volume if recent_volume > 0 else 0
        
        # Check if this is today's candle (same-day trading)
        breakout_date = pd.to_datetime(breakout_candle['date']).date()
        today = datetime.now(TIMEZONE).date()
        is_today_candle = breakout_date >= today
        
        if is_today_candle:
            # Relaxed volume requirement for live/same-day candles
            # Since volume accumulates during the day, use a lower threshold
            volume_surge = breakout_volume > recent_volume * 0.3  # 30% of historical average
            logger.debug(f"Live candle volume check for {df.iloc[0]['symbol'] if 'symbol' in df.columns else 'symbol'}: {breakout_volume:.0f} vs {recent_volume * 0.3:.0f} (30% threshold)")
        else:
            # Standard volume requirement for historical candles
            volume_surge = breakout_volume > recent_volume * VCP_CONFIG['volume_multiplier']
    else:
        volume_surge = True
        volume_ratio = 1.0
    
    # Enhanced breakout candle quality checks
    green_candle = breakout_close >= breakout_open  # Green candle (close >= open)
    valid_volume = breakout_volume > 0
    
    # Additional real-time checks  
    strong_close = breakout_candle['close'] > pattern_high * 0.995  # More flexible close requirement
    good_range = (breakout_candle['high'] - breakout_candle['low']) / breakout_candle['close'] < 0.12  # More flexible range
    
    # Relaxed breakout conditions (removed higher_close requirement)
    valid = (price_breakout and volume_surge and green_candle and valid_volume)
    
    return {
        'valid': valid,
        'price_breakout': price_breakout,
        'volume_surge': volume_surge,
        'green_candle': green_candle,
        'valid_volume': valid_volume,
        'strong_close': strong_close,
        'good_range': good_range,
        'pattern_high': pattern_high,
        'breakout_high': breakout_high,
        'breakout_close': breakout_close,
        'previous_close': previous_close,
        'volume_ratio': volume_ratio,
        'breakout_strength': ((breakout_high - pattern_high) / pattern_high) * 100,
        'close_strength': ((breakout_candle['close'] - pattern_high) / pattern_high) * 100,
        'details': f'Price: {price_breakout}, Volume: {volume_surge}, Green: {green_candle}, Strong Close: {strong_close}'
    }

def check_volatility_compression(df: pd.DataFrame, pattern_start: int, pattern_end: int) -> Dict:
    """Stage 6: Volatility compression analysis (same as backtest)"""
    if not STAGE_FLAGS['require_volatility_compression']:
        return {'valid': True, 'ratio': 0.5, 'details': 'Skipped'}
    
    pattern_data = df.iloc[pattern_start:pattern_end]
    closes = pattern_data['close'].values
    
    if len(closes) < 9:
        return {'valid': False, 'ratio': 1.0, 'details': 'Pattern too short'}
    
    third_len = len(closes) // 3
    early_closes = closes[:third_len]
    late_closes = closes[-third_len:]
    
    early_volatility = np.std(early_closes)
    late_volatility = np.std(late_closes)
    
    if early_volatility == 0:
        return {'valid': False, 'ratio': 1.0, 'details': 'No early volatility'}
    
    compression_ratio = late_volatility / early_volatility
    valid = compression_ratio <= VCP_CONFIG['compression_threshold']
    
    return {
        'valid': valid,
        'ratio': compression_ratio,
        'early_volatility': early_volatility,
        'late_volatility': late_volatility,
        'details': f'Compression ratio: {compression_ratio:.3f}'
    }

def calculate_quality_score(pattern_duration: int, num_contractions: int, 
                          compression_ratio: float, volume_ratio: float) -> Dict:
    """Stage 7: Quality scoring system (same as backtest)"""
    score = 0
    
    # Duration scoring (0-2 points)
    if 30 <= pattern_duration <= 80:
        duration_score = 2
    elif 20 <= pattern_duration <= 100:
        duration_score = 1
    else:
        duration_score = 0
    score += duration_score
    
    # Contractions scoring (0-2 points)
    if num_contractions >= 3:
        contraction_score = 2
    elif num_contractions >= 2:
        contraction_score = 1
    else:
        contraction_score = 0
    score += contraction_score
    
    # Compression scoring (0-2 points)
    if compression_ratio < 0.5:
        compression_score = 2
    elif compression_ratio < 0.7:
        compression_score = 1
    else:
        compression_score = 0
    score += compression_score
    
    # Volume scoring (0-2 points)
    if volume_ratio > 2.0:
        volume_score = 2
    elif volume_ratio > 1.5:
        volume_score = 1
    else:
        volume_score = 0
    score += volume_score
    
    return {
        'total_score': score,
        'duration_score': duration_score,
        'contraction_score': contraction_score,
        'compression_score': compression_score,
        'volume_score': volume_score,
        'is_acceptable': score >= VCP_CONFIG['minimum_quality_score']
    }

# =============================================================================
# REAL-TIME VCP DETECTION ENGINE
# =============================================================================

def detect_realtime_vcp_breakout(df: pd.DataFrame, symbol: str) -> Optional[Dict]:
    """
    Detect if recent candles show a VCP breakout (more flexible for real-time)
    Returns pattern data if valid breakout found, None otherwise
    """
    if len(df) < VCP_CONFIG['min_data_candles']:
        return None
    
    # EARLY SMA FILTER: Check SMA positioning on latest candle first
    # This prevents expensive pattern analysis if SMA criteria isn't met
    latest_candle = df.iloc[-1]
    latest_close = latest_candle['close']
    sma_50 = latest_candle['sma_50']
    sma_100 = latest_candle['sma_100'] 
    sma_200 = latest_candle['sma_200']
    
    # Apply comprehensive SMA filter early
    early_sma_filter = (not pd.isna(sma_50) and not pd.isna(sma_100) and not pd.isna(sma_200) and
                       latest_close > sma_50 and 
                       latest_close > sma_100 and 
                       latest_close > sma_200 and
                       sma_50 > sma_100 > sma_200)
    
    if not early_sma_filter:
        return None  # Skip this stock entirely if SMA criteria not met
    
    # Check last 3 candles for breakouts, prioritizing today's candle
    today = datetime.now(TIMEZONE).date()
    
    for lookback in range(0, min(3, len(df))):
        breakout_idx = len(df) - 1 - lookback
        
        # Check if this is today's candle
        candle_date = pd.to_datetime(df.iloc[breakout_idx]['date']).date()
        is_today_candle = candle_date >= today
        
        # Try different pattern durations ending at the breakout candle
        for pattern_duration in range(VCP_CONFIG['min_pattern_duration'], 
                                    min(VCP_CONFIG['max_pattern_duration'], breakout_idx - 50) + 1, 10):
            
            pattern_start = breakout_idx - pattern_duration
            pattern_end = breakout_idx  # Pattern ends at the breakout candle (exclusive)
            
            if pattern_start < 50:  # Need enough history for prior uptrend
                continue
            
            # Stage 1: Prior uptrend check
            uptrend_result = check_prior_uptrend(df, pattern_start, pattern_duration)
            if not uptrend_result['valid']:
                continue
            
            # Stage 2: Find contractions
            contractions = find_contractions(df, pattern_start, pattern_end)
            required_contractions = max(VCP_CONFIG['min_contractions'], 
                                      min(VCP_CONFIG['max_contractions'], pattern_duration // 20))
            
            if len(contractions) < required_contractions:
                continue
            
            # Stage 3: Volume contraction
            volume_result = check_volume_contraction(df, contractions, pattern_start)
            if not volume_result['valid']:
                continue
            
            # Stage 4: SMA position (already validated at start, but get detailed metrics)
            sma_result = check_sma_position(df, breakout_idx)
            # Note: sma_result['valid'] should always be True here due to early filter
            
            # Stage 5: REAL-TIME breakout validation (checks the candle at breakout_idx)
            breakout_result = validate_realtime_breakout(df, pattern_start, breakout_idx)
            if not breakout_result['valid']:
                continue
            
            # Stage 6: Volatility compression
            compression_result = check_volatility_compression(df, pattern_start, pattern_end)
            if not compression_result['valid']:
                continue
            
            # Stage 7: Quality scoring
            quality_result = calculate_quality_score(
                pattern_duration, len(contractions), 
                compression_result['ratio'], breakout_result['volume_ratio']
            )
            
            if not quality_result['is_acceptable']:
                continue
            
            # Valid VCP breakout found - collect metrics
            result = collect_realtime_metrics(
                df, symbol, pattern_start, pattern_end, breakout_idx,
                uptrend_result, contractions, volume_result, sma_result,
                breakout_result, compression_result, quality_result
            )
            
            # If this is today's breakout, prioritize it and return immediately
            if is_today_candle:
                logger.info(f"🔥 TODAY'S VCP BREAKOUT found for {symbol} - prioritizing over historical patterns")
                return result
            
            # Store historical breakout but continue checking for today's breakout
            historical_result = result
    
    # If no today's breakout found, return the best historical breakout if any
    if 'historical_result' in locals():
        logger.info(f"📅 No today's breakout for {symbol}, using historical VCP breakout")
        return historical_result
    
    return None

def collect_realtime_metrics(df: pd.DataFrame, symbol: str, pattern_start: int, 
                           pattern_end: int, breakout_idx: int, uptrend_result: Dict,
                           contractions: List[int], volume_result: Dict, sma_result: Dict,
                           breakout_result: Dict, compression_result: Dict, 
                           quality_result: Dict) -> Dict:
    """Collect comprehensive pattern metrics for real-time analysis"""
    
    breakout_candle = df.iloc[breakout_idx]
    pattern_data = df.iloc[pattern_start:pattern_end]
    
    # Calculate potential exit levels
    atr_50 = breakout_candle['atr']
    entry_price = breakout_candle['close']
    
    # Stop loss calculation (3x ATR with bounds)
    if not pd.isna(atr_50) and atr_50 > 0:
        atr_stop = entry_price - (3.0 * atr_50)
        stop_pct = abs(atr_stop - entry_price) / entry_price * 100
        
        if stop_pct <= 6.5:
            suggested_stop = entry_price * 0.925  # 7.5% stop
        elif 7.0 <= stop_pct <= 10.0:
            suggested_stop = atr_stop
        else:
            suggested_stop = entry_price * 0.90   # 10% max stop
    else:
        suggested_stop = entry_price * 0.92  # 8% default stop
    
    # Take profit calculation (6x ATR with bounds)
    if not pd.isna(atr_50) and atr_50 > 0:
        atr_target = entry_price + (6.0 * atr_50)
        target_pct = abs(atr_target - entry_price) / entry_price * 100
        
        if target_pct <= 15.0:
            suggested_target = entry_price * 1.15  # 15% minimum
        elif 15.0 <= target_pct <= 30.0:
            suggested_target = atr_target
        else:
            suggested_target = entry_price * 1.30  # 30% max target
    else:
        suggested_target = entry_price * 1.20  # 20% default target
    
    # Calculate detailed contraction information
    contraction_details = []
    for i, contraction_idx in enumerate(contractions):
        contraction_date = df.iloc[contraction_idx]['date']
        
        # Calculate contraction length (days until next contraction or pattern end)
        if i < len(contractions) - 1:
            contraction_length = contractions[i + 1] - contraction_idx
        else:
            contraction_length = pattern_end - contraction_idx
            
        # Contraction price and volume data
        contraction_data = df.iloc[contraction_idx]
        
        contraction_details.append({
            'contraction_number': i + 1,
            'date': contraction_date,
            'index_in_pattern': contraction_idx - pattern_start,
            'length_days': contraction_length,
            'price': contraction_data['close'],
            'high': contraction_data['high'],
            'low': contraction_data['low'],
            'volume': contraction_data['volume'],
            'range_pct': ((contraction_data['high'] - contraction_data['low']) / contraction_data['close']) * 100
        })
    
    # Calculate weekly price analysis within pattern
    pattern_weeks = []
    for week_start in range(pattern_start, pattern_end, 5):  # 5-day intervals
        week_end = min(week_start + 5, pattern_end)
        week_data = df.iloc[week_start:week_end]
        if len(week_data) > 0:
            pattern_weeks.append({
                'week_start_date': week_data.iloc[0]['date'],
                'week_end_date': week_data.iloc[-1]['date'],
                'week_high': week_data['high'].max(),
                'week_low': week_data['low'].min(),
                'week_close': week_data.iloc[-1]['close'],
                'week_volume': week_data['volume'].sum(),
                'week_avg_volume': week_data['volume'].mean()
            })
    
    # Prior uptrend detailed analysis
    uptrend_start_idx = max(0, pattern_start - uptrend_result['period'])
    uptrend_data = df.iloc[uptrend_start_idx:pattern_start]
    
    # Calculate pattern pivot points
    pattern_pivot_high_idx = pattern_data['high'].idxmax()
    pattern_pivot_low_idx = pattern_data['low'].idxmin()
    
    # Volume analysis during pattern
    pattern_avg_volume = pattern_data['volume'].mean()
    pattern_max_volume = pattern_data['volume'].max()
    pattern_min_volume = pattern_data['volume'].min()
    
    # Calculate current percentage change if possible
    current_change_pct = 0.0
    try:
        # Try to calculate percentage change from available data
        if not pd.isna(atr_50) and len(df) >= 2:
            # Get previous day's close price
            prev_close = df.iloc[breakout_idx - 1]['close'] if breakout_idx > 0 else None
            current_price = entry_price
            
            if prev_close and prev_close != 0:
                current_change_pct = ((current_price - prev_close) / prev_close) * 100
        
        # Alternative: use pattern start as reference if previous day not available
        elif pattern_start < breakout_idx:
            pattern_start_price = df.iloc[pattern_start]['close']
            if pattern_start_price and pattern_start_price != 0:
                current_change_pct = ((entry_price - pattern_start_price) / pattern_start_price) * 100
    except Exception as e:
        logger.warning(f"Could not calculate percentage change for {symbol}: {e}")
        current_change_pct = 0.0

    # Compile comprehensive metrics
    return {
        # ===== BASIC IDENTIFICATION =====
        'symbol': symbol,
        'scan_date': breakout_candle['date'],
        'scan_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'quality_score': quality_result['total_score'],
        'change': current_change_pct,  # Add percentage change field
        
        # ===== PATTERN STRUCTURE DETAILS =====
        'pattern_start_date': df.iloc[pattern_start]['date'],
        'pattern_end_date': df.iloc[pattern_end - 1]['date'] if pattern_end > pattern_start else df.iloc[pattern_start]['date'],
        'pattern_duration_days': pattern_end - pattern_start,
        'pattern_duration_weeks': round((pattern_end - pattern_start) / 5, 1),
        'pattern_start_price': df.iloc[pattern_start]['close'],
        'pattern_high': breakout_result['pattern_high'],
        'pattern_low': pattern_data['low'].min(),
        'pattern_high_date': df.iloc[pattern_pivot_high_idx]['date'],
        'pattern_low_date': df.iloc[pattern_pivot_low_idx]['date'],
        'pattern_range_pct': ((breakout_result['pattern_high'] - pattern_data['low'].min()) / pattern_data['low'].min()) * 100,
        
        # ===== CONTRACTION ANALYSIS =====
        'num_contractions': len(contractions),
        'contraction_details': contraction_details,
        'avg_contraction_length': sum([c['length_days'] for c in contraction_details]) / len(contraction_details) if contraction_details else 0,
        'first_contraction_date': contraction_details[0]['date'] if contraction_details else None,
        'last_contraction_date': contraction_details[-1]['date'] if contraction_details else None,
        'days_since_last_contraction': (breakout_candle['date'] - contraction_details[-1]['date']).days if contraction_details else 0,
        
        # ===== PRIOR UPTREND DETAILS =====
        'prior_uptrend_start_date': df.iloc[uptrend_start_idx]['date'],
        'prior_uptrend_start_price': df.iloc[uptrend_start_idx]['close'],
        'prior_uptrend_end_price': df.iloc[pattern_start]['close'],
        'prior_uptrend_duration_days': uptrend_result['period'],
        'prior_uptrend_gain_pct': uptrend_result['gain'],
        'prior_uptrend_high': uptrend_data['high'].max() if len(uptrend_data) > 0 else np.nan,
        'prior_uptrend_low': uptrend_data['low'].min() if len(uptrend_data) > 0 else np.nan,
        
        # ===== BREAKOUT CANDLE DETAILS =====
        'breakout_date': breakout_candle['date'],
        'breakout_open': breakout_candle['open'],
        'breakout_high': breakout_candle['high'],
        'breakout_low': breakout_candle['low'],
        'breakout_close': breakout_candle['close'],
        'breakout_volume': breakout_candle['volume'],
        'breakout_range_pct': ((breakout_candle['high'] - breakout_candle['low']) / breakout_candle['close']) * 100,
        'gap_up_from_prev_close': ((breakout_candle['open'] - df.iloc[breakout_idx-1]['close']) / df.iloc[breakout_idx-1]['close']) * 100,
        'breakout_strength_vs_pattern_high': breakout_result['breakout_strength'],
        'close_strength_vs_pattern_high': breakout_result['close_strength'],
        'breakout_body_pct': ((breakout_candle['close'] - breakout_candle['open']) / breakout_candle['close']) * 100,
        
        # ===== VOLUME ANALYSIS =====
        'volume_surge_ratio': breakout_result['volume_ratio'],
        'avg_volume_10d': df.iloc[max(0, breakout_idx-10):breakout_idx]['volume'].mean(),
        'avg_volume_20d': df.iloc[max(0, breakout_idx-20):breakout_idx]['volume'].mean(),
        'pattern_avg_volume': pattern_avg_volume,
        'pattern_max_volume': pattern_max_volume,
        'pattern_min_volume': pattern_min_volume,
        'breakout_vs_pattern_avg_volume': breakout_candle['volume'] / pattern_avg_volume if pattern_avg_volume > 0 else 0,
        'volume_trend_in_pattern': 'increasing' if pattern_data['volume'].iloc[-5:].mean() > pattern_data['volume'].iloc[:5].mean() else 'decreasing',
        
        # ===== TECHNICAL INDICATORS =====
        'current_price': entry_price,
        'sma_20': breakout_candle['sma_20'],
        'sma_50': breakout_candle['sma_50'],
        'sma_100': breakout_candle['sma_100'],
        'sma_200': breakout_candle['sma_200'],
        'price_vs_sma20_pct': ((entry_price - breakout_candle['sma_20']) / breakout_candle['sma_20']) * 100 if not pd.isna(breakout_candle['sma_20']) else np.nan,
        'price_vs_sma50_pct': sma_result.get('price_vs_sma50_pct', np.nan),
        'price_vs_sma100_pct': sma_result.get('price_vs_sma100_pct', np.nan),
        'price_vs_sma200_pct': ((entry_price - breakout_candle['sma_200']) / breakout_candle['sma_200']) * 100 if not pd.isna(breakout_candle['sma_200']) else np.nan,
        'atr_50': atr_50,
        'atr_vs_price_pct': (atr_50 / entry_price) * 100 if not pd.isna(atr_50) else np.nan,
        
        # ===== QUALITY SCORE BREAKDOWN =====
        'duration_score': quality_result['duration_score'],
        'contraction_score': quality_result['contraction_score'],
        'compression_score': quality_result['compression_score'],
        'volume_score': quality_result['volume_score'],
        'compression_ratio': compression_result['ratio'],
        
        # ===== ENTRY AND EXIT LEVELS =====
        'entry_price': entry_price,
        'suggested_stop_loss': suggested_stop,
        'suggested_take_profit': suggested_target,
        'stop_loss_pct': abs(suggested_stop - entry_price) / entry_price * 100,
        'take_profit_pct': abs(suggested_target - entry_price) / entry_price * 100,
        'risk_reward_ratio': abs(suggested_target - entry_price) / abs(entry_price - suggested_stop),
        'max_risk_amount': entry_price - suggested_stop,
        'max_reward_amount': suggested_target - entry_price,
        
        # ===== PATTERN VALIDATION FLAGS =====
        'green_breakout_candle': breakout_result['green_candle'],
        'strong_close': breakout_result['strong_close'],
        'good_range': breakout_result['good_range'],
        'price_breakout': breakout_result['price_breakout'],
        'volume_surge': breakout_result['volume_surge'],
        'above_sma50': sma_result.get('above_sma50', False),
        'above_sma100': sma_result.get('above_sma100', False),
        
        # ===== MARKET CONTEXT =====
        'days_since_pattern_start': (breakout_candle['date'] - df.iloc[pattern_start]['date']).days,
        'weekday_of_breakout': breakout_candle['date'].strftime('%A'),
        'month_of_breakout': breakout_candle['date'].strftime('%B %Y'),
        'pattern_weekly_breakdown': pattern_weeks,
        
        # ===== ADDITIONAL INSIGHTS =====
        'pattern_tightness_score': round(10 - (compression_result['ratio'] * 10), 1),
        'uptrend_strength': 'strong' if uptrend_result['gain'] > 20 else 'moderate' if uptrend_result['gain'] > 10 else 'weak',
        'volatility_compression_quality': 'excellent' if compression_result['ratio'] < 0.5 else 'good' if compression_result['ratio'] < 0.7 else 'acceptable',
        'overall_pattern_grade': 'A' if quality_result['total_score'] >= 7 else 'B' if quality_result['total_score'] >= 5 else 'C' if quality_result['total_score'] >= 3 else 'D',
        
        # ===== LIVE DATA INTEGRATION FLAGS =====
        'used_live_data': pd.to_datetime(breakout_candle['date']).date() >= datetime.now(TIMEZONE).date(),
        'is_same_day_breakout': pd.to_datetime(breakout_candle['date']).date() >= datetime.now(TIMEZONE).date(),
    }

# =============================================================================
# MAIN SCANNING ENGINE
# =============================================================================

def run_advanced_vcp_scan_sequential() -> bool:
    """
    Sequential VCP scan that processes one stock at a time for memory efficiency.
    Now includes live data integration during market hours.
    This eliminates deadlocks and memory issues by:
    1. Getting just the symbols list first
    2. Checking market hours once
    3. Processing each symbol individually with its own DB connection
    4. Fetching live data for each symbol during market hours
    5. Creating same-day candles with actual OHLCV data
    6. Saving results incrementally
    """
    from models import SaveOHLC
    
    logger.info("Starting sequential advanced VCP scan with live data integration...")
    
    # Step 1: Check market hours once at the beginning
    is_market_open = check_market_hours()
    if is_market_open:
        logger.info("🟢 Market is OPEN - Will fetch live data for each symbol during processing")
    else:
        logger.info("🔴 Market is CLOSED - Using historical data only")
    
    # Step 2: Get list of symbols to process
    conn, cur = None, None
    try:
        conn, cur = get_trade_db_connection()
        symbols_list = SaveOHLC.fetch_symbols_for_screening(cur)
        
        if not symbols_list:
            logger.warning("No symbols found for VCP screening")
            return False
            
        logger.info(f"Found {len(symbols_list)} symbols for processing")
            
    except Exception as e:
        logger.error(f"Error fetching symbols for screening: {e}", exc_info=True)
        return False
    finally:
        if conn:
            release_trade_db_connection(conn, cur)
    
    # Step 3: Clear old results before starting
    try:
        conn, cur = get_trade_db_connection()
        AdvancedVcpResult.delete_all(cur)
        conn.commit()
        logger.info("Cleared old VCP results from database")
    except Exception as e:
        logger.error(f"Error clearing old VCP results: {e}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            release_trade_db_connection(conn, cur)
    
    # Step 4: Process symbols in batches with efficient live data integration
    breakouts = []
    total_symbols = len(symbols_list)
    processed_count = 0
    error_count = 0
    live_data_fetched_count = 0
    same_day_candles_created = 0
    batch_size = 50
    
    logger.info(f"Processing {total_symbols} symbols in batches of {batch_size}...")
    
    # Process symbols in batches
    for batch_start in range(0, total_symbols, batch_size):
        batch_end = min(batch_start + batch_size, total_symbols)
        batch_symbols = symbols_list[batch_start:batch_end]
        
        logger.info(f"Processing batch {batch_start//batch_size + 1}: symbols {batch_start+1}-{batch_end}")
        
        # Fetch live data for entire batch if market is open
        batch_live_data = {}
        if is_market_open:
            try:
                batch_tokens = [instrument_token for _, instrument_token in batch_symbols]
                batch_live_data = fetch_batch_live_data(batch_tokens)
                live_data_fetched_count += len(batch_live_data)
                logger.debug(f"Fetched live data for {len(batch_live_data)}/{len(batch_tokens)} symbols in batch")
            except Exception as e:
                logger.warning(f"Failed to fetch batch live data: {e}")
        
        # Process each symbol in the batch
        for symbol, instrument_token in batch_symbols:
            processed_count += 1
            
            try:
                # Get fresh DB connection for this symbol
                conn, cur = None, None
                try:
                    conn, cur = get_trade_db_connection()
                    
                    # Fetch OHLC data for just this symbol
                    stock_df = SaveOHLC.fetch_ohlc_for_single_symbol(cur, symbol)
                    
                    if stock_df.empty:
                        continue
                    
                    # Ensure required columns are present
                    required_cols = ['open', 'high', 'low', 'close', 'volume', 'date', 'sma_50', 'sma_100', 'sma_200']
                    if not all(col in stock_df.columns for col in required_cols):
                        logger.debug(f"Skipping {symbol}: missing required columns")
                        continue

                    # Calculate necessary indicators that might be missing
                    stock_df = calculate_technical_indicators(stock_df)
                    
                    # LIVE DATA INTEGRATION: Use pre-fetched batch live data during market hours
                    if is_market_open and instrument_token in batch_live_data:
                        try:
                            live_ohlcv = batch_live_data[instrument_token]
                            
                            # Create same-day candle with actual OHLCV data and recalculate indicators
                            original_shape = stock_df.shape
                            stock_df = create_same_day_candle(stock_df, live_ohlcv, symbol)
                            
                            # Check if same-day candle was actually added
                            if stock_df.shape[0] > original_shape[0]:
                                same_day_candles_created += 1
                                logger.debug(f"✅ Added same-day candle for {symbol}")
                            else:
                                logger.debug(f"ℹ️ No same-day candle needed for {symbol} (already current)")
                                
                        except Exception as live_error:
                            logger.warning(f"Failed to process live data for {symbol}: {live_error}")
                            # Continue with historical data only
                    elif is_market_open:
                        logger.debug(f"⚠️ No live data available for {symbol}")
                    else:
                        logger.debug(f"Market closed - using historical data only for {symbol}")
                    
                    # Apply basic filters
                    if not apply_realtime_filters(stock_df):
                        continue
                    
                    # Run VCP detection logic on the updated data (with same-day candle if market is open)
                    pattern = detect_realtime_vcp_breakout(stock_df, symbol)
                    if pattern:
                        # Add additional metadata about live data usage
                        pattern['used_live_data'] = is_market_open and instrument_token in batch_live_data
                        pattern['same_day_candle_used'] = pattern['used_live_data']
                        pattern['instrument_token'] = instrument_token
                        
                        logger.info(f"✅ VCP BREAKOUT FOUND: {symbol} (Score: {pattern['quality_score']}, Live Data: {pattern['used_live_data']})")
                        breakouts.append(pattern)
                        
                except Exception as symbol_error:
                    error_count += 1
                    logger.error(f"Error processing symbol {symbol}: {symbol_error}", exc_info=True)
                    continue
                finally:
                    if conn:
                        release_trade_db_connection(conn, cur)
                        
            except Exception as e:
                error_count += 1
                logger.error(f"Unexpected error processing {symbol}: {e}", exc_info=True)
                continue
        
        # Log progress after each batch
        logger.info(f"Batch VCP scan progress: {processed_count}/{total_symbols} ({len(breakouts)} breakouts found, {live_data_fetched_count} live data fetched, {same_day_candles_created} same-day candles)")
    
    # Step 5: Log final statistics
    logger.info(f"Sequential VCP scan completed:")
    logger.info(f"  📊 Total symbols processed: {processed_count}")
    logger.info(f"  ✅ VCP breakouts found: {len(breakouts)}")
    logger.info(f"  🔴 Errors encountered: {error_count}")
    if is_market_open:
        logger.info(f"  📡 Live data fetched: {live_data_fetched_count}")
        logger.info(f"  📈 Same-day candles created: {same_day_candles_created}")
    
    # Step 6: Save results to database
    if breakouts:
        conn, cur = None, None
        try:
            conn, cur = get_trade_db_connection()
            AdvancedVcpResult.batch_save(cur, breakouts)
            
            # Send NOTIFY to trigger WebSocket subscription updates
            cur.execute("NOTIFY data_changed, 'advanced_vcp_results'")
            logger.info("Sent NOTIFY to update ticker subscriptions with advanced VCP screener tokens")
            
            conn.commit()
            logger.info(f"✅ Successfully saved {len(breakouts)} advanced VCP results to database")
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
        # If no breakouts, still clear the old data (already done in step 3)
        logger.info("No breakouts found to save.")
        conn, cur = None, None
        try:
            conn, cur = get_trade_db_connection()
            # Send NOTIFY even when no results to update subscriptions
            cur.execute("NOTIFY data_changed, 'advanced_vcp_results'")
            logger.info("Sent NOTIFY to update ticker subscriptions after clearing advanced VCP results")
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to send notification: {e}", exc_info=True)
        finally:
            if conn:
                release_trade_db_connection(conn, cur)

    return True

def run_advanced_vcp_scan(ohlc_df: pd.DataFrame, max_results: int = 50) -> bool:
    """
    DEPRECATED: Legacy bulk VCP scan - use run_advanced_vcp_scan_sequential() instead.
    This function is kept for backward compatibility but may cause memory/deadlock issues.
    """
    logger.warning("Using legacy bulk VCP scan - consider switching to sequential version")
    
    if ohlc_df.empty:
        logger.warning("Advanced VCP screener called with empty OHLC data.")
        return False

    logger.info(f"Starting legacy VCP scan on {len(ohlc_df['symbol'].unique())} stocks.")
    
    breakouts = []
    total_symbols = len(ohlc_df['symbol'].unique())
    processed_count = 0

    # Group by symbol and process each stock
    for symbol, group_df in ohlc_df.groupby('symbol'):
        processed_count += 1
        # Removed max_results limit - let it scan all stocks
        # if len(breakouts) >= max_results:
        #     logger.info(f"Reached max results ({max_results}). Stopping scan.")
        #     break
            
        try:
            # Log progress
            if processed_count % 100 == 0:
                logger.info(f"Legacy VCP scan progress: {processed_count}/{total_symbols}")

            # Sort by date and reset index for consistent processing
            stock_df = group_df.sort_values('date').reset_index(drop=True)
            
            # Ensure required columns are present
            required_cols = ['open', 'high', 'low', 'close', 'volume', 'date', 'sma_50', 'sma_100', 'sma_200']
            if not all(col in stock_df.columns for col in required_cols):
                logger.warning(f"Skipping {symbol}: missing one or more required columns.")
                continue

            # Calculate necessary indicators that might be missing
            stock_df = calculate_technical_indicators(stock_df)
            
            # Apply basic filters
            if not apply_realtime_filters(stock_df):
                continue
            
            # Run detection logic
            pattern = detect_realtime_vcp_breakout(stock_df, symbol)
            if pattern:
                logger.info(f"✅ LEGACY VCP BREAKOUT FOUND: {pattern['symbol']} (Score: {pattern['quality_score']})")
                breakouts.append(pattern)
                
        except Exception as e:
            logger.error(f"Error processing symbol {symbol} in legacy VCP scan: {e}", exc_info=True)
            continue
            
    logger.info(f"Legacy VCP scan loop finished. Found {len(breakouts)} breakouts. Now attempting to save to DB.")
    
    # Save results to the database
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
            logger.info("Successfully saved advanced VCP results to database.")
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
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to clear old advanced VCP results: {e}", exc_info=True)
        finally:
            if conn:
                release_trade_db_connection(conn, cur)

    return True

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("Starting VCP Real-Time Scanner...")
    
    # Configuration options
    max_results = 5000
    if '--max' in sys.argv:
        try:
            max_idx = sys.argv.index('--max')
            max_results = int(sys.argv[max_idx + 1])
        except (IndexError, ValueError):
            print("Invalid --max parameter, using default 50")
    
    # Run the scan
    breakouts = run_advanced_vcp_scan(max_results=max_results)
    
    if breakouts:
        # Generate and save report
        report = generate_trading_report(breakouts)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = 'Backtester/full_test'
        os.makedirs(output_dir, exist_ok=True)
        
        # Save detailed data
        df = pd.DataFrame(breakouts)
        csv_file = f'{output_dir}/vcp_breakouts_{timestamp}.csv'
        df.to_csv(csv_file, index=False)
        
        # Save report
        report_file = f'{output_dir}/vcp_trading_report_{timestamp}.txt'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Print summary
        print(report)
        print(f"\n📊 Detailed data saved: {csv_file}")
        print(f"📋 Trading report saved: {report_file}")
        
    else:
        print("❌ No VCP breakouts found in current scan.")
        print("Try running during market hours or check data availability.") 