import logging
from models import RiskPool, SaveTradeDetails, SaveHistoricalTradeDetails, SaveOHLC
from db import get_db_connection, close_db_connection
import json
from datetime import datetime, time
from controllers import kite
import pytz
import pandas_ta as ta
import pandas as pd

logger = logging.getLogger(__name__)

TIMEZONE = pytz.timezone("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 35)

def fetch_risk_pool_for_display():
    conn, cur = get_db_connection()
    try:
        risk_pool = RiskPool.fetch_risk_pool(cur)
        if risk_pool:
            return {
                "used_risk": float(risk_pool['used_risk']),
                "available_risk": float(risk_pool['available_risk'])
            }
        return None
    except Exception as e:
        logger.error(f"Error fetching risk pool for display: {e}")
        raise e
    finally:
        close_db_connection()

def format_trade_record(trade):
    return {
        "stock_name": trade['stock_name'],
        "token": trade['token'],
        "entry_time": trade['entry_time'].isoformat(),
        "entry_price": float(trade['entry_price']),
        "stop_loss": float(trade['stop_loss']),
        "target": float(trade['target']),
        "initial_qty": float(trade['initial_qty']),
        "current_qty": float(trade['current_qty']),
        "booked_pnl": float(trade['booked_pnl'])
    }

def fetch_trade_details_for_display():
    conn, cur = get_db_connection()
    try:
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
        raise e
    finally:
        close_db_connection()

def format_historical_trade_record(trade):
    return {
        "stock_name": trade['stock_name'],
        "entry_time": trade['entry_time'].isoformat(),
        "entry_price": float(trade['entry_price']),
        "exit_time": trade['exit_time'].isoformat() if trade['exit_time'] else None,
        "exit_price": float(trade['exit_price']),
        "final_pnl": float(trade['final_pnl']),
        "highest_qty": float(trade['highest_qty'])
    }

def fetch_historical_trade_details_for_display():
    conn, cur = get_db_connection()
    try:
        trade_details = SaveHistoricalTradeDetails.fetch_all_historical_trades(cur)
        return [format_historical_trade_record(trade) for trade in trade_details] if trade_details else []
    except Exception as e:
        logger.error(f"Error fetching historical trade details: {e}")
        raise e
    finally:
        close_db_connection()

def get_combined_ohlc(instrument_token, symbol):
    """
    Fetch historical OHLC data and combine with real-time data from Kite API.
    Returns: List of OHLC records sorted by date (oldest first).
    """
    conn, cur = get_db_connection()
    combined_data = []
    try:
        historical_data = SaveOHLC.fetch_by_instrument(cur, instrument_token)
        combined_data = [dict(record) for record in historical_data]
        now = datetime.now(TIMEZONE)
        today_date = now.date()
        if not historical_data:
            return combined_data
        last_historical_date = historical_data[-1]['date'].astimezone(TIMEZONE).date()
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
            formatted['date'] = formatted['date'].isoformat()
            for key in ['open', 'high', 'low', 'close', 'volume']:
                formatted[key] = float(formatted[key])
            formatted_data.append(formatted)
        
        # Convert to a DataFrame and compute additional columns
        formatted_data = pd.DataFrame(formatted_data)
        formatted_data['sma_50'] = ta.sma(formatted_data['close'], length=min(50, len(formatted_data)))
        formatted_data['sma_150'] = ta.sma(formatted_data['close'], length=min(150, len(formatted_data)))
        formatted_data['sma_200'] = ta.sma(formatted_data['close'], length=min(200, len(formatted_data)))
        
        # Replace non-finite values (NaN, Inf, -Inf) in SMA columns with None
        import numpy as np
        for col in ['sma_50', 'sma_150', 'sma_200']:
            formatted_data[col] = formatted_data[col].replace([np.inf, -np.inf], np.nan)
            formatted_data[col] = formatted_data[col].fillna(0)

        # Return the JSON serializable result
        return formatted_data.to_dict(orient="records")
    except Exception as e:
        logger.error(f"Error in get_combined_ohlc for instrument {instrument_token}, symbol {symbol}: {e}")
        raise e
    finally:
        close_db_connection()
