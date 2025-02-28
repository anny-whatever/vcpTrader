import datetime
import time
import logging
from requests import get
from controllers import kite 
from db import get_db_connection, close_db_connection
from models import  FnoInstruments

logger = logging.getLogger(__name__)

def get_instrument_fno():
    if kite.access_token: 
        try:
            conn, cur = get_db_connection()  # Get connection and cursor
            response = kite.instruments(exchange="NFO")
            
            filtered_response = []
            for instrument in response:
                if instrument['name'] in ("NIFTY") or instrument['name'] in ("BANKNIFTY") or instrument['name'] in ("FINNIFTY"):
                    filtered_response.append(instrument)
            
            # Convert 'expiry' to ISO format for datetime objects
            for instrument in filtered_response:
                if isinstance(instrument['expiry'], (datetime.date, datetime.datetime)):
                    instrument['expiry'] = instrument['expiry'].isoformat()

            # Create table and delete old data
            FnoInstruments.create_table(cur)
            FnoInstruments.delete_all(cur)
            
            # Insert new data
            for instrument in filtered_response:
                fno = FnoInstruments(
                    instrument['instrument_token'], instrument['exchange_token'], instrument['tradingsymbol'], 
                    instrument['name'], instrument['last_price'],
                    instrument['expiry'], instrument['strike'], instrument['tick_size'], 
                    instrument['lot_size'], instrument['instrument_type'], instrument['segment'], instrument['exchange']
                )
                fno.save(cur)  # Save each instrument
            
            conn.commit()  # Commit changes after insertions

        except (Exception) as err: 
            conn.rollback()  # Rollback transaction in case of error
            return {"error": str(err)}

        finally:
            close_db_connection()  # Close connection in the end

        return {"data": filtered_response}  # Return filtered data
    else:
        return {"error": "Access token not found"}