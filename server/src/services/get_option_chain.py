import datetime
from db import get_db_connection, close_db_connection
import pandas as pd

from models import FnoInstruments, ExpiryDates, NiftyOptionChain, BankNiftyOptionChain, FinNiftyOptionChain
from controllers import kite

def filter_expiry_dates():
    conn, cur = get_db_connection()  # Get connection and cursor
    
    try:
        # Log start of process
        print("Fetching instruments from FnoInstruments...")
        
        # Fetch all instruments
        response = FnoInstruments.select_all(cur)
        print(f"Received {len(response)} instruments")

        expiry_dates = set()

        # Collect unique expiry dates and names
        for instrument in response:
            expiry_dates.add((instrument['name'], instrument['expiry'], instrument['segment']))

        # Convert set to list for ordered processing
        expiry_dates = list(expiry_dates)
        
        # Create table if not exists
        print("Creating expiry_dates table if not exists...")
        ExpiryDates.create_table(cur)

        # Clear previous data
        print("Clearing all entries from expiry_dates table...")
        ExpiryDates.delete_all(cur)

        # Insert new expiry dates
        for date in expiry_dates:
            print(f"Inserting: Name: {date[0]}, Expiry: {date[1]}")  # Debugging print
            ExpiryDates(date[0], date[1], date[2]).save(cur)  # Save each instrument

        # Commit changes
        conn.commit()
        print("All changes committed successfully.")
        
        return expiry_dates

    except Exception as err:
        print(f"Error: {err}")
        conn.rollback()  # Rollback transaction in case of error
        return {"error": str(err)}
        
    finally:
        # Ensure the connection is closed
        close_db_connection()
        print("Connection closed.")


def generate_option_chain_nifty():
    conn, cur = get_db_connection()  # Get connection and cursor
    
    try:  
        futures_response_nifty = ExpiryDates.select_by_type_and_name(cur,"NFO-FUT", "NIFTY")
        
        latest_nifty_expiry = futures_response_nifty[0]
        
        # print(latest_nifty_expiry, "dhijursghdijrth iorutdeioprthioudrthiou[erthijoperthijopuerthjkopertbhijkoert]")
        if latest_nifty_expiry[1].date() == datetime.datetime.now().replace(hour=00, minute=00, second=0).date():
            latest_nifty_expiry = futures_response_nifty[1]

        nifty_ltp = kite.ltp('NSE:NIFTY 50')
        nifty_ltp = nifty_ltp['NSE:NIFTY 50']['last_price']
        nifty_strike_limit = 1000

        select_query = """
        SELECT * FROM fno_instruments 
        WHERE name = %s 
        AND expiry <= %s
        AND strike <= %s
        AND strike >= %s
        ORDER BY expiry ASC;"""
        
        cur.execute(select_query, (latest_nifty_expiry[0], latest_nifty_expiry[1], nifty_ltp + nifty_strike_limit, nifty_ltp - nifty_strike_limit))
        nifty_response = cur.fetchall()
        
        NiftyOptionChain.create_table(cur)
        NiftyOptionChain.delete_all(cur)

        for item in nifty_response:
            NiftyOptionChain(item['instrument_token'], item['exchange_token'], item['tradingsymbol'], item['name'], item['last_price'], item['expiry'], item['strike'], item['tick_size'], item['lot_size'], item['instrument_type'], item['segment'], item['exchange']).save(cur)

        conn.commit()


        
        return "Successfully generated option chain"
    except Exception as err:
        print(f"Error: {err}")
        return {"error": str(err)}
        
    finally:
        # Ensure the connection is closed
        close_db_connection()
        print("Connection closed.")

def generate_option_chain_bank_nifty():
    conn, cur = get_db_connection()  # Get connection and cursor
    
    try:  
        futures_response_nifty = ExpiryDates.select_by_type_and_name(cur,"NFO-FUT", "BANKNIFTY")
        
        latest_nifty_expiry = futures_response_nifty[0]
        
        # print(latest_nifty_expiry, "dhijursghdijrth iorutdeioprthioudrthiou[erthijoperthijopuerthjkopertbhijkoert]")
        if latest_nifty_expiry[1].date() == datetime.datetime.now().replace(hour=00, minute=00, second=0).date():
            latest_nifty_expiry = futures_response_nifty[1]

        nifty_ltp = kite.ltp('NSE:NIFTY BANK')
        nifty_ltp = nifty_ltp['NSE:NIFTY BANK']['last_price']
        nifty_strike_limit = 1000

        select_query = """
        SELECT * FROM fno_instruments 
        WHERE name = %s 
        AND expiry <= %s
        AND strike <= %s
        AND strike >= %s
        ORDER BY expiry ASC;"""
        
        cur.execute(select_query, (latest_nifty_expiry[0], latest_nifty_expiry[1], nifty_ltp + nifty_strike_limit, nifty_ltp - nifty_strike_limit))
        nifty_response = cur.fetchall()
        
        BankNiftyOptionChain.create_table(cur)
        BankNiftyOptionChain.delete_all(cur)

        for item in nifty_response:
            BankNiftyOptionChain(item['instrument_token'], item['exchange_token'], item['tradingsymbol'], item['name'], item['last_price'], item['expiry'], item['strike'], item['tick_size'], item['lot_size'], item['instrument_type'], item['segment'], item['exchange']).save(cur)

        conn.commit()


        
        return "Successfully generated option chain"
    except Exception as err:
        print(f"Error: {err}")
        return {"error": str(err)}
        
    finally:
        # Ensure the connection is closed
        close_db_connection()
        print("Connection closed.")

def generate_option_chain_fin_nifty():
    conn, cur = get_db_connection()  # Get connection and cursor
    
    try:  
        futures_response_nifty = ExpiryDates.select_by_type_and_name(cur,"NFO-FUT", "FINNIFTY")
        
        latest_nifty_expiry = futures_response_nifty[0]
        
        # print(latest_nifty_expiry, "dhijursghdijrth iorutdeioprthioudrthiou[erthijoperthijopuerthjkopertbhijkoert]")
        if latest_nifty_expiry[1].date() == datetime.datetime.now().replace(hour=00, minute=00, second=0).date():
            latest_nifty_expiry = futures_response_nifty[1]

        nifty_ltp = kite.ltp('NSE:NIFTY FIN SERVICE')
        nifty_ltp = nifty_ltp['NSE:NIFTY FIN SERVICE']['last_price']
        nifty_strike_limit = 1000

        select_query = """
        SELECT * FROM fno_instruments 
        WHERE name = %s 
        AND expiry <= %s
        AND strike <= %s
        AND strike >= %s
        ORDER BY expiry ASC;"""
        
        cur.execute(select_query, (latest_nifty_expiry[0], latest_nifty_expiry[1], nifty_ltp + nifty_strike_limit, nifty_ltp - nifty_strike_limit))
        nifty_response = cur.fetchall()
        
        FinNiftyOptionChain.create_table(cur)
        FinNiftyOptionChain.delete_all(cur)

        for item in nifty_response:
            FinNiftyOptionChain(item['instrument_token'], item['exchange_token'], item['tradingsymbol'], item['name'], item['last_price'], item['expiry'], item['strike'], item['tick_size'], item['lot_size'], item['instrument_type'], item['segment'], item['exchange']).save(cur)

        conn.commit()


        
        return "Successfully generated option chain"
    except Exception as err:
        print(f"Error: {err}")
        return {"error": str(err)}
        
    finally:
        # Ensure the connection is closed
        close_db_connection()
        print("Connection closed.")