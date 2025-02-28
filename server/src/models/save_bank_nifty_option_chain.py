class BankNiftyOptionChain:
    def __init__(self, instrument_token, exchange_token, tradingsymbol, name, last_price, expiry, strike, tick_size, lot_size, instrument_type, segment, exchange):
        self.instrument_token = instrument_token
        self.exchange_token = exchange_token
        self.tradingsymbol = tradingsymbol
        self.name = name
        self.last_price = last_price
        self.expiry = expiry
        self.strike = strike
        self.tick_size = tick_size
        self.lot_size = lot_size
        self.instrument_type = instrument_type
        self.segment = segment
        self.exchange = exchange

    @classmethod
    def create_table(cls, cur):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS bank_nifty_option_chain (
            instrument_token BIGINT PRIMARY KEY,
            exchange_token BIGINT,
            tradingsymbol VARCHAR(255),
            name VARCHAR(255),
            last_price DECIMAL,
            expiry DATE,
            strike DECIMAL,
            tick_size DECIMAL,
            lot_size INT,
            instrument_type VARCHAR(255),
            segment VARCHAR(255),
            exchange VARCHAR(255)
        );
        """
        cur.execute(create_table_query)
        
        
    @classmethod
    def select_all(cls, cur):
        select_query = """SELECT * FROM bank_nifty_option_chain;"""
        cur.execute(select_query)
        return cur.fetchall()
    
    @classmethod
    def select_by_expiry(cls, cur, instrument_token):
        select_query = """SELECT * FROM bank_nifty_option_chain WHERE expiry = %s;"""
        cur.execute(select_query, (instrument_token,))
        return cur.fetchall()
    
    @classmethod
    def select_by_strike_and_expiry(cls, cur, instrument_token, strike):
        select_query = """SELECT * FROM bank_nifty_option_chain WHERE strike = %s AND expiry = %s;"""
        cur.execute(select_query, (strike, instrument_token))
        return cur.fetchall()

    @classmethod
    def delete_all(cls, cur):
        delete_query = """DELETE FROM bank_nifty_option_chain;"""
        cur.execute(delete_query)

    def save(self, cur):
        insert_query = """INSERT INTO bank_nifty_option_chain (instrument_token, exchange_token, tradingsymbol, name, last_price, expiry, strike, tick_size, lot_size, instrument_type, segment, exchange) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (instrument_token) DO NOTHING;"""
        cur.execute(insert_query, (self.instrument_token, self.exchange_token, self.tradingsymbol, self.name, self.last_price, self.expiry, self.strike, self.tick_size, self.lot_size, self.instrument_type, self.segment, self.exchange))