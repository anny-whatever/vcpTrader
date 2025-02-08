import logging

logger = logging.getLogger(__name__)

class RiskPool:
    def __init__(self, used_risk, available_risk):
        self.used_risk = used_risk
        self.available_risk = available_risk

    def save(self, cur):
        try:
            query = """
                INSERT INTO risk_pool (used_risk, available_risk) 
                VALUES (%s, %s);
            """
            cur.execute(query, (self.used_risk, self.available_risk))
            logger.info("Risk pool record saved successfully.")
        except Exception as err:
            logger.error(f"Error saving risk pool: {err}")
            raise err
    
    @classmethod
    def update_used_risk(cls, cur, new_used_risk):
        try:
            query = """
                UPDATE risk_pool 
                SET used_risk = %s;
            """
            cur.execute(query, (new_used_risk,))
            logger.info("Used risk updated successfully.")
        except Exception as err:
            logger.error(f"Error updating used risk: {err}")
            raise err
    
    @classmethod
    def update_available_risk(cls, cur, new_available_risk):
        try:
            query = """
                UPDATE risk_pool 
                SET available_risk = %s;
            """
            cur.execute(query, (new_available_risk,))
            logger.info("Available risk updated successfully.")
        except Exception as err:
            logger.error(f"Error updating available risk: {err}")
            raise err
    
    @classmethod
    def fetch_risk_pool(cls, cur):
        try:
            query = "SELECT used_risk, available_risk FROM risk_pool;"
            cur.execute(query)
            result = cur.fetchone()
            logger.info("Risk pool data fetched successfully.")
            return result
        except Exception as err:
            logger.error(f"Error fetching risk pool: {err}")
            return None
