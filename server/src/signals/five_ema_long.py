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
from .send_telegram_signals import _send_telegram_in_thread_five_ema  # Telegram notifier

logger = logging.getLogger(__name__)

# Global instrument details (mapping index to instrument token)
INSTRUMENT_DETAILS = {
    'nifty': {'instrument_token': 256265, 'ltp_symbol': 'NSE:NIFTY 50'},
    'banknifty': {'instrument_token': 260105, 'ltp_symbol': 'NSE:NIFTY BANK'},
    'finnifty': {'instrument_token': 257801, 'ltp_symbol': 'NSE:NIFTY FIN SERVICE'},
}

# Global locks and state variables
fema_buy_entry_lock_long = threading.Lock()
fema_buy_entry_running_long = False
fema_buy_exit_lock_long = threading.Lock()
fema_buy_exit_running_long = False
buy_order_status_lock_long = threading.Lock()

fema_runner_running_long = False
fema_runner_lock_long = threading.Lock()

fema_monitor_signal_candle_lock_long = threading.Lock()
fema_monitor_entry_lock_long = threading.Lock()
fema_monitor_exit_lock_long = threading.Lock()

position_lock_long = threading.Lock()
position_info_long = None  # Holds active long trade details

# Global flags & signal candle levels for long
signal_candle_flag_long = False
open_trade_flag_long = False
signal_candle_low_long = None   # For stop-loss in long trade
signal_candle_high_long = None  # For entry trigger in long trade

# Globals to hold current index info (for long strategy)
current_index_long = None
current_instrument_token_long = None

# ----------------------------------
# Runner Function for Long Strategy (15min TF)
# ----------------------------------
def fema_runner_fifteen_minute_long(index, strategy_type):
    """
    Runner function for the 5EMA long strategy using 15min candles.
    `index` must be one of 'nifty', 'banknifty', or 'finnifty'.
    `strategy_type` is a unique string (e.g., 'fema_fifteen_long') used in flag/position tables.
    """
    global fema_runner_running_long, signal_candle_flag_long, open_trade_flag_long, current_index_long, current_instrument_token_long

    current_index_long = index
    current_instrument_token_long = INSTRUMENT_DETAILS[index]['instrument_token']

    trade_conn, trade_cur = get_trade_db_connection()
    logger.info(f"Long: Starting 5EMA long strategy runner for {index} on 15min TF")
    with fema_runner_lock_long:
        if fema_runner_running_long:
            logger.info("Long: Runner already running.")
            return
        fema_runner_running_long = True

    try:
        # Get flag status from the database for this long strategy
        flags = FemaModel.get_flags_by_type(trade_cur, strategy_type)
        if flags:
            # flags structure: (signal_candle_flag, signal_candle_low, signal_candle_high, open_trade_flag, trail_flag)
            last_flag = flags[-1]
            signal_candle_flag_long = last_flag[0]
            open_trade_flag_long = last_flag[3]
        else:
            signal_candle_flag_long = False
            open_trade_flag_long = False

        # Based on flag status, decide which monitoring function to invoke:
        if not open_trade_flag_long and not signal_candle_flag_long:
            logger.info("Long: Checking for Signal Candle.")
            fema_monitor_signal_candle_long(index, strategy_type)
        elif signal_candle_flag_long and not open_trade_flag_long:
            logger.info("Long: Monitoring for Entry Trigger via live ticks.")
            # Live ticks will trigger monitor_live_entry_fema_long
        elif open_trade_flag_long:
            logger.info("Long: Monitoring for Exit Trigger via live ticks.")
            # Live ticks will trigger monitor_live_exit_fema_long
    except Exception as e:
        logger.error(f"Long: Error in runner: {e}")
    finally:
        release_trade_db_connection(trade_conn, trade_cur)
        with fema_runner_lock_long:
            fema_runner_running_long = False

