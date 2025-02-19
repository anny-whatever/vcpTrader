# schedulers.py
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.base import STATE_RUNNING

logger = logging.getLogger(__name__)
scheduler = None

def check_exits_on_schedule():
    try:
        logger.info("Checking for exits")
        # Add your exit checking logic here
    except Exception as e:
        logger.error(f"Error in check_exits_on_schedule: {e}")

def get_ohlc_on_schedule():
    try:
        from services import get_equity_ohlc_data_loop, download_nse_csv, load_ohlc_data
        download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv", "500")
        download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv", "250")
        download_nse_csv("https://www.niftyindices.com/IndexConstituent/ind_niftyIPO_list.csv", "IPO")
        download_nse_csv("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv", "ALL")
        get_equity_ohlc_data_loop("day")
        load_ohlc_data()
        logger.info("OHLC data retrieval job completed.")
    except Exception as e:
        logger.error(f"Error in get_ohlc_on_schedule: {e}")

def get_scheduler():
    """
    Returns a running scheduler. If the global scheduler is None or not running,
    a new BackgroundScheduler is created, jobs are added, and it is started.
    """
    global scheduler
    if scheduler is None or scheduler.state != STATE_RUNNING:
        scheduler = BackgroundScheduler()
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
    return scheduler
