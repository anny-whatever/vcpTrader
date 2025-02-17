import logging
from fastapi import HTTPException
from models import EquityToken
from models import WatchlistEntry

logger = logging.getLogger(__name__)

def add_stock_to_watchlist(cur, user_id: int, watchlist_name: str, instrument_token: int, symbol: str):
    # Verify that the instrument exists using the EquityToken model.
    try:
        instrument = EquityToken.get_by_token(cur, instrument_token)
        if not instrument:
            raise HTTPException(status_code=404, detail="Instrument not found")
    except Exception as e:
        logger.error(f"Error checking instrument: {e}")
        raise HTTPException(status_code=500, detail="Error checking instrument")
    
    # Create a WatchlistEntry instance and save it.
    entry = WatchlistEntry(user_id, watchlist_name, instrument_token, symbol)
    try:
        entry.save(cur)
        saved_entry = WatchlistEntry.get_by_user_and_instrument(cur, user_id, watchlist_name, instrument_token)
        return saved_entry
    except Exception as e:
        logger.error(f"Error saving watchlist entry: {e}")
        raise HTTPException(status_code=500, detail="Error saving watchlist entry")

def get_watchlist_entries(cur, user_id: int, watchlist_name: str):
    try:
        return WatchlistEntry.fetch_by_user_and_list(cur, user_id, watchlist_name)
    except Exception as e:
        logger.error(f"Error fetching watchlist entries: {e}")
        raise HTTPException(status_code=500, detail="Error fetching watchlist entries")

def search_equity(cur, query: str):
    try:
        return EquityToken.search(cur, query)
    except Exception as e:
        logger.error(f"Error searching equities: {e}")
        raise HTTPException(status_code=500, detail="Error searching equities")