# ----------------------------------
# Signal Candle Monitoring for Long
# ----------------------------------
def fema_monitor_signal_candle_long(index, strategy_type):
    """
    Checks the last 10 15-minute candles from the resampled table for a long signal candle.
    For long trades, a signal candle is defined as:
      candle['open'] < candle['EMA5'] and candle['high'] < candle['EMA5'].
    When detected, updates the flag table with signal_candle_flag = True,
    and saves signal_candle_low (for stop loss) and signal_candle_high (for entry trigger).
    Sends a Telegram message with the details.
    """
    global signal_candle_flag_long, signal_candle_low_long, signal_candle_high_long

    with fema_monitor_signal_candle_lock_long:
        trade_conn, trade_cur = get_trade_db_connection()
        try:
            token = INSTRUMENT_DETAILS[index]['instrument_token']
            # Use interval '15min' for long trades
            select_query = """
            SELECT * FROM (
                SELECT * FROM ohlc_resampled
                WHERE instrument_token = %s AND interval = '15min'
                ORDER BY time_stamp DESC LIMIT 10
            ) as r ORDER BY r.time_stamp ASC;
            """
            trade_cur.execute(select_query, (token,))
            rows = trade_cur.fetchall()
            df = pd.DataFrame(rows, columns=['instrument_token', 'time_stamp', 'open', 'high', 'low', 'close', 'interval'])
            if df.empty:
                logger.info(f"Long: No 15min data available for {index}.")
                return

            # Compute the 5EMA on the fetched data
            df = get_indicators_5ema(df)
            df = df.dropna()
            if df.empty:
                logger.info(f"Long: Insufficient data for indicators on {index}.")
                return

            last_candle = df.iloc[-1]
            if last_candle['open'] < last_candle['EMA5'] and last_candle['high'] < last_candle['EMA5']:
                # For a long trade, we store the candle's low for stop loss and high for entry trigger.
                FemaModel.set_flags(trade_cur, strategy_type, True, False, last_candle['low'], last_candle['high'])
                trade_conn.commit()
                signal_candle_flag_long = True
                signal_candle_low_long = last_candle['low']
                signal_candle_high_long = last_candle['high']
                msg = (
                    f"Signal Candle Detected (Long)\n"
                    f"Low (SL): {signal_candle_low_long}\n"
                    f"High (Entry): {signal_candle_high_long}\n"
                    f"Time: {last_candle['time_stamp']}"
                )
                _send_telegram_in_thread_five_ema(msg)
                logger.info(msg)
            else:
                FemaModel.set_flags(trade_cur, strategy_type, False, False, None, None)
                trade_conn.commit()
                if signal_candle_flag_long:
                    msg = "Signal Candle Discarded (Long)"
                    _send_telegram_in_thread_five_ema(msg)
                    logger.info(msg)
                signal_candle_flag_long = False
        except Exception as e:
            logger.error(f"Long: Error in signal candle monitoring: {e}")
            trade_conn.rollback()
        finally:
            release_trade_db_connection(trade_conn, trade_cur)

# ----------------------------------
# Live Tick Entry Monitoring for Long
# ----------------------------------
def monitor_live_entry_fema_long(ticks, strategy_type):
    """
    Processes live ticks to look for a long entry trigger.
    For a long trade, entry is triggered when the tick price rises to or above the signal_candle_high.
    Once triggered, calculates risk, profit target and calls the simulated entry function.
    """
    global signal_candle_flag_long, open_trade_flag_long, position_info_long, signal_candle_low_long, signal_candle_high_long, current_instrument_token_long, current_index_long

    if not signal_candle_flag_long or open_trade_flag_long:
        return

    for tick in ticks:
        if tick['instrument_token'] == current_instrument_token_long:
            price = tick['last_price']
            # For a long trade, entry triggers when price >= signal_candle_high_long
            if price >= signal_candle_high_long:
                entry_price = signal_candle_high_long
                risk = entry_price - signal_candle_low_long
                profit_points = max(3 * risk, entry_price * 0.003)
                profit_target = entry_price + profit_points
                stop_loss = signal_candle_low_long
                trade = {
                    'entry_time': datetime.datetime.now(),
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'profit_target': profit_target,
                    'strategy_type': strategy_type,
                    'index': current_index_long
                }
                msg = (
                    f"Trade Entry Triggered (Long)\n"
                    f"Entry: {entry_price}\n"
                    f"Stoploss: {stop_loss}\n"
                    f"Target: {profit_target}\n"
                    f"Time: {trade['entry_time']}"
                )
                _send_telegram_in_thread_five_ema(msg)
                logger.info(msg)
                fema_buy_entry_long(trade)
                break

