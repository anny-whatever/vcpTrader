import logging
from fastapi import HTTPException
from models import EquityToken
from models import WatchlistEntry
from controllers import kite_ticker, kite

logger = logging.getLogger(__name__)

def add_stock_to_watchlist(cur, watchlist_name: str, instrument_token: int, symbol: str):
    # Verify that the instrument exists using the EquityToken model.
    try:
        instrument = EquityToken.get_by_token(cur, instrument_token)
        if not instrument:
            raise HTTPException(status_code=404, detail="Instrument not found")
    except Exception as e:
        logger.error(f"Error checking instrument: {e}")
        raise HTTPException(status_code=500, detail="Error checking instrument")
    
    # Create a WatchlistEntry instance and save it.
    entry = WatchlistEntry(watchlist_name, instrument_token, symbol)
    try:
        entry.save(cur)
        saved_entry = WatchlistEntry.get_by_instrument(cur, watchlist_name, instrument_token)
        if kite_ticker is not None:
            if kite_ticker.is_connected():
                kite_ticker.subscribe([instrument_token])
                kite_ticker.set_mode(kite_ticker.MODE_FULL, [instrument_token])
        return saved_entry
    except Exception as e:
        logger.error(f"Error saving watchlist entry: {e}")
        raise HTTPException(status_code=500, detail="Error saving watchlist entry")

def get_watchlist_entries(cur, watchlist_name: str):
    try:
        entries = WatchlistEntry.fetch_by_list(cur, watchlist_name)
        if not entries:
            return []
        
        # Collect unique instrument tokens from the watchlist entries.
        unique_tokens = list({entry['instrument_token'] for entry in entries})
        
        # Attempt to fetch live quotes for these tokens.
        try:
            live_quotes = kite.quote(unique_tokens)
        except Exception as e:
            logger.error(f"Error fetching live quotes for watchlist: {e}")
            live_quotes = {}
        
        # Update each entry with additional live quote details.
        
        updated_entries = []
        for entry in entries:
            token_str = str(entry['instrument_token'])
            quote_data = live_quotes.get(token_str, {})
            
            # Attach basic live data
            entry['last_price'] = float(quote_data.get('last_price', 0))
            # If available, unpack the OHLC details.
            ohlc = quote_data.get('ohlc', {})
            entry['prevClose'] = float(ohlc.get('close', 0))
            # Calculate percentage change, if previous close is available.
            if ohlc.get('close', 0):
                change_pct = ((entry['last_price'] - ohlc.get('close', 0)) / ohlc.get('close', 0)) * 100
                entry['change'] = round(change_pct, 2)
            else:
                entry['change'] = 0.0
            
            updated_entries.append(entry)
        
        return updated_entries 
    except Exception as e:
        logger.error(f"Error fetching watchlist entries: {e}")
        raise HTTPException(status_code=500, detail="Error fetching watchlist entries")

def search_equity(cur, query: str):
    try:
        return EquityToken.search(cur, query)
    except Exception as e:
        logger.error(f"Error searching equities: {e}")
        raise HTTPException(status_code=500, detail="Error searching equities")

