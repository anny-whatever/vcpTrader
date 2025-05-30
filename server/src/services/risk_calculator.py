import logging
import pandas as pd
import numpy as np
import pandas_ta as ta
from datetime import datetime, timedelta
from db import get_trade_db_connection, release_trade_db_connection
from models import SaveOHLC

logger = logging.getLogger(__name__)

class RiskCalculator:
    """
    Calculate comprehensive risk scores for stocks based on historical data.
    Risk score ranges from 1 (lowest risk) to 10 (highest risk).
    """
    
    def __init__(self):
        self.risk_weights = {
            'volatility': 0.30,      # Price movement consistency
            'atr_risk': 0.20,        # Average True Range relative to price
            'drawdown_risk': 0.10,   # Maximum decline from peaks
            'gap_risk': 0.25,        # Overnight/weekend price gaps
            'volume_consistency': 0.10,  # Liquidity stability
            'trend_stability': 0.05  # Directional consistency
        }
    
    def calculate_volatility_score(self, df):
        """
        Calculate volatility-based risk score (1-10).
        Higher volatility = Higher risk score.
        """
        try:
            # Calculate daily returns
            df['returns'] = df['close'].pct_change()
            
            # Calculate annualized volatility
            daily_vol = df['returns'].std()
            annual_vol = daily_vol * np.sqrt(252)
            
            # Convert to risk score (1-10)
            # Typical equity volatility ranges: 15%-60%
            if annual_vol <= 0.15:
                return 1
            elif annual_vol <= 0.20:
                return 2
            elif annual_vol <= 0.25:
                return 3
            elif annual_vol <= 0.30:
                return 4
            elif annual_vol <= 0.35:
                return 5
            elif annual_vol <= 0.40:
                return 6
            elif annual_vol <= 0.45:
                return 7
            elif annual_vol <= 0.50:
                return 8
            elif annual_vol <= 0.60:
                return 9
            else:
                return 10
                
        except Exception as e:
            logger.error(f"Error calculating volatility score: {e}")
            return 5  # Default medium risk
    
    def calculate_atr_risk_score(self, df):
        """
        Calculate ATR-based risk score (1-10).
        Higher ATR relative to price = Higher risk score.
        """
        try:
            # Calculate average ATR percentage
            df['atr_pct'] = (df['atr'] / df['close']) * 100
            avg_atr_pct = df['atr_pct'].mean()
            
            # Convert to risk score (1-10)
            # ATR percentage ranges: 1%-8%+
            if avg_atr_pct <= 1.0:
                return 1
            elif avg_atr_pct <= 1.5:
                return 2
            elif avg_atr_pct <= 2.0:
                return 3
            elif avg_atr_pct <= 2.5:
                return 4
            elif avg_atr_pct <= 3.0:
                return 5
            elif avg_atr_pct <= 3.5:
                return 6
            elif avg_atr_pct <= 4.0:
                return 7
            elif avg_atr_pct <= 5.0:
                return 8
            elif avg_atr_pct <= 6.0:
                return 9
            else:
                return 10
                
        except Exception as e:
            logger.error(f"Error calculating ATR risk score: {e}")
            return 5  # Default medium risk
    
    def calculate_drawdown_risk_score(self, df):
        """
        Calculate maximum drawdown-based risk score (1-10).
        Higher maximum drawdown = Higher risk score.
        """
        try:
            # Calculate running maximum and drawdown
            df['running_max'] = df['close'].expanding().max()
            df['drawdown'] = (df['close'] - df['running_max']) / df['running_max']
            max_drawdown = abs(df['drawdown'].min())
            
            # Calculate average drawdown magnitude
            negative_drawdowns = df['drawdown'][df['drawdown'] < 0]
            avg_drawdown = abs(negative_drawdowns.mean()) if len(negative_drawdowns) > 0 else 0
            
            # Combine max and average drawdown
            combined_drawdown = (max_drawdown * 0.7) + (avg_drawdown * 0.3)
            
            # Convert to risk score (1-10)
            # Drawdown ranges: 5%-50%+
            if combined_drawdown <= 0.05:
                return 1
            elif combined_drawdown <= 0.10:
                return 2
            elif combined_drawdown <= 0.15:
                return 3
            elif combined_drawdown <= 0.20:
                return 4
            elif combined_drawdown <= 0.25:
                return 5
            elif combined_drawdown <= 0.30:
                return 6
            elif combined_drawdown <= 0.35:
                return 7
            elif combined_drawdown <= 0.40:
                return 8
            elif combined_drawdown <= 0.50:
                return 9
            else:
                return 10
                
        except Exception as e:
            logger.error(f"Error calculating drawdown risk score: {e}")
            return 5  # Default medium risk
    
    def calculate_gap_risk_score(self, df):
        """
        Calculate gap risk score based on price gaps (1-10).
        Higher gap frequency/magnitude = Higher risk score.
        """
        try:
            # Calculate gaps (difference between open and previous close)
            df['prev_close'] = df['close'].shift(1)
            df['gap'] = (df['open'] - df['prev_close']) / df['prev_close']
            df['gap'] = df['gap'].fillna(0)
            
            # Calculate gap statistics
            gap_volatility = df['gap'].std()
            large_gaps = (abs(df['gap']) > 0.03).sum()  # Gaps > 3%
            gap_frequency = large_gaps / len(df)
            
            # Combined gap risk metric
            gap_risk = (gap_volatility * 0.6) + (gap_frequency * 0.4)
            
            # Convert to risk score (1-10)
            if gap_risk <= 0.005:
                return 1
            elif gap_risk <= 0.010:
                return 2
            elif gap_risk <= 0.015:
                return 3
            elif gap_risk <= 0.020:
                return 4
            elif gap_risk <= 0.025:
                return 5
            elif gap_risk <= 0.030:
                return 6
            elif gap_risk <= 0.035:
                return 7
            elif gap_risk <= 0.040:
                return 8
            elif gap_risk <= 0.050:
                return 9
            else:
                return 10
                
        except Exception as e:
            logger.error(f"Error calculating gap risk score: {e}")
            return 5  # Default medium risk
    
    def calculate_volume_consistency_score(self, df):
        """
        Calculate volume consistency risk score (1-10).
        Higher volume inconsistency = Higher risk score.
        """
        try:
            # Calculate volume statistics
            volume_cv = df['volume'].std() / df['volume'].mean()  # Coefficient of variation
            
            # Identify volume spikes (> 2x average)
            avg_volume = df['volume'].mean()
            volume_spikes = (df['volume'] > avg_volume * 2).sum()
            spike_frequency = volume_spikes / len(df)
            
            # Combined volume risk
            volume_risk = (volume_cv * 0.7) + (spike_frequency * 0.3)
            
            # Convert to risk score (1-10)
            if volume_risk <= 0.5:
                return 1
            elif volume_risk <= 1.0:
                return 2
            elif volume_risk <= 1.5:
                return 3
            elif volume_risk <= 2.0:
                return 4
            elif volume_risk <= 2.5:
                return 5
            elif volume_risk <= 3.0:
                return 6
            elif volume_risk <= 3.5:
                return 7
            elif volume_risk <= 4.0:
                return 8
            elif volume_risk <= 5.0:
                return 9
            else:
                return 10
                
        except Exception as e:
            logger.error(f"Error calculating volume consistency score: {e}")
            return 5  # Default medium risk
    
    def calculate_trend_stability_score(self, df):
        """
        Calculate trend stability risk score (1-10).
        Higher trend instability = Higher risk score.
        """
        try:
            # Calculate trend using moving averages
            df['sma_20'] = df['close'].rolling(window=20).mean()
            
            # Count trend changes (when price crosses SMA)
            df['above_sma'] = df['close'] > df['sma_20']
            trend_changes = (df['above_sma'] != df['above_sma'].shift(1)).sum()
            trend_stability = trend_changes / len(df)
            
            # Convert to risk score (1-10)
            if trend_stability <= 0.05:
                return 1
            elif trend_stability <= 0.10:
                return 2
            elif trend_stability <= 0.15:
                return 3
            elif trend_stability <= 0.20:
                return 4
            elif trend_stability <= 0.25:
                return 5
            elif trend_stability <= 0.30:
                return 6
            elif trend_stability <= 0.35:
                return 7
            elif trend_stability <= 0.40:
                return 8
            elif trend_stability <= 0.50:
                return 9
            else:
                return 10
                
        except Exception as e:
            logger.error(f"Error calculating trend stability score: {e}")
            return 5  # Default medium risk
    
    def calculate_stock_risk_score(self, symbol, instrument_token, lookback_days=252):
        """
        Calculate comprehensive risk score for a single stock.
        
        Args:
            symbol: Stock symbol
            instrument_token: Instrument token
            lookback_days: Number of days to look back for calculation
            
        Returns:
            dict: Risk score and component scores
        """
        try:
            conn, cur = get_trade_db_connection()
            
            # Fetch historical data
            query = """
                SELECT 
                    date, open, high, low, close, volume, atr
                FROM ohlc
                WHERE instrument_token = %s
                AND interval = 'day'
                AND date >= NOW() - INTERVAL '%s days'
                ORDER BY date ASC
            """
            
            cur.execute(query, (instrument_token, lookback_days))
            rows = cur.fetchall()
            
            if len(rows) < 50:  # Need minimum data
                logger.warning(f"Insufficient data for {symbol}: {len(rows)} rows")
                return self._default_risk_score()
            
            # Convert to DataFrame
            columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'atr']
            df = pd.DataFrame(rows, columns=columns)
            df['date'] = pd.to_datetime(df['date'])
            
            # Ensure numeric columns
            numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'atr']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
            df = df.dropna()
            
            # Calculate individual risk components
            volatility_score = self.calculate_volatility_score(df)
            atr_risk_score = self.calculate_atr_risk_score(df)
            drawdown_score = self.calculate_drawdown_risk_score(df)
            gap_risk_score = self.calculate_gap_risk_score(df)
            volume_score = self.calculate_volume_consistency_score(df)
            trend_score = self.calculate_trend_stability_score(df)
            
            # Calculate weighted overall risk score
            overall_risk = (
                volatility_score * self.risk_weights['volatility'] +
                atr_risk_score * self.risk_weights['atr_risk'] +
                drawdown_score * self.risk_weights['drawdown_risk'] +
                gap_risk_score * self.risk_weights['gap_risk'] +
                volume_score * self.risk_weights['volume_consistency'] +
                trend_score * self.risk_weights['trend_stability']
            )
            
            # Round to one decimal place
            overall_risk = round(overall_risk, 1)
            
            return {
                'symbol': symbol,
                'instrument_token': instrument_token,
                'overall_risk_score': overall_risk,
                'risk_components': {
                    'volatility': volatility_score,
                    'atr_risk': atr_risk_score,
                    'drawdown_risk': drawdown_score,
                    'gap_risk': gap_risk_score,
                    'volume_consistency': volume_score,
                    'trend_stability': trend_score
                },
                'data_points': len(df),
                'calculated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk score for {symbol}: {e}")
            return self._default_risk_score(symbol, instrument_token)
        finally:
            if 'conn' in locals() and 'cur' in locals():
                release_trade_db_connection(conn, cur)
    
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
    
    def calculate_bulk_risk_scores(self, symbols_list=None, limit=None):
        """
        Calculate risk scores for multiple stocks.
        
        Args:
            symbols_list: List of symbols to calculate (None for all)
            limit: Maximum number of symbols to process
            
        Returns:
            list: Risk score results for all symbols
        """
        try:
            conn, cur = get_trade_db_connection()
            
            # Get unique symbols from OHLC data
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
            logger.info(f"Calculating risk scores for {len(symbols)} symbols")
            
            results = []
            for i, (symbol, instrument_token) in enumerate(symbols):
                if i % 50 == 0:
                    logger.info(f"Processing symbol {i+1}/{len(symbols)}: {symbol}")
                
                risk_result = self.calculate_stock_risk_score(symbol, instrument_token)
                results.append(risk_result)
            
            logger.info(f"Completed risk calculation for {len(results)} symbols")
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk risk calculation: {e}")
            return []
        finally:
            if 'conn' in locals() and 'cur' in locals():
                release_trade_db_connection(conn, cur)


# Utility functions for easy access
def get_stock_risk_score(symbol, instrument_token):
    """Get risk score for a single stock."""
    calculator = RiskCalculator()
    return calculator.calculate_stock_risk_score(symbol, instrument_token)

def get_bulk_risk_scores(symbols_list=None, limit=100):
    """Get risk scores for multiple stocks."""
    calculator = RiskCalculator()
    return calculator.calculate_bulk_risk_scores(symbols_list, limit)

def get_risk_ranking(limit=50):
    """Get top N stocks ranked by risk score (lowest to highest)."""
    calculator = RiskCalculator()
    results = calculator.calculate_bulk_risk_scores(limit=limit)
    
    # Sort by risk score (ascending - lowest risk first)
    results.sort(key=lambda x: x['overall_risk_score'])
    return results 