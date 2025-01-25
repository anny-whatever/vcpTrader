from db import get_trade_db_connection, release_trade_db_connection
from .manage_risk_pool import update_risk_pool_on_exit
from models import SaveHistoricalTradeDetails
import datetime
import threading
import time
import queue
from controllers import kite
import logging

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
        return

    sell_exit_event.set()
    conn, cur = None, None

    try:
        conn, cur = get_trade_db_connection()

        # Fetch the current trade details
        cur.execute("""
            SELECT trade_id, stock_name, entry_time, entry_price, current_qty, booked_pnl, stop_loss 
            FROM trades 
            WHERE stock_name = %s;
        """, (symbol,))
        trade = cur.fetchone()

        if not trade:
            logging.info(f"No active trade found for symbol: {symbol}")
            return

        # Extract trade details
        trade_id = trade['trade_id']
        entry_time = trade['entry_time']
        entry_price = float(trade['entry_price'])
        current_qty = float(trade['current_qty'])
        booked_pnl = float(trade['booked_pnl'])
        stop_loss = float(trade['stop_loss'])

        if current_qty <= 0:
            logging.info(f"No quantity left to exit for symbol: {symbol}")
            return

        start_time = datetime.datetime.now()

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
        logging.info(f"Sell order placed: {response_sell}")

        # Start a thread to monitor the sell order status
        threading.Thread(
            target=monitor_sell_order_status,
            args=(response_sell, trade_id, symbol, entry_time, entry_price, current_qty, booked_pnl, stop_loss, 300)
        ).start()

        # Retrieve the result from the queue
        status = sell_status_queue.get(timeout=305)
        logging.info(f"Final Exit Status: {status}")
        return status

    except Exception as e:
        logging.exception("Error executing exit strategy")

    finally:
        sell_exit_event.clear()
        release_trade_db_connection(conn, cur)
        logging.info(f"Execution time: {datetime.datetime.now() - start_time}")

def monitor_sell_order_status(order_id, trade_id, symbol, entry_time, entry_price, current_qty, booked_pnl, stop_loss, timeout=300):
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
            logging.info(f"Sell Order Status: {sell_status}")

            if sell_status == 'COMPLETE':
                sell_status_queue.put({"status": sell_status, "message": sell_status_message})

                # Calculate final PnL
                exit_price = float(sell_order[-1]['average_price'])
                unrealized_pnl = (exit_price - entry_price) * current_qty
                final_pnl = booked_pnl + unrealized_pnl

                # Update risk pool
                is_profit = final_pnl > booked_pnl
                update_risk_pool_on_exit(cur, stop_loss, entry_price, exit_price, current_qty)

                # Save trade details to the historical_trades table
                SaveHistoricalTradeDetails(
                    stock_name=symbol,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    exit_time=sell_order[-1]['exchange_timestamp'],
                    exit_price=exit_price,
                    final_pnl=final_pnl,
                    highest_qty=current_qty
                ).save(cur)
                logging.info(f"Trade details saved to historical_trades for symbol: {symbol}")

                # Delete the trade from the active trades table
                cur.execute("DELETE FROM trades WHERE trade_id = %s;", (trade_id,))
                conn.commit()
                logging.info(f"Trade for {symbol} exited successfully. Final PnL: {final_pnl}")
                return

            if sell_status == 'REJECTED':
                sell_status_queue.put({"status": sell_status, "message": sell_status_message})
                logging.warning(f"Sell Order Rejected: {sell_status_message}")
                return

            time.sleep(0.5)

        # Timeout
        sell_status_queue.put('TIMEOUT')
        logging.warning("Sell order monitoring timed out")

    except Exception as e:
        sell_status_queue.put(f"ERROR: {str(e)}")
        logging.exception("Error during sell order monitoring")

    finally:
        release_trade_db_connection(conn, cur)
