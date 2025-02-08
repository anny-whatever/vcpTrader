import logging

logger = logging.getLogger(__name__)

class SaveTradeDetails:
    def __init__(self, stock_name, token, entry_time, entry_price, stop_loss, target, initial_qty, current_qty, booked_pnl):
        self.stock_name = stock_name
        self.token = token
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.target = target
        self.initial_qty = initial_qty
        self.current_qty = current_qty
        self.booked_pnl = booked_pnl

    def save(self, cur):
        query = """INSERT INTO trades (stock_name, token, entry_time, entry_price, stop_loss, target, initial_qty, current_qty, booked_pnl) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);"""
        try:
            cur.execute(query, (
                self.stock_name,
                self.token,
                self.entry_time,
                self.entry_price,
                self.stop_loss,
                self.target,
                self.initial_qty,
                self.current_qty,
                self.booked_pnl
            ))
            logger.info(f"Trade details saved for stock: {self.stock_name}")
        except Exception as err:
            logger.error(f"Error saving trade details: {err}")
            raise err

    @classmethod
    def fetch_all_trades(cls, cur):
        query = "SELECT * FROM trades;"
        try:
            cur.execute(query)
            result = cur.fetchall()
            logger.info("Fetched all trade details successfully.")
            return result
        except Exception as err:
            logger.error(f"Error fetching all trades: {err}")
            raise err
