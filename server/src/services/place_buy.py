from db import get_trade_db_connection, release_trade_db_connection
from models import SaveTradeDetails
from .manage_risk_pool import check_risk_pool_availability_for_buy, apply_risk_pool_update_on_buy
import datetime
import threading
import time
import queue
from controllers import kite

buy_entry_lock = threading.Lock()
buy_entry_running = False
order_status_queue = queue.Queue()

def buy_order_execute(symbol, qty):
    """
    Executes a buy order for the given symbol and quantity.
    """
    global buy_entry_running
    conn, cur = get_trade_db_connection()

    # Check if a trade already exists for the symbol
    if get_trade_id_by_symbol(cur, symbol):
        print(f"Trade already exists for {symbol}")
        release_trade_db_connection(conn, cur)
        return {"status": "error", "message": f"Trade for '{symbol}' already exists."}

    with buy_entry_lock:
        if buy_entry_running:
            print("Buy entry already running")
            release_trade_db_connection(conn, cur)
            return {"status": "error", "message": "A buy order is already in progress. Please wait."}
        buy_entry_running = True

    try:
        # Fetch live entry price and calculate stop-loss
        entry_price = kite.ltp(f"NSE:{symbol}")[f"NSE:{symbol}"]['last_price']
        stop_loss = entry_price - (entry_price * 0.1)  # Example: 10% stop-loss

        # Check risk pool availability
        try:
            check_risk_pool_availability_for_buy(cur, entry_price, stop_loss, qty)
        except ValueError as e:
            print(f"Risk pool availability check failed: {e}")
            return {"status": "error", "message": "Insufficient risk pool for this order."}

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

        # Start a thread to monitor the order status
        threading.Thread(
            target=monitor_order_status,
            args=(response_buy, qty, entry_price, stop_loss, 300)
        ).start()

        status = order_status_queue.get(timeout=305)
        print(f"Final Order Status: {status}")
        return status
    except Exception as e:
        print(f"Error executing buy order: {e}")
        return {"status": "error", "message": "An error occurred while executing the buy order."}
    finally:
        with buy_entry_lock:
            buy_entry_running = False
        release_trade_db_connection(conn, cur)

def monitor_order_status(order_id, qty, entry_price, stop_loss, timeout=300):
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

            if buy_status == 'COMPLETE':
                order_status_queue.put({"status": "success", "message": "Buy order executed successfully."})
                avg_price = buy_order[-1].get('average_price', entry_price)  # Use actual avg price or fallback to entry price

                # Apply risk pool update with actual order price
                apply_risk_pool_update_on_buy(cur, avg_price, stop_loss, qty)

                # Save trade details
                SaveTradeDetails(
                    stock_name=buy_order[-1]['tradingsymbol'],
                    token=buy_order[-1]['instrument_token'],
                    entry_time=buy_order[-1]['exchange_timestamp'],
                    entry_price=avg_price,
                    stop_loss=stop_loss,
                    target=avg_price + (avg_price * 0.2),  # Example: 20% target
                    initial_qty=qty,
                    current_qty=qty,
                    booked_pnl=0
                ).save(cur)
                conn.commit()
                print(f"Order completed: {buy_order}")
                break

            elif buy_status == 'REJECTED':
                order_status_queue.put({"status": "error", "message": "Buy order was rejected."})
                print(f"Order rejected: {buy_order}")
                # Optionally, you may choose to send only one error message instead of two.
                order_status_queue.put({"status": "error", "message": "Order monitoring timed out."})
                print("Order monitoring timed out")
                break

            time.sleep(1)  # Adjust polling frequency as needed

    except Exception as e:
        order_status_queue.put({"status": "error", "message": f"Order monitoring error: {str(e)}"})
        print(f"Error monitoring order status: {e}")
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
        return None
