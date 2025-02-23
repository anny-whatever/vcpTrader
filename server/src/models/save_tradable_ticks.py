import json
import logging

logger = logging.getLogger(__name__)

class TradableTicks:
    def __init__(self, instrument_token, last_price, last_traded_quantity, average_traded_price, 
                 volume_traded, total_buy_quantity, total_sell_quantity, change, last_trade_time, 
                 exchange_timestamp):
        self.instrument_token = instrument_token
        self.last_price = last_price
        self.last_traded_quantity = last_traded_quantity
        self.average_traded_price = average_traded_price
        self.volume_traded = volume_traded
        self.total_buy_quantity = total_buy_quantity
        self.total_sell_quantity = total_sell_quantity
        self.change = change
        self.last_trade_time = last_trade_time
        self.exchange_timestamp = exchange_timestamp

    @classmethod
    def create_table(cls, cur):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS tradable_ticks (
            id SERIAL PRIMARY KEY,
            instrument_token BIGINT,
            last_price DECIMAL,
            last_traded_quantity DECIMAL,
            average_traded_price DECIMAL,
            volume_traded DECIMAL,
            total_buy_quantity DECIMAL,
            total_sell_quantity DECIMAL,
            change DECIMAL,
            last_trade_time TIMESTAMPTZ,
            exchange_timestamp TIMESTAMPTZ
        );
        """
        try:
            cur.execute(create_table_query)
            logger.info("Created tradable_ticks table successfully.")
        except Exception as e:
            logger.error(f"Error creating tradable_ticks table: {e}")
            raise

    @classmethod
    def select_all(cls, cur):
        select_query = "SELECT * FROM tradable_ticks;"
        try:
            cur.execute(select_query)
            rows = cur.fetchall()
            logger.info("Fetched all records from tradable_ticks table.")
            return rows
        except Exception as e:
            logger.error(f"Error selecting tradable ticks: {e}")
            raise

    @classmethod
    def delete_all(cls, cur):
        delete_query = "DELETE FROM tradable_ticks;"
        try:
            cur.execute(delete_query)
            logger.info("Deleted all records from tradable_ticks table.")
        except Exception as e:
            logger.error(f"Error deleting tradable ticks: {e}")
            raise

    def save(self, cur):
        insert_query = """
        INSERT INTO tradable_ticks (
            instrument_token, last_price, last_traded_quantity, average_traded_price, 
            volume_traded, total_buy_quantity, total_sell_quantity, change, last_trade_time, 
            exchange_timestamp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            self.instrument_token,
            self.last_price,
            self.last_traded_quantity,
            self.average_traded_price,
            self.volume_traded,
            self.total_buy_quantity,
            self.total_sell_quantity,
            self.change,
            self.last_trade_time.isoformat(),
            self.exchange_timestamp.isoformat()
        )
        try:
            cur.execute(insert_query, values)
        except Exception as e:
            logger.error(f"Error saving tradable tick: {e}")
            raise

    @classmethod
    def save_batch(cls, cur, ticks):
        """
        Batch insert tradable ticks using the provided database cursor.
        :param cur: Database cursor.
        :param ticks: List of tick dictionaries.
        """
        insert_query = """
        INSERT INTO tradable_ticks (
            instrument_token, last_price, last_traded_quantity, average_traded_price, 
            volume_traded, total_buy_quantity, total_sell_quantity, change, last_trade_time, 
            exchange_timestamp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        data_to_insert = []
        for tick in ticks:
            if tick.get('tradable'):
                last_trade_time = tick['last_trade_time'].isoformat() if hasattr(tick['last_trade_time'], 'isoformat') else tick['last_trade_time']
                exchange_timestamp = tick['exchange_timestamp'].isoformat() if hasattr(tick['exchange_timestamp'], 'isoformat') else tick['exchange_timestamp']
                data_to_insert.append((
                    tick['instrument_token'],
                    tick['last_price'],
                    tick['last_traded_quantity'],
                    tick['average_traded_price'],
                    tick['volume_traded'],
                    tick['total_buy_quantity'],
                    tick['total_sell_quantity'],
                    tick['change'],
                    last_trade_time,
                    exchange_timestamp
                ))
        if data_to_insert:
            try:
                cur.executemany(insert_query, data_to_insert)
            except Exception as e:
                logger.error(f"Error in batch saving tradable ticks: {e}")
                raise
