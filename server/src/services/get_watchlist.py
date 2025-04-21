import datetime
import logging
from fastapi import HTTPException
import pytz
from models import WatchlistEntry
from controllers import kite_ticker, kite
from db import get_db_connection, close_db_connection

logger = logging.getLogger(__name__)

def add_stock_to_watchlist(cur, watchlist_name: str, instrument_token: int, symbol: str):
    try:
        if cur is None:
            cur , _ = get_db_connection()
        instrument = WatchlistEntry.get_by_token(cur, instrument_token)
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
        if cur is None:
            cur , _ = get_db_connection()
        entries = WatchlistEntry.fetch_by_list(cur, watchlist_name)
        if not entries:
            return []
        
        # Collect unique instrument tokens from the watchlist entries.
        unique_tokens = list({entry['instrument_token'] for entry in entries})

        # Attempt to fetch live quotes for these tokens.
        live_quotes = {}
        try:
            START_TIME = datetime.time(9, 15)
            END_TIME = datetime.time(15, 30, 5)
            TIMEZONE = pytz.timezone("Asia/Kolkata")
            now = datetime.datetime.now(TIMEZONE).time()
            if START_TIME <= now <= END_TIME:
                try:
                    live_quotes = kite.quote(unique_tokens)
                except Exception as quote_error:
                    logger.error(f"Error fetching quotes from Kite API: {quote_error}")
                    # Proceed without live quotes, using fallback data
        except Exception as e:
            logger.error(f"Error checking market hours: {e}")
        
        # Update each entry with additional live quote details.
        updated_entries = []
        for entry in entries:
            token_str = str(entry['instrument_token'])
            quote_data = live_quotes.get(token_str, {})
            
            # Attach basic live data with fallbacks to prevent null values
            entry['last_price'] = float(quote_data.get('last_price', 0))
            
            # If available, unpack the OHLC details with fallbacks
            ohlc = quote_data.get('ohlc', {})
            entry['prevClose'] = float(ohlc.get('close', 0))
            
            # Calculate percentage change safely
            if entry['prevClose'] and entry['prevClose'] != 0:
                change_pct = ((entry['last_price'] - entry['prevClose']) / entry['prevClose']) * 100
                entry['change'] = round(change_pct, 2)
            else:
                entry['change'] = 0.0
            
            # Ensure all entries have consistent format
            updated_entries.append({
                'id': entry.get('id', 0),
                'watchlist_name': entry.get('watchlist_name', watchlist_name),
                'instrument_token': entry.get('instrument_token', 0),
                'symbol': entry.get('symbol', ''),
                'added_at': entry.get('added_at', ''),
                'last_price': entry.get('last_price', 0.0),
                'prevClose': entry.get('prevClose', 0.0),
                'change': entry.get('change', 0.0)
            })
        
        return updated_entries 
    except Exception as e:
        logger.error(f"Error fetching watchlist entries: {e}")
        raise HTTPException(status_code=500, detail="Error fetching watchlist entries")

def search_equity(cur, query: str):
    try:
        if cur is None:
            cur , _ = get_db_connection()
        return WatchlistEntry.search(cur, query)
    except Exception as e:
        logger.error(f"Error searching equities: {e}")
        raise HTTPException(status_code=500, detail="Error searching equities")

