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
        from services import (
            get_equity_ohlc_data_loop,
            download_nse_csv,
        )
        download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv", "500")
        download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv", "250")
        download_nse_csv("https://www.niftyindices.com/IndexConstituent/ind_niftyIPO_list.csv", "IPO")
        download_nse_csv("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv", "ALL")
        get_equity_ohlc_data_loop("day")
        logger.info("OHLC data retrieval job completed.")
    except Exception as e:
        logger.error(f"Error in get_ohlc_on_schedule: {e}")

#
# NEW: We'll add two screener jobs for VCP and IPO.
#

def run_vcp_screener_on_schedule():
    try:
        from services import run_vcp_screener
        run_vcp_screener()
    except Exception as e:
        logger.error(f"Error in run_vcp_screener_on_schedule: {e}")

def run_ipo_screener_on_schedule():
    try:
        from services import run_ipo_screener
        run_ipo_screener()
    except Exception as e:
        logger.error(f"Error in run_ipo_screener_on_schedule: {e}")

def get_scheduler():
    """
    Returns a running scheduler. If the global scheduler is None or not running,
    a new BackgroundScheduler is created, jobs are added, and it is started.
    """
    global scheduler
    if scheduler is None or scheduler.state != STATE_RUNNING:
        scheduler = BackgroundScheduler()

        # Existing jobs
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

        #
        #  NEW: Add VCP & IPO screener jobs => runs every 1 minute, Mon-Fri, 9:00-15:59
        #       We rely on the screener function to skip if time < 9:15 or > 15:30
        #
        scheduler.add_job(
            run_vcp_screener_on_schedule,
            CronTrigger(
                day_of_week='mon-fri',
                hour='9-15',         # 9 AM through 3 PM
                minute='*'
            ),
            max_instances=3,       # allow parallel runs if one is slow
            replace_existing=False,
            id="run_vcp_screener_job"
        )
        scheduler.add_job(
            run_ipo_screener_on_schedule,
            CronTrigger(
                day_of_week='mon-fri',
                hour='9-15',
                minute='*'
            ),
            max_instances=3,
            replace_existing=False,
            id="run_ipo_screener_job"
        )

        scheduler.start()
        logger.info("Scheduler started.")
    return scheduler
