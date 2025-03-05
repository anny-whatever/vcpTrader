import logging

logger = logging.getLogger(__name__)

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
            type VARCHAR(255),
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
            target_level DECIMAL,
            PRIMARY KEY (type, index)
        );
        """
        try:
            cur.execute(create_table_query)
            logger.info("Table fema_positions created successfully (or already exists).")
        except Exception as e:
            logger.error(f"Error creating table fema_positions: {e}")
            raise e

    @classmethod
    def create_table_flags(cls, cur):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS fema_flags (
            type VARCHAR(255),
            index VARCHAR(255),
            signal_candle_flag BOOLEAN,
            signal_candle_low DECIMAL,
            signal_candle_high DECIMAL,
            open_trade_flag BOOLEAN,
            trail_flag BOOLEAN,
            PRIMARY KEY (type, index)
        );
        """
        try:
            cur.execute(create_table_query)
            logger.info("Table fema_flags created successfully (or already exists).")
        except Exception as e:
            logger.error(f"Error creating table fema_flags: {e}")
            raise e

    def insert_trade_data(self, cur):
        try:
            insert_query = """
            INSERT INTO fema_positions (type, index, sell_strike_order_id, buy_strike_order_id, 
                sell_strike_entry_price, buy_strike_entry_price, sell_strike_instrument_token, 
                buy_strike_instrument_token, sell_strike_trading_symbol, buy_strike_trading_symbol, 
                expiry, qty, entry_time, entry_price, stop_loss_level, target_level)    
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT ON CONSTRAINT fema_positions_pkey
            DO UPDATE SET
                sell_strike_order_id = EXCLUDED.sell_strike_order_id,
                buy_strike_order_id = EXCLUDED.buy_strike_order_id,
                sell_strike_entry_price = EXCLUDED.sell_strike_entry_price,
                buy_strike_entry_price = EXCLUDED.buy_strike_entry_price,
                sell_strike_instrument_token = EXCLUDED.sell_strike_instrument_token,
                buy_strike_instrument_token = EXCLUDED.buy_strike_instrument_token,
                sell_strike_trading_symbol = EXCLUDED.sell_strike_trading_symbol,
                buy_strike_trading_symbol = EXCLUDED.buy_strike_trading_symbol,
                expiry = EXCLUDED.expiry,
                qty = EXCLUDED.qty,
                entry_time = EXCLUDED.entry_time,
                entry_price = EXCLUDED.entry_price,
                stop_loss_level = EXCLUDED.stop_loss_level,
                target_level = EXCLUDED.target_level;
            """
            cur.execute(insert_query, (
                self.type, self.index, self.sell_strike_order_id, self.buy_strike_order_id,
                self.sell_strike_entry_price, self.buy_strike_entry_price, self.sell_strike_instrument_token,
                self.buy_strike_instrument_token, self.sell_strike_trading_symbol, self.buy_strike_trading_symbol,
                self.expiry, self.qty, self.entry_time, self.entry_price, self.stop_loss_level, self.target_level
            ))
            logger.info(f"Inserted/Updated trade data for type {self.type} and index {self.index} successfully.")
        except Exception as e:
            logger.error(f"Error inserting trade data for type {self.type} and index {self.index}: {e}")
            raise e

    @classmethod
    def get_trade_data_by_type(cls, cur, type):
        """
        Retrieves all trade records for a given type.
        Since the type is not unique (primary key is (type, index)),
        this method might return multiple rows.
        """
        select_query = """
        SELECT index, sell_strike_order_id, buy_strike_order_id, sell_strike_entry_price, buy_strike_entry_price, 
               sell_strike_instrument_token, buy_strike_instrument_token, sell_strike_trading_symbol, 
               buy_strike_trading_symbol, expiry, qty, entry_time, entry_price, stop_loss_level, target_level 
        FROM fema_positions
        WHERE type = %s
        """
        cur.execute(select_query, (type,))
        results = cur.fetchall()
        logger.info(f"Retrieved trade data for type {type}.")
        return results

    @classmethod
    def get_trade_data_by_type_and_index(cls, cur, type, index):
        """
        Retrieves a single trade record using both type and index.
        """
        select_query = """
        SELECT index, sell_strike_order_id, buy_strike_order_id, sell_strike_entry_price, buy_strike_entry_price, 
               sell_strike_instrument_token, buy_strike_instrument_token, sell_strike_trading_symbol, 
               buy_strike_trading_symbol, expiry, qty, entry_time, entry_price, stop_loss_level, target_level 
        FROM fema_positions
        WHERE type = %s AND index = %s
        """
        cur.execute(select_query, (type, index))
        results = cur.fetchall()
        logger.info(f"Retrieved trade data for type {type} and index {index}.")
        return results

    @classmethod
    def delete_trade_data_by_type_and_index(cls, cur, type, index):
        """
        Deletes a specific trade record using both type and index.
        """
        delete_query = """
        DELETE FROM fema_positions
        WHERE type = %s AND index = %s
        """
        try:
            cur.execute(delete_query, (type, index))
            logger.info(f"Deleted trade data for type {type} and index {index} successfully.")
        except Exception as e:
            logger.error(f"Error deleting trade data for type {type} and index {index}: {e}")
            raise e

    @classmethod
    def set_flags(cls, cur, type, index, signal_candle_flag, open_trade_flag, signal_candle_low, signal_candle_high):
        update_query = """
        UPDATE fema_flags
        SET signal_candle_flag = %s, open_trade_flag = %s, signal_candle_low = %s, signal_candle_high = %s
        WHERE type = %s AND index = %s
        """
        try:
            cur.execute(update_query, (signal_candle_flag, open_trade_flag, signal_candle_low, signal_candle_high, type, index))
            logger.info(f"Updated flags for type {type} and index {index} successfully.")
        except Exception as e:
            logger.error(f"Error updating flags for type {type} and index {index}: {e}")
            raise e

    @classmethod
    def get_flags_by_type_and_index(cls, cur, type, index):
        select_query = """
        SELECT signal_candle_flag, signal_candle_low, signal_candle_high, open_trade_flag, trail_flag 
        FROM fema_flags
        WHERE type = %s AND index = %s
        """
        try:
            cur.execute(select_query, (type, index))
            results = cur.fetchall()
            logger.info(f"Retrieved flags for type {type} and index {index} successfully.")
            return results
        except Exception as e:
            logger.error(f"Error retrieving flags for type {type} and index {index}: {e}")
            raise e

    @classmethod
    def set_trail_flag(cls, cur, type, index, trail_flag):
        update_query = """
        UPDATE fema_flags
        SET trail_flag = %s
        WHERE type = %s AND index = %s
        """
        try:
            cur.execute(update_query, (trail_flag, type, index))
            logger.info(f"Updated trail flag for type {type} and index {index} successfully.")
        except Exception as e:
            logger.error(f"Error updating trail flag for type {type} and index {index}: {e}")
            raise e

    @classmethod
    def set_trailing_sl(cls, cur, type, index, trailing_sl):
        """
        Updates the trailing stop loss for a specific record identified by type and index.
        """
        update_query = """
        UPDATE fema_positions
        SET stop_loss_level = %s
        WHERE type = %s AND index = %s
        """
        try:
            cur.execute(update_query, (trailing_sl, type, index))
            logger.info(f"Updated trailing stop loss for type {type} and index {index} successfully.")
        except Exception as e:
            logger.error(f"Error updating trailing stop loss for type {type} and index {index}: {e}")
            raise e
