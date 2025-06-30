#!/usr/bin/env python3
"""
VCP Real-Time Scanner for Live Market Detection
Identifies stocks breaking out from VCP patterns on the latest candle
Designed for end-of-day execution when candles are nearly complete
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import warnings
import logging
from db import get_trade_db_connection, release_trade_db_connection
from models import AdvancedVcpResult
warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION - SAME AS BACKTEST FOR CONSISTENCY
# =============================================================================

VCP_CONFIG = {
    'min_pattern_duration': 40,           # Reduced from 60
    'max_pattern_duration': 120,          # Reduced from 150
    'min_contractions': 2,
    'max_contractions': 8,
    'volume_multiplier': 1.2,             # Reduced from 1.3
    'compression_threshold': 0.85,        # Relaxed from 0.8
    'prior_uptrend_min': 3.0,             # Reduced from 5.0
    'prior_uptrend_max': 150.0,           # Increased from 100.0
    'minimum_quality_score': 3,           # Reduced from 4
    'min_data_candles': 200,              # Reduced from 1000 as we have limited historical data
}

STAGE_FLAGS = {
    'require_prior_uptrend': True,
    'require_volume_contraction': True,    # Enabled for volume contraction filtering
    'require_sma_position': True,
    'require_volume_surge': True,          # Enabled for volume surge filtering  
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
    """Calculate missing technical indicators."""
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_100'] = df['close'].rolling(window=100).mean()
    
    # Calculate ATR with a period of 50
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift(1))
    low_close = np.abs(df['low'] - df['close'].shift(1))
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr_50'] = true_range.rolling(window=50).mean()

    df['returns'] = df['close'].pct_change()
    df['range_pct'] = (df['high'] - df['low']) / df['close'] * 100
    
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
    """Stage 4: Enhanced Moving average position filter with additional VCP conditions"""
    if not STAGE_FLAGS['require_sma_position']:
        return {'valid': True, 'details': 'Skipped'}
    
    row = df.iloc[breakout_idx]
    close_price = row['close']
    sma_50 = row['sma_50']
    sma_100 = row['sma_100']
    sma_200 = row['sma_200']
    
    if pd.isna(sma_50) or pd.isna(sma_100) or pd.isna(sma_200):
        return {'valid': False, 'details': 'Missing SMA data'}
    
    # Basic SMA position checks
    above_sma50 = close_price > sma_50
    above_sma100 = close_price > sma_100
    above_sma200 = close_price > sma_200
    
    # Enhanced SMA alignment: 50 SMA > 100 SMA > 200 SMA (trending upward)
    sma_alignment = sma_50 > sma_100 > sma_200
    
    # All conditions must be met
    valid = above_sma50 and above_sma100 and above_sma200 and sma_alignment
    
    return {
        'valid': valid,
        'above_sma50': above_sma50,
        'above_sma100': above_sma100,
        'above_sma200': above_sma200,
        'sma_alignment': sma_alignment,
        'price_vs_sma50_pct': ((close_price - sma_50) / sma_50) * 100 if sma_50 != 0 else 0,
        'price_vs_sma100_pct': ((close_price - sma_100) / sma_100) * 100 if sma_100 != 0 else 0,
        'price_vs_sma200_pct': ((close_price - sma_200) / sma_200) * 100 if sma_200 != 0 else 0,
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
        volume_surge = breakout_volume > recent_volume * VCP_CONFIG['volume_multiplier']
        volume_ratio = breakout_volume / recent_volume if recent_volume > 0 else 0
    else:
        volume_surge = True
        volume_ratio = 1.0
    
    # Enhanced breakout candle quality checks
    green_candle = breakout_close >= breakout_open  # Green candle (close >= open)
    higher_close = breakout_close >= previous_close  # Higher than previous close
    valid_volume = breakout_volume > 0
    
    # Additional real-time checks  
    strong_close = breakout_candle['close'] > pattern_high * 0.995  # More flexible close requirement
    good_range = (breakout_candle['high'] - breakout_candle['low']) / breakout_candle['close'] < 0.12  # More flexible range
    
    # All breakout conditions must be met
    valid = (price_breakout and volume_surge and green_candle and 
             higher_close and valid_volume)
    
    return {
        'valid': valid,
        'price_breakout': price_breakout,
        'volume_surge': volume_surge,
        'green_candle': green_candle,
        'higher_close': higher_close,
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
        'details': f'Price: {price_breakout}, Volume: {volume_surge}, Green: {green_candle}, Higher: {higher_close}, Strong Close: {strong_close}'
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
    
    # Check last 3 candles for breakouts (more flexible)
    for lookback in range(0, min(3, len(df))):
        breakout_idx = len(df) - 1 - lookback
        
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
            
            # Stage 4: SMA position
            sma_result = check_sma_position(df, breakout_idx)
            if not sma_result['valid']:
                continue
            
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
            return collect_realtime_metrics(
                df, symbol, pattern_start, pattern_end, breakout_idx,
                uptrend_result, contractions, volume_result, sma_result,
                breakout_result, compression_result, quality_result
            )
    
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
    atr_50 = breakout_candle['atr_50']
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
    }

# =============================================================================
# MAIN SCANNING ENGINE
# =============================================================================

def run_advanced_vcp_scan(ohlc_df: pd.DataFrame, max_results: int = 50) -> bool:
    """
    Run the advanced VCP scan across all stocks from the provided OHLC DataFrame.
    Saves results to the database.
    """
    if ohlc_df.empty:
        logger.warning("Advanced VCP screener called with empty OHLC data.")
        return False

    logger.info(f"Starting advanced VCP scan on {len(ohlc_df['symbol'].unique())} stocks.")
    
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
                logger.info(f"Advanced VCP scan progress: {processed_count}/{total_symbols}")

            # Sort by date and reset index for consistent processing
            stock_df = group_df.sort_values('date').reset_index(drop=True)
            
            # Ensure required columns are present
            required_cols = ['open', 'high', 'low', 'close', 'volume', 'date', 'sma_50', 'sma_200']
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
                logger.info(f"✅ ADVANCED VCP BREAKOUT FOUND: {pattern['symbol']} (Score: {pattern['quality_score']})")
                breakouts.append(pattern)
                
        except Exception as e:
            logger.error(f"Error processing symbol {symbol} in advanced VCP scan: {e}", exc_info=True)
            continue
            
    logger.info(f"Advanced VCP scan loop finished. Found {len(breakouts)} breakouts. Now attempting to save to DB.")
    
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