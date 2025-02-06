from db import get_trade_db_connection, release_trade_db_connection
from .manage_risk_pool import update_risk_pool_on_increase, update_risk_pool_on_decrease
import datetime
import threading
import queue
import time
from controllers import kite

adjustment_lock = threading.Lock()
adjustment_running = False
adjustment_status_queue = queue.Queue()

def adjust_order_execute(symbol, qty, adjustment_type):
    """
    Execute an adjustment to an existing order.
    """
    global adjustment_running
    conn, cur = get_trade_db_connection()
    with adjustment_lock:
        if adjustment_running:
            print(f"Adjustment: {adjustment_type.capitalize()} already running for {symbol}")
            release_trade_db_connection(conn, cur)
            return {
                "status": "error",
                "message": f"An adjustment ({adjustment_type}) for {symbol} is already in progress. Please wait until it completes."
            }
        adjustment_running = True

    try:
        # Retrieve the trade details
        cur.execute("""
            SELECT trade_id, entry_price, stop_loss, current_qty 
            FROM trades 
            WHERE stock_name = %s;
        """, (symbol,))
        trade = cur.fetchone()

        if not trade:
            print(f"No position found for {symbol}")
            return {
                "status": "error",
                "message": f"No active position found for {symbol}. Cannot perform a {adjustment_type} adjustment."
            }

        trade_id = trade['trade_id']
        entry_price = float(trade['entry_price'])
        stop_loss = float(trade['stop_loss'])
        current_qty = float(trade['current_qty'])
        qty = float(qty)

        if adjustment_type == 'decrease' and qty > current_qty:
            raise ValueError(f"Cannot decrease by {qty}, only {current_qty} available.")

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
        print(f"Order placed: {response_adjust}")

        # Start status monitoring. Pass symbol via kwargs so messages can include it.
        threading.Thread(
            target=monitor_adjustment_status,
            args=(response_adjust, trade_id, qty, adjustment_type, entry_price, stop_loss, 300),
            kwargs={'symbol': symbol}
        ).start()

        status = adjustment_status_queue.get(timeout=305)
        print(f"Final Adjustment Status: {status}")
        return status

    except Exception as e:
        print(f"Adjustment Error ({adjustment_type.capitalize()}): {e}")
        return {
            "status": "error",
            "message": f"Adjustment error for {symbol} ({adjustment_type}): {str(e)}"
        }
    finally:
        with adjustment_lock:
            adjustment_running = False
        release_trade_db_connection(conn, cur)

def monitor_adjustment_status(order_id, trade_id, qty, adjustment_type, entry_price, stop_loss, timeout=300, symbol=None):
    """
    Monitor the status of an adjustment order and update the database and risk pool.
    """
    conn, cur = get_trade_db_connection()
    try:
        qty = float(qty)
        entry_price = float(entry_price)
        stop_loss = float(stop_loss)
        start_time = time.time()

        while time.time() - start_time < timeout:
            adjust_order = kite.order_history(order_id)
            adjust_status = adjust_order[-1]['status']
            adjust_status_message = adjust_order[-1]['status_message']
            print(f"Adjustment Order Status: {adjust_status}")

            if adjust_status == 'COMPLETE':
                actual_price = float(adjust_order[-1].get('average_price', 0))
                if actual_price == 0:
                    raise ValueError("Adjustment order completed, but no valid average price available.")
                
                if adjustment_type == 'increase':
                    update_risk_pool_on_increase(cur, stop_loss, actual_price, qty)
                elif adjustment_type == 'decrease':
                    update_risk_pool_on_decrease(cur, stop_loss, entry_price, actual_price, qty)

                update_trade_record(cur, conn, trade_id, qty, actual_price, adjustment_type)

                message = (
                    f"Adjustment ({adjustment_type.capitalize()}) for {symbol} executed successfully: "
                    f"{qty} shares adjusted at an average price of {actual_price:.2f} "
                    f"(Entry: {entry_price:.2f}, Stop-loss: {stop_loss:.2f})."
                )
                adjustment_status_queue.put({"status": "success", "message": message})
                print(message)
                return

            if adjust_status == 'REJECTED':
                message = f"Adjustment ({adjustment_type.capitalize()}) for {symbol} was rejected. Reason: {adjust_status_message}."
                adjustment_status_queue.put({"status": "error", "message": message})
                print(message)
                return

            time.sleep(0.2)

        timeout_message = f"Adjustment ({adjustment_type.capitalize()}) monitoring for {symbol} timed out after {timeout} seconds."
        adjustment_status_queue.put({"status": "error", "message": timeout_message})
        print(timeout_message)

    except Exception as e:
        error_message = f"Adjustment monitoring error for {symbol} ({adjustment_type}): {str(e)}"
        adjustment_status_queue.put({"status": "error", "message": error_message})
        print(f"Error during adjustment status monitoring: {e}")
    finally:
        release_trade_db_connection(conn, cur)

def update_trade_record(cur, conn, trade_id, qty, actual_price, adjustment_type):
    """
    Update the trade record in the database.
    """
    try:
        cur.execute("SELECT current_qty, entry_price, booked_pnl FROM trades WHERE trade_id = %s;", (trade_id,))
        result = cur.fetchone()

        if not result:
            raise ValueError(f"No trade found with trade ID {trade_id}")

        current_qty = float(result['current_qty'])
        current_entry_price = float(result['entry_price'])
        booked_pnl = float(result['booked_pnl'])
        qty = float(qty)
        actual_price = float(actual_price)

        if adjustment_type == 'increase':
            new_entry_price = (
                (current_qty * current_entry_price) + (qty * actual_price)
            ) / (current_qty + qty)
        else:
            new_entry_price = current_entry_price
            booked_pnl += (actual_price - current_entry_price) * qty

        query = """
            UPDATE trades
            SET 
                current_qty = current_qty + %s,
                entry_price = CASE 
                    WHEN %s > 0 THEN %s
                    ELSE entry_price
                END,
                booked_pnl = %s,
                adjustments = COALESCE(adjustments, '[]'::jsonb) || to_jsonb(json_build_object(
                    'time', %s,
                    'type', %s,
                    'qty', %s,
                    'price', %s,
                    'reason', 'Adjustment Order'
                ))::jsonb
            WHERE trade_id = %s;
        """

        adjustment_value = qty if adjustment_type == 'increase' else -qty
        cur.execute(query, (
            adjustment_value, qty, new_entry_price, booked_pnl, datetime.datetime.now().isoformat(),
            adjustment_type, abs(qty), actual_price, trade_id
        ))
        conn.commit()
        print(f"Updated trade record for trade ID {trade_id}")

    except Exception as e:
        conn.rollback()
        print(f"Error updating trade ID {trade_id}: {e}")

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
