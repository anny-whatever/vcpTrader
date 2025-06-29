import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from concurrent.futures import ThreadPoolExecutor

# If you have an auth file for user authentication:
from auth import get_current_user

from services import fetch_screener_data, run_advanced_vcp_screener, load_precomputed_ohlc

logger = logging.getLogger(__name__)
router = APIRouter()

# Dedicated thread pool for manual screener requests
# This is separate from the scheduled screeners
manual_screener_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="manual_screener")

@router.get("/vcpscreen")
async def screen_vcp(user: dict = Depends(get_current_user)):
    """
    Returns the most recently saved VCP screener results from the screener_results table as JSON.
    If there's no data, it will retry up to 5 times (1-second pause).
    If still empty, it will run_vcp_screener() to force generation, and then fetch again.
    If still empty after forcing the screener, it will run it one more time.
    """
    try:
        max_tries = 5
        for attempt in range(1, max_tries + 1):
            # Make the fetch call in a thread so we don't block the event loop
            data = await asyncio.to_thread(fetch_screener_data, "vcp")
            if data:  # If we got results, return them immediately
                logger.info(f"Returning VCP screener data with {len(data)} results")
                return JSONResponse(content=data)

            logger.debug(f"No VCP screener data found (attempt {attempt}/{max_tries}). Retrying in 1 second...")
            await asyncio.sleep(1)

        # If we still have no data, run the VCP screener to force generation
        logger.debug("No data after 5 tries. Forcing a run of the advanced VCP screener.")
        # Use our dedicated thread pool for manual screening
        success = await asyncio.wrap_future(manual_screener_executor.submit(run_advanced_vcp_screener))
        
        if not success:
            logger.error("Advanced VCP screener run failed. Will try one more time.")
            # Try running it one more time immediately
            success = await asyncio.wrap_future(manual_screener_executor.submit(run_advanced_vcp_screener))
            if not success:
                logger.error("Second advanced VCP screener run also failed.")
                return JSONResponse(content={"error": "Failed to generate advanced VCP screener data"}, status_code=500)

        # After forcing the screener, fetch one more time
        data = await asyncio.to_thread(fetch_screener_data, "vcp")
        if data:
            logger.info(f"Returning VCP screener data with {len(data)} results after forced run")
            return JSONResponse(content=data)
            
        # If still no data, run the screener one more time
        logger.debug("No data after first run. Running advanced VCP screener one more time.")
        success = await asyncio.wrap_future(manual_screener_executor.submit(run_advanced_vcp_screener))
        if not success:
            logger.error("Final advanced VCP screener run failed.")
            return JSONResponse(content={"error": "Failed to generate advanced VCP screener data after multiple attempts"}, status_code=500)
        
        # Fetch data one final time
        data = await asyncio.to_thread(fetch_screener_data, "vcp")
        if data:
            logger.info(f"Returning VCP screener data with {len(data)} results after second forced run")
            return JSONResponse(content=data)
        else:
            logger.error("No VCP screener data found after multiple attempts")
            return JSONResponse(content={"error": "No VCP screener data found after multiple attempts"}, status_code=404)

    except Exception as e:
        logger.error(f"Error in screen_vcp: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch VCP screener data")

@router.get("/test_screener_data")
async def test_screener_data(user: dict = Depends(get_current_user)):
    """
    Diagnostic endpoint to test OHLC data structure and screener functionality.
    Returns some debug information about the loaded OHLC data.
    """
    try:
        # Testing the regular OHLC data
        logger.info("Loading OHLC data for diagnostics...")
        regular_ohlc = await asyncio.to_thread(load_precomputed_ohlc)
        
        # Collect diagnostics info
        diagnostics = {
            "regular_ohlc": {
                "data_exists": not regular_ohlc.empty,
                "row_count": len(regular_ohlc) if not regular_ohlc.empty else 0,
                "column_count": len(regular_ohlc.columns) if not regular_ohlc.empty else 0,
                "columns": list(regular_ohlc.columns) if not regular_ohlc.empty else [],
                "unique_symbols": list(regular_ohlc['symbol'].unique())[:20] if not regular_ohlc.empty else [],
                "symbol_count": len(regular_ohlc['symbol'].unique()) if not regular_ohlc.empty else 0,
                "date_range": [
                    regular_ohlc['date'].min().isoformat() if not regular_ohlc.empty else None,
                    regular_ohlc['date'].max().isoformat() if not regular_ohlc.empty else None
                ],
                "has_IPO_segment": "IPO" in regular_ohlc['segment'].unique() if not regular_ohlc.empty else False,
                "segments": list(regular_ohlc['segment'].unique()) if not regular_ohlc.empty else []
            }
        }
        
        return JSONResponse(content=diagnostics)
    except Exception as e:
        logger.error(f"Error in test_screener_data: {e}")
        raise HTTPException(status_code=500, detail=f"Diagnostic test failed: {str(e)}")
