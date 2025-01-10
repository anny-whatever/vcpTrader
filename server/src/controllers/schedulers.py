from concurrent.futures import ThreadPoolExecutor
import datetime
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from time import sleep
from datetime import datetime, time, timedelta


scheduler = BackgroundScheduler()


RESAMPLE_START_TIME = time(9, 15)
RESAMPLE_END_TIME = time(15, 30, 5)

STRATEGY_START_TIME = time(9, 15)
STRATEGY_END_TIME = time(15, 29, 50)

def is_within_resample_time_range():
    now = datetime.now().time()
    return RESAMPLE_START_TIME <= now <= RESAMPLE_END_TIME

def is_within_strategy_time_range():
    now = datetime.now().time()
    return STRATEGY_START_TIME <= now <= STRATEGY_END_TIME
    

def check_exits():
    print("Checking for exits")

# Scheduler Setup
def setup_scheduler():
    # Also run 60-minute job at 3:15 and 3:30 PM
    scheduler.add_job(
        check_exits,
        CronTrigger(minute='20', hour='15', day_of_week='mon-fri'),
        max_instances=1,
        replace_existing=True,
        id="vcp_trader_check_exits"
    )
    
    scheduler.start()