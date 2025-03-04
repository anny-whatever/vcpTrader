import datetime
import logging
from db import get_db_connection, close_db_connection
import pandas as pd

from models import FnoInstruments, ExpiryDates, NiftyOptionChain, BankNiftyOptionChain, FinNiftyOptionChain
from controllers import kite

logger = logging.getLogger(__name__)

def filter_expiry_dates():
    conn, cur = None, None
    try:
        conn, cur = get_db_connection()  # Get connection and cursor
        
        logger.info("Fetching instruments from FnoInstruments...")
        response = FnoInstruments.select_all(cur)
        logger.info(f"Received {len(response)} instruments")

        expiry_dates = set()
        # Collect unique expiry dates and names
        for instrument in response:
            expiry_dates.add((instrument['name'], instrument['expiry'], instrument['segment']))

        # Convert set to list for ordered processing
        expiry_dates = list(expiry_dates)
        
        logger.info("Creating expiry_dates table if not exists...")
        ExpiryDates.create_table(cur)

        logger.info("Clearing all entries from expiry_dates table...")
        ExpiryDates.delete_all(cur)

        # Insert new expiry dates
        for date in expiry_dates:
            logger.info(f"Inserting: Name: {date[0]}, Expiry: {date[1]}")
            ExpiryDates(date[0], date[1], date[2]).save(cur)

        conn.commit()
        logger.info("All changes committed successfully.")
        return expiry_dates

    except Exception as err:
        logger.error(f"Error in filter_expiry_dates: {err}", exc_info=True)
        if conn:
            conn.rollback()  # Rollback transaction in case of error
        return {"error": str(err)}
        
    finally:
        close_db_connection()
        logger.info("Database connection closed.")

def generate_option_chain_nifty():
    conn, cur = None, None
    try:  
        conn, cur = get_db_connection()  # Get connection and cursor
        
        futures_response_nifty = ExpiryDates.select_by_type_and_name(cur, "NFO-FUT", "NIFTY")
        if not futures_response_nifty:
            logger.error("No futures response found for NIFTY.")
            return {"error": "No futures response found for NIFTY."}
        
        latest_nifty_expiry = futures_response_nifty[0]
        
        if latest_nifty_expiry[1].date() == datetime.datetime.now().replace(hour=0, minute=0, second=0).date():
            if len(futures_response_nifty) > 1:
                latest_nifty_expiry = futures_response_nifty[1]
            else:
                logger.warning("Only one expiry date available for NIFTY; proceeding with available date.")

        nifty_ltp_response = kite.ltp('NSE:NIFTY 50')
        nifty_ltp = nifty_ltp_response['NSE:NIFTY 50']['last_price']
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
            NiftyOptionChain(
                item['instrument_token'], item['exchange_token'], item['tradingsymbol'], 
                item['name'], item['last_price'], item['expiry'], item['strike'], 
                item['tick_size'], item['lot_size'], item['instrument_type'], 
                item['segment'], item['exchange']
            ).save(cur)

        conn.commit()
        logger.info("Successfully generated Nifty option chain.")
        return "Successfully generated option chain"

    except Exception as err:
        logger.error(f"Error in generate_option_chain_nifty: {err}", exc_info=True)
        if conn:
            conn.rollback()
        return {"error": str(err)}
        
    finally:
        close_db_connection()
        logger.info("Database connection closed for Nifty option chain.")

