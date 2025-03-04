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
from .send_telegram_signals import _send_telegram_in_thread_five_ema as _send_telegram_signal

logger = logging.getLogger(__name__)

# Global instrument details (mapping index to instrument token)
INSTRUMENT_DETAILS = {
    'nifty': {'instrument_token': 256265, 'ltp_symbol': 'NSE:NIFTY 50'},
    'banknifty': {'instrument_token': 260105, 'ltp_symbol': 'NSE:NIFTY BANK'},
    'finnifty': {'instrument_token': 257801, 'ltp_symbol': 'NSE:NIFTY FIN SERVICE'},
}

# Per‑index state for the long strategy (15min timeframe)
LONG_STRATEGY_STATE = {
    'nifty': {
        'instrument_token': INSTRUMENT_DETAILS['nifty']['instrument_token'],
        'runner_running': False,
        'signal_candle_flag': False,
        'open_trade_flag': False,
        'signal_candle_low': None,
        'signal_candle_high': None,
        'position_info': None,
        'buy_entry_running': False,
        'buy_exit_running': False,
    },
    'banknifty': {
        'instrument_token': INSTRUMENT_DETAILS['banknifty']['instrument_token'],
        'runner_running': False,
        'signal_candle_flag': False,
        'open_trade_flag': False,
        'signal_candle_low': None,
        'signal_candle_high': None,
        'position_info': None,
        'buy_entry_running': False,
        'buy_exit_running': False,
    },
    'finnifty': {
        'instrument_token': INSTRUMENT_DETAILS['finnifty']['instrument_token'],
        'runner_running': False,
        'signal_candle_flag': False,
        'open_trade_flag': False,
        'signal_candle_low': None,
        'signal_candle_high': None,
        'position_info': None,
        'buy_entry_running': False,
        'buy_exit_running': False,
    },
}

# Global locks for long strategy
runner_lock_long = threading.Lock()
monitor_signal_candle_lock_long = threading.Lock()
buy_entry_lock_long = threading.Lock()
buy_exit_lock_long = threading.Lock()

# ----------------------------------
# Runner Function for Long Strategy (15min TF)
# ----------------------------------
def fema_runner_fifteen_minute_long(index, strategy_type):
    """
    Runner function for the 5EMA long strategy using 15min candles.
    """
    state = LONG_STRATEGY_STATE[index]
    trade_conn, trade_cur = get_trade_db_connection()
    logger.info(f"5EMA Long {index}: Strategy runner started on 15min TF")
    with runner_lock_long:
        if state['runner_running']:
            logger.info(f"5EMA Long {index}: Runner already running.")
            return
        state['runner_running'] = True

    try:
        flags = FemaModel.get_flags_by_type(trade_cur, strategy_type)
        if flags:
            last_flag = flags[-1]  # (signal_candle_flag, signal_candle_low, signal_candle_high, open_trade_flag, trail_flag)
            state['signal_candle_flag'] = last_flag[0]
            state['open_trade_flag'] = last_flag[3]
        else:
            state['signal_candle_flag'] = False
            state['open_trade_flag'] = False

        if not state['open_trade_flag']:
            logger.info(f"5EMA Long {index}: Checking for Signal Candle.")
            fema_monitor_signal_candle_long(index, strategy_type)
        elif state['signal_candle_flag'] and not state['open_trade_flag']:
            logger.info(f"5EMA Long {index}: Monitoring for entry trigger via live ticks.")
            # Live ticks will trigger monitor_live_entry_fema_long
        elif state['open_trade_flag']:
            logger.info(f"5EMA Long {index}: Monitoring for exit trigger via live ticks.")
            # Live ticks will trigger monitor_live_exit_fema_long
    except Exception as e:
        logger.error(f"5EMA Long {index}: Error in runner: {e}")
    finally:
        release_trade_db_connection(trade_conn, trade_cur)
        with runner_lock_long:
            state['runner_running'] = False

