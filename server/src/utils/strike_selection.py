import logging
from controllers import kite
from db import get_trade_db_connection, release_trade_db_connection

logger = logging.getLogger(__name__)

# Mapping of index details to its properties.
INSTRUMENT_DETAILS = {
    'banknifty': {
        'ltp_symbol': 'NSE:NIFTY BANK',
        'rounding': 100,    # Round to nearest 100
        'increment': 100,   # Strike steps in multiples of 100
        'table': 'banknifty_option_chain'
    },
    'finnifty': {
        'ltp_symbol': 'NSE:NIFTY FIN SERVICE',
        'rounding': 50,     # Round to nearest 50
        'increment': 50,    # Strike steps in multiples of 50
        'table': 'finnifty_option_chain'
    },
    'nifty': {
        'ltp_symbol': 'NSE:NIFTY 50',
        'rounding': 50,     # Round to nearest 50
        'increment': 50,    # Strike steps in multiples of 50
        'table': 'nifty_option_chain'
    }
}

def get_strike_option(index, option, strike_step, expiry_step=0):
    """
    Fetch an option strike for a given index.

    Parameters:
        index (str): The index for which to fetch the option. Valid values are
                     'banknifty', 'finnifty', or 'nifty'.
        option (str): The type of option ('call' or 'put').
        strike_step (int): The number of strike steps from the ATM strike.
                           For a call, the strike will be ATM + (strike_step * increment).
                           For a put, it will be ATM - (strike_step * increment).
        expiry_step (int, optional): Offset in the ordered list of expiries (default is 0 for the nearest expiry).

    Returns:
        dict: A dictionary with option details (instrument_token, tradingsymbol, strike, expiry)
              or an error message if no matching option is found.
    """
    index = index.lower()
    option = option.lower()
    if index not in INSTRUMENT_DETAILS:
        return {"error": f"Invalid index '{index}'. Valid options are: {list(INSTRUMENT_DETAILS.keys())}"}
    if option not in ['call', 'put']:
        return {"error": "Invalid option type. Must be 'call' or 'put'."}

    details = INSTRUMENT_DETAILS[index]
    ltp_symbol = details['ltp_symbol']
    rounding = details['rounding']
    increment = details['increment']
    table = details['table']

    instrument_type = 'CE' if option == 'call' else 'PE'

    conn, cur = None, None
    try:
        conn, cur = get_trade_db_connection()

        # 1) Get the Last Traded Price (LTP)
        ltp_data = kite.ltp(ltp_symbol)
        last_price = ltp_data[ltp_symbol]['last_price']
        # Round to the nearest valid strike level
        atm_strike = rounding * round(last_price / rounding)

        # 2) Determine the target strike based on the option type and strike step
        if option == 'call':
            target_strike = atm_strike + (strike_step * increment)
        else:  # put
            target_strike = atm_strike - (strike_step * increment)

        # 3) Query the appropriate option chain table.
        # Using OFFSET allows you to choose a later expiry date if needed.
        select_query = f"""
        SELECT instrument_token, tradingsymbol, strike, expiry
        FROM {table}
        WHERE strike = %s AND instrument_type = %s
        ORDER BY expiry ASC
        LIMIT 1 OFFSET %s;
        """
        cur.execute(select_query, (target_strike, instrument_type, expiry_step))
        row = cur.fetchone()
        if not row:
            return {"error": f"No matching {index.upper()} {option} option found at strike {target_strike}."}

        return {
            'instrument_token': row['instrument_token'],
            'tradingsymbol': row['tradingsymbol'],
            'strike': row['strike'],
            'expiry': row['expiry']
        }
    except Exception as e:
        logger.error(f"Error in get_strike_option: {e}", exc_info=True)
        return {"error": str(e)}
    finally:
        release_trade_db_connection(conn, cur)
