import logging

logger = logging.getLogger(__name__)

class SaveTradeDetails:
    def __init__(self, stock_name, token, entry_time, entry_price, stop_loss, target, 
                initial_qty, current_qty, booked_pnl, auto_exit=False):
        self.stock_name = stock_name
        self.token = token
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.target = target
        self.initial_qty = initial_qty
        self.current_qty = current_qty
        self.booked_pnl = booked_pnl
        self.auto_exit = auto_exit  # New boolean field

    def save(self, cur):
        query = """
            INSERT INTO trades 
            (stock_name, token, entry_time, entry_price, stop_loss, target, 
            initial_qty, current_qty, booked_pnl, auto_exit) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
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
                self.booked_pnl,
                self.auto_exit
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

    @classmethod
    def update_auto_exit(cls, cur, trade_id, new_auto_exit):
        """
        Updates the auto_exit flag for a given trade identified by trade_id.

        :param cur: Database cursor.
        :param trade_id: The ID of the trade to update.
        :param new_auto_exit: Boolean value to set for the auto_exit flag.
        """
        query = "UPDATE trades SET auto_exit = %s WHERE trade_id = %s;"
        try:
            cur.execute(query, (new_auto_exit, trade_id))
            logger.info(f"Updated auto_exit flag to {new_auto_exit} for trade_id: {trade_id}")
        except Exception as err:
            logger.error(f"Error updating auto_exit flag for trade_id {trade_id}: {err}")
            raise err