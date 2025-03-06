import threading
import time
import datetime
import pandas as pd
from decimal import Decimal
import logging
from db import get_trade_db_connection, release_trade_db_connection
from models import FemaModel, HistoricalVirtualTrades
from utils import get_indicators_5ema, get_strike_option
from controllers import kite
from .send_telegram_signals import _send_telegram_in_thread_five_ema as _send_telegram_signal
from datetime import time as dtime

logger = logging.getLogger(__name__)

# Global instrument details
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
        'initialized': False,
        'lot_size': 75,
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
        'initialized': False,
        'lot_size': 30,
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
        'initialized': False,
    },
}

# Global locks for long strategy
runner_lock_long = threading.Lock()
monitor_signal_candle_lock_long = threading.Lock()
buy_entry_lock_long = threading.Lock()
buy_exit_lock_long = threading.Lock()

def initialize_long_strategy_state(strategy_type):
    """
    Initializes the LONG_STRATEGY_STATE for each index based on the DB flags
    and loads any open positions from the fema_positions table.
    """
    trade_conn, trade_cur = get_trade_db_connection()
    try:
        # Load flags from fema_flags table.
        for index, state in LONG_STRATEGY_STATE.items():
            flags = FemaModel.get_flags_by_type_and_index(trade_cur, strategy_type, index)
            if flags:
                last_flag = flags[-1]
                state['signal_candle_flag'] = last_flag[0]
                state['signal_candle_low'] = last_flag[1]
                state['signal_candle_high'] = last_flag[2]
                state['open_trade_flag'] = last_flag[3]
            else:
                state['signal_candle_flag'] = False
                state['signal_candle_low'] = None
                state['signal_candle_high'] = None
                state['open_trade_flag'] = False
            state['initialized'] = True
            logger.info(f"Initialized long strategy state for {index}: {state}")

        # Load any open positions from fema_positions table.
        positions = FemaModel.get_trade_data_by_type(trade_cur, strategy_type)
        for pos in positions:
            pos_index = pos[0]  # Assuming the first column is the index.
            if pos_index in LONG_STRATEGY_STATE:
                fema_trade = FemaModel(
                    type=strategy_type,
                    index=pos[0],
                    buy_strike_order_id=pos[1],
                    sell_strike_order_id=pos[2],
                    buy_strike_entry_price=pos[3],
                    sell_strike_entry_price=pos[4],
                    buy_strike_instrument_token=pos[5],
                    sell_strike_instrument_token=pos[6],
                    buy_strike_trading_symbol=pos[7],
                    sell_strike_trading_symbol=pos[8],
                    expiry=pos[9],
                    qty=pos[10],
                    entry_time=pos[11],
                    entry_price=pos[12],
                    stop_loss_level=pos[13],
                    target_level=pos[14]
                )
                LONG_STRATEGY_STATE[pos_index]['position_info'] = fema_trade
                LONG_STRATEGY_STATE[pos_index]['open_trade_flag'] = True
                logger.info(f"Loaded open position for {pos_index}: {fema_trade}")
    except Exception as e:
        logger.error(f"Error initializing long strategy state: {e}")
    finally:
        release_trade_db_connection(trade_conn, trade_cur)

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
        flags = FemaModel.get_flags_by_type_and_index(trade_cur, strategy_type, index)
        if flags:
            last_flag = flags[-1]
            state['signal_candle_flag'] = last_flag[0]
            state['open_trade_flag'] = last_flag[3]
        else:
            state['signal_candle_flag'] = False
            state['open_trade_flag'] = False

        if not state['open_trade_flag']:
            logger.info(f"5EMA Long {index}: Checking for Signal Candle.")
            fema_monitor_signal_candle_long(index, strategy_type)
        elif state['signal_candle_flag'] and not state['open_trade_flag']:
            fema_monitor_signal_candle_long(index, strategy_type)
            logger.info(f"5EMA Long {index}: Monitoring for entry trigger via live ticks and signal candle.")
        elif state['open_trade_flag']:
            logger.info(f"5EMA Long {index}: Monitoring for exit trigger via live ticks.")
    except Exception as error:
        logger.error(f"5EMA Long {index}: Error in runner: {error}")
    finally:
        release_trade_db_connection(trade_conn, trade_cur)
        with runner_lock_long:
            state['runner_running'] = False

