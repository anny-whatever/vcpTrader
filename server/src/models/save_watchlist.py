import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WatchlistEntry:
    def __init__(self, watchlist_name, instrument_token, symbol, added_at=None):
        self.watchlist_name = watchlist_name
        self.instrument_token = instrument_token
        self.symbol = symbol
        self.added_at = added_at if added_at else datetime.now()

    @classmethod
    def create_table(cls, cur):
        # No ON DELETE CASCADE, so watchlist doesn't get wiped out on reload
        create_table_query = """
        CREATE TABLE IF NOT EXISTS watchlist (
            id SERIAL PRIMARY KEY,
            watchlist_name VARCHAR(255) NOT NULL,
            instrument_token BIGINT NOT NULL,
            symbol VARCHAR(50) NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (watchlist_name, instrument_token),
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
        INSERT INTO watchlist (watchlist_name, instrument_token, symbol, added_at)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (watchlist_name, instrument_token) DO NOTHING;
        """
        try:
            cur.execute(insert_query, (
                self.watchlist_name,
                self.instrument_token,
                self.symbol,
                self.added_at
            ))
        except Exception as e:
            logger.error(f"Error saving watchlist entry: {e}")
            raise

    @classmethod
    def get_by_instrument(cls, cur, watchlist_name, instrument_token):
        query = """
        SELECT * FROM watchlist
        WHERE watchlist_name = %s AND instrument_token = %s;
        """
        try:
            cur.execute(query, (watchlist_name, instrument_token))
            row = cur.fetchone()
            if row:
                col_names = [desc[0] for desc in cur.description]
                result = dict(zip(col_names, row))
                # Convert datetime fields to ISO string
                if isinstance(result.get("added_at"), datetime):
                    result["added_at"] = result["added_at"].isoformat()
                return result
            return None
        except Exception as e:
            logger.error(f"Error in get_by_instrument: {e}")
            raise

    @classmethod
    def fetch_by_list(cls, cur, watchlist_name):
        query = "SELECT * FROM watchlist WHERE watchlist_name = %s;"
        try:
            cur.execute(query, (watchlist_name,))
            rows = cur.fetchall()
            col_names = [desc[0] for desc in cur.description]
            results = []
            for row in rows:
                row_dict = dict(zip(col_names, row))
                # Convert datetime fields to ISO string
                if isinstance(row_dict.get("added_at"), datetime):
                    row_dict["added_at"] = row_dict["added_at"].isoformat()
                results.append(row_dict)
            return results
        except Exception as e:
            logger.error(f"Error fetching watchlist entries: {e}")
            raise

    @classmethod
    def delete_by_instrument(cls, cur, watchlist_name, instrument_token):
        query = """
        DELETE FROM watchlist 
        WHERE watchlist_name = %s AND instrument_token = %s
        RETURNING id;
        """
        try:
            cur.execute(query, (watchlist_name, instrument_token))
            result = cur.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"Error deleting watchlist entry: {e}")
            raise

    @classmethod
    def get_by_token(cls, cur, instrument_token: int):
        query = "SELECT * FROM equity_tokens WHERE instrument_token = %s"
        try:
            cur.execute(query, (instrument_token,))
            return cur.fetchone()
        except Exception as e:
            logger.error(f"Error in get_by_token: {e}")
            raise

    @classmethod
    def search(cls, cur, query_str: str):
        like_query = f"%{query_str}%"
        sql = """
        SELECT * FROM equity_tokens
        WHERE tradingsymbol ILIKE %s OR company_name ILIKE %s
        LIMIT 50;
        """
        try:
            cur.execute(sql, (like_query, like_query))
            rows = cur.fetchall()
            col_names = [desc[0] for desc in cur.description]
            results = [dict(zip(col_names, row)) for row in rows]
            return results
        except Exception as e:
            logger.error(f"Error searching equity_token: {e}")
            raise


class WatchlistName:
    """
    Represents a "container" for watchlists (e.g. "Favorites", "Intraday", etc.)
    This does NOT replace the existing 'watchlist' table.
    """
    def __init__(self, name: str, created_at=None, id=None):
        self.id = id
        self.name = name
        self.created_at = created_at if created_at else datetime.now()

    @classmethod
    def create_table(cls, cur):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS watchlist_name (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        try:
            cur.execute(create_table_query)
            logger.info("Table 'watchlist_name' created successfully (or already exists).")
        except Exception as e:
            logger.error(f"Error creating table 'watchlist_name': {e}")
            raise

    def save(self, cur):
        insert_query = """
        INSERT INTO watchlist_name (name, created_at)
        VALUES (%s, %s)
        RETURNING id, created_at;
        """
        try:
            cur.execute(insert_query, (self.name, self.created_at))
            row = cur.fetchone()
            self.id, self.created_at = row[0], row[1]
            logger.info(f"Inserted new watchlist_name '{self.name}' with id {self.id}.")
        except Exception as e:
            logger.error(f"Error saving watchlist_name: {e}")
            raise

    @classmethod
    def get_all(cls, cur):
        query = "SELECT id, name, created_at FROM watchlist_name ORDER BY id;"
        try:
            cur.execute(query)
            rows = cur.fetchall()
            return [
                cls(id=row[0], name=row[1], created_at=row[2])
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Error fetching all watchlist names: {e}")
            raise

    @classmethod
    def get_by_id(cls, cur, watchlist_id: int):
        query = "SELECT id, name, created_at FROM watchlist_name WHERE id = %s;"
        try:
            cur.execute(query, (watchlist_id,))
            row = cur.fetchone()
            if row:
                return cls(id=row[0], name=row[1], created_at=row[2])
            return None
        except Exception as e:
            logger.error(f"Error fetching watchlist_name by id {watchlist_id}: {e}")
            raise

    @classmethod
    def get_by_name(cls, cur, name: str):
        query = "SELECT id, name, created_at FROM watchlist_name WHERE name = %s;"
        try:
            cur.execute(query, (name,))
            row = cur.fetchone()
            if row:
                return cls(id=row[0], name=row[1], created_at=row[2])
            return None
        except Exception as e:
            logger.error(f"Error fetching watchlist_name by name '{name}': {e}")
            raise

    @classmethod
    def delete(cls, cur, watchlist_id: int):
        query = "DELETE FROM watchlist_name WHERE id = %s RETURNING id;"
        try:
            cur.execute(query, (watchlist_id,))
            result = cur.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"Error deleting watchlist_name with id {watchlist_id}: {e}")
            raise