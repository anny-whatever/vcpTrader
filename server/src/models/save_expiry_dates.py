import logging

logger = logging.getLogger(__name__)

class ExpiryDates:
    def __init__(self, name, expiry_date, instrument_type):
        self.name = name
        self.expiry_date = expiry_date
        self.instrument_type = instrument_type
        
    @classmethod
    def create_table(cls, cur):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS expiry_dates (
            name VARCHAR(255),
            expiry_date TIMESTAMPTZ,
            instrument_type VARCHAR(255),
            UNIQUE (name, expiry_date, instrument_type)
        );
        """
        try:
            cur.execute(create_table_query)
            logger.info("Table expiry_dates created successfully (or already exists).")
        except Exception as e:
            logger.error(f"Error creating table expiry_dates: {e}")
            raise e
    
    @classmethod
    def select_by_name(cls, cur, name):
        select_query = "SELECT * FROM expiry_dates WHERE name = %s ORDER BY expiry_date ASC;"
        try:
            cur.execute(select_query, (name,))
            results = cur.fetchall()
            logger.info(f"Retrieved records for name {name} successfully.")
            return results
        except Exception as e:
            logger.error(f"Error selecting expiry_dates by name {name}: {e}")
            raise e
    
    @classmethod
    def select_by_date(cls, cur, expiry_date):
        select_query = "SELECT * FROM expiry_dates WHERE expiry_date = %s ORDER BY expiry_date ASC;"
        try:
            cur.execute(select_query, (expiry_date,))
            results = cur.fetchall()
            logger.info(f"Retrieved records for expiry_date {expiry_date} successfully.")
            return results
        except Exception as e:
            logger.error(f"Error selecting expiry_dates by expiry_date {expiry_date}: {e}")
            raise e
    
    @classmethod
    def select_by_type(cls, cur, instrument_type):
        select_query = "SELECT * FROM expiry_dates WHERE instrument_type = %s ORDER BY expiry_date ASC;"
        try:
            cur.execute(select_query, (instrument_type,))
            results = cur.fetchall()
            logger.info(f"Retrieved records for instrument_type {instrument_type} successfully.")
            return results
        except Exception as e:
            logger.error(f"Error selecting expiry_dates by instrument_type {instrument_type}: {e}")
            raise e
    
    @classmethod
    def select_by_type_and_name(cls, cur, instrument_type, name):
        select_query = "SELECT * FROM expiry_dates WHERE instrument_type = %s AND name = %s ORDER BY expiry_date ASC;"
        try:
            cur.execute(select_query, (instrument_type, name))
            results = cur.fetchall()
            logger.info(f"Retrieved records for instrument_type {instrument_type} and name {name} successfully.")
            return results
        except Exception as e:
            logger.error(f"Error selecting expiry_dates by instrument_type {instrument_type} and name {name}: {e}")
            raise e   
    
    @classmethod
    def select_all(cls, cur):
        select_query = "SELECT * FROM expiry_dates ORDER BY expiry_date ASC;"
        try:
            cur.execute(select_query)
            results = cur.fetchall()
            logger.info("Retrieved all records from expiry_dates successfully.")
            return results
        except Exception as e:
            logger.error(f"Error selecting all records from expiry_dates: {e}")
            raise e
    
    @classmethod
    def delete_by_name(cls, cur, name):
        delete_query = "DELETE FROM expiry_dates WHERE name = %s;"
        try:
            cur.execute(delete_query, (name,))
            logger.info(f"Deleted records for name {name} successfully.")
        except Exception as e:
            logger.error(f"Error deleting expiry_dates records for name {name}: {e}")
            raise e

    @classmethod
    def delete_by_date(cls, cur, expiry_date):
        delete_query = "DELETE FROM expiry_dates WHERE expiry_date = %s;"
        try:
            cur.execute(delete_query, (expiry_date,))
            logger.info(f"Deleted records for expiry_date {expiry_date} successfully.")
        except Exception as e:
            logger.error(f"Error deleting expiry_dates records for expiry_date {expiry_date}: {e}")
            raise e
        
    @classmethod
    def delete_by_type(cls, cur, instrument_type):
        delete_query = "DELETE FROM expiry_dates WHERE instrument_type = %s;"
        try:
            cur.execute(delete_query, (instrument_type,))
            logger.info(f"Deleted records for instrument_type {instrument_type} successfully.")
        except Exception as e:
            logger.error(f"Error deleting expiry_dates records for instrument_type {instrument_type}: {e}")
            raise e
        
    @classmethod
    def delete_all(cls, cur):
        delete_query = "DELETE FROM expiry_dates;"
        try:
            cur.execute(delete_query)
            logger.info("Deleted all records from expiry_dates successfully.")
        except Exception as e:
            logger.error(f"Error deleting all records from expiry_dates: {e}")
            raise e

    def save(self, cur):
        insert_query = "INSERT INTO expiry_dates (name, expiry_date, instrument_type) VALUES (%s, %s, %s)"
        try:
            logger.debug(f"Saving: {self.name}, {self.expiry_date}, {self.instrument_type}")
            cur.execute(insert_query, (self.name, self.expiry_date, self.instrument_type))
            logger.info(f"Saved record for name {self.name} successfully.")
        except Exception as e:
            logger.error(f"Error saving expiry_dates record for name {self.name}: {e}")
            raise e
