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
    def fetch_by_instrument(cls, cursor, instrument_token):
        """
        Fetches OHLC rows (plus indicator columns) from the 'ohlc' table
        for a given instrument_token (with interval='day' as an example).
        """
        try:
            cursor.execute("""
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
                ORDER BY date ASC
            """, (instrument_token,))
            results = cursor.fetchall()
            logger.info(f"Fetched OHLC data for instrument_token: {instrument_token}")
            return results
        except Exception as e:
            logger.error(f"Error fetching OHLC data for instrument_token {instrument_token}: {e}")
            raise e

    @classmethod
    def fetch_precomputed_ohlc(cls, cur, limit=200):
        """
        Fetch the last `limit` rows per symbol from `ohlc`, including
        precomputed columns (sma_50, sma_150, sma_200, atr, "52_week_high", etc.).
        
        Uses a window function (ROW_NUMBER) over (PARTITION BY symbol ORDER BY date DESC).
        After computing row_number, we filter rows where rn <= limit.
        
        Returns a pandas DataFrame with all those rows combined.
        """
        logger.info(f"Fetching up to {limit} rows of precomputed OHLC+Indicators per symbol from DB...")

        query = f"""
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
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY date DESC) AS rn
                FROM ohlc
                WHERE segment != 'ALL'
            ) sub
            WHERE rn <= {limit};
        """

        try:
            logger.debug("About to execute window function query for precomputed OHLC...")
            logger.debug(f"Window function query:\n{query}")
            cur.execute(query)
            logger.debug("Query executed successfully; now fetching rows from DB cursor...")
            rows = cur.fetchall()
            logger.debug(f"Fetched {len(rows)} rows from `ohlc` table (for all symbols).")

            # If no rows, return an empty DataFrame quickly
            if not rows:
                logger.warning("No rows returned from fetch_precomputed_ohlc. Returning empty DataFrame.")
                return pd.DataFrame()

            logger.debug("Constructing DataFrame from fetched rows...")
            columns = [
                "instrument_token",
                "symbol",
                "interval",
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "segment",
                "sma_50",
                "sma_150",
                "sma_200",
                "atr",
                "52_week_high",
                "52_week_low",
                "away_from_high",
                "away_from_low"
            ]
            try:
                df = pd.DataFrame(rows, columns=columns)
            except Exception as e:
                logger.error(f"Error constructing DataFrame from DB rows: {e}")
                return pd.DataFrame()

            logger.info(f"Constructed DataFrame with {len(df)} rows of precomputed OHLC data.")
            
            # Convert numeric columns to float, where applicable
            float_cols = [
                "open","high","low","close","volume","sma_50","sma_150","sma_200","atr",
                "52_week_high","52_week_low","away_from_high","away_from_low"
            ]
            logger.debug("Attempting to convert numeric columns to float...")
            for col in float_cols:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
                except Exception as e:
                    logger.error(f"Error converting column '{col}' to numeric: {e}")
                    # You can decide whether to keep going or raise; here, we keep going

            logger.debug("Numeric column conversion complete. Attempting to parse 'date' column as datetime...")
            try:
                df["date"] = pd.to_datetime(df["date"], errors='coerce')
            except Exception as e:
                logger.error(f"Error converting 'date' column to datetime: {e}")
                # If needed, set df["date"] to pd.NaT or continue

            logger.debug("Replacing infinite values with 0.0 if any exist...")
            df.replace([float('inf'), float('-inf')], 0.0, inplace=True)

            logger.info(f"Final DataFrame shape after cleanup: {df.shape}")
            logger.debug(f"DataFrame columns after cleanup: {df.dtypes}")

            return df

        except Exception as e:
            logger.error(f"Error in fetch_precomputed_ohlc: {e}", exc_info=True)
            # Return an empty DataFrame if there's a critical error
            return pd.DataFrame()
