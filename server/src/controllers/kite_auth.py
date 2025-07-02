import os
import logging
import asyncio
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

from .kite_ticker import initialize_kite_ticker
from .optimized_schedulers import get_optimized_scheduler as get_scheduler

load_dotenv()
logger = logging.getLogger(__name__)
router = APIRouter()

kite = KiteConnect(api_key=os.getenv("API_KEY"))

# Global ThreadPoolExecutor
thread_pool = ThreadPoolExecutor(max_workers=5)

async def generate_session_async(request_token):
    """Run kite.generate_session in a separate thread to prevent blocking."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, lambda: kite.generate_session(request_token, os.getenv("API_SECRET")))

@router.get("/auth")
async def auth():
    """Initiate the Kite authentication flow."""
    try:
        login_url = kite.login_url()
        current_scheduler = get_scheduler()
        if current_scheduler.running:
            current_scheduler.shutdown()
            logger.info("Scheduler shutdown before authentication redirect.")
        return RedirectResponse(url=login_url)
    except Exception as e:
        logger.error(f"Error in /auth endpoint: {e}")
        raise HTTPException(status_code=500, detail="Kite authentication initiation failed")

@router.get("/callback")
async def callback(request_token: str):
    """Handles the callback after the user logs in via Kite."""
    try:
        # Lazy import to avoid circular dependencies
        from services import get_instrument_indices, get_instrument_equity, get_instrument_fno, generate_option_chain_nifty, generate_option_chain_fin_nifty, generate_option_chain_bank_nifty, filter_expiry_dates
        
        current_scheduler = get_scheduler()
        
        # Generate session asynchronously
        session = await generate_session_async(request_token)
        access_token = session["access_token"]
        kite.set_access_token(access_token)
        
        get_instrument_fno()
        get_instrument_indices()
        get_instrument_equity()
        filter_expiry_dates() 
        generate_option_chain_nifty()
        generate_option_chain_bank_nifty()
        generate_option_chain_fin_nifty()

        initialize_kite_ticker(access_token)

        logger.info("Kite authentication callback successful.")
        return RedirectResponse(url="https://tradekeep.in?login=true&kiteAuth=success")

    except Exception as e:
        logger.error(f"Error in /callback endpoint: {e}")
        raise HTTPException(status_code=400, detail="Kite callback failed")
