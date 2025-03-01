import threading
import time
import datetime
import pandas as pd
from decimal import Decimal
import logging

from db import get_trade_db_connection, release_trade_db_connection
from models import FemaModel, HistoricalVirtualTrades
from utils import get_indicators_5ema
from controllers import kite
from .send_telegram_signals import _send_telegram_in_thread_five_ema  # Import the telegram send function

logger = logging.getLogger(__name__)

# Global instrument details (mapping index to instrument token)
INSTRUMENT_DETAILS = {
    'nifty': {'instrument_token': 256265, 'ltp_symbol': 'NSE:NIFTY 50'},
    'banknifty': {'instrument_token': 260105, 'ltp_symbol': 'NSE:NIFTY BANK'},
    'finnifty': {'instrument_token': 257801, 'ltp_symbol': 'NSE:NIFTY FIN SERVICE'},
}

# Global locks and state variables
fema_buy_entry_lock = threading.Lock()
fema_buy_entry_running = False
fema_buy_exit_lock = threading.Lock()
fema_buy_exit_running = False
buy_order_status_lock = threading.Lock()

fema_runner_running = False
fema_runner_lock = threading.Lock()

fema_monitor_signal_candle_lock = threading.Lock()
fema_monitor_entry_lock = threading.Lock()
fema_monitor_exit_lock = threading.Lock()

position_lock = threading.Lock()
position_info = None  # Will hold active trade details

# Global flags & signal candle levels
signal_candle_flag = False
open_trade_flag = False
signal_candle_low = None  # For entry
signal_candle_high = None  # For stop loss

# Globals to hold current index info
current_index = None
current_instrument_token = None

# ----------------------------------
# Runner Function
# ----------------------------------
def fema_runner_five_minute_short(index, strategy_type):
    """
    Runner function for the 5EMA short strategy.
    `index` must be one of 'nifty', 'banknifty', or 'finnifty'.
    `strategy_type` is a unique string (e.g., 'fema_five_short') used in flag/position tables.
    """
    global fema_runner_running, signal_candle_flag, open_trade_flag, current_index, current_instrument_token

    current_index = index
    current_instrument_token = INSTRUMENT_DETAILS[index]['instrument_token']

    trade_conn, trade_cur = get_trade_db_connection()
    logger.info(f"Short: Starting 5EMA strategy runner for {index}")
    with fema_runner_lock:
        if fema_runner_running:
            logger.info("Short: Runner already running.")
            return
        fema_runner_running = True

    try:
        # Get flag status from the database for this strategy
        flags = FemaModel.get_flags_by_type(trade_cur, strategy_type)
        if flags:
            # flags structure: (signal_candle_flag, signal_candle_low, signal_candle_high, open_trade_flag, trail_flag)
            last_flag = flags[-1]
            signal_candle_flag = last_flag[0]
            open_trade_flag = last_flag[3]
        else:
            signal_candle_flag = False
            open_trade_flag = False

        # Based on flag status, choose which monitoring function to run:
        if not open_trade_flag and not signal_candle_flag:
            logger.info("Short: Checking for Signal Candle.")
            fema_monitor_signal_candle(index, strategy_type)
        elif signal_candle_flag and not open_trade_flag:
            logger.info("Short: Monitoring for Entry Trigger via live ticks.")
            # Live ticks will trigger monitor_live_entry_fema
        elif open_trade_flag:
            logger.info("Short: Monitoring for Exit Trigger via live ticks.")
            # Live ticks will trigger monitor_live_exit_fema
    except Exception as e:
        logger.error(f"Short: Error in runner: {e}")
    finally:
        release_trade_db_connection(trade_conn, trade_cur)
        with fema_runner_lock:
            fema_runner_running = False

