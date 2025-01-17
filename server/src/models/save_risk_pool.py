class RiskPool:
    def __init__(self, used_risk, available_risk):
        self.used_risk = used_risk
        self.available_risk = available_risk

    def save(self, cur):
        """
        Save the risk pool record to the database.
        """
        try:
            query = """
                INSERT INTO risk_pool (used_risk, available_risk) 
                VALUES (%s, %s);
            """
            cur.execute(query, (self.used_risk, self.available_risk))
        except Exception as err:
            print(f"Error saving risk pool: {str(err)}")
            return {"error": str(err)}
    
    @classmethod
    def update_used_risk(cls, cur, new_used_risk):
        """
        Update the used risk in the risk pool.
        """
        try:
            query = """
                UPDATE risk_pool 
                SET used_risk = %s;
            """
            cur.execute(query, (new_used_risk,))
        except Exception as err:
            print(f"Error updating used risk: {str(err)}")
            return {"error": str(err)}
    
    @classmethod
    def update_available_risk(cls, cur, new_available_risk):
        """
        Update the available risk in the risk pool.
        """
        try:
            query = """
                UPDATE risk_pool 
                SET available_risk = %s;
            """
            cur.execute(query, (new_available_risk,))
        except Exception as err:
            print(f"Error updating available risk: {str(err)}")
            return {"error": str(err)}
    
    @classmethod
    def fetch_risk_pool(cls, cur):
        """
        Fetch the current risk pool from the database.
        """
        try:
            query = "SELECT used_risk, available_risk FROM risk_pool;"
            cur.execute(query)
            result = cur.fetchone()
            return result
        except Exception as err:
            print(f"Error fetching risk pool: {str(err)}")
            return None
