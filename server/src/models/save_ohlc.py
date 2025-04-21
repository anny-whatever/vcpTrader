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
        sma_150=0.0,
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
        self.sma_150 = sma_150
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
            sma_50, sma_150, sma_200, atr,
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
                self.sma_150,
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
                sma_150,
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
    def fetch_precomputed_ohlc(cls, cur, limit=200):
        """
        Fast retrieval of the last `limit` rows per symbol from the ohlc table,
        including precomputed columns (sma_50, sma_150, sma_200, atr, "52_week_high", etc.).
        
        Uses a window function to partition by symbol and order by date descending.
        Returns a pandas DataFrame with the combined results.
        """
        logger.info(f"Fetching up to {limit} rows of precomputed OHLC+Indicators per symbol from DB...")

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
            sma_150,
            sma_200,
            atr,
            "52_week_high",
            "52_week_low",
            away_from_high,
            away_from_low
        FROM ohlc
        WHERE segment != 'ALL'
        AND date >= NOW() - INTERVAL '333 days';
        """

        try:
            # Use parameterized query to safely pass the limit
            cur.execute(query)
            rows = cur.fetchall()
            logger.info(f"Fetched processed OHLC+Indicators data for {len(rows)} symbols.")
            if not rows:
                logger.warning("No rows returned from fetch_precomputed_ohlc. Returning empty DataFrame.")
                return pd.DataFrame(columns=[
                    "instrument_token", "symbol", "interval", "date", "open", "high", "low", "close",
                    "volume", "segment", "sma_50", "sma_150", "sma_200", "atr", "52_week_high",
                    "52_week_low", "away_from_high", "away_from_low"
                ])

            # Convert to DataFrame
            columns = [
                "instrument_token", "symbol", "interval", "date", "open", "high", "low", "close",
                "volume", "segment", "sma_50", "sma_150", "sma_200", "atr", "52_week_high",
                "52_week_low", "away_from_high", "away_from_low"
            ]
            df = pd.DataFrame(rows, columns=columns)

            # Convert all numeric columns in one vectorized step
            float_cols = [
                "open", "high", "low", "close", "volume",
                "sma_50", "sma_150", "sma_200", "atr",
                "52_week_high", "52_week_low", "away_from_high", "away_from_low"
            ]
            df[float_cols] = df[float_cols].apply(pd.to_numeric, errors='coerce').fillna(0.0)

            # Parse the date column with inferred format for speed
            df["date"] = pd.to_datetime(df["date"], errors='coerce')

            # Replace infinite values in one go
            df.replace({float('inf'): 0.0, float('-inf'): 0.0}, inplace=True)

            logger.info(f"Constructed DataFrame with {len(df)} rows of precomputed OHLC data.")
            return df
        except Exception as e:
            logger.error(f"Error in fetch_precomputed_ohlc: {e}", exc_info=True)
            raise e

    @classmethod
    def fetch_precomputed_weekly_ohlc(cls, cur, limit=200):
        """
        Fast retrieval of the last `limit` rows per symbol from the ohlc table with 'week' interval,
        including precomputed columns (sma_50, sma_150, sma_200, atr, "52_week_high", etc.).
        
        Returns a pandas DataFrame with the combined results.
        """
        logger.info(f"Fetching up to {limit} rows of precomputed weekly OHLC+Indicators per symbol from DB...")

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
            sma_150,
            sma_200,
            atr,
            "52_week_high",
            "52_week_low",
            away_from_high,
            away_from_low
        FROM ohlc
        WHERE interval = 'week'
        AND date >= NOW() - INTERVAL '1000 days';
        """

        try:
            # Use parameterized query to safely pass the limit
            cur.execute(query)
            rows = cur.fetchall()
            logger.info(f"Fetched processed weekly OHLC+Indicators data for {len(rows)} symbols.")
            if not rows:
                logger.warning("No rows returned from fetch_precomputed_weekly_ohlc. Returning empty DataFrame.")
                return pd.DataFrame(columns=[
                    "instrument_token", "symbol", "interval", "date", "open", "high", "low", "close",
                    "volume", "segment", "sma_50", "sma_150", "sma_200", "atr", "52_week_high",
                    "52_week_low", "away_from_high", "away_from_low"
                ])

            # Convert to DataFrame
            columns = [
                "instrument_token", "symbol", "interval", "date", "open", "high", "low", "close",
                "volume", "segment", "sma_50", "sma_150", "sma_200", "atr", "52_week_high",
                "52_week_low", "away_from_high", "away_from_low"
            ]
            df = pd.DataFrame(rows, columns=columns)

            # Convert all numeric columns in one vectorized step
            float_cols = [
                "open", "high", "low", "close", "volume",
                "sma_50", "sma_150", "sma_200", "atr",
                "52_week_high", "52_week_low", "away_from_high", "away_from_low"
            ]
            df[float_cols] = df[float_cols].apply(pd.to_numeric, errors='coerce').fillna(0.0)

            # Parse the date column with inferred format for speed
            df["date"] = pd.to_datetime(df["date"], errors='coerce')

            # Replace infinite values in one go
            df.replace({float('inf'): 0.0, float('-inf'): 0.0}, inplace=True)

            logger.info(f"Constructed DataFrame with {len(df)} rows of precomputed weekly OHLC data.")
            return df
        except Exception as e:
            logger.error(f"Error in fetch_precomputed_weekly_ohlc: {e}", exc_info=True)
            raise e

