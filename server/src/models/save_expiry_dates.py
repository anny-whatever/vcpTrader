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
        cur.execute(create_table_query)
    
    @classmethod
    def select_by_name(cls, cur, name):
        select_query = """SELECT * FROM expiry_dates WHERE name = %s ORDER BY expiry_date ASC;"""
        cur.execute(select_query , (name,))
        return cur.fetchall()
    
    @classmethod
    def select_by_date(cls, cur, expiry_date):
        select_query = """SELECT * FROM expiry_dates WHERE expiry_date = %s ORDER BY expiry_date ASC;"""
        cur.execute(select_query , (expiry_date,))
        return cur.fetchall()
    
    @classmethod
    def select_by_type(cls, cur, instrument_type):
        select_query = """SELECT * FROM expiry_dates WHERE instrument_type = %s ORDER BY expiry_date ASC;"""
        cur.execute(select_query , (instrument_type,))
        return cur.fetchall()
    
    @classmethod
    def select_by_type_and_name(cls, cur, instrument_type, name):
        select_query = """SELECT * FROM expiry_dates WHERE instrument_type = %s AND name = %s ORDER BY expiry_date ASC;"""
        cur.execute(select_query , (instrument_type, name))
        return cur.fetchall()   
    
    @classmethod
    def select_all(cls, cur):
        select_query = """SELECT * FROM expiry_dates ORDER BY expiry_date ASC;"""
        cur.execute(select_query)
        return cur.fetchall()
    
    @classmethod
    def delete_by_name(cls, cur, name):
        delete_query = """DELETE FROM expiry_dates WHERE name = %s;"""
        cur.execute(delete_query, (name,))

    @classmethod
    def delete_by_date(cls, cur, expiry_date):
        delete_query = """DELETE FROM expiry_dates WHERE expiry_date = %s;"""
        cur.execute(delete_query, (expiry_date,))
        
    @classmethod
    def delete_by_type(cls, cur, instrument_type):
        delete_query = """DELETE FROM expiry_dates WHERE instrument_type = %s;"""        
        cur.execute(delete_query, (instrument_type,))
        
    @classmethod
    def delete_all(cls, cur):
        delete_query = """DELETE FROM expiry_dates;"""        
        cur.execute(delete_query)

    def save(self, cur):
        insert_query = """
        INSERT INTO expiry_dates (name, expiry_date, instrument_type)
        VALUES (%s, %s, %s)
        """
        print(f"Saving: {self.name}, {self.expiry_date}, {self.instrument_type}")  # Debugging print
        cur.execute(insert_query, (self.name, self.expiry_date, self.instrument_type))