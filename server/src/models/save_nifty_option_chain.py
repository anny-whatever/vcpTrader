class NiftyOptionChain:
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
        CREATE TABLE IF NOT EXISTS nifty_option_chain (
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
        select_query = """SELECT * FROM nifty_option_chain ORDER BY expiry ASC;"""
        cur.execute(select_query)
        return cur.fetchall()

    @classmethod
    def select_by_expiry(cls, cur, instrument_token):
        select_query = """SELECT * FROM nifty_option_chain WHERE expiry = %s ORDER BY strike ASC;"""
        cur.execute(select_query, (instrument_token,))
        return cur.fetchall()
    
    @classmethod
    def select_by_strike_and_expiry(cls, cur, expiry, strike):
        select_query = """SELECT * FROM nifty_option_chain WHERE strike = %s AND expiry = %s ORDER BY strike ASC;"""
        cur.execute(select_query, (strike, expiry))
        return cur.fetchall()
    
    @classmethod
    def select_by_expiry_and_type(cls, cur, expiry, instrument_type):
        select_query = """SELECT * FROM nifty_option_chain WHERE expiry = %s AND instrument_type = %s ORDER BY strike ASC;"""
        cur.execute(select_query, (expiry, instrument_type))
        return cur.fetchall()
    
    @classmethod
    def select_by_strike_and_expiry_and_type(cls, cur, expiry, strike, instrument_type):
        select_query = """SELECT * FROM nifty_option_chain WHERE strike = %s AND expiry = %s AND instrument_type = %s;"""
        cur.execute(select_query, (strike, expiry, instrument_type))
        return cur.fetchall()
    
    

    @classmethod
    def delete_all(cls, cur):
        delete_query = """DELETE FROM nifty_option_chain;"""
        cur.execute(delete_query)

    def save(self, cur):
        insert_query = """
        INSERT INTO nifty_option_chain (instrument_token, exchange_token, tradingsymbol, name, last_price, expiry, strike, tick_size, lot_size, instrument_type, segment, exchange)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (instrument_token) DO NOTHING;
        """
        cur.execute(insert_query, (self.instrument_token, self.exchange_token, self.tradingsymbol, self.name, self.last_price, self.expiry, self.strike, self.tick_size, self.lot_size, self.instrument_type, self.segment, self.exchange))