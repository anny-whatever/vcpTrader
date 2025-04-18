import logging
from db import get_trade_db_connection, release_trade_db_connection
from models import SaveTradeDetails
from .manage_risk_pool import check_risk_pool_availability_for_buy, apply_risk_pool_update_on_buy
import datetime
import threading
import time
import queue
from controllers import kite

logger = logging.getLogger(__name__)

buy_entry_lock = threading.Lock()
buy_entry_running = False
order_status_queue = queue.Queue()

def buy_order_execute(symbol, qty):
    """
    Executes a buy order for the given symbol and quantity.
    """
    global buy_entry_running
    conn, cur = get_trade_db_connection()

    try:
        # Check if a trade already exists for the symbol
        if get_trade_id_by_symbol(cur, symbol):
            print(f"Trade already exists for {symbol}")
            logger.info(f"Trade already exists for {symbol}")
            return {
                "status": "error",
                "message": f"Trade for '{symbol}' already exists. Please exit the existing position before buying again."
            }

        with buy_entry_lock:
            if buy_entry_running:
                print("Buy entry already running")
                logger.info("Buy entry already running")
                return {
                    "status": "error",
                    "message": f"A buy order is already in progress for {symbol}. Please wait until it completes."
                }
            buy_entry_running = True

        try:
            # Fetch live entry price and calculate stop-loss
            ltp_data = kite.ltp(f"NSE:{symbol}")
            entry_price = ltp_data[f"NSE:{symbol}"]['last_price']
            stop_loss = entry_price - (entry_price * 0.1)  # Example: 10% stop-loss
        except Exception as e:
            print(f"Error fetching LTP for {symbol}: {e}")
            logger.error(f"Error fetching LTP for {symbol}: {e}")
            return {"status": "error", "message": f"Error fetching LTP for {symbol}: {str(e)}"}

        try:
            # Check risk pool availability
            check_risk_pool_availability_for_buy(cur, entry_price, stop_loss, qty)
        except ValueError as e:
            print(f"Risk pool availability check failed: {e}")
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
        print(f"Order placed: {response_buy}")
        logger.info(f"Order placed for {symbol}: {response_buy}")

        # Start a thread to monitor the order status; pass symbol as an extra parameter.
        threading.Thread(
            target=monitor_order_status,
            args=(response_buy, qty, entry_price, stop_loss, symbol, 300)
        ).start()

        status = order_status_queue.get(timeout=305)
        print(f"Final Order Status: {status}")
        logger.info(f"Final Order Status for {symbol}: {status}")
        return status

    except Exception as e:
        print(f"Error executing buy order: {e}")
        logger.exception(f"Error executing buy order for {symbol}: {e}")
        return {
            "status": "error",
            "message": f"An error occurred while executing the buy order for {symbol}. Error: {str(e)}"
        }
    finally:
        with buy_entry_lock:
            buy_entry_running = False
        release_trade_db_connection(conn, cur)

def monitor_order_status(order_id, qty, entry_price, stop_loss, symbol, timeout=300):
    """
    Monitors the order status and updates the risk pool after order completion.
    """
    conn, cur = get_trade_db_connection()
    try:
        start_time = time.time()
        while time.time() - start_time < timeout:
            buy_order = kite.order_history(order_id)
            buy_status = buy_order[-1]['status']
            buy_status_message = buy_order[-1]['status_message']
            print(f"Order Status: {buy_status}")
            logger.info(f"Order Status for {symbol}: {buy_status}")

            if buy_status == 'COMPLETE':
                avg_price = buy_order[-1].get('average_price', entry_price)
                target = avg_price + (avg_price * 0.2)  # Example: 20% target
                message = (f"Buy order executed successfully for {symbol}. "
                        f"Quantity: {qty}, Avg Price: {avg_price:.2f}, "
                        f"Stop Loss: {stop_loss:.2f}, Target: {target:.2f}.")
                order_status_queue.put({"status": "success", "message": message})
                print(f"Order completed: {buy_order}")
                logger.info(f"Order completed for {symbol}: {buy_order}")

                # Apply risk pool update with actual order price
                apply_risk_pool_update_on_buy(cur, avg_price, stop_loss, qty)

                # Save trade details including the new auto_exit flag (set to False by default)
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
                    auto_exit=False  # New field as per the updated table
                ).save(cur)
                conn.commit()
                break

            elif buy_status == 'REJECTED':
                message = (f"Buy order for {symbol} was rejected. "
                        f"Reason: {buy_status_message}.")
                order_status_queue.put({"status": "error", "message": message})
                print(f"Order rejected: {buy_order}")
                logger.warning(f"Order rejected for {symbol}: {buy_order}")
                order_status_queue.put({"status": "error", "message": f"Order monitoring timed out for {symbol}."})
                print("Order monitoring timed out")
                break

            time.sleep(1)  # Adjust polling frequency as needed

    except Exception as e:
        error_message = f"Order monitoring error for {symbol}: {str(e)}"
        order_status_queue.put({"status": "error", "message": error_message})
        print(f"Error monitoring order status: {e}")
        logger.exception(f"Error monitoring order status for {symbol}: {e}")
    finally:
        release_trade_db_connection(conn, cur)

def get_trade_id_by_symbol(cur, symbol):
    """
    Retrieve the trade ID based on the stock symbol.
    """
    try:
        query = "SELECT trade_id FROM trades WHERE stock_name = %s;"
        cur.execute(query, (symbol,))
        result = cur.fetchone()
        return result['trade_id'] if result else None
    except Exception as e:
        print(f"Error retrieving trade ID: {e}")
        logger.error(f"Error retrieving trade ID for symbol {symbol}: {e}")
        return None
