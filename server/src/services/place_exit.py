from db import get_trade_db_connection, release_trade_db_connection
from .manage_risk_pool import update_risk_pool_on_exit
from models import SaveHistoricalTradeDetails
import datetime
import threading
import time
import queue
from controllers import kite
import logging
import json  # Needed to parse adjustments

# Configure logging
logging.basicConfig(level=logging.INFO)

sell_exit_lock = threading.Lock()
sell_exit_event = threading.Event()
sell_status_queue = queue.Queue()

def sell_order_execute(symbol):
    """
    Execute the sell order to exit the trade.
    """
    if sell_exit_event.is_set():
        logging.info("Exit already running")
        return {"status": "error", "message": f"Sell exit already in progress for {symbol}."}

    sell_exit_event.set()
    conn, cur = None, None
    start_time = datetime.datetime.now()  # Record start time for execution time logging

    try:
        conn, cur = get_trade_db_connection()

        # Fetch the current trade details, including adjustments and initial_qty
        cur.execute("""
            SELECT trade_id, stock_name, entry_time, entry_price, current_qty, booked_pnl, stop_loss, adjustments, initial_qty
            FROM trades 
            WHERE stock_name = %s;
        """, (symbol,))
        trade = cur.fetchone()

        if not trade:
            logging.info(f"No active trade found for {symbol}")
            return {"status": "error", "message": f"No active trade found for {symbol}. Please ensure you have an open position before exiting."}

        # Extract trade details
        trade_id = trade['trade_id']
        entry_time = trade['entry_time']
        entry_price = float(trade['entry_price'])
        current_qty = float(trade['current_qty'])
        booked_pnl = float(trade['booked_pnl'])
        stop_loss = float(trade['stop_loss'])
        
        # Calculate highest quantity ever held.
        # Use initial_qty if present; otherwise, fallback to current_qty.
        if 'initial_qty' in trade and trade['initial_qty'] is not None:
            initial_qty = float(trade['initial_qty'])
        else:
            initial_qty = current_qty

        highest_adj = 0.0
        current_adj = 0.0
        if trade.get('adjustments'):
            try:
                adjustments = trade['adjustments']
                # If adjustments are stored as a JSON string, parse it.
                if isinstance(adjustments, str):
                    adjustments = json.loads(adjustments)
                # Sort adjustments by their time (assumes ISO 8601 format)
                adjustments_sorted = sorted(adjustments, key=lambda a: a.get("time"))
                for adj in adjustments_sorted:
                    adj_qty = float(adj.get("qty", 0))
                    if adj.get("type") == "increase":
                        current_adj += adj_qty
                    elif adj.get("type") == "decrease":
                        current_adj -= adj_qty
                    if current_adj > highest_adj:
                        highest_adj = current_adj
            except Exception as e:
                logging.error(f"Error calculating highest adjustments for {symbol}: {e}")
                highest_adj = 0.0
        # If the maximum cumulative adjustment is negative, use initial_qty.
        if highest_adj < 0:
            highest_qty = initial_qty
        else:
            highest_qty = initial_qty + highest_adj

        if current_qty <= 0:
            logging.info(f"No quantity left to exit for {symbol}")
            return {"status": "error", "message": f"No quantity left to exit for {symbol}. Current Quantity: {current_qty}."}

        # Place the sell order to exit the trade
        response_sell = kite.place_order(
            variety='regular',
            exchange='NSE',
            tradingsymbol=symbol,
            transaction_type='SELL',
            quantity=int(current_qty),
            product='CNC',
            order_type='MARKET'
        )
        logging.info(f"Sell order placed for {symbol}: {response_sell}")

        # Start a thread to monitor the sell order status, passing highest_qty as an argument.
        threading.Thread(
            target=monitor_sell_order_status,
            args=(response_sell, trade_id, symbol, entry_time, entry_price, current_qty, booked_pnl, stop_loss, highest_qty, 300)
        ).start()

        # Retrieve the result from the queue
        status = sell_status_queue.get(timeout=305)
        logging.info(f"Final exit status for {symbol}: {status}")
        return status

    except Exception as e:
        logging.exception("Error executing exit strategy")
        return {
            "status": "error",
            "message": f"Error executing exit strategy for {symbol}. Please try again. ({str(e)})"
        }

    finally:
        sell_exit_event.clear()
        release_trade_db_connection(conn, cur)
        logging.info(f"Execution time for {symbol}: {datetime.datetime.now() - start_time}")

def monitor_sell_order_status(order_id, trade_id, symbol, entry_time, entry_price, current_qty, booked_pnl, stop_loss, highest_qty, timeout=300):
    """
    Monitor the sell order status and update the database and risk pool accordingly.
    """
    conn, cur = None, None

    try:
        conn, cur = get_trade_db_connection()
        start_time = time.time()

        while time.time() - start_time < timeout:
            sell_order = kite.order_history(order_id)
            sell_status = sell_order[-1]['status']
            sell_status_message = sell_order[-1]['status_message']
            logging.info(f"Sell Order Status for {symbol}: {sell_status}")

            if sell_status == 'COMPLETE':
                # Successful sell order
                exit_price = float(sell_order[-1]['average_price'])
                unrealized_pnl = (exit_price - entry_price) * current_qty
                final_pnl = booked_pnl + unrealized_pnl

                message = (
                    f"Exit successful for {symbol}: Sold {current_qty} shares at {exit_price:.2f} "
                    f"(Entry: {entry_price:.2f}, Stop-loss: {stop_loss:.2f}, Highest Qty Held: {highest_qty}). "
                    f"Final PnL: {final_pnl:.2f}."
                )
                sell_status_queue.put({"status": "success", "message": message})
                logging.info(message)

                # Update risk pool
                update_risk_pool_on_exit(cur, stop_loss, entry_price, exit_price, current_qty)

                # Save trade details to the historical_trades table, including highest_qty
                SaveHistoricalTradeDetails(
                    stock_name=symbol,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    exit_time=sell_order[-1]['exchange_timestamp'],
                    exit_price=exit_price,
                    final_pnl=final_pnl,
                    highest_qty=highest_qty
                ).save(cur)
                logging.info(f"Trade details saved to historical_trades for {symbol}")

                # Delete the trade from the active trades table
                cur.execute("DELETE FROM trades WHERE trade_id = %s;", (trade_id,))
                conn.commit()
                logging.info(f"Trade for {symbol} exited successfully. Final PnL: {final_pnl:.2f}")
                return

            if sell_status == 'REJECTED':
                message = f"Exit for {symbol} was rejected. Reason: {sell_status_message}."
                sell_status_queue.put({"status": "error", "message": message})
                logging.warning(message)
                return

            time.sleep(0.5)

        # Timeout handling
        timeout_message = f"Sell order monitoring for {symbol} timed out after {timeout} seconds."
        sell_status_queue.put({"status": "error", "message": timeout_message})
        logging.warning(timeout_message)

    except Exception as e:
        error_message = f"Sell order monitoring error for {symbol}: {str(e)}"
        sell_status_queue.put({"status": "error", "message": error_message})
        logging.exception("Error during sell order monitoring")

    finally:
        release_trade_db_connection(conn, cur)
