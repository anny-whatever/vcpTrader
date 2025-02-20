# kite_auth.py
import os
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from .kite_ticker import initialize_kite_ticker
from .schedulers import get_scheduler
from auth import create_access_token, require_admin

load_dotenv()
logger = logging.getLogger(__name__)
router = APIRouter()

kite = KiteConnect(api_key=os.getenv("API_KEY"))

@router.get("/auth")
async def auth():
    try:
        login_url = kite.login_url()
        # If a scheduler is running, shut it down to ensure a fresh start later.
        current_scheduler = get_scheduler()
        if current_scheduler.running:
            current_scheduler.shutdown()
            logger.info("Scheduler shutdown before authentication redirect.")
        return RedirectResponse(url=login_url)
    except Exception as e:
        logger.error(f"Error in /auth endpoint: {e}")
        raise HTTPException(status_code=500, detail="Kite authentication initiation failed")
    
@router.get("/callback")
async def callback(request_token: str, background_tasks: BackgroundTasks):
    from services import get_instrument_indices, get_instrument_equity, load_ohlc_data
    # Reinitialize the scheduler if needed (a new one will be created if the previous one was shut down)
    current_scheduler = get_scheduler()
    try:
        # Generate session and get access token from Kite
        session = kite.generate_session(request_token, os.getenv("API_SECRET"))
        access_token = session["access_token"]
        kite.set_access_token(access_token)
        
        # Initialize KiteTicker and load required data
        get_instrument_indices()
        get_instrument_equity()
        initialize_kite_ticker(access_token)
        
        # Offload the heavy task to a background thread
        background_tasks.add_task(load_ohlc_data)

        logger.info("Kite authentication callback successful.")
        # Redirect to frontend with a success flag
        return RedirectResponse(url="https://devstatz.com?login=true&kiteAuth=success")
    except Exception as e:
        logger.error(f"Error in /callback endpoint: {e}")
        raise HTTPException(status_code=400, detail="Kite callback failed")
