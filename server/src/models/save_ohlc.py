import logging
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class SaveOHLC:
    def __init__(
        self,
        instrument_token,
        symbol,
        interval,
        date,
        open_price,
        high,
        low,
        close,
        volume,
        sma_50=0.0,
        sma_100=0.0,
        sma_200=0.0,
        atr=0.0,
        week52_high=0.0,
        week52_low=0.0,
        away_from_high=0.0,
        away_from_low=0.0
    ):
        self.instrument_token = instrument_token
        self.symbol = symbol
        self.interval = interval
        self.date = date
        self.open = open_price
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume
        # New columns for indicators
        self.sma_50 = sma_50
        self.sma_100 = sma_100
        self.sma_200 = sma_200
        self.atr = atr
        self.week52_high = week52_high
        self.week52_low = week52_low
        self.away_from_high = away_from_high
        self.away_from_low = away_from_low

    def save(self, cur):
        """
        Inserts one row into the 'ohlc' table, including
        technical indicators that have been precomputed.
        """
        query = """
        INSERT INTO ohlc (
            instrument_token, symbol, interval, date,
            open, high, low, close, volume,
            sma_50, sma_100, sma_200, atr,
            "52_week_high", "52_week_low",
            away_from_high, away_from_low
        )
        VALUES (%s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s);
        """
        try:
            cur.execute(query, (
                self.instrument_token,
                self.symbol,
                self.interval,
                self.date,
                self.open,
                self.high,
                self.low,
                self.close,
                self.volume,
                self.sma_50,
                self.sma_100,
                self.sma_200,
                self.atr,
                self.week52_high,
                self.week52_low,
                self.away_from_high,
                self.away_from_low
            ))
            logger.info(f"OHLC+Indicators data saved for instrument_token: {self.instrument_token}")
        except Exception as e:
            logger.error(f"Error saving OHLC data: {e}")
            raise e

    @classmethod
    def select_token(cls, cur):
        """
        Example method to select all tokens from 'equity_tokens' table.
        """
        query = "SELECT * FROM equity_tokens;"
        try:
            cur.execute(query)
            tokens = cur.fetchall()
            logger.info("Tokens selected successfully from equity_tokens.")
            return tokens
        except Exception as e:
            logger.error(f"Error selecting token from equity_tokens: {e}")
            return None

    @classmethod
    def delete_all(cls, cur, instrument_token, interval):
        """
        Deletes all rows in the 'ohlc' table matching
        the provided instrument_token and interval.
        """
        delete_query = """
            DELETE FROM ohlc
            WHERE instrument_token = %s
              AND interval = %s;
        """
        try:
            cur.execute(delete_query, (instrument_token, interval))
            logger.info(f"Deleted OHLC records for instrument_token: {instrument_token} and interval: {interval}")
        except Exception as e:
            logger.error(f"Error deleting OHLC data: {e}")
            raise e
    
    @classmethod
    def delete_by_interval(cls, cur, interval):
        """
        Deletes all rows in the 'ohlc' table matching
        the provided interval only.
        """
        delete_query = """
            DELETE FROM ohlc
            WHERE interval = %s;
        """
        try:
            cur.execute(delete_query, (interval,))
            logger.info(f"Deleted OHLC records for interval: {interval}")
        except Exception as e:
            logger.error(f"Error deleting OHLC data by interval: {e}")
            raise e


    @classmethod
    def fetch_by_instrument(cls, cur, instrument_token):
        """
        Fetches OHLC rows (plus indicator columns) from the 'ohlc' table
        for a given instrument_token (with interval='day' as an example).
        """
        try:
            cur.execute("""
                SELECT 
                instrument_token,
                symbol,
                interval,
                date,
                open,
                high,
                low,
                close,
                volume,
                segment
            FROM ohlc
            WHERE instrument_token = %s
            AND interval = 'day'
            AND date >= NOW() - INTERVAL '1800 days'
            ORDER BY date ASC;
            """, (instrument_token,))
            results = cur.fetchall()
            logger.info(f"Fetched OHLC data for instrument_token: {instrument_token}")
            return results
        except Exception as e:
            logger.error(f"Error fetching OHLC data for instrument_token {instrument_token}: {e}")
            raise e

    @classmethod
    def fetch_by_instrument_weekly(cls, cur, instrument_token):
        """
        Fetches weekly OHLC rows (plus indicator columns) from the 'ohlc' table
        for a given instrument_token with interval='week'.
        """
        try:
            cur.execute("""
                SELECT 
                instrument_token,
                symbol,
                interval,
                date,
                open,
                high,
                low,
                close,
                volume,
                segment,
                sma_50,
                sma_100,
                sma_200,
                atr,
                "52_week_high",
                "52_week_low",
                away_from_high,
                away_from_low
            FROM ohlc
            WHERE instrument_token = %s
            AND interval = 'week'
            AND date >= NOW() - INTERVAL '1800 days'
            ORDER BY date ASC;
            """, (instrument_token,))
            results = cur.fetchall()
            logger.info(f"Fetched weekly OHLC data for instrument_token: {instrument_token}")
            return results
        except Exception as e:
            logger.error(f"Error fetching weekly OHLC data for instrument_token {instrument_token}: {e}")
            raise e

    @classmethod
    def fetch_precomputed_ohlc(cls, cur, limit=200, exclude_segments=None):
        """
        DEPRECATED - Use fetch_ohlc_exclude_ipo(), fetch_ohlc_exclude_all_segment(), 
        or fetch_ohlc_exclude_ipo_and_all() instead.
        
        This method is kept for backward compatibility.
        By default, it excludes both IPO and ALL segments.
        """
        logger.warning("fetch_precomputed_ohlc is deprecated. Use fetch_ohlc_exclude_ipo_and_all() instead.")
        return cls.fetch_ohlc_exclude_ipo_and_all(cur)

    @classmethod
    def fetch_precomputed_weekly_ohlc(cls, cur, limit=200, exclude_segments=None, include_segments=None):
        """
        DEPRECATED - Use fetch_ohlc_exclude_ipo() instead.
        
        This method is kept for backward compatibility.
        By default, it excludes only IPO segment.
        """
        logger.warning("fetch_precomputed_weekly_ohlc is deprecated. Use fetch_ohlc_exclude_ipo() instead.")
        return cls.fetch_ohlc_exclude_ipo(cur)

    @classmethod
    def fetch_precomputed_ohlc_without_segments(cls, cur, exclude_segments=None, limit=200):
        """
        DEPRECATED - Use fetch_ohlc_exclude_ipo(), fetch_ohlc_exclude_all_segment(), 
        or fetch_ohlc_exclude_ipo_and_all() instead.
        
        This method is kept for backward compatibility.
        By default, it excludes both IPO and ALL segments.
        """
        logger.warning("fetch_precomputed_ohlc_without_segments is deprecated. Use fetch_ohlc_exclude_ipo_and_all() instead.")
        return cls.fetch_ohlc_exclude_ipo_and_all(cur)

    @classmethod
    def fetch_precomputed_weekly_ohlc_with_filtering(cls, cur, include_segments=None, exclude_segments=None, limit=200):
        """
        DEPRECATED - Use fetch_ohlc_exclude_ipo() instead.
        
        This method is kept for backward compatibility.
        By default, it excludes only IPO segment.
        """
        logger.warning("fetch_precomputed_weekly_ohlc_with_filtering is deprecated. Use fetch_ohlc_exclude_ipo() instead.")
        return cls.fetch_ohlc_exclude_ipo(cur)

    @classmethod
    def fetch_ohlc_exclude_ipo(cls, cur):
        """
        Fetch precomputed OHLC data excluding only IPO segment.
        
        Args:
            cur: Database cursor
            
        Returns:
            DataFrame with OHLC data excluding the IPO segment
        """
        logger.info("Fetching OHLC data excluding IPO segment")
        
        query = """
            SELECT 
                instrument_token,
                symbol,
                interval,
                date,
                open,
                high,
                low,
                close,
                volume,
                segment,
                sma_50,
                sma_100,
                sma_200,
                atr,
                "52_week_high",
                "52_week_low",
                away_from_high,
                away_from_low
            FROM ohlc
            WHERE interval = 'day'
            AND date >= NOW() - INTERVAL '365 days'
            AND segment != 'IPO'
            ORDER BY date DESC
        """
        
        try:
            cur.execute(query)
            rows = cur.fetchall()
            logger.info(f"Fetched {len(rows)} OHLC rows excluding IPO segment")
            
            if not rows:
                logger.warning("No rows returned. Returning empty DataFrame.")
                return pd.DataFrame(columns=[
                    "instrument_token", "symbol", "interval", "date", "open", "high", "low", "close",
                    "volume", "segment", "sma_50", "sma_100", "sma_200", "atr", "52_week_high",
                    "52_week_low", "away_from_high", "away_from_low"
                ])

            # Convert to DataFrame
            columns = [
                "instrument_token", "symbol", "interval", "date", "open", "high", "low", "close",
                "volume", "segment", "sma_50", "sma_100", "sma_200", "atr", "52_week_high",
                "52_week_low", "away_from_high", "away_from_low"
            ]
            df = pd.DataFrame(rows, columns=columns)

            # Convert all numeric columns in one vectorized step
            float_cols = [
                "open", "high", "low", "close", "volume",
                "sma_50", "sma_100", "sma_200", "atr",
                "52_week_high", "52_week_low", "away_from_high", "away_from_low"
            ]
            df[float_cols] = df[float_cols].apply(pd.to_numeric, errors='coerce').fillna(0.0)

            # Parse the date column with inferred format for speed
            df["date"] = pd.to_datetime(df["date"], errors='coerce')

            # Replace infinite values in one go
            df.replace({float('inf'): 0.0, float('-inf'): 0.0}, inplace=True)

            # Log summary statistics for debugging
            logger.info(f"Constructed DataFrame with {len(df)} rows excluding IPO segment")
            symbols = df['symbol'].unique()
            logger.info(f"DataFrame contains {len(symbols)} unique symbols")
            
            return df
        except Exception as e:
            logger.error(f"Error in fetch_ohlc_exclude_ipo: {e}", exc_info=True)
            logger.error("Returning empty DataFrame due to error")
            return pd.DataFrame(columns=[
                "instrument_token", "symbol", "interval", "date", "open", "high", "low", "close",
                "volume", "segment", "sma_50", "sma_100", "sma_200", "atr", "52_week_high",
                "52_week_low", "away_from_high", "away_from_low"
            ])

    @classmethod
    def fetch_ohlc_exclude_all_segment(cls, cur):
        """
        Fetch precomputed OHLC data excluding only ALL segment.
        
        Args:
            cur: Database cursor
            
        Returns:
            DataFrame with OHLC data excluding the ALL segment
        """
        logger.info("Fetching OHLC data excluding ALL segment")
        
        query = """
            SELECT 
                instrument_token,
                symbol,
                interval,
                date,
                open,
                high,
                low,
                close,
                volume,
                segment,
                sma_50,
                sma_100,
                sma_200,
                atr,
                "52_week_high",
                "52_week_low",
                away_from_high,
                away_from_low
            FROM ohlc
            WHERE interval = 'day'
            AND date >= NOW() - INTERVAL '365 days'
            AND segment != 'ALL'
            AND segment != 'IPO'
            ORDER BY date DESC
        """
        
        try:
            cur.execute(query)
            rows = cur.fetchall()
            logger.info(f"Fetched {len(rows)} OHLC rows excluding ALL segment")
            
            if not rows:
                logger.warning("No rows returned. Returning empty DataFrame.")
                return pd.DataFrame(columns=[
                    "instrument_token", "symbol", "interval", "date", "open", "high", "low", "close",
                    "volume", "segment", "sma_50", "sma_100", "sma_200", "atr", "52_week_high",
                    "52_week_low", "away_from_high", "away_from_low"
                ])

            # Convert to DataFrame
            columns = [
                "instrument_token", "symbol", "interval", "date", "open", "high", "low", "close",
                "volume", "segment", "sma_50", "sma_100", "sma_200", "atr", "52_week_high",
                "52_week_low", "away_from_high", "away_from_low"
            ]
            df = pd.DataFrame(rows, columns=columns)

            # Convert all numeric columns in one vectorized step
            float_cols = [
                "open", "high", "low", "close", "volume",
                "sma_50", "sma_100", "sma_200", "atr",
                "52_week_high", "52_week_low", "away_from_high", "away_from_low"
            ]
            df[float_cols] = df[float_cols].apply(pd.to_numeric, errors='coerce').fillna(0.0)

            # Parse the date column with inferred format for speed
            df["date"] = pd.to_datetime(df["date"], errors='coerce')

            # Replace infinite values in one go
            df.replace({float('inf'): 0.0, float('-inf'): 0.0}, inplace=True)

            # Log summary statistics for debugging
            logger.info(f"Constructed DataFrame with {len(df)} rows excluding ALL segment")
            symbols = df['symbol'].unique()
            logger.info(f"DataFrame contains {len(symbols)} unique symbols")
            
            return df
        except Exception as e:
            logger.error(f"Error in fetch_ohlc_exclude_all_segment: {e}", exc_info=True)
            logger.error("Returning empty DataFrame due to error")
            return pd.DataFrame(columns=[
                "instrument_token", "symbol", "interval", "date", "open", "high", "low", "close",
                "volume", "segment", "sma_50", "sma_100", "sma_200", "atr", "52_week_high",
                "52_week_low", "away_from_high", "away_from_low"
            ])

    @classmethod
    def fetch_ohlc_exclude_ipo_and_all(cls, cur):
        """
        Fetch precomputed OHLC data excluding both IPO and ALL segments.
        
        Args:
            cur: Database cursor
            
        Returns:
            DataFrame with OHLC data excluding both IPO and ALL segments
        """
        logger.info("Fetching OHLC data excluding both IPO and ALL segments")
        
        query = """
            SELECT 
                instrument_token,
                symbol,
                interval,
                date,
                open,
                high,
                low,
                close,
                volume,
                segment,
                sma_50,
                sma_100,
                sma_200,
                atr,
                "52_week_high",
                "52_week_low",
                away_from_high,
                away_from_low
            FROM ohlc
            WHERE interval = 'day'
            AND date >= NOW() - INTERVAL '365 days'
            AND segment NOT IN ('IPO', 'ALL')
            ORDER BY date DESC
        """
        
        try:
            cur.execute(query)
            rows = cur.fetchall()
            logger.info(f"Fetched {len(rows)} OHLC rows excluding both IPO and ALL segments")
            
            if not rows:
                logger.warning("No rows returned. Returning empty DataFrame.")
                return pd.DataFrame(columns=[
                    "instrument_token", "symbol", "interval", "date", "open", "high", "low", "close",
                    "volume", "segment", "sma_50", "sma_100", "sma_200", "atr", "52_week_high",
                    "52_week_low", "away_from_high", "away_from_low"
                ])

            # Convert to DataFrame
            columns = [
                "instrument_token", "symbol", "interval", "date", "open", "high", "low", "close",
                "volume", "segment", "sma_50", "sma_100", "sma_200", "atr", "52_week_high",
                "52_week_low", "away_from_high", "away_from_low"
            ]
            df = pd.DataFrame(rows, columns=columns)

            # Convert all numeric columns in one vectorized step
            float_cols = [
                "open", "high", "low", "close", "volume",
                "sma_50", "sma_100", "sma_200", "atr",
                "52_week_high", "52_week_low", "away_from_high", "away_from_low"
            ]
            df[float_cols] = df[float_cols].apply(pd.to_numeric, errors='coerce').fillna(0.0)

            # Parse the date column with inferred format for speed
            df["date"] = pd.to_datetime(df["date"], errors='coerce')

            # Replace infinite values in one go
            df.replace({float('inf'): 0.0, float('-inf'): 0.0}, inplace=True)

            # Log summary statistics for debugging
            logger.info(f"Constructed DataFrame with {len(df)} rows excluding both IPO and ALL segments")
            symbols = df['symbol'].unique()
            logger.info(f"DataFrame contains {len(symbols)} unique symbols")
            
            return df
        except Exception as e:
            logger.error(f"Error in fetch_ohlc_exclude_ipo_and_all: {e}", exc_info=True)
            logger.error("Returning empty DataFrame due to error")
            return pd.DataFrame(columns=[
                "instrument_token", "symbol", "interval", "date", "open", "high", "low", "close",
                "volume", "segment", "sma_50", "sma_100", "sma_200", "atr", "52_week_high",
                "52_week_low", "away_from_high", "away_from_low"
            ])

