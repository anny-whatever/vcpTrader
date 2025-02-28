import logging
from controllers import kite
from db import get_trade_db_connection, release_trade_db_connection

logger = logging.getLogger(__name__)

def get_strikes_from_finnifty_by_steps_call(expiry_step, strike_step):
    """
    Fetch a call option for FINNIFTY (instrument_token=257801).
    'strike_step' might be 50 points for FINNIFTY or 100, depends on your data.
    Adjust as needed.
    """
    conn, cur = None, None
    try:
        conn, cur = get_trade_db_connection()

        # 1) Get LTP of FINNIFTY
        ltp_data = kite.ltp('NSE:NIFTY FIN SERVICE')
        fn_ltp = ltp_data['NSE:NIFTY FIN SERVICE']['last_price']
        # Suppose FINNIFTY increments in steps of 50
        atm_strike = 50 * round(fn_ltp / 50)

        # 2) The call strike
        call_strike = atm_strike + (strike_step * 50)

        # 3) Query from 'finnifty_option_chain'
        select_query = """
        SELECT instrument_token, tradingsymbol, strike, expiry
        FROM finnifty_option_chain
        WHERE strike = %s AND instrument_type = 'CE'
        ORDER BY expiry ASC
        LIMIT 1;
        """
        cur.execute(select_query, (call_strike,))
        row = cur.fetchone()
        if not row:
            return {"error": "No matching FINNIFTY call option found."}

        return {
            'instrument_token': row['instrument_token'],
            'tradingsymbol': row['tradingsymbol'],
            'strike': row['strike'],
            'expiry': row['expiry']
        }
    except Exception as e:
        logger.error(f"Error in get_strikes_from_finnifty_by_steps_call: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        release_trade_db_connection(conn, cur)

def get_strikes_from_finnifty_by_steps_put(expiry_step, strike_step):
    """
    Fetch a put option for FINNIFTY.
    'strike_step' is the number of 50-point steps from ATM for put.
    """
    conn, cur = None, None
    try:
        conn, cur = get_trade_db_connection()

        # 1) Get LTP of FINNIFTY
        ltp_data = kite.ltp('NSE:NIFTY FIN SERVICE')
        fn_ltp = ltp_data['NSE:NIFTY FIN SERVICE']['last_price']
        atm_strike = 50 * round(fn_ltp / 50)

        # 2) The put strike
        put_strike = atm_strike - (strike_step * 50)

        # 3) Query from 'finnifty_option_chain'
        select_query = """
        SELECT instrument_token, tradingsymbol, strike, expiry
        FROM finnifty_option_chain
        WHERE strike = %s AND instrument_type = 'PE'
        ORDER BY expiry ASC
        LIMIT 1;
        """
        cur.execute(select_query, (put_strike,))
        row = cur.fetchone()
        if not row:
            return {"error": "No matching FINNIFTY put option found."}

        return {
            'instrument_token': row['instrument_token'],
            'tradingsymbol': row['tradingsymbol'],
            'strike': row['strike'],
            'expiry': row['expiry']
        }
    except Exception as e:
        logger.error(f"Error in get_strikes_from_finnifty_by_steps_put: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        release_trade_db_connection(conn, cur)
