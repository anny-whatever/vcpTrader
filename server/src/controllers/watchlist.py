import datetime
import json
import logging
import asyncio
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel
from typing import List
from db import get_db_connection, close_db_connection
from services import add_stock_to_watchlist, get_watchlist_entries, search_equity
from auth import require_admin, require_user

# Import the WebSocket helper for sending watchlist updates.
# Make sure your ws_clients.py exports process_and_send_watchlist_update_message.
from .ws_clients import process_and_send_watchlist_update_message

logger = logging.getLogger(__name__)
router = APIRouter()

# ---------------------------------------------------
# Watchlist Entry Endpoints (for stock entries)
# ---------------------------------------------------
class WatchlistEntryIn(BaseModel):
    watchlist_name: str
    instrument_token: int
    symbol: str

class WatchlistEntryOut(BaseModel):
    id: int
    watchlist_name: str
    instrument_token: int
    symbol: str
    added_at: str  # ISO formatted datetime string
    # Additional live quote fields
    last_price: float = 0.0
    prevClose: float = 0.0
    change: float = 0.0

@router.post("/add", response_model=WatchlistEntryOut)
def add_to_watchlist(
    entry: WatchlistEntryIn, 
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_admin)
):
    """
    Add a stock to a watchlist. Requires admin privileges.
    Endpoint: POST /api/watchlist/add
    """
    
    try:
        conn, cur = get_db_connection()
        saved_entry = add_stock_to_watchlist(
            cur,
            entry.watchlist_name,
            entry.instrument_token,
            entry.symbol
        )
        conn.commit()
        # Prepare payload for broadcasting
        payload = {
            "action": "added_stock",
            "data": saved_entry
        }
        # Schedule a background task that only uses the pre-fetched payload.
        background_tasks.add_task(
            lambda: asyncio.run(process_and_send_watchlist_update_message(payload))
        )
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


@router.delete("/remove", response_model=dict)
def remove_from_watchlist(
    watchlist_name: str, 
    instrument_token: int, 
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_admin)
):
    """
    Remove a stock from a watchlist. Requires admin privileges.
    Endpoint: DELETE /api/watchlist/remove
    Query parameters: ?watchlist_name=XYZ&instrument_token=12345
    """
    
    try:
        from models import WatchlistEntry  # adjust the import as needed
        conn, cur = get_db_connection()
        removed = WatchlistEntry.delete_by_instrument(cur, watchlist_name, instrument_token)
        conn.commit()
        payload = {
            "action": "removed_stock",
            "watchlist_name": watchlist_name,
            "instrument_token": instrument_token
        }
        background_tasks.add_task(
            lambda: asyncio.run(process_and_send_watchlist_update_message(payload))
        )
        return {"detail": "Watchlist entry removed"} if removed else {"detail": "Entry not found"}
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in remove_from_watchlist: {e}")
        raise HTTPException(status_code=500, detail="Error removing watchlist entry")


@router.get("/{watchlist_name}", response_model=List[WatchlistEntryOut])
def get_watchlist(watchlist_name: str, user: dict = Depends(require_user)):
    """
    Retrieve a specific watchlist by name. Requires observer or admin privileges.
    Endpoint: GET /api/watchlist/{watchlist_name}
    """
    
    try:
        conn, cur = get_db_connection()
        entries = get_watchlist_entries(cur, watchlist_name)
        return entries
    except Exception as e:
        logger.error(f"Error in get_watchlist: {e}")
        raise HTTPException(status_code=500, detail="Error fetching watchlist")


@router.get("/search/{query}", response_model=List[dict])
def search_equities(query: str, user: dict = Depends(require_admin)):
    """
    Real-time search endpoint that returns up to 10 matching stocks
    from the equity_tokens table (matching tradingsymbol or company_name).
    Endpoint: GET /api/watchlist/search/{query}
    """
    
    try:
        conn, cur = get_db_connection()
        logger.info(f"Search query received: {query}")
        results = search_equity(cur, query)
        # If results are tuples, convert them to dicts.
        if results and isinstance(results[0], tuple):
            col_names = [desc[0] for desc in cur.description]
            results = [dict(zip(col_names, row)) for row in results]
            for r in results:
                if isinstance(r.get("added_at"), datetime.datetime):
                    r["added_at"] = r["added_at"].isoformat()
        logger.info(f"Search results: {results}")
        return results
    except Exception as e:
        logger.error(f"Error in search_equities: {e}")
        raise HTTPException(status_code=500, detail="Error searching equities")


