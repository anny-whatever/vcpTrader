import datetime
import threading
import queue
import time
import logging
from db import get_trade_db_connection, release_trade_db_connection
from .manage_risk_pool import update_risk_pool_on_increase, update_risk_pool_on_decrease
from controllers import kite

logger = logging.getLogger(__name__)

adjustment_lock = threading.Lock()
adjustment_running = False
adjustment_status_queue = queue.Queue()

def adjust_order_execute(symbol, qty, adjustment_type):
    global adjustment_running
    conn, cur = get_trade_db_connection()
    with adjustment_lock:
        if adjustment_running:
            logger.info(f"Adjustment ({adjustment_type.capitalize()}) already running for {symbol}")
            release_trade_db_connection(conn, cur)
            return {
                "status": "error",
                "message": f"An adjustment ({adjustment_type}) for {symbol} is already in progress. Please wait until it completes."
            }
        adjustment_running = True

    try:
        entry_price = kite.ltp(f"NSE:{symbol}")[f"NSE:{symbol}"]['last_price']
        stop_loss = entry_price - (entry_price * 0.1)
        try:
            # Check risk pool availability
            check = __import__("manage_risk_pool").manage_risk_pool.check_risk_pool_availability_for_buy(cur, entry_price, stop_loss, qty)
        except ValueError as e:
            logger.error(f"Risk pool check failed for {symbol}: {e}")
            return {
                "status": "error",
                "message": f"Insufficient risk pool for {symbol}. Entry Price: {entry_price:.2f}, Stop Loss: {stop_loss:.2f}, Quantity: {qty}."
            }
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
        threading.Thread(
            target=monitor_adjustment_status,
            args=(response_buy, __import__("manage_trade_params").manage_trade_params.get_trade_id_by_symbol(cur, symbol), qty, adjustment_type, entry_price, stop_loss, 300),
            kwargs={'symbol': symbol}
        ).start()
        status = adjustment_status_queue.get(timeout=305)
        logger.info(f"Final Adjustment Status for {symbol}: {status}")
        return status
    except Exception as e:
        logger.error(f"Error executing buy order adjustment for {symbol}: {e}")
        return {
            "status": "error",
            "message": f"Adjustment error for {symbol} ({adjustment_type}): {str(e)}"
        }
    finally:
        with adjustment_lock:
            adjustment_running = False
        release_trade_db_connection(conn, cur)

def monitor_adjustment_status(order_id, trade_id, qty, adjustment_type, entry_price, stop_loss, timeout=300, symbol=None):
    conn, cur = get_trade_db_connection()
    try:
        start_time = time.time()
        while time.time() - start_time < timeout:
            adjust_order = kite.order_history(order_id)
            adjust_status = adjust_order[-1]['status']
            adjust_status_message = adjust_order[-1]['status_message']
            logger.info(f"Adjustment Order Status for {symbol}: {adjust_status}")
            if adjust_status == 'COMPLETE':
                actual_price = float(adjust_order[-1].get('average_price', 0))
                if actual_price == 0:
                    raise ValueError("Adjustment order completed, but no valid average price available.")
                if adjustment_type == 'increase':
                    update_risk_pool_on_increase(cur, stop_loss, actual_price, qty)
                elif adjustment_type == 'decrease':
                    update_risk_pool_on_decrease(cur, stop_loss, entry_price, actual_price, qty)
                __import__("manage_trade_params").manage_trade_params.update_trade_record(cur, conn, trade_id, qty, actual_price, adjustment_type)
                message = (
                    f"Adjustment ({adjustment_type.capitalize()}) for {symbol} executed successfully: "
                    f"{qty} shares adjusted at an average price of {actual_price:.2f} "
                    f"(Entry: {entry_price:.2f}, Stop-loss: {stop_loss:.2f})."
                )
                adjustment_status_queue.put({"status": "success", "message": message})
                logger.info(message)
                return
            if adjust_status == 'REJECTED':
                message = f"Adjustment ({adjustment_type.capitalize()}) for {symbol} was rejected. Reason: {adjust_status_message}."
                adjustment_status_queue.put({"status": "error", "message": message})
                logger.warning(message)
                return
            time.sleep(1)
        timeout_message = f"Adjustment ({adjustment_type.capitalize()}) for {symbol} timed out after {timeout} seconds."
        adjustment_status_queue.put({"status": "error", "message": timeout_message})
        logger.warning(timeout_message)
    except Exception as e:
        error_message = f"Adjustment monitoring error for {symbol} ({adjustment_type}): {str(e)}"
        adjustment_status_queue.put({"status": "error", "message": error_message})
        logger.exception(f"Error during adjustment status monitoring for {symbol}: {e}")
    finally:
        release_trade_db_connection(conn, cur)

def update_trade_record(cur, conn, trade_id, qty, actual_price, adjustment_type):
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
            new_entry_price = ((current_qty * current_entry_price) + (qty * actual_price)) / (current_qty + qty)
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
        logger.info(f"Trade record updated for trade ID {trade_id}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating trade record for trade ID {trade_id}: {e}")
    # Note: Not re-raising here because update_trade_record is used in a monitoring thread

def get_trade_id_by_symbol(cur, symbol):
    try:
        query = "SELECT trade_id FROM trades WHERE stock_name = %s;"
        cur.execute(query, (symbol,))
        result = cur.fetchone()
        return result['trade_id'] if result else None
    except Exception as e:
        logger.error(f"Error retrieving trade ID for {symbol}: {e}")
        return None