# ----------------------------------
# Signal Candle Monitoring for Long
# ----------------------------------
def fema_monitor_signal_candle_long(index, strategy_type):
    """
    Checks the last 10 15-minute candles for a long signal candle.
    Signal condition for long: candle['open'] < candle['EMA5'] and candle['high'] < candle['EMA5'].
    For long trades, the candle's low becomes the stoploss and the candle's high is the entry trigger.
    """
    state = LONG_STRATEGY_STATE[index]
    with monitor_signal_candle_lock_long:
        trade_conn, trade_cur = get_trade_db_connection()
        try:
            token = INSTRUMENT_DETAILS[index]['instrument_token']
            select_query = """
            SELECT * FROM (
                SELECT * FROM ohlc_resampled
                WHERE instrument_token = %s AND interval = '15min'
                ORDER BY time_stamp DESC LIMIT 10
            ) as r ORDER BY r.time_stamp ASC;
            """
            trade_cur.execute(select_query, (token,))
            rows = trade_cur.fetchall()
            logger.info(rows)
            df = pd.DataFrame(rows, columns=['instrument_token', 'time_stamp', 'open', 'high', 'low', 'close', 'interval'])
            if df.empty:
                logger.info(f"5EMA Long {index}: No 15min data available.")
                return

            df = get_indicators_5ema(df)
            df = df.dropna()
            if df.empty:
                logger.info(f"5EMA Long {index}: Insufficient data for indicators.")
                return

            last_candle = df.iloc[-1]
            if last_candle['open'] < last_candle['EMA5'] and last_candle['high'] < last_candle['EMA5']:
                FemaModel.set_flags(trade_cur, strategy_type, index, True, False, last_candle['low'], last_candle['high'])
                trade_conn.commit()
                state['signal_candle_flag'] = True
                state['signal_candle_low'] = last_candle['low']
                state['signal_candle_high'] = last_candle['high']
                msg = (
                    f"5EMA Long {index}:\n"
                    "------------------------------\n"
                    "Signal Found\n"
                    f"Entry Trigger      : {state['signal_candle_high']}\n"
                    f"Stoploss           : {state['signal_candle_low']}\n"
                    f"Time               : {last_candle['time_stamp']}\n"
                    "Action              : Algo is Waiting for entry trigger\n"
                    "------------------------------"
                )
                _send_telegram_signal(msg)
                logger.info(msg)
            else:
                FemaModel.set_flags(trade_cur, strategy_type, index, False, False, None, None)
                trade_conn.commit()
                if state['signal_candle_flag']:
                    msg = (
                        f"5EMA Long {index}:\n"
                        "------------------------------\n"
                        "Signal Cancelled\n"
                        "Reason             : Entry rules not met\n"
                        "------------------------------"
                    )
                    _send_telegram_signal(msg)
                    logger.info(msg)
                state['signal_candle_flag'] = False
        except Exception as e:
            logger.error(f"5EMA Long {index}: Error in signal candle monitoring: {e}")
            trade_conn.rollback()
        finally:
            release_trade_db_connection(trade_conn, trade_cur)

# ----------------------------------
# Live Tick Entry Monitoring for Long
# ----------------------------------
def monitor_live_entry_fema_long(ticks, strategy_type, index):
    """
    Processes live ticks to look for a long entry trigger.
    For a long trade, entry is triggered when tick price rises to or above the signal_candle_high.
    """
    state = LONG_STRATEGY_STATE[index]
    if not state['signal_candle_flag'] or state['open_trade_flag']:
        return

    for tick in ticks:
        if tick['instrument_token'] == INSTRUMENT_DETAILS[index]['instrument_token']:
            price = tick['last_price']
            if price >= state['signal_candle_high']:
                entry_price = state['signal_candle_high']
                risk = entry_price - state['signal_candle_low']
                profit_points = max(3 * risk, entry_price * 0.003)
                profit_target = entry_price + profit_points
                stop_loss = state['signal_candle_low']
                trade = {
                    'entry_time': datetime.datetime.now(),
                    'entry_price': price,
                    'stop_loss': stop_loss,
                    'profit_target': profit_target,
                    'strategy_type': strategy_type,
                    'index': index
                }
                fema_buy_entry_long(trade, index)
                break

