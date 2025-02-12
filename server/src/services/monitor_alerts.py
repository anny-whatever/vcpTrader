# monitor_alerts.py

import logging
from services import get_all_alerts, remove_alert, create_and_send_alert_message

logger = logging.getLogger(__name__)

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
    try:
        for tick_data in ticks:
            instrument_token = tick_data.get('instrument_token')
            last_price = tick_data.get('last_price')
            
            # Retrieve all active alerts for the instrument token from the database.
            alerts = get_all_alerts(instrument_token)
            
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
                
                except (TypeError, ValueError) as e:
                    logger.error(f"Error processing alert: {e}")
                    continue
                
    except Exception as e:
        logger.error(f"Error processing live alerts: {e}")
        raise
