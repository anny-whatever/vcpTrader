from concurrent.futures import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import datetime
import time
from datetime import datetime, time

scheduler = BackgroundScheduler()

def check_exits_on_schedule():
    print("Checking for exits")

def get_ohlc_on_schedule():
    from services import get_equity_ohlc_data_loop, download_nse_csv
    get_equity_ohlc_data_loop("day")
    download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",  "500")
    download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv",  "250")
    download_nse_csv("https://www.niftyindices.com/IndexConstituent/ind_niftyIPO_list.csv",  "IPO")
    print("Getting OHLC data")

# Scheduler Setup
def setup_scheduler():
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
    
    try:
        scheduler.start()
        print("Scheduler started.")
    except Exception as e:
        print(f"Error starting scheduler: {e}")
