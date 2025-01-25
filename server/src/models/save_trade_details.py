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
        try:
            query = """INSERT INTO trades (stock_name, token, entry_time, entry_price, stop_loss, target, initial_qty, current_qty, booked_pnl) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);"""
            cur.execute(query, (self.stock_name, self.token, self.entry_time, self.entry_price, self.stop_loss, self.target, self.initial_qty, self.current_qty, self.booked_pnl))
        except Exception as err:
            print(f"Error saving trade details: {str(err)}")
            return {"error": str(err)}

    @classmethod
    def fetch_all_trades(cls, cur):
        try:
            query = "SELECT * FROM trades;"
            cur.execute(query)
            result = cur.fetchall()
            return result
        except Exception as err:
            print(f"Error fetching all trades: {str(err)}")
            return None