# ----------------------------------
# Signal Candle Monitoring
# ----------------------------------
def fema_monitor_signal_candle(index, strategy_type):
    """
    Checks the last 10 5-minute candles from the resampled table for a signal candle.
    For short trades, a signal candle is defined as:
      candle['open'] > candle['EMA5'] and candle['low'] > candle['EMA5'].
    When detected, updates the flag table with signal_candle_flag = True,
    and saves signal_candle_low (entry price) and signal_candle_high (stop loss).
    Sends a Telegram message with the details.
    """
    global signal_candle_flag, signal_candle_low, signal_candle_high

    with fema_monitor_signal_candle_lock:
        trade_conn, trade_cur = get_trade_db_connection()
        try:
            token = INSTRUMENT_DETAILS[index]['instrument_token']
            select_query = """
            SELECT * FROM (
                SELECT * FROM ohlc_resampled
                WHERE instrument_token = %s AND interval = '5min'
                ORDER BY time_stamp DESC LIMIT 10
            ) as r ORDER BY r.time_stamp ASC;
            """
            trade_cur.execute(select_query, (token,))
            rows = trade_cur.fetchall()
            df = pd.DataFrame(rows, columns=['instrument_token', 'time_stamp', 'open', 'high', 'low', 'close', 'interval'])
            if df.empty:
                logger.info(f"Short: No 5min data available for {index}.")
                return

            # Compute the 5 EMA on the fetched data
            df = get_indicators_5ema(df)
            df = df.dropna()
            if df.empty:
                logger.info(f"Short: Insufficient data for indicators on {index}.")
                return

            last_candle = df.iloc[-1]
            if last_candle['open'] > last_candle['EMA5'] and last_candle['low'] > last_candle['EMA5']:
                # Update flags with signal candle details
                FemaModel.set_flags(trade_cur, strategy_type, True, False, last_candle['low'], last_candle['high'])
                trade_conn.commit()
                signal_candle_flag = True
                signal_candle_low = last_candle['low']
                signal_candle_high = last_candle['high']
                msg = (
                    f"Signal Candle Detected\n"
                    f"Low: {signal_candle_low}\n"
                    f"High: {signal_candle_high}\n"
                    f"Time: {last_candle['time_stamp']}"
                )
                _send_telegram_in_thread_five_ema(msg)
                logger.info(msg)
            else:
                # Reset the signal flag if conditions are not met and send notification
                FemaModel.set_flags(trade_cur, strategy_type, False, False, None, None)
                trade_conn.commit()
                if signal_candle_flag:
                    msg = "Signal Candle Discarded"
                    _send_telegram_in_thread_five_ema(msg)
                    logger.info(msg)
                signal_candle_flag = False
        except Exception as e:
            logger.error(f"Short: Error in signal candle monitoring: {e}")
            trade_conn.rollback()
        finally:
            release_trade_db_connection(trade_conn, trade_cur)

# ----------------------------------
# Live Tick Entry Monitoring
# ----------------------------------
def monitor_live_entry_fema(ticks, strategy_type):
    """
    Processes live ticks to look for an entry trigger.
    For a short trade, entry is triggered when the tick price falls to or below the signal_candle_low.
    Once triggered, calculates risk, profit target and calls the entry function.
    """
    global signal_candle_flag, open_trade_flag, position_info, signal_candle_low, signal_candle_high, current_instrument_token, current_index

    if not signal_candle_flag or open_trade_flag:
        return

    for tick in ticks:
        if tick['instrument_token'] == current_instrument_token:
            price = tick['last_price']
            # For a short trade, entry triggers when price <= signal_candle_low
            if price <= signal_candle_low:
                entry_price = signal_candle_low
                risk = signal_candle_high - entry_price
                profit_points = max(3 * risk, entry_price * 0.003)
                profit_target = entry_price - profit_points
                stop_loss = signal_candle_high
                trade = {
                    'entry_time': datetime.datetime.now(),
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'profit_target': profit_target,
                    'strategy_type': strategy_type,
                    'index': current_index
                }
                msg = (
                    f"Trade Entry Triggered\n"
                    f"Entry: {entry_price}\n"
                    f"Stoploss: {stop_loss}\n"
                    f"Target: {profit_target}\n"
                    f"Time: {trade['entry_time']}"
                )
                _send_telegram_in_thread_five_ema(msg)
                logger.info(msg)
                fema_buy_entry(trade)
                break

# ----------------------------------
# Virtual Order Entry (Simulated for Short Trades)
# ----------------------------------
def fema_buy_entry(trade):
    """
    Simulated entry for a short trade.
    Instead of placing an order, we fetch the current last price using kite.quote.
    Trade details are stored in the fema_positions table.
    """
    global fema_buy_entry_running, position_info
    with fema_buy_entry_lock:
        if fema_buy_entry_running:
            logger.info("Short: fema_buy_entry already running.")
            return
        fema_buy_entry_running = True

    try:
        start_time = datetime.datetime.now()
        # Instead of placing an order, fetch the last price via kite.quote
        quote = kite.quote(INSTRUMENT_DETAILS[current_index]['ltp_symbol'])
        simulated_order = {
            'order_id': f"SIM-{int(time.time())}",
            'average_price': quote[INSTRUMENT_DETAILS[current_index]['ltp_symbol']]['last_price'],
            'instrument_token': current_instrument_token,
            'tradingsymbol': INSTRUMENT_DETAILS[current_index]['ltp_symbol'],
            'quantity': 1
        }
        fema_trade = FemaModel(
            type=trade['strategy_type'],
            index=trade['index'],
            sell_strike_order_id=simulated_order['order_id'],
            buy_strike_order_id=None,
            sell_strike_entry_price=simulated_order['average_price'],
            buy_strike_entry_price=None,
            sell_strike_instrument_token=simulated_order['instrument_token'],
            buy_strike_instrument_token=None,
            sell_strike_trading_symbol=simulated_order['tradingsymbol'],
            buy_strike_trading_symbol=None,
            expiry=None,
            qty=simulated_order['quantity'],
            entry_time=trade['entry_time'],
            entry_price=trade['entry_price'],
            stop_loss_level=trade['stop_loss'],
            target_level=trade['profit_target']
        )
        trade_conn, trade_cur = get_trade_db_connection()
        FemaModel.create_table_positions(trade_cur)
        FemaModel.create_table_flags(trade_cur)
        fema_trade.insert_trade_data(trade_cur)
        trade_conn.commit()
        position_info = fema_trade
        # Update flag table: mark open_trade_flag True and reset signal candle flag.
        FemaModel.set_flags(trade_cur, trade['strategy_type'], False, True, None, None)
        trade_conn.commit()
        release_trade_db_connection(trade_conn, trade_cur)
        msg = (
            f"Trade Entered\n"
            f"Entry Price: {simulated_order['average_price']}\n"
            f"Stoploss: {trade['stop_loss']}\n"
            f"Target: {trade['profit_target']}\n"
            f"Time: {trade['entry_time']}"
        )
        _send_telegram_in_thread_five_ema(msg)
        logger.info(msg)
    except Exception as e:
        logger.error(f"Short: Error executing simulated entry: {e}")
    finally:
        with fema_buy_entry_lock:
            fema_buy_entry_running = False
        end_time = datetime.datetime.now()
        logger.info(f"Short: fema_buy_entry execution time: {end_time - start_time}")

