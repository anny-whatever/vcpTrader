import threading
import time
import datetime
import pandas as pd
from decimal import Decimal
import logging
from decimal import Decimal
from db import get_trade_db_connection, release_trade_db_connection
from models import FemaModel, HistoricalVirtualTrades
from utils import get_indicators_5ema
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

# Per‑index state for the short strategy (5min timeframe)
SHORT_STRATEGY_STATE = {
    'nifty': {
        'instrument_token': INSTRUMENT_DETAILS['nifty']['instrument_token'],
        'signal_candle_flag': False,
        'open_trade_flag': False,
        'signal_candle_low': None,
        'signal_candle_high': None,
        'position_info': None,
        'runner_running': False,
        'buy_entry_running': False,
        'buy_exit_running': False,
        'initialized': False,
        'lot_size': 75,
    },
    'banknifty': {
        'instrument_token': INSTRUMENT_DETAILS['banknifty']['instrument_token'],
        'signal_candle_flag': False,
        'open_trade_flag': False,
        'signal_candle_low': None,
        'signal_candle_high': None,
        'position_info': None,
        'runner_running': False,
        'buy_entry_running': False,
        'buy_exit_running': False,
        'initialized': False,
        'lot_size': 30,
    },
    'finnifty': {
        'instrument_token': INSTRUMENT_DETAILS['finnifty']['instrument_token'],
        'signal_candle_flag': False,
        'open_trade_flag': False,
        'signal_candle_low': None,
        'signal_candle_high': None,
        'position_info': None,
        'runner_running': False,
        'buy_entry_running': False,
        'buy_exit_running': False,
        'initialized': False,
    },
}

# Global locks for short strategy
runner_lock_short = threading.Lock()
monitor_signal_candle_lock_short = threading.Lock()
buy_entry_lock_short = threading.Lock()
buy_exit_lock_short = threading.Lock()

def initialize_short_strategy_state(strategy_type):
    """
    Initializes the SHORT_STRATEGY_STATE for each index based on the DB flags 
    and loads any open positions from the fema_positions table.
    """
    trade_conn, trade_cur = get_trade_db_connection()
    try:
        # Initialize flag values from fema_flags table.
        for index, state in SHORT_STRATEGY_STATE.items():
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
            logger.info(f"Initialized short strategy state for {index}: {state}")

        # --- New Code: Load any open positions from fema_positions table ---
        # Ensure that FemaModel.get_trade_data_by_type returns the 'index' as the first column.
        positions = FemaModel.get_trade_data_by_type(trade_cur, strategy_type)
        for pos in positions:
            pos_index = pos[0]  # Assuming the first column is the index.
            if pos_index in SHORT_STRATEGY_STATE:
                fema_trade = FemaModel(
                    type=strategy_type,
                    index=pos[0],
                    sell_strike_order_id=pos[1],
                    buy_strike_order_id=pos[2],
                    sell_strike_entry_price=pos[3],
                    buy_strike_entry_price=pos[4],
                    sell_strike_instrument_token=pos[5],
                    buy_strike_instrument_token=pos[6],
                    sell_strike_trading_symbol=pos[7],
                    buy_strike_trading_symbol=pos[8],
                    expiry=pos[9],
                    qty=pos[10],
                    entry_time=pos[11],
                    entry_price=pos[12],
                    stop_loss_level=pos[13],
                    target_level=pos[14]
                )
                SHORT_STRATEGY_STATE[pos_index]['position_info'] = fema_trade
                SHORT_STRATEGY_STATE[pos_index]['open_trade_flag'] = True
                logger.info(f"Loaded open position for {pos_index}: {fema_trade}")
    except Exception as e:
        logger.error(f"Error initializing short strategy state: {e}")
    finally:
        release_trade_db_connection(trade_conn, trade_cur)