# ---------------------------------------------------
# Watchlist Name Endpoints (for managing watchlist containers)
# These endpoints will be available under /api/watchlist/watchlistname/...
# ---------------------------------------------------
class WatchlistNameIn(BaseModel):
    name: str

class WatchlistNameOut(BaseModel):
    id: int
    name: str
    created_at: str  # or datetime if preferred

@router.post("/watchlistname/add", response_model=WatchlistNameOut)
def create_watchlist_name(
    watchlist: WatchlistNameIn, 
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_admin)
):
    """
    Create a new watchlist container (e.g., "Oil Stocks").
    Endpoint: POST /api/watchlist/watchlistname/add
    """
    
    try:
        conn, cur = get_db_connection()
        from models import WatchlistName  # adjust the import as needed
        new_watchlist = WatchlistName(name=watchlist.name)
        new_watchlist.save(cur)
        conn.commit()
        new_watchlist_out = WatchlistNameOut(
            id=new_watchlist.id,
            name=new_watchlist.name,
            created_at=new_watchlist.created_at.isoformat()
        )
        payload = {
            "action": "created_watchlist",
            "watchlist": new_watchlist_out.dict()
        }
        background_tasks.add_task(
            lambda: asyncio.run(process_and_send_watchlist_update_message(payload))
        )
        return new_watchlist_out
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in create_watchlist_name: {e}")
        raise HTTPException(status_code=500, detail="Error creating watchlist")


@router.get("/watchlistname/", response_model=List[WatchlistNameOut])
def list_watchlist_names(user: dict = Depends(require_user)):
    """
    Retrieve all watchlist containers.
    Endpoint: GET /api/watchlist/watchlistname/
    """
    
    try:
        conn, cur = get_db_connection()
        from models import WatchlistName
        watchlists = WatchlistName.get_all(cur)
        return [
            WatchlistNameOut(
                id=wl.id,
                name=wl.name,
                created_at=wl.created_at.isoformat()
            ) for wl in watchlists
        ]
    except Exception as e:
        logger.error(f"Error in list_watchlist_names: {e}")
        raise HTTPException(status_code=500, detail="Error fetching watchlist names")


@router.get("/watchlistname/{watchlist_id}", response_model=WatchlistNameOut)
def get_watchlist_name(watchlist_id: int, user: dict = Depends(require_user)):
    """
    Retrieve a specific watchlist container by its ID.
    Endpoint: GET /api/watchlist/watchlistname/{watchlist_id}
    """
    
    try:
        conn, cur = get_db_connection()
        from models import WatchlistName
        watchlist = WatchlistName.get_by_id(cur, watchlist_id)
        if not watchlist:
            raise HTTPException(status_code=404, detail="Watchlist not found")
        return WatchlistNameOut(
            id=watchlist.id,
            name=watchlist.name,
            created_at=watchlist.created_at.isoformat()
        )
    except Exception as e:
        logger.error(f"Error in get_watchlist_name: {e}")
        raise HTTPException(status_code=500, detail="Error fetching watchlist")


@router.delete("/watchlistname/remove/{watchlist_id}", response_model=dict)
def delete_watchlist_name(
    watchlist_id: int, 
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_admin)
):
    """
    Delete a watchlist container by its ID.
    Endpoint: DELETE /api/watchlist/watchlistname/remove/{watchlist_id}
    """
    
    try:
        conn, cur = get_db_connection()
        from models import WatchlistName
        deleted = WatchlistName.delete(cur, watchlist_id)
        conn.commit()
        if deleted:
            payload = {
                "action": "deleted_watchlist",
                "watchlist_id": watchlist_id
            }
            background_tasks.add_task(
                lambda: asyncio.run(process_and_send_watchlist_update_message(payload))
            )
            return {"detail": "Watchlist deleted"}
        else:
            raise HTTPException(status_code=404, detail="Watchlist not found")
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in delete_watchlist_name: {e}")
        raise HTTPException(status_code=500, detail="Error deleting watchlist")

