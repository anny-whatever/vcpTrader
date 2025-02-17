import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WatchlistEntry:
    def __init__(self, user_id, watchlist_name, instrument_token, symbol, added_at=None):
        self.user_id = user_id
        self.watchlist_name = watchlist_name
        self.instrument_token = instrument_token
        self.symbol = symbol
        self.added_at = added_at if added_at else datetime.now()

    @classmethod
    def create_table(cls, cur):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS watchlist (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            watchlist_name VARCHAR(255) NOT NULL,
            instrument_token BIGINT NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, watchlist_name, instrument_token),
            FOREIGN KEY (instrument_token) REFERENCES equity_tokens(instrument_token)
        );
        """
        try:
            cur.execute(create_table_query)
            logger.info("Table 'watchlist' created successfully (or already exists).")
        except Exception as e:
            logger.error(f"Error creating table 'watchlist': {e}")
            raise

    def save(self, cur):
        insert_query = """
        INSERT INTO watchlist (user_id, watchlist_name, instrument_token, symbol, added_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id, watchlist_name, instrument_token) DO NOTHING;
        """
        try:
            cur.execute(insert_query, (
                self.user_id,
                self.watchlist_name,
                self.instrument_token,
                self.symbol,
                self.added_at
            ))
        except Exception as e:
            logger.error(f"Error saving watchlist entry: {e}")
            raise

    @classmethod
    def get_by_user_and_instrument(cls, cur, user_id, watchlist_name, instrument_token):
        query = """
        SELECT * FROM watchlist 
        WHERE user_id = %s AND watchlist_name = %s AND instrument_token = %s;
        """
        try:
            cur.execute(query, (user_id, watchlist_name, instrument_token))
            return cur.fetchone()
        except Exception as e:
            logger.error(f"Error in get_by_user_and_instrument: {e}")
            raise

    @classmethod
    def fetch_by_user_and_list(cls, cur, user_id, watchlist_name):
        query = "SELECT * FROM watchlist WHERE user_id = %s AND watchlist_name = %s;"
        try:
            cur.execute(query, (user_id, watchlist_name))
            return cur.fetchall()
        except Exception as e:
            logger.error(f"Error fetching watchlist entries: {e}")
            raise

    @classmethod
    def delete_by_user_and_instrument(cls, cur, user_id, watchlist_name, instrument_token):
        query = """
        DELETE FROM watchlist 
        WHERE user_id = %s AND watchlist_name = %s AND instrument_token = %s
        RETURNING id;
        """
        try:
            cur.execute(query, (user_id, watchlist_name, instrument_token))
            result = cur.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"Error deleting watchlist entry: {e}")
            raise
