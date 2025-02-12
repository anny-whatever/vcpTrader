# services.py
import json
import logging
import asyncio
from db import get_db_connection, close_db_connection
from models import PriceAlert, AlertMessage
from get_display_data import get_all_alerts


logger = logging.getLogger(__name__)

# Global cache for alerts (Note: Consider thread-safe caching for highly concurrent scenarios)
alerts_cache = None

def add_alert(instrument_token: int, symbol: str, price: float, alert_type: str):
    """
    Add a new price alert to the database.
    """
    global alerts_cache
    conn, cur = None, None
    try:
        conn, cur = get_db_connection()
        alert = PriceAlert(instrument_token, symbol, price, alert_type)
        alert.save(cur)
        conn.commit()
        logger.info(f"Alert added for {symbol} at price {price} with type {alert_type}.")
        alerts_cache = None
        return {"success": True, "message": "Alert added successfully."}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error adding alert: {e}")
        return {"success": False, "message": f"Error adding alert: {e}"}
    finally:
        if conn and cur:
            close_db_connection()

def remove_alert(alert_id: int):
    """
    Remove a price alert from the database.
    """
    global alerts_cache
    conn, cur = None, None
    try:
        conn, cur = get_db_connection()
        PriceAlert.delete_alert(cur, alert_id)
        conn.commit()
        logger.info(f"Alert with id {alert_id} removed successfully.")
        alerts_cache = None
        return {"success": True, "message": "Alert removed successfully."}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error removing alert: {e}")
        return {"success": False, "message": f"Error removing alert: {e}"}
    finally:
        if conn and cur:
            close_db_connection()

async def create_and_send_alert_message(
    instrument_token: int,
    symbol: str,
    alert_type: str,
    triggered_price: float,
    custom_message: str = None,
    send_update_func=None
):
    """
    Create an alert message, save it to the database, and send it to clients.
    This function is used when a live alert is triggered.
    It leverages the provided send_update_func (which should be process_and_send_alert_triggered_message)
    to send a WebSocket message with the event "alert_triggered".
    """
    conn, cur = None, None
    from controllers import process_and_send_alert_triggered_message  # Import the dedicated alert trigger sender
    try:
        conn, cur = get_db_connection()
        if custom_message is None:
            if alert_type.lower() == 'target':
                custom_message = f"Target alert hit for {symbol}: Triggered at price {triggered_price}."
            elif alert_type.lower() == 'sl':
                custom_message = f"Stop loss alert hit for {symbol}: Triggered at price {triggered_price}."
            else:
                custom_message = f"Alert for {symbol}: Triggered at price {triggered_price}."
        # Create and save the alert message
        alert_message = AlertMessage(instrument_token, symbol, alert_type, triggered_price, custom_message)
        alert_message.save(cur)
        conn.commit()
        
        # Instead of duplicating sending logic, call the dedicated alert trigger sender.
        await process_and_send_alert_triggered_message(custom_message)
        logger.info("Alert message processed and sent successfully.")
        return {"success": True, "message": "Alert message processed and sent successfully."}
    except Exception as e:
        logger.error(f"Error processing alert message: {e}")
        return {"success": False, "message": f"Error processing alert message: {e}"}
    finally:
        if conn and cur:
            close_db_connection()

async def process_live_alerts(ticks):
    """
    Process incoming tick data and trigger alerts if conditions are met.
    """
    global alerts_cache
    try:
        for tick_data in ticks:
            instrument_token = tick_data.get('instrument_token')
            last_price = tick_data.get('last_price')
            if alerts_cache is None:
                alerts_cache = get_all_alerts()
            for alert in alerts_cache:
                try:
                    alert_id = alert.get('id')
                    symbol = alert.get('symbol')
                    alert_type = alert.get('alert_type').lower()
                    alert_price = float(alert.get('price'))
                    if (alert_type == 'target' and last_price >= alert_price) or \
                       (alert_type == 'sl' and last_price <= alert_price):
                        logger.info(
                            f"Alert triggered for {symbol} (token: {instrument_token}). "
                            f"Alert type: {alert_type}, Triggered at price: {last_price}."
                        )
                        # When an alert is triggered, pass the dedicated sender function.
                        await create_and_send_alert_message(
                            instrument_token=instrument_token,
                            symbol=symbol,
                            alert_type=alert_type,
                            triggered_price=last_price,
                        )
                        remove_alert(alert_id)
                        alerts_cache = None
                except (TypeError, ValueError) as e:
                    logger.error(f"Error processing alert: {e}")
                    continue
    except Exception as e:
        logger.error(f"Error processing live alerts: {e}")
        raise
