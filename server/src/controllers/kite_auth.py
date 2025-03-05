import os
import logging
import asyncio
import atexit
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

# Global ThreadPoolExecutor
thread_pool = ThreadPoolExecutor(max_workers=5)

# Global variable to hold our ticker equity process
equity_process = None

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
    from services import get_instrument_indices, get_instrument_equity, get_instrument_fno, generate_option_chain_nifty, generate_option_chain_fin_nifty, generate_option_chain_bank_nifty, filter_expiry_dates
    from signals import initialize_long_strategy_state, initialize_short_strategy_state
    global equity_process
    try:
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
        initialize_long_strategy_state('fema_five_long')
        initialize_short_strategy_state('fema_five_short')
        initialize_kite_ticker(access_token)

        # Start the equity ticker in a separate process if not already running.
        # from .run_kite_ticker_equity import main as run_equity_ticker
        # if equity_process and equity_process.is_alive():
        #     logger.info("KiteTickerEquity process already running. Not starting a new one.")
        # else:
        #     equity_process = Process(target=run_equity_ticker, args=(access_token,), daemon=True)
        #     equity_process.start()
        #     logger.info("Started KiteTickerEquity process.")

        logger.info("Kite authentication callback successful.")
        return RedirectResponse(url="https://devstatz.com?login=true&kiteAuth=success")

    except Exception as e:
        logger.error(f"Error in /callback endpoint: {e}")
        raise HTTPException(status_code=400, detail="Kite callback failed")

# @atexit.register
# def cleanup():
#     """Terminate process on FastAPI shutdown."""
#     global equity_process
#     if equity_process and equity_process.is_alive():
#         equity_process.terminate()
#         equity_process.join()
#         logger.info("KiteTickerEquity process terminated on FastAPI shutdown.")
