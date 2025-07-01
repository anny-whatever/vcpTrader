#!/usr/bin/env python3
"""
Background Worker Process for Heavy Operations

This process runs separately from the main web server to handle
CPU and I/O intensive tasks without blocking API responses.
"""

import asyncio
import logging
import signal
import sys
import os
from datetime import datetime, time
import multiprocessing as mp
from typing import Dict, Any

# Add src to path for imports
sys.path.append(os.path.dirname(__file__))

from controllers.optimized_schedulers import OptimizedScheduler
from services.optimized_ohlc_collector import OptimizedOHLCCollector
from services.optimized_risk_calculator import OptimizedRiskCalculator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler('background_worker.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class BackgroundWorker:
    """Background worker for heavy operations"""
    
    def __init__(self):
        self.scheduler = OptimizedScheduler()
        self.running = False
        self.processes: Dict[str, mp.Process] = {}
        
        # Initialize optimized services
        self.ohlc_collector = OptimizedOHLCCollector()
        self.risk_calculator = OptimizedRiskCalculator()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.stop()
    
    async def start(self):
        """Start the background worker"""
        logger.info("Starting background worker...")
        self.running = True
        
        # Start the optimized scheduler
        await self.scheduler.start()
        
        # Main worker loop
        while self.running:
            try:
                # Check for scheduled tasks
                await self._check_scheduled_tasks()
                
                # Monitor running processes
                await self._monitor_processes()
                
                # Sleep for a short interval
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in background worker loop: {e}")
                await asyncio.sleep(30)  # Wait longer on error
        
        logger.info("Background worker stopped")
    
    async def _check_scheduled_tasks(self):
        """Check if any scheduled tasks need to run"""
        current_time = datetime.now().time()
        
        # OHLC Collection - 15:35 daily
        if current_time.hour == 15 and current_time.minute == 35:
            if not self._is_process_running('ohlc_collection'):
                await self._start_ohlc_collection()
        
        # VCP Screening - 10:00, 12:00, 14:00
        screening_times = [time(10, 0), time(12, 0), time(14, 0)]
        if current_time.replace(second=0, microsecond=0) in screening_times:
            if not self._is_process_running('vcp_screening'):
                await self._start_vcp_screening()
        
        # Risk Calculation - 16:00 daily
        if current_time.hour == 16 and current_time.minute == 0:
            if not self._is_process_running('risk_calculation'):
                await self._start_risk_calculation()
    
    def _is_process_running(self, process_name: str) -> bool:
        """Check if a process is currently running"""
        process = self.processes.get(process_name)
        return process is not None and process.is_alive()
    
    async def _start_ohlc_collection(self):
        """Start OHLC collection in separate process"""
        logger.info("Starting OHLC collection process...")
        
        def run_ohlc_collection():
            try:
                import asyncio
                asyncio.run(self.ohlc_collector.collect_all_ohlc_data())
            except Exception as e:
                logger.error(f"Error in OHLC collection process: {e}")
        
        process = mp.Process(target=run_ohlc_collection, name="ohlc_collection")
        process.start()
        self.processes['ohlc_collection'] = process
        
        logger.info(f"OHLC collection process started with PID: {process.pid}")
    
    async def _start_vcp_screening(self):
        """Start VCP screening in separate process using sequential processing"""
        logger.info("Starting sequential VCP screening process...")
        
        def run_vcp_screening():
            try:
                from services.get_screener import run_advanced_vcp_screener
                result = run_advanced_vcp_screener()  # Now uses sequential processing by default
                logger.info(f"Sequential VCP screening completed with result: {result}")
            except Exception as e:
                logger.error(f"Error in sequential VCP screening process: {e}")
        
        process = mp.Process(target=run_vcp_screening, name="vcp_screening")
        process.start()
        self.processes['vcp_screening'] = process
        
        logger.info(f"Sequential VCP screening process started with PID: {process.pid}")
    
    async def _start_risk_calculation(self):
        """Start risk calculation in separate process"""
        logger.info("Starting risk calculation process...")
        
        def run_risk_calculation():
            try:
                import asyncio
                # Get all active symbols
                symbols = self.risk_calculator.get_all_symbols()
                asyncio.run(self.risk_calculator.calculate_batch_risk_scores(symbols))
            except Exception as e:
                logger.error(f"Error in risk calculation process: {e}")
        
        process = mp.Process(target=run_risk_calculation, name="risk_calculation")
        process.start()
        self.processes['risk_calculation'] = process
        
        logger.info(f"Risk calculation process started with PID: {process.pid}")
    
    async def _monitor_processes(self):
        """Monitor running processes and clean up completed ones"""
        completed_processes = []
        
        for name, process in self.processes.items():
            if not process.is_alive():
                exit_code = process.exitcode
                if exit_code == 0:
                    logger.info(f"Process {name} completed successfully")
                else:
                    logger.warning(f"Process {name} exited with code {exit_code}")
                
                process.join()  # Clean up the process
                completed_processes.append(name)
        
        # Remove completed processes
        for name in completed_processes:
            del self.processes[name]
    
    def stop(self):
        """Stop the background worker and all processes"""
        logger.info("Stopping background worker...")
        self.running = False
        
        # Terminate all running processes
        for name, process in self.processes.items():
            if process.is_alive():
                logger.info(f"Terminating process {name}...")
                process.terminate()
                
                # Wait for process to terminate gracefully
                process.join(timeout=30)
                
                # Force kill if it doesn't terminate
                if process.is_alive():
                    logger.warning(f"Force killing process {name}")
                    process.kill()
                    process.join()
        
        # Stop the scheduler
        if hasattr(self.scheduler, 'stop'):
            self.scheduler.stop()
        
        logger.info("Background worker stopped successfully")

def main():
    """Main entry point for the background worker"""
    logger.info("VCP Trader Background Worker starting...")
    
    # Check if we're the main process
    if mp.current_process().name != 'MainProcess':
        logger.error("Background worker must be run as the main process")
        sys.exit(1)
    
    # Create and start the worker
    worker = BackgroundWorker()
    
    try:
        # Run the async worker
        asyncio.run(worker.start())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error in background worker: {e}")
        sys.exit(1)
    finally:
        worker.stop()

if __name__ == "__main__":
    main() 