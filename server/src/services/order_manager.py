import logging
import threading
import time
import queue
import asyncio
from concurrent.futures import ThreadPoolExecutor
from controllers import kite
from controllers.ws_clients import process_and_send_update_message
from db import get_trade_db_connection, release_trade_db_connection

logger = logging.getLogger(__name__)

# Thread-local storage to track active orders per thread 
_thread_local = threading.local()

class OrderManager:
    """
    Manages all order operations (buy, sell, adjust) using a thread pool
    to prevent blocking the main application thread.
    """
    
    def __init__(self, max_workers=5):
        """
        Initialize the OrderManager with a thread pool and shared resources.
        
        Args:
            max_workers: Maximum number of concurrent order operations
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.order_queues = {}  # Symbol-specific queues for order operations
        self.order_locks = {}   # Symbol-specific locks
        self.global_lock = threading.Lock()  # Lock for creating new queues/locks
        self.active_orders = {}  # Track currently active orders by symbol
        self.active_orders_lock = threading.Lock()  # Lock for the active_orders dict
        
    def get_order_resources(self, symbol):
        """Get or create queue and lock for a specific symbol"""
        with self.global_lock:
            if symbol not in self.order_queues:
                self.order_queues[symbol] = queue.Queue()
                self.order_locks[symbol] = threading.Lock()
            return self.order_queues[symbol], self.order_locks[symbol]
    
    def execute_buy(self, symbol, qty, callback=None):
        """
        Schedule a buy order execution in the thread pool.
        
        Args:
            symbol: Trading symbol
            qty: Quantity to buy
            callback: Optional function to call with the result
        
        Returns:
            Future object representing the pending operation
        """
        # First check if there's already an active order for this symbol
        with self.active_orders_lock:
            if symbol in self.active_orders:
                order_info = self.active_orders[symbol]
                return {"status": "error", "message": f"Order already in progress for {symbol} (type: {order_info['type']})"}
        
        future = self.executor.submit(self._buy_order_execute, symbol, qty)
        
        # Register order and wrap callback to ensure cleanup
        with self.active_orders_lock:
            self.active_orders[symbol] = {"type": "buy", "future": future}
        
        def wrapped_callback(result):
            try:
                # If the order was successful, trigger token refresh and socket update
                if result.get("status") == "success":
                    self._refresh_tokens_and_send_update()
                
                if callback:
                    callback(result)
            finally:
                # Always clean up active orders entry when finished
                with self.active_orders_lock:
                    if symbol in self.active_orders:
                        del self.active_orders[symbol]
        
        future.add_done_callback(lambda f: wrapped_callback(f.result()))
        return {"status": "processing", "message": f"Buy order for {symbol} (qty: {qty}) submitted for processing"}
    
    def execute_sell(self, symbol, callback=None):
        """
        Schedule a sell order execution in the thread pool.
        
        Args:
            symbol: Trading symbol
            callback: Optional function to call with the result
        
        Returns:
            Future object representing the pending operation
        """
        # First check if there's already an active order for this symbol
        with self.active_orders_lock:
            if symbol in self.active_orders:
                order_info = self.active_orders[symbol]
                return {"status": "error", "message": f"Order already in progress for {symbol} (type: {order_info['type']})"}
        
        future = self.executor.submit(self._sell_order_execute, symbol)
        
        # Register order and wrap callback to ensure cleanup
        with self.active_orders_lock:
            self.active_orders[symbol] = {"type": "sell", "future": future}
        
        def wrapped_callback(result):
            try:
                # If the order was successful, trigger token refresh and socket update
                if result.get("status") == "success":
                    self._refresh_tokens_and_send_update()
                
                if callback:
                    callback(result)
            finally:
                # Always clean up active orders entry when finished
                with self.active_orders_lock:
                    if symbol in self.active_orders:
                        del self.active_orders[symbol]
        
        future.add_done_callback(lambda f: wrapped_callback(f.result()))
        return {"status": "processing", "message": f"Sell order for {symbol} submitted for processing"}
    
    def execute_adjust(self, symbol, qty, adjustment_type, callback=None):
        """
        Schedule an adjustment order execution in the thread pool.
        
        Args:
            symbol: Trading symbol
            qty: Quantity to adjust
            adjustment_type: 'increase' or 'decrease'
            callback: Optional function to call with the result
        
        Returns:
            Future object representing the pending operation
        """
        # First check if there's already an active order for this symbol
        with self.active_orders_lock:
            if symbol in self.active_orders:
                order_info = self.active_orders[symbol]
                return {"status": "error", "message": f"Order already in progress for {symbol} (type: {order_info['type']})"}
        
        future = self.executor.submit(
            self._adjust_order_execute, symbol, qty, adjustment_type)
        
        # Register order and wrap callback to ensure cleanup
        with self.active_orders_lock:
            self.active_orders[symbol] = {"type": f"adjust-{adjustment_type}", "future": future}
        
        def wrapped_callback(result):
            try:
                # If the order was successful, trigger token refresh and socket update
                if result.get("status") == "success":
                    self._refresh_tokens_and_send_update()
                
                if callback:
                    callback(result)
            finally:
                # Always clean up active orders entry when finished
                with self.active_orders_lock:
                    if symbol in self.active_orders:
                        del self.active_orders[symbol]
        
        future.add_done_callback(lambda f: wrapped_callback(f.result()))
        return {"status": "processing", "message": f"{adjustment_type.capitalize()} order for {symbol} (qty: {qty}) submitted for processing"}
    
    def _refresh_tokens_and_send_update(self):
        """
        Refresh the tokens and send an update to the frontend.
        This is called after successful order operations to ensure:
        1. The ticker subscriptions are updated with the latest tokens
        2. The frontend is notified to refresh its data
        """
        try:
            # 1. Update the filtered_tokens global variable
            from services.get_essential_tokens import refresh_tokens
            refresh_tokens()
            
            # 2. Update the kite_ticker subscription with the new tokens
            from services.get_essential_tokens import filtered_tokens
            from controllers.kite_ticker import update_kite_ticker_subscription
            update_kite_ticker_subscription(filtered_tokens)
            
            # 3. Send a WebSocket update to the frontend
            self._send_websocket_update()
            
            logger.info("Successfully refreshed tokens and sent update")
        except Exception as e:
            logger.error(f"Error in _refresh_tokens_and_send_update: {e}")
    
    def _send_websocket_update(self):
        """
        Send a WebSocket update to all connected clients to notify them of changes.
        """
        try:
            # Create a new event loop for the async operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Run the async function in the new loop
                loop.run_until_complete(process_and_send_update_message())
            finally:
                # Clean up
                loop.close()
            
            logger.info("WebSocket update sent successfully")
        except Exception as e:
            logger.error(f"Error sending WebSocket update: {e}")
    
    def get_order_status(self, symbol):
        """Get the current status of any active order for a symbol"""
        with self.active_orders_lock:
            if symbol in self.active_orders:
                order_info = self.active_orders[symbol]
                # Check if the future is done
                if order_info["future"].done():
                    try:
                        result = order_info["future"].result()
                        return {"status": "completed", "order_type": order_info["type"], "result": result}
                    except Exception as e:
                        return {"status": "error", "order_type": order_info["type"], "message": str(e)}
                else:
                    return {"status": "processing", "order_type": order_info["type"]}
            else:
                return {"status": "no_active_orders", "message": f"No active orders found for {symbol}"}
    
    def _buy_order_execute(self, symbol, qty):
        """Execute a buy order for the given symbol and quantity."""
        # Set thread local to track the current operation
        _thread_local.current_symbol = symbol
        _thread_local.current_operation = "buy"
        
        order_queue, order_lock = self.get_order_resources(symbol)
        
        # Try to acquire the lock, return immediately if another operation
        # is already in progress for this symbol
        if not order_lock.acquire(blocking=False):
            return {
                "status": "error",
                "message": f"Another order operation is already in progress for {symbol}."
            }
        
        conn, cur = None, None
        try:
            conn, cur = get_trade_db_connection()
            
            # Check if a trade already exists for the symbol
            from services.place_buy import get_trade_id_by_symbol
            if get_trade_id_by_symbol(cur, symbol):
                return {
                    "status": "error",
                    "message": f"Trade already exists for '{symbol}'. Please exit the existing position before buying again."
                }
                
            # Fetch live entry price
            try:
                ltp_data = kite.ltp(f"NSE:{symbol}")
                entry_price = ltp_data[f"NSE:{symbol}"]['last_price']
                stop_loss = entry_price - (entry_price * 0.1)  # Example: 10% stop-loss
            except Exception as e:
                logger.error(f"Error fetching LTP for {symbol}: {e}")
                return {"status": "error", "message": f"Error fetching LTP for {symbol}: {str(e)}"}
                
            # Check risk pool availability
            try:
                from services.manage_risk_pool import check_risk_pool_availability_for_buy
                check_risk_pool_availability_for_buy(cur, entry_price, stop_loss, qty)
            except ValueError as e:
                logger.error(f"Risk pool availability check failed for {symbol}: {e}")
                return {
                    "status": "error",
                    "message": f"Insufficient risk pool for {symbol}. Entry Price: {entry_price:.2f}, Stop Loss: {stop_loss:.2f}, Quantity: {qty}."
                }
                
            # Place the buy order
            response_buy = kite.place_order(
                variety='regular',
                exchange='NSE',
                tradingsymbol=symbol,
                transaction_type='BUY',
                quantity=qty,
                product='CNC',
                order_type='MARKET'
            )
            logger.info(f"Order placed for {symbol}: {response_buy}")
            
            # Monitor the order status
            return self._monitor_buy_order(
                response_buy, qty, entry_price, stop_loss, symbol, cur, conn)
                
        except Exception as e:
            logger.exception(f"Error executing buy order for {symbol}: {e}")
            if conn:
                conn.rollback()
            return {
                "status": "error",
                "message": f"An error occurred while executing the buy order for {symbol}. Error: {str(e)}"
            }
        finally:
            if conn:
                release_trade_db_connection(conn, cur)
            order_lock.release()
            
            # Clear thread local
            if hasattr(_thread_local, 'current_symbol'):
                del _thread_local.current_symbol
            if hasattr(_thread_local, 'current_operation'):
                del _thread_local.current_operation
    
    def _monitor_buy_order(self, order_id, qty, entry_price, stop_loss, symbol, cur, conn, timeout=60):
        """Monitor a buy order until it completes or times out."""
        max_retries = 3  # Add retry for transient failures
        retry_count = 0
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                buy_order = kite.order_history(order_id)
                buy_status = buy_order[-1]['status']
                logger.info(f"Order Status for {symbol}: {buy_status}")
                
                if buy_status == 'COMPLETE':
                    avg_price = buy_order[-1].get('average_price', entry_price)
                    target = avg_price + (avg_price * 0.2)  # Example: 20% target
                    
                    # Apply risk pool update with actual order price
                    from services.manage_risk_pool import apply_risk_pool_update_on_buy
                    apply_risk_pool_update_on_buy(cur, avg_price, stop_loss, qty)
                    
                    # Save trade details 
                    from models import SaveTradeDetails
                    SaveTradeDetails(
                        stock_name=buy_order[-1]['tradingsymbol'],
                        token=buy_order[-1]['instrument_token'],
                        entry_time=buy_order[-1]['exchange_timestamp'],
                        entry_price=avg_price,
                        stop_loss=stop_loss,
                        target=target,
                        initial_qty=qty,
                        current_qty=qty,
                        booked_pnl=0,
                        auto_exit=False
                    ).save(cur)
                    conn.commit()
                    
                    message = (f"Buy order executed successfully for {symbol}. "
                            f"Quantity: {qty}, Avg Price: {avg_price:.2f}, "
                            f"Stop Loss: {stop_loss:.2f}, Target: {target:.2f}.")
                    return {"status": "success", "message": message}
                    
                elif buy_status == 'REJECTED' or buy_status == 'CANCELLED':
                    buy_status_message = buy_order[-1].get('status_message', '')
                    message = (f"Buy order for {symbol} was {buy_status.lower()}. "
                            f"Reason: {buy_status_message}.")
                    return {"status": "error", "message": message}
                    
                time.sleep(1)
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"Retry {retry_count}/{max_retries} for monitoring buy order {order_id}: {e}")
                if retry_count >= max_retries:
                    return {"status": "error", "message": f"Failed to monitor order status after {max_retries} retries: {str(e)}"}
                time.sleep(2)  # Wait before retrying
        
        return {"status": "error", "message": f"Order monitoring timed out for {symbol}."}
    
    def _sell_order_execute(self, symbol):
        """Execute a sell order to exit a trade."""
        # Set thread local to track the current operation
        _thread_local.current_symbol = symbol
        _thread_local.current_operation = "sell"
        
        order_queue, order_lock = self.get_order_resources(symbol)
        
        # Try to acquire the lock, return immediately if another operation
        # is already in progress for this symbol
        if not order_lock.acquire(blocking=False):
            return {
                "status": "error",
                "message": f"Another order operation is already in progress for {symbol}."
            }
        
        conn, cur = None, None
        try:
            conn, cur = get_trade_db_connection()
            
            # Fetch the current trade details
            cur.execute("""
                SELECT trade_id, entry_time, entry_price, current_qty, booked_pnl, stop_loss, 
                       adjustments, initial_qty
                FROM trades 
                WHERE stock_name = %s;
            """, (symbol,))
            trade = cur.fetchone()
            
            if not trade:
                return {
                    "status": "error",
                    "message": f"No active trade found for {symbol}. Please ensure you have an open position before exiting."
                }
                
            # Extract trade details
            trade_id = trade['trade_id']
            entry_time = trade['entry_time']
            entry_price = float(trade['entry_price'])
            current_qty = float(trade['current_qty'])
            booked_pnl = float(trade['booked_pnl'])
            stop_loss = float(trade['stop_loss'])
            
            # Calculate highest quantity ever held
            if 'initial_qty' in trade and trade['initial_qty'] is not None:
                initial_qty = float(trade['initial_qty'])
            else:
                initial_qty = current_qty
                
            # Calculate adjustments (simplified for this example)
            highest_qty = initial_qty
            
            if current_qty <= 0:
                return {
                    "status": "error", 
                    "message": f"No quantity left to exit for {symbol}. Current Quantity: {current_qty}."
                }
                
            # Place the sell order
            response_sell = kite.place_order(
                variety='regular',
                exchange='NSE',
                tradingsymbol=symbol,
                transaction_type='SELL',
                quantity=int(current_qty),
                product='CNC',
                order_type='MARKET'
            )
            logger.info(f"Sell order placed for {symbol}: {response_sell}")
            
            # Monitor the sell order status
            return self._monitor_sell_order(
                response_sell, trade_id, symbol, entry_time, entry_price, 
                current_qty, booked_pnl, stop_loss, highest_qty, cur, conn)
                
        except Exception as e:
            logger.exception(f"Error executing exit strategy for {symbol}: {e}")
            if conn:
                conn.rollback()
            return {
                "status": "error",
                "message": f"Error executing exit strategy for {symbol}. Please try again. ({str(e)})"
            }
        finally:
            if conn:
                release_trade_db_connection(conn, cur)
            order_lock.release()
            
            # Clear thread local
            if hasattr(_thread_local, 'current_symbol'):
                del _thread_local.current_symbol
            if hasattr(_thread_local, 'current_operation'):
                del _thread_local.current_operation
    
    def _monitor_sell_order(self, order_id, trade_id, symbol, entry_time, entry_price, 
                         current_qty, booked_pnl, stop_loss, highest_qty, cur, conn, timeout=60):
        """Monitor a sell order until it completes or times out."""
        max_retries = 3  # Add retry for transient failures
        retry_count = 0
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                sell_order = kite.order_history(order_id)
                sell_status = sell_order[-1]['status']
                logger.info(f"Sell Order Status for {symbol}: {sell_status}")
                
                if sell_status == 'COMPLETE':
                    exit_price = float(sell_order[-1]['average_price'])
                    unrealized_pnl = (exit_price - entry_price) * current_qty
                    final_pnl = booked_pnl + unrealized_pnl
                    
                    # Update risk pool
                    from services.manage_risk_pool import update_risk_pool_on_exit
                    update_risk_pool_on_exit(cur, stop_loss, entry_price, exit_price, current_qty)
                    
                    # Save trade details to the historical_trades table
                    from models import SaveHistoricalTradeDetails
                    SaveHistoricalTradeDetails(
                        stock_name=symbol,
                        entry_time=entry_time,
                        entry_price=entry_price,
                        exit_time=sell_order[-1]['exchange_timestamp'],
                        exit_price=exit_price,
                        final_pnl=final_pnl,
                        highest_qty=highest_qty
                    ).save(cur)
                    
                    # Delete the trade from the active trades table
                    cur.execute("DELETE FROM trades WHERE trade_id = %s;", (trade_id,))
                    conn.commit()
                    
                    message = (
                        f"Exit successful for {symbol}: Sold {current_qty} shares at {exit_price:.2f} "
                        f"(Entry: {entry_price:.2f}, Stop-loss: {stop_loss:.2f}, Highest Qty Held: {highest_qty}). "
                        f"Final PnL: {final_pnl:.2f}."
                    )
                    return {"status": "success", "message": message}
                    
                elif sell_status == 'REJECTED' or sell_status == 'CANCELLED':
                    sell_status_message = sell_order[-1].get('status_message', '')
                    message = f"Exit for {symbol} was {sell_status.lower()}. Reason: {sell_status_message}."
                    return {"status": "error", "message": message}
                    
                time.sleep(1)
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"Retry {retry_count}/{max_retries} for monitoring sell order {order_id}: {e}")
                if retry_count >= max_retries:
                    return {"status": "error", "message": f"Failed to monitor order status after {max_retries} retries: {str(e)}"}
                time.sleep(2)  # Wait before retrying
            
        return {
            "status": "error",
            "message": f"Sell order monitoring for {symbol} timed out after {timeout} seconds."
        }
    
    def _adjust_order_execute(self, symbol, qty, adjustment_type):
        """Execute an adjustment to an existing order."""
        # Set thread local to track the current operation
        _thread_local.current_symbol = symbol
        _thread_local.current_operation = f"adjust-{adjustment_type}"
        
        order_queue, order_lock = self.get_order_resources(symbol)
        
        # Try to acquire the lock, return immediately if another operation
        # is already in progress for this symbol
        if not order_lock.acquire(blocking=False):
            return {
                "status": "error",
                "message": f"Another order operation is already in progress for {symbol}."
            }
        
        conn, cur = None, None
        try:
            conn, cur = get_trade_db_connection()
            
            # Retrieve the trade details
            cur.execute("""
                SELECT trade_id, entry_price, stop_loss, current_qty 
                FROM trades 
                WHERE stock_name = %s;
            """, (symbol,))
            trade = cur.fetchone()
            
            if not trade:
                return {
                    "status": "error",
                    "message": f"No active position found for {symbol}. Cannot perform a {adjustment_type} adjustment."
                }
                
            trade_id = trade['trade_id']
            entry_price = float(trade['entry_price'])
            stop_loss = float(trade['stop_loss'])
            current_qty = float(trade['current_qty'])
            qty = float(qty)
            
            if adjustment_type == 'decrease' and qty >= current_qty:
                return {
                    "status": "error",
                    "message": f"Cannot decrease by {qty}, only {current_qty} available. Please perform a full exit if you want to sell."
                }
                
            transaction_type = 'BUY' if adjustment_type == 'increase' else 'SELL'
            response_adjust = kite.place_order(
                variety='regular',
                exchange='NSE',
                tradingsymbol=symbol,
                transaction_type=transaction_type,
                quantity=int(qty),
                product='CNC',
                order_type='MARKET'
            )
            logger.info(f"Adjustment order placed for {symbol}: {response_adjust}")
            
            # Monitor the adjustment order status
            return self._monitor_adjustment_order(
                response_adjust, trade_id, qty, adjustment_type, entry_price, 
                stop_loss, symbol, cur, conn)
                
        except Exception as e:
            logger.exception(f"Adjustment Error ({adjustment_type}) for {symbol}: {e}")
            if conn:
                conn.rollback()
            return {
                "status": "error",
                "message": f"Adjustment error for {symbol} ({adjustment_type}): {str(e)}"
            }
        finally:
            if conn:
                release_trade_db_connection(conn, cur)
            order_lock.release()
            
            # Clear thread local
            if hasattr(_thread_local, 'current_symbol'):
                del _thread_local.current_symbol
            if hasattr(_thread_local, 'current_operation'):
                del _thread_local.current_operation
    
    def _monitor_adjustment_order(self, order_id, trade_id, qty, adjustment_type, 
                              entry_price, stop_loss, symbol, cur, conn, timeout=60):
        """Monitor an adjustment order until it completes or times out."""
        import datetime
        from services.place_adjust import update_trade_record
        
        max_retries = 3  # Add retry for transient failures
        retry_count = 0
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                adjust_order = kite.order_history(order_id)
                adjust_status = adjust_order[-1]['status']
                logger.info(f"Adjustment Order Status for {symbol}: {adjust_status}")
                
                if adjust_status == 'COMPLETE':
                    actual_price = float(adjust_order[-1].get('average_price', 0))
                    if actual_price == 0:
                        return {
                            "status": "error",
                            "message": "Adjustment order completed, but no valid average price available."
                        }
                    
                    if adjustment_type == 'increase':
                        from services.manage_risk_pool import update_risk_pool_on_increase
                        update_risk_pool_on_increase(cur, stop_loss, actual_price, qty)
                    elif adjustment_type == 'decrease':
                        from services.manage_risk_pool import update_risk_pool_on_decrease
                        update_risk_pool_on_decrease(cur, stop_loss, entry_price, actual_price, qty)
                    
                    update_trade_record(cur, conn, trade_id, qty, actual_price, adjustment_type)
                    
                    message = (
                        f"Adjustment ({adjustment_type.capitalize()}) for {symbol} executed successfully: "
                        f"{qty} shares adjusted at an average price of {actual_price:.2f} "
                        f"(Entry: {entry_price:.2f}, Stop-loss: {stop_loss:.2f})."
                    )
                    return {"status": "success", "message": message}
                    
                elif adjust_status == 'REJECTED' or adjust_status == 'CANCELLED':
                    adjust_status_message = adjust_order[-1].get('status_message', '')
                    message = f"Adjustment ({adjustment_type.capitalize()}) for {symbol} was {adjust_status.lower()}. Reason: {adjust_status_message}."
                    return {"status": "error", "message": message}
                    
                time.sleep(1)
                
            except Exception as e:
                retry_count += 1
                logger.warning(f"Retry {retry_count}/{max_retries} for monitoring adjustment order {order_id}: {e}")
                if retry_count >= max_retries:
                    return {"status": "error", "message": f"Failed to monitor order status after {max_retries} retries: {str(e)}"}
                time.sleep(2)  # Wait before retrying
            
        return {
            "status": "error",
            "message": f"Adjustment ({adjustment_type.capitalize()}) monitoring for {symbol} timed out after {timeout} seconds."
        }

# Create a global instance of the OrderManager
order_manager = OrderManager(max_workers=10)

# Convenience functions for external code
def execute_buy(symbol, qty, callback=None):
    return order_manager.execute_buy(symbol, qty, callback)

def execute_sell(symbol, callback=None):
    return order_manager.execute_sell(symbol, callback)

def execute_adjust(symbol, qty, adjustment_type, callback=None):
    return order_manager.execute_adjust(symbol, qty, adjustment_type, callback)

def get_order_status(symbol):
    return order_manager.get_order_status(symbol) 