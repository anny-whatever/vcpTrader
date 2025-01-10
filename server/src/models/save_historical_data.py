class HistoricalData:
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
        CREATE TABLE IF NOT EXISTS historical_data (
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
        cur.execute(create_table_query)
        
    @classmethod
    def select_by_token_and_interval(cls, cur, instrument_token, interval):
        select_query = """SELECT * FROM historical_data WHERE instrument_token = %s AND interval = %s;"""
        cur.execute(select_query, (instrument_token, interval))
        return cur.fetchall()
    
    @classmethod
    def select_by_token(cls, cur, instrument_token):
        select_query = """SELECT * FROM historical_data WHERE instrument_token = %s;"""
        cur.execute(select_query, (instrument_token,))
        return cur.fetchall()
    
    @classmethod
    def select_all(cls, cur):
        select_query = """SELECT * FROM historical_data;"""
        cur.execute(select_query)
        return cur.fetchall()
    
    @classmethod
    def delete_all(cls, cur, instrument_token, interval):
        delete_query = """DELETE FROM historical_data WHERE instrument_token = %s AND interval = %s;"""
        cur.execute(delete_query, (instrument_token, interval))

    def save(self, cur):
        insert_query = """
        INSERT INTO historical_data (instrument_token, symbol, interval, date, open, high, low, close, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(insert_query, (self.instrument_token, self.symbol, self.interval, self.date, self.open, self.high, self.low, self.close, self.volume))