# ----------------------------------
# Virtual Order Entry (Simulated for Long Trades)
# ----------------------------------
def fema_buy_entry_long(trade, index):
    """
    Simulated entry for a long synthetic futures trade.
    Fetches the underlying's current price, retrieves ATM call and put option details,
    and stores trade details in the positions table.
    """
    state = LONG_STRATEGY_STATE[index]
    with buy_entry_lock_long:
        if state['buy_entry_running']:
            logger.info(f"5EMA Long {index}: Entry already running.")
            return
        state['buy_entry_running'] = True

    try:
        start_time = datetime.datetime.now()
        underlying_quote = kite.quote(INSTRUMENT_DETAILS[index]['ltp_symbol'])
        underlying_price = underlying_quote[INSTRUMENT_DETAILS[index]['ltp_symbol']]['last_price']
        
        from signals import get_strike_option
        call_option_details = get_strike_option(index, 'call', 0)
        if "error" in call_option_details:
            logger.error(f"5EMA Long {index}: Error fetching call strike details: {call_option_details['error']}")
            return
        call_option_quote = kite.quote(call_option_details['tradingsymbol'])
        call_option_price = call_option_quote[call_option_details['tradingsymbol']]['last_price']
        
        put_option_details = get_strike_option(index, 'put', 0)
        if "error" in put_option_details:
            logger.error(f"5EMA Long {index}: Error fetching put strike details: {put_option_details['error']}")
            return
        put_option_quote = kite.quote(put_option_details['tradingsymbol'])
        put_option_price = put_option_quote[put_option_details['tradingsymbol']]['last_price']
        
        simulated_call_order = {
            'order_id': f"SIM-CALL-{int(time.time())}",
            'average_price': call_option_price,
            'instrument_token': call_option_details['instrument_token'],
            'tradingsymbol': call_option_details['tradingsymbol'],
            'quantity': 1
        }
        simulated_put_order = {
            'order_id': f"SIM-PUT-{int(time.time())}",
            'average_price': put_option_price,
            'instrument_token': put_option_details['instrument_token'],
            'tradingsymbol': put_option_details['tradingsymbol'],
            'quantity': 1
        }
        
        fema_trade = FemaModel(
            type=trade['strategy_type'],
            index=trade['index'],
            buy_strike_order_id=simulated_call_order['order_id'],
            sell_strike_order_id=simulated_put_order['order_id'],
            buy_strike_entry_price=simulated_call_order['average_price'],
            sell_strike_entry_price=simulated_put_order['average_price'],
            buy_strike_instrument_token=simulated_call_order['instrument_token'],
            sell_strike_instrument_token=simulated_put_order['instrument_token'],
            buy_strike_trading_symbol=simulated_call_order['tradingsymbol'],
            sell_strike_trading_symbol=simulated_put_order['tradingsymbol'],
            expiry=call_option_details.get('expiry'),
            qty=simulated_call_order['quantity'],
            entry_time=trade['entry_time'],
            entry_price=underlying_price,
            stop_loss_level=trade['stop_loss'],
            target_level=trade['profit_target']
        )
        trade_conn, trade_cur = get_trade_db_connection()
        FemaModel.create_table_positions(trade_cur)
        FemaModel.create_table_flags(trade_cur)
        fema_trade.insert_trade_data(trade_cur)
        trade_conn.commit()
        state['position_info'] = fema_trade
        FemaModel.set_flags(trade_cur, trade['strategy_type'], trade['index'], False, True, None, None)
        trade_conn.commit()
        release_trade_db_connection(trade_conn, trade_cur)
        msg = (
            f"5EMA Long {index}:\n"
            "------------------------------\n"
            "Trade Entered\n"
            f"Underlying Price : {underlying_price}\n"
            f"Call Price       : {simulated_call_order['average_price']}\n"
            f"Put Price        : {simulated_put_order['average_price']}\n"
            f"Stoploss         : {trade['stop_loss']}\n"
            f"Target           : {trade['profit_target']}\n"
            f"Entry Time       : {trade['entry_time']}\n"
            f"Action           : Algo is Buying ATM Call, Selling ATM Put\n"
            f"Note             : Trade for educational purposes only\n"
            "------------------------------"
        )
        _send_telegram_signal(msg)
        logger.info(msg)
    except Exception as e:
        logger.error(f"5EMA Long {index}: Error executing entry: {e}")
    finally:
        with buy_entry_lock_long:
            state['buy_entry_running'] = False
        end_time = datetime.datetime.now()
        logger.info(f"5EMA Long {index}: Entry execution time: {end_time - start_time}")

# ----------------------------------
# Live Tick Exit Monitoring for Long
# ----------------------------------
def monitor_live_exit_fema_long(ticks, index):
    """
    Processes live ticks for an active long trade.
    If an exit condition is met, captures the exit reason and calls the exit function.
    """
    state = LONG_STRATEGY_STATE[index]
    if state['position_info'] is None:
        return

    exit_reason = None
    for tick in ticks:
        if tick['instrument_token'] == INSTRUMENT_DETAILS[index]['instrument_token']:
            price = tick['last_price']
            if price <= state['position_info'].stop_loss_level:
                exit_reason = f"Stoploss Triggered\nPrice              : {price}"
                break
            if price >= state['position_info'].target_level:
                exit_reason = f"Target Achieved\nPrice              : {price}"
                break
            now = datetime.datetime.now()
            if now.hour == 15 and now.minute == 20 and price > state['position_info'].entry_price:
                exit_reason = f"Time-based Exit\nPrice              : {price}"
                break

    if exit_reason:
        fema_buy_exit_long(state['position_info'], index, exit_reason)

