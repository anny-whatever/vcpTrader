import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Process

from .kite_ticker import initialize_kite_ticker
from .schedulers import get_scheduler

load_dotenv()
logger = logging.getLogger(__name__)
router = APIRouter()

kite = KiteConnect(api_key=os.getenv("API_KEY"))

# Global ThreadPoolExecutor (for other tasks)
thread_pool = ThreadPoolExecutor(max_workers=5)

# Global variable to hold our ticker equity process.
equity_process = None

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
    """
    Handles the callback after the user logs in via Kite.
    """
    from services import get_instrument_indices, get_instrument_equity
    global equity_process
    try:
        current_scheduler = get_scheduler()

        session = kite.generate_session(request_token, os.getenv("API_SECRET"))
        access_token = session["access_token"]
        kite.set_access_token(access_token)

        get_instrument_indices()
        get_instrument_equity()
        initialize_kite_ticker(access_token)

        # Start the equity ticker in a separate process if not already running.
        if equity_process is None or not equity_process.is_alive():
            from .run_kite_ticker_equity import main as run_equity_ticker
            equity_process = Process(target=run_equity_ticker, args=(access_token,))
            equity_process.start()
            logger.info("Started KiteTickerEquity process.")

        logger.info("Kite authentication callback successful.")
        return RedirectResponse(url="https://devstatz.com?login=true&kiteAuth=success")

    except Exception as e:
        logger.error(f"Error in /callback endpoint: {e}")
        raise HTTPException(status_code=400, detail="Kite callback failed")