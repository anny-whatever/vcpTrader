import logging
from datetime import datetime, time as dtime, timedelta
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.base import STATE_RUNNING



logger = logging.getLogger(__name__)
scheduler = None

#
# Existing Jobs
#

def check_exits_on_schedule():
    try:
        logger.info("Checking for exits")
        # Add your exit checking logic here
    except Exception as e:
        logger.error(f"Error in check_exits_on_schedule: {e}")

def get_ohlc_on_schedule():
    try:
        # Import only inside the function to avoid circular imports
        from services import (
            get_equity_ohlc_data_loop,
            download_nse_csv,
            load_precomputed_ohlc
        )
        download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv", "500")
        download_nse_csv("https://nsearchives.nseindia.com/content/indices/ind_niftymicrocap250_list.csv", "250")
        download_nse_csv("https://www.niftyindices.com/IndexConstituent/ind_niftyIPO_list.csv", "IPO")
        download_nse_csv("https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv", "ALL")

        get_equity_ohlc_data_loop("day")
        get_equity_ohlc_data_loop("week")
        load_precomputed_ohlc()

        run_vcp_screener_on_schedule()
        run_ipo_screener_on_schedule()
        run_weekly_vcp_screener_on_schedule()

        logger.info("OHLC data retrieval job completed.")
    except Exception as e:
        logger.error(f"Error in get_ohlc_on_schedule: {e}")

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

def run_weekly_vcp_screener_on_schedule():
    try:
        from services import run_weekly_vcp_screener
        run_weekly_vcp_screener()
    except Exception as e:
        logger.error(f"Error in run_vcp_screener_on_schedule: {e}")

#
# Utility to decide if we are within the time range for resampling
#
def is_within_resample_time_range():
    now = datetime.now().time()
    RESAMPLE_START_TIME = dtime(9, 15)
    RESAMPLE_END_TIME   = dtime(15, 30, 5)
    return RESAMPLE_START_TIME <= now <= RESAMPLE_END_TIME

#
# New Resample Jobs for 1/5/15-min
#
def resample_job_one_minute():
    """
    Grabs last 1 minute's raw ticks, resamples to 1-min candles, stores in 'ohlc_resampled'.
    """
    try:
        from services import calculate_ohlcv_1min
        end_time = datetime.now().replace(second=0, microsecond=0)
        start_time_one_min = end_time - timedelta(minutes=1)
        instrument_tokens = [256265, 260105, 257801]  # Example tokens

        if is_within_resample_time_range():
            logger.info("Running 1-minute resample job...")
            calculate_ohlcv_1min(instrument_tokens, start_time_one_min, end_time)
        else:
            logger.info("Outside trading hours, skipping 1-min resample job.")

    except Exception as e:
        logger.error(f"Error in resample_job_one_minute: {e}")

def is_within_strategy_time_range():
    now = datetime.now().time()
    STRATEGY_START_TIME = dtime(9, 20)
    STRATEGY_END_TIME = dtime(15, 25)
    return STRATEGY_START_TIME <= now <= STRATEGY_END_TIME

def resample_job_five_minute():
    """
    Resamples 1-min data into 5-min candles and, if within trading and strategy times,
    launches the 5EMA short strategy runner on separate threads.
    """
    try:
        from signals import fema_runner_five_minute_short, fema_runner_fifteen_minute_long
        from services import calculate_ohlcv_5min
        end_time = datetime.now().replace(second=0, microsecond=0)
        start_time_five_min = end_time - timedelta(minutes=5)
        sleep(0.5)  # Small delay if needed

        if is_within_resample_time_range():
            logger.info("Running 5-minute resample job...")
            calculate_ohlcv_5min([256265, 260105, 257801], start_time_five_min, end_time)
        else:
            logger.info("Outside trading hours, skipping 5-min resample job.")

        if is_within_strategy_time_range():
            with ThreadPoolExecutor(max_workers=3) as executor:
                # Launch the short strategy runner for each index
                executor.submit(fema_runner_five_minute_short, 'nifty', 'fema_five_short')
                executor.submit(fema_runner_five_minute_short, 'banknifty', 'fema_five_short')
        else:
            logger.info("Outside strategy time range, not launching short strategy runner.")
    except Exception as e:
        logger.error(f"Error in resample_job_five_minute: {e}")

def resample_job_fifteen_minute():
    """
    Resamples 1-min data into 15-min candles and, if within trading and strategy times,
    launches the 5EMA long strategy runner on separate threads.
    """
    try:
        from signals import fema_runner_five_minute_short, fema_runner_fifteen_minute_long
        from services import calculate_ohlcv_15min
        end_time = datetime.now().replace(second=0, microsecond=0)
        start_time_fifteen_min = end_time - timedelta(minutes=15)
        sleep(0.5)  # Small delay if needed
        if is_within_resample_time_range():
            logger.info("Running 15-minute resample job...")
            calculate_ohlcv_15min([256265, 260105, 257801], start_time_fifteen_min, end_time)
        else:
            logger.info("Outside trading hours, skipping 15-min resample job.")

        if is_within_strategy_time_range():
            with ThreadPoolExecutor(max_workers=3) as executor:
                # Launch the long strategy runner for each index
                executor.submit(fema_runner_fifteen_minute_long, 'nifty', 'fema_fifteen_long')
                executor.submit(fema_runner_fifteen_minute_long, 'banknifty', 'fema_fifteen_long')
        else:
            logger.info("Outside strategy time range, not launching long strategy runner.")
    except Exception as e:
        logger.error(f"Error in resample_job_fifteen_minute: {e}")

#
# Main function to get and/or start the scheduler
#
def get_scheduler():
    """
    Returns a running scheduler. If the global scheduler is None or not running,
    it creates a new one, adds all jobs, and starts it.
    """
    global scheduler
    if scheduler is None or scheduler.state != STATE_RUNNING:
        scheduler = BackgroundScheduler()

        # -- Existing daily jobs --
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

        # VCP screener jobs => runs multiple times daily
        scheduler.add_job(
            run_vcp_screener_on_schedule,
            CronTrigger(day_of_week='mon-fri', hour='9', minute='15-59'),
            max_instances=3,
            replace_existing=False,
            id="run_vcp_screener_job_part1"
        )
        scheduler.add_job(
            run_vcp_screener_on_schedule,
            CronTrigger(day_of_week='mon-fri', hour='10-14', minute='*'),
            max_instances=3,
            replace_existing=False,
            id="run_vcp_screener_job_part2"
        )
        scheduler.add_job(
            run_vcp_screener_on_schedule,
            CronTrigger(day_of_week='mon-fri', hour='15', minute='0-30'),
            max_instances=3,
            replace_existing=False,
            id="run_vcp_screener_job_part3"
        )
        
        # Weekly VCP screener jobs => runs less frequently (every 5 minutes)
        scheduler.add_job(
            run_weekly_vcp_screener_on_schedule,
            CronTrigger(day_of_week='mon-fri', hour='9', minute='15,20,25,30,35,40,45,50,55'),
            max_instances=2,
            replace_existing=False,
            id="run_weekly_vcp_screener_job_part1"
        )
        scheduler.add_job(
            run_weekly_vcp_screener_on_schedule,
            CronTrigger(day_of_week='mon-fri', hour='10-14', minute='0,5,10,15,20,25,30,35,40,45,50,55'),
            max_instances=2,
            replace_existing=False,
            id="run_weekly_vcp_screener_job_part2"
        )
        scheduler.add_job(
            run_weekly_vcp_screener_on_schedule,
            CronTrigger(day_of_week='mon-fri', hour='15', minute='0,5,10,15,20,25,30'),
            max_instances=2,
            replace_existing=False,
            id="run_weekly_vcp_screener_job_part3"
        )

        # IPO screener jobs => runs multiple times daily
        scheduler.add_job(
            run_ipo_screener_on_schedule,
            CronTrigger(day_of_week='mon-fri', hour='9', minute='15-59'),
            max_instances=3,
            replace_existing=False,
            id="run_ipo_screener_job_part1"
        )
        scheduler.add_job(
            run_ipo_screener_on_schedule,
            CronTrigger(day_of_week='mon-fri', hour='10-14', minute='*'),
            max_instances=3,
            replace_existing=False,
            id="run_ipo_screener_job_part2"
        )
        scheduler.add_job(
            run_ipo_screener_on_schedule,
            CronTrigger(day_of_week='mon-fri', hour='15', minute='0-30'),
            max_instances=3,
            replace_existing=False,
            id="run_ipo_screener_job_part3"
        )

        # -- New 1/5/15-min resample jobs --
        scheduler.add_job(
            resample_job_one_minute,
            CronTrigger(minute='*/1', hour='9-15', day_of_week='mon-fri'),
            max_instances=1,
            replace_existing=True,
            id="resample_job_one_minute"
        )
        scheduler.add_job(
            resample_job_five_minute,
            CronTrigger(minute='*/5', hour='9-15', day_of_week='mon-fri'),
            max_instances=1,
            replace_existing=True,
            id="resample_job_five_minute"
        )
        scheduler.add_job(
            resample_job_fifteen_minute,
            CronTrigger(minute='*/15', hour='9-15', day_of_week='mon-fri'),
            max_instances=1,
            replace_existing=True,
            id="resample_job_fifteen_minute"
        )

        # Start the scheduler
        scheduler.start()
        logger.info("Scheduler started.")

    return scheduler
