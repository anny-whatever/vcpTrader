import json
import logging

logger = logging.getLogger(__name__)

class NonTradableTicks:
    def __init__(self, instrument_token, last_price, change, exchange_timestamp):
        self.instrument_token = instrument_token
        self.last_price = last_price
        self.change = change
        self.exchange_timestamp = exchange_timestamp

    @classmethod
    def create_table(cls, cur):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS nontradable_ticks (
            id SERIAL PRIMARY KEY,
            instrument_token BIGINT,
            last_price DECIMAL,
            change DECIMAL,
            exchange_timestamp TIMESTAMPTZ
        );
        """
        try:
            cur.execute(create_table_query)
            logger.info("Created nontradable_ticks table successfully.")
        except Exception as e:
            logger.error(f"Error creating nontradable_ticks table: {e}")
            raise

    @classmethod
    def select_all(cls, cur):
        select_query = "SELECT * FROM nontradable_ticks;"
        try:
            cur.execute(select_query)
            rows = cur.fetchall()
            logger.info("Fetched all records from nontradable_ticks table.")
            return rows
        except Exception as e:
            logger.error(f"Error selecting nontradable ticks: {e}")
            raise

    @classmethod
    def delete_all(cls, cur):
        delete_query = "DELETE FROM nontradable_ticks;"
        try:
            cur.execute(delete_query)
            logger.info("Deleted all records from nontradable_ticks table.")
        except Exception as e:
            logger.error(f"Error deleting nontradable ticks: {e}")
            raise

    def save(self, cur):
        insert_query = """
        INSERT INTO nontradable_ticks (
            instrument_token, last_price, change, exchange_timestamp
        )
        VALUES (%s, %s, %s, %s)
        """
        values = (
            self.instrument_token,
            self.last_price,
            self.change,
            self.exchange_timestamp.isoformat()
        )
        try:
            cur.execute(insert_query, values)
        except Exception as e:
            logger.error(f"Error saving nontradable tick: {e}")
            raise

    @classmethod
    def save_batch(cls, cur, ticks):
        """
        Batch insert nontradable ticks using the provided database cursor.
        :param cur: Database cursor.
        :param ticks: List of tick dictionaries.
        """
        insert_query = """
        INSERT INTO nontradable_ticks (
            instrument_token, last_price, change, exchange_timestamp
        )
        VALUES (%s, %s, %s, %s)
        """
        data_to_insert = []
        for tick in ticks:
            if not tick.get('tradable'):
                exchange_timestamp = tick['exchange_timestamp'].isoformat() if hasattr(tick['exchange_timestamp'], 'isoformat') else tick['exchange_timestamp']
                data_to_insert.append((
                    tick['instrument_token'],
                    tick['last_price'],
                    tick['change'],
                    exchange_timestamp
                ))
        if data_to_insert:
            try:
                cur.executemany(insert_query, data_to_insert)
            except Exception as e:
                logger.error(f"Error in batch saving nontradable ticks: {e}")
                raise
