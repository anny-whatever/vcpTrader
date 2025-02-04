import os
from time import sleep
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from requests import get
from .kite_ticker import initialize_kite_ticker, kite_ticker
from .schedulers import scheduler, setup_scheduler   

load_dotenv()

router = APIRouter()

kite = KiteConnect(
    api_key=os.getenv("API_KEY")
)

# Global KiteTicker instance to be set after authentication
kite_ticker = None

@router.get("/auth")
async def auth():
    global kite_ticker
    login_url = kite.login_url()
    if scheduler.running:
        scheduler.shutdown()
    kite_ticker = None

    return RedirectResponse(url=login_url)
    

@router.get("/callback")
async def callback(request_token: str):
    from services import get_instrument_indices,  get_instrument_equity, load_ohlc_data, download_nse_csv
    if not scheduler.running:
        setup_scheduler()
    try:
        # Generate session and get access token
        session = kite.generate_session(request_token, os.getenv("API_SECRET"))
        access_token = session["access_token"]
        kite.set_access_token(access_token)

        # Initialize KiteTicker
        get_instrument_indices()
        get_instrument_equity()
        initialize_kite_ticker(access_token)
        load_ohlc_data ()
        
        download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",  "500")
        download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv",  "250")
        download_nse_csv("https://www.niftyindices.com/IndexConstituent/ind_niftyIPO_list.csv",  "IPO")

        
        return RedirectResponse(url="http://localhost:5173?login=true")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))