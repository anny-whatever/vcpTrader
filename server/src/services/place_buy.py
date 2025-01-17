from db import get_trade_db_connection, release_trade_db_connection
from models import SaveTradeDetails
from .manage_risk_pool import update_risk_pool_on_buy
import datetime
import threading
import time
import queue
from controllers import kite

buy_entry_lock = threading.Lock()
buy_entry_running = False
order_status_queue = queue.Queue()

def buy_order_execute(symbol, qty):
    global buy_entry_running
    conn, cur = get_trade_db_connection()

    with buy_entry_lock:
        if buy_entry_running:
            print("Buy entry already running")
            return
        buy_entry_running = True

    try:
        # Fetch live entry price and calculate stop-loss
        entry_price = kite.ltp(f"NSE:{symbol}")[f"NSE:{symbol}"]['last_price']
        stop_loss = entry_price - (entry_price * 0.1)  # Example: 10% stop-loss

        # Manage risk pool
        try:
            update_risk_pool_on_buy(cur, entry_price, stop_loss, qty)
        except ValueError as e:
            print(f"Risk pool update failed: {e}")
            return {"status": "INSUFFICIENT_RISK"}

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
        print(response_buy)

        # Start a thread to monitor the order status
        threading.Thread(
            target=monitor_order_status,
            args=(response_buy, qty, entry_price, stop_loss, 300)
        ).start()

        # Retrieve the result from the queue
        status = order_status_queue.get(timeout=305)
        print(f"Final Order Status: {status}")
        return status

    except Exception as e:
        print(f"Error executing buy order: {e}")
    finally:
        with buy_entry_lock:
            buy_entry_running = False
        release_trade_db_connection(conn, cur)

def monitor_order_status(order_id, qty, entry_price, stop_loss, timeout=300):
    conn, cur = get_trade_db_connection()
    try:
        start_time = time.time()
        while time.time() - start_time < timeout:
            buy_order = kite.order_history(order_id)
            buy_status = buy_order[-1]['status']
            buy_status_message = buy_order[-1]['status_message']
            print(f"Order Status: {buy_status}")

            if buy_status == 'COMPLETE':
                order_status_queue.put({"status": buy_status, "message": buy_status_message})
                SaveTradeDetails(
                    stock_name=buy_order[-1]['tradingsymbol'],
                    token=buy_order[-1]['instrument_token'],
                    entry_time=buy_order[-1]['exchange_timestamp'],
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    target=entry_price + (entry_price * 0.2),  # Example: 20% target
                    initial_qty=qty,
                    current_qty=qty,
                    booked_pnl=0
                ).save(cur)
                conn.commit()
                print(f"Order completed: {buy_order}")
                break

            elif buy_status == 'REJECTED':
                order_status_queue.put({"status": buy_status, "message": buy_status_message})
                print(f"Order rejected: {buy_order}")
                break

            time.sleep(1)  # Adjust polling frequency if needed

        # Timeout
        order_status_queue.put('TIMEOUT')

    except Exception as e:
        order_status_queue.put(f"ERROR: {str(e)}")
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
        print(f"Error retrieving trade ID: {str(e)}")
        return None
