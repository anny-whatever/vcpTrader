# models.py
import logging

logger = logging.getLogger(__name__)

class PriceAlert:
    def __init__(self, instrument_token: int, symbol: str, price: float, alert_type: str):
        self.instrument_token = instrument_token
        self.symbol = symbol
        self.price = price
        self.alert_type = alert_type

    def save(self, cur):
        try:
            query = """
                INSERT INTO price_alerts (instrument_token, symbol, price, alert_type)
                VALUES (%s, %s, %s, %s);
            """
            cur.execute(query, (self.instrument_token, self.symbol, self.price, self.alert_type))
            logger.info("Price alert saved successfully.")
        except Exception as err:
            logger.error(f"Error saving price alert: {err}")
            raise

    @classmethod
    def delete_alert(cls, cur, alert_id: int):
        try:
            query = "DELETE FROM price_alerts WHERE id = %s;"
            cur.execute(query, (alert_id,))
            logger.info(f"Price alert with id {alert_id} deleted successfully.")
        except Exception as err:
            logger.error(f"Error deleting price alert with id {alert_id}: {err}")
            raise

    @classmethod
    def fetch_all_alerts(cls, cur):
        try:
            query = """
                SELECT id, instrument_token, symbol, price, alert_type
                FROM price_alerts;
            """
            cur.execute(query)
            alerts = cur.fetchall()
            logger.info("Price alerts fetched successfully.")
            return alerts
        except Exception as err:
            logger.error(f"Error fetching price alerts: {err}")
            return []

class AlertMessage:
    def __init__(self, instrument_token: int, symbol: str, alert_type: str, triggered_price: float, message: str):
        self.instrument_token = instrument_token
        self.symbol = symbol
        self.alert_type = alert_type
        self.triggered_price = triggered_price
        self.message = message

    def save(self, cur):
        try:
            query = """
                INSERT INTO alert_messages (instrument_token, symbol, alert_type, triggered_price, message)
                VALUES (%s, %s, %s, %s, %s);
            """
            cur.execute(query, (
                self.instrument_token,
                self.symbol,
                self.alert_type,
                self.triggered_price,
                self.message
            ))
            logger.info("Alert message saved successfully.")
        except Exception as err:
            logger.error(f"Error saving alert message: {err}")
            raise

    @classmethod
    def fetch_all_messages(cls, cur):
        try:
            query = """
                SELECT id, instrument_token, symbol, alert_type, triggered_price, message, created_at
                FROM alert_messages;
            """
            cur.execute(query)
            messages = cur.fetchall()
            logger.info("Alert messages fetched successfully.")
            return messages
        except Exception as err:
            logger.error(f"Error fetching alert messages: {err}")
            return []

    @classmethod
    def fetch_latest_messages(cls, cur):
        try:
            query = """
                SELECT id, instrument_token, symbol, alert_type, triggered_price, message, created_at
                FROM alert_messages
                ORDER BY created_at DESC
                LIMIT 10;
            """
            cur.execute(query)
            messages = cur.fetchall()
            logger.info("Latest alert messages fetched successfully.")
            return messages
        except Exception as err:
            logger.error(f"Error fetching alert messages: {err}")
            return []