# ----------------------------------
# Live Tick Exit Monitoring
# ----------------------------------
def monitor_live_exit_fema(ticks):
    """
    Processes live ticks for an active trade.
    For short trades:
      - Exit if tick price >= stop_loss_level (stop loss triggered).
      - Exit if tick price <= target_level (profit target reached).
      - Exit if at a specified time (e.g., 15:20) and price is below entry price.
    """
    global position_info, current_instrument_token
    if position_info is None:
        return

    for tick in ticks:
        if tick['instrument_token'] == current_instrument_token:
            price = tick['last_price']
            if price >= position_info.stop_loss_level:
                logger.info("Short: Stop loss triggered via live tick.")
                _send_telegram_in_thread_five_ema("Stoploss Triggered")
                fema_buy_exit(position_info)
                return
            if price <= position_info.target_level:
                logger.info("Short: Profit target reached via live tick.")
                _send_telegram_in_thread_five_ema("Target Reached")
                fema_buy_exit(position_info)
                return
            now = datetime.datetime.now()
            if now.hour == 15 and now.minute == 20 and price < position_info.entry_price:
                logger.info("Short: Time-based exit triggered via live tick.")
                _send_telegram_in_thread_five_ema("Time Exit Triggered")
                fema_buy_exit(position_info)
                return

# ----------------------------------
# Virtual Order Exit (Simulated for Short Trades)
# ----------------------------------
def fema_buy_exit(trade):
    """
    Simulated exit for a short trade.
    Instead of placing an order, we use kite.quote to fetch the current last price.
    After simulated execution, the trade is recorded in the historical_virtual_trades table.
    """
    global fema_buy_exit_running, position_info
    with fema_buy_exit_lock:
        if fema_buy_exit_running:
            logger.info("Short: fema_buy_exit already running.")
            return
        fema_buy_exit_running = True

    try:
        start_time = datetime.datetime.now()
        quote = kite.quote(INSTRUMENT_DETAILS[current_index]['ltp_symbol'])
        simulated_exit_price = quote[INSTRUMENT_DETAILS[current_index]['ltp_symbol']]['last_price']
        pnl = (position_info.sell_strike_entry_price - simulated_exit_price) * position_info.qty
        trade_conn, trade_cur = get_trade_db_connection()
        hv_trade = HistoricalVirtualTrades(
            strategy_type=position_info.type,
            index=position_info.index,
            entry_time=position_info.entry_time,
            entry_price=position_info.entry_price,
            exit_time=datetime.datetime.now(),
            exit_price=simulated_exit_price,
            qty=position_info.qty,
            pnl=pnl
        )
        hv_trade.insert_virtual_trade(trade_cur)
        trade_conn.commit()
        FemaModel.delete_trade_data_by_type(trade_cur, position_info.type)
        trade_conn.commit()
        release_trade_db_connection(trade_conn, trade_cur)
        msg = (
            f"Trade Exited\n"
            f"Exit Price: {simulated_exit_price}\n"
            f"PnL: {pnl}\n"
            f"Time: {datetime.datetime.now()}"
        )
        _send_telegram_in_thread_five_ema(msg)
        logger.info(msg)
        position_info = None
    except Exception as e:
        logger.error(f"Short: Error executing simulated exit: {e}")
    finally:
        with fema_buy_exit_lock:
            fema_buy_exit_running = False
        end_time = datetime.datetime.now()
        logger.info(f"Short: fema_buy_exit execution time: {end_time - start_time}")

# ----------------------------------
# Live Position Monitoring (Entry & Exit)
# ----------------------------------
def monitor_live_position_fema_short(ticks, strategy_type):
    """
    Call this function with live tick data.
    If no trade is active, it checks for an entry trigger.
    If a trade is active, it monitors for exit conditions.
    """
    global position_info
    if position_info is None:
        monitor_live_entry_fema(ticks, strategy_type)
    else:
        monitor_live_exit_fema(ticks)
