class FemaModel:
    
    def __init__(self, type, index, sell_strike_order_id, buy_strike_order_id, sell_strike_entry_price,
                 buy_strike_entry_price, sell_strike_instrument_token, buy_strike_instrument_token,
                 sell_strike_trading_symbol, buy_strike_trading_symbol, expiry, qty, entry_time,
                 entry_price, stop_loss_level, target_level):
        
        self.type = type
        self.index = index
        self.sell_strike_order_id = sell_strike_order_id
        self.buy_strike_order_id = buy_strike_order_id
        self.sell_strike_entry_price = sell_strike_entry_price
        self.buy_strike_entry_price = buy_strike_entry_price        
        self.sell_strike_instrument_token = sell_strike_instrument_token
        self.buy_strike_instrument_token = buy_strike_instrument_token
        self.sell_strike_trading_symbol = sell_strike_trading_symbol        
        self.buy_strike_trading_symbol = buy_strike_trading_symbol
        self.expiry = expiry
        self.qty = qty
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.stop_loss_level = stop_loss_level
        self.target_level = target_level

    @classmethod
    def create_table_positions(cls, cur):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS fema_positions ( 
            type VARCHAR(255) PRIMARY KEY,
            index VARCHAR(255),
            sell_strike_order_id VARCHAR(255),
            buy_strike_order_id VARCHAR(255),
            sell_strike_entry_price DECIMAL,
            buy_strike_entry_price DECIMAL,
            sell_strike_instrument_token BIGINT,
            buy_strike_instrument_token BIGINT,                
            sell_strike_trading_symbol VARCHAR(255),
            buy_strike_trading_symbol VARCHAR(255),
            expiry TIMESTAMPTZ,
            qty DECIMAL,
            entry_time TIMESTAMPTZ,
            entry_price DECIMAL,
            stop_loss_level DECIMAL,
            target_level DECIMAL
        );
        """
        cur.execute(create_table_query)

    @classmethod
    def create_table_flags(cls, cur):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS fema_flags (
            type VARCHAR(255) PRIMARY KEY,
            index VARCHAR(255),
            signal_candle_flag BOOLEAN,
            signal_candle_low DECIMAL,
            signal_candle_high DECIMAL,
            open_trade_flag BOOLEAN,
            trail_flag BOOLEAN
        );
        """
        cur.execute(create_table_query)

    def insert_trade_data(self, cur):
        try:
            insert_query = """
            INSERT INTO fema_positions (type, index, sell_strike_order_id, buy_strike_order_id, 
                sell_strike_entry_price, buy_strike_entry_price, sell_strike_instrument_token, 
                buy_strike_instrument_token, sell_strike_trading_symbol, buy_strike_trading_symbol, 
                expiry, qty, entry_time, entry_price, stop_loss_level, target_level)    
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.execute(insert_query, (
                self.type, self.index, self.sell_strike_order_id, self.buy_strike_order_id,
                self.sell_strike_entry_price, self.buy_strike_entry_price, self.sell_strike_instrument_token,
                self.buy_strike_instrument_token, self.sell_strike_trading_symbol, self.buy_strike_trading_symbol,
                self.expiry, self.qty, self.entry_time, self.entry_price, self.stop_loss_level, self.target_level
            ))
        except Exception as e:
            print(f"Error inserting trade data: {e}")

    @classmethod
    def get_trade_data_by_type(cls, cur, type):
        select_query = """
        SELECT sell_strike_order_id, buy_strike_order_id, sell_strike_entry_price, buy_strike_entry_price, 
               sell_strike_instrument_token, buy_strike_instrument_token, sell_strike_trading_symbol, 
               buy_strike_trading_symbol, expiry, qty, entry_time, entry_price, stop_loss_level, target_level 
        FROM fema_positions
        WHERE type = %s
        """
        cur.execute(select_query, (type,))
        return cur.fetchall()

    @classmethod
    def delete_trade_data_by_type(cls, cur, type):
        delete_query = """
        DELETE FROM fema_positions
        WHERE type = %s
        """
        cur.execute(delete_query, (type,))

    @classmethod
    def set_flags(cls, cur, type, signal_candle_flag, open_trade_flag, signal_candle_low, signal_candle_high):
        update_query = """
        UPDATE fema_flags
        SET signal_candle_flag = %s, open_trade_flag = %s, signal_candle_low = %s, signal_candle_high = %s
        WHERE type = %s
        """
        cur.execute(update_query, (signal_candle_flag, open_trade_flag, signal_candle_low, signal_candle_high, type))

    @classmethod
    def get_flags_by_type(cls, cur, type):
        select_query = """
        SELECT signal_candle_flag, signal_candle_low, signal_candle_high, open_trade_flag, trail_flag 
        FROM fema_flags
        WHERE type = %s
        """
        cur.execute(select_query, (type,))
        return cur.fetchall()

    @classmethod
    def set_trail_flag(cls, cur, type, trail_flag):
        update_query = """
        UPDATE fema_flags
        SET trail_flag = %s
        WHERE type = %s
        """
        cur.execute(update_query, (trail_flag, type))

    @classmethod
    def set_trailing_sl(cls, cur, type, trailing_sl):
        update_query = """
        UPDATE fema_positions
        SET stop_loss_level = %s
        WHERE type = %s
        """
        cur.execute(update_query, (trailing_sl, type))