def fema_monitor_signal_candle_long(index, strategy_type):
    """
    Checks the last 10 15-minute candles for a long signal candle.
    For long trades, the candle's low becomes the stoploss and the high is the entry trigger.
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

            prev_candle = df.iloc[-2]
            last_candle = df.iloc[-1]
            
            now = datetime.datetime.now().time()
            END_TIME = dtime(15, 25)  # Updated for consistency with short side
            if now >= END_TIME:
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
                
            if last_candle['open'] < last_candle['EMA5'] and float(last_candle['high']) + float(float(last_candle['high']) * 0.0003) < float(last_candle['EMA5']):
                FemaModel.set_flags(trade_cur, strategy_type, index, True, False, last_candle['low'], last_candle['high'])
                trade_conn.commit()
                state['signal_candle_flag'] = True
                state['signal_candle_low'] = last_candle['low']
                state['signal_candle_high'] = last_candle['high']
                msg = (
                    f"5EMA Long {index}:\n"
                    "------------------------------\n"
                    "Signal Found\n"
                    f"Entry Trigger      : {round(state['signal_candle_high'], 2)}\n"
                    f"Stoploss           : {round(state['signal_candle_low'], 2)}\n"
                    f"Time               : {last_candle['time_stamp']}\n"
                    "Action             : Algo is Waiting for entry trigger\n"
                    "------------------------------"
                )
                _send_telegram_signal(msg)
                logger.info(msg)
            elif last_candle['high'] >= last_candle['EMA5']:
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
        except Exception as error:
            logger.error(f"5EMA Long {index}: Error in signal candle monitoring: {error}")
            trade_conn.rollback()
        finally:
            release_trade_db_connection(trade_conn, trade_cur)

def monitor_live_entry_fema_long(ticks, strategy_type, index):
    """
    Processes live ticks to look for a long entry trigger.
    Entry is triggered when the tick price rises to or above the signal_candle_high.
    """
    state = LONG_STRATEGY_STATE[index]
    if not state['signal_candle_flag'] or state['open_trade_flag']:
        return

    for tick in ticks:
        logger.debug(f"Processing tick for {index}: {tick}")
        if tick['instrument_token'] == INSTRUMENT_DETAILS[index]['instrument_token']:
            price = tick['last_price']
            if Decimal(str(price)) >= state['signal_candle_high']:
                entry_price = state['signal_candle_high']
                risk = entry_price - state['signal_candle_low']
                profit_points = max(3 * float(risk), float(entry_price) * 0.003)
                profit_target = float(entry_price) + float(profit_points)
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

def fema_buy_entry_long(trade, index):
    """
    Simulated entry for a long synthetic futures trade.
    Fetches the underlying price, retrieves ATM option details, and stores the trade.
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
        
        call_option_details = get_strike_option(index, 'call', 0)
        if "error" in call_option_details:
            logger.error(f"5EMA Long {index}: Error fetching call strike details: {call_option_details['error']}")
            return
        call_option_key = "NFO:" + call_option_details['tradingsymbol']
        call_option_quote = kite.quote(call_option_key)
        call_option_price = call_option_quote[call_option_key]['last_price']
        
        put_option_details = get_strike_option(index, 'put', 0)
        if "error" in put_option_details:
            logger.error(f"5EMA Long {index}: Error fetching put strike details: {put_option_details['error']}")
            return
        put_option_key = "NFO:" + put_option_details['tradingsymbol']
        put_option_quote = kite.quote(put_option_key)
        put_option_price = put_option_quote[put_option_key]['last_price']
        
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
            f"Underlying Price : {round(underlying_price, 2)}\n"
            f"Call Price       : {round(simulated_call_order['average_price'], 2)}\n"
            f"Put Price        : {round(simulated_put_order['average_price'], 2)}\n"
            f"Stoploss         : {round(trade['stop_loss'], 2)}\n"
            f"Target           : {round(trade['profit_target'], 2)}\n"
            f"Entry Time       : {trade['entry_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Action           : Algo is Buying ATM Call, Selling ATM Put\n"
            "Note             : Trade for educational purposes only\n"
            "------------------------------"
        )
        _send_telegram_signal(msg)
        logger.info(msg)
    except Exception as error:
        logger.error(f"5EMA Long {index}: Error executing entry: {error}")
    finally:
        with buy_entry_lock_long:
            state['buy_entry_running'] = False
        end_time = datetime.datetime.now()
        logger.info(f"5EMA Long {index}: Entry execution time: {end_time - start_time}")

