import logging

logger = logging.getLogger(__name__)

class HistoricalVirtualTrades:
    def __init__(self, strategy_type, index, entry_time, entry_price, exit_time, exit_price, qty, pnl):
        self.strategy_type = strategy_type
        self.index = index
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.qty = qty
        self.pnl = pnl

    @classmethod
    def create_table(cls, cur):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS historical_virtual_trades (
            id SERIAL PRIMARY KEY,
            strategy_type VARCHAR(255),
            index VARCHAR(255),
            entry_time TIMESTAMPTZ,
            entry_price DECIMAL,
            exit_time TIMESTAMPTZ,
            exit_price DECIMAL,
            qty DECIMAL,
            pnl DECIMAL
        );
        """
        try:
            cur.execute(create_table_query)
            logger.info("Table historical_virtual_trades created successfully (or already exists).")
        except Exception as e:
            logger.error(f"Error creating table historical_virtual_trades: {e}")
            raise e

    def insert_virtual_trade(self, cur):
        insert_query = """
        INSERT INTO historical_virtual_trades (
            strategy_type, index, entry_time, entry_price, exit_time, exit_price, qty, pnl
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        try:
            cur.execute(insert_query, (
                self.strategy_type,
                self.index,
                self.entry_time,
                self.entry_price,
                self.exit_time,
                self.exit_price,
                self.qty,
                self.pnl
            ))
            logger.info(f"Inserted historical virtual trade record for strategy_type {self.strategy_type} and index {self.index} successfully.")
        except Exception as e:
            logger.error(f"Error inserting historical virtual trade record for strategy_type {self.strategy_type} and index {self.index}: {e}")
            raise e
