# schedulers.py
import time
import datetime
import logging
from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()

def check_exits_on_schedule():
    try:
        logger.info("Checking for exits")
        # Add exit checking logic here if needed
    except Exception as e:
        logger.error(f"Error in check_exits_on_schedule: {e}")

def get_ohlc_on_schedule():
    try:
        from services import get_equity_ohlc_data_loop, download_nse_csv, load_ohlc_data
        get_equity_ohlc_data_loop("day")
        download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv", "500")
        download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv", "250")
        download_nse_csv("https://www.niftyindices.com/IndexConstituent/ind_niftyIPO_list.csv", "IPO")
        download_nse_csv("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv", "ALL")
        load_ohlc_data()
        logger.info("OHLC data retrieval job completed.")
    except Exception as e:
        logger.error(f"Error in get_ohlc_on_schedule: {e}")

def setup_scheduler():
    try:
        scheduler.add_job(
            check_exits_on_schedule,
            CronTrigger(minute='25', hour='15', day_of_week='mon-fri'),
            max_instances=1,
            replace_existing=True,
            id="vcp_trader_check_exits"
        )
    
        scheduler.add_job(
            get_ohlc_on_schedule,
            CronTrigger(minute='31', hour='15', day_of_week='mon-fri'),
            max_instances=1,
            replace_existing=True,
            id="vcp_trader_get_ohlc"
        )
    
        scheduler.start()
        logger.info("Scheduler started.")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
