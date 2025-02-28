import logging
from db import get_ticker_db_connection, release_ticker_db_connection
from models import TradableTicks, NonTradableTicks
import time

logger = logging.getLogger(__name__)

def save_tradable_ticks(ticks):
    ticker_conn, ticker_cur = get_ticker_db_connection()
    try:
        # If you had a TradableTicks model, you'd call something like:
        TradableTicks.save_batch(ticker_cur, ticks)
        ticker_conn.commit()
        return "Successfully stored tradable ticks"
    except Exception as e:
        ticker_conn.rollback()
        logger.error(f"Error in saving tradable ticks: {str(e)}")
        return {"error": str(e)}
    finally:
        release_ticker_db_connection(ticker_conn, ticker_cur)


def save_nontradable_ticks(ticks):
    ticker_conn, ticker_cur = get_ticker_db_connection()
    try:
        NonTradableTicks.save_batch(ticker_cur, ticks)
        ticker_conn.commit()
        return "Successfully stored nontradable ticks"
    except Exception as e:
        ticker_conn.rollback()
        logger.error(f"Error in saving nontradable ticks: {str(e)}")
        return {"error": str(e)}
    finally:
        release_ticker_db_connection(ticker_conn, ticker_cur)
