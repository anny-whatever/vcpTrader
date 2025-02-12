import logging

logger = logging.getLogger(__name__)

class PriceAlert:
    def __init__(self, instrument_token, symbol, price, alert_type):
        """
        Initialize a PriceAlert instance.
        
        :param instrument_token: int - The unique token for the instrument.
        :param symbol: str - The stock symbol.
        :param price: float - The target/stop-loss price for the alert.
        :param alert_type: str - The type of alert (e.g., 'target' or 'sl').
        """
        self.instrument_token = instrument_token
        self.symbol = symbol
        self.price = price
        self.alert_type = alert_type

    def save(self, cur):
        """
        Save this price alert to the price_alerts table.
        """
        try:
            query = """
                INSERT INTO price_alerts (instrument_token, symbol, price, alert_type)
                VALUES (%s, %s, %s, %s);
            """
            cur.execute(query, (self.instrument_token, self.symbol, self.price, self.alert_type))
            logger.info("Price alert saved successfully.")
        except Exception as err:
            logger.error(f"Error saving price alert: {err}")
            raise err

    @classmethod
    def delete_alert(cls, cur, alert_id):
        """
        Delete an alert from the price_alerts table using its id.
        
        :param alert_id: int - The unique identifier of the alert to delete.
        """
        try:
            query = """
                DELETE FROM price_alerts
                WHERE id = %s;
            """
            cur.execute(query, (alert_id,))
            logger.info(f"Price alert with id {alert_id} deleted successfully.")
        except Exception as err:
            logger.error(f"Error deleting price alert with id {alert_id}: {err}")
            raise err

    @classmethod
    def fetch_all_alerts(cls, cur):
        """
        Fetch all active price alerts from the price_alerts table.
        
        :return: A list of alerts, where each alert is represented as a dict or tuple.
        """
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
            return None


class AlertMessage:
    def __init__(self, instrument_token, symbol, alert_type, triggered_price, message):
        """
        Initialize an AlertMessage instance.
        
        :param instrument_token: int - The instrument token associated with the alert.
        :param symbol: str - The stock symbol.
        :param alert_type: str - The type of alert (e.g., 'target' or 'sl').
        :param triggered_price: float - The price at which the alert was triggered.
        :param message: str - A descriptive message for the alert.
        """
        self.instrument_token = instrument_token
        self.symbol = symbol
        self.alert_type = alert_type
        self.triggered_price = triggered_price
        self.message = message

    def save(self, cur):
        """
        Save this alert message to the alert_messages table.
        """
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
            raise err

    @classmethod
    def fetch_all_messages(cls, cur):
        """
        Fetch all alert messages from the alert_messages table.
        
        :return: A list of alert messages.
        """
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
            return None

    @classmethod
    def fetch_latest_messages(cls, cur):
        """
        Fetch the latest 10 alert messages from the alert_messages table,
        ordered by the creation timestamp in descending order.
        
        :return: A list of alert messages.
        """
        try:
            query = """
                SELECT id, instrument_token, symbol, alert_type, triggered_price, message, created_at
                FROM alert_messages
                ORDER BY created_at DESC
                LIMIT 10;
            """
            cur.execute(query)
            messages = cur.fetchall()
            logger.info("Alert messages fetched successfully.")
            return messages
        except Exception as err:
            logger.error(f"Error fetching alert messages: {err}")
            return None
