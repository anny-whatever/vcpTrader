# models/equity_tokens.py

import logging

logger = logging.getLogger(__name__)

class EquityToken:
    """
    Model class for the 'equity_tokens' table.
    It abstracts away direct SQL queries so you can just call methods on this class.
    """

    def __init__(self, instrument_token, tradingsymbol, company_name, exchange, segment):
        self.instrument_token = instrument_token
        self.tradingsymbol = tradingsymbol
        self.company_name = company_name
        self.exchange = exchange
        self.segment = segment

    @classmethod
    def create_table(cls, cur):
        """
        Create the equity_tokens table if it doesn't exist.
        (If you're already running 'database_setup.py', you can omit this.)
        """
        create_table_query = """
        CREATE TABLE IF NOT EXISTS equity_tokens (
            id SERIAL PRIMARY KEY,
            instrument_token BIGINT NOT NULL,
            tradingsymbol VARCHAR(100) NOT NULL,
            company_name VARCHAR(255),
            exchange VARCHAR(50),
            segment VARCHAR(50),
            UNIQUE (instrument_token, tradingsymbol)
        );
        """
        try:
            cur.execute(create_table_query)
            logger.info("Table 'equity_tokens' created or already exists.")
        except Exception as e:
            logger.error(f"Error creating table 'equity_tokens': {e}")
            raise

    def save(self, cur):
        """
        Inserts this EquityToken into the DB.
        On conflict, does nothing (can be adjusted to DO UPDATE if desired).
        """
        insert_query = """
        INSERT INTO equity_tokens (instrument_token, tradingsymbol, company_name, exchange, segment)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (instrument_token, tradingsymbol) DO NOTHING;
        """
        try:
            cur.execute(
                insert_query,
                (
                    self.instrument_token,
                    self.tradingsymbol,
                    self.company_name,
                    self.exchange,
                    self.segment
                )
            )
        except Exception as e:
            logger.error(f"Error saving equity token: {e}")
            raise

    @classmethod
    def save_many(cls, cur, token_list):
        """
        Insert multiple EquityTokens at once.
        Expects a list of EquityToken objects.
        """
        insert_query = """
        INSERT INTO equity_tokens (instrument_token, tradingsymbol, company_name, exchange, segment)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (instrument_token, tradingsymbol) DO NOTHING;
        """
        try:
            data_to_insert = [
                (
                    token.instrument_token,
                    token.tradingsymbol,
                    token.company_name,
                    token.exchange,
                    token.segment
                )
                for token in token_list
            ]
            cur.executemany(insert_query, data_to_insert)
        except Exception as e:
            logger.error(f"Error inserting multiple equity tokens: {e}")
            raise

    @classmethod
    def delete_by_segment(cls, cur, segment):
        """
        Deletes all rows where the 'segment' matches the provided value.
        With 'ON DELETE CASCADE' on the watchlist table, any watchlist rows
        referencing these tokens will also be removed automatically.
        """
        delete_query = "DELETE FROM equity_tokens WHERE segment = %s;"
        try:
            cur.execute(delete_query, (segment,))
        except Exception as e:
            logger.error(f"Error deleting equity tokens by segment '{segment}': {e}")
            raise

    @classmethod
    def fetch_all(cls, cur):
        """
        Fetch all rows from equity_tokens.
        """
        select_query = "SELECT * FROM equity_tokens;"
        try:
            cur.execute(select_query)
            return cur.fetchall()
        except Exception as e:
            logger.error(f"Error fetching all equity tokens: {e}")
            raise

    @classmethod
    def get_by_token(cls, cur, instrument_token: int):
        """
        Retrieves a single record from equity_tokens by instrument_token.
        Returns a single row or None if not found.
        """
        query = "SELECT * FROM equity_tokens WHERE instrument_token = %s"
        try:
            cur.execute(query, (instrument_token,))
            return cur.fetchone()
        except Exception as e:
            logger.error(f"Error in get_by_token: {e}")
            raise

    @classmethod
    def search(cls, cur, query_str: str):
        """
        Search for tokens matching the query in either 'tradingsymbol' or 'company_name'.
        Returns up to 10 results.
        """
        like_query = f"%{query_str}%"
        sql = """
        SELECT * FROM equity_tokens
        WHERE tradingsymbol ILIKE %s OR company_name ILIKE %s
        LIMIT 10;
        """
        try:
            cur.execute(sql, (like_query, like_query))
            rows = cur.fetchall()
            col_names = [desc[0] for desc in cur.description]
            # Convert each row tuple into a dict
            results = [dict(zip(col_names, row)) for row in rows]
            return results
        except Exception as e:
            logger.error(f"Error searching equity_tokens: {e}")
            raise
