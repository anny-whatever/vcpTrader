class FetchPosition:
    def __init__(self, strategy, direction, flags):
        self.strategy = strategy
        self.direction = direction        
        self.flags = flags
    
    @classmethod
    def get_all_positions_sabbo(cls, cur):
        try:
            select_sabbo_positions_query = "SELECT * FROM sabbo_positions"
            cur.execute(select_sabbo_positions_query)
            return cur.fetchall()
        except Exception as e:
            print(f"Error fetching positions: {str(e)}")
            return []

    @classmethod
    def get_all_flags_sabbo(cls, cur):
        try:
            select_sabbo_flags_query = "SELECT * FROM sabbo_flags"
            cur.execute(select_sabbo_flags_query)
            return cur.fetchall()
        except Exception as e:
            print(f"Error fetching flags: {str(e)}")
            return []
    
    @classmethod
    def get_all_positions_danbo(cls, cur):
        try:
            select_danbo_positions_query = "SELECT * FROM danbo_positions"
            cur.execute(select_danbo_positions_query)
            return cur.fetchall()
        except Exception as e:
            print(f"Error fetching positions: {str(e)}")
            return []

    @classmethod
    def get_all_flags_danbo(cls, cur):
        try:
            select_danbo_flags_query = "SELECT * FROM danbo_flags"
            cur.execute(select_danbo_flags_query)
            return cur.fetchall()
        except Exception as e:
            print(f"Error fetching flags: {str(e)}")
            return []
    
    @classmethod
    def get_all_positions_sutbo(cls, cur):
        try:
            select_sutbo_positions_query = "SELECT * FROM sutbo_positions"
            cur.execute(select_sutbo_positions_query)
            return cur.fetchall()
        except Exception as e:
            print(f"Error fetching positions: {str(e)}")
            return []

    @classmethod
    def get_all_flags_sutbo(cls, cur):
        try:
            select_sutbo_flags_query = "SELECT * FROM sutbo_flags"
            cur.execute(select_sutbo_flags_query)
            return cur.fetchall()
        except Exception as e:
            print(f"Error fetching flags: {str(e)}")            
            return []