import logging
import asyncio
import json
from db import get_db_connection, close_db_connection
from models import PriceAlert, AlertMessage
from services import get_all_alerts


logger = logging.getLogger(__name__)

alerts = None

def add_alert(instrument_token, symbol, price, alert_type):
    """
    Add a new price alert to the price_alerts table.
    
    :param instrument_token: int - The unique token for the instrument.
    :param symbol: str - The stock symbol.
    :param price: float - The target or stop-loss price.
    :param alert_type: str - The type of alert ('target' or 'sl').
    :return: dict - A response dictionary indicating success or failure.
    """
    global alerts
    try:
        conn, cur = get_db_connection()
        alert = PriceAlert(instrument_token, symbol, price, alert_type)
        alert.save(cur)
        conn.commit()
        logger.info(f"Alert added for {symbol} at price {price} with type {alert_type}.")
        alerts = None
        return {"success": True, "message": "Alert added successfully."}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error adding alert: {e}")
        return {"success": False, "message": f"Error adding alert: {e}"}
    finally:
        if conn and cur:
            close_db_connection()

def remove_alert(alert_id):
    """
    Remove a price alert from the price_alerts table.
    
    :param alert_id: int - The unique identifier of the alert to delete.
    :return: dict - A response dictionary indicating success or failure.
    """
    global alerts
    try:
        conn, cur = get_db_connection()
        PriceAlert.delete_alert(cur, alert_id)
        conn.commit()
        logger.info(f"Alert with id {alert_id} removed successfully.")
        alerts = None
        return {"success": True, "message": "Alert removed successfully."}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error removing alert: {e}")
        return {"success": False, "message": f"Error removing alert: {e}"}
    finally:
        if conn and cur:
            close_db_connection()

async def create_and_send_alert_message(instrument_token, symbol, alert_type, triggered_price, custom_message=None, send_update_func=None):
    """
    Create a templated alert message for a given alert trigger, save it to the alert_messages table,
    and then send the message using the provided function.
    
    :param instrument_token: int - The instrument token for the stock.
    :param symbol: str - The stock symbol.
    :param alert_type: str - The type of alert ('target' or 'sl').
    :param triggered_price: float - The price at which the alert was triggered.
    :param custom_message: str, optional - A custom message to override the default template.
    :param send_update_func: callable, optional - Function to send the alert update message.
    :return: dict - A response indicating success or failure.
    """
    
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
        
        # Save the alert message to the database (assuming this functionality exists)
        alert_message = AlertMessage(instrument_token, symbol, alert_type, triggered_price, custom_message)
        alert_message.save(cur)
        conn.commit()
        
        # Send the alert message using the provided function
        if send_update_func:
            await send_update_func(custom_message)
        
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
    Process incoming tick data and check for any triggered alerts.
    
    For each instrument token in the ticks data, this function:
        - Retrieves all active alerts from the database.
        - Checks if there are any active alerts for the instrument token.
        - Evaluates each alert against the corresponding tick data:
            - For a 'target' alert: triggers if last_price >= alert price.
            - For a 'sl' alert: triggers if last_price <= alert price.
        - Sends an alert message to the frontend and removes the alert from the database if triggered.
    
    :param ticks: List of dictionaries where each dictionary represents tick data for an instrument token.
                  Each dictionary must include 'instrument_token' and 'last_price' keys.
    """
    global alerts
    try:
        for tick_data in ticks:
            instrument_token = tick_data.get('instrument_token')
            last_price = tick_data.get('last_price')
            
            # Retrieve all active alerts for the instrument token from the database.
            if alerts is None:
                alerts = get_all_alerts()       
            
            for alert in alerts:
                try:
                    alert_id = alert.get('id')
                    symbol = alert.get('symbol')
                    alert_type = alert.get('alert_type').lower()
                    alert_price = float(alert.get('price'))
                    
                    # Check if the alert condition is met.
                    if (alert_type == 'target' and last_price >= alert_price) or \
                       (alert_type == 'sl' and last_price <= alert_price):
                        
                        # Trigger the alert.
                        logger.info(
                            f"Alert triggered for {symbol} (token: {instrument_token}). "
                            f"Alert type: {alert_type}, Triggered at price: {last_price}."
                        )
                        
                        # Send alert message to the frontend asynchronously.
                        await create_and_send_alert_message(
                            instrument_token=instrument_token,
                            symbol=symbol,
                            alert_type=alert_type,
                            triggered_price=last_price
                        )
                        
                        # Remove the triggered alert from the database.
                        remove_alert(alert_id)
                        alerts = None
                
                except (TypeError, ValueError) as e:
                    logger.error(f"Error processing alert: {e}")
                    continue
                
    except Exception as e:
        logger.error(f"Error processing live alerts: {e}")
        raise
