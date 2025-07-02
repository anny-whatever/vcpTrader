import logging
from datetime import datetime, time as dtime, timedelta
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.base import STATE_RUNNING
import os



logger = logging.getLogger(__name__)
scheduler = None

# DEPRECATED: This scheduler is kept for backward compatibility only
# Use controllers.optimized_schedulers.get_optimized_scheduler() instead
logger.warning("DEPRECATED: Using legacy scheduler - consider switching to optimized_schedulers.py")

# Dedicated thread pool for screeners
screener_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="screener")

#
# DEPRECATED Legacy Jobs - These functions redirect to optimized versions
#

def calculate_daily_risk_scores():
    """
    DEPRECATED: Legacy risk calculation - automatically redirects to optimized version.
    This function is kept for backward compatibility but now calls the optimized version.
    """
    logger.warning("Legacy function called - redirecting to optimized risk calculation")
    return calculate_daily_risk_scores_optimized()

def calculate_daily_risk_scores_optimized():
    """
    Optimized daily risk score calculation using parallel processing.
    This runs after the OHLC data collection completes and provides much better performance.
    """
    try:
        logger.info("Starting optimized daily risk scores calculation...")
        from services.optimized_risk_calculator import calculate_daily_risk_scores_optimized as calc_optimized
        
        # Run the optimized risk calculation
        processed_count = calc_optimized()
        
        if processed_count > 0:
            logger.info(f"✅ Optimized daily risk calculation completed: {processed_count} stocks processed")
        else:
            logger.warning("⚠️ No risk scores calculated - check if OHLC data is available")
        
        return processed_count
        
    except Exception as e:
        logger.error(f"❌ Error in optimized daily risk calculation: {e}", exc_info=True)
        return 0

def check_exits_on_schedule():
    try:
        logger.info("Checking for exits")
        # Add your exit checking logic here
    except Exception as e:
        logger.error(f"Error in check_exits_on_schedule: {e}")

def get_ohlc_on_schedule():
    """
    DEPRECATED: Legacy OHLC collection - redirects to optimized version.
    This function now uses optimized modules for better performance.
    """
    logger.warning("Legacy OHLC function called - redirecting to optimized version")
    try:
        # Import optimized modules
        from services.optimized_ohlc_collector import get_ohlc_on_schedule_optimized
        return get_ohlc_on_schedule_optimized()
        
    except Exception as e:
        logger.error(f"❌ Error in redirected OHLC collection: {e}", exc_info=True)

def run_vcp_screener_on_schedule():
    """
    DEPRECATED: Legacy VCP screener - redirects to optimized version.
    """
    logger.warning("Legacy VCP screener called - redirecting to optimized version")
    try:
        from services.get_screener import run_advanced_vcp_screener
        # Run in a separate thread to avoid blocking the scheduler
        screener_executor.submit(run_advanced_vcp_screener)
        logger.info("Advanced VCP screener job submitted to thread pool (legacy redirect)")
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
        from services.resample_indices import calculate_ohlcv_1min
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
        from services.resample_indices import calculate_ohlcv_5min
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
        from services.resample_indices import calculate_ohlcv_15min
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

def clean_server_log():
    """
    Clean the server.log file every day at 6 PM.
    This helps prevent the log file from growing too large.
    """
    try:
        log_file_path = "server.log"
        
        if os.path.exists(log_file_path):
            # Get file size before cleaning
            file_size = os.path.getsize(log_file_path)
            
            # Clear the file contents
            with open(log_file_path, 'w') as f:
                f.write("")
            
            logger.info(f"Server log cleaned. Previous size: {file_size} bytes")
        else:
            logger.warning("Server log file not found at expected location")
            
    except Exception as e:
        logger.error(f"Error in clean_server_log: {e}")

#
# Main function to get and/or start the scheduler
#
def get_scheduler():
    """
    DEPRECATED: Legacy scheduler - Use get_optimized_scheduler() from optimized_schedulers.py instead.
    This function is kept for backward compatibility but now redirects to optimized version.
    """
    logger.warning("⚠️ DEPRECATED: Legacy scheduler being used. Consider switching to optimized_schedulers.get_optimized_scheduler()")
    logger.warning("🔄 Redirecting to optimized scheduler...")
    
    try:
        from .optimized_schedulers import get_optimized_scheduler
        return get_optimized_scheduler()
    except ImportError as e:
        logger.error(f"Could not import optimized scheduler: {e}")
        logger.warning("Falling back to legacy scheduler implementation")
        
        # Fallback to legacy implementation
        global scheduler
        if scheduler is None or scheduler.state != STATE_RUNNING:
            scheduler = BackgroundScheduler()

            # Only add essential jobs with optimized functions
            scheduler.add_job(
                check_exits_on_schedule,
                CronTrigger(minute='25', hour='15', day_of_week='mon-fri'),
                max_instances=1,
                replace_existing=True,
                id="legacy_check_exits"
            )
            scheduler.add_job(
                get_ohlc_on_schedule,  # This now redirects to optimized
                CronTrigger(minute='40', hour='22', day_of_week='mon-fri'),
                max_instances=1,
                replace_existing=True,
                id="legacy_get_ohlc"
            )
            
            # Use optimized risk calculation
            scheduler.add_job(
                calculate_daily_risk_scores_optimized,
                CronTrigger(minute='00', hour='18', day_of_week='mon-fri'),
                max_instances=1,
                replace_existing=True,
                id="legacy_calculate_risk_scores"
            )

            # Use optimized VCP screener
            scheduler.add_job(
                run_vcp_screener_on_schedule,  # This now redirects to optimized
                CronTrigger(day_of_week='mon-fri', hour='9-15', minute='30,0'),
                max_instances=3,
                replace_existing=False,
                id="legacy_vcp_screener_job"
            )

            # Log cleaning job
            scheduler.add_job(
                clean_server_log,
                CronTrigger(minute='0', hour='18'),
                max_instances=1,
                replace_existing=True,
                id="legacy_clean_log"
            )

            scheduler.start()
            logger.info("Legacy scheduler started with optimized job redirects.")

        return scheduler
