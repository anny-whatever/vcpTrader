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
            print("Trade saved to historical_trades successfully.")
        except Exception as e:
            print(f"Error saving to historical_trades: {str(e)}")