def fema_runner_five_minute_short(index, strategy_type):
    """
    Runner function for the 5EMA short strategy on 5min TF.
    """
    state = SHORT_STRATEGY_STATE[index]
    trade_conn, trade_cur = get_trade_db_connection()
    logger.info(f"5EMA Short {index}: Strategy runner started on 5min TF")
    with runner_lock_short:
        if state['runner_running']:
            logger.info(f"5EMA Short {index}: Runner already running.")
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

        if not state['open_trade_flag'] and not state['signal_candle_flag']:
            logger.info(f"5EMA Short {index}: Checking for Signal Candle.")
            fema_monitor_signal_candle_short(index, strategy_type)
        elif state['signal_candle_flag'] and not state['open_trade_flag']:
            fema_monitor_signal_candle_short(index, strategy_type)
            logger.info(f"5EMA Short {index}: Monitoring for entry trigger via live ticks and signal candle.")
        elif state['open_trade_flag']:
            logger.info(f"5EMA Short {index}: Monitoring for exit trigger via live ticks.")
    except Exception as error:
        logger.error(f"5EMA Short {index}: Error in runner: {error}")
    finally:
        release_trade_db_connection(trade_conn, trade_cur)
        with runner_lock_short:
            state['runner_running'] = False

def fema_monitor_signal_candle_short(index, strategy_type):
    """
    Checks the last 10 5-minute candles for a short signal candle.
    Signal condition for short: candle['open'] > candle['EMA5'] and candle['low'] > candle['EMA5'].
    """
    state = SHORT_STRATEGY_STATE[index]
    with monitor_signal_candle_lock_short:
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
            logger.info(rows)
            df = pd.DataFrame(rows, columns=['instrument_token', 'time_stamp', 'open', 'high', 'low', 'close', 'interval'])
            if df.empty:
                logger.info(f"5EMA Short {index}: No 5min data available.")
                return

            df = get_indicators_5ema(df)
            df = df.dropna()
            if df.empty:
                logger.info(f"5EMA Short {index}: Insufficient data for indicators.")
                return

            prev_candle = df.iloc[-2]
            last_candle = df.iloc[-1]
            
            now = datetime.datetime.now().time()
            END_TIME   = dtime(15, 25)
            if now >= END_TIME:
                FemaModel.set_flags(trade_cur, strategy_type, index, False, False, None, None)
                trade_conn.commit()
                if state['signal_candle_flag']:
                    msg = (
                        f"5EMA Short {index}:\n"
                        "------------------------------\n"
                        "Signal Cancelled\n"
                        "Reason             : Entry rules not met\n"
                        "------------------------------"
                    )
                    _send_telegram_signal(msg)
                    logger.info(msg)
                state['signal_candle_flag'] = False
            
            if last_candle['open'] > last_candle['EMA5'] and float(last_candle['low']) - float(float(last_candle['low']) * 0.0001) > float(last_candle['EMA5']):
                FemaModel.set_flags(trade_cur, strategy_type, index, True, False, last_candle['low'], last_candle['high'])
                trade_conn.commit()
                state['signal_candle_flag'] = True
                state['signal_candle_low'] = last_candle['low']
                state['signal_candle_high'] = last_candle['high']
                msg = (
                    f"5EMA Short {index}:\n"
                    "------------------------------\n"
                    "Signal Found\n"
                    f"Entry Trigger      : {round(state['signal_candle_low'], 2)}\n"
                    f"Stoploss           : {round(state['signal_candle_high'], 2)}\n"
                    f"Time               : {last_candle['time_stamp']}\n"
                    "Action             : Algo is Waiting for entry trigger\n"
                    "------------------------------"
                )
                _send_telegram_signal(msg)
                logger.info(msg)
            elif last_candle['low'] <= last_candle['EMA5']:
                FemaModel.set_flags(trade_cur, strategy_type, index, False, False, None, None)
                trade_conn.commit()
                if state['signal_candle_flag']:
                    msg = (
                        f"5EMA Short {index}:\n"
                        "------------------------------\n"
                        "Signal Cancelled\n"
                        "Reason             : Entry rules not met\n"
                        "------------------------------"
                    )
                    _send_telegram_signal(msg)
                    logger.info(msg)
                state['signal_candle_flag'] = False
        except Exception as error:
            logger.error(f"5EMA Short {index}: Error in signal candle monitoring: {error}")
            trade_conn.rollback()
        finally:
            release_trade_db_connection(trade_conn, trade_cur)

