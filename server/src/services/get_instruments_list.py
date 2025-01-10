import datetime
import time
from requests import get
from controllers import kite 
from db import get_db_connection, close_db_connection
from models import IndicesInstruments
from models import EquityInstruments

    
def get_instrument_indices():
    if kite.access_token: 
        try:
            conn, cur = get_db_connection()  # Get connection and cursor
            response = kite.instruments(exchange="NSE")
            
            filtered_response = []
            for instrument in response:
                if instrument['segment'] == "INDICES":
                    filtered_response.append(instrument)

            # Convert 'expiry' to ISO format for datetime objects
            for instrument in filtered_response:
                if isinstance(instrument['expiry'], (datetime.date, datetime.datetime)):
                    instrument['expiry'] = instrument['expiry'].isoformat()
            
            # Create table and delete old data
            IndicesInstruments.create_table(cur)
            IndicesInstruments.delete_all(cur)
            
            # Insert new data
            for instrument in filtered_response:
                indices = IndicesInstruments(
                    instrument['instrument_token'], instrument['exchange_token'], instrument['tradingsymbol'], 
                    instrument['name'], instrument['last_price'],
                    instrument['expiry'], instrument['strike'], instrument['tick_size'], 
                    instrument['lot_size'], instrument['instrument_type'], instrument['segment'], instrument['exchange']
                )
                indices.save(cur)  # Save each instrument
            
            conn.commit()  # Commit changes after insertions

        except (Exception) as err: 
            return {"error": str(err)}
        
        finally:
            close_db_connection()  # Close connection in the end
        
        return {"data": filtered_response}
    else:
        return {"error": "Access token not found"}