# ----------------------------------
# Virtual Order Exit (Simulated for Long Trades)
# ----------------------------------
def fema_buy_exit_long(trade, index, exit_reason):
    """
    Simulated exit for a long synthetic futures trade.
    Fetches current option prices, calculates synthetic PnL,
    records the trade in the historical_virtual_trades table,
    and sends a unified exit message that includes the exit reason.
    """
    state = LONG_STRATEGY_STATE[index]
    with buy_exit_lock_long:
        if state['buy_exit_running']:
            logger.info(f"5EMA Long {index}: Exit already running.")
            return
        state['buy_exit_running'] = True

    try:
        start_time = datetime.datetime.now()
        underlying_quote_exit = kite.quote(INSTRUMENT_DETAILS[index]['ltp_symbol'])
        underlying_price_exit = underlying_quote_exit[INSTRUMENT_DETAILS[index]['ltp_symbol']]['last_price']
        
        call_tradingsymbol = state['position_info'].buy_strike_trading_symbol
        put_tradingsymbol = state['position_info'].sell_strike_trading_symbol

        call_quote = kite.quote(call_tradingsymbol)
        put_quote = kite.quote(put_tradingsymbol)
        call_exit_price = call_quote[call_tradingsymbol]['last_price']
        put_exit_price = put_quote[put_tradingsymbol]['last_price']

        call_entry_price = state['position_info'].buy_strike_entry_price
        put_entry_price = state['position_info'].sell_strike_entry_price
        pnl = (call_exit_price - call_entry_price) + (put_entry_price - put_exit_price)
        
        trade_conn, trade_cur = get_trade_db_connection()
        hv_trade = HistoricalVirtualTrades(
            strategy_type=state['position_info'].type,
            index=state['position_info'].index,
            entry_time=state['position_info'].entry_time,
            entry_price=state['position_info'].entry_price,
            exit_time=datetime.datetime.now(),
            exit_price=(call_exit_price + put_exit_price) / 2,
            qty=state['position_info'].qty,
            pnl=pnl
        )
        hv_trade.insert_virtual_trade(trade_cur)
        trade_conn.commit()
        FemaModel.delete_trade_data_by_type(trade_cur, state['position_info'].type)
        trade_conn.commit()
        release_trade_db_connection(trade_conn, trade_cur)
        final_msg = (
            f"5EMA Long {index}:\n"
            "------------------------------\n"
            "Trade Exited\n"
            f"Exit Reason          : {exit_reason}\n"
            f"Underlying Exit Price: {underlying_price_exit}\n"
            f"Call Exit Price      : {call_exit_price}\n"
            f"Put Exit Price       : {put_exit_price}\n"
            f"PnL                  : {pnl}\n"
            f"Exit Time            : {datetime.datetime.now()}\n"
            f"Action               : Algo has now exited the trade\n"
            "Note                  : Trade for educational purposes only\n"
            "------------------------------"
        )
        _send_telegram_signal(final_msg)
        logger.info(final_msg)
        state['position_info'] = None
    except Exception as e:
        logger.error(f"5EMA Long {index}: Error executing exit: {e}")
    finally:
        with buy_exit_lock_long:
            state['buy_exit_running'] = False
        end_time = datetime.datetime.now()
        logger.info(f"5EMA Long {index}: Exit execution time: {end_time - start_time}")

# ----------------------------------
# Live Position Monitoring for Long (Entry & Exit)
# ----------------------------------
def monitor_live_position_fema_long(ticks, strategy_type):
    """
    Processes live tick data.
    For each index, if no trade is active, checks for a long entry trigger.
    If a trade is active, monitors for exit conditions.
    """
    for index, state in LONG_STRATEGY_STATE.items():
        token = INSTRUMENT_DETAILS[index]['instrument_token']
        relevant_ticks = [tick for tick in ticks if tick['instrument_token'] == token]
        if not relevant_ticks:
            continue
        if state['position_info'] is None:
            monitor_live_entry_fema_long(relevant_ticks, strategy_type, index)
        else:
            monitor_live_exit_fema_long(relevant_ticks, index)
