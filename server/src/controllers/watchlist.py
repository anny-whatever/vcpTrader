# endpoints/watchlist_endpoints.py
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
from db import get_db_connection, close_db_connection
from services import add_stock_to_watchlist, get_watchlist_entries, search_equity
from auth import require_admin, require_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic schemas for request/response.
class WatchlistEntryIn(BaseModel):
    user_id: int
    watchlist_name: str
    instrument_token: int
    symbol: str

class WatchlistEntryOut(BaseModel):
    id: int
    user_id: int
    watchlist_name: str
    instrument_token: int
    symbol: str
    added_at: str  # or datetime if preferred

@router.post("/watchlist", response_model=WatchlistEntryOut)
def add_to_watchlist(entry: WatchlistEntryIn, user: dict = Depends(require_admin)):
    """
    Add a stock to a watchlist. Requires admin privileges.
    """
    conn, cur = None, None
    try:
        conn, cur = get_db_connection()
        saved_entry = add_stock_to_watchlist(
            cur,
            entry.user_id,
            entry.watchlist_name,
            entry.instrument_token,
            entry.symbol
        )
        conn.commit()
        return saved_entry
    except HTTPException as he:
        if conn:
            conn.rollback()
        raise he
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in add_to_watchlist: {e}")
        raise HTTPException(status_code=500, detail="Error adding to watchlist")
    finally:
        if conn and cur:
            close_db_connection(conn, cur)

@router.delete("/watchlist", response_model=dict)
def remove_from_watchlist(user_id: int, watchlist_name: str, instrument_token: int, user: dict = Depends(require_admin)):
    """
    Remove a stock from a watchlist. Requires admin privileges.
    """
    conn, cur = None, None
    try:
        from models import WatchlistEntry  # Import if needed
        conn, cur = get_db_connection()
        removed = WatchlistEntry.delete_by_user_and_instrument(cur, user_id, watchlist_name, instrument_token)
        conn.commit()
        return {"detail": "Watchlist entry removed"} if removed else {"detail": "Entry not found"}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in remove_from_watchlist: {e}")
        raise HTTPException(status_code=500, detail="Error removing watchlist entry")
    finally:
        if conn and cur:
            close_db_connection(conn, cur)

@router.get("/watchlist/{user_id}/{watchlist_name}", response_model=List[WatchlistEntryOut])
def get_watchlist(user_id: int, watchlist_name: str, user: dict = Depends(require_user)):
    """
    Retrieve a user's watchlist. Requires observer or admin privileges.
    """
    conn, cur = None, None
    try:
        conn, cur = get_db_connection()
        entries = get_watchlist_entries(cur, user_id, watchlist_name)
        return entries
    except Exception as e:
        logger.error(f"Error in get_watchlist: {e}")
        raise HTTPException(status_code=500, detail="Error fetching watchlist")
    finally:
        if conn and cur:
            close_db_connection(conn, cur)

@router.get("/search", response_model=List[dict])
def search_equities(query: str, user: dict = Depends(require_admin)):
    """
    Real-time search endpoint that returns up to 10 matching stocks
    from the equity_tokens table (matching tradingsymbol or company_name).
    """
    conn, cur = None, None
    try:
        conn, cur = get_db_connection()
        results = search_equity(cur, query)
        return results
    except Exception as e:
        logger.error(f"Error in search_equities: {e}")
        raise HTTPException(status_code=500, detail="Error searching equities")
    finally:
        if conn and cur:
            close_db_connection(conn, cur)
