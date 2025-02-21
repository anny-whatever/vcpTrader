import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse

# If you have an auth file for user authentication:
from auth import get_current_user

from services import fetch_screener_data, run_vcp_screener, run_ipo_screener

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/vcpscreen")
async def screen_vcp(user: dict = Depends(get_current_user)):
    """
    Returns the most recently saved VCP screener results from the screener_results table as JSON.
    If there's no data, it will retry up to 5 times (1-second pause).
    If still empty, it will run_vcp_screener() to force generation, and then fetch again.
    """
    try:
        max_tries = 5
        for attempt in range(1, max_tries + 1):
            # Make the fetch call in a thread so we don't block the event loop
            data = await asyncio.to_thread(fetch_screener_data, "vcp")
            if data:  # If we got results, return them immediately
                return JSONResponse(content=data)

            logger.debug(f"No VCP screener data found (attempt {attempt}/{max_tries}). Retrying in 1 second...")
            await asyncio.sleep(1)

        # If we still have no data, run the VCP screener to force generation
        logger.debug("No data after 5 tries. Forcing a run of 'run_vcp_screener()'.")
        await asyncio.to_thread(run_vcp_screener)

        # After forcing the screener, fetch one more time
        data = await asyncio.to_thread(fetch_screener_data, "vcp")
        return JSONResponse(content=data)

    except Exception as e:
        logger.error(f"Error in screen_vcp: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch VCP screener data")

@router.get("/iposcreen")
async def screen_ipo(user: dict = Depends(get_current_user)):
    """
    Returns the most recently saved IPO screener results from the screener_results table as JSON.
    If there's no data, it will retry up to 5 times (1-second pause).
    If still empty, it will run_ipo_screener() to force generation, and then fetch again.
    """
    try:
        max_tries = 5
        for attempt in range(1, max_tries + 1):
            data = await asyncio.to_thread(fetch_screener_data, "ipo")
            if data:
                return JSONResponse(content=data)

            logger.debug(f"No IPO screener data found (attempt {attempt}/{max_tries}). Retrying in 1 second...")
            await asyncio.sleep(1)

        # If no data after 5 tries, run the IPO screener forcibly
        logger.debug("No data after 5 tries. Forcing a run of 'run_ipo_screener()'.")
        await asyncio.to_thread(run_ipo_screener)

        # One final fetch after forcing the screener
        data = await asyncio.to_thread(fetch_screener_data, "ipo")
        return JSONResponse(content=data)

    except Exception as e:
        logger.error(f"Error in screen_ipo: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch IPO screener data")
