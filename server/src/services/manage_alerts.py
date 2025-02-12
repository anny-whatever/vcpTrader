# manage_alerts.py

import logging
import asyncio
import json
from db import get_db_connection, close_db_connection
from models import PriceAlert, AlertMessage
from controllers import process_and_send_alert_update_message # Import the async function to send messages to clients

logger = logging.getLogger(__name__)

def add_alert(instrument_token, symbol, price, alert_type):
    """
    Add a new price alert to the price_alerts table.
    
    :param instrument_token: int - The unique token for the instrument.
    :param symbol: str - The stock symbol.
    :param price: float - The target or stop-loss price.
    :param alert_type: str - The type of alert ('target' or 'sl').
    :return: dict - A response dictionary indicating success or failure.
    """
    conn, cur = None, None
    try:
        conn, cur = get_db_connection()
        alert = PriceAlert(instrument_token, symbol, price, alert_type)
        alert.save(cur)
        conn.commit()
        logger.info(f"Alert added for {symbol} at price {price} with type {alert_type}.")
        return {"success": True, "message": "Alert added successfully."}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error adding alert: {e}")
        return {"success": False, "message": f"Error adding alert: {e}"}
    finally:
        if conn and cur:
            close_db_connection(conn, cur)

def remove_alert(alert_id):
    """
    Remove a price alert from the price_alerts table.
    
    :param alert_id: int - The unique identifier of the alert to delete.
    :return: dict - A response dictionary indicating success or failure.
    """
    conn, cur = None, None
    try:
        conn, cur = get_db_connection()
        PriceAlert.delete_alert(cur, alert_id)
        conn.commit()
        logger.info(f"Alert with id {alert_id} removed successfully.")
        return {"success": True, "message": "Alert removed successfully."}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error removing alert: {e}")
        return {"success": False, "message": f"Error removing alert: {e}"}
    finally:
        if conn and cur:
            close_db_connection(conn, cur)

async def create_and_send_alert_message(instrument_token, symbol, alert_type, triggered_price, custom_message=None):
    """
    Create a templated alert message for a given alert trigger, save it to the alert_messages table,
    and then send the message to connected WebSocket clients.
    
    :param instrument_token: int - The instrument token for the stock.
    :param symbol: str - The stock symbol.
    :param alert_type: str - The type of alert ('target' or 'sl').
    :param triggered_price: float - The price at which the alert was triggered.
    :param custom_message: str, optional - A custom message to override the default template.
    :return: dict - A response indicating success or failure.
    """
    conn, cur = None, None
    try:
        conn, cur = get_db_connection()
        
        # Build a default message if none is provided.
        if custom_message is None:
            if alert_type.lower() == 'target':
                custom_message = f"Target alert hit for {symbol}: Triggered at price {triggered_price}."
            elif alert_type.lower() == 'sl':
                custom_message = f"Stop loss alert hit for {symbol}: Triggered at price {triggered_price}."
            else:
                custom_message = f"Alert for {symbol}: Triggered at price {triggered_price}."
        
        # Create the alert message record
        alert_msg = AlertMessage(
            instrument_token=instrument_token,
            symbol=symbol,
            alert_type=alert_type,
            triggered_price=triggered_price,
            message=custom_message
        )
        alert_msg.save(cur)
        conn.commit()
        logger.info(f"Alert message saved for {symbol} with alert type {alert_type}.")

        # Prepare the payload to send to the frontend
        payload = {
            "event": "alert_triggered",
            "data": {
                "instrument_token": instrument_token,
                "symbol": symbol,
                "alert_type": alert_type,
                "triggered_price": triggered_price,
                "message": custom_message
            }
        }
        message_json = json.dumps(payload)
        
        # Send the socket message synchronously
        await process_and_send_alert_update_message(message_json)
        
        return {"success": True, "message": "Alert message processed and sent successfully."}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error creating and sending alert message: {e}")
        return {"success": False, "message": f"Error creating and sending alert message: {e}"}
    finally:
        if conn and cur:
            close_db_connection(conn, cur)
