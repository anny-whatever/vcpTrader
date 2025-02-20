# services.py
import json
import logging
import asyncio
from db import get_db_connection, close_db_connection
from models import PriceAlert, AlertMessage
from services import get_all_alerts
import threading
from .send_telegram_alert import _send_telegram_in_thread


logger = logging.getLogger(__name__)

# Global cache for alerts (Note: Consider thread-safe caching for highly concurrent scenarios)
alert_trigger_lock = threading.Lock()
alert_trigger_running = False

alerts_cache = None
def add_alert(instrument_token: int, symbol: str, price: float, alert_type: str):
    """
    Add a new price alert to the database.
    """
    global alerts_cache
    
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
        thread = threading.Thread(target=_send_telegram_in_thread, args=(custom_message,))
        thread.start()
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
    
    This function uses a lock (alert_trigger_lock) and a boolean flag 
    (alert_trigger_running) to ensure only one instance of the alert-processing 
    logic runs at a time.
    """
    global alerts_cache
    global alert_trigger_running

    # Acquire the lock at the start.
    with alert_trigger_lock:
        if alert_trigger_running:
            logger.info("process_live_alerts is already running; exiting.")
            return
        # Mark that we are now running
        alert_trigger_running = True

    try:
        # If alerts_cache is empty or None, fetch fresh alerts from DB
        if alerts_cache is None:
            alerts_cache = get_all_alerts()

        # Outer loop: iterate over each alert
        for alert in alerts_cache:
            alert_id = alert.get("id")
            instrument_token = alert.get("instrument_token")
            symbol = alert.get("symbol")
            alert_type = str(alert.get("alert_type")).lower()
            alert_price = float(alert.get("price"))

            # Inner loop: check if any tick has the same instrument_token
            matching_tick = None
            for tick_data in ticks:
                if tick_data.get("instrument_token") == instrument_token:
                    matching_tick = tick_data
                    break

            # If there's no match, move on
            if not matching_tick:
                continue

            # Check if the alert condition is met
            last_price = matching_tick.get("last_price")
            if (alert_type == "target" and last_price >= alert_price) or \
               (alert_type == "sl" and last_price <= alert_price):
                logger.info(
                    f"Alert triggered for {symbol} (token: {instrument_token}). "
                    f"Alert type: {alert_type}, Triggered at price: {last_price}."
                )

                # Send alert message to the frontend asynchronously
                await create_and_send_alert_message(
                    instrument_token=instrument_token,
                    symbol=symbol,
                    alert_type=alert_type,
                    triggered_price=last_price,
                )
                # Remove the triggered alert from DB
                remove_alert(alert_id)

                # Force refresh the cache so we don't reprocess this alert
                alerts_cache = None

    except Exception as e:
        logger.error(f"Error processing live alerts: {e}")
        raise
    finally:
        # Release the lock so future calls can enter
        with alert_trigger_lock:
            alert_trigger_running = False