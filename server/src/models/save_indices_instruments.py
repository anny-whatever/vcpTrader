import logging

logger = logging.getLogger(__name__)

class IndicesInstruments:
    def __init__(self, instrument_token, exchange_token, tradingsymbol, name, last_price, expiry, strike, tick_size, lot_size, instrument_type, segment, exchange):
        self.instrument_token = instrument_token
        self.exchange_token = exchange_token
        self.tradingsymbol = tradingsymbol
        self.name = name
        self.last_price = last_price
        self.tick_size = tick_size
        self.instrument_type = instrument_type
        self.segment = segment
        self.exchange = exchange

    @classmethod
    def create_table(cls, cur):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS indices_instruments (
            instrument_token BIGINT PRIMARY KEY,
            exchange_token BIGINT,
            tradingsymbol VARCHAR(255),
            name VARCHAR(255),
            last_price DECIMAL,
            tick_size DECIMAL,
            instrument_type VARCHAR(255),
            segment VARCHAR(255),
            exchange VARCHAR(255)
        );
        """
        try:
            cur.execute(create_table_query)
            logger.info("Table indices_instruments created successfully (or already exists).")
        except Exception as e:
            logger.error(f"Error creating table indices_instruments: {e}")
            raise e

    @classmethod
    def select_all(cls, cur):
        select_query = """SELECT * FROM indices_instruments;"""
        try:
            cur.execute(select_query)
            results = cur.fetchall()
            return results
        except Exception as e:
            logger.error(f"Error selecting all from indices_instruments: {e}")
            raise e

    @classmethod
    def delete_all(cls, cur):
        delete_query = """DELETE FROM indices_instruments;"""
        try:
            cur.execute(delete_query)
            logger.info("All records from indices_instruments deleted.")
        except Exception as e:
            logger.error(f"Error deleting all from indices_instruments: {e}")
            raise e

    def save(self, cur):
        insert_query = """
        INSERT INTO indices_instruments (instrument_token, exchange_token, tradingsymbol, name, last_price, tick_size, instrument_type, segment, exchange)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (instrument_token) DO NOTHING;
        """
        try:
            cur.execute(insert_query, (
                self.instrument_token,
                self.exchange_token,
                self.tradingsymbol,
                self.name,
                self.last_price,
                self.tick_size,
                self.instrument_type,
                self.segment,
                self.exchange
            ))
        except Exception as e:
            logger.error(f"Error saving indices instrument: {e}")
            raise e
