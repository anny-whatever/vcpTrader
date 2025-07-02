import logging
from datetime import datetime, time as dtime, timedelta
from concurrent.futures import ThreadPoolExecutor
from time import sleep
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.base import STATE_RUNNING
import os
import threading

logger = logging.getLogger(__name__)
scheduler = None

# Optimized thread pool configuration
# Reduce thread pool sizes to prevent system overload
screener_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="opt_screener")
ohlc_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="opt_ohlc")
risk_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="opt_risk")

# Task status tracking
task_status = {
    'ohlc_collection': {'running': False, 'last_run': None, 'last_duration': None},
    'vcp_screening': {'running': False, 'last_run': None, 'last_duration': None},
    'risk_calculation': {'running': False, 'last_run': None, 'last_duration': None}
}
status_lock = threading.Lock()

def update_task_status(task_name: str, running: bool, duration: float = None):
    """Update task status in a thread-safe manner."""
    with status_lock:
        task_status[task_name]['running'] = running
        if not running:
            task_status[task_name]['last_run'] = datetime.now().isoformat()
            if duration:
                task_status[task_name]['last_duration'] = duration

def get_task_status():
    """Get current task status."""
    with status_lock:
        return task_status.copy()

#
# Optimized Jobs
#

def calculate_daily_risk_scores_optimized():
    """
    Optimized risk calculation with better resource management.
    """
    if task_status['risk_calculation']['running']:
        logger.info("Risk calculation already running, skipping this invocation")
        return
    
    start_time = datetime.now()
    update_task_status('risk_calculation', True)
    
    try:
        logger.info("Starting optimized daily risk scores calculation...")
        from services.optimized_risk_calculator import calculate_daily_risk_scores_optimized
        
        result_count = calculate_daily_risk_scores_optimized()
        
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Optimized risk calculation completed: {result_count} stocks processed in {duration:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error in optimized risk calculation: {e}")
    finally:
        duration = (datetime.now() - start_time).total_seconds()
        update_task_status('risk_calculation', False, duration)

def get_ohlc_on_schedule_optimized():
    """
    Optimized OHLC data collection with parallel processing.
    """
    if task_status['ohlc_collection']['running']:
        logger.info("OHLC collection already running, skipping this invocation")
        return
    
    start_time = datetime.now()
    update_task_status('ohlc_collection', True)
    
    try:
        logger.info("Starting optimized OHLC data collection...")
        from services.optimized_ohlc_collector import get_ohlc_on_schedule_optimized
        
        result = get_ohlc_on_schedule_optimized()
        
        duration = (datetime.now() - start_time).total_seconds()
        if result.get('success'):
            logger.info(f"Optimized OHLC collection completed successfully in {duration:.2f} seconds")
            logger.info(f"Success rate: {result.get('successful_fetches', 0)}/{result.get('total_tokens', 0)}")
        else:
            logger.error(f"Optimized OHLC collection failed: {result.get('error', 'Unknown error')}")
        
    except Exception as e:
        logger.error(f"Error in optimized OHLC collection: {e}")
    finally:
        duration = (datetime.now() - start_time).total_seconds()
        update_task_status('ohlc_collection', False, duration)

def run_vcp_screener_on_schedule_optimized():
    """
    Optimized VCP screener with multiprocessing.
    """
    if task_status['vcp_screening']['running']:
        logger.info("VCP screening already running, skipping this invocation")
        return
    
    start_time = datetime.now()
    update_task_status('vcp_screening', True)
    
    try:
        logger.info("Starting sequential advanced VCP screener...")
        from services.get_screener import run_advanced_vcp_screener
        
        success = run_advanced_vcp_screener()  # Now uses memory-efficient sequential processing
        
        duration = (datetime.now() - start_time).total_seconds()
        if success:
            logger.info(f"Sequential advanced VCP screener completed successfully in {duration:.2f} seconds")
        else:
            logger.warning(f"Sequential advanced VCP screener completed with issues in {duration:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error in advanced VCP screener: {e}")
    finally:
        duration = (datetime.now() - start_time).total_seconds()
        update_task_status('vcp_screening', False, duration)

def check_exits_on_schedule():
    """Keep the original exit checking logic as it's not thread-heavy."""
    try:
        # Note: check_exits_daily function doesn't exist, removing this call
        # This function should be implemented if exit checking is needed
        logger.info("Exit checking job placeholder - no implementation found.")
    except Exception as e:
        logger.error(f"Error in check_exits_on_schedule: {e}")

def clean_server_log():
    """Keep the original log cleaning logic."""
    try:
        log_file_path = os.path.join(os.path.dirname(__file__), '..', 'server.log')
        if os.path.exists(log_file_path):
            # Keep only last 1000 lines
            with open(log_file_path, 'r') as file:
                lines = file.readlines()
            
            if len(lines) > 1000:
                with open(log_file_path, 'w') as file:
                    file.writelines(lines[-1000:])
                logger.info(f"Cleaned server log, kept last 1000 lines")
            else:
                logger.info("Server log is within size limits")
        else:
            logger.info("Server log file not found")
    except Exception as e:
        logger.error(f"Error cleaning server log: {e}")

#
# Optimized Resampling Jobs with Resource Limits
#

def resample_job_one_minute_optimized():
    """Optimized 1-minute resampling with resource management."""
    try:
        from services.resample_indices import calculate_ohlcv_1min
        end_time = datetime.now().replace(second=0, microsecond=0)
        start_time_one_min = end_time - timedelta(minutes=1)
        instrument_tokens = [256265, 260105, 257801]

        if is_within_resample_time_range():
            # Use a smaller thread pool for resampling during heavy task times
            if any(task_status[task]['running'] for task in ['ohlc_collection', 'vcp_screening', 'risk_calculation']):
                logger.info("Heavy tasks running, skipping 1-min resample to conserve resources")
                return
            
            logger.info("Running optimized 1-minute resample job...")
            calculate_ohlcv_1min(instrument_tokens, start_time_one_min, end_time)
        else:
            logger.info("Outside trading hours, skipping 1-min resample job.")

    except Exception as e:
        logger.error(f"Error in optimized resample_job_one_minute: {e}")

def resample_job_five_minute_optimized():
    """Optimized 5-minute resampling with conditional strategy execution."""
    try:
        from signals import fema_runner_five_minute_short
        from services.resample_indices import calculate_ohlcv_5min
        end_time = datetime.now().replace(second=0, microsecond=0)
        start_time_five_min = end_time - timedelta(minutes=5)
        sleep(0.5)

        if is_within_resample_time_range():
            # Skip if heavy tasks are running
            if any(task_status[task]['running'] for task in ['ohlc_collection', 'vcp_screening']):
                logger.info("Heavy tasks running, skipping 5-min resample to conserve resources")
                return
                
            logger.info("Running optimized 5-minute resample job...")
            calculate_ohlcv_5min([256265, 260105, 257801], start_time_five_min, end_time)
        else:
            logger.info("Outside trading hours, skipping 5-min resample job.")

        # Only run strategy if no heavy computational tasks are running
        if is_within_strategy_time_range() and not any(task_status[task]['running'] for task in task_status):
            with ThreadPoolExecutor(max_workers=2) as executor:  # Reduced workers
                executor.submit(fema_runner_five_minute_short, 'nifty', 'fema_five_short')
                executor.submit(fema_runner_five_minute_short, 'banknifty', 'fema_five_short')
        else:
            logger.info("Skipping strategy execution - heavy tasks running or outside time range")
            
    except Exception as e:
        logger.error(f"Error in optimized resample_job_five_minute: {e}")

def resample_job_fifteen_minute_optimized():
    """Optimized 15-minute resampling with conditional strategy execution."""
    try:
        from signals import fema_runner_fifteen_minute_long
        from services.resample_indices import calculate_ohlcv_15min
        end_time = datetime.now().replace(second=0, microsecond=0)
        start_time_fifteen_min = end_time - timedelta(minutes=15)
        sleep(0.5)
        
        if is_within_resample_time_range():
            # Skip if heavy tasks are running
            if any(task_status[task]['running'] for task in ['ohlc_collection', 'vcp_screening']):
                logger.info("Heavy tasks running, skipping 15-min resample to conserve resources")
                return
                
            logger.info("Running optimized 15-minute resample job...")
            calculate_ohlcv_15min([256265, 260105, 257801], start_time_fifteen_min, end_time)
        else:
            logger.info("Outside trading hours, skipping 15-min resample job.")

        # Only run strategy if no heavy computational tasks are running
        if is_within_strategy_time_range() and not any(task_status[task]['running'] for task in task_status):
            with ThreadPoolExecutor(max_workers=2) as executor:  # Reduced workers
                executor.submit(fema_runner_fifteen_minute_long, 'nifty', 'fema_fifteen_long')
                executor.submit(fema_runner_fifteen_minute_long, 'banknifty', 'fema_fifteen_long')
        else:
            logger.info("Skipping strategy execution - heavy tasks running or outside time range")
            
    except Exception as e:
        logger.error(f"Error in optimized resample_job_fifteen_minute: {e}")

#
# Time Range Helpers
#

def is_within_resample_time_range():
    """Check if current time is within resampling hours."""
    current_time = datetime.now().time()
    return dtime(9, 15) <= current_time <= dtime(15, 35)

def is_within_strategy_time_range():
    """Check if current time is within strategy execution hours."""
    current_time = datetime.now().time()
    return dtime(9, 30) <= current_time <= dtime(15, 25)

#
# Main Optimized Scheduler
#

def get_optimized_scheduler():
    """
    Returns an optimized scheduler with better resource management.
    Reduces thread usage and prevents resource conflicts.
    """
    global scheduler
    if scheduler is None or scheduler.state != STATE_RUNNING:
        scheduler = BackgroundScheduler()

        # -- Core daily jobs with optimized timing --
        
        
        # OHLC data collection (heavy task, run once daily with optimization)
        scheduler.add_job(
            get_ohlc_on_schedule_optimized,
            CronTrigger(minute='35', hour='15', day_of_week='mon-fri'),
            max_instances=1,
            replace_existing=True,
            id="optimized_get_ohlc"
        )
        
        # Risk calculation (heavy task, run after OHLC with delay)
        scheduler.add_job(
            calculate_daily_risk_scores_optimized,
            CronTrigger(minute='30', hour='18', day_of_week='mon-fri'),  # Delayed to allow OHLC to complete
            max_instances=1,
            replace_existing=True,
            id="optimized_risk_calculation"
        )

        # VCP screener (very heavy, run less frequently)
        scheduler.add_job(
            run_vcp_screener_on_schedule_optimized,
            CronTrigger(day_of_week='mon-fri', hour='10,11,12,13,14,15', minute='0'),  # Only 3 times per day
            max_instances=1,
            replace_existing=True,
            id="optimized_vcp_screener"
        )
        scheduler.add_job(
            run_vcp_screener_on_schedule_optimized,
            CronTrigger(day_of_week='mon-fri', hour='9', minute='30'),  # 9am 
            max_instances=1,
            replace_existing=True,
            id="optimized_vcp_screener"
        )

        # -- Optimized resampling jobs with resource awareness --    

        # Log cleaning (lightweight, daily)
        scheduler.add_job(
            clean_server_log,
            CronTrigger(minute='0', hour='19'),  # Later in evening
            max_instances=1,
            replace_existing=True,
            id="optimized_clean_log"
        )

        scheduler.start()
        logger.info("Optimized scheduler started with resource-aware job configuration")

    return scheduler

def shutdown_optimized_scheduler():
    """Gracefully shutdown the optimized scheduler and thread pools."""
    global scheduler
    
    try:
        if scheduler and scheduler.state == STATE_RUNNING:
            scheduler.shutdown(wait=True)
            logger.info("Optimized scheduler shut down gracefully")
        
        # Shutdown thread pools
        screener_executor.shutdown(wait=True, timeout=30)
        ohlc_executor.shutdown(wait=True, timeout=30)
        risk_executor.shutdown(wait=True, timeout=30)
        
        logger.info("All optimized thread pools shut down gracefully")
        
    except Exception as e:
        logger.error(f"Error during optimized scheduler shutdown: {e}")

def get_scheduler_status():
    """Get comprehensive status of scheduler and tasks."""
    status = {
        "scheduler_running": scheduler is not None and scheduler.state == STATE_RUNNING,
        "task_status": get_task_status(),
        "thread_pools": {
            "screener_executor": {
                "max_workers": screener_executor._max_workers,
                "threads": len(screener_executor._threads)
            },
            "ohlc_executor": {
                "max_workers": ohlc_executor._max_workers,
                "threads": len(ohlc_executor._threads)
            },
            "risk_executor": {
                "max_workers": risk_executor._max_workers,
                "threads": len(risk_executor._threads)
            }
        }
    }
    
    if scheduler:
        status["scheduled_jobs"] = [
            {
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in scheduler.get_jobs()
        ]
    
    return status 