def monitor_live_entry_fema_short(ticks, strategy_type, index):
    """
    Processes live ticks to look for a short entry trigger.
    Entry is triggered when tick price falls to or below signal_candle_low.
    """
    state = SHORT_STRATEGY_STATE[index]
    if not state['signal_candle_flag'] or state['open_trade_flag']:
        return

    for tick in ticks:
        logger.debug(f"Processing tick for {index}: {tick}")
        if tick['instrument_token'] == INSTRUMENT_DETAILS[index]['instrument_token']:
            price = tick['last_price']
            if Decimal(str(price)) <= state['signal_candle_low']:
                entry_price = state['signal_candle_low']
                risk = state['signal_candle_high'] - entry_price
                profit_points = max(3 * float(risk), float(entry_price) * 0.003)
                profit_target = float(entry_price) - float(profit_points)
                stop_loss = float(state['signal_candle_high'])
                trade = {
                    'entry_time': datetime.datetime.now(),
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'profit_target': profit_target,
                    'strategy_type': strategy_type,
                    'index': index
                }
                fema_buy_entry_short(trade, index)

def fema_buy_entry_short(trade, index):
    """
    Simulated entry for a short synthetic futures trade.
    Fetches underlying price, retrieves ATM option details, and stores trade details.
    """
    state = SHORT_STRATEGY_STATE[index]
    with buy_entry_lock_short:
        if state['buy_entry_running']:
            logger.info(f"5EMA Short {index}: Entry already running.")
            return
        state['buy_entry_running'] = True

    try:
        start_time = datetime.datetime.now()
        underlying_quote = kite.quote(INSTRUMENT_DETAILS[index]['ltp_symbol'])
        underlying_price = underlying_quote[INSTRUMENT_DETAILS[index]['ltp_symbol']]['last_price']
        
        from utils import get_strike_option
        call_option_details = get_strike_option(index, 'call', 0)
        if "error" in call_option_details:
            logger.error(f"5EMA Short {index}: Error fetching call strike details: {call_option_details['error']}")
            return
        call_option_key = "NFO:" + call_option_details['tradingsymbol']
        call_option_quote = kite.quote(call_option_key)
        call_option_price = call_option_quote[call_option_key]['last_price']
        
        put_option_details = get_strike_option(index, 'put', 0)
        if "error" in put_option_details:
            logger.error(f"5EMA Short {index}: Error fetching put strike details: {put_option_details['error']}")
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
        
        # For a short trade, typically the roles of call and put are reversed.
        fema_trade = FemaModel(
            type=trade['strategy_type'],
            index=trade['index'],
            sell_strike_order_id=simulated_call_order['order_id'],
            buy_strike_order_id=simulated_put_order['order_id'],
            sell_strike_entry_price=simulated_call_order['average_price'],
            buy_strike_entry_price=simulated_put_order['average_price'],
            sell_strike_instrument_token=simulated_call_order['instrument_token'],
            buy_strike_instrument_token=simulated_put_order['instrument_token'],
            sell_strike_trading_symbol=simulated_call_order['tradingsymbol'],
            buy_strike_trading_symbol=simulated_put_order['tradingsymbol'],
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
            f"5EMA Short {index}:\n"
            "------------------------------\n"
            "Trade Entered\n"
            f"Underlying Price         : {round(underlying_price, 2)}\n"
            f"Call Option Price (Sell) : {round(simulated_call_order['average_price'], 2)}\n"
            f"Put Option Price (Buy)   : {round(simulated_put_order['average_price'], 2)}\n"
            f"Stoploss                 : {round(trade['stop_loss'], 2)}\n"
            f"Target                   : {round(trade['profit_target'], 2)}\n"
            f"Entry Time               : {trade['entry_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Action                   : Algo is Buying ATM Put, Selling ATM Call\n"
            "Note                     : Trade for educational purposes only\n"
            "------------------------------"
        )
        _send_telegram_signal(msg)
        logger.info(msg)
    except Exception as error:
        logger.error(f"5EMA Short {index}: Error executing simulated entry: {error}")
    finally:
        with buy_entry_lock_short:
            state['buy_entry_running'] = False
        end_time = datetime.datetime.now()
        logger.info(f"5EMA Short {index}: Entry execution time: {end_time - start_time}")

