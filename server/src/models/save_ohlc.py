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
        try:
            query = """
                INSERT INTO ohlc 
                (instrument_token, symbol, interval, date, open, high, low, close, volume) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
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
            print("OHLC saved to ohlc successfully.")
        except Exception as e:
            print(f"Error saving to ohlc: {str(e)}")
            
    @classmethod
    def select_token(cls, cur):
        try:
            query = "SELECT * FROM equity_tokens;"
            
            cur.execute(query)
            tokens = cur.fetchall()
            
            return tokens
        except Exception as e:
            print(f"Error selecting token: {str(e)}")
            return None
    
    @classmethod
    def delete_all(cls, cur, instrument_token, interval):
        delete_query = """DELETE FROM ohlc WHERE instrument_token = %s AND interval = %s;"""
        cur.execute(delete_query, (instrument_token, interval))
    
    @classmethod
    def fetch_by_instrument(cls, cursor, instrument_token):
        cursor.execute("""
            SELECT * FROM ohlc 
            WHERE instrument_token = %s 
            AND interval = 'day'
            ORDER BY date ASC
        """, (instrument_token,))
        return cursor.fetchall()