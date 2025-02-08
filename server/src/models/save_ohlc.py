import logging

logger = logging.getLogger(__name__)

class SaveOHLC:
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

    def save(self, cur):
        query = """
        INSERT INTO ohlc 
        (instrument_token, symbol, interval, date, open, high, low, close, volume) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
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
            ))
            logger.info(f"OHLC data saved for instrument_token: {self.instrument_token}")
        except Exception as e:
            logger.error(f"Error saving OHLC data: {e}")
            raise e
            
    @classmethod
    def select_token(cls, cur):
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
        delete_query = """DELETE FROM ohlc WHERE instrument_token = %s AND interval = %s;"""
        try:
            cur.execute(delete_query, (instrument_token, interval))
            logger.info(f"Deleted OHLC records for instrument_token: {instrument_token} and interval: {interval}")
        except Exception as e:
            logger.error(f"Error deleting OHLC data: {e}")
            raise e
    
    @classmethod
    def fetch_by_instrument(cls, cursor, instrument_token):
        try:
            cursor.execute("""
                SELECT * FROM ohlc 
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
