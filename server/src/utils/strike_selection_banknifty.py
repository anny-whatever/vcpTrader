import logging
from controllers import kite
from db import get_trade_db_connection, release_trade_db_connection

logger = logging.getLogger(__name__)

def get_strikes_from_banknifty_by_steps_call(expiry_step, strike_step):
    """
    Fetch a call option for BANKNIFTY (instrument_token=260105).
    'strike_step' is the number of 100-point steps from ATM, if that's typical for BankNifty.
    Adjust step size as needed (often BankNifty strikes differ by 100).
    """
    conn, cur = None, None
    try:
        conn, cur = get_trade_db_connection()

        # 1) Get LTP of BANKNIFTY
        ltp_data = kite.ltp('NSE:NIFTY BANK')
        bn_ltp = ltp_data['NSE:NIFTY BANK']['last_price']
        # Round to nearest 100 if that's your standard
        atm_strike = 100 * round(bn_ltp / 100)

        # 2) The call strike
        call_strike = atm_strike + (strike_step * 100)

        # 3) Query from 'banknifty_option_chain'
        select_query = """
        SELECT instrument_token, tradingsymbol, strike, expiry
        FROM banknifty_option_chain
        WHERE strike = %s AND instrument_type = 'CE'
        ORDER BY expiry ASC
        LIMIT 1;
        """
        cur.execute(select_query, (call_strike,))
        row = cur.fetchone()
        if not row:
            return {"error": "No matching BANKNIFTY call option found."}

        return {
            'instrument_token': row['instrument_token'],
            'tradingsymbol': row['tradingsymbol'],
            'strike': row['strike'],
            'expiry': row['expiry']
        }
    except Exception as e:
        logger.error(f"Error in get_strikes_from_banknifty_by_steps_call: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        release_trade_db_connection(conn, cur)

def get_strikes_from_banknifty_by_steps_put(expiry_step, strike_step):
    """
    Fetch a put option for BANKNIFTY.
    'strike_step' is the number of 100-point steps from ATM for put.
    """
    conn, cur = None, None
    try:
        conn, cur = get_trade_db_connection()

        # 1) Get LTP of BANKNIFTY
        ltp_data = kite.ltp('NSE:NIFTY BANK')
        bn_ltp = ltp_data['NSE:NIFTY BANK']['last_price']
        atm_strike = 100 * round(bn_ltp / 100)

        # 2) The put strike
        put_strike = atm_strike - (strike_step * 100)

        # 3) Query from 'banknifty_option_chain'
        select_query = """
        SELECT instrument_token, tradingsymbol, strike, expiry
        FROM banknifty_option_chain
        WHERE strike = %s AND instrument_type = 'PE'
        ORDER BY expiry ASC
        LIMIT 1;
        """
        cur.execute(select_query, (put_strike,))
        row = cur.fetchone()
        if not row:
            return {"error": "No matching BANKNIFTY put option found."}

        return {
            'instrument_token': row['instrument_token'],
            'tradingsymbol': row['tradingsymbol'],
            'strike': row['strike'],
            'expiry': row['expiry']
        }
    except Exception as e:
        logger.error(f"Error in get_strikes_from_banknifty_by_steps_put: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        release_trade_db_connection(conn, cur)
