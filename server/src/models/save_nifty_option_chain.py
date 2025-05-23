import logging

logger = logging.getLogger(__name__)

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
        try:
            cur.execute(create_table_query)
            logger.info("Table nifty_option_chain created successfully (or already exists).")
        except Exception as e:
            logger.error(f"Error creating table nifty_option_chain: {e}")
            raise e
        
    @classmethod
    def select_all(cls, cur):
        select_query = "SELECT * FROM nifty_option_chain ORDER BY expiry ASC;"
        try:
            cur.execute(select_query)
            results = cur.fetchall()
            logger.info("Retrieved all records from nifty_option_chain successfully.")
            return results
        except Exception as e:
            logger.error(f"Error selecting all records from nifty_option_chain: {e}")
            raise e

    @classmethod
    def select_by_expiry(cls, cur, instrument_token):
        select_query = "SELECT * FROM nifty_option_chain WHERE expiry = %s ORDER BY strike ASC;"
        try:
            cur.execute(select_query, (instrument_token,))
            results = cur.fetchall()
            logger.info(f"Retrieved records from nifty_option_chain for expiry {instrument_token} successfully.")
            return results
        except Exception as e:
            logger.error(f"Error selecting records by expiry {instrument_token} from nifty_option_chain: {e}")
            raise e
    
    @classmethod
    def select_by_strike_and_expiry(cls, cur, expiry, strike):
        select_query = "SELECT * FROM nifty_option_chain WHERE strike = %s AND expiry = %s ORDER BY strike ASC;"
        try:
            cur.execute(select_query, (strike, expiry))
            results = cur.fetchall()
            logger.info(f"Retrieved records from nifty_option_chain for strike {strike} and expiry {expiry} successfully.")
            return results
        except Exception as e:
            logger.error(f"Error selecting records by strike {strike} and expiry {expiry} from nifty_option_chain: {e}")
            raise e

    @classmethod
    def select_by_expiry_and_type(cls, cur, expiry, instrument_type):
        select_query = "SELECT * FROM nifty_option_chain WHERE expiry = %s AND instrument_type = %s ORDER BY strike ASC;"
        try:
            cur.execute(select_query, (expiry, instrument_type))
            results = cur.fetchall()
            logger.info(f"Retrieved records from nifty_option_chain for expiry {expiry} and instrument_type {instrument_type} successfully.")
            return results
        except Exception as e:
            logger.error(f"Error selecting records by expiry {expiry} and instrument_type {instrument_type} from nifty_option_chain: {e}")
            raise e

    @classmethod
    def select_by_strike_and_expiry_and_type(cls, cur, expiry, strike, instrument_type):
        select_query = "SELECT * FROM nifty_option_chain WHERE strike = %s AND expiry = %s AND instrument_type = %s;"
        try:
            cur.execute(select_query, (strike, expiry, instrument_type))
            results = cur.fetchall()
            logger.info(f"Retrieved records from nifty_option_chain for strike {strike}, expiry {expiry} and instrument_type {instrument_type} successfully.")
            return results
        except Exception as e:
            logger.error(f"Error selecting records by strike {strike}, expiry {expiry} and instrument_type {instrument_type} from nifty_option_chain: {e}")
            raise e

    @classmethod
    def delete_all(cls, cur):
        delete_query = "DELETE FROM nifty_option_chain;"
        try:
            cur.execute(delete_query)
            logger.info("Deleted all records from nifty_option_chain successfully.")
        except Exception as e:
            logger.error(f"Error deleting records from nifty_option_chain: {e}")
            raise e

    def save(self, cur):
        insert_query = """
        INSERT INTO nifty_option_chain (instrument_token, exchange_token, tradingsymbol, name, last_price, expiry, strike, tick_size, lot_size, instrument_type, segment, exchange)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (instrument_token) DO NOTHING;
        """
        try:
            cur.execute(insert_query, (
                self.instrument_token, self.exchange_token, self.tradingsymbol, self.name,
                self.last_price, self.expiry, self.strike, self.tick_size, self.lot_size,
                self.instrument_type, self.segment, self.exchange
            ))

        except Exception as e:
            logger.error(f"Error saving NiftyOptionChain record with instrument_token {self.instrument_token}: {e}")
            raise e
