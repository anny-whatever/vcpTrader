from db import get_ticker_db_connection, release_ticker_db_connection
from models import TradableTicks, NonTradableTicks
import logging
import time

logger = logging.getLogger(__name__)

def save_tradable_ticks(ticks):
    ticker_conn, ticker_cur = get_ticker_db_connection()
    try:
        start = time.time()
        TradableTicks.save_batch(ticker_cur, ticks)
        ticker_conn.commit()
        end = time.time()
        logger.info(f"Batch saving tradable ticks took {end - start} seconds")
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
        start = time.time()
        NonTradableTicks.save_batch(ticker_cur, ticks)
        ticker_conn.commit()
        end = time.time()
        logger.info(f"Batch saving nontradable ticks took {end - start} seconds")
        return "Successfully stored nontradable ticks"
    except Exception as e:
        ticker_conn.rollback()
        logger.error(f"Error in saving nontradable ticks: {str(e)}")
        return {"error": str(e)}
    finally:
        release_ticker_db_connection(ticker_conn, ticker_cur)
