# get_display_data.py
import logging
import pytz
from datetime import datetime, time
import pandas as pd
import pandas_ta as ta
from db import get_db_connection, close_db_connection
from models import PriceAlert, AlertMessage, RiskPool, SaveTradeDetails, SaveHistoricalTradeDetails, SaveOHLC
from controllers import kite  # Assumes you have a kite module for live quotes

logger = logging.getLogger(__name__)
TIMEZONE = pytz.timezone("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 35)

def fetch_risk_pool_for_display():
    
    try:
        conn, cur = get_db_connection()
        risk_pool = RiskPool.fetch_risk_pool(cur)
        if risk_pool:
            return {
                "used_risk": float(risk_pool['used_risk']),
                "available_risk": float(risk_pool['available_risk'])
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching risk pool for display: {e}")
        raise
    finally:
        if conn and cur:
            close_db_connection()

def format_trade_record(trade):
    return {
        "trade_id" : trade['trade_id'],
        "stock_name": trade['stock_name'],
        "token": trade['token'],
        "entry_time": trade['entry_time'].isoformat() if trade['entry_time'] else None,
        "entry_price": float(trade['entry_price']),
        "stop_loss": float(trade['stop_loss']),
        "target": float(trade['target']),
        "initial_qty": float(trade['initial_qty']),
        "current_qty": float(trade['current_qty']),
        "booked_pnl": float(trade['booked_pnl']),
        "auto_exit": trade['auto_exit']
    }

def fetch_trade_details_for_display():
    
    try:
        conn, cur = get_db_connection()
        trade_details = SaveTradeDetails.fetch_all_trades(cur)
        if not trade_details:
            return []
        unique_tokens = list({trade['token'] for trade in trade_details})
        try:
            live_quotes = kite.quote(unique_tokens)
        except Exception as e:
            logger.error(f"Error fetching live quotes: {e}")
            live_quotes = {}
        formatted_trades = []
        for trade in trade_details:
            formatted = format_trade_record(trade)
            token_str = str(trade['token'])
            formatted['last_price'] = float(live_quotes.get(token_str, {}).get('last_price', 0))
            formatted_trades.append(formatted)
        return formatted_trades
    except Exception as e:
        logger.error(f"Error in fetch_trade_details_for_display: {e}")
        raise
    finally:
        if conn and cur:
            close_db_connection()

def format_historical_trade_record(trade):
    return {
        "stock_name": trade['stock_name'],
        "entry_time": trade['entry_time'].isoformat() if trade['entry_time'] else None,
        "entry_price": float(trade['entry_price']),
        "exit_time": trade['exit_time'].isoformat() if trade['exit_time'] else None,
        "exit_price": float(trade['exit_price']),
        "final_pnl": float(trade['final_pnl']),
        "highest_qty": float(trade['highest_qty'])
    }

def fetch_historical_trade_details_for_display():
    
    try:
        conn, cur = get_db_connection()
        trade_details = SaveHistoricalTradeDetails.fetch_all_historical_trades(cur)
        return [format_historical_trade_record(trade) for trade in trade_details] if trade_details else []
    except Exception as e:
        logger.error(f"Error fetching historical trade details: {e}")
        raise
    finally:
        if conn and cur:
            close_db_connection()

def get_combined_ohlc(instrument_token, symbol):
    
    try:
        conn, cur = get_db_connection()
        historical_data = SaveOHLC.fetch_by_instrument(cur, instrument_token)
        combined_data = [dict(record) for record in historical_data] if historical_data else []
        now = datetime.now(TIMEZONE)
        today_date = now.date()
        if combined_data:
            last_historical_date = pd.to_datetime(combined_data[-1]['date']).astimezone(TIMEZONE).date()
            if last_historical_date < today_date and MARKET_OPEN <= now.time() <= MARKET_CLOSE:
                try:
                    quote = kite.quote(instrument_token)[str(instrument_token)]
                    logger.info(f'quote: {quote}')
                    ohlc = quote.get('ohlc', {})
                    if ohlc:
                        today_entry = {
                            'instrument_token': instrument_token,
                            'symbol': symbol,
                            'interval': 'day',
                            'date': TIMEZONE.localize(datetime.combine(today_date, time(15, 30))),
                            'open': ohlc['open'],
                            'high': ohlc['high'],
                            'low': ohlc['low'],
                            'close': quote.get('last_price', 0),
                            'volume': quote.get('volume_today', 0)
                        }
                        combined_data.append(today_entry)
                except Exception as e:
                    logger.error(f"Error fetching live data for {symbol}: {e}")
        formatted_data = []
        for record in combined_data:
            formatted = record.copy()
            formatted['date'] = pd.to_datetime(formatted['date']).isoformat()
            for key in ['open', 'high', 'low', 'close', 'volume']:
                formatted[key] = float(formatted[key])
            formatted_data.append(formatted)
        
        df = pd.DataFrame(formatted_data)
        if not df.empty:
            df['sma_50'] = ta.sma(df['close'], length=min(50, len(df)))
            df['sma_150'] = ta.sma(df['close'], length=min(150, len(df)))
            df['sma_200'] = ta.sma(df['close'], length=min(200, len(df)))
            import numpy as np
            for col in ['sma_50', 'sma_150', 'sma_200']:
                df[col] = df[col].replace([np.inf, -np.inf], np.nan)
                df[col] = df[col].fillna(0)
                df[col] = np.around(df[col], decimals=2)
            import math
            df = df.map(lambda x: 0 if isinstance(x, float) and not math.isfinite(x) else x)
            logger.info(f"get_combined_ohlc: returning {len(df)} rows")
            return df.to_dict(orient="records")
        else:
            return []
    except Exception as e:
        logger.error(f"Error in get_combined_ohlc for instrument {instrument_token}, symbol {symbol}: {e}")
        raise
    finally:
        if conn and cur:
            close_db_connection()

def get_all_alerts():
    
    try:
        conn, cur = get_db_connection()
        alerts = PriceAlert.fetch_all_alerts(cur)
        if alerts is None:
            return []
        logger.info("All alerts fetched successfully.")
        return alerts
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        return []
    finally:
        if conn and cur:
            close_db_connection()

def get_latest_alert_messages():
    
    try:
        conn, cur = get_db_connection()
        messages = AlertMessage.fetch_latest_messages(cur)
        if messages is None:
            return []
        logger.info("Latest alert messages fetched successfully.")
        return messages
    except Exception as e:
        logger.error(f"Error fetching latest alert messages: {e}")
        return []
    finally:
        if conn and cur:
            close_db_connection()
