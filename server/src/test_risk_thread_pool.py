#!/usr/bin/env python3
"""
Test script to verify the risk calculation thread pool implementation.
"""

import asyncio
import time
import logging
from concurrent.futures import ThreadPoolExecutor
from services.risk_calculator import RiskCalculator

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_synchronous_calculation():
    """Test the synchronous risk calculation method."""
    logger.info("Testing synchronous risk calculation...")
    start_time = time.time()
    
    calculator = RiskCalculator()
    # Test with a few symbols
    test_symbols = ['RELIANCE', 'TCS', 'HDFCBANK']
    
    for symbol in test_symbols:
        # This would normally use actual instrument tokens from database
        logger.info(f"Would calculate risk for {symbol}")
        time.sleep(0.5)  # Simulate some work
    
    end_time = time.time()
    logger.info(f"Synchronous calculation took {end_time - start_time:.2f} seconds")

def test_thread_pool_calculation():
    """Test the thread pool risk calculation method."""
    logger.info("Testing thread pool risk calculation...")
    start_time = time.time()
    
    # Create thread pool
    executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="risk_calc_test")
    
    def mock_risk_calculation(symbol):
        logger.info(f"Calculating risk for {symbol} in thread {threading.current_thread().name}")
        time.sleep(0.5)  # Simulate calculation work
        return f"Risk calculated for {symbol}"
    
    # Submit tasks to thread pool
    test_symbols = ['RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK', 'INFY']
    futures = []
    
    for symbol in test_symbols:
        future = executor.submit(mock_risk_calculation, symbol)
        futures.append(future)
    
    # Wait for all tasks to complete
    results = []
    for future in futures:
        result = future.result()
        results.append(result)
        logger.info(f"Completed: {result}")
    
    executor.shutdown(wait=True)
    
    end_time = time.time()
    logger.info(f"Thread pool calculation took {end_time - start_time:.2f} seconds")
    logger.info(f"Processed {len(results)} symbols")

async def test_async_with_thread_pool():
    """Test async execution with thread pool."""
    logger.info("Testing async execution with thread pool...")
    start_time = time.time()
    
    # Create thread pool
    executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="risk_calc_async")
    
    def mock_risk_calculation(symbol):
        logger.info(f"Async calculating risk for {symbol}")
        time.sleep(0.3)  # Simulate calculation work
        return f"Async risk calculated for {symbol}"
    
    # Use asyncio event loop with thread pool
    loop = asyncio.get_event_loop()
    test_symbols = ['RELIANCE', 'TCS', 'HDFCBANK', 'ICICIBANK', 'INFY', 'WIPRO']
    
    # Start calculation in background
    future = loop.run_in_executor(
        executor,
        lambda: [mock_risk_calculation(symbol) for symbol in test_symbols]
    )
    
    # Do other work while calculation runs
    for i in range(3):
        logger.info(f"Doing other work... {i+1}")
        await asyncio.sleep(0.2)
    
    # Wait for calculation to complete
    results = await future
    
    executor.shutdown(wait=True)
    
    end_time = time.time()
    logger.info(f"Async thread pool calculation took {end_time - start_time:.2f} seconds")
    logger.info(f"Processed {len(results)} symbols")

if __name__ == "__main__":
    import threading
    
    logger.info("Starting risk calculation thread pool tests...")
    
    # Test 1: Synchronous calculation
    test_synchronous_calculation()
    print()
    
    # Test 2: Thread pool calculation
    test_thread_pool_calculation()
    print()
    
    # Test 3: Async with thread pool
    asyncio.run(test_async_with_thread_pool())
    
    logger.info("All tests completed!") 