import datetime
import time
import logging
from requests import get
from controllers import kite 
from db import get_db_connection, close_db_connection
from models import EquityInstruments

logger = logging.getLogger(__name__)

def get_instrument_equity():
    if kite.access_token:
        try:
            conn, cur = get_db_connection()  # Get connection and cursor
            response = kite.instruments(exchange="NSE")
            
            filtered_response = []
            for instrument in response:
                if instrument['instrument_type'] == "EQ" and instrument['segment'] == "NSE":
                    filtered_response.append(instrument)

            for instrument in filtered_response:
                if isinstance(instrument['expiry'], (datetime.date, datetime.datetime)):
                    instrument['expiry'] = instrument['expiry'].isoformat()
            
            EquityInstruments.create_table(cur)
            EquityInstruments.delete_all(cur)
            
            for instrument in filtered_response:
                indices = EquityInstruments(
                    instrument['instrument_token'],
                    instrument['exchange_token'],
                    instrument['tradingsymbol'], 
                    instrument['name'],
                    instrument['last_price'],
                    instrument['expiry'],
                    instrument['strike'],
                    instrument['tick_size'], 
                    instrument['lot_size'],
                    instrument['instrument_type'],
                    instrument['segment'],
                    instrument['exchange']
                )
                indices.save(cur)  # Save each instrument
            
            conn.commit()  # Commit changes after insertions
        except Exception as err:
            logger.error(f"Error in get_instrument_equity: {err}")
            return {"error": str(err)}
        finally:
            close_db_connection()  # Close connection in the end
        
        return {"data": filtered_response}
    else:
        return {"error": "Access token not found"}
