import os
import logging
import time
from controllers.kite_ticker_equity import initialize_kite_ticker_equity
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

def main(access_token: str):
    if not access_token:
        logger.error("ACCESS_TOKEN not provided to run_kite_ticker_equity.")
        return

    # Initialize the equity ticker with the provided access token.
    initialize_kite_ticker_equity(access_token)
    
    # Keep this process alive indefinitely.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("KiteTickerEquity process interrupted. Exiting.")

if __name__ == "__main__":
    import sys
    # Allow passing the token via command-line argument if needed.
    access_token = sys.argv[1] if len(sys.argv) > 1 else None
    main(access_token)