# ----------------------------------
# Virtual Order Entry (Simulated for Long Trades)
# ----------------------------------
def fema_buy_entry_long(trade):
    """
    Simulated entry for a long trade.
    Instead of placing an order, we fetch the current last price using kite.quote.
    Trade details are stored in the fema_positions table.
    """
    global fema_buy_entry_running_long, position_info_long
    with fema_buy_entry_lock_long:
        if fema_buy_entry_running_long:
            logger.info("Long: fema_buy_entry already running.")
            return
        fema_buy_entry_running_long = True

    try:
        start_time = datetime.datetime.now()
        # Instead of placing an order, fetch the last price via kite.quote
        quote = kite.quote(INSTRUMENT_DETAILS[current_index_long]['ltp_symbol'])
        simulated_order = {
            'order_id': f"SIM-{int(time.time())}",
            'average_price': quote[INSTRUMENT_DETAILS[current_index_long]['ltp_symbol']]['last_price'],
            'instrument_token': current_instrument_token_long,
            'tradingsymbol': INSTRUMENT_DETAILS[current_index_long]['ltp_symbol'],
            'quantity': 1
        }
        fema_trade = FemaModel(
            type=trade['strategy_type'],
            index=trade['index'],
            sell_strike_order_id=simulated_order['order_id'],  # For long, this acts as our entry order ID
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
        position_info_long = fema_trade
        # Update flag table: mark open_trade_flag True and reset signal candle flag.
        FemaModel.set_flags(trade_cur, trade['strategy_type'], False, True, None, None)
        trade_conn.commit()
        release_trade_db_connection(trade_conn, trade_cur)
        msg = (
            f"Trade Entered (Long)\n"
            f"Entry Price: {simulated_order['average_price']}\n"
            f"Stoploss: {trade['stop_loss']}\n"
            f"Target: {trade['profit_target']}\n"
            f"Time: {trade['entry_time']}"
        )
        _send_telegram_in_thread_five_ema(msg)
        logger.info(msg)
    except Exception as e:
        logger.error(f"Long: Error executing simulated entry: {e}")
    finally:
        with fema_buy_entry_lock_long:
            fema_buy_entry_running_long = False
        end_time = datetime.datetime.now()
        logger.info(f"Long: fema_buy_entry execution time: {end_time - start_time}")

# ----------------------------------
# Live Tick Exit Monitoring for Long
# ----------------------------------
def monitor_live_exit_fema_long(ticks):
    """
    Processes live ticks for an active long trade.
    For long trades:
      - Exit if tick price <= stop_loss_level (stop loss triggered).
      - Exit if tick price >= target_level (profit target reached).
      - Exit if at a specified time (e.g., 15:20) and price is above entry price.
    """
    global position_info_long, current_instrument_token_long
    if position_info_long is None:
        return

    for tick in ticks:
        if tick['instrument_token'] == current_instrument_token_long:
            price = tick['last_price']
            if price <= position_info_long.stop_loss_level:
                logger.info("Long: Stop loss triggered via live tick.")
                _send_telegram_in_thread_five_ema("Stoploss Triggered (Long)")
                fema_buy_exit_long(position_info_long)
                return
            if price >= position_info_long.target_level:
                logger.info("Long: Profit target reached via live tick.")
                _send_telegram_in_thread_five_ema("Target Reached (Long)")
                fema_buy_exit_long(position_info_long)
                return
            now = datetime.datetime.now()
            if now.hour == 15 and now.minute == 20 and price > position_info_long.entry_price:
                logger.info("Long: Time-based exit triggered via live tick.")
                _send_telegram_in_thread_five_ema("Time Exit Triggered (Long)")
                fema_buy_exit_long(position_info_long)
                return

# ----------------------------------
# Virtual Order Exit (Simulated for Long Trades)
# ----------------------------------
def fema_buy_exit_long(trade):
    """
    Simulated exit for a long trade.
    Instead of placing an order, we use kite.quote to fetch the current last price.
    After simulated execution, the trade is recorded in the historical_virtual_trades table.
    """
    global fema_buy_exit_running_long, position_info_long
    with fema_buy_exit_lock_long:
        if fema_buy_exit_running_long:
            logger.info("Long: fema_buy_exit already running.")
            return
        fema_buy_exit_running_long = True

    try:
        start_time = datetime.datetime.now()
        quote = kite.quote(INSTRUMENT_DETAILS[current_index_long]['ltp_symbol'])
        simulated_exit_price = quote[INSTRUMENT_DETAILS[current_index_long]['ltp_symbol']]['last_price']
        pnl = (simulated_exit_price - position_info_long.sell_strike_entry_price) * position_info_long.qty
        trade_conn, trade_cur = get_trade_db_connection()
        hv_trade = HistoricalVirtualTrades(
            strategy_type=position_info_long.type,
            index=position_info_long.index,
            entry_time=position_info_long.entry_time,
            entry_price=position_info_long.entry_price,
            exit_time=datetime.datetime.now(),
            exit_price=simulated_exit_price,
            qty=position_info_long.qty,
            pnl=pnl
        )
        hv_trade.insert_virtual_trade(trade_cur)
        trade_conn.commit()
        FemaModel.delete_trade_data_by_type(trade_cur, position_info_long.type)
        trade_conn.commit()
        release_trade_db_connection(trade_conn, trade_cur)
        msg = (
            f"Trade Exited (Long)\n"
            f"Exit Price: {simulated_exit_price}\n"
            f"PnL: {pnl}\n"
            f"Time: {datetime.datetime.now()}"
        )
        _send_telegram_in_thread_five_ema(msg)
        logger.info(msg)
        position_info_long = None
    except Exception as e:
        logger.error(f"Long: Error executing simulated exit: {e}")
    finally:
        with fema_buy_exit_lock_long:
            fema_buy_exit_running_long = False
        end_time = datetime.datetime.now()
        logger.info(f"Long: fema_buy_exit execution time: {end_time - start_time}")

# ----------------------------------
# Live Position Monitoring for Long (Entry & Exit)
# ----------------------------------
def monitor_live_position_fema_long(ticks, strategy_type):
    """
    Call this function with live tick data.
    If no trade is active, it checks for a long entry trigger.
    If a trade is active, it monitors for exit conditions.
    """
    global position_info_long
    if position_info_long is None:
        monitor_live_entry_fema_long(ticks, strategy_type)
    else:
        monitor_live_exit_fema_long(ticks)
