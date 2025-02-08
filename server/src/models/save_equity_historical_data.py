import logging

logger = logging.getLogger(__name__)

class EquityHistoricalData:
    def __init__(self, instrument_token, symbol, interval, date, open, high, low, close, volume):
        self.instrument_token = instrument_token
        self.symbol = symbol
        self.interval = interval
        self.date = date
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume

    @classmethod
    def create_table(cls, cur):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS equity_historical_data (
            instrument_token BIGINT,
            symbol VARCHAR(255),
            interval VARCHAR(255),
            date TIMESTAMPTZ,
            open DECIMAL,
            high DECIMAL,
            low DECIMAL,
            close DECIMAL,
            volume DECIMAL
        );
        """
        try:
            cur.execute(create_table_query)
            logger.info("Table equity_historical_data created successfully (or already exists).")
        except Exception as e:
            logger.error(f"Error creating table equity_historical_data: {e}")
            raise e

    @classmethod
    def select_by_token_and_interval(cls, cur, instrument_token, interval):
        select_query = """SELECT * FROM equity_historical_data WHERE instrument_token = %s AND interval = %s;"""
        try:
            cur.execute(select_query, (instrument_token, interval))
            results = cur.fetchall()
            return results
        except Exception as e:
            logger.error(f"Error selecting equity_historical_data by token and interval: {e}")
            raise e

    @classmethod
    def select_by_token(cls, cur, instrument_token):
        select_query = """SELECT * FROM equity_historical_data WHERE instrument_token = %s;"""
        try:
            cur.execute(select_query, (instrument_token,))
            results = cur.fetchall()
            return results
        except Exception as e:
            logger.error(f"Error selecting equity_historical_data by token: {e}")
            raise e

    @classmethod
    def select_all(cls, cur):
        select_query = """SELECT * FROM equity_historical_data;"""
        try:
            cur.execute(select_query)
            results = cur.fetchall()
            return results
        except Exception as e:
            logger.error(f"Error selecting all from equity_historical_data: {e}")
            raise e

    @classmethod
    def delete_all(cls, cur, instrument_token, interval):
        delete_query = """DELETE FROM equity_historical_data WHERE instrument_token = %s AND interval = %s;"""
        try:
            cur.execute(delete_query, (instrument_token, interval))
            logger.info(f"Deleted records from equity_historical_data for token {instrument_token} and interval {interval}.")
        except Exception as e:
            logger.error(f"Error deleting records from equity_historical_data: {e}")
            raise e

    def save(self, cur):
        insert_query = """
        INSERT INTO equity_historical_data (instrument_token, symbol, interval, date, open, high, low, close, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            cur.execute(insert_query, (
                self.instrument_token,
                self.symbol,
                self.interval,
                self.date,
                self.open,
                self.high,
                self.low,
                self.close,
                self.volume
            ))
            logger.info(f"Saved equity historical data for instrument_token: {self.instrument_token}")
        except Exception as e:
            logger.error(f"Error saving equity historical data: {e}")
            raise e
