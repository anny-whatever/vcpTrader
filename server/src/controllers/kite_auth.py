# kite_auth.py
import os
import datetime
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from .kite_ticker import initialize_kite_ticker
from .schedulers import scheduler, setup_scheduler
from auth import create_access_token, require_admin


load_dotenv()
logger = logging.getLogger(__name__)
router = APIRouter()

kite = KiteConnect(api_key=os.getenv("API_KEY"))

# Global KiteTicker instance to be set after authentication

@router.get("/auth")
async def auth():
    try:
        login_url = kite.login_url()
        if scheduler.running:
            scheduler.shutdown()
        return RedirectResponse(url=login_url)
    except Exception as e:
        logger.error(f"Error in /auth endpoint: {e}")
        raise HTTPException(status_code=500, detail="Kite authentication initiation failed")
    
@router.get("/callback")
async def callback(request_token: str):
    from services import get_instrument_indices, get_instrument_equity
    if not scheduler.running:
        setup_scheduler()
    try:
        # Generate session and get access token from Kite
        session = kite.generate_session(request_token, os.getenv("API_SECRET"))
        access_token = session["access_token"]
        kite.set_access_token(access_token)
        # Initialize KiteTicker and load required data
        get_instrument_indices()
        get_instrument_equity()
        initialize_kite_ticker(access_token)


        # Redirect to frontend with a success flag
        return RedirectResponse(url="https://devstatz.com?login=true&kiteAuth=success")
    except Exception as e:
        logger.error(f"Error in /callback endpoint: {e}")
        raise HTTPException(status_code=400, detail="Kite callback failed")