def monitor_live_exit_fema_long(ticks, index):
    """
    Processes live ticks for an active long trade.
    Checks for exit conditions and calls the exit function if met.
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

def fema_buy_exit_long(trade, index, exit_reason):
    """
    Simulated exit for a long synthetic futures trade.
    Fetches current option prices, calculates synthetic PnL,
    records the trade in the historical table, and sends an exit message.
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
        
        call_tradingsymbol = trade.buy_strike_trading_symbol
        put_tradingsymbol = trade.sell_strike_trading_symbol
        call_key = "NFO:" + call_tradingsymbol
        put_key = "NFO:" + put_tradingsymbol

        call_quote = kite.quote(call_key)
        put_quote = kite.quote(put_key)
        call_exit_price = call_quote[call_key]['last_price']
        put_exit_price = put_quote[put_key]['last_price']

        call_entry_price = trade.buy_strike_entry_price
        put_entry_price = trade.sell_strike_entry_price
        pnl = (float(call_exit_price) - float(call_entry_price)) + (float(put_entry_price) - float(put_exit_price))
        
        trade_conn, trade_cur = get_trade_db_connection()
        hv_trade = HistoricalVirtualTrades(
            strategy_type=trade.type,
            index=trade.index,
            entry_time=trade.entry_time,
            entry_price=trade.entry_price,
            exit_time=datetime.datetime.now(),
            exit_price=underlying_price_exit,
            qty=state['lot_size'] * 5,
            pnl=pnl * state['lot_size'] * 5
        )
        hv_trade.insert_virtual_trade(trade_cur)
        trade_conn.commit()
        state['signal_candle_flag'] = False
        state['open_trade_flag'] = False
        state['signal_candle_low'] = None
        state['signal_candle_high'] = None
        FemaModel.delete_trade_data_by_type_and_index(trade_cur, trade.type, trade.index)
        FemaModel.set_flags(trade_cur, trade.type, trade.index, False, False, None, None)
        trade_conn.commit()
        release_trade_db_connection(trade_conn, trade_cur)
        final_msg = (
            f"5EMA Long {index}:\n"
            "------------------------------\n"
            "Trade Exited\n"
            f"Exit Reason          : {exit_reason}\n"
            f"Call Exit Price      : {round(call_exit_price, 2)}\n"
            f"Put Exit Price       : {round(put_exit_price, 2)}\n"
            f"PnL                  : {round(pnl * state['lot_size'] * 5, 2)}\n"
            f"Exit Time            : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Action               : Algo has now exited the trade\n"
            "Note                 : Trade for educational purposes only\n"
            "------------------------------"
        )
        _send_telegram_signal(final_msg)
        logger.info(final_msg)
        state['position_info'] = None
    except Exception as error:
        logger.error(f"5EMA Long {index}: Error executing exit: {error}")
    finally:
        with buy_exit_lock_long:
            state['buy_exit_running'] = False
        end_time = datetime.datetime.now()
        logger.info(f"5EMA Long {index}: Exit execution time: {end_time - start_time}")

def monitor_live_position_fema_long(ticks, strategy_type):
    """
    Processes live tick data for long trades.
    For each index, if no trade is active, checks for an entry trigger;
    if a trade is active, monitors for exit conditions.
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
