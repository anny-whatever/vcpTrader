import datetime
import time
import logging
from requests import get
from controllers import kite 
from db import get_db_connection, close_db_connection
from models import IndicesInstruments, EquityInstruments

logger = logging.getLogger(__name__)

def get_instrument_indices():
    if kite.access_token:
        try:
            conn, cur = get_db_connection()  # Get connection and cursor
            response = kite.instruments(exchange="NSE")
            
            filtered_response = []
            for instrument in response:
                if instrument['segment'] == "INDICES":
                    filtered_response.append(instrument)

            for instrument in filtered_response:
                if isinstance(instrument['expiry'], (datetime.date, datetime.datetime)):
                    instrument['expiry'] = instrument['expiry'].isoformat()
            
            IndicesInstruments.create_table(cur)
            IndicesInstruments.delete_all(cur)
            
            for instrument in filtered_response:
                indices = IndicesInstruments(
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
                indices.save(cur)
            
            conn.commit()
        except Exception as err:
            logger.error(f"Error in get_instrument_indices: {err}")
            return {"error": str(err)}
        finally:
            if conn and cur:
                close_db_connection()
        return {"data": filtered_response}
    else:
        return {"error": "Access token not found"}