def generate_option_chain_bank_nifty():
    conn, cur = None, None
    try:  
        conn, cur = get_db_connection()  # Get connection and cursor
        
        futures_response_bank_nifty = ExpiryDates.select_by_type_and_name(cur, "NFO-FUT", "BANKNIFTY")
        if not futures_response_bank_nifty:
            logger.error("No futures response found for BANKNIFTY.")
            return {"error": "No futures response found for BANKNIFTY."}
        
        latest_bank_nifty_expiry = futures_response_bank_nifty[0]
        
        if latest_bank_nifty_expiry[1].date() == datetime.datetime.now().replace(hour=0, minute=0, second=0).date():
            if len(futures_response_bank_nifty) > 1:
                latest_bank_nifty_expiry = futures_response_bank_nifty[1]
            else:
                logger.warning("Only one expiry date available for BANKNIFTY; proceeding with available date.")

        nifty_ltp_response = kite.ltp('NSE:NIFTY BANK')
        nifty_ltp = nifty_ltp_response['NSE:NIFTY BANK']['last_price']
        nifty_strike_limit = 1000

        select_query = """
        SELECT * FROM fno_instruments 
        WHERE name = %s 
        AND expiry <= %s
        AND strike <= %s
        AND strike >= %s
        ORDER BY expiry ASC;"""
        
        cur.execute(select_query, (latest_bank_nifty_expiry[0], latest_bank_nifty_expiry[1], nifty_ltp + nifty_strike_limit, nifty_ltp - nifty_strike_limit))
        nifty_response = cur.fetchall()
        
        BankNiftyOptionChain.create_table(cur)
        BankNiftyOptionChain.delete_all(cur)

        for item in nifty_response:
            BankNiftyOptionChain(
                item['instrument_token'], item['exchange_token'], item['tradingsymbol'], 
                item['name'], item['last_price'], item['expiry'], item['strike'], 
                item['tick_size'], item['lot_size'], item['instrument_type'], 
                item['segment'], item['exchange']
            ).save(cur)

        conn.commit()
        logger.info("Successfully generated Bank Nifty option chain.")
        return "Successfully generated option chain"

    except Exception as err:
        logger.error(f"Error in generate_option_chain_bank_nifty: {err}", exc_info=True)
        if conn:
            conn.rollback()
        return {"error": str(err)}
        
    finally:
        close_db_connection()
        logger.info("Database connection closed for Bank Nifty option chain.")

def generate_option_chain_fin_nifty():
    conn, cur = None, None
    try:  
        conn, cur = get_db_connection()  # Get connection and cursor
        
        futures_response_fin_nifty = ExpiryDates.select_by_type_and_name(cur, "NFO-FUT", "FINNIFTY")
        if not futures_response_fin_nifty:
            logger.error("No futures response found for FINNIFTY.")
            return {"error": "No futures response found for FINNIFTY."}
        
        latest_fin_nifty_expiry = futures_response_fin_nifty[0]
        
        if latest_fin_nifty_expiry[1].date() == datetime.datetime.now().replace(hour=0, minute=0, second=0).date():
            if len(futures_response_fin_nifty) > 1:
                latest_fin_nifty_expiry = futures_response_fin_nifty[1]
            else:
                logger.warning("Only one expiry date available for FINNIFTY; proceeding with available date.")

        nifty_ltp_response = kite.ltp('NSE:NIFTY FIN SERVICE')
        nifty_ltp = nifty_ltp_response['NSE:NIFTY FIN SERVICE']['last_price']
        nifty_strike_limit = 1000

        select_query = """
        SELECT * FROM fno_instruments 
        WHERE name = %s 
        AND expiry <= %s
        AND strike <= %s
        AND strike >= %s
        ORDER BY expiry ASC;"""
        
        cur.execute(select_query, (latest_fin_nifty_expiry[0], latest_fin_nifty_expiry[1], nifty_ltp + nifty_strike_limit, nifty_ltp - nifty_strike_limit))
        nifty_response = cur.fetchall()
        
        FinNiftyOptionChain.create_table(cur)
        FinNiftyOptionChain.delete_all(cur)

        for item in nifty_response:
            FinNiftyOptionChain(
                item['instrument_token'], item['exchange_token'], item['tradingsymbol'], 
                item['name'], item['last_price'], item['expiry'], item['strike'], 
                item['tick_size'], item['lot_size'], item['instrument_type'], 
                item['segment'], item['exchange']
            ).save(cur)

        conn.commit()
        logger.info("Successfully generated Fin Nifty option chain.")
        return "Successfully generated option chain"

    except Exception as err:
        logger.error(f"Error in generate_option_chain_fin_nifty: {err}", exc_info=True)
        if conn:
            conn.rollback()
        return {"error": str(err)}
        
    finally:
        close_db_connection()
        logger.info("Database connection closed for Fin Nifty option chain.")