def monitor_live_exit_fema_short(ticks, index):
    """
    Processes live ticks for an active short trade.
    Checks for exit conditions and calls the exit function if met.
    """
    state = SHORT_STRATEGY_STATE[index]
    if state['position_info'] is None:
        return

    exit_reason = None
    for tick in ticks:
        if tick['instrument_token'] == INSTRUMENT_DETAILS[index]['instrument_token']:
            price = tick['last_price']
            if price <= state['position_info'].target_level:
                exit_reason = f"Target Achieved\nPrice            : {price}"
                break
            if price >= state['position_info'].stop_loss_level:
                exit_reason = f"Stoploss Triggered\nPrice            : {price}"
                break
            now = datetime.datetime.now()
            if now.hour == 15 and now.minute == 20:
                exit_reason = f"Time-based Exit\nPrice            : {price}"
                break

    if exit_reason:
        fema_buy_exit_short(state['position_info'], index, exit_reason)

def fema_buy_exit_short(trade, index, exit_reason):
    """
    Simulated exit for a short synthetic futures trade.
    Fetches current option prices, calculates synthetic PnL,
    records the trade in the historical table, and sends an exit message.
    """
    state = SHORT_STRATEGY_STATE[index]
    with buy_exit_lock_short:
        if state['buy_exit_running']:
            logger.info(f"5EMA Short {index}: Exit already running.")
            return
        state['buy_exit_running'] = True

    try:
        start_time = datetime.datetime.now()
        underlying_quote_exit = kite.quote(INSTRUMENT_DETAILS[index]['ltp_symbol'])
        underlying_price_exit = underlying_quote_exit[INSTRUMENT_DETAILS[index]['ltp_symbol']]['last_price']
        
        call_tradingsymbol = trade.sell_strike_trading_symbol
        put_tradingsymbol = trade.buy_strike_trading_symbol

        call_key = "NFO:" + call_tradingsymbol
        put_key = "NFO:" + put_tradingsymbol

        call_quote = kite.quote(call_key)
        put_quote = kite.quote(put_key)
        call_exit_price = call_quote[call_key]['last_price']
        put_exit_price = put_quote[put_key]['last_price']

        
        call_entry_price = trade.sell_strike_entry_price
        put_entry_price = trade.buy_strike_entry_price
        pnl = (float(call_entry_price) - float(call_exit_price)) + (float(put_exit_price) - float(put_entry_price))
        
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
            f"5EMA Short {index}:\n"
            "------------------------------\n"
            "Trade Exited\n"
            f"Exit Reason          : {exit_reason}\n"
            f"Call Option Exit Price : {round(call_exit_price, 2)}\n"
            f"Put Option Exit Price  : {round(put_exit_price, 2)}\n"
            f"PnL                    : {round(pnl * state['lot_size'] * 5, 2)}\n"
            f"Exit Time              : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Action                 : Algo has now exited the trade\n"
            f"Note                   : Trade for educational purposes only\n"
            "------------------------------"
        )
        _send_telegram_signal(final_msg)
        logger.info(final_msg)
        state['position_info'] = None
    except Exception as error:
        logger.error(f"5EMA Short {index}: Error executing simulated exit: {error}")
    finally:
        with buy_exit_lock_short:
            state['buy_exit_running'] = False
        end_time = datetime.datetime.now()
        logger.info(f"5EMA Short {index}: Exit execution time: {end_time - start_time}")

def monitor_live_position_fema_short(ticks, strategy_type):
    """
    Processes live tick data for short trades.
    For each index, if no trade is active, checks for an entry trigger;
    if a trade is active, monitors for exit conditions.
    """
    for index, state in SHORT_STRATEGY_STATE.items():
        token = INSTRUMENT_DETAILS[index]['instrument_token']
        relevant_ticks = [tick for tick in ticks if tick['instrument_token'] == token]
        if not relevant_ticks:
            continue
        if state['position_info'] is None:
            monitor_live_entry_fema_short(relevant_ticks, strategy_type, index)
        else:
            monitor_live_exit_fema_short(relevant_ticks, index)
