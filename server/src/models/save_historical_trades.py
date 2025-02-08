import logging

logger = logging.getLogger(__name__)

class SaveHistoricalTradeDetails:
    def __init__(self, stock_name, entry_time, entry_price, exit_time, exit_price, final_pnl, highest_qty):
        self.stock_name = stock_name
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.final_pnl = final_pnl
        self.highest_qty = highest_qty

    def save(self, cur):
        try:
            query = """
                INSERT INTO historical_trades 
                (stock_name, entry_time, entry_price, exit_time, exit_price, final_pnl, highest_qty) 
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """
            cur.execute(query, (
                self.stock_name,
                self.entry_time,
                self.entry_price,
                self.exit_time,
                self.exit_price,
                self.final_pnl,
                self.highest_qty
            ))
            logger.info("Historical trade saved successfully.")
        except Exception as e:
            logger.error(f"Error saving historical trade details: {e}")
            raise e

    @classmethod
    def fetch_all_historical_trades(cls, cur):
        try:
            query = "SELECT * FROM historical_trades;"
            cur.execute(query)
            result = cur.fetchall()
            logger.info("Fetched all historical trades successfully.")
            return result
        except Exception as e:
            logger.error(f"Error fetching all historical trades: {e}")
            raise e
