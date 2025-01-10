class HistoricalTrades:
    def __init__(self, strategy_type, entry_time, entry_price, exit_time, exit_price, qty, pnl):
        self.strategy_type = strategy_type
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.qty = qty
        self.pnl = pnl


    @classmethod
    def create_table(cls, cur):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS historical_trades (
            id SERIAL PRIMARY KEY,
            strategy_type VARCHAR(255),
            entry_time TIMESTAMPTZ,
            entry_price DECIMAL,
            exit_time TIMESTAMPTZ,
            exit_price DECIMAL,
            qty DECIMAL,
            pnl DECIMAL
            );
        """
        cur.execute(create_table_query)
    
    def insert_historical_trade(self, cur):
        query = """
        INSERT INTO historical_trades (strategy_type, entry_time, entry_price, exit_time, exit_price, qty, pnl)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(query, (self.strategy_type, self.entry_time, self.entry_price, self.exit_time, self.exit_price, self.qty, self.pnl))