import os
from time import sleep
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from kiteconnect import KiteConnect
from dotenv import load_dotenv
from requests import get


from .kite_ticker import initialize_kite_ticker

load_dotenv()

router = APIRouter()

kite = KiteConnect(
    api_key=os.getenv("API_KEY")
)

# Global KiteTicker instance to be set after authentication
kite_ticker = None

@router.get("/auth")
async def auth():
    login_url = kite.login_url()
    return RedirectResponse(url=login_url)
    

@router.get("/callback")
async def callback(request_token: str):
    
    from services import get_instrument_indices,  get_instrument_equity


    try:
        # Generate session and get access token
        session = kite.generate_session(request_token, os.getenv("API_SECRET"))
        access_token = session["access_token"]
        kite.set_access_token(access_token)

        # Initialize KiteTicker
    

        get_instrument_indices()
        get_instrument_equity()
        initialize_kite_ticker(access_token)
        
        sleep(1)
        # print(get_strikes_from_nifty_by_delta_put(0, 0.5))
        # print(get_strikes_from_nifty_by_delta_call(0, 0.5))
        # sma_bounce_fifteen_minute_buy_entry()
        
        
        # get_strikes_from_nifty_by_steps_pair(0, 0)
        # print(get_strikes_from_nifty_by_steps_call(0, -1))
        # print(get_strikes_from_nifty_by_steps_put(0, -1))
        
        
        
        
        # get_historical_data_with_atr()
        
        
        return RedirectResponse(url="http://localhost:5173?login=true")

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


