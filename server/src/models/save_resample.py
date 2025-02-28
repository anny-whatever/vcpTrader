import logging

logger = logging.getLogger(__name__)

class SaveResample:
    """
    Manages the single 'ohlc_resampled' table for storing 1/5/15-minute data.
    """
    @classmethod
    def create_table_ohlc_resampled(cls, cur):
        """
        Create a single table to store all resampled OHLC data (1/5/15-min),
        for multiple instrument_tokens, with an 'interval' column.
        """
        try:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS ohlc_resampled (
                instrument_token BIGINT,
                time_stamp TIMESTAMPTZ,
                open DECIMAL,
                high DECIMAL,
                low DECIMAL,
                close DECIMAL,
                interval VARCHAR(10)
            );
            """
            cur.execute(create_table_query)
            logger.info("Created 'ohlc_resampled' table if not exists.")
        except Exception as e:
            cur.connection.rollback()
            logger.error(f"Error creating ohlc_resampled table: {e}")
            raise

    @classmethod
    def save_ohlc_resampled(cls, cur,
                            instrument_token, time_stamp,
                            open_price, high_price,
                            low_price, close_price,
                            interval):
        """
        Insert a single row of resampled data (1/5/15-min) into 'ohlc_resampled'.
        """
        try:
            insert_query = """
            INSERT INTO ohlc_resampled
            (instrument_token, time_stamp, open, high, low, close, interval)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(insert_query,
                        (instrument_token, time_stamp,
                         open_price, high_price,
                         low_price, close_price,
                         interval))
        except Exception as e:
            cur.connection.rollback()
            logger.error(f"Error saving resampled data: {e}")
            raise
