import os
import logging
import asyncio
from time import sleep
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from kiteconnect import KiteConnect
from dotenv import load_dotenv

from .kite_ticker import initialize_kite_ticker
from .schedulers import get_scheduler
from concurrent.futures import ThreadPoolExecutor  # Use ThreadPoolExecutor now

load_dotenv()
logger = logging.getLogger(__name__)
router = APIRouter()

kite = KiteConnect(api_key=os.getenv("API_KEY"))

# Create a global ThreadPoolExecutor
thread_pool = ThreadPoolExecutor(max_workers=5)

@router.get("/auth")
async def auth():
    """Initiate the Kite authentication flow."""
    try:
        login_url = kite.login_url()
        # If a scheduler is running, shut it down to ensure a fresh start.
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
    """
    Handles the callback after the user logs in via Kite.
    We offload load_ohlc_data to a separate thread WITHOUT awaiting it (fire-and-forget).
    """
    from services import get_instrument_indices, get_instrument_equity, load_ohlc_data

    try:
        # Reinitialize the scheduler if needed (a new one will be created if the previous one was shut down)
        current_scheduler = get_scheduler()

        # Generate session and set access token
        session = kite.generate_session(request_token, os.getenv("API_SECRET"))
        access_token = session["access_token"]
        kite.set_access_token(access_token)

        # Initialize required data and KiteTicker
        get_instrument_indices()
        get_instrument_equity()
        initialize_kite_ticker(access_token)


        logger.info("Kite authentication callback successful. load_ohlc_data is running in the background.")
        return RedirectResponse(url="https://devstatz.com?login=true&kiteAuth=success")

    except Exception as e:
        logger.error(f"Error in /callback endpoint: {e}")
        raise HTTPException(status_code=400, detail="Kite callback failed